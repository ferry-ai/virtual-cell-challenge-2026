"""Private CPU job: verify all inputs, smoke on real rows, fit frozen view."""
import json
import os
from pathlib import Path
import shutil
import threading
import time
import urllib.request
from datetime import datetime, timezone

import numpy as np

from chunk_store_v2 import build_store, load_store
from embedding_ridge import MaskedRidge
from feature_policy import POLICY, prepare_features
from job_preflight import validate
from pie_adapter import sha256
from run_sufficient_probe_v2 import load_features, run
from runtime_view_resolver import resolve
from target_sufficient_ridge_v2 import TargetSufficientRidge


def write_new(path, data):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(data, f, indent=1, allow_nan=False)


def resources(stage, root):
    def kb_fields(path):
        return {line.split(':')[0]:int(line.split(':')[1].strip().split()[0])*1024
                for line in Path(path).read_text().splitlines() if ':' in line and line.strip().endswith('kB')}
    memory = kb_fields('/proc/meminfo')
    process = kb_fields('/proc/self/status')
    return dict(utc=datetime.now(timezone.utc).isoformat(), stage=stage,
                cpu_count=os.cpu_count(), available_ram=memory['MemAvailable'],
                rss=process['VmRSS'], peak_rss=process['VmHWM'], disk_free=shutil.disk_usage(root).free)


def smoke(store, receipt_hash, esm, expected):
    y, m, axes, _ = load_store(store, receipt_hash)
    n, g = min(128, y.shape[0]), min(32, y.shape[1])
    targets = axes['targets'][:n].tolist()
    contexts = axes['context_groups'][:n].tolist()
    unique_targets = list(dict.fromkeys(targets))
    by_name = {t:i for i,t in enumerate(unique_targets)}
    indices = np.array([by_name[t] for t in targets])
    x, available, _ = load_features(esm, expected, unique_targets)
    x, _, _ = prepare_features(x, available, len(x), indices, axes['weights'][:n], POLICY)
    yy, mm = np.asarray(y[:n, :g]), m[:n, :g]
    policy = dict(row_targets=targets, row_contexts=contexts, excluded_targets=[],
                  excluded_contexts=[], sample_weight=axes['weights'][:n])
    start = time.monotonic()
    dense = MaskedRidge(1.).fit(x[indices], yy, mm, **policy)
    reduced = TargetSufficientRidge(1.).fit(x, yy, mm, feature_targets=unique_targets,
        row_feature_indices=indices, row_block=32, gene_block=16, **policy)
    np.testing.assert_allclose(dense.coef, reduced.coef, rtol=1e-8, atol=1e-9)
    np.testing.assert_allclose(dense.intercept, reduced.intercept, rtol=1e-8, atol=1e-9)
    return dict(status='PASS', rows=n, genes=g, seconds=time.monotonic()-start,
                max_coef_error=float(np.max(np.abs(dense.coef-reduced.coef))),
                purpose='technical real-data smoke; not validation or complete training')


def main(bundle):
    bundle = Path(bundle)
    config = json.loads((bundle/'job_config.json').read_text())
    scratch = Path('/kaggle/temp')/config['job_id']
    output = Path('/kaggle/working')/config['job_id']
    scratch.mkdir(parents=True, exist_ok=False)
    output.mkdir(parents=True, exist_ok=False)
    phase = ['preflight']
    stopped = threading.Event()
    def heartbeat():
        while not stopped.is_set():
            state = resources(phase[0], scratch)
            with (output/'heartbeat.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(state)+'\n')
            print(json.dumps(state), flush=True)
            stopped.wait(45)
    thread = threading.Thread(target=heartbeat, daemon=True); thread.start()
    try:
        contract = json.loads((bundle/'preflight.json').read_text())
        write_new(output/'package_preflight.json', validate(contract, 'runtime'))
        view = json.loads((bundle/'view.json').read_text())
        rows = sum(view['expected_rows_by_context'].values())
        required = rows*len(view['genes'])*4 + config['private_bytes'] + 2*1024**3
        initial = resources('before_input_staging', scratch)
        initial['required_disk_including_cache_outputs_margin'] = required
        write_new(output/'initial_resources.json', initial)
        if initial['disk_free'] < required or initial['available_ram'] < 3*1024**3:
            raise ValueError('insufficient runtime disk/RAM margin')
        phase[0] = 'resolve_all_chunks'
        resolved = scratch/'resolved_view.json'
        resolve(bundle/'view.json', config['view_sha256'], ['/kaggle/input'],
                scratch/'private-cache', resolved, bundle/'private_locators.json')
        # The resolver removes bearer locators from the view and its receipt.
        shutil.copy2(resolved.with_suffix('.receipt.json'), output/'resolution_receipt.json')
        view = json.loads(resolved.read_text())
        chunk_contract = dict(schema_version=1, job_id=config['job_id']+'-chunks',
            inputs=[dict(id='chunk-'+str(i), paths={'runtime':c['path']},
                sha256=c['sha256'], bytes=c['bytes']) for i,c in enumerate(view['chunks'])],
            outputs=[dict(id='store', paths={'runtime':str(scratch/'store')}, must_be_absent=True)],
            environment={'packages':{'numpy':None,'scipy':None},
                         'imports':['numpy','scipy.linalg'], 'probes':[]})
        write_new(output/'chunk_preflight.json', validate(chunk_contract, 'runtime'))
        phase[0] = 'acquire_pinned_esm2'
        esm = scratch/'esm2'; esm.mkdir()
        for name, item in config['esm2'].items():
            path = esm/name
            with urllib.request.urlopen(item['url'], timeout=120) as response, path.open('xb') as target:
                shutil.copyfileobj(response, target, length=1024**2)
            if path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
                raise ValueError('pinned ESM2 download differs')
        expected = {n:i['sha256'] for n,i in config['esm2'].items()}
        phase[0] = 'stage_full_view'
        view['mask_storage'] = 'finite_verified'
        stage_spec = scratch/'store_spec.json'; write_new(stage_spec, view)
        started = time.monotonic()
        store = scratch/'store'; build_store(stage_spec, store)
        write_new(output/'staging.json', dict(seconds=time.monotonic()-started,
            rows=rows, contexts=len(view['expected_rows_by_context']),
            store_receipt_sha256=sha256(store/'manifest.json'), resources=resources('staged',scratch)))
        shutil.copy2(store/'manifest.json', output/'store_manifest.json')
        phase[0] = 'real_smoke'
        write_new(output/'real_smoke.json', smoke(store, sha256(store/'manifest.json'), esm, expected))
        manifest = {k:view[k] for k in ('quantity','normalization','modality','regime',
            'release_sha256','split_manifest_sha256','expected_rows_by_context','excluded_targets','excluded_contexts')}
        manifest.update(schema_version=1, protocol_status='agreed',
            validation_review={'technical_fit':'authorized', 'scientific_admission':'pending'},
            mode='production' if view['regime']=='production' else 'development', alpha=1.,
            train={'path':str(store),'sha256':sha256(store/'manifest.json')},
            esm2={'path':str(esm),'sha256':expected}, queries=config['queries'],
            missing_feature_policy=POLICY, gene_block=64, row_block=128, factor_cache=2)
        fit_manifest = output/'fit_manifest.json'; write_new(fit_manifest, manifest)
        phase[0] = 'full_fit'
        checkpoint = output/'checkpoints'; checkpoint.mkdir()
        def progress(model, start, stop, counters):
            dest = checkpoint/f'genes_{start:05d}_{stop:05d}.npz'
            np.savez_compressed(dest, coef=model.coef[:,start:stop], intercept=model.intercept[start:stop],
                generic=model.generic[start:stop], support=model.support[start:stop],
                feature_mean=model.feature_mean, feature_scale=model.feature_scale)
            counters.update(resources('fit_gene_block', scratch), checkpoint_sha256=sha256(dest))
            with (output/'progress.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(counters)+'\n')
            print(json.dumps(counters), flush=True)
        receipt = run(fit_manifest, output/'fit', progress=progress)
        write_new(output/'complete.json', dict(status='COMPLETE', scientific_benefit='not_scored',
            model_sha256=receipt['model_sha256'], predictions_sha256=receipt['native_predictions_sha256'],
            receipt_sha256=sha256(output/'fit'/'manifest.json'), resources=resources('complete', scratch)))
    except Exception as exc:
        # No exception text: network exceptions may carry bearer URLs.
        write_new(output/'failure.json', dict(stage=phase[0], exception_type=type(exc).__name__,
            resources=resources('failed',scratch)))
        print(json.dumps(dict(status='FAILED', stage=phase[0], exception_type=type(exc).__name__)), flush=True)
        raise RuntimeError('Private job failed; see sanitized phase/type receipt') from None
    finally:
        stopped.set(); thread.join(timeout=1)


if __name__ == '__main__':
    main(Path(__file__).parent)
