"""Same-target effects from several perturbation sources, on the official gene axis.

This module implements the same-target transfer baseline: for target t it borrows
responses from contexts where t was perturbed. This is a constraint of this method,
not a requirement for research datasets or models of unseen perturbation targets
(D-044, docs/GENERALIZZAZIONE.md). It puts every source on one footing -- ln fold
change of pooled fractions against the source's own non-targeting controls, a
quasi-Poisson standard error and empirical-Bayes shrinkage, as `effects_from_bulk` does
for the K562 bulk -- and then:

* `effects_from_pseudobulk`: the same estimate from summed-count rows (guide x donor x
  condition, e.g. the CD4 pseudobulk), one fold change per donor against that donor's own
  controls, averaged over donors;
* `AxisTable`: one source's effects, SE and measured-gene mask on the official axis;
* `mix`: a reliability-weighted average over the sources that measured each
  (target, gene), after removing ``gamma`` x each source's own mean response. A pair a
  source did not measure never votes zero (D-009);
* `transfer_report`: how well one set of effects predicts another, in effect space, with
  proxies for what the scorer reads: centred correlation, sign purity at the head of the
  prediction's own ranking, discrimination among targets, and squared-error skill at the
  best single amplitude. Proxies, not scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import scipy.sparse as sp

from vcc2026.predictor_sc import SourceEffects

__all__ = ["effects_from_pseudobulk", "z_shrink", "AxisTable", "mix", "shared_signal", "transfer_report"]


def z_shrink(eff: np.ndarray, se: np.ndarray, k: float = 4.0) -> np.ndarray:
    """Local shrinkage ``eff * z^2 / (z^2 + k)``, with ``z = eff / se``.

    The single-normal prior of `sc_effects.eb_shrink` fits one variance to all genes of a
    target. A knockdown response is sparse, so that variance is set by the many null genes
    and the few large effects are crushed: K562 HDAC1's own knockdown goes from ln -2.46 to
    -0.35 (stage 98, 2026-09-22). Here each gene keeps a share that grows with its own
    evidence: 0.2 at |z| = 1, 0.5 at |z| = 2, 0.86 at |z| = 5. ``k`` is fixed, not tuned.
    """
    eff = np.asarray(eff, dtype=np.float64)
    z2 = np.divide(eff * eff, np.asarray(se, dtype=np.float64) ** 2,
                   out=np.zeros_like(eff), where=np.asarray(se) > 0)
    return eff * z2 / (z2 + k)


def effects_from_pseudobulk(X, obs: pd.DataFrame, genes, *, targets, condition: str | None = None,
                            phi: float = 0.2, min_control_frac: float = 1e-6,
                            min_cells: float = 10.0, pseudo: float = 0.5) -> SourceEffects:
    """Per-target ln fold changes from summed-count pseudobulk rows.

    ``obs`` needs ``target`` ('non-targeting' for controls), ``donor``, ``condition`` and
    ``n_cells``. Within ``condition`` (all conditions pooled when None), each donor's rows
    for a target are summed and compared with the same donor's control rows:
    ``ln((S_t + pseudo) / L_t) - ln((S_c + pseudo) / L_c)``, with ``S`` a gene's summed counts
    and ``L`` the group's total. The variance is quasi-Poisson on those counts,
    ``1/(S_t + pseudo) + 1/(S_c + pseudo) + phi/n_t + phi/n_c``. The donor fold changes are
    averaged with weights equal to the target's cells in that donor. Donors with fewer than
    ``min_cells`` target cells are skipped. ``shrunk`` is `z_shrink` of the donor mean.
    """
    X = sp.csr_matrix(X)            # keep the stored dtype; sums are taken in float64
    genes = np.asarray(genes).astype(str)
    obs = obs.reset_index(drop=True)
    target_col = obs["target"].to_numpy().astype(str)
    donor_col = obs["donor"].to_numpy().astype(str)
    cells_col = obs["n_cells"].to_numpy().astype(np.float64)
    use = np.ones(len(obs), dtype=bool) if condition is None else (obs["condition"].to_numpy() == condition)
    is_ntc = target_col == "non-targeting"
    donors = sorted(set(donor_col[use]))

    def colsum(mask):
        return np.asarray(X[mask].sum(axis=0, dtype=np.float64)).ravel()

    ctrl = {}
    for d in donors:
        m = use & is_ntc & (donor_col == d)
        if not m.any():
            continue
        ctrl[d] = (colsum(m), float(cells_col[m].sum()))
    pooled_ctrl = sum(v[0] for v in ctrl.values())
    ctrl_frac = pooled_ctrl / pooled_ctrl.sum()
    usable = ctrl_frac >= min_control_frac
    rows_s, rows_r, rows_se, ncell, kept = [], [], [], [], []
    per_donor_used = {}
    for t in targets:
        eff_sum = np.zeros(genes.size)
        var_sum = np.zeros(genes.size)
        wsum = 0.0
        used = []
        for d, (cs, cn) in ctrl.items():
            m = use & (target_col == t) & (donor_col == d)
            if not m.any():
                continue
            n_t = float(cells_col[m].sum())
            if n_t < min_cells:
                continue
            st = colsum(m)
            e = np.log((st + pseudo) / st.sum()) - np.log((cs + pseudo) / cs.sum())
            v = 1.0 / (st + pseudo) + phi / n_t + 1.0 / (cs + pseudo) + phi / cn
            eff_sum += n_t * e
            var_sum += n_t**2 * v
            wsum += n_t
            used.append(d)
        if wsum <= 0:
            continue
        eff = eff_sum / wsum
        se = np.sqrt(var_sum) / wsum
        shr = np.where(usable, z_shrink(eff, se), 0.0)
        rows_s.append(shr.astype(np.float32))
        rows_r.append(np.where(usable, eff, 0.0).astype(np.float32))
        rows_se.append(se.astype(np.float32))
        ncell.append(int(wsum))
        kept.append(t)
        per_donor_used[t] = used
    meta = {"condition": condition, "donors": donors, "phi": phi,
            "n_control_cells": int(sum(v[1] for v in ctrl.values())),
            "se_model": f"quasi-Poisson phi={phi}, donor-weighted"}
    if not kept:
        return SourceEffects(genes, [], np.zeros((0, genes.size), np.float32), np.zeros((0, genes.size), np.float32),
                             np.zeros((0, genes.size), np.float32), np.zeros(0, int), ctrl_frac, meta)
    return SourceEffects(genes, kept, np.vstack(rows_s), np.vstack(rows_r), np.vstack(rows_se),
                         np.array(ncell), ctrl_frac, meta)


@dataclass
class AxisTable:
    """One source's effects on the official axis. Unmeasured entries are NaN, never zero."""

    name: str
    targets: list[str]
    shrunk: np.ndarray            # (T, G) ln fold change, NaN where unmeasured
    raw: np.ndarray               # (T, G)
    se: np.ndarray                # (T, G)
    n_cells: np.ndarray           # (T,)
    meta: dict = field(default_factory=dict)

    @classmethod
    def from_source(cls, name: str, src: SourceEffects, axis, *, usable_frac: float = 1e-6) -> "AxisTable":
        axis = np.asarray(axis).astype(str)
        pos = pd.Index(axis).get_indexer(np.asarray(src.genes).astype(str))
        ok = (pos >= 0) & (np.asarray(src.control_mean) >= usable_frac)
        T, G = len(src.targets), axis.size
        out = {k: np.full((T, G), np.nan, dtype=np.float32) for k in ("shrunk", "raw", "se")}
        for k in out:
            out[k][:, pos[ok]] = getattr(src, k)[:, ok]
        return cls(name, list(src.targets), out["shrunk"], out["raw"], out["se"],
                   np.asarray(src.n_cells), dict(src.meta))

    def index(self) -> dict[str, int]:
        return {t: i for i, t in enumerate(self.targets)}

    def rows(self, targets) -> np.ndarray:
        """(len(targets), G) shrunk effects, NaN for a target the source lacks."""
        idx = self.index()
        out = np.full((len(targets), self.shrunk.shape[1]), np.nan, dtype=np.float32)
        for i, t in enumerate(targets):
            if t in idx:
                out[i] = self.shrunk[idx[t]]
        return out

    def common(self, targets=None) -> np.ndarray:
        """Mean shrunk response over ``targets`` (default: all of this source's targets)."""
        rows = self.shrunk if targets is None else self.rows(targets)
        n = np.isfinite(rows).sum(axis=0)
        total = np.nansum(rows, axis=0, dtype=np.float64)
        return np.divide(total, n, out=np.zeros(rows.shape[1]), where=n > 0)


def mix(tables, targets, *, weights=None, gamma: float = 0.0, reliability_scale: float = 100.0,
        common: dict | None = None):
    """Reliability-weighted mean over sources of ``shrunk - gamma * common``, per (target, gene).

    ``weights`` maps source name -> non-negative weight (default 1). Reliability is
    ``n / (n + reliability_scale)`` on the source's cells for that target. Returns
    ``(effects, weight_sum)``; where no source measured a pair the effect is 0 and the
    weight is 0, so callers can tell "predicted zero" from "not predicted".
    """
    weights = weights or {}
    G = tables[0].shrunk.shape[1]
    num = np.zeros((len(targets), G))
    den = np.zeros((len(targets), G))
    for tab in tables:
        w_s = float(weights.get(tab.name, 1.0))
        if w_s <= 0:
            continue
        m_s = (common or {}).get(tab.name)
        if m_s is None:
            m_s = tab.common()
        m_s = np.nan_to_num(np.asarray(m_s, dtype=np.float64))
        idx = tab.index()
        for i, t in enumerate(targets):
            j = idx.get(t)
            if j is None:
                continue
            row = tab.shrunk[j].astype(np.float64)
            ok = np.isfinite(row)
            rel = tab.n_cells[j] / (tab.n_cells[j] + reliability_scale)
            num[i, ok] += w_s * rel * (row[ok] - gamma * m_s[ok])
            den[i, ok] += w_s * rel
    out = np.divide(num, den, out=np.zeros_like(num), where=den > 0)
    return out, den


def topk_sign_agreement(pred: np.ndarray, truth: np.ndarray, ks, *, exclude=(), keep=None) -> dict:
    """Share of the top-|pred| genes whose predicted sign matches ``truth``, for each k.

    A gene counts only where both values are finite and non-zero, like the scorer's
    direction members, which judge a called gene only where the real fold change is
    defined and not null. ``exclude`` drops columns (the target gene itself); ``keep``
    is an optional boolean mask applied first (for example a consensus of sources).
    Returns ``{k: (agree, n)}``; n is below k when fewer genes qualify.
    """
    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth, dtype=np.float64)
    ok = np.isfinite(pred) & np.isfinite(truth) & (pred != 0) & (truth != 0)
    if keep is not None:
        ok &= np.asarray(keep, dtype=bool)
    ok[list(exclude)] = False
    idx = np.flatnonzero(ok)
    order = idx[np.argsort(-np.abs(pred[idx]), kind="stable")]
    same = np.sign(pred[order]) == np.sign(truth[order])
    return {k: (int(same[:k].sum()), int(min(k, same.size))) for k in ks}


def shared_signal(a: AxisTable, b: AxisTable, targets, *, exclude_cols=(), gamma: float = 0.0) -> dict:
    """Method-of-moments split of two sources into a shared part and their own parts.

    Model, per (target, gene): ``a = s + e_a``, ``b = s + e_b`` with ``e_a``, ``e_b`` and ``s``
    uncorrelated. Then ``E[ab] = V_s``, ``E[a^2] = V_s + V_a``, ``E[b^2] = V_s + V_b``. For a new
    context ``x = s + e_x`` equally unrelated to both, the best linear predictor from ``a`` and
    ``b`` is ``amp * (w a + (1 - w) b)`` with ``w = V_b / (V_a + V_b)`` and
    ``amp = V_s / (V_s + w^2 V_a + (1 - w)^2 V_b)``. That is an ASSUMPTION about the new
    context, stated here so it can be checked against the leaderboard, not a measurement.
    """
    targets = [t for t in targets if t in a.index() and t in b.index()]
    A = a.rows(targets).astype(np.float64)
    B = b.rows(targets).astype(np.float64)
    if gamma:
        A = A - gamma * a.common()
        B = B - gamma * b.common()
    ok = np.isfinite(A) & np.isfinite(B)
    if len(exclude_cols):
        ok[:, np.asarray(list(exclude_cols), dtype=int)] = False
    n = int(ok.sum())
    saa, sbb, sab = (float((X * Y)[ok].mean()) for X, Y in ((A, A), (B, B), (A, B)))
    v_s = max(sab, 0.0)
    v_a, v_b = max(saa - v_s, 1e-12), max(sbb - v_s, 1e-12)
    w = v_b / (v_a + v_b)
    amp = v_s / (v_s + w**2 * v_a + (1 - w) ** 2 * v_b) if v_s > 0 else 0.0
    return {"targets": len(targets), "pairs": n, "gamma": gamma, "E_aa": saa, "E_bb": sbb, "E_ab": sab,
            "corr": sab / np.sqrt(saa * sbb) if saa > 0 and sbb > 0 else None,
            "weight_a": w, "weight_b": 1 - w, "amplitude": amp,
            "single_source_amplitude": {"a": v_s / saa if saa > 0 else 0.0, "b": v_s / sbb if sbb > 0 else 0.0}}


def _purity_depth(pred_sign, obs_sign, floor: float = 0.9) -> int:
    """Deepest prefix whose sign agreement is >= floor (the raw reach rule of the scorer)."""
    if pred_sign.size == 0:
        return 0
    agree = np.cumsum(pred_sign == obs_sign)
    depth = np.arange(1, pred_sign.size + 1)
    ok = np.flatnonzero(agree / depth >= floor)
    return int(ok[-1] + 1) if ok.size else 0


def transfer_report(pred: np.ndarray, pred_weight: np.ndarray, truth: AxisTable, targets, *,
                    exclude_cols=(), z_conf: float = 3.0, heads=(10, 50)) -> dict:
    """Effect-space proxies of how well ``pred`` (T x G, ln) anticipates ``truth``.

    Scored genes per target: predicted (weight > 0) and measured by the truth source, the
    columns in ``exclude_cols`` (the panel's own target genes) removed. "Confident" truth
    genes are those with |raw / se| >= ``z_conf``, the stand-in for reference-significant.
    """
    tidx = truth.index()
    # compare only targets both sides carry: one target the predictor lacks would otherwise
    # empty the shared gene set and pin the discrimination proxy at 0.5
    keep = [i for i, t in enumerate(targets) if t in tidx and (pred_weight[i] > 0).any()]
    P = pred[keep].astype(np.float64)
    W = pred_weight[keep]
    rows = np.array([tidx[targets[i]] for i in keep])
    O = truth.shrunk[rows].astype(np.float64)
    Z = (truth.raw[rows] / truth.se[rows]).astype(np.float64)
    valid = (W > 0) & np.isfinite(O) & np.isfinite(Z)
    if len(exclude_cols):
        valid[:, np.asarray(list(exclude_cols), dtype=int)] = False
    cols = valid.all(axis=0)                       # genes usable for every compared target
    per = {"pearson": [], "pearson_centred": [], "reach_proxy": [], "n_conf": []}
    per.update({f"purity_top{h}": [] for h in heads})
    Pc = P - np.nanmean(np.where(valid, P, np.nan), axis=0)
    Oc = O - np.nanmean(np.where(valid, O, np.nan), axis=0)
    for i in range(len(keep)):
        v = valid[i]
        if v.sum() < 20:
            continue
        p, o, z = P[i, v], O[i, v], Z[i, v]
        per["pearson"].append(float(np.corrcoef(p, o)[0, 1]) if p.std() > 0 and o.std() > 0 else np.nan)
        pc, oc = Pc[i, v], Oc[i, v]
        per["pearson_centred"].append(float(np.corrcoef(pc, oc)[0, 1]) if pc.std() > 0 and oc.std() > 0 else np.nan)
        conf = np.abs(z) >= z_conf
        per["n_conf"].append(int(conf.sum()))
        if conf.sum() == 0:
            continue
        order = np.argsort(-np.abs(p[conf]), kind="stable")
        ps, os_ = np.sign(p[conf][order]), np.sign(o[conf][order])
        for h in heads:
            k = min(h, ps.size)
            per[f"purity_top{h}"].append(float(np.mean(ps[:k] == os_[:k])))
        per["reach_proxy"].append(_purity_depth(ps, os_) / conf.sum())
    # discrimination: cosine of each prediction with every target's truth, on shared genes
    A, B = np.where(cols, P, 0.0), np.where(cols, O, 0.0)
    na, nb = np.linalg.norm(A, axis=1), np.linalg.norm(B, axis=1)
    cos = (A @ B.T) / np.maximum(np.outer(na, nb), 1e-12)
    n = cos.shape[0]
    ranks = np.array([(cos[i] > cos[i, i]).sum() + 0.5 * ((cos[i] == cos[i, i]).sum() - 1) for i in range(n)])
    pds_proxy = 1.0 - ranks / max(n - 1, 1)
    # squared error at the best single amplitude, ratio of sums as the official MSE
    pv, ov = np.where(valid, P, 0.0), np.where(valid, O, 0.0)
    a_star = float((pv * ov).sum() / max((pv * pv).sum(), 1e-12))
    skill = 1.0 - float(((ov - a_star * pv) ** 2).sum() / max((ov * ov).sum(), 1e-12))
    med = {k: (float(np.nanmedian(v)) if len(v) else None) for k, v in per.items()}
    return {"targets": len(keep), "genes_shared_by_all": int(cols.sum()),
            "median": med, "pds_proxy_mean": float(pds_proxy.mean()) if n else None,
            "amplitude_star": a_star, "skill_at_amplitude_star": skill}
