"""Small synthetic parity tests and measured input-path benchmark, CPU only."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time
import unittest
import numpy as np
import scipy.sparse as sp
import torch
from ammi_inputs_v3 import module
from ammi_controls_v4 import DiskControls
from ammi_context import ContextCorrection, weighted_masked_loss
from ammi_encoder_v4 import forward_grouped
from ammi_normalized_cache_v1 import NormalizedBlockCache, CachedControl, CachedControlMap
from pie_adapter import sha256

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONTRACT = ROOT/'reports/modelli/dati_transfer_2026-10-08_01a11c34/ammi_ntc_runtime_contract_r3.json'
READER_PIN = json.loads(CONTRACT.read_text())['reader']
READER = module(READER_PIN, 'cache_fixture_pinned_reader')


def fixture(n=513, genes=12, seed=17):
    rng = np.random.default_rng(seed)
    bundles = {}
    for part in range(2):
        counts = rng.poisson(.8, (n, genes)).astype(np.float32)
        masks = rng.random((3, genes)) > .15
        masks[:, 0] = True
        bundles[part] = dict(counts=sp.csr_matrix(counts), masks=masks,
            mask_index=rng.integers(0, 3, n), native_depth=counts.sum(1)+100)
    addresses = np.column_stack((np.arange(n)%2, rng.permutation(n)))
    return DiskControls('synthetic', addresses, bundles, READER, genes)


class CacheTests(unittest.TestCase):
    def test_exact_and_mutation_isolation(self):
        control = fixture()
        cache = NormalizedBlockCache(1 << 20)
        cached = CachedControl(control, cache)
        expected = control.batch(5, 311)
        first = cached.batch(5, 311)
        first[0][:] = -10
        first[1][:] = False
        second = cached.batch(5, 311)
        for left, right in zip(second, expected): np.testing.assert_array_equal(left, right)
        second[0][:] = -100
        third = cached.batch(5, 311)
        np.testing.assert_array_equal(third[0], expected[0])
        self.assertEqual(cache.hits, 2)
        for values, masks in cache.entries.values():
            self.assertFalse(values.flags.writeable)
            self.assertFalse(masks.flags.writeable)

    def test_bounds_eviction_namespace_and_bypass(self):
        cache = NormalizedBlockCache(10*12*5, max_entries=1)
        a, b = CachedControl(fixture(), cache), CachedControl(fixture(seed=19), cache)
        a.batch(0, 10); b.batch(0, 10)
        self.assertEqual(cache.hits, 0)
        self.assertEqual(cache.evictions, 1)
        expected = b.control.batch(0, 10)
        for left, right in zip(b.batch(0, 10), expected): np.testing.assert_array_equal(left, right)
        a.batch(0, 11)
        self.assertEqual(cache.bypasses, 1)
        self.assertLessEqual(cache.peak, cache.max_bytes)
        with self.assertRaises(ValueError): a.batch(-1, 10)
        with self.assertRaises(ValueError): NormalizedBlockCache(-1)

    def test_three_optimizer_updates_bit_exact(self):
        torch.set_num_threads(1)
        torch.manual_seed(17)
        controls = dict(a=fixture(), b=fixture(seed=23))
        cache = NormalizedBlockCache(1 << 20)
        cached = CachedControlMap(controls, cache)
        left = ContextCorrection(12, 4, torch.zeros(6), rank=4, hidden=8)
        right = copy.deepcopy(left)
        optimizers = [torch.optim.AdamW(m.parameters(), lr=.001) for m in (left, right)]
        features, anchor, truth = torch.randn(8, 6), torch.randn(8, 4), torch.randn(8, 4)
        contexts = ['b','a']*4
        mask, weights = torch.ones(8,4,dtype=torch.bool), torch.ones(8)
        encoder_gradient_seen = False
        for step in range(3):
            outputs, losses = [], []
            for model, optimizer, inputs in zip((left,right), optimizers, (controls,cached)):
                optimizer.zero_grad(set_to_none=True)
                prediction, _ = forward_grouped(model,features,contexts,inputs,anchor,'cpu')
                loss = weighted_masked_loss(prediction,truth,mask,weights)
                loss.backward()
                outputs.append(prediction.detach().clone()); losses.append(loss.detach().clone())
            self.assertTrue(torch.equal(outputs[0],outputs[1]))
            self.assertTrue(torch.equal(losses[0],losses[1]))
            for (name,a),(other,b) in zip(left.named_parameters(),right.named_parameters()):
                self.assertEqual(name, other)
                self.assertTrue(torch.equal(a.grad,b.grad), (step,name,'gradient'))
                if name.startswith('cell_encoder') and a.grad.abs().sum()>0: encoder_gradient_seen=True
            for optimizer in optimizers: optimizer.step()
            for a,b in zip(left.parameters(),right.parameters()): self.assertTrue(torch.equal(a,b))
        self.assertTrue(encoder_gradient_seen)
        self.assertGreater(cache.hits,0)


def benchmark():
    control = fixture(2048,128)
    trace = [(start,start+256) for _ in range(12) for start in range(0,2048,256)]
    def trial(budget):
        cache = NormalizedBlockCache(budget) if budget is not None else None
        source = CachedControl(control,cache) if cache else control
        checksum = 0.
        begun = time.perf_counter()
        for start,stop in trace:
            values,masks = source.batch(start,stop)
            checksum += float(values.sum(dtype=np.float64)) + int(masks.sum())
        return dict(seconds=time.perf_counter()-begun,checksum=checksum,
                    cache=cache.stats() if cache else None)
    # Interleave variants to reduce order/warm-up bias; includes cold cache insertion.
    variants = {'uncached':None,'fits':2<<20,'thrashing':256*128*5}
    trial(None)
    measurements = {key:[] for key in variants}
    for _ in range(5):
        for key,budget in variants.items(): measurements[key].append(trial(budget))
    checksums = {row['checksum'] for rows in measurements.values() for row in rows}
    assert len(checksums)==1
    medians = {key:statistics.median(row['seconds'] for row in rows) for key,rows in measurements.items()}
    return dict(synthetic=True,CPU_only=True,cells=2048,genes=128,blocks_per_pass=8,
        passes=12,repeats=5,median_seconds=medians,
        fitting_cache_speedup=medians['uncached']/medians['fits'],
        measurements=measurements,cloud_speedup_measured=False,
        scope='input normalization only; excludes learned encoder, backward and CUDA transfer',
        limitation='LRU may thrash on real contexts larger than the cache; payload bound excludes Python object overhead')


if __name__=='__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CacheTests))
    if not result.wasSuccessful(): raise SystemExit(1)
    report = dict(utc=datetime.now(timezone.utc).isoformat(),status='PASS',tests=result.testsRun,
        parity='bit-exact outputs, losses, gradients and parameters for three AdamW updates',
        reader=READER_PIN,code={name:sha256(HERE/name) for name in
            ('test_ammi_normalized_cache_v1.py','ammi_normalized_cache_v1.py','ammi_controls_v4.py','ammi_encoder_v4.py')},
        benchmark=benchmark(),running_pilots_modified=False)
    out = HERE/'ammi_normalized_cache_verified_r1.json'
    with out.open('x',encoding='utf-8') as stream: json.dump(report,stream,indent=2)
    print(json.dumps(dict(status=report['status'],tests=report['tests'],benchmark=report['benchmark']['median_seconds'])))
