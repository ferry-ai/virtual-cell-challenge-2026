"""Evaluate frozen C/T/J splits and paired context controls in effect space.

Example: python scripts/105_ctj_bench.py --cache CACHE --basal basal.csv
    --context-column source_a=A --context-column source_b=B --regime T --out NEW
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from vcc2026.ctj import (Predictor, file_hash, frozen_splits, training_sources,
                         score_targets, paired_bootstrap)
from vcc2026.config import paths
from vcc2026.genes import official_axis
from vcc2026.multisource import AxisTable


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--basal', type=Path, required=True)
    p.add_argument('--context-column', action='append', required=True, metavar='SOURCE=COLUMN')
    p.add_argument('--sources', nargs='+', default=None,
                   help='cache sources to evaluate (default: every npz in --cache)')
    p.add_argument('--regime', choices=['C', 'T', 'J'], required=True)
    p.add_argument('--predictors', nargs='+', default=['null', 'common', 'transfer', 'linear_embedding', 'context_linear'],
                   choices=['null', 'common', 'transfer', 'linear_embedding', 'context_linear'])
    p.add_argument('--splits', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--folds', type=int, default=5)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--k', type=int, default=8, help='PCA rank, 1 to 32 (bounded ridge workspace)')
    p.add_argument('--ridge', type=float, default=.01)
    p.add_argument('--gamma', type=float, default=0.)
    p.add_argument('--reliability-scale', type=float, default=100.)
    p.add_argument('--precision-n', type=int, default=100)
    p.add_argument('--exclude-genes', nargs='*', default=[])
    p.add_argument('--bootstrap', type=int, default=1000)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    if args.bootstrap < 1:
        raise ValueError('bootstrap must be positive')
    contexts = dict(item.split('=', 1) for item in args.context_column)
    axis_path = paths().raw / "controls" / "gene_names.csv"
    genes = list(official_axis(axis_path).symbols)
    hashes = {'basal': file_hash(args.basal),
              'gene_axis': file_hash(axis_path)}
    sources = {}
    files = sorted(args.cache.glob('*.npz'))
    if args.sources is not None:
        unknown = sorted(set(args.sources) - {f.stem for f in files})
        if unknown:
            raise ValueError(f'Sources not in the cache: {unknown}')
        files = [f for f in files if f.stem in set(args.sources)]
    if set(contexts) != {f.stem for f in files}:
        raise ValueError('Provide exactly one context mapping for each cache source')
    for path in files:
        hashes[path.name] = file_hash(path)
        with np.load(path, allow_pickle=False) as data:
            tab = AxisTable(path.stem, data['targets'].astype(str).tolist(),
                            *(data[key].astype(np.float32) for key in ('shrunk', 'raw', 'se', 'n_cells')),
                            json.loads(str(data['meta'])))
        if (len(set(tab.targets)) != len(tab.targets)
                or any(a.shape != (len(tab.targets), len(genes)) for a in (tab.raw, tab.shrunk, tab.se))
                or tab.n_cells.shape != (len(tab.targets),)):
            raise ValueError(f'Invalid cache shape or duplicate targets: {path}')
        sources[path.stem] = tab
    basal_frame = pd.read_csv(args.basal).set_index('gene_name')
    if basal_frame.index.has_duplicates:
        raise ValueError('Duplicate basal genes')
    cpm = {c: basal_frame.loc[genes, c].to_numpy(dtype=np.float32) for c in set(contexts.values())}
    if any(not np.isfinite(v).all() or (v < 0).any() for v in cpm.values()):
        raise ValueError('Basal CPM must be finite and nonnegative on the entire axis')
    basal = {c: np.log1p(v) for c, v in cpm.items()}
    spec = frozen_splits(sources, contexts, hashes, args.regime, args.folds, args.seed, args.splits)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'splits.json').write_text(json.dumps(spec, indent=2), encoding='utf-8')
    records, summaries, comparisons = [], [], []
    metrics = ['pds', 'reach', 'precision_at_n', 'mse_ratio']
    for split_id, split in enumerate(spec['splits']):
        train = training_sources(sources, spec, split)
        for name in args.predictors:
            model = Predictor(name, genes, contexts, basal, args.k, args.ridge,
                              args.gamma, args.reliability_scale).fit(train, split['context'])
            for source, truth in sources.items():
                if contexts[source] != split['context']:
                    continue
                available = {t for s in train.values() for t in s.targets}
                indices = [i for i, t in enumerate(truth.targets)
                           if (t in available if args.regime == 'C' else
                               spec['target_folds'][t] == split['fold'])]
                if not indices:
                    continue
                targets = [truth.targets[i] for i in indices]
                for control, context in [('true', split['context']), ('swapped', split['swap'])]:
                    pred = model.predict(targets, context)
                    scores = score_targets(pred, truth.raw[indices], truth.se[indices], targets,
                                           genes, cpm[split['context']], args.exclude_genes, args.precision_n)
                    for row in scores:
                        records.append(dict(split=split_id, source=source, context=split['context'],
                                            swap=split['swap'], predictor=name, control=control, **row))
            del model
        del train
    frame = pd.DataFrame(records)
    if frame.empty:
        raise ValueError('No held-out targets to evaluate')
    for keys, group in frame.groupby(['split', 'source', 'predictor'], sort=True):
        true = group[group.control == 'true'].set_index('target')
        swap = group[group.control == 'swapped'].set_index('target').reindex(true.index)
        for metric in metrics:
            # Positive always means improvement: reverse the loss metric.
            a, b = (swap[metric], true[metric]) if metric == 'mse_ratio' else (true[metric], swap[metric])
            stats = paired_bootstrap(a, b, spec['seed'], args.bootstrap)
            summaries.append(dict(split=keys[0], source=keys[1], predictor=keys[2], metric=metric,
                                  true=true[metric].mean(), swapped=swap[metric].mean(), **stats))
    for keys, group in frame[frame.control == 'true'].groupby(['split', 'source'], sort=True):
        for first, second in itertools.combinations(sorted(group.predictor.unique()), 2):
            a = group[group.predictor == first].set_index('target')
            b = group[group.predictor == second].set_index('target').reindex(a.index)
            for metric in metrics:
                x, y = (b[metric], a[metric]) if metric == 'mse_ratio' else (a[metric], b[metric])
                comparisons.append(dict(split=keys[0], source=keys[1], first=first, second=second,
                                        metric=metric, **paired_bootstrap(x, y, spec['seed'], args.bootstrap)))
    frame.to_csv(args.out / 'per_target.csv', index=False)
    pd.DataFrame(summaries).to_csv(args.out / 'summary.csv', index=False)
    pd.DataFrame(comparisons).to_csv(args.out / 'comparisons.csv', index=False)
    measurements = dict(arguments={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                        seed=spec['seed'], splits=len(spec['splits']), rows=len(frame),
                        inputs=hashes, training_effect='shrunk', truth_effect='raw',
                        difference='positive means better; mse_ratio uses second minus first',
                        bootstrap_unit='target within split and truth source',
                        missing='NaN metrics excluded pairwise; targets reports the paired count',
                        context='log1p CPM; swapped only at predict; scoring weights remain true context',
                        transfer='C only; T/J lack same-target evidence and return NaN',
                        numpy=np.__version__)
    (args.out / 'measurements.json').write_text(json.dumps(measurements, indent=2), encoding='utf-8')
    print(f'Wrote {len(frame)} target/control records across {len(spec["splits"])} frozen splits')


if __name__ == '__main__':
    main()
