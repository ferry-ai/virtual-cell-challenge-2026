"""Four-parameter context gates; numpy/scipy only. Run with --selftest.

Axes: C contexts, S training sources, T targets, G genes. Features are float32;
missing basal features are zero *terms*, with explicit availability masks.
Unknown rho is median-imputed before clipping (all unknown -> neutral 0.5).
Family arrays may be memory maps: fitting only converts target blocks.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import OptimizeResult, minimize
from scipy.special import expit

Array = NDArray[np.float32]
Mask = NDArray[np.bool_]


@dataclass(frozen=True)
class GateFeatures:
    """Context terms and masks; blind target terms use the source-average context."""

    dl_t: Array  # (C, T)
    soft_t: Array  # (C, T)
    dl_g: Array  # (C, G)
    logit_rho: Array  # (G,), including median-imputed entries
    dl_t_known: Mask
    soft_t_known: Mask
    dl_g_known: Mask
    rho_known: Mask  # (G,), False means imputed, not disabled
    blind_dl_t: Array  # (T,)
    blind_soft_t: Array  # (T,)


@dataclass(frozen=True)
class Family:
    """One training family, sharing aligned target/gene axes with its features."""

    y: NDArray  # (T, G), NaN labels ignored
    se: NDArray  # (T, G), finite and nonnegative on usable labels
    m: NDArray  # (T, G), NaN baseline remains undefined
    k: NDArray  # (T, G), finite
    features: GateFeatures
    context: int


def _basal(value: ArrayLike, ndim: int, name: str) -> Array:
    result = np.asarray(value, dtype=np.float32)
    if result.ndim != ndim or np.isinf(result).any():
        raise ValueError(f"{name}: expected {ndim} dimensions, finite values or NaN")
    return result


def _mean_known(values: Array, axis: int) -> Array:
    known = np.isfinite(values)
    count = known.sum(axis=axis)
    total = np.where(known, values, 0).sum(axis=axis, dtype=np.float64)
    result = np.full(count.shape, np.nan, dtype=np.float32)
    np.divide(total, count, out=result, where=count > 0, casting="unsafe")
    return result


def gate_features(
    context_l: ArrayLike,
    source_l: ArrayLike,
    target_gene: ArrayLike,
    source_measured: ArrayLike,
    rho: ArrayLike,
    *,
    l_min: float,
) -> GateFeatures:
    """Build masked gates from l[C,G], sources[S,G], indices[T], measured[S,T].

    Means exclude unknown basal values; an empty mean is unknown. soft_t only
    requires the context's own target basal value, not a known source mean.
    Blind features substitute the all-training-source gene mean for context_l;
    the target-specific source reference and context-independent rho stay fixed.
    """
    lc = _basal(context_l, 2, "context_l")
    ls = _basal(source_l, 2, "source_l")
    tg = np.asarray(target_gene)
    measured = np.asarray(source_measured)
    r = _basal(rho, 1, "rho")
    if (tg.ndim != 1 or not np.issubdtype(tg.dtype, np.integer)
            or np.any(tg < -1) or np.any(tg >= lc.shape[1])):
        raise ValueError("target_gene must be integer indices in [-1, G)")
    if (ls.shape[1] != lc.shape[1] or r.shape != (lc.shape[1],)
            or measured.shape != (ls.shape[0], tg.size)
            or measured.dtype != np.bool_ or not np.isfinite(l_min)):
        raise ValueError("inconsistent gene/source axes, boolean source_measured, or l_min")
    known_r = np.isfinite(r)
    if np.any((r[known_r] < 0) | (r[known_r] > 1)):
        raise ValueError("known rho must lie in [0, 1]")
    rhat = np.clip(np.where(known_r, r, np.median(r[known_r])
                           if known_r.any() else 0.5), 1e-3, 1 - 1e-3)
    logit = np.log(rhat) - np.log1p(-rhat)
    gene_mean = _mean_known(ls, axis=0)
    # Do not use -1 as a numpy index: absent genes remain explicitly unknown.
    own = np.full((lc.shape[0], tg.size), np.nan, dtype=np.float32)
    target_sources = np.full((ls.shape[0], tg.size), np.nan, dtype=np.float32)
    blind_own = np.full(tg.size, np.nan, dtype=np.float32)
    present = tg >= 0
    own[:, present] = lc[:, tg[present]]
    target_sources[:, present] = ls[:, tg[present]]
    target_mean = _mean_known(np.where(measured, target_sources, np.nan), axis=0)
    blind_own[present] = gene_mean[tg[present]]

    def target_terms(values: Array) -> tuple[Array, Array, Mask, Mask]:
        soft_known = np.isfinite(values)
        delta_known = soft_known & np.isfinite(target_mean)
        delta = np.where(delta_known, values - target_mean, 0).astype(np.float32)
        soft = np.where(soft_known, np.logaddexp(0, l_min - np.where(soft_known, values, 0)), 0)
        return delta, soft.astype(np.float32), delta_known, soft_known

    dt, st, dtk, stk = target_terms(own)
    bdt, bst, _, _ = target_terms(blind_own)
    dgk = np.isfinite(lc) & np.isfinite(gene_mean)
    dg = np.where(dgk, lc - gene_mean, 0).astype(np.float32)
    return GateFeatures(dt, st, dg, logit.astype(np.float32), dtk, stk,
                        dgk, known_r, bdt, bst)


def _params(params: ArrayLike) -> NDArray[np.float64]:
    p = np.asarray(params, dtype=np.float64)
    if p.shape != (4,) or not np.isfinite(p).all():
        raise ValueError("params must be four finite values: alpha1, alpha2, beta1, beta3")
    return p


def _terms(features: GateFeatures, context: int, blind: bool = False
           ) -> tuple[Array, Array, Array, Array]:
    if not isinstance(context, (int, np.integer)) or not 0 <= context < features.dl_t.shape[0]:
        raise ValueError("context index out of range")
    if blind:
        return (features.blind_dl_t, features.blind_soft_t,
                np.zeros(features.dl_g.shape[1], dtype=np.float32), features.logit_rho)
    return (features.dl_t[context], features.soft_t[context],
            features.dl_g[context], features.logit_rho)


def _signal(p: NDArray, m: Array, dt: Array, st: Array, dg: Array,
            lr: Array, A: float) -> tuple[Array, Array]:
    # Explicit float32 parameters avoid promotion of block intermediates.
    a1, a2, b1, b3 = p.astype(np.float32)
    q = expit(b1 * dg + b3 * lr)
    with np.errstate(over="ignore", invalid="ignore"):
        s = np.exp(a1 * dt - a2 * st)
        signal = (np.float32(A) * s[:, None]) * (2 * q[None, :]) * m
    return signal, q


def _check_axes(m: NDArray, k: NDArray, terms: tuple[Array, ...],
                A: float, block_size: int) -> None:
    if (m.ndim != 2 or k.shape != m.shape
            or m.shape != (terms[0].size, terms[2].size)):
        raise ValueError("m and k must have shape (T, G) matching the features")
    if (not np.isfinite(A) or not np.isfinite(np.float32(A))
            or not isinstance(block_size, (int, np.integer)) or block_size <= 0):
        raise ValueError("A must be finite float32; block_size must be a positive integer")


def predict(
    params: ArrayLike, m: NDArray, k: NDArray, features: GateFeatures,
    context: int, *, A: float, block_size: int = 64, blind: bool = False,
) -> Array:
    """Compute yhat[T,G] in float32 blocks; NaN m gives NaN output."""
    p = _params(params)
    terms = _terms(features, context, blind)
    _check_axes(m, k, terms, A, block_size)
    dt, st, dg, lr = terms
    out = np.empty(m.shape, dtype=np.float32)
    for start in range(0, m.shape[0], block_size):
        sl = slice(start, start + block_size)
        mb = np.asarray(m[sl], dtype=np.float32)
        kb = np.asarray(k[sl], dtype=np.float32)
        if np.isinf(mb).any() or not np.isfinite(kb).all():
            raise ValueError("m must be finite or NaN; k must be finite")
        signal, _ = _signal(p, mb, dt[sl], st[sl], dg, lr, A)
        out[sl] = signal + kb
    return out


def predict_blind(
    params: ArrayLike, m: NDArray, k: NDArray, features: GateFeatures,
    context: int, *, A: float, block_size: int = 64,
) -> Array:
    """Predict in the source-average context, independent of context index."""
    return predict(params, m, k, features, context, A=A,
                   block_size=block_size, blind=True)


def predict_swap(
    params: ArrayLike, m: NDArray, k: NDArray, features: GateFeatures,
    swap_context: int, *, A: float, block_size: int = 64,
) -> Array:
    """Predict using swap_context's features instead of the true context."""
    return predict(params, m, k, features, swap_context, A=A, block_size=block_size)


def _weights(f: Family, sl: slice, gw: Array, tau2: float
             ) -> tuple[Array, Array, Array, Array]:
    y, se, m, k = (np.asarray(v[sl], dtype=np.float32)
                    for v in (f.y, f.se, f.m, f.k))
    use = np.isfinite(y) & np.isfinite(m) & (gw[None, :] > 0)
    # Zero ignored operands before arithmetic, so NaN * 0 never enters a sum.
    w = np.zeros(y.shape, dtype=np.float32)
    denom = np.square(np.where(use, se, 0)) + np.float32(tau2)
    np.divide(gw[None, :], denom, out=w, where=use)
    return np.where(use, y, 0), np.where(use, m, 0), np.where(use, k, 0), w


def _objective(
    params: NDArray, families: Sequence[Family], gene_weight: Array,
    A: float, tau2: float, lam: float, block_size: int,
) -> tuple[float, NDArray[np.float64]]:
    """Return weighted SSE + ridge and its four analytic derivatives."""
    loss = float(lam * np.dot(params, params))
    grad = 2 * lam * params.astype(np.float64)
    for f in families:
        dt, st, dg, lr = _terms(f.features, f.context)
        for start in range(0, f.y.shape[0], block_size):
            sl = slice(start, start + block_size)
            y, m, k, w = _weights(f, sl, gene_weight, tau2)
            signal, q = _signal(params, m, dt[sl], st[sl], dg, lr, A)
            residual = signal + k - y
            # Reject overflowing line-search trials without clipping the model.
            if not np.isfinite(residual).all():
                return float("inf"), np.zeros(4, dtype=np.float64)
            weighted = w * residual
            loss += np.einsum("ij,ij->", weighted, residual, dtype=np.float64)
            common = 2 * weighted * signal
            row = common.sum(axis=1, dtype=np.float64)
            col = common.sum(axis=0, dtype=np.float64) * (1 - q)
            grad += np.array([row @ dt[sl], -row @ st[sl], col @ dg, col @ lr])
    if not np.isfinite(loss) or not np.isfinite(grad).all():
        return float("inf"), np.zeros(4, dtype=np.float64)
    return float(loss), grad


def fit(
    families: Sequence[Family], gene_weight: ArrayLike, *, A: float,
    tau2: float, lam: float = 0.0, initial: ArrayLike = (0., 0., 0., 0.),
    block_size: int = 64, maxiter: int = 300,
) -> OptimizeResult:
    """Fit with L-BFGS-B; result.x holds (alpha1, alpha2, beta1, beta3).

    Minimize sum gene_weight[g]/(se**2+tau2) * (yhat-y)**2 + lam*p@p.
    Usable labels have finite y and m and positive gene weight. Invalid SE on
    usable labels raises; undefined baselines and NaN labels are excluded.
    Derivatives of signal v=A*s*h*m are v*[dl_t,-soft_t,(1-q)*dl_g,
    (1-q)*logit_rho], q=sigmoid(...). Accumulations are float64; block arrays
    are float32. No T*G*4 design matrix or full-family weights are allocated.
    Check result.success/message before using result.x on real data.
    """
    p = _params(initial)
    gw = np.asarray(gene_weight, dtype=np.float32)
    if (not families or gw.ndim != 1 or not np.isfinite(gw).all()
            or np.any(gw < 0) or not np.isfinite(tau2) or tau2 < 0
            or not np.isfinite(np.float32(tau2))
            or not np.isfinite(lam) or lam < 0):
        raise ValueError("need families, finite nonnegative gene_weight, tau2 and lam")
    usable = 0
    for f in families:
        _check_axes(f.m, f.k, _terms(f.features, f.context), A, block_size)
        if f.y.shape != f.m.shape or f.se.shape != f.m.shape or gw.size != f.m.shape[1]:
            raise ValueError("y, se, m, k must be (T,G); gene_weight must be (G,)")
        for start in range(0, f.y.shape[0], block_size):
            sl = slice(start, start + block_size)
            y, se, m, k = (np.asarray(v[sl], dtype=np.float32)
                            for v in (f.y, f.se, f.m, f.k))
            if np.isinf(y).any() or np.isinf(m).any() or not np.isfinite(k).all():
                raise ValueError("y/m may contain NaN but not inf; k must be finite")
            use = np.isfinite(y) & np.isfinite(m) & (gw[None, :] > 0)
            den = se[use] ** 2 + np.float32(tau2)
            if (not np.isfinite(se[use]).all() or np.any(se[use] < 0)
                    or not np.isfinite(den).all() or np.any(den <= 0)
                    or not np.isfinite(np.broadcast_to(gw, y.shape)[use] / den).all()):
                raise ValueError("usable labels need finite nonnegative SE and finite positive variance/weights")
            usable += np.count_nonzero(use)
    if usable == 0:
        raise ValueError("no usable positively weighted observations")
    return minimize(_objective, p, args=(families, gw, A, tau2, lam, block_size),
                    method="L-BFGS-B", jac=True,
                    options={"maxiter": maxiter, "ftol": 1e-12, "gtol": 1e-5, "maxls": 40})


def _selftest() -> None:
    """Exercise recovery, neutral gates, missingness, blindness and gradients."""
    rng = np.random.default_rng(9272026)
    C, S, T, G = 4, 5, 240, 320
    A, tau2, lam = 0.8, 0.03, 0.01
    sources = rng.uniform(0.2, 3.5, (S, G)).astype(np.float32)
    contexts = rng.uniform(0.1, 4, (C, G)).astype(np.float32)
    measured = rng.random((S, T)) > 0.25
    measured[0] = True
    tg = np.arange(T)
    tg[-1] = -1
    sources[:, 3] = np.nan
    contexts[0, 5] = np.nan
    rho = rng.uniform(0.05, 0.95, G).astype(np.float32)
    rho[7] = np.nan
    features = gate_features(contexts, sources, tg, measured, rho, l_min=1.8)
    planted = np.array([0.16, 0.22, -0.19, 0.13])
    gw = rng.uniform(0.5, 1.5, G).astype(np.float32)
    gw[8] = 0
    families = []
    for c in range(C):
        m = rng.normal(0, 0.6, (T, G)).astype(np.float32)
        k = rng.normal(0, 0.1, (T, G)).astype(np.float32)
        m[1, 2] = np.nan
        se = rng.uniform(0.05, 0.2, (T, G)).astype(np.float32)
        y = predict(planted, m, k, features, c, A=A)
        y += rng.normal(0, 0.003, y.shape).astype(np.float32)
        y[rng.random(y.shape) < 0.12] = np.nan
        y[1, 2] = 123  # A label with undefined m must also be excluded.
        families.append(Family(y, se, m, k, features, c))

    recovered = fit(families, gw, A=A, tau2=tau2, lam=lam, block_size=37)
    error = float(np.max(np.abs(recovered.x - planted)))
    # Independent feature variation and >250k labels with noise SD .003:
    # absolute tolerance .002 is conservative versus sampling/float32 errors.
    assert recovered.success and error < 0.002, (recovered.message, recovered.x)
    print(f"PASS planted recovery: max_abs_error={error:.3g} < 0.002; params={np.array2string(recovered.x, precision=6)}")

    zero_families = [Family(A * f.m + f.k, f.se, f.m, f.k, features, f.context)
                     for f in families]
    zero = fit(zero_families, gw, A=A, tau2=tau2, lam=lam,
               initial=(0.04, -0.03, 0.02, -0.02), block_size=43)
    assert zero.success and np.max(np.abs(zero.x)) < 2e-5, (zero.message, zero.x)
    for f in zero_families:
        np.testing.assert_array_equal(predict(np.zeros(4), f.m, f.k, features, f.context, A=A), f.y)
        np.testing.assert_allclose(predict(zero.x, f.m, f.k, features, f.context, A=A),
                                   f.y, atol=2e-5, rtol=2e-5)
    print(f"PASS zero parameters: fitted max_abs={np.max(np.abs(zero.x)):.3g} < 2e-5; exact zero-gate baseline")

    f = families[0]
    b0 = predict_blind(planted, f.m, f.k, features, 0, A=A)
    b1 = predict_blind(planted, f.m, f.k, features, 1, A=A)
    np.testing.assert_array_equal(b0, b1)
    average = _mean_known(sources, axis=0)[None, :]
    average_features = gate_features(average, sources, tg, measured, rho, l_min=1.8)
    np.testing.assert_array_equal(b0, predict(planted, f.m, f.k, average_features, 0, A=A))
    np.testing.assert_array_equal(predict_swap(planted, f.m, f.k, features, 1, A=A),
                                  predict(planted, f.m, f.k, features, 1, A=A))
    assert not np.allclose(predict(planted, f.m, f.k, features, 0, A=A),
                           predict(planted, f.m, f.k, features, 1, A=A), equal_nan=True)
    print("PASS blind/swap: blind contexts identical and equal source-average substitution; swap matches supplied context")

    assert features.dl_t[0, 5] == features.soft_t[0, 5] == features.dl_g[0, 5] == 0
    assert not features.dl_t_known[0, 5] and not features.soft_t_known[0, 5]
    assert not features.dl_g_known[0, 5]
    assert np.all(features.dl_t[:, -1] == 0) and np.all(features.soft_t[:, -1] == 0)
    assert np.all(features.dl_t[:, 3] == 0) and np.all(features.dl_g[:, 3] == 0)
    assert np.all(features.soft_t_known[:, 3])  # Source missingness does not erase own basal.
    assert not features.rho_known[7]
    median = np.median(rho[np.isfinite(rho)])
    np.testing.assert_allclose(features.logit_rho[7], np.log(median / (1 - median)), atol=1e-6)
    unknown = gate_features(contexts, sources, tg, measured, np.full(G, np.nan), l_min=1.8)
    assert np.all(unknown.logit_rho == 0) and not unknown.rho_known.any()
    tiny = gate_features([[0., np.nan, 2.]], [[1., 2., 3.], [3., 4., np.nan]],
                         [0, 1, 2, -1], [[True, True, False, True],
                                         [False, True, True, True]],
                         [0., 1., np.nan], l_min=1.)
    np.testing.assert_array_equal(tiny.dl_t, [[-1., 0., 0., 0.]])
    np.testing.assert_array_equal(tiny.dl_g, [[-2., 0., -1.]])
    np.testing.assert_allclose(tiny.soft_t, [[np.logaddexp(0, 1), 0., np.logaddexp(0, -1), 0.]])
    np.testing.assert_allclose(tiny.logit_rho, [-np.log(999), np.log(999), 0.], atol=2e-5)
    assert tiny.soft_t_known[0, 0] and not tiny.dl_t_known[0, 2]
    pred = predict(planted, f.m, f.k, features, 0, A=A)
    assert np.isnan(pred[1, 2])
    # An independent dense formula checks exclusion of NaN labels and baselines.
    probe = np.array([0.08, 0.12, -0.09, 0.06])
    actual, _ = _objective(probe, families, gw, A, tau2, lam, 37)
    missing_se = f.se.copy()
    missing_se[~np.isfinite(f.y) | ~np.isfinite(f.m)] = np.nan
    masked_family = Family(f.y, missing_se, f.m, f.k, features, f.context)
    np.testing.assert_array_equal(_objective(probe, [masked_family], gw, A, tau2, lam, 37)[0],
                                  _objective(probe, [f], gw, A, tau2, lam, 37)[0])
    expected = lam * (probe @ probe)
    for fam in families:
        yh = predict(probe, fam.m, fam.k, features, fam.context, A=A).astype(np.float64)
        use = np.isfinite(fam.y) & np.isfinite(fam.m) & (gw[None, :] > 0)
        w = gw[None, :] / (fam.se.astype(np.float64) ** 2 + tau2)
        expected += np.sum((w * (yh - fam.y) ** 2)[use])
    np.testing.assert_allclose(actual, expected, rtol=2e-6)
    print("PASS missingness: neutral basal terms/masks, absent targets, rho imputation, undefined m, ignored NaN labels")

    _, analytic = _objective(probe, families, gw, A, tau2, lam, 37)
    eps = 1e-3  # Float32 forward arithmetic requires a larger step than float64 sqrt(eps).
    numeric = np.empty(4)
    for j in range(4):
        step = np.eye(4)[j] * eps
        numeric[j] = (_objective(probe + step, families, gw, A, tau2, lam, 37)[0]
                      - _objective(probe - step, families, gw, A, tau2, lam, 37)[0]) / (2 * eps)
    relative = float(np.max(np.abs(analytic - numeric) / np.maximum(1, np.abs(numeric))))
    np.testing.assert_allclose(analytic, numeric, rtol=2e-3, atol=0.05)
    blocked = _objective(probe, families, gw, A, tau2, lam, T)
    np.testing.assert_allclose(blocked[0], actual, rtol=1e-12)
    np.testing.assert_allclose(blocked[1], analytic, rtol=1e-12, atol=1e-8)
    print(f"PASS analytic gradient: max_relative_error={relative:.3g} < 0.002 (central step=0.001); block-size invariant")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="run deterministic planted-parameter checks")
    args = parser.parse_args()
    if args.selftest:
        _selftest()
    else:
        parser.print_help()
