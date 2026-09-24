"""Audit existing DLD1 Low1 matrices without modifying data or submission caches.

Run: scripts\\py.cmd reports\\dld1_audit_2026-09-24\\audit.py --out <new-directory>
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from vcc2026.config import paths
from vcc2026.genes import official_axis


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def summary(values):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    return {'n': len(values), **dict(zip(('p10', 'median', 'p90'),
            map(float, np.quantile(values, [.1, .5, .9]))))} if len(values) else {'n': 0}


def similarity(left, right, pearson=False):
    if pearson:
        left = left - left.mean(axis=1, keepdims=True)
        right = right - right.mean(axis=1, keepdims=True)
    denom = np.linalg.norm(left, axis=1)[:, None] * np.linalg.norm(right, axis=1)[None, :]
    return np.divide(left @ right.T, denom, out=np.full(denom.shape, np.nan), where=denom > 0)


def describe_pairs(scores, targets, metric, rows):
    correct = np.diag(scores)
    wrong = scores.copy()
    np.fill_diagonal(wrong, np.nan)
    baseline = np.nanmedian(wrong, axis=1)
    discrimination = []
    for i, target in enumerate(targets):
        valid = wrong[i, np.isfinite(wrong[i])]
        rank = float(np.mean((correct[i] > valid) + .5 * (correct[i] == valid))) if len(valid) else np.nan
        discrimination.append(rank)
        rows.append(dict(target=target, metric=metric, matched=correct[i],
                         mismatched_median=baseline[i], discrimination=rank))
    return dict(matched=summary(correct), mismatched_median_per_target=summary(baseline),
                paired_difference=summary(correct-baseline), discrimination=summary(discrimination))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    root = paths().data_root
    p.add_argument('--source', type=Path, default=root/'external/dld1_gse337988')
    p.add_argument('--cache', type=Path, default=root/'processed/multisource_2026-09-23_r5/k562.npz')
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((args.source/'manifest.json').read_text())
    checked = []
    for record in manifest['files']:
        path = args.source/record['file']
        actual = digest(path)
        if actual != record['sha256'] or path.stat().st_size != record['bytes']:
            raise ValueError(f'Manifest mismatch: {path}')
        checked.append(dict(file=path.name, sha256=actual, bytes=path.stat().st_size))
    print('Manifest verified', flush=True)
    lfc_path = args.source/'GSE337988_sublib2_de_matrices_lfc_matrix_Low1.csv.gz'
    se_path = args.source/'GSE337988_sublib2_de_matrices_se_matrix_Low1.csv.gz'
    with gzip.open(lfc_path, 'rt') as f:
        header = next(csv.reader(f))
    with gzip.open(se_path, 'rt') as f:
        if next(csv.reader(f)) != header:
            raise ValueError('LFC and SE column axes differ')
    if len(set(header)) != len(header):
        raise ValueError('Duplicate source columns')
    labels = {}
    unmatched = []
    for col in header[1:]:
        match = re.fullmatch(r'(.+)_P(\d+)', col)
        if match:
            labels[col] = (match[1], int(match[2]))
        else:
            unmatched.append(col)
    controls = root/'raw/controls'
    panel = pd.read_csv(controls/'pert_counts.csv').iloc[:, 0].astype(str).tolist()
    axis = list(official_axis().symbols)
    chosen = {target: col for col, (target, suffix) in labels.items() if suffix == 1 and target in panel}
    print(f'Reading {len(chosen)} P1 columns', flush=True)
    lfc = pd.read_csv(lfc_path, usecols=['gene', *chosen.values()]).set_index('gene')
    se = pd.read_csv(se_path, usecols=['gene', *chosen.values()]).set_index('gene')
    if not lfc.index.is_unique or not se.index.is_unique or not lfc.index.equals(se.index):
        raise ValueError('Duplicate or mismatched gene rows')
    invalid_se = int((~np.isfinite(se.to_numpy()) | (se.to_numpy() <= 0)).sum())
    with np.load(args.cache, allow_pickle=False) as cache:
        kt = cache['targets'].astype(str).tolist()
        kr = cache['raw'].astype(float)
    if kr.shape != (len(kt), len(axis)):
        raise ValueError('K562 dimensions differ from official axis')
    targets = [t for t in panel if t in chosen and t in kt]
    if len(targets) < 3:
        raise ValueError('Too few shared targets')
    d = lfc.reindex(axis)[[chosen[t] for t in targets]].to_numpy(dtype=float).T
    k = kr[[kt.index(t) for t in targets]]
    mask = np.isfinite(d).all(axis=0) & np.isfinite(k).all(axis=0) & ~np.isin(axis, panel)
    d, k = d[:, mask], k[:, mask]
    if d.shape[1] < 100:
        raise ValueError('Too few common measured genes')
    rows, metrics = [], {}
    for mode in ('raw', 'source_mean_removed'):
        kd = k if mode == 'raw' else k-k.mean(axis=0)
        dd = d if mode == 'raw' else d-d.mean(axis=0)
        for name, center in [('cosine', False), ('pearson', True)]:
            label = f'{mode}_{name}'
            metrics[label] = describe_pairs(similarity(kd, dd, center), targets, label, rows)
    signs = np.empty((len(targets), len(targets)))
    for i in range(len(targets)):
        top = np.argsort(-np.abs(k[i]), kind='stable')[:100]
        signs[i] = np.mean(np.sign(k[i, top])[None, :] == np.sign(d[:, top]), axis=1)
    metrics['raw_sign_top100_k562'] = describe_pairs(signs, targets, 'raw_sign_top100_k562', rows)
    measured_targets = sorted(set(t for t, _ in labels.values()) & set(panel))
    result = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                  claim_type='exploratory measurements, not VCC scores',
                  input_files=checked, k562_sha256=digest(args.cache),
                  panel_sha256=digest(controls/'pert_counts.csv'),
                  axis_sha256=digest(controls/'gene_names.csv'),
                  script_sha256=digest(Path(__file__)),
                  source_columns=len(header)-1, parsed_distinct_labels=len(set(t for t, _ in labels.values())),
                  unparsed_columns=unmatched, panel_targets_any_suffix=measured_targets,
                  panel_targets_p1=sorted(chosen), targets_shared_k562=targets,
                  missing_panel_targets=sorted(set(panel)-set(measured_targets)),
                  genes_source=len(lfc), genes_on_official_axis=len(set(lfc.index)&set(axis)),
                  official_axis_size=len(axis), genes_comparison=int(mask.sum()),
                  invalid_or_nonpositive_se_p1=invalid_se,
                  metrics=metrics,
                  limitations=['Low1 only; P1 only; units not converted',
                               'Raw limma/source coefficients and K562 pseudobulk estimates may differ',
                               'K562 axis inferred from stage98 contract; cache lacks embedded gene names',
                               'Column suffix meaning not independently verified',
                               'No replicate ceiling, no official score, no adoption decision'])
    with (args.out/'measurements.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
    pd.DataFrame(rows).to_csv(args.out/'per_target.csv', index=False)
    print(json.dumps({key: result[key] for key in ['source_columns', 'genes_source', 'genes_on_official_axis',
                      'genes_comparison', 'invalid_or_nonpositive_se_p1', 'metrics']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
