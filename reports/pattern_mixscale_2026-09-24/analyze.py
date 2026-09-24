"""Reanalyse existing Mixscale measurements; no fitting or official scoring.

Run with scripts/py.cmd reports/pattern_mixscale_2026-09-24/analyze.py --out <new-dir>
"""
import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd


def summarize(frame):
    # Collapse repeated stimuli/contexts before resampling target identities.
    grouped = frame.groupby('target')[['delta_r', 'delta_sign', 'delta_cos']].mean()
    rng = np.random.default_rng(20260924)
    values = grouped.to_numpy()
    draws = values[rng.integers(len(values), size=(5000, len(values)))].mean(axis=1)
    result = dict(rows=len(frame), targets=len(grouped))
    for i, col in enumerate(grouped):
        result[col] = dict(mean=float(values[:, i].mean()),
                           ci95=np.quantile(draws[:, i], [.025, .975]).tolist())
    result['median_r'] = float(frame.pearson.median())
    result['median_blind_r'] = float(frame.blind_pearson.median())
    result['median_sign'] = float(frame.sign_top100.median())
    result['median_blind_sign'] = float(frame.blind_sign_same100.median())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source = Path('reports/dld1_audit_2026-09-24/mixscale_r1/per_target_context.csv')
    df = pd.read_csv(source)
    assert len(df) == 1626 and df.target.nunique() == 218
    assert not df.duplicated(['target', 'pathway', 'held_out']).any()
    assert df.groupby(['target', 'pathway']).size().eq(6).all()
    df['delta_r'] = df.pearson - df.blind_pearson
    df['delta_cos'] = df.cosine - df.blind_cosine
    df['delta_sign'] = df.sign_top100 - df.blind_sign_same100
    assert np.isfinite(df.select_dtypes('number')).all().all()
    args.out.mkdir(parents=True, exist_ok=False)
    result = dict(claim_type='exploratory paired reanalysis, fixed six lines; not J validation or VCC score',
                  input=str(source), sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  bootstrap='5000 resamples of target identities; equal target weight; seed 20260924',
                  overall=summarize(df),
                  by_stimulus={k:summarize(v) for k,v in df.groupby('pathway')},
                  by_context={k:summarize(v) for k,v in df.groupby('held_out')})
    agg = df.groupby(['target', 'pathway']).agg(
        mean_r=('pearson','mean'), median_r=('pearson','median'),
        mean_delta_r=('delta_r','mean'), min_delta_r=('delta_r','min'),
        positive_contexts=('delta_r',lambda x: int((x>0).sum())),
        mean_delta_sign=('delta_sign','mean')).reset_index()
    agg.sort_values('mean_delta_r', ascending=False).to_csv(args.out/'target_stimulus.csv', index=False)
    result['positive_context_counts'] = {str(k):int(v) for k,v in agg.positive_contexts.value_counts().sort_index().items()}
    result['top_specific'] = agg.sort_values('mean_delta_r',ascending=False).head(15).to_dict('records')
    # Paired contrasts across stimuli use the identical target and line.
    contrasts = []
    for a,b in combinations(sorted(df.pathway.unique()),2):
        left = df[df.pathway.eq(a)].set_index(['target','held_out'])
        right = df[df.pathway.eq(b)].set_index(['target','held_out'])
        common = left.index.intersection(right.index)
        if len(common)<12:
            continue
        paired = left.loc[common,['delta_r','delta_cos','delta_sign']] - right.loc[common,['delta_r','delta_cos','delta_sign']]
        paired = paired.reset_index()
        for col in ['pearson','blind_pearson','sign_top100','blind_sign_same100']:
            paired[col] = 0.0
        stats = summarize(paired)
        for key in list(stats):
            if key.startswith('median_'):
                del stats[key]
        contrasts.append(dict(stimulus_a=a,stimulus_b=b,**stats))
    result['within_target_stimulus_contrasts_a_minus_b'] = contrasts
    # Remove the largest observed gains as a sensitivity check, not a selection rule.
    target_gain = df.groupby('target').delta_r.mean().sort_values(ascending=False)
    result['sensitivity_without_top10_targets'] = summarize(df[~df.target.isin(target_gain.head(10).index)])
    with (args.out/'measurements.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__ == '__main__':
    main()
