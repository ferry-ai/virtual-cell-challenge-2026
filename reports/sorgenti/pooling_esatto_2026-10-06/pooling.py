"""Exact stage-98 pooling for the extended bank: the identical refit of t28 must pool BEFORE shrinking.

Stage 98 (scripts/98_multisource_effects.py) calls `vcc2026.multisource.effects_from_pseudobulk` once per
source table on summed-count rows: within a donor every row of a target is summed (across conditions too when
condition=None), one ln fold change per donor, the donor mean weighted by cells, then `z_shrink` once. The
`usable` mask comes from the controls pooled over all donors of the call.

Three tools:
  pool_units          the identical route: concatenate the count-sum rows of the bank units that formed one
                      original table and call the ORIGINAL function (imported, not copied).
  combine_donors      the shortcut when the units are DISJOINT donors, each with one row set: exact from per-donor
                      unmasked statistics (ln fc, variance, cells, evidence) plus the donors' control sums.
                      Not valid when a donor is split across units (H1 train/val, fragments, conditions pooled
                      with condition=None): there the log of sums is not the mean of logs; use pool_units.
  compare_tables      equality report of a new table against the reference (same targets, genes, slots).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
from vcc2026.multisource import effects_from_pseudobulk, z_shrink  # noqa: E402

CALL = {"phi": 0.2, "min_control_frac": 1e-6, "min_cells": 10.0, "pseudo": 0.5, "pseudo_scale": "constant"}


@dataclass
class Unit:
    """Summed-count rows of one bank unit. obs: target ('non-targeting' for controls), donor, condition, n_cells.
    `donor` must name the physical donor or clone: the same donor in two units gets the same label."""
    name: str
    X: object               # rows x genes, counts (dense or sparse)
    obs: pd.DataFrame
    genes: np.ndarray


def pool_units(units: list[Unit], *, targets, condition=None, min_expected: float = 0.0, **call):
    """Identical route: one call of the original estimator on the concatenated rows."""
    genes = np.asarray(units[0].genes).astype(str)
    for u in units[1:]:
        if not np.array_equal(np.asarray(u.genes).astype(str), genes):
            raise ValueError(f"{u.name}: gene axis differs from {units[0].name}")
    X = sp.vstack([sp.csr_matrix(u.X) for u in units]).tocsr()
    obs = pd.concat([u.obs[["target", "donor", "condition", "n_cells"]] for u in units], ignore_index=True)
    kw = {**CALL, **call}
    return effects_from_pseudobulk(X, obs, genes, targets=targets, condition=condition,
                                   min_expected=min_expected, **kw)


@dataclass
class DonorStats:
    """One donor's unmasked statistics for each target it informs (n_t >= min_cells), as stage 98 forms them."""
    donor: str
    targets: list[str]
    eff: np.ndarray          # targets x genes, ln fc before any mask
    var: np.ndarray          # targets x genes, quasi-Poisson variance of eff
    n_t: np.ndarray          # cells per target
    evidence: np.ndarray     # targets x genes, controls predict >= min_expected counts (all True when 0)
    ctrl_sum: np.ndarray     # genes, the donor's control counts (for the pooled usable mask)


def donor_stats(X, obs, genes, donor, *, targets, condition=None, min_expected=0.0, **call) -> DonorStats:
    """Per-donor statistics with the formulas of effects_from_pseudobulk (checked end to end by the tests)."""
    kw = {**CALL, **call}
    X = sp.csr_matrix(X)
    obs = obs.reset_index(drop=True)
    tcol = obs["target"].to_numpy().astype(str)
    dcol = obs["donor"].to_numpy().astype(str)
    ncol = obs["n_cells"].to_numpy().astype(np.float64)
    use = np.ones(len(obs), bool) if condition is None else (obs["condition"].to_numpy() == condition)
    m = use & (tcol == "non-targeting") & (dcol == donor)
    cs = np.asarray(X[m].sum(axis=0, dtype=np.float64)).ravel()
    cn = float(ncol[m].sum())
    out_t, E, V, N, EV = [], [], [], [], []
    for t in targets:
        mt = use & (tcol == t) & (dcol == donor)
        if not mt.any():
            continue
        n_t = float(ncol[mt].sum())
        if n_t < kw["min_cells"]:
            continue
        st = np.asarray(X[mt].sum(axis=0, dtype=np.float64)).ravel()
        if kw["pseudo_scale"] == "library":
            ref = min(st.sum(), cs.sum())
            pt, pc = kw["pseudo"] * (st.sum() / ref), kw["pseudo"] * (cs.sum() / ref)
        else:
            pt = pc = kw["pseudo"]
        E.append(np.log((st + pt) / st.sum()) - np.log((cs + pc) / cs.sum()))
        V.append(1.0 / (st + pt) + kw["phi"] / n_t + 1.0 / (cs + pc) + kw["phi"] / cn)
        EV.append(cs * (st.sum() / cs.sum()) >= min_expected if min_expected > 0 else np.ones(cs.size, bool))
        N.append(n_t)
        out_t.append(t)
    G = np.asarray(genes).size
    z = np.zeros((0, G))
    return DonorStats(donor, out_t, np.array(E) if E else z, np.array(V) if V else z, np.array(N),
                      np.array(EV) if EV else z.astype(bool), cs)


def combine_donors(parts: list[DonorStats], *, targets, min_expected=0.0, min_control_frac=1e-6):
    """Shortcut for DISJOINT donors: cell-weighted mean of the donors' unmasked ln fc, then z_shrink once, with the
    usable mask of the pooled controls. Returns (targets kept, shrunk, raw, se, n_cells) like the original."""
    pooled = sum(p.ctrl_sum for p in parts)
    usable = pooled / pooled.sum() >= min_control_frac
    G = pooled.size
    kept, S, R, SE, NC = [], [], [], [], []
    for t in targets:
        num, var, wv, wsum = np.zeros(G), np.zeros(G), np.zeros(G), 0.0
        for p in sorted(parts, key=lambda q: q.donor):             # the original iterates donors sorted
            if t not in p.targets:
                continue
            i = p.targets.index(t)
            n = p.n_t[i]
            ev = p.evidence[i]
            num += np.where(ev, n * p.eff[i], 0.0)
            var += np.where(ev, n ** 2 * p.var[i], 0.0)
            wv += np.where(ev, n, 0.0)
            wsum += n
        if wsum <= 0:
            continue
        if min_expected > 0:
            has = wv > 0
            eff = np.where(has, num / np.where(has, wv, 1.0), np.nan)
            se = np.where(has, np.sqrt(var) / np.where(has, wv, 1.0), np.nan)
        else:
            eff, se = num / wsum, np.sqrt(var) / wsum
        S.append(np.where(usable, z_shrink(eff, se), 0.0).astype(np.float32))
        R.append(np.where(usable, eff, 0.0).astype(np.float32))
        SE.append(se.astype(np.float32))
        NC.append(int(wsum))
        kept.append(t)
    return kept, np.array(S), np.array(R), np.array(SE), np.array(NC)


def compare_tables(new: dict, ref: dict, *, rtol=1e-5, atol=1e-6) -> dict:
    """new/ref: {'targets': [...], 'genes': [...], 'shrunk', 'raw', 'se': targets x genes, 'n_cells': per target}.
    Equal means same targets, same genes, same NaN pattern and allclose on every slot."""
    rep = {"targets_only_new": sorted(set(new["targets"]) - set(ref["targets"])),
           "targets_only_ref": sorted(set(ref["targets"]) - set(new["targets"]))}
    if list(map(str, new["genes"])) != list(map(str, ref["genes"])):
        rep["genes_equal"] = False
        rep["equal"] = False
        return rep
    rep["genes_equal"] = True
    common = [t for t in ref["targets"] if t in set(new["targets"])]
    ia = [list(new["targets"]).index(t) for t in common]
    ib = [list(ref["targets"]).index(t) for t in common]
    ok = not rep["targets_only_new"] and not rep["targets_only_ref"]
    for slot in ("shrunk", "raw", "se"):
        a = np.asarray(new[slot])[ia].astype(np.float64)
        b = np.asarray(ref[slot])[ib].astype(np.float64)
        nan_same = np.array_equal(np.isnan(a), np.isnan(b))
        fin = np.isfinite(a) & np.isfinite(b)
        diff = np.abs(a - b)[fin]
        close = bool(np.allclose(a[fin], b[fin], rtol=rtol, atol=atol))
        rep[slot] = {"nan_pattern_equal": nan_same, "allclose": close,
                     "max_abs_diff": float(diff.max()) if diff.size else 0.0,
                     "entries_off": int((~np.isclose(a[fin], b[fin], rtol=rtol, atol=atol)).sum())}
        ok &= nan_same and close
    nc_eq = bool(np.array_equal(np.asarray(new["n_cells"])[ia], np.asarray(ref["n_cells"])[ib]))
    rep["n_cells_equal"] = nc_eq
    rep["equal"] = bool(ok and nc_eq)
    return rep


def as_table(src) -> dict:
    """SourceEffects (or the combine_donors tuple with genes) to the compare_tables dict."""
    if isinstance(src, tuple):
        (kept, S, R, SE, NC), genes = src
        return {"targets": kept, "genes": list(genes), "shrunk": S, "raw": R, "se": SE, "n_cells": NC}
    return {"targets": list(src.targets), "genes": list(src.genes), "shrunk": src.shrunk, "raw": src.raw,
            "se": src.se, "n_cells": src.n_cells}
