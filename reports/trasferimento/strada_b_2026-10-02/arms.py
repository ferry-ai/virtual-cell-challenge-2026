"""Route B arms (PROTOCOLLO.md in this folder): three one-factor changes to the t22 form of the transfer.

All three act on one context's transferred effects BEFORE the cis head, and keep the context's total energy, so a
difference against the reference is a difference of direction or allocation, never of global amplitude:

* ``alloc``    -- per-target amplitude from cross-source agreement and magnitude,
                  f_t = clip((A_t / med A)^ALPHA * (m_t / med m)^-BETA, LOW, HIGH), energy kept;
* ``normrest`` -- per-target norm restoration, r_t = median_k ||S_k,t|| / ||M_t||, clipped, energy kept;
* ``cis50``    -- the CRISPRi cis prior extended from 5 kb to 50 kb (`CIS_EDGES`, `cis_scale`; bins from
                  `vcc2026.predictor_sc.CisModel.from_pairs`), added after the amplitude.

Inputs are arrays on one gene axis: per-source effects ``S`` of shape (K, T, G) with NaN where a source did not
measure a (target, gene) pair, the pooled transfer ``M`` (T, G) as stage 100 builds it, and a boolean ``genes`` mask
(G,) of the genes the agreement and norms are read on (expressed in the context). Units are stage 100's (ln).
"""
from __future__ import annotations

import numpy as np

# Registered in PROTOCOLLO.md before any measurement; not tuned afterwards.
ALPHA, BETA, LOW, HIGH, EPS = 1.0, 0.875, 1.0 / 3.0, 3.0, 1e-3
CIS_EDGES = (0, 1000, 2000, 5000, 10000, 20000, 30000, 50000)
CIS_SCALE_NEAR, CIS_SCALE_FAR, CIS_NEAR_BP = 2.0, 1.0, 5000


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na > 0 and nb > 0 else np.nan


def agreement(S: np.ndarray, genes: np.ndarray, min_genes: int = 20) -> np.ndarray:
    """(T,) mean pairwise cosine between the sources that measured a target, on ``genes`` both measured.

    NaN where fewer than two sources reach ``min_genes`` shared genes: no agreement can be read there.
    """
    K, T, _ = S.shape
    out = np.full(T, np.nan)
    for t in range(T):
        vals = []
        for k in range(K):
            for j in range(k + 1, K):
                both = genes & np.isfinite(S[k, t]) & np.isfinite(S[j, t])
                if both.sum() >= min_genes:
                    c = _cos(S[k, t, both], S[j, t, both])
                    if np.isfinite(c):
                        vals.append(c)
        if vals:
            out[t] = float(np.mean(vals))
    return out


def keep_energy(M: np.ndarray, f: np.ndarray, genes: np.ndarray) -> np.ndarray:
    """Factors ``f`` rescaled by one constant so that sum_t ||f_t M_t||^2 equals sum_t ||M_t||^2 on ``genes``."""
    e = (M[:, genes] ** 2).sum(axis=1)
    moved = float((f ** 2 * e).sum())
    return f * np.sqrt(float(e.sum()) / moved) if moved > 0 else f


def alloc_factors(S: np.ndarray, M: np.ndarray, genes: np.ndarray) -> tuple[np.ndarray, dict]:
    """Per-target factors of the ``alloc`` arm; a target without a readable agreement gets the median agreement."""
    A = agreement(S, genes)
    readable = np.isfinite(A)
    med_a = float(np.median(np.maximum(A[readable], 0.0))) if readable.any() else 0.0
    a = np.where(readable, np.maximum(A, 0.0), med_a)
    m = np.linalg.norm(M[:, genes], axis=1)
    med_m = float(np.median(m[m > 0])) if (m > 0).any() else 1.0
    f = ((a + EPS) / (med_a + EPS)) ** ALPHA * (np.maximum(m, 1e-12) / med_m) ** (-BETA)
    f = np.clip(f, LOW, HIGH)
    f = np.where(m > 0, f, 1.0)
    f = keep_energy(M, f, genes)
    return f, {"agreement_readable": int(readable.sum()), "agreement_median": med_a,
               "factor_quantiles": np.quantile(f, [0.1, 0.5, 0.9]).tolist()}


def normrest_factors(S: np.ndarray, M: np.ndarray, genes: np.ndarray) -> tuple[np.ndarray, dict]:
    """Per-target factors of the ``normrest`` arm: the median single-source norm over the pooled norm, clipped."""
    K, T, _ = S.shape
    r = np.ones(T)
    for t in range(T):
        norms = [np.linalg.norm(S[k, t, genes & np.isfinite(S[k, t])]) for k in range(K)
                 if (genes & np.isfinite(S[k, t])).any()]
        pooled = np.linalg.norm(M[t, genes])
        if len(norms) >= 2 and pooled > 0:
            r[t] = float(np.median(norms)) / pooled
    r = np.clip(r, LOW, HIGH)
    f = keep_energy(M, r, genes)
    return f, {"factor_quantiles": np.quantile(f, [0.1, 0.5, 0.9]).tolist()}


def cis_scale(dist: np.ndarray) -> np.ndarray:
    """The registered dose: x2 within 5 kb (production), x1 from 5 to 50 kb."""
    return np.where(np.asarray(dist) < CIS_NEAR_BP, CIS_SCALE_NEAR, CIS_SCALE_FAR)
