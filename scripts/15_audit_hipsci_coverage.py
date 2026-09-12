"""Measure target and context support from downloaded HIPSCI metadata only."""
import json
from pathlib import Path
import pandas as pd


def main():
    root = Path(__file__).resolve().parents[1] / 'reports/data_audit'
    local = pd.read_csv(root / 'target_inventory.csv').set_index('target_gene')
    targets = set(local.index)
    missing = set(local.index[local['missing_all_local_sources']])
    summaries, tables = {}, []
    for path in sorted((root / 'hipsci_metadata').glob('*Cell-Metadata.tsv.gz')):
        df = pd.read_csv(path, sep='\t', usecols=['Guide_Call', 'Cell_Line', 'Batch'])
        # Require exactly one gene/20-base guide assignment. Multiplets and
        # unassigned cells cannot count as evidence of a single perturbation.
        symbol = df.Guide_Call.str.extract(r'^([^_,;+|]+)_[ACGT]{20}$', expand=False)
        unmatched = df.loc[symbol.isna(), 'Guide_Call'].value_counts().head(8).to_dict()
        valid = symbol.notna() & ~symbol.eq('NonTarget') & df.Cell_Line.notna()
        df = df.loc[valid].assign(target_gene=symbol[valid])
        counts = df.groupby(['target_gene', 'Cell_Line', 'Batch'], observed=True).size().rename('n_cells').reset_index()
        label = path.name.split('_Cell-Metadata')[0]
        counts['source'] = label
        tables.append(counts)
        hits = targets & set(df.target_gene)
        rescued = missing & hits
        summaries[label] = {'valid_single_guide_rows': len(df),
            'cell_line_labels': sorted(df.Cell_Line.unique().tolist()),
            'unmatched_guide_labels_top': unmatched,
            'target_hits': len(hits), 'rescued_vs_replogle': sorted(rescued),
            'hits': sorted(hits)}
    table = pd.concat(tables, ignore_index=True)
    table.loc[table.target_gene.isin(targets)].to_csv(root / 'hipsci_target_context_batch_counts.csv', index=False)
    support = table.loc[table.target_gene.isin(targets)].groupby(['source', 'target_gene', 'Cell_Line']).n_cells.sum()
    support_summary = support.groupby('source').agg(['count', 'median', 'max'])
    support_summary['pairs_ge100'] = support.ge(100).groupby('source').sum()
    support_summary['pairs_ge400'] = support.ge(400).groupby('source').sum()
    support_summary.to_csv(root / 'hipsci_support_summary.csv')
    all_hits = set().union(*(set(s['hits']) for s in summaries.values()))
    summaries['combined'] = {'target_hits': len(all_hits), 'rescued_vs_replogle': sorted(missing & all_hits),
        'still_missing': sorted(missing - all_hits),
        'note': 'Metadata support only; RNA matrix presence, donor mapping, QC, guide efficacy and effective sample size remain to verify.'}
    (root / 'hipsci_coverage.json').write_text(json.dumps(summaries, indent=2), encoding='utf-8')
    for k, v in summaries.items():
        print(k, {x: y for x, y in v.items() if x not in ['hits', 'cell_line_labels']})


if __name__ == '__main__':
    main()
