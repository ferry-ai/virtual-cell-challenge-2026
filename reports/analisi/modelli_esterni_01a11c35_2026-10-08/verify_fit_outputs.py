"""Verify frozen scientific outputs in bounded blocks, without reading training data."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import zipfile

import numpy as np

from pie_adapter import sha256
from predict_saved_ridge import predict


def blocks(archive, name, rows=8):
    """Read a C-order NPY member without decompressing the whole prediction matrix."""
    with archive.open(name + '.npy') as source:
        version = np.lib.format.read_magic(source)
        reader = { (1,0): np.lib.format.read_array_header_1_0,
                   (2,0): np.lib.format.read_array_header_2_0 }.get(version)
        if reader is None:
            raise ValueError('unsupported NPY version')
        shape, fortran, dtype = reader(source)
        if len(shape) != 2 or fortran or dtype.hasobject:
            raise ValueError('expected C-order numeric matrix')
        for start in range(0, shape[0], rows):
            count = min(rows, shape[0]-start)
            size = count*shape[1]*dtype.itemsize
            raw = source.read(size)
            if len(raw) != size:
                raise ValueError('truncated matrix')
            yield start, np.frombuffer(raw, dtype=dtype).reshape(count,shape[1])
        if source.read(1):
            raise ValueError('unexpected trailing data')


def verify(job_root, prepared_path, esm2_root):
    root = Path(job_root)
    fit = root/'fit'
    complete = json.loads((root/'complete.json').read_text())
    receipt = json.loads((fit/'manifest.json').read_text())
    prepared = json.loads(Path(prepared_path).read_text())
    if complete['status'] != 'COMPLETE':
        raise ValueError('terminal completion required')
    for file, key in [('manifest.json','receipt_sha256'), ('ridge.npz','model_sha256'),
                      ('native_predictions.npz','predictions_sha256')]:
        if sha256(fit/file) != complete[key]:
            raise ValueError('artifact checksum mismatch: ' + file)
    if receipt['model_sha256'] != complete['model_sha256'] or receipt['native_predictions_sha256'] != complete['predictions_sha256']:
        raise ValueError('completion/fit identity differs')
    manifest = receipt['manifest']
    queries = manifest['queries']
    genes = receipt['store_receipt']['source_manifest']['genes']
    if len(queries) != prepared['queries']:
        raise ValueError('prepared query count differs')
    with np.load(fit/'ridge.npz', allow_pickle=False) as model:
        support = model['support']
        generic = model['generic']
        coef = model['coef']
        if coef.shape != (1281,len(genes)) or support.shape != (len(genes),) or support.dtype != bool:
            raise ValueError('model axes differ')
        for start in range(0,len(genes),64):
            if not np.isfinite(coef[:,start:start+64]).all():
                raise ValueError('nonfinite coefficient')
        for name in ('intercept','generic','feature_mean','feature_scale','imputation_mean'):
            if not np.isfinite(model[name]).all():
                raise ValueError('nonfinite frozen transform')
        if np.any(model['feature_scale'] <= 0):
            raise ValueError('invalid feature scale')
        del coef
    prediction_path = fit/'native_predictions.npz'
    with np.load(prediction_path, allow_pickle=False) as axes:
        if axes['genes'].tolist() != genes:
            raise ValueError('gene order differs')
        for name, key in [('targets','target'), ('context_ids','context_id'), ('context_groups','context_group')]:
            if axes[name].tolist() != [q[key] for q in queries]:
                raise ValueError('query axis differs: ' + name)
        available = axes['esm2_observed']
        if available.dtype != bool or available.shape != (len(queries),):
            raise ValueError('feature mask differs')
    # Select a few queries before seeing values; include absent features if present.
    selected = sorted(set([0,len(queries)-1] + np.flatnonzero(~available)[:1].tolist()))
    frozen = predict(fit, esm2_root, [queries[i] for i in selected])
    checked = 0
    with zipfile.ZipFile(prediction_path) as archive:
        iterators = [blocks(archive,n) for n in ('effects','observed','generic','generic_observed')]
        for parts in zip(*iterators, strict=True):
            start = parts[0][0]
            effect, observed, baseline, baseline_mask = [p[1] for p in parts]
            stop = start + len(effect)
            expected = available[start:stop,None] & support[None,:]
            if any(p[0] != start for p in parts) or effect.shape != expected.shape:
                raise ValueError('prediction matrix axes differ')
            if observed.dtype != bool or not np.array_equal(observed,expected):
                raise ValueError('specific prediction mask differs')
            if not np.array_equal(np.isfinite(effect),expected) or not np.isnan(effect[~expected]).all():
                raise ValueError('prediction finiteness differs from mask')
            if baseline_mask.dtype != bool or not np.array_equal(baseline_mask,np.broadcast_to(support,effect.shape)):
                raise ValueError('generic mask differs')
            if not np.array_equal(baseline,np.broadcast_to(generic,effect.shape)):
                raise ValueError('generic values differ')
            for index, row in enumerate(selected):
                if start <= row < stop:
                    np.testing.assert_allclose(effect[row-start], frozen['effects'][index], rtol=1e-10, atol=1e-10, equal_nan=True)
                    np.testing.assert_array_equal(observed[row-start],frozen['observed'][index])
            checked += len(effect)
    if checked != len(queries):
        raise ValueError('not all query rows checked')
    return dict(status='PASS',utc=datetime.now(timezone.utc).isoformat(),
                job_id=prepared['job_id'], job_root=str(root.resolve()),
                complete_sha256=sha256(root/'complete.json'),
                prepared_sha256=sha256(prepared_path), receipt_sha256=sha256(fit/'manifest.json'),
                model_sha256=complete['model_sha256'], predictions_sha256=complete['predictions_sha256'],
                queries=checked,genes=len(genes),feature_missing_queries=int((~available).sum()),
                reloaded_prediction_rows=selected, all_prediction_cells_verified=True,
                training_response_arrays_read=False, independent_consumption_check='separate DATI verifier',
                uses_context=False,scientific_benefit='not_scored',emitter_compatibility='not_established')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job-root',type=Path,required=True)
    p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--esm2',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists(): raise FileExistsError(a.out)
    result=verify(a.job_root,a.prepared,a.esm2)
    with a.out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=1)
    print(json.dumps(result))
