"""Level A of the independent validation (contract v1): effect-space measures, one value per target.

Proxies of what the scorer reads, computed against a truth table of aggregated effects. Not VCC scores.
The definitions follow `vcc2026.multisource.transfer_report` (same valid pairs, same discrimination rank,
same sign measures), kept per target so that two arms can be compared target by target, and
`test_metrics.py` checks them against that function.

    disc        1 - normalised rank of a target's own truth among all truths, by cosine  (primary)
    r_spec      Pearson of prediction and truth after removing each side's mean over targets (primary)
    sign50      sign agreement among the 50 largest predicted effects on the truth's confident genes
    reach       deepest prefix of that ranking with purity >= 0.9, over the confident genes
    nmae_conf   sum |p - o| / sum |o| on the confident genes      (< 1 is better than predicting zero)
    mse_ratio   sum (p - o)^2 / sum o^2 on the valid genes        (< 1 is better than predicting zero)

"Confident" truth genes have |raw / se| >= 3. `o` is the truth's shrunk effect for disc, r_spec and the
sign measures, as in the library, and its raw effect for the two error ratios.
"""
from __future__ import annotations

import numpy as np

Z_CONF = 3.0
HEAD = 50
PURITY_FLOOR = 0.9
BOOT = 10_000
BOOT_SEED = 20261008
MEASURES = ("disc", "r_spec", "sign50", "reach", "nmae_conf", "mse_ratio")
HIGHER_IS_BETTER = {"disc": True, "r_spec": True, "sign50": True, "reach": True, "nmae_conf": False,
                    "mse_ratio": False}


def valid_pairs(observed: np.ndarray, shrunk: np.ndarray, raw: np.ndarray, se: np.ndarray, exclude_cols) -> np.ndarray:
    """(T, G) pairs a prediction can be judged on: predicted, measured by the truth with a finite z."""
    with np.errstate(all="ignore"):
        z = raw / se
    valid = np.asarray(observed, bool) & np.isfinite(shrunk) & np.isfinite(z)
    if len(exclude_cols):
        valid[:, np.asarray(list(exclude_cols), dtype=int)] = False
    return valid


def _purity_depth(pred_sign: np.ndarray, obs_sign: np.ndarray) -> int:
    if pred_sign.size == 0:
        return 0
    agree = np.cumsum(pred_sign == obs_sign)
    ok = np.flatnonzero(agree / np.arange(1, pred_sign.size + 1) >= PURITY_FLOOR)
    return int(ok[-1] + 1) if ok.size else 0


def per_target(pred: np.ndarray, valid: np.ndarray, shrunk: np.ndarray, raw: np.ndarray, se: np.ndarray,
               cols: np.ndarray | None = None) -> dict:
    """Every measure for every row. ``valid`` from `valid_pairs`; ``cols`` are the genes used by the
    discrimination rank (default: valid for every row), given explicitly when several arms must share them."""
    P = np.asarray(pred, np.float64)
    O = np.asarray(shrunk, np.float64)
    R = np.asarray(raw, np.float64)
    with np.errstate(all="ignore"):
        Z = R / np.asarray(se, np.float64)
    n = P.shape[0]
    if cols is None:
        cols = valid.all(axis=0)
    out = {m: np.full(n, np.nan) for m in MEASURES}
    out["n_valid"] = valid.sum(axis=1).astype(float)
    out["n_conf"] = np.zeros(n)
    with np.errstate(all="ignore"):
        Pc = P - np.nanmean(np.where(valid, P, np.nan), axis=0)
        Oc = O - np.nanmean(np.where(valid, O, np.nan), axis=0)
    for i in range(n):
        v = valid[i]
        if v.sum() < 20:
            continue
        p, o, r, z = P[i, v], O[i, v], R[i, v], Z[i, v]
        pc, oc = Pc[i, v], Oc[i, v]
        if pc.std() > 0 and oc.std() > 0:
            out["r_spec"][i] = float(np.corrcoef(pc, oc)[0, 1])
        den = float((r * r).sum())
        if den > 0:
            out["mse_ratio"][i] = float(((p - r) ** 2).sum() / den)
        conf = np.abs(z) >= Z_CONF
        out["n_conf"][i] = float(conf.sum())
        if conf.sum() == 0:
            continue
        den = float(np.abs(r[conf]).sum())
        if den > 0:
            out["nmae_conf"][i] = float(np.abs(p[conf] - r[conf]).sum() / den)
        order = np.argsort(-np.abs(p[conf]), kind="stable")
        ps, os_ = np.sign(p[conf][order]), np.sign(o[conf][order])
        k = min(HEAD, ps.size)
        out["sign50"][i] = float(np.mean(ps[:k] == os_[:k]))
        out["reach"][i] = _purity_depth(ps, os_) / conf.sum()
    A, B = np.where(cols, P, 0.0), np.where(cols, O, 0.0)
    na, nb = np.linalg.norm(A, axis=1), np.linalg.norm(B, axis=1)
    cos = (A @ B.T) / np.maximum(np.outer(na, nb), 1e-12)
    own = np.diag(cos)
    ranks = (cos > own[:, None]).sum(axis=1) + 0.5 * ((cos == own[:, None]).sum(axis=1) - 1)
    out["disc"] = 1.0 - ranks / max(n - 1, 1)
    return out


def arm_summary(pred: np.ndarray, valid: np.ndarray, raw: np.ndarray, cols: np.ndarray, own_cols: np.ndarray,
                observed: np.ndarray) -> dict:
    """Diagnostics of one arm on one fold: common share, amplitude, agreement of the two mean responses, and
    the effect on the target's own gene. ``own_cols[i]`` is the axis column of target i's gene, -1 if absent."""
    P = np.asarray(pred, np.float64)
    R = np.asarray(raw, np.float64)
    Pm, Rm = np.where(cols, P, 0.0), np.where(cols, np.nan_to_num(R), 0.0)
    mp, mr = Pm.mean(axis=0), Rm.mean(axis=0)

    def share(M, m):
        row = float((M * M).sum(axis=1).mean())
        return float((m * m).sum() / row) if row > 0 else float("nan")

    pv, rv = np.where(valid, P, 0.0), np.where(valid, np.nan_to_num(R), 0.0)
    pp = float((pv * pv).sum())
    amp = float((pv * rv).sum() / pp) if pp > 0 else float("nan")
    nmp, nmr = float(np.linalg.norm(mp)), float(np.linalg.norm(mr))
    own_p, own_r = [], []
    for i, j in enumerate(own_cols):
        if j >= 0 and observed[i, j] and np.isfinite(R[i, j]):
            own_p.append(P[i, j])
            own_r.append(R[i, j])
    own = {"pairs": len(own_p)}
    if len(own_p) >= 3:
        a, b = np.asarray(own_p), np.asarray(own_r)
        own.update(pred_mean=float(a.mean()), truth_mean=float(b.mean()),
                   pearson=float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else None)
    return {"common_share_pred": share(Pm, mp), "common_share_truth": share(Rm, mr),
            "cos_of_means": float(mp @ mr / (nmp * nmr)) if nmp > 0 and nmr > 0 else None,
            "amplitude_star": amp, "rms_pred": float(np.sqrt((pv * pv).sum() / max(valid.sum(), 1))),
            "rms_truth": float(np.sqrt((rv * rv).sum() / max(valid.sum(), 1))), "genes_for_rank": int(cols.sum()),
            "own_gene": own}


def shuffled_rows(n: int, seed: int = BOOT_SEED) -> np.ndarray:
    """A derangement of range(n): every row gets another target's prediction (the target-shuffle control)."""
    if n < 2:
        raise ValueError("a shuffle needs at least two targets")
    rng = np.random.default_rng([seed, n])
    while True:
        perm = rng.permutation(n)
        if not (perm == np.arange(n)).any():
            return perm


def paired_bootstrap(a: np.ndarray, b: np.ndarray, *, seed: int = BOOT_SEED, n_boot: int = BOOT) -> dict:
    """Mean of a - b over the targets where both are finite, with a percentile interval from resampling
    targets. The unit is the target; cells and seeds are not replicates here."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    d = a[ok] - b[ok]
    if d.size < 2:
        return {"n": int(d.size), "mean": float(d.mean()) if d.size else None, "lo": None, "hi": None,
                "resolved": False, "boot": None}
    rng = np.random.default_rng([seed, d.size])
    means = d[rng.integers(0, d.size, size=(n_boot, d.size))].mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return {"n": int(d.size), "mean": float(d.mean()), "lo": float(lo), "hi": float(hi),
            "resolved": bool(lo > 0 or hi < 0), "share_positive": float((d > 0).mean()),
            "share_negative": float((d < 0).mean()), "boot": means}


def macro(per_fold: list) -> dict:
    """Equal-weight mean over folds of the per-fold mean differences, resampling targets within each fold."""
    usable = [r for r in per_fold if r.get("boot") is not None]
    if not usable:
        return {"folds": 0, "mean": None, "lo": None, "hi": None, "resolved": False}
    means = np.mean([r["boot"] for r in usable], axis=0)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return {"folds": len(usable), "mean": float(np.mean([r["mean"] for r in usable])), "lo": float(lo),
            "hi": float(hi), "resolved": bool(lo > 0 or hi < 0)}


def strip(result: dict) -> dict:
    """A bootstrap result without its resampled means, for JSON."""
    return {k: v for k, v in result.items() if k != "boot"}
