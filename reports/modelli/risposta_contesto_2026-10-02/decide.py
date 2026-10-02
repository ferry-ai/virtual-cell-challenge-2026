"""Apply the frozen P3 rule (PROTOCOLLO.json) to the per-target records of a run.

Writes ``group_means.csv`` (every arm, metric and group), ``context_ablation.json`` (true, retrained
without context, swapped, permutation nulls, target-permuted) and ``decision.json``. The rule is read
from the protocol file; nothing here is tuned on the results.

    py.cmd decide.py --run <p3 output> --protocol PROTOCOLLO.json --out <report folder>
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from common import now_utc, sha256, write_json

SEED = 20261002


def load_records(runs: list[Path], regime: str) -> pd.DataFrame:
    files = sorted(f for run in runs for f in run.glob(f'per_target_{regime}_*.csv.gz'))
    if not files:
        return pd.DataFrame()
    # 'null' is an arm name, not a missing value: only empty cells and 'nan' are missing
    return pd.concat([pd.read_csv(f, keep_default_na=False, na_values=['', 'nan', 'NaN']) for f in files],
                     ignore_index=True)


def oriented(metric: str, proto: dict) -> float:
    return -1.0 if proto['metrics']['secondary'].get(metric) == 'lower' else 1.0


def paired(df: pd.DataFrame, a: str, b: str, metric: str, sign: float = 1.0) -> pd.Series:
    """Per group: mean over rows of sign * (arm a - arm b), rows where both are finite."""
    keys = ['held_group', 'table', 'target_key']
    x = df[df.arm == a].set_index(keys)[metric]
    y = df[df.arm == b].set_index(keys)[metric]
    d = (x - y.reindex(x.index)) * sign
    d = d[np.isfinite(d)]
    return d.groupby(level='held_group').mean()


def group_boot(values: pd.Series, draws: int = 10000) -> list:
    v = values.to_numpy(float)
    if len(v) < 2:
        return [None, None]
    rng = np.random.default_rng(SEED)
    m = rng.choice(v, (draws, len(v)), replace=True).mean(1)
    return [float(np.quantile(m, .025)), float(np.quantile(m, .975))]


def context_rule(df: pd.DataFrame, proto: dict, cand: str, twin: str, swap: str, null_prefix: str) -> dict:
    sec = proto['metrics']['secondary']
    arms = set(df.arm.unique())
    nulls = sorted(a for a in arms if a.startswith(null_prefix))
    prim = proto['metrics']['primary']
    d_ctx = paired(df, cand, twin, prim)
    d_swap = paired(df, cand, swap, prim)
    n = len(d_ctx)
    need = math.ceil(6 / 7 * n)
    null_macro = {nl: float(paired(df, nl, twin, prim).mean()) for nl in nulls}
    c1 = bool(d_ctx.mean() > 0 and (not null_macro or d_ctx.mean() > max(null_macro.values())))
    c2 = bool((d_ctx > 0).sum() >= need)
    c3 = bool(d_swap.mean() > 0 and (d_swap > 0).sum() >= min(5, n))
    c4_detail = {}
    for m in sec:
        s = oriented(m, proto)
        cand_macro = float(paired(df, cand, twin, m, s).mean())
        worst_null = min((float(paired(df, nl, twin, m, s).mean()) for nl in nulls), default=-np.inf)
        c4_detail[m] = dict(candidate_minus_twin=cand_macro, worst_null_minus_twin=worst_null,
                            ok=bool(cand_macro >= worst_null))
    c4 = all(v['ok'] for v in c4_detail.values())
    passed = c1 and c2 and c3 and c4
    inconclusive = (not passed) and c1 and c3 and ((not c2 and (d_ctx > 0).sum() == need - 1 and c4) or (c2 and not c4))
    return dict(candidate=cand, twin=twin, swap=swap, groups=n,
                delta_ctx_by_group=d_ctx.to_dict(), delta_ctx_macro=float(d_ctx.mean()),
                delta_ctx_group_bootstrap_95=group_boot(d_ctx),
                groups_positive=int((d_ctx > 0).sum()), groups_needed=need,
                null_macro=null_macro, delta_swap_by_group=d_swap.to_dict(), delta_swap_macro=float(d_swap.mean()),
                c1=c1, c2=c2, c3=c3, c4=c4, c4_detail=c4_detail, passed=passed, inconclusive=bool(inconclusive))


def chain_rule(df: pd.DataFrame, proto: dict, arm: str, ref: str = 'transfer') -> dict:
    d = paired(df, arm, ref, proto['metrics']['primary'])
    n = len(d)
    h1 = bool(d.mean() > 0 and (d > 0).sum() >= math.ceil(6 / 7 * n))
    sec = {}
    for m in proto['metrics']['secondary']:
        s = oriented(m, proto)
        sec[m] = float(paired(df, arm, ref, m, s).mean())
    h2 = all(v >= 0 for v in sec.values())
    return dict(arm=arm, reference=ref, primary=proto['metrics']['primary'], delta_by_group=d.to_dict(),
                delta_macro=float(d.mean()), delta_group_bootstrap_95=group_boot(d), groups_positive=int((d > 0).sum()), groups=n,
                secondary_oriented_macro=sec, h1=h1, h2=h2, passed=h1 and h2)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--run', type=Path, nargs='+', required=True, help='one or more run folders (C and J)')
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    proto = json.loads(a.protocol.read_text(encoding='utf-8'))
    a.out.mkdir(parents=True)
    result = dict(written_utc=now_utc(), protocol=str(a.protocol), protocol_sha256=sha256(a.protocol),
                  runs=[str(r) for r in a.run],
                  inputs={str(f): sha256(f) for r in a.run for f in sorted(r.glob('per_target_*.csv.gz'))},
                  regimes={})
    ablation = {}
    tables = []
    for regime in ('C', 'J'):
        df = load_records(a.run, regime)
        if df.empty:
            continue
        metrics = ['pds', 'cos', 'cos_spec', 'mse_ratio', 'sign_sig']
        gm = df.groupby(['held_group', 'arm'])[metrics].mean().reset_index()
        gm['regime'] = regime
        tables.append(gm)
        cands = proto['arms'][f'candidates_{regime}']
        ctx = {c: context_rule(df, proto, c, t, proto['arms']['swap'][c], proto['arms']['nulls'][c])
               for c, t in cands.items()}
        out = dict(context=ctx, rows=int(len(df)), groups=sorted(df.held_group.unique()))
        if regime == 'C':
            chain = {arm: chain_rule(df, proto, arm) for arm in proto['rule_C_chain']['applies_to']}
            out['chain'] = chain
            tperm = {c: {m: float(paired(df, c, f'{c}_tperm', m).mean()) for m in ('pds', 'cos', 'cos_spec')}
                     for c in ('m1',) if f'{c}_tperm' in set(df.arm)}
            out['target_specificity'] = tperm
            if any(v['passed'] for v in ctx.values()):
                outcome = 'context_benefit'
            elif any(v['passed'] for v in chain.values()):
                outcome = 'chain_improvement_without_context'
            elif any(v['inconclusive'] for v in ctx.values()):
                outcome = 'inconclusive'
            else:
                outcome = 'no_benefit'
            out['outcome'] = outcome
        else:
            ref = proto['rule_J']
            emb = paired(df, 'embed', 'generic', 'pds')
            out['reference_viability'] = dict(macro_embed_minus_generic=float(emb.mean()),
                                              by_group=emb.to_dict(), passed=bool(emb.mean() > 0))
            out['outcome'] = ('context_benefit' if any(v['passed'] for v in ctx.values()) else
                              'inconclusive' if any(v['inconclusive'] for v in ctx.values()) else 'no_benefit')
            out['protection'] = ref['protection']
        result['regimes'][regime] = out
        ablation[regime] = {c: dict(true_vs_retrained_without_context=v['delta_ctx_by_group'],
                                    true_vs_swapped=v['delta_swap_by_group'], permutation_nulls=v['null_macro'])
                            for c, v in ctx.items()}
    pd.concat(tables).to_csv(a.out / 'group_means.csv', index=False)
    write_json(a.out / 'context_ablation.json', ablation)
    write_json(a.out / 'decision.json', result)
    print(json.dumps({r: v.get('outcome') for r, v in result['regimes'].items()}))


if __name__ == '__main__':
    main()
