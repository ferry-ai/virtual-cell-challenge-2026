"""Synthetic checks of preregistered inference, sampling, and six-score lifecycle."""
import contextlib
from dataclasses import dataclass
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp
import stack_confirmation_score as confirm

HERE = Path(__file__).resolve().parent
ANCHORS = HERE.parents[2]/'gara/anchors_2026-09-17/anchors.json'


def simple_anchors():
    return {m: {'baseline':0.,'replicate':-1. if 'nmae' in m else 1.} for m in confirm.FIVE}


@dataclass
class FakeConfig:
    synthetic: bool = True


class FakeBench:
    """Exercise integration and ratio-of-sums without running biological scoring."""
    fail_on = None

    def __init__(self, real_x, real_labels, controls, genes, targets, out):
        assert real_x.shape == (24, 3)
        assert controls.shape == (2000, 3)
        self.targets, self.out, self.results, self.cfg = targets, out, {}, FakeConfig()

    def score(self, name, x, labels):
        if name == self.fail_on:
            raise RuntimeError('synthetic interruption')
        assert x.shape == (4800,3)
        assert pd.Series(labels).value_counts().to_dict() == dict.fromkeys(self.targets,400)
        anchors = json.loads(ANCHORS.read_text())['anchors']
        is_stack = name.startswith('stack')
        raw = {m: .3+(anchors[m]['replicate']-anchors[m]['baseline'])*.012*is_stack
               for m in confirm.FIVE}
        mse = 1.1 if is_stack else 1.
        raw['expr_mse_unbiased_capped_norm'] = mse
        rows = []
        for i,target in enumerate(self.targets):
            for metric,value in raw.items():
                rows.append(dict(perturbation=target,metric=metric,value=value))
            rows += [dict(perturbation=target,metric='expr_distance_unbiased',value=i+1),
                     dict(perturbation=target,metric='expr_mse_unbiased_capped',value=mse*(i+1))]
        pd.DataFrame(rows).to_csv(self.out/f'per_pert_{name}.csv',index=False)
        self.results[name] = {'raw':raw}


def fixture(root):
    pilot = confirm.pilot
    bundle, profiles_dir = root/'bundle', root/'profiles'
    bundle.mkdir(); profiles_dir.mkdir()
    genes = np.asarray(['G1','G2','G3'],dtype=str)
    targets = np.asarray(confirm.EXPECTED,dtype=str)
    ctrl = sp.csr_matrix(np.tile([5,6,7],(2000,1)).astype(np.float32))
    pilot.write_counts(bundle/'destination_controls.h5ad',ctrl,genes,pilot.CONTROL)
    truth = root/'truth.h5ad'
    obj = ad.AnnData(sp.csr_matrix(np.tile([6,5,7],(24,1)).astype(np.float32)),
        obs=pd.DataFrame({'gene':pd.Categorical(np.repeat(targets,2))},index=[str(i) for i in range(24)]),
        var=pd.DataFrame(index=genes))
    obj.write_h5ad(truth)
    np.savez_compressed(bundle/'transfer.npz',targets=targets,genes=genes,
                        lfc=np.zeros((12,3),np.float32),observed=np.ones((12,3),bool))
    basal = np.asarray(ctrl.sum(0),np.float64).ravel()
    q0 = pilot.predicted_profile(basal,np.zeros(3),np.ones(3,bool))[0]
    transfer = np.tile(q0,(12,1)).astype(np.float64)
    stack = transfer.copy()
    stack[:,0] += .01*stack[:,1]; stack[:,1] *= .99
    payload = dict(targets=targets,genes=genes,transfer=transfer,stack=stack,
                   basal=basal,library_sizes=np.asarray(ctrl.sum(1),np.float64).ravel(),shared=np.ones(3,bool))
    np.savez_compressed(profiles_dir/'profiles.npz',**payload)
    manifest = dict(targets=list(targets),destination_size=truth.stat().st_size,
        destination_sha256=pilot.sha(truth),protocol_sha256=confirm.PROTOCOL_SHA,
        scoring_code_sha256=pilot.sha(confirm.__file__),inference_adapter_sha256='synthetic-inference',
        adapter_sha256=confirm.PILOT_SHA,
        files={name:pilot.sha(bundle/name) for name in ['destination_controls.h5ad','transfer.npz']})
    pilot.write_json(bundle/'bundle.json',manifest)
    pilot.write_json(profiles_dir/'inference_manifest.json',dict(
        bundle_sha256=pilot.sha(bundle/'bundle.json'),adapter_sha256='synthetic-inference',
        preparation_adapter_sha256=confirm.PILOT_SHA,protocol_sha256=confirm.PROTOCOL_SHA,
        checkpoint_sha256=pilot.CHECKPOINT_SHA,genelist_sha256=pilot.GENELIST_SHA,shared_genes=3,
        versions={'numpy':np.__version__}))
    pilot.write_json(profiles_dir/'finished.json',dict(targets=list(targets),
        final_poisson_seeds=[1,2,3],profile_sha256=pilot.sha(profiles_dir/'profiles.npz'),
        status='profiles_exported_no_final_cells_no_scores',stack_seed=pilot.SEED,
        protocol_sha256=confirm.PROTOCOL_SHA,profile_dtype='float64'))
    return SimpleNamespace(bundle=bundle,profiles=profiles_dir,truth=truth,anchors=ANCHORS,out=root/'scored'),payload


class ConfirmationScoreTests(unittest.TestCase):
    def test_gate_exact_boundaries_and_nonfinite_values(self):
        good = dict(delta=.005,per_seed=[.001,.006,.008],interval=[.0001,.01],pds_delta=0)
        self.assertTrue(confirm.decision(**good))
        for change in [dict(delta=np.nextafter(.005,0)),dict(per_seed=[.01,0,.01]),
                       dict(interval=[0,.01]),dict(pds_delta=-1e-15),dict(valid=False),
                       dict(interval=None),dict(delta=np.inf),dict(interval=[.01,.001])]:
            self.assertFalse(confirm.decision(**(good|change)),change)

    def test_bootstrap_pairs_seeds_and_recomputes_head_denominators(self):
        anchors = simple_anchors(); n=3
        b = np.zeros((3,n,len(confirm.FIVE)))
        b[:,1,1] = np.nan
        a = b.copy()
        spans = np.array([anchors[m]['replicate'] for m in confirm.FIVE])
        for seed in range(3):
            a[seed] += np.arange(1,n+1)[:,None]*(seed+1)*.01*spans
        indices = np.array([[0,0,2],[0,1,2],[2,2,0]])
        summary,boot = confirm.compare(a,b,anchors,indices)
        oracle=[]
        for draw in indices:
            seeds=[]
            for seed in range(3):
                heads=[]
                for j,m in enumerate(confirm.FIVE):
                    values = [a[seed,t,j]-b[seed,t,j] for t in draw if np.isfinite(a[seed,t,j])]
                    heads.append(sum(values)/len(values)/spans[j]/6)
                seeds.append(sum(heads))
            oracle.append(sum(seeds)/3)
        np.testing.assert_allclose(boot,oracle,atol=1e-14)
        self.assertEqual(summary['eligible_targets_per_member'][confirm.FIVE[1]],2)

    def test_missing_bootstrap_head_is_not_dropped_or_imputed(self):
        b = np.zeros((3,2,len(confirm.FIVE))); b[:,0,1]=np.nan
        a = b+.02
        summary,boot = confirm.compare(a,b,simple_anchors(),np.array([[0,0],[1,1]]))
        self.assertTrue(np.isnan(boot[0])); self.assertTrue(np.isfinite(boot[1]))
        self.assertIsNone(summary['paired_target_bootstrap_ci95'])
        self.assertEqual(summary['bootstrap_complete_fraction'],.5)
        self.assertFalse(summary['passes_confirmation'])

    def test_changed_eligibility_or_infinite_metric_rejected(self):
        a = np.ones((3,3,len(confirm.FIVE))); b=a.copy()
        for invalid in ('arm','seed','infinite'):
            c,d=a.copy(),b.copy()
            if invalid=='arm': c[0,0,1]=np.nan
            elif invalid=='seed': c[0,0,1]=d[0,0,1]=np.nan
            else: c[0,0,1]=d[0,0,1]=np.inf
            with self.assertRaises(ValueError): confirm.compare(c,d,simple_anchors())

    def test_pds_guard_uses_name_under_column_permutation(self):
        old=confirm.FIVE; order=old[1:]+old[:1]
        with patch.object(confirm,'FIVE',order):
            a=np.ones((3,4,len(order)))*.1; b=np.zeros_like(a)
            a[:,:,order.index('pds_cosine')]=-.001
            summary,_=confirm.compare(a,b,simple_anchors())
        self.assertLess(summary['mean_pds_raw_delta'],0)
        self.assertFalse(summary['passes_confirmation'])

    def test_sampler_is_bitwise_original_and_libraries_paired(self):
        p=np.array([2.,3.,7.]); libraries=np.array([100.,150.,300.])
        x,d=confirm.generate_profile(p,libraries,'PCBP1',2)
        rng=confirm.target_rng(2,'PCBP1')
        sizes=confirm.resample_library_sizes(libraries,400,rng)
        oracle=confirm.sample_counts(p,sizes,rng,max_stored_per_cell=12000,max_counts_per_cell=1000000)
        np.testing.assert_array_equal(x.toarray(),oracle.toarray())
        _,other=confirm.generate_profile(p[::-1],libraries,'PCBP1',2)
        self.assertEqual(d['sampled_libraries_sha256'],other['sampled_libraries_sha256'])
        x2,_=confirm.generate_profile(p,libraries,'PCBP1',2)
        np.testing.assert_array_equal(x.toarray(),x2.toarray())

    def test_observer_records_caps_without_altering_rng(self):
        rates=np.ones((4,8))*10
        rng=np.random.default_rng(33); observer=confirm.PoissonObserver(rng,10,2)
        counts=observer.poisson(rates)
        np.testing.assert_array_equal(counts,np.random.default_rng(33).poisson(rates))
        self.assertEqual(observer.diagnostics['count_cap_cells'],4)
        self.assertGreater(observer.diagnostics['storage_cap_cells'],0)

    def test_npz_roundtrip_exact_and_support_mass_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,payload=fixture(Path(tmp))
            with np.load(args.profiles/'profiles.npz',allow_pickle=False) as z:
                restored={k:z[k] for k in z.files}
            confirm.validate_profiles(restored,payload['targets'],payload['genes'])
            np.testing.assert_array_equal(restored['stack'],payload['stack'])
            restored['shared'][2]=False; restored['stack'][0,2]+=1
            with self.assertRaisesRegex(ValueError,'fallback'): confirm.validate_profiles(restored,payload['targets'],payload['genes'])

    def test_nonzero_float32_effect_preserves_recorded_numpy_promotion(self):
        effect=np.array([.3,1.7,-.5],dtype=np.float32)
        legacy=confirm.inference_log2_effect(effect,'1.26.4')
        modern=confirm.inference_log2_effect(effect,'2.5.3')
        self.assertEqual(legacy.dtype,np.dtype('float32'))
        self.assertEqual(modern.dtype,np.dtype('float64'))
        np.testing.assert_array_equal(legacy,np.divide(effect,np.float32(np.log(2)),dtype=np.float32))
        self.assertGreater(float(np.max(np.abs(legacy-modern))),1e-8)
        basal=np.array([500.,600.,700.]); mask=np.ones(3,bool)
        old_profile=confirm.pilot.predicted_profile(basal,legacy,mask)[0]
        wrong_profile=confirm.pilot.predicted_profile(basal,modern,mask)[0]
        self.assertFalse(np.allclose(old_profile,wrong_profile,rtol=1e-12,atol=0))
        with self.assertRaises(ValueError): confirm.inference_log2_effect(effect,'3.0.0')

    def test_complete_six_score_pipeline_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,_=fixture(Path(tmp))
            with patch.object(confirm.scorer,'FrozenTruthBench',FakeBench),contextlib.redirect_stdout(io.StringIO()):
                result=confirm.run(args)
            self.assertTrue(result['passes_confirmation'])
            self.assertEqual(len(result['raw']),6)
            self.assertTrue((args.out/'confirmation_comparison.json').exists())
            self.assertEqual(len(list(args.out.glob('per_pert_*.csv'))),6)
            manifest=json.loads((args.out/'evaluation_manifest.json').read_text())
            self.assertEqual(manifest['input_files'][str(args.truth)]['sha256'],confirm.pilot.sha(args.truth))
            self.assertAlmostEqual(result['aggregation_checks']['stack_s1']['ratio'],1.1)
            np.testing.assert_allclose(result['mse_raw_delta_per_seed'],[.1,.1,.1])
            with np.load(args.out/'bootstrap.npz',allow_pickle=False) as z:
                self.assertEqual(z['delta_projection'].shape,(2000,))
            with self.assertRaises(FileExistsError): confirm.run(args)

    def test_profile_tampering_rejected_before_truth_or_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,payload=fixture(Path(tmp))
            payload['stack'][0,0]+=1
            np.savez_compressed(args.profiles/'profiles.npz',**payload)
            with patch.object(confirm.pilot,'read_rows',side_effect=AssertionError('truth read')):
                with self.assertRaisesRegex(ValueError,'archive changed'): confirm.run(args)
            self.assertFalse(args.out.exists())

    def test_failure_after_partial_scores_cannot_write_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,_=fixture(Path(tmp))
            with patch.object(FakeBench,'fail_on','stack_s2'),patch.object(confirm.scorer,'FrozenTruthBench',FakeBench):
                with self.assertRaisesRegex(RuntimeError,'synthetic interruption'): confirm.run(args)
            self.assertTrue((args.out/'evaluation_manifest.json').exists())
            self.assertEqual(len(list(args.out.glob('result_*.json'))),3)
            self.assertFalse((args.out/'confirmation_comparison.json').exists())


if __name__=='__main__':
    unittest.main()
