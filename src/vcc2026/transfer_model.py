"""A learned magnitude channel for transferred knockdown effects (stage 104).

The transferred effect of a target (the same target measured in other contexts, pooled) carries
its specific direction; what a model learns well from many targets is which genes actually move
in a given context. This module builds per-(target, gene) features from the sources and the
context's basal expression, fits a gradient-boosting regressor on the target-specific part of
held-out public sources (labels centred per gene over targets), and reweights a transferred
effect by the predicted magnitude profile:

    reweighted = effect x (|m| / mean_genes |m|) ^ a

then rescales it so that the median number of detectable genes per target (4 / sqrt(400 mu),
mu the context's expected UMI per cell at 20,000 per cell, at >= 5 CPM) matches the input. Parts
that carry their own calibration (the cis head, each target's own gene) can be left out of the
reweighting and of the scale (``keep``, ``offset``). A bench centres the sources on its training
targets only (``pair_features(centre_on=...)``) and validates early stopping on whole targets
(``fit_magnitude_model(groups=...)``). Evidence: reports/trasferimento_appreso_2026-09-26/ (r2-r5).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .multisource import AxisTable, mix

__all__ = ["FEATURES", "percentile", "mixture_se", "gene_priors", "pair_features", "training_rows", "fit_magnitude_model",
           "predict_magnitude", "reweight", "own_gene_mask", "match_detectable", "detectable_threshold"]

FEATURES = ["m_raw", "m_shr", "n_src", "sign_agree", "spread", "max_absz", "mean_z", "cis", "own_gene",
            "assoc", "expr_ctx", "expr_src", "expr_diff", "target_expr", "gene_resp", "gene_common",
            "gene_spread", "panel_gene", "target_strength"]


def percentile(cpm: np.ndarray) -> np.ndarray:
    """Percentile of log1p CPM among the genes a context measured; NaN where it did not."""
    cpm = np.asarray(cpm, dtype=np.float64)
    out = np.full(cpm.shape, np.nan)
    ok = np.isfinite(cpm)
    out[ok] = pd.Series(np.log1p(cpm[ok])).rank(pct=True).to_numpy()
    return out


def mixture_se(parts: list[AxisTable], targets: list[str], n_genes: int, reliability_scale: float = 100.0) -> np.ndarray:
    """SE of `mix`'s reliability-weighted mean of ``parts`` (gamma 0): sqrt(sum (r se)^2) / sum r,
    r = n / (n + reliability_scale), independence assumed. NaN where no part measured the pair."""
    num = np.zeros((len(targets), n_genes))
    den = np.zeros((len(targets), n_genes))
    for tab in parts:
        ix = tab.index()
        for i, t in enumerate(targets):
            if t in ix:
                j = ix[t]
                r = tab.n_cells[j] / (tab.n_cells[j] + reliability_scale)
                ok = np.isfinite(tab.raw[j]) & np.isfinite(tab.se[j])
                num[i, ok] += (r * tab.se[j][ok].astype(np.float64)) ** 2
                den[i, ok] += r
    return np.where(den > 0, np.sqrt(num) / np.maximum(den, 1e-12), np.nan).astype(np.float32)


def gene_priors(universe_chunks: list[dict], exclude: set, n_genes: int) -> dict:
    """Per-gene responsiveness (share of targets moving it at |z| >= 3), mean response and spread
    over a universe of targets, ``exclude`` left out. Each chunk: {"targets", "raw", "se", "shrunk"}."""
    s1, s2, hits, n = (np.zeros(n_genes) for _ in range(4))
    for z in universe_chunks:
        keep = ~np.isin(np.asarray(z["targets"]).astype(str), list(exclude))
        eff = np.asarray(z["shrunk"], dtype=np.float64)[keep]
        zz = np.asarray(z["raw"], dtype=np.float64)[keep] / np.asarray(z["se"], dtype=np.float64)[keep]
        ok = np.isfinite(eff)
        s1 += np.where(ok, eff, 0).sum(axis=0)
        s2 += np.where(ok, eff ** 2, 0).sum(axis=0)
        hits += (np.abs(np.nan_to_num(zz)) >= 3).sum(axis=0)
        n += ok.sum(axis=0)
    with np.errstate(all="ignore"):
        mean = np.where(n > 0, s1 / n, np.nan)
        var = np.where(n > 0, s2 / n, np.nan) - mean ** 2
        return {"gene_resp": np.where(n > 0, hits / n, np.nan), "gene_common": mean,
                "gene_spread": np.sqrt(np.maximum(var, 0))}


def pair_features(raw_tables: list[AxisTable], shrunk_tables: list[AxisTable], ses: list[np.ndarray],
                  targets: list[str], col: dict, context_cpm: np.ndarray, source_cpms: list[np.ndarray],
                  priors: dict, cis: np.ndarray, assoc: np.ndarray, panel_cols: np.ndarray,
                  centre_on: list[str] | None = None) -> dict:
    """Features (targets x genes) of FEATURES for one context. ``ses[k]`` is the SE of
    ``raw_tables[k]`` on ``targets`` (NaN where unknown); pooled effects use gamma 1, as the recipe.
    Each source's common response is its mean over ``centre_on`` (default: all its targets); a
    bench passes its training targets, so that no held-out target moves a training feature."""
    T, G = len(targets), raw_tables[0].raw.shape[1]
    names = {tab.name: 1.0 for tab in raw_tables}
    common = {tab.name: tab.common(centre_on) for tab in shrunk_tables}
    m_raw, d_raw = mix(raw_tables, targets, weights=names, gamma=1.0, reliability_scale=100.0,
                       common={tab.name: tab.common(centre_on) for tab in raw_tables})
    m_shr, _ = mix(shrunk_tables, targets, weights=names, gamma=1.0, reliability_scale=100.0, common=common)
    F = {"m_raw": np.where(d_raw > 0, m_raw, np.nan).astype(np.float32),
         "m_shr": np.where(d_raw > 0, m_shr, np.nan).astype(np.float32)}
    vals, zs, strength = [], [], []
    for tab, se in zip(raw_tables, ses):
        rows = tab.rows(targets).astype(np.float32)
        vals.append(rows - tab.common(centre_on).astype(np.float32))
        z = rows / se
        zs.append(z)
        has = np.isfinite(z).any(axis=1)
        strength.append(np.where(has, (np.abs(np.nan_to_num(z)) >= 3).sum(axis=1), np.nan))
    V, Z = np.stack(vals), np.stack(zs)
    fin = np.isfinite(V)
    F["n_src"] = fin.sum(axis=0).astype(np.float32)
    sgn = np.where(fin, np.sign(V), 0).sum(axis=0)
    with np.errstate(all="ignore"):
        F["sign_agree"] = np.where(F["n_src"] > 0, np.abs(sgn) / F["n_src"], np.nan).astype(np.float32)
        F["spread"] = np.nanstd(np.where(fin, V, np.nan), axis=0).astype(np.float32)
        F["max_absz"] = np.nanmax(np.abs(Z), axis=0).astype(np.float32)
        F["mean_z"] = np.nanmean(Z, axis=0).astype(np.float32)
        target_strength = np.nanmedian(np.vstack(strength), axis=0).astype(np.float32)
        src = np.nanmean(np.vstack([percentile(c) for c in source_cpms]), axis=0)
    F["cis"] = cis.astype(np.float32)
    own = np.zeros((T, G), dtype=np.float32)
    for i, t in enumerate(targets):
        if t in col:
            own[i, col[t]] = 1
    F["own_gene"] = own
    F["assoc"] = assoc.astype(np.float32)
    ctx = percentile(context_cpm)
    F["expr_ctx"] = np.broadcast_to(ctx.astype(np.float32), (T, G))
    F["expr_src"] = np.broadcast_to(src.astype(np.float32), (T, G))
    F["expr_diff"] = F["expr_ctx"] - F["expr_src"]
    texpr = np.array([ctx[col[t]] if t in col else np.nan for t in targets], dtype=np.float32)
    F["target_expr"] = np.broadcast_to(texpr[:, None], (T, G))
    for k in ("gene_resp", "gene_common", "gene_spread"):
        F[k] = np.broadcast_to(np.asarray(priors[k], dtype=np.float32), (T, G))
    pg = np.zeros(G, dtype=np.float32)
    pg[panel_cols] = 1
    F["panel_gene"] = np.broadcast_to(pg, (T, G))
    F["target_strength"] = np.broadcast_to(target_strength[:, None], (T, G))
    return F


def _flat(F: dict, rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    return np.column_stack([F[k][rows, cols] for k in FEATURES]).astype(np.float32)


def training_rows(F: dict, y: np.ndarray, w: np.ndarray, genes_per_target: int, rng, with_rows: bool = False) -> tuple:
    """Rows of one held-out task: features, the label centred per gene over the task's targets
    (the target-specific part), clipped at +/-4, and the gene weights; at most ``genes_per_target``
    genes per target, drawn among those with a finite label and a positive weight. With
    ``with_rows`` also the target index of each row (for validation grouped by target)."""
    with np.errstate(all="ignore"):
        yc = y - np.nanmean(y, axis=0, keepdims=True)
    Xs, ys, ws, rs = [], [], [], []
    for i in range(y.shape[0]):
        g = np.flatnonzero(np.isfinite(yc[i]) & (w > 0))
        if g.size > genes_per_target:
            g = rng.choice(g, size=genes_per_target, replace=False)
        Xs.append(_flat(F, np.full(g.size, i), g))
        ys.append(np.clip(yc[i, g], -4, 4))
        ws.append(w[g])
        rs.append(np.full(g.size, i))
    out = (np.vstack(Xs), np.concatenate(ys), np.concatenate(ws))
    return out + (np.concatenate(rs),) if with_rows else out


def fit_magnitude_model(X: np.ndarray, y: np.ndarray, w: np.ndarray, seed: int, groups: np.ndarray | None = None):
    """The regressor of the benches (reports/trasferimento_appreso_2026-09-26/lct_bench3.py).

    With ``groups`` (one label per row, e.g. task and target), early stopping is validated on a
    tenth of the groups held out whole, not on random rows: rows of one target are correlated, and
    a random split lets the validation score reward memorising targets."""
    from sklearn.ensemble import HistGradientBoostingRegressor

    kw = dict(max_iter=600, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=500, l2_regularization=1.0,
              n_iter_no_change=30, random_state=seed)
    if groups is None:
        model = HistGradientBoostingRegressor(early_stopping=True, validation_fraction=0.1, **kw)
        model.fit(X, y, sample_weight=w)
        return model
    labels = np.unique(groups)
    held = np.random.default_rng(seed).choice(labels, size=max(1, labels.size // 10), replace=False)
    val = np.isin(groups, held)
    model = HistGradientBoostingRegressor(early_stopping=True, **kw)
    model.fit(X[~val], y[~val], sample_weight=w[~val], X_val=X[val], y_val=y[val], sample_weight_val=w[val])
    return model


def predict_magnitude(model, F: dict, n_targets: int, n_genes: int, block: int = 40) -> np.ndarray:
    out = np.zeros((n_targets, n_genes), dtype=np.float32)
    for a in range(0, n_targets, block):
        part = np.arange(a, min(a + block, n_targets))
        out[part] = model.predict(_flat(F, np.repeat(part, n_genes), np.tile(np.arange(n_genes), part.size))).reshape(-1, n_genes)
    return out


def reweight(effect: np.ndarray, magnitude: np.ndarray, a: float, keep: np.ndarray | None = None) -> np.ndarray:
    """effect x (|m| / mean over genes of |m|) ^ a, per target; a target with |m| all 0 is zeroed.
    Entries where ``keep`` is true (e.g. each target's own gene) keep weight 1."""
    mag = np.abs(np.asarray(magnitude, dtype=np.float64))
    mean = mag.mean(axis=1, keepdims=True)
    ratio = np.divide(mag, mean, out=np.zeros_like(mag), where=mean > 0)
    weight = np.power(ratio, a)
    if keep is not None:
        weight = np.where(keep, 1.0, weight)
    return (np.asarray(effect, dtype=np.float64) * weight).astype(np.float32)


def own_gene_mask(targets: list[str], col: dict, n_genes: int) -> np.ndarray:
    """(targets x genes) true at each target's own gene."""
    mask = np.zeros((len(targets), n_genes), dtype=bool)
    for i, t in enumerate(targets):
        if t in col:
            mask[i, col[t]] = True
    return mask


def detectable_threshold(cpm: np.ndarray, umi_per_cell: float = 20000.0, cells: int = 400) -> np.ndarray:
    mu = np.asarray(cpm, dtype=np.float64) * umi_per_cell / 1e6
    return np.where(mu > 0, 4.0 / np.sqrt(cells * np.maximum(mu, 1e-12)), np.inf)


def match_detectable(effect: np.ndarray, reference: np.ndarray, threshold: np.ndarray, gate: np.ndarray,
                     offset: np.ndarray | None = None) -> tuple[np.ndarray, float]:
    """Scale ``effect`` so that the median count of genes with |s effect + offset| > threshold (on
    ``gate`` genes) equals ``reference``'s; returns (s effect + offset, s). ``offset`` is a part left
    outside the scale (the cis head)."""
    off = 0.0 if offset is None else np.asarray(offset, dtype=np.float32)

    def med(E):
        return float(np.median(((np.abs(E) > threshold[None, :]) & gate[None, :]).sum(axis=1)))
    target = med(reference)
    lo, hi = 1e-3, 1e4
    for _ in range(60):
        mid = np.sqrt(lo * hi)
        lo, hi = (mid, hi) if med(mid * effect + off) < target else (lo, mid)
    s = float(np.sqrt(lo * hi))
    return (effect * s + off).astype(np.float32), s
