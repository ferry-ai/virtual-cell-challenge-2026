"""Official-anchor scores of bench arms, from per-target values, with a paired bootstrap.

A bench writes, per arm, `per_pert_<arm>.csv` (target, metric, value). The six scored members
are means over targets, so an arm's score in official units -- the anchors solved in
`reports/anchors_2026-09-17/anchors.json`, with an optional per-member calibration ratio as in
stage 84 -- is a function of per-member means, and the uncertainty of a DIFFERENCE between two
arms can be resampled over the targets both define. `expr_mse_unbiased_capped_norm` counts 0,
as in stage 84: its anchors are unsolved and the challenge clipped it to 0 in every entry.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = ["MEMBERS", "per_target", "member_means", "score", "calibration", "paired_bootstrap", "consistency"]

MEMBERS = ["pds_cosine", "expr_mse_unbiased_capped_norm", "de_wilcoxon_lfc_nmae",
           "de_wilcoxon_direction_fidelity_yield_raw", "de_wilcoxon_direction_reach_raw",
           "de_wilcoxon_sig_jaccard"]
SCORED = [m for m in MEMBERS if m != "expr_mse_unbiased_capped_norm"]


def per_target(run: Path, arm: str) -> pd.DataFrame:
    """targets x scored members, NaN where the scorer leaves a member undefined."""
    f = pd.read_csv(Path(run) / f"per_pert_{arm}.csv")
    f = f[f.metric.isin(SCORED)]
    return f.pivot_table(index="perturbation", columns="metric", values="value", aggfunc="first").reindex(columns=SCORED)


def member_means(tab: pd.DataFrame) -> dict:
    return {m: float(tab[m].mean()) for m in SCORED}


def score(means: dict, anchors: dict, ratio: dict | None = None) -> float:
    total = 0.0
    for m in SCORED:
        a = anchors[m]
        v = means[m] * (ratio[m] if ratio else 1.0)
        total += (v - a["baseline"]) / (a["replicate"] - a["baseline"])
    return total / len(MEMBERS)


def calibration(run: Path, calib_arm: str, status: dict) -> dict:
    """Per-member official_raw / bench_raw of the arm matching a scored submission (stage 84)."""
    mm = member_means(per_target(run, calib_arm))
    return {m: status[m] / mm[m] for m in SCORED}


def paired_bootstrap(run: Path, arm_a: str, arm_b: str, anchors: dict, ratio: dict | None = None, *,
                     n: int = 2000, seed: int = 2026) -> dict:
    """score(a) - score(b), resampling targets; each member on the targets BOTH arms define."""
    ta, tb = per_target(run, arm_a), per_target(run, arm_b)
    idx = ta.index.intersection(tb.index)
    ta, tb = ta.loc[idx], tb.loc[idx]
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(idx), (n, len(idx)))
    diffs = np.zeros(n)
    point = {}
    for m in SCORED:
        ok = (ta[m].notna() & tb[m].notna()).to_numpy()
        a, b = ta[m].to_numpy(), tb[m].to_numpy()
        w = (ratio[m] if ratio else 1.0) / (anchors[m]["replicate"] - anchors[m]["baseline"]) / len(MEMBERS)
        point[m] = float((a[ok] - b[ok]).mean() * w)
        okd = ok[draws]
        num = np.where(okd, a[draws] - b[draws], 0.0).sum(axis=1)
        diffs += np.where(okd.sum(axis=1) > 0, num / np.maximum(okd.sum(axis=1), 1), 0.0) * w
    return {"diff": float(sum(point.values())), "ci95": [float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))],
            "by_member": point, "n_targets": int(len(idx))}


def consistency(run: Path, arm: str) -> dict:
    """|mean of per-target values - the bench's own aggregate| per member (should be ~0)."""
    raw = json.loads((Path(run) / "bench.json").read_text(encoding="utf-8"))["results"][arm]["raw"]
    mm = member_means(per_target(run, arm))
    return {m: abs(mm[m] - raw[m]) for m in SCORED if raw.get(m) is not None}
