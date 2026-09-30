"""Post-hoc description of completed A outputs; no truth, fitting or gate changes.

Reads CSR in blocks of 64 cells, never materializes a full prediction AnnData.
Geometric summaries are diagnostics, not a reimplementation of official PDS.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

import stack_pilot as pilot
from select_stack_ab import h5_strings


def axis(f):
    index = f['var'].attrs.get('_index', '_index')
    if isinstance(index, bytes):
        index = index.decode()
    return h5_strings(f['var'], 'gene_name' if 'gene_name' in f['var'] else index)


def aggregate(f, targets):
    genes = axis(f)
    labels = np.asarray(h5_strings(f['obs'], 'gene'))
    if set(labels) != set(targets):
        raise ValueError('Unexpected target/control identities')
    x = f['X']
    if x.attrs.get('encoding-type') not in ('csr_matrix', b'csr_matrix'):
        raise ValueError('Expected CSR counts')
    arrays = {name: np.zeros((len(targets), len(genes)), dtype=np.float64)
              for name in ('counts', 'cpm', 'log1p_cpm', 'log1p_cpm_half1', 'log1p_cpm_half2')}
    cells, reads = [], []
    for i, target in enumerate(targets):
        rows = np.flatnonzero(labels == target)
        cells.append(len(rows))
        total = 0.
        for start in range(0, len(rows), 64):
            chunk_rows = rows[start:start+64]
            # Rows need not be contiguous in the on-disk matrix.
            chunks = []
            for row in chunk_rows:
                lo, hi = x['indptr'][int(row):int(row)+2]
                data = x['data'][int(lo):int(hi)].astype(np.float64)
                indices = x['indices'][int(lo):int(hi)]
                if not np.isfinite(data).all() or np.any(data < 0) or np.any(data != np.floor(data)):
                    raise ValueError('Invalid raw counts')
                chunks.append(sp.csr_matrix((data, indices, [0, len(data)]), shape=(1, len(genes))))
            block = sp.vstack(chunks, format='csr')
            libraries = np.asarray(block.sum(axis=1)).ravel()
            if np.any(libraries <= 0):
                raise ValueError('Zero-library cell')
            total += libraries.sum()
            arrays['counts'][i] += np.asarray(block.sum(axis=0)).ravel()
            normalized = block.multiply((1e6 / libraries)[:, None]).tocsr()
            arrays['cpm'][i] += np.asarray(normalized.sum(axis=0)).ravel()
            normalized.data = np.log1p(normalized.data)
            arrays['log1p_cpm'][i] += np.asarray(normalized.sum(axis=0)).ravel()
            first = np.arange(start, start + len(chunk_rows)) < len(rows)//2
            for flag, name in ((first, 'log1p_cpm_half1'), (~first, 'log1p_cpm_half2')):
                if flag.any():
                    arrays[name][i] += np.asarray(normalized[flag].sum(axis=0)).ravel()
        reads.append(total)
        arrays['cpm'][i] /= len(rows)
        arrays['log1p_cpm'][i] /= len(rows)
        arrays['log1p_cpm_half1'][i] /= len(rows)//2
        arrays['log1p_cpm_half2'][i] /= len(rows)-len(rows)//2
    arrays['log1p_pooled_cpm'] = np.log1p(arrays['counts'] / np.asarray(reads)[:, None] * 1e6)
    return genes, arrays, {'cells': cells, 'reads': reads}


def geometry(effects):
    common = effects.mean(axis=0)
    residual = effects - common
    total = float(np.sum(effects**2))
    norms = np.linalg.norm(effects, axis=1)
    cos = effects @ effects.T / np.outer(norms, norms)
    upper = cos[np.triu_indices(len(effects), 1)]
    singular = np.linalg.svd(effects, compute_uv=False)
    return {'mean_target_rms': float(np.sqrt(np.mean(effects**2, axis=1)).mean()),
            'common_rms': float(np.sqrt(np.mean(common**2))),
            'target_residual_rms': float(np.sqrt(np.mean(residual**2))),
            'common_energy_fraction': float(len(effects)*np.sum(common**2)/total),
            'first_singular_energy_fraction': float(singular[0]**2/total),
            'mean_pair_cosine': float(upper.mean()), 'median_pair_cosine': float(np.median(upper))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prediction', 'score', 'reports', 'bundle', 'genelist', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    paths = [a.bundle, a.genelist, a.score/'pilot_comparison.json', a.reports/'finished.json']
    comparison = json.loads((a.score/'pilot_comparison.json').read_text())
    finished = json.loads((a.reports/'finished.json').read_text())
    targets = finished['targets']
    members = {}
    with tarfile.open(a.bundle, 'r:gz') as archive:
        for name in ('bundle.json', 'destination_controls.h5ad', 'source_00.h5ad'):
            found = [m for m in archive.getmembers() if Path(m.name).name == name]
            if len(found) != 1:
                raise ValueError('Ambiguous bundle member')
            members[name] = archive.extractfile(found[0]).read()
    bundle = json.loads(members['bundle.json'])
    if bundle['targets'] != targets:
        raise ValueError('Target order mismatch')
    for name in ('destination_controls.h5ad', 'source_00.h5ad'):
        if hashlib.sha256(members[name]).hexdigest() != bundle['files'][name]:
            raise ValueError('Bundle control changed')
    with h5py.File(io.BytesIO(members.pop('source_00.h5ad')), 'r') as f:
        source_genes = set(axis(f))
    with h5py.File(io.BytesIO(members.pop('destination_controls.h5ad')), 'r') as f:
        genes, controls, control_size = aggregate(f, [pilot.CONTROL])
    with a.genelist.open('rb') as f:
        model_genes = set(pilot.GeneListUnpickler(f).load())
    shared = np.array([g in source_genes and g in model_genes for g in genes])
    if shared.sum() != 5179:
        raise ValueError('Frozen shared support mismatch')
    arrays, sizes, metrics = {}, {}, {}
    for arm in ('transfer', 'stack'):
        path = a.prediction/f'prediction_{arm}.h5ad'
        paths.append(path)
        with h5py.File(path, 'r') as f:
            axis_now, arrays[arm], sizes[arm] = aggregate(f, targets)
        if axis_now != genes or sizes[arm]['cells'] != [400]*12:
            raise ValueError('Prediction axis or sample size mismatch')
        path = a.score/f'per_pert_{arm}.csv'; paths.append(path)
        metrics[arm] = pd.read_csv(path).pivot(index='perturbation', columns='metric', values='value').loc[targets]
    masks = {'all_genes': np.ones(len(genes), bool), 'shared_5179': shared,
             'outside_shared': ~shared, 'shared_excluding_pilot_targets': shared & ~np.isin(genes, targets)}
    result = {'claim_type': 'Post-hoc measured output diagnostics, not confirmatory or official scores',
              'truth_expression_read': False, 'reserve_outcomes_read': False,
              'inputs': {str(x): {'sha256': pilot.sha(x), 'bytes': x.stat().st_size} for x in paths},
              'script_sha256': pilot.sha(__file__), 'targets': targets, 'genes': len(genes),
              'control_sizes': control_size, 'prediction_sizes': sizes, 'official_local_comparison': comparison,
              'geometry': {}, 'diagnostics': finished['diagnostics']}
    for transform in ('log1p_cpm', 'log1p_pooled_cpm', 'cpm'):
        result['geometry'][transform] = {}
        for label, mask in masks.items():
            by_arm = {arm: arrays[arm][transform][:, mask] - controls[transform][:, mask] for arm in arrays}
            stats = {arm: geometry(e) for arm, e in by_arm.items()}
            stats['stack_to_transfer_residual_rms_ratio'] = stats['stack']['target_residual_rms']/stats['transfer']['target_residual_rms']
            stats['same_target_cross_arm_cosines'] = [float(np.dot(x, y)/np.linalg.norm(x)/np.linalg.norm(y)) for x, y in zip(by_arm['transfer'], by_arm['stack'])]
            if transform == 'log1p_cpm':
                for arm in arrays:
                    delta = arrays[arm]['log1p_cpm_half1'][:, mask] - arrays[arm]['log1p_cpm_half2'][:, mask]
                    stats[arm]['split_half_noise_rms_for_400cell_mean'] = float(np.sqrt(np.mean(delta**2)/4))
            result['geometry'][transform][label] = stats
    rows = []
    for i, t in enumerate(targets):
        row = {'target': t, **finished['diagnostics'][i]}
        for metric in metrics['transfer'].columns:
            for arm in metrics:
                row[f'{arm}__{metric}'] = float(metrics[arm].loc[t, metric])
            row[f'delta__{metric}'] = float(metrics['stack'].loc[t, metric]-metrics['transfer'].loc[t, metric])
        for arm in arrays:
            effect = arrays[arm]['log1p_cpm'][i] - controls['log1p_cpm'][0]
            row[f'{arm}__effect_rms_shared'] = float(np.sqrt(np.mean(effect[shared]**2)))
        rows.append(row)
    delta_table = pd.DataFrame(rows)
    result['per_metric_delta_counts'] = {m: {'positive': int((delta_table['delta__'+m]>0).sum()),
        'negative': int((delta_table['delta__'+m]<0).sum()), 'zero': int((delta_table['delta__'+m]==0).sum()),
        'missing': int(delta_table['delta__'+m].isna().sum())} for m in metrics['transfer'].columns}
    # A common direction is a numerical observation, not a stress/pathway label.
    common = arrays['stack']['log1p_cpm'].mean(axis=0)-controls['log1p_cpm'][0]
    order = np.argsort(-np.abs(common[shared]))[:30]
    result['shared_common_top30'] = [{'gene': genes[j], 'mean_log1p_cpm_delta': float(common[j])}
                                   for j in np.flatnonzero(shared)[order]]
    try:
        import psutil
        memory = psutil.Process().memory_info()
        result['memory_rss_bytes_end'] = memory.rss
        result['memory_peak_working_set_bytes'] = getattr(memory, 'peak_wset', None)
    except ImportError:
        result['memory_measurement'] = 'psutil unavailable; CSR block limit 64 cells'
    a.out.mkdir(parents=True)
    pilot.write_json(a.out/'analysis.json', result)
    delta_table.to_csv(a.out/'per_target.csv', index=False)
    print(json.dumps({'output': str(a.out), 'shared': int(shared.sum()), 'geometry': result['geometry']['log1p_cpm']['shared_5179']}))


if __name__ == '__main__':
    main()
