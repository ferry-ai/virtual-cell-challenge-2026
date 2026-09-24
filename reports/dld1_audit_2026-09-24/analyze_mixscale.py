"""Explore six-context transfer directly from the Mixscale DE ZIP, using bounded RAM.

Run: scripts\\py.cmd reports\\dld1_audit_2026-09-24\\analyze_mixscale.py --out <new-directory>
"""
import argparse
import hashlib
import json
import re
import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from vcc2026.config import paths
from vcc2026.genes import official_axis


def metrics(pred, truth, control):
    def cos(a, b):
        den = np.linalg.norm(a)*np.linalg.norm(b)
        return float(a@b/den) if den else np.nan
    top = np.argsort(-np.abs(pred), kind='stable')[:100]
    return dict(pearson=cos(pred-pred.mean(), truth-truth.mean()), cosine=cos(pred, truth),
                blind_pearson=cos(control-control.mean(), truth-truth.mean()),
                blind_cosine=cos(control, truth),
                sign_top100=float(np.mean(np.sign(pred[top]) == np.sign(truth[top]))),
                blind_sign_same100=float(np.mean(np.sign(control[top]) == np.sign(truth[top]))))


def main():
    root = paths().data_root
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, default=root/'external/mixscale_zenodo14518762/DE_results_all_pathway.zip')
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    with args.archive.open('rb') as f:
        checksum = hashlib.file_digest(f, 'md5').hexdigest()
    if checksum != 'f077cba680a1affc599f5153d99b0e45':
        raise ValueError('Unexpected archive checksum')
    contexts = ['A549', 'BXPC3', 'HAP1', 'HT29', 'K562', 'MCF7']
    cols = ['log2FC_'+c for c in contexts]
    official = set(official_axis().symbols)
    panel = set(pd.read_csv(root/'raw/controls/pert_counts.csv').iloc[:, 0])
    rows, inventory = [], []
    with zipfile.ZipFile(args.archive) as z:
        files = []
        for name in z.namelist():
            match = re.fullmatch(r'(.+)_(IFNB|IFNG|INS|TGFB1|TNFA)_pathway_DE_results.txt', Path(name).name)
            if match and not name.startswith('__MACOSX/'):
                files.append((name, match[1], match[2]))
        excluded = panel | {t for _, t, _ in files}
        for pathway in sorted({s for _, _, s in files}):
            frames, targets = [], []
            for name, target, stimulus in files:
                if stimulus != pathway:
                    continue
                with z.open(name) as f:
                    df = pd.read_csv(f, sep=r'\s+')
                if df.shape[1] != 19 or not set(['gene_ID', *cols]).issubset(df.columns):
                    raise ValueError(f'Unexpected schema: {name}')
                if not df['gene_ID'].is_unique:
                    raise ValueError(f'Duplicate genes: {name}')
                df = df.set_index('gene_ID')[cols]
                inventory.append(dict(path=name, target=target, pathway=pathway, genes=len(df),
                                      genes_official=len(set(df.index)&official),
                                      finite_per_context={c:int(np.isfinite(df['log2FC_'+c]).sum()) for c in contexts}))
                frames.append(df)
                targets.append(target)
            if len(targets) != len(set(targets)):
                raise ValueError('Duplicate target within a stimulus')
            genes = sorted(set().union(*(set(f.index) for f in frames)) & official - excluded)
            arr = np.stack([f.reindex(genes).to_numpy(float).T for f in frames])
            finite = np.isfinite(arr)
            sums = np.where(finite, arr, 0).sum(axis=0)
            counts = finite.sum(axis=0)
            for i, target in enumerate(targets):
                other_counts = counts-finite[i]
                blind = np.divide(sums-np.where(finite[i], arr[i], 0), other_counts,
                                  out=np.full_like(sums, np.nan), where=other_counts > 0)
                for j, context in enumerate(contexts):
                    train = [c for c in range(6) if c != j]
                    mask = np.isfinite(arr[i]).all(axis=0) & np.isfinite(blind[train]).all(axis=0)
                    if mask.sum() < 100:
                        continue
                    pred = arr[i, train][:, mask].mean(axis=0)
                    truth = arr[i, j, mask]
                    null = blind[train][:, mask].mean(axis=0)
                    rows.append(dict(target=target, pathway=pathway, held_out=context,
                                     genes=int(mask.sum()), **metrics(pred, truth, null)))
            print(f'{pathway}: {len(targets)} targets', flush=True)
    result = pd.DataFrame(rows)
    result.to_csv(args.out/'per_target_context.csv', index=False)
    numeric = ['genes','pearson','cosine','blind_pearson','blind_cosine','sign_top100','blind_sign_same100']
    grouped = result.groupby(['pathway','held_out'])[numeric].median().reset_index()
    grouped.to_csv(args.out/'by_context_stimulus.csv', index=False)
    counts = result.groupby(['pathway','held_out']).size().rename('n_targets').reset_index()
    counts.to_csv(args.out/'counts.csv', index=False)
    summary = dict(claim_type='exploratory leave-one-context-out DE comparison; no VCC score',
                   archive_md5=checksum, contexts=contexts, files=len(files),
                   targets=len({t for _, t, _ in files}), panel_overlap=sorted(panel & {t for _, t, _ in files}),
                   evaluated_rows=len(result), median_over_target_stimulus_context=result[numeric].median().to_dict(),
                   inventory=inventory)
    with (args.out/'measurements.json').open('x', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps({k:v for k,v in summary.items() if k != 'inventory'}, indent=2))


if __name__ == '__main__':
    main()
