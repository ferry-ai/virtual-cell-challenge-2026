"""Markdown tables of a P3 decision folder: group means of the main arms and the rule's components.

    py.cmd summarize.py --decision <report>/p3_decision_r1 --out <report>/p3_decision_r1/summary.md --runs <C run> <J run>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = {'C': ['null', 'generic', 'transfer', 'tm0', 'm1', 'm1_swap', 'm1_tperm', 'm2_0', 'm2', 'm2_swap'],
        'J': ['null', 'generic', 'embed', 'jm1_0', 'jm1', 'jm1_swap', 'jm1_tperm']}
METRICS = ['cos', 'pds', 'cos_spec', 'sign_sig', 'mse_ratio']


def fmt(x) -> str:
    return '—' if pd.isna(x) else f'{x:+.4f}' if abs(x) < 10 else f'{x:.1f}'


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--decision', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--runs', type=Path, nargs='*', default=[], help='run folders for the per-stratum tables')
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    gm = pd.read_csv(a.decision / 'group_means.csv', keep_default_na=False, na_values=['', 'nan', 'NaN'])
    dec = json.loads((a.decision / 'decision.json').read_text(encoding='utf-8'))
    lines = []
    for regime, arms in MAIN.items():
        sub = gm[gm.regime == regime]
        if sub.empty:
            continue
        lines.append(f'## Regime {regime}: esito `{dec["regimes"][regime]["outcome"]}`\n')
        for m in METRICS:
            t = sub[sub.arm.isin(arms)].pivot(index='held_group', columns='arm', values=m)
            t = t[[c for c in arms if c in t.columns]]
            t.loc['macro'] = t.mean()
            lines.append(f'### {m} (media per gruppo)\n')
            lines.append('| gruppo | ' + ' | '.join(t.columns) + ' |')
            lines.append('|---|' + '---|' * len(t.columns))
            for idx, row in t.iterrows():
                lines.append(f'| {idx} | ' + ' | '.join(fmt(v) for v in row.values) + ' |')
            lines.append('')
        for cand, r in dec['regimes'][regime]['context'].items():
            lines.append(f"**Regola del contesto, {cand}:** c1 {r['c1']}, c2 {r['c2']} ({r['groups_positive']}/{r['groups']} "
                         f"gruppi, servono {r['groups_needed']}), c3 {r['c3']}, c4 {r['c4']}; "
                         f"Δctx macro {r['delta_ctx_macro']:+.5f} (bootstrap sui gruppi {r['delta_ctx_group_bootstrap_95']}), "
                         f"nulli {', '.join(f'{v:+.5f}' for v in r['null_macro'].values())}; Δswap macro {r['delta_swap_macro']:+.5f}. "
                         f"**Passa: {r['passed']}**; inconclusivo: {r['inconclusive']}.\n")
        for arm, r in dec['regimes'][regime].get('chain', {}).items():
            lines.append(f"**Catena, {arm} − transfer:** Δ macro {r['delta_macro']:+.5f} ({r['groups_positive']}/{r['groups']} "
                         f"gruppi positivi), secondari orientati {json.dumps({k: round(v, 5) for k, v in r['secondary_oriented_macro'].items()})}; "
                         f"**passa: {r['passed']}**.\n")
    if a.runs:
        lines += strata_tables(a.runs)
    a.out.write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))


CONTRASTS = {'C': [('m1', 'tm0'), ('m1', 'm1_swap'), ('m1', 'm1_tperm'), ('tm0', 'transfer'), ('m1', 'transfer'),
                   ('m2', 'm2_0'), ('m2', 'm2_swap'), ('m2_0', 'transfer'), ('m2', 'transfer'),
                   ('transfer', 'generic')],
             'J': [('jm1', 'jm1_0'), ('jm1', 'jm1_swap'), ('jm1', 'jm1_tperm'), ('embed', 'generic'),
                   ('jm1_0', 'embed')]}


def strata_tables(runs: list[Path]) -> list[str]:
    """Descriptive only (not part of the rule): macro over groups of paired differences, per stratum."""
    out = ['## Per strato (descrittivo, fuori dalla regola)\n']
    for regime, pairs in CONTRASTS.items():
        files = sorted(f for r in runs for f in r.glob(f'per_target_{regime}_*.csv.gz'))
        if not files:
            continue
        df = pd.concat([pd.read_csv(f, keep_default_na=False, na_values=['', 'nan', 'NaN']) for f in files])
        keys = ['held_group', 'table', 'target_key']
        out.append(f'### Regime {regime}: macro sui gruppi della differenza appaiata (cos / pds / cos_spec)\n')
        out.append('| contrasto | ' + ' | '.join(sorted(df.stratum.unique())) + ' | tutti |')
        out.append('|---|' + '---|' * (df.stratum.nunique() + 1))
        for a_, b_ in pairs:
            if a_ not in set(df.arm) or b_ not in set(df.arm):
                continue
            x = df[df.arm == a_].set_index(keys)
            y = df[df.arm == b_].set_index(keys).reindex(x.index)
            cells = []
            for st in sorted(df.stratum.unique()) + [None]:
                m = (x.stratum == st) if st else np.ones(len(x), bool)
                vals = []
                for metric in ('cos', 'pds', 'cos_spec'):
                    d = (x.loc[m, metric] - y.loc[m, metric]).dropna()
                    vals.append(d.groupby(level='held_group').mean().mean() if len(d) else np.nan)
                cells.append(' / '.join(fmt(v) for v in vals))
            out.append(f'| {a_} − {b_} | ' + ' | '.join(cells) + ' |')
        out.append('')
    return out


if __name__ == '__main__':
    main()
