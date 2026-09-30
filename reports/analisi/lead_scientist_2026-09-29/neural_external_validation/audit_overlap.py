"""Metadata-only feasibility audit. Never reads X or perturbation effect values."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import h5py
import numpy as np
import pandas as pd


def strings(node):
    if isinstance(node, h5py.Group):
        categories = strings(node['categories'])
        codes = node['codes'][:]
        return np.asarray([categories[i] if i >= 0 else '' for i in codes], dtype=str)
    return np.asarray([x.decode() if isinstance(x, bytes) else str(x) for x in node[:]], dtype=str)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    r2 = a.data_root / 'processed/rete_contesti_r2'
    pool_manifest = json.loads((r2 / 'manifest.json').read_text())
    targets = pd.read_csv(r2 / 'targets.csv', keep_default_na=False)
    contexts = pd.read_csv(r2 / 'contexts.csv', keep_default_na=False)
    axis = pd.read_csv(r2 / 'axis.csv').gene.astype(str).tolist()
    genes = pd.read_csv(r2 / 'genes.csv').gene.astype(str).tolist()
    panel = set(targets.loc[targets.in_panel.astype(str).str.lower() == 'true', 'target'])
    raw = a.data_root / 'raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad'
    with h5py.File(raw, 'r') as f:
        labels = strings(f['obs/gene'])
        response = strings(f['var/gene_name'])
        counts = Counter(labels)
        shape = list(f['X'].shape)
        dtype = str(f['X'].dtype)
    eligible = {t for t, n in counts.items() if t != 'non-targeting' and n >= 50 and t in set(axis)}
    old_bank_path = a.data_root / 'processed/banco_hepg2_v2_2026-09-26/targets.txt'
    old_bank = set(old_bank_path.read_text().splitlines())
    rtargets = np.load(r2 / 'row_target.npy', mmap_mode='r')
    names = targets.target.to_numpy(dtype=str)
    sources = {}
    for c in contexts.itertuples():
        observed = set(names[rtargets[c.row_start:c.row_stop]])
        sources[c.context] = {'targets': len(observed), 'panel_direct': len(panel & observed),
                              'hepg2_eligible_direct': len(eligible & observed)}
    cache = {}
    for name in ('k562', 'cd4_mix', 'cd4_Rest', 'cd4_Stim8hr', 'cd4_Stim48hr', 'orion_hct116', 'orion_hek293t'):
        path = a.data_root / f'processed/multisource_2026-09-27_r9/{name}.npz'
        with np.load(path, allow_pickle=False) as z:
            ts = set(z['targets'].astype(str))
        cache[name] = {'targets': len(ts), 'panel_overlap': len(ts & panel),
                       'hepg2_eligible_overlap': len(ts & eligible)}
    result = {'created_utc': datetime.now(timezone.utc).isoformat(),
              'claim_type': 'measured metadata only; no X, source effects or model/scorer outputs read',
              'raw_file': str(raw), 'raw_file_bytes': raw.stat().st_size,
              'shape': shape, 'dtype': dtype, 'all_labels': len(counts),
              'perturbation_targets': len(set(counts) - {'non-targeting'}),
              'control_cells': counts['non-targeting'], 'challenge_panel': len(panel),
              'panel_target_overlap': sorted(panel & set(counts)),
              'panel_response_gene_overlap': len(panel & set(response)),
              'response_genes': len(response), 'response_unique': len(set(response)),
              'response_overlap_official_axis': len(set(response) & set(axis)),
              'response_overlap_r2_model_axis': len(set(response) & set(genes)),
              'eligible_targets_min50_on_axis': len(eligible),
              'eligible_targets_in_r2': len(eligible & set(names)),
              'eligible_cell_count_quantiles': np.quantile([counts[t] for t in eligible], [0,.25,.5,.75,1]).tolist(),
              'current_basal_names': pool_manifest['basal_names'],
              'hepg2_in_current_basal_pool': any('hepg2' in str(x).lower() for x in pool_manifest['basal_names']),
              'old_generator_bank_targets': len(old_bank),
              'eligible_outside_entire_old_generator_bank': len(eligible - old_bank),
              'old_generator_bank_sha256': hashlib.sha256(old_bank_path.read_bytes()).hexdigest(),
              'r2_direct_source_membership': sources, 'r9_cached_membership': cache,
              'small_input_sha256': {n: hashlib.sha256((r2/n).read_bytes()).hexdigest()
                                     for n in ('targets.csv','contexts.csv','genes.csv','axis.csv','row_target.npy')}}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
