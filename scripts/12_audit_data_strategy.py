"""Read-only audit of local inputs; write small reports inside the repository.

Run with scripts/py.cmd scripts/12_audit_data_strategy.py.
No downloads, imputation, normalization in place, or writes to source data.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
from scipy import sparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=Path('C:/Users/ferra/vcc2026-data'))
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'reports/data_audit')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    bundle = args.data_root / 'raw/controls'
    genes = pd.read_csv(bundle / 'gene_names.csv')['gene_name'].astype(str)
    targets = pd.read_csv(bundle / 'pert_counts.csv')['target_gene'].astype(str).drop_duplicates()
    if genes.duplicated().any():
        raise ValueError('Duplicate challenge gene symbols require explicit resolution')
    source_files = {
        'k562_gwps': 'K562_gwps_raw_bulk_01.h5ad',
        'k562_essential': 'K562_essential_raw_bulk_01.h5ad',
        'rpe1': 'rpe1_raw_bulk_01.h5ad',
    }
    coverage = pd.DataFrame(index=targets)
    coverage.index.name = 'target_gene'
    gene_coverage = pd.DataFrame(index=pd.Index(genes, name='gene_name'))
    summary = {'sources': {}, 'contexts': {}, 'caveats': [
        'Symbol-exact matching; alias/Ensembl reconciliation still required.',
        'CPM >5 reproduces the control-expression gate, before own-target exclusion.',
        'core_control is an author annotation, not proof of a non-targeting guide.',
        'Existing source checksums are not recomputed by this audit.',
    ]}
    pattern = re.compile(r'^\d+_(.+?)_(P[0-9P]*|ENST[^_]+)_(ENSG\d+|nan)$')
    for label, name in source_files.items():
        a = ad.read_h5ad(args.data_root / 'external' / name)
        parsed = [pattern.match(str(x)) for x in a.obs_names]
        symbols = {m[1] for m in parsed if m}
        src_genes = set(a.var['gene_name'].astype(str))
        coverage[label] = coverage.index.isin(symbols)
        gene_coverage[label] = gene_coverage.index.isin(src_genes)
        sample = a.X[:min(500, a.n_obs)]
        sample = sample.toarray() if sparse.issparse(sample) else np.asarray(sample)
        num = a.obs.get('num_cells_filtered')
        summary['sources'][label] = {
            'path': str(args.data_root / 'external' / name),
            'shape': list(a.shape), 'targets_hit': int(coverage[label].sum()),
            'genes_hit': int(gene_coverage[label].sum()),
            'duplicate_gene_symbols': int(a.var['gene_name'].duplicated().sum()),
            'unparsed_obs_count': sum(m is None for m in parsed),
            'sample_min': float(sample.min()), 'sample_max': float(sample.max()),
            'sample_fraction_noninteger': float(np.mean(np.abs(sample - np.rint(sample)) > 1e-5)),
            'median_cells_filtered_per_row': None if num is None else float(num.median()),
            'core_control_rows': int(a.obs['core_control'].sum()) if 'core_control' in a.obs else None,
        }
        del a
    coverage['missing_all_local_sources'] = ~coverage.any(axis=1)
    gene_coverage['any_source'] = gene_coverage.any(axis=1)
    for ctx in ['A', 'B', 'C']:
        a = ad.read_h5ad(bundle / f'context_{ctx}.h5ad', backed='r')
        try:
            if not np.array_equal(a.var_names.astype(str), genes.to_numpy()):
                raise ValueError(f'Gene order mismatch: {ctx}')
            total_cpm = np.zeros(a.n_vars, dtype=np.float64)
            total_counts = np.zeros(a.n_vars, dtype=np.float64)
            detected = np.zeros(a.n_vars, dtype=np.int64)
            totals = []
            for start in range(0, a.n_obs, 512):
                x = a.X[start:start + 512]
                x = sparse.csr_matrix(x, dtype=np.float64)
                x.eliminate_zeros()
                if not np.isfinite(x.data).all() or (x.data < 0).any() or not np.allclose(x.data, np.rint(x.data), atol=1e-6, rtol=0):
                    raise ValueError(f'Invalid raw counts in {ctx}')
                lib = np.asarray(x.sum(axis=1)).ravel()
                if (lib <= 0).any():
                    raise ValueError(f'Zero library in {ctx}')
                totals.extend(lib.tolist())
                total_counts += np.asarray(x.sum(axis=0)).ravel()
                total_cpm += np.asarray(x.multiply((1e6 / lib)[:, None]).sum(axis=0)).ravel()
                detected += x.getnnz(axis=0)
            mean_cpm = total_cpm / a.n_obs
            gate = mean_cpm > 5
            gene_coverage[f'{ctx}_mean_cpm'] = mean_cpm
            gene_coverage[f'{ctx}_de_gate'] = gate
            target_positions = genes.tolist()
            positions = {g: i for i, g in enumerate(target_positions)}
            for field, values in [('mean_cpm', mean_cpm), ('detection_rate', detected / a.n_obs)]:
                coverage[f'{ctx}_{field}'] = [values[positions[t]] if t in positions else np.nan for t in coverage.index]
            ctx_summary = {'n_cells': a.n_obs, 'median_umi': float(np.median(totals)), 'de_gate_genes': int(gate.sum())}
            for label in [*source_files, 'any_source']:
                observed = gene_coverage[label].to_numpy()
                ctx_summary[label] = {
                    'de_gate_covered': int((gate & observed).sum()),
                    'de_gate_coverage_fraction': float((gate & observed).sum() / max(1, gate.sum())),
                    'basal_umi_mass_coverage': float(total_counts[observed].sum() / total_counts.sum()),
                }
            summary['contexts'][ctx] = ctx_summary
        finally:
            a.file.close()
    coverage.to_csv(args.out / 'target_inventory.csv')
    gene_coverage.to_csv(args.out / 'gene_coverage.csv')
    coverage.loc[coverage['missing_all_local_sources']].to_csv(args.out / 'acquisition_targets.csv')
    (args.out / 'audit.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
