"""C-regime fits and predictions of one held-out line group: the single implementation used by p3_run.py,
six_member_hepg2.py and the export.

Inner model selection of M2 (version 2, 2/10 18:00): for each inner validation group v, the gene basis, the
out-of-fold transfers of the inner training rows and the basal PCA are all rebuilt WITHOUT v; v's rows are
then projected on that basis with their own out-of-fold transfer (sources: the outer training groups minus
v). Version 1 (commit e60767c, run p3_c_r1 stopped before any reading) reused the outer basis and transfers
that contained v: an optimistic inner tuning, flagged by an external review. Every inner fold records which
groups fed its basis and transfers (``inner_audit``), and the code asserts that v is never among them.
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np

from arms import (AMPLITUDE_T25, BasalPCA, Cube, LinearGain, LowRankBilinear, combine_groups, derangement,
                  fit_keys, gain_features, gene_weight, generic_vector, group_mean, reference_basal)
from splits import Split, assert_no_leak

F32 = np.float32


class GMCache:
    """Group means of fit keys, keyed by (source group, fit group): independent of the held-out group in C."""

    def __init__(self, cube: Cube, commons: dict, folder: Path):
        self.cube, self.commons, self.folder = cube, commons, Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def get(self, src: str, keys: list[str], tag: str, held: str) -> np.ndarray:
        if src == held:
            raise AssertionError(f'group mean of the held-out group {held} requested')
        path = self.folder / f'{src}__{tag}.npy'
        if path.exists():
            return np.load(path).astype(F32)
        gm = group_mean(self.cube, src, keys, self.commons)
        np.save(path, gm.astype(np.float16))
        return np.load(path).astype(F32)      # always the stored (float16) values: order-independent


class ReadOnlyGMCache(GMCache):
    """The group means a finished run cached; never writes into the run's folder."""

    def get(self, src, keys, tag, held):
        if src == held:
            raise AssertionError(f'group mean of the held-out group {held} requested')
        path = self.folder / f'{src}__{tag}.npy'
        if not path.exists():
            raise FileNotFoundError(f'{path}: not cached by the run; refusing to write into its folder')
        return np.load(path).astype(F32)


def transfer_for(cube: Cube, keys: list[str], groups: list[str], commons: dict) -> tuple[np.ndarray, np.ndarray]:
    return combine_groups([group_mean(cube, h, keys, commons) for h in groups])


def basis(rows: np.ndarray, k: int, max_rows: int = 2000) -> np.ndarray:
    """Top-k orthonormal gene directions of the training transfers (rows), via the row Gram matrix."""
    X = np.nan_to_num(rows, nan=0.0).astype(np.float64)
    if len(X) > max_rows:
        X = X[np.linspace(0, len(X) - 1, max_rows).astype(int)]
    X = X - X.mean(0, keepdims=True)
    vals, vecs = np.linalg.eigh(X @ X.T)
    top = np.argsort(vals)[::-1][:k]
    top = top[vals[top] > vals.max() * 1e-9]
    V = (X.T @ vecs[:, top]) / np.sqrt(vals[top])[None, :]
    return V.astype(F32)


def oof_transfer(gm: GMCache, keys: list[str], fit_group: str, sources: list[str], held: str):
    if fit_group in sources or held in sources:
        raise AssertionError(f'transfer of {fit_group} rows would use {fit_group} or the held group {held}')
    s, support = combine_groups([gm.get(x, keys, f'fit_{fit_group}', held) for x in sources])
    return s, support


def projections(cube: Cube, groups: list[str], fit_s: dict, U: np.ndarray) -> list[dict]:
    """z = U^T s and r = U^T (y - s) for every training table row of ``groups``."""
    out = []
    for h in groups:
        keys, s = fit_s[h]['keys'], fit_s[h]['s'] * AMPLITUDE_T25
        for t in cube.tables_of(h):
            y, have = cube.get(t, 'raw', keys)
            if not have.any():
                continue
            yy, ss = y[have], s[have]
            s0 = np.nan_to_num(ss, nan=0.0)
            resid = np.nan_to_num(yy - np.where(np.isfinite(ss), ss, 0.0), nan=0.0)
            out.append(dict(group=h, table=t, z=s0 @ U, r=resid @ U))
    return out


def m2_fit(cube: Cube, proj: list[dict], U: np.ndarray, k: int, d: int, ridge: float, pca: BasalPCA,
           phi_override: dict | None = None) -> LowRankBilinear:
    model = LowRankBilinear(U[:, :k], d, ridge)
    for pr in proj:
        table = (phi_override or {}).get(pr['table'], pr['table'])
        phi = pca.coords(cube.basal[table])[:d] if d else np.zeros(0, F32)
        model.add(pr['r'][:, :k], pr['z'][:, :k], phi)
    model.solve()
    return model


def m2_gain(cube: Cube, model: LowRankBilinear, pr: dict, k: int, d: int, pca: BasalPCA) -> float:
    """Full-gene squared-error reduction on one table's rows: 2 c.r - |c|^2 with c the projected correction."""
    phi = pca.coords(cube.basal[pr['table']])[:d] if d else np.zeros(0, F32)
    corr = model._u(pr['z'][:, :k], phi) @ model.theta
    return float((2 * (corr * pr['r'][:, :k]).sum(1) - (corr ** 2).sum(1)).sum())


def fit_c(cube: Cube, g: str, P: dict, commons: dict, raw_means: dict, gm: GMCache) -> dict:
    split = Split('C', g, None, P['n_folds'])
    train_groups = [h for h in cube.groups if h != g]
    assert_no_leak(cube.training_rows(split), split, 'every arm (shared training rows)')
    kmax = max(P['m2_k_grid'])
    # ---- outer training rows: out-of-fold transfers (sources: training groups other than the row's own)
    fitdata = {}
    for h in train_groups:
        K = fit_keys(cube, h, split, P['n_fit'])
        s, support = oof_transfer(gm, K, h, [x for x in train_groups if x != h], g)
        keep = support > 0
        # all_keys is the list the group-mean cache is keyed by; keys/s keep the supported rows
        fitdata[h] = dict(all_keys=K, keys=[k for k, kk in zip(K, keep) if kk], s=s[keep])
    U = basis(np.vstack([fd['s'] for fd in fitdata.values()]) * AMPLITUDE_T25, kmax)
    # ---- M1 (gains) with its context-free twin and five permutation nulls
    m1 = LinearGain(True, P['m1_ridge'])
    tm0 = LinearGain(False, P['m1_ridge'])
    order = sorted(train_groups)
    perms = [{order[i]: order[(i + r) % len(order)] for i in range(len(order))} for r in range(1, len(order))]
    nulls = [LinearGain(True, P['m1_ridge']) for _ in perms]
    for h in train_groups:
        fd = fitdata[h]
        m_h = generic_vector(cube, raw_means, {g, h})
        xref = reference_basal(cube, {g, h})
        s = fd['s'] * AMPLITUDE_T25
        for t in cube.tables_of(h):
            y, have = cube.get(t, 'raw', fd['keys'])
            if not have.any():
                continue
            yy, ss = y[have], s[have]
            w = gene_weight(cube.basal[t])
            m1.add(yy, ss, m_h, gain_features(cube.basal[t], xref, context=True), w)
            tm0.add(yy, ss, m_h, gain_features(cube.basal[t], xref, context=False), w)
            for nl, shift in zip(nulls, perms):
                tp = cube.tables_of(shift[h])[0]
                nl.add(yy, ss, m_h, gain_features(cube.basal[tp], xref, context=True), w)
    for mdl in [m1, tm0] + nulls:
        mdl.solve()
    # ---- M2: inner leave-one-group-out selection, everything rebuilt without the validation group
    grid = list(itertools.product(P['m2_k_grid'], P['m2_d_grid'], P['m2_ridge_grid']))
    inner = {cfg: 0.0 for cfg in grid}
    inner_audit = {}
    for v in train_groups:
        F = [x for x in train_groups if x != v]
        fit_s = {}
        for h in F:
            sources = [x for x in F if x != h]
            K = fitdata[h]['all_keys']
            s, support = oof_transfer(gm, K, h, sources, g)
            if v in sources:
                raise AssertionError('inner transfer uses the validation group')
            keep = support > 0
            fit_s[h] = dict(keys=[k for k, kk in zip(K, keep) if kk], s=s[keep])
        U_v = basis(np.vstack([fs['s'] for fs in fit_s.values()]) * AMPLITUDE_T25, kmax)
        proj_in = projections(cube, F, fit_s, U_v)
        del fit_s
        proj_val = projections(cube, [v], {v: fitdata[v]}, U_v)   # v's transfer: sources = train_groups - v
        pcas = {d: BasalPCA(cube, F, max(d, 1)) for d in P['m2_d_grid']}
        for (k, d, ridge) in grid:
            mdl = m2_fit(cube, proj_in, U_v, k, d, ridge, pcas[d])
            inner[(k, d, ridge)] += sum(m2_gain(cube, mdl, pr, k, d, pcas[d]) for pr in proj_val)
        inner_audit[v] = dict(basis_and_pca_groups=F, transfer_sources={h: [x for x in F if x != h] for h in F},
                              validation_transfer_sources=[x for x in train_groups if x != v])
    k, d, ridge = max(grid, key=lambda c: inner[c])
    proj = projections(cube, train_groups, fitdata, U)
    pca = BasalPCA(cube, train_groups, max(d, 1))
    m2 = m2_fit(cube, proj, U, k, d, ridge, pca)
    m2_0 = m2_fit(cube, proj, U, k, 0, ridge, pca)
    m2_nulls = []
    for shift in perms:
        override = {t: cube.tables_of(shift[cube.group[t]])[0] for t in cube.tables if cube.group[t] in shift}
        m2_nulls.append(m2_fit(cube, proj, U, k, d, ridge, pca, override))
    return dict(g=g, train_groups=train_groups, m1=m1, tm0=tm0, nulls=nulls, m2=m2, m2_0=m2_0, m2_nulls=m2_nulls,
                k=k, d=d, ridge=ridge, pca=pca, perms=perms, inner=inner, inner_audit=inner_audit,
                fit_keys={h: len(fd['keys']) for h, fd in fitdata.items()},
                m_g=generic_vector(cube, raw_means, {g}), xref_g=reference_basal(cube, {g}))


def predict_c(cube: Cube, fitted: dict, e: str, bkeys: list[str], commons: dict, swap_group: str) -> dict | None:
    """Every C arm for one block of keys of held-out table ``e`` (keys without any training support dropped)."""
    s, support = transfer_for(cube, bkeys, fitted['train_groups'], commons)
    keep = support > 0
    if not keep.any():
        return None
    bkeys = [kk for kk, kp in zip(bkeys, keep) if kp]
    s = s[keep] * AMPLITUDE_T25
    d, pca, m_g, xref_g = fitted['d'], fitted['pca'], fitted['m_g'], fitted['xref_g']
    swap_table = cube.tables_of(swap_group)[0]
    f_true = gain_features(cube.basal[e], xref_g, context=True)
    f_cf = gain_features(cube.basal[e], xref_g, context=False)
    f_swap = gain_features(cube.basal[swap_table], xref_g, context=True)
    perm = derangement(bkeys, f'tperm:{e}')
    s_perm = s[[bkeys.index(perm[kk]) for kk in bkeys]]
    phi_true = pca.coords(cube.basal[e])[:d] if d else np.zeros(0, F32)
    phi_swap = pca.coords(cube.basal[swap_table])[:d] if d else np.zeros(0, F32)
    arms = {
        'null': np.zeros_like(s),
        'generic': np.broadcast_to(m_g, s.shape).copy(),
        'transfer': np.nan_to_num(s, nan=0.0),
        'tm0': fitted['tm0'].predict(s, m_g, f_cf),
        'm1': fitted['m1'].predict(s, m_g, f_true),
        'm1_swap': fitted['m1'].predict(s, m_g, f_swap),
        'm1_tperm': fitted['m1'].predict(s_perm, m_g, f_true),
        'm2_0': np.nan_to_num(fitted['m2_0'].predict(s, np.zeros(0, F32)), nan=0.0),
        'm2': np.nan_to_num(fitted['m2'].predict(s, phi_true), nan=0.0),
        'm2_swap': np.nan_to_num(fitted['m2'].predict(s, phi_swap), nan=0.0),
    }
    for i, nl in enumerate(fitted['nulls']):
        arms[f'm1_null{i + 1}'] = nl.predict(s, m_g, f_true)
    for i, nl in enumerate(fitted['m2_nulls']):
        arms[f'm2_null{i + 1}'] = np.nan_to_num(nl.predict(s, phi_true), nan=0.0)
    return dict(keys=bkeys, support=support[keep], arms=arms, s_finite=np.isfinite(s))
