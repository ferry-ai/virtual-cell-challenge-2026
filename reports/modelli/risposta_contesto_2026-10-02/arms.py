"""Arms of the R-LEAD P3 comparison, on the bench cube (effect space, ln fold change).

Common contract: every arm is fitted from training rows that `splits.Split.row_allowed` admits
(checked by `assert_no_leak` before any fit) and predicts, for a held-out table, an effect on the
cube genes. The held-out table's controls enter only through its basal profile, as an input.

* ``null``       zero effect.
* ``generic``    trained common response: mean over training groups of each group's mean raw effect
                 over its training targets; identical for every target (no target identity).
* ``transfer``   the t25 recipe generalised to the bench: each table's shrunk effect minus gamma x
                 its common response (gamma 1), reliability n / (n + 100), averaged within a group,
                 then at equal weight over the training groups that measured the target; amplitude
                 1.576. NaN where no group measured the pair (production writes 0 there).
* ``tm0``        target model without context: transfer and generic recombined with gains that depend
                 only on gene features computed from the SOURCE controls (`gain_features` with the
                 reference profile in place of the context): same lawful descriptors, no context.
* ``m1``         conditioned model, per-gene gain: as ``tm0``, with the features of the held-out
                 table's own controls (log-expression difference to the sources, level, low-expression
                 flag): a diagonal bilinear correction  s * (beta . f(c, g)) + m * (alpha . f(c, g)).
* ``m2``         conditioned model, low-rank bilinear: s + U (W0 + sum_l phi_l(c) W_l) U^T s, with U a
                 gene basis of training transfers and phi(c) the context's coordinates on the top
                 principal axes of the training controls; ``m2_0`` keeps only W0 (no context).
* swapped        ``m1``/``m2`` with the descriptors of another group's controls (fixed derangement);
                 basal, targets and fit unchanged: only the conditioning of the effect moves.
* target-permuted ``m1`` applied to another target's shared effect (fixed derangement): specificity.

Corrections are fitted on residuals of OUT-OF-FOLD transfers: a training row of group h uses the
transfer computed without the held-out group AND without h, so no row sees its own line.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from splits import Split, unit_hash

LOG5 = float(np.log1p(5.0))      # 5 CPM, the expression gate of t26
AMPLITUDE_T25 = 1.576
F32 = np.float32


class Cube:
    """Memory-mapped bench cube written by cube.py."""

    def __init__(self, folder: Path, min_cells: float = 10):
        folder = Path(folder)
        self.folder = folder
        self.manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
        self.genes = pd.read_csv(folder / 'genes.csv')['gene'].astype(str).tolist()
        self.gpos = {g: i for i, g in enumerate(self.genes)}
        self.tables = list(self.manifest['tables'])
        self.meta = self.manifest['tables']
        self.group = {t: self.meta[t]['group'] for t in self.tables}
        self.groups = sorted(set(self.group.values()))
        self.rows, self.arr, self.index = {}, {}, {}
        for t in self.tables:
            r = pd.read_csv(folder / t / 'rows.csv')
            r['usable'] = (~r['duplicate_of_key'].astype(bool)) & (r['n_cells'] >= min_cells)
            self.rows[t] = r
            self.arr[t] = {k: np.load(folder / t / f'{k}.npy', mmap_mode='r') for k in ('raw', 'se', 'shrunk')}
            self.index[t] = {k: i for i, (k, u) in enumerate(zip(r['target_key'], r['usable'])) if u}
        with np.load(folder / 'basal.npz') as z:
            self.basal = {k: z[k].astype(F32) for k in z.files}
        self.symbol = {}
        for t in self.tables:
            for k, s in zip(self.rows[t]['target_key'], self.rows[t]['target']):
                self.symbol.setdefault(k, s)
        self.reads: set = set()

    def fit_reads_of(self, group: str) -> list[str]:
        return sorted(t for t, purpose in self.reads if purpose == 'fit' and self.group[t] == group)

    def target_gene_positions(self, keys, ensembl_to_symbol: dict) -> np.ndarray:
        """Cube column of each target's own gene: by Ensembl ID on the axis table, else by symbol; -1 if absent."""
        out = []
        for k in keys:
            sym = ensembl_to_symbol.get(k, self.symbol.get(k, ''))
            out.append(self.gpos.get(sym, self.gpos.get(self.symbol.get(k, ''), -1)))
        return np.array(out, dtype=np.int64)

    def tables_of(self, group: str) -> list[str]:
        return [t for t in self.tables if self.group[t] == group]

    def keys_of(self, table: str) -> list[str]:
        return list(self.index[table])

    def get(self, table: str, kind: str, keys, purpose: str = 'fit') -> tuple[np.ndarray, np.ndarray]:
        """Rows for ``keys`` (NaN rows where absent) and the presence mask.

        Every read is logged with its purpose ('fit' feeds a model, 'truth' scores one), so a run can
        assert afterwards that no fit read a table of the held-out group.
        """
        self.reads.add((table, purpose))
        idx = np.array([self.index[table].get(k, -1) for k in keys], dtype=np.int64)
        have = idx >= 0
        out = np.full((len(keys), len(self.genes)), np.nan, F32)
        if have.any():
            order = np.argsort(idx[have])
            src = idx[have][order]
            block = np.asarray(self.arr[table][kind][src], dtype=F32)
            dest = np.flatnonzero(have)[order]
            out[dest] = block
        return out, have

    def cells(self, table: str, keys) -> np.ndarray:
        r = self.rows[table]
        idx = np.array([self.index[table].get(k, -1) for k in keys], dtype=np.int64)
        return np.where(idx >= 0, r['n_cells'].to_numpy(float)[np.maximum(idx, 0)], 0.0)

    def training_rows(self, split: Split) -> pd.DataFrame:
        out = []
        for t in self.tables:
            r = self.rows[t]
            r = r[r['usable']]
            out.append(pd.DataFrame(dict(table=t, group=self.group[t], target_key=r['target_key'].to_numpy())))
        allr = pd.concat(out, ignore_index=True)
        ok = np.array([split.row_allowed(g, k) for g, k in zip(allr.group, allr.target_key)], dtype=bool)
        return allr[ok]


def table_means(cube: Cube, split: Split, block: int = 1000) -> tuple[dict, dict]:
    """Per training table: mean shrunk (the gamma term) and mean raw over its allowed rows."""
    shr, raw = {}, {}
    for t in cube.tables:
        if split.regime in ('C', 'J') and cube.group[t] == split.held_group:
            continue
        keys = [k for k in cube.keys_of(t) if split.row_allowed(cube.group[t], k)]
        sums = {'shrunk': np.zeros(len(cube.genes)), 'raw': np.zeros(len(cube.genes))}
        cnts = {'shrunk': np.zeros(len(cube.genes)), 'raw': np.zeros(len(cube.genes))}
        for b0 in range(0, len(keys), block):
            for kind in sums:
                x, _ = cube.get(t, kind, keys[b0:b0 + block])
                ok = np.isfinite(x)
                sums[kind] += np.where(ok, x, 0).sum(0)
                cnts[kind] += ok.sum(0)
        shr[t] = np.divide(sums['shrunk'], cnts['shrunk'], out=np.zeros(len(cube.genes)), where=cnts['shrunk'] > 0).astype(F32)
        raw[t] = np.divide(sums['raw'], cnts['raw'], out=np.full(len(cube.genes), np.nan), where=cnts['raw'] > 0).astype(F32)
    return shr, raw


def group_mean(cube: Cube, group: str, keys, common: dict, gamma: float = 1.0, rel_scale: float = 100.0,
               kind: str = 'shrunk') -> np.ndarray:
    """Within-group reliability-weighted mean of (effect - gamma * table common) for ``keys``."""
    G = len(cube.genes)
    num = np.zeros((len(keys), G), F32)
    den = np.zeros((len(keys), G), F32)
    for t in cube.tables_of(group):
        x, have = cube.get(t, kind, keys)
        if not have.any():
            continue
        x = x[have]
        if gamma:
            x = x - gamma * common[t][None, :]
        n = cube.cells(t, keys)[have]
        w = (n / (n + rel_scale)).astype(F32)
        ok = np.isfinite(x)
        num[have] += np.where(ok, x * w[:, None], 0)
        den[have] += np.where(ok, w[:, None], 0)
    return np.divide(num, den, out=np.full_like(num, np.nan), where=den > 0)


def combine_groups(parts: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Equal-weight mean over groups of their (keys x genes) means, NaN-aware; and groups per key."""
    tot = np.zeros_like(parts[0])
    cnt = np.zeros(parts[0].shape, np.int16)
    for p in parts:
        ok = np.isfinite(p)
        tot += np.where(ok, p, 0)
        cnt += ok
    support = np.zeros(parts[0].shape[0], np.int16)
    for p in parts:
        support += np.isfinite(p).any(1)
    return np.divide(tot, cnt, out=np.full_like(tot, np.nan), where=cnt > 0), support


def generic_vector(cube: Cube, raw_means: dict, exclude: set) -> np.ndarray:
    parts = []
    for g in cube.groups:
        if g in exclude:
            continue
        ts = [raw_means[t] for t in cube.tables_of(g) if t in raw_means]
        if ts:
            parts.append(np.nanmean(np.vstack(ts), 0))
    return np.nanmean(np.vstack(parts), 0).astype(F32)


def reference_basal(cube: Cube, exclude: set) -> np.ndarray:
    """Mean over groups (each the mean of its tables) of log1p CPM: what the sources' controls look like."""
    parts = []
    for g in cube.groups:
        if g in exclude:
            continue
        parts.append(np.nanmean(np.vstack([cube.basal[t] for t in cube.tables_of(g)]), 0))
    return np.nanmean(np.vstack(parts), 0).astype(F32)


def gene_weight(log1p_cpm: np.ndarray) -> np.ndarray:
    """ctj convention: w = 0.05 cpm / (1 + 0.05 cpm); 0 where the profile lacks the gene."""
    cpm = np.expm1(np.nan_to_num(log1p_cpm, nan=0.0))
    return (0.05 * cpm / (1 + 0.05 * cpm)).astype(F32)


def gain_features(x_ctx: np.ndarray, x_ref: np.ndarray, *, context: bool) -> np.ndarray:
    """(G, 3) gene features: [log-expression difference to the sources, level, low-expression flag].

    Without context the context's profile is replaced by the reference one: difference 0, level and
    flag of the sources. Missing context values fall back to the reference (feature = no information).
    """
    ref = np.nan_to_num(x_ref, nan=0.0)
    x = np.where(np.isfinite(x_ctx), x_ctx, ref) if context else ref
    d = np.clip(x - ref, -3, 3)
    level = x - 2.0                          # centred near log1p(6): keeps the gain terms separable
    low = (x < LOG5).astype(F32)
    return np.stack([d, level, low], 1).astype(F32)


def m1_design(s: np.ndarray, m: np.ndarray, feats: np.ndarray, context: bool) -> np.ndarray:
    """Per (row, gene) regressors; s (R, G), m (G,), feats (G, 3) -> (R, G, P)."""
    cols = [s, s * feats[None, :, 2]] + ([s * feats[None, :, 0]] if context else []) + [s * feats[None, :, 1]]
    mm = np.broadcast_to(m[None, :], s.shape)
    cols += [mm, mm * feats[None, :, 2]] + ([mm * feats[None, :, 0]] if context else []) + [mm * feats[None, :, 1]]
    return np.stack(cols, -1).astype(F32)


@dataclass
class LinearGain:
    """Weighted ridge for the per-gene gain model (m1 with context, tm0 without)."""
    context: bool
    ridge: float = 1e-3
    xtx: np.ndarray | None = None
    xty: np.ndarray | None = None
    n: int = 0

    def add(self, y: np.ndarray, s: np.ndarray, m: np.ndarray, feats: np.ndarray, w: np.ndarray) -> None:
        s0 = np.nan_to_num(s, nan=0.0)
        X = m1_design(s0, np.nan_to_num(m, nan=0.0), feats, self.context)
        ok = np.isfinite(y) & np.isfinite(s) & (w[None, :] > 0)
        W = np.where(ok, w[None, :], 0.0).astype(F32)
        Xw = X * W[..., None]
        P = X.shape[-1]
        a = np.einsum('rgp,rgq->pq', Xw, X, optimize=True)
        b = np.einsum('rgp,rg->p', Xw, np.where(ok, y, 0.0), optimize=True)
        self.xtx = a if self.xtx is None else self.xtx + a
        self.xty = b if self.xty is None else self.xty + b
        self.n += int(ok.sum())
        self.P = P

    def solve(self) -> np.ndarray:
        reg = self.ridge * np.trace(self.xtx) / self.xtx.shape[0]
        self.coef = np.linalg.solve(self.xtx + reg * np.eye(self.xtx.shape[0]), self.xty)
        return self.coef

    def predict(self, s: np.ndarray, m: np.ndarray, feats: np.ndarray) -> np.ndarray:
        """A pair no source measured (s NaN) keeps only the generic term, as production keeps 0 + common."""
        X = m1_design(np.nan_to_num(s, nan=0.0), np.nan_to_num(m, nan=0.0), feats, self.context)
        return (X @ self.coef.astype(F32)).astype(F32)


def derangement(items: list[str], salt: str) -> dict:
    """Fixed derangement by stable hash order: each item maps to the next one in hash order."""
    order = sorted(items, key=lambda x: unit_hash(x, salt))
    return {order[i]: order[(i + 1) % len(order)] for i in range(len(order))}


def fit_keys(cube: Cube, group: str, split: Split, n_fit: int, salt: str = 'fit') -> list[str]:
    """Up to ``n_fit`` training keys of a group, by stable hash, among keys allowed in ``split``."""
    keys = sorted({k for t in cube.tables_of(group) for k in cube.keys_of(t)
                   if split.row_allowed(group, k)}, key=lambda k: unit_hash(k, salt))
    return keys[:n_fit]


class BasalPCA:
    """Context coordinates: top principal axes of training tables' log1p CPM (group-balanced)."""

    def __init__(self, cube: Cube, train_groups: list[str], d: int):
        rows, weights = [], []
        for g in train_groups:
            ts = cube.tables_of(g)
            for t in ts:
                rows.append(np.nan_to_num(cube.basal[t], nan=0.0))
                weights.append(1.0 / len(ts))
        X = np.vstack(rows).astype(np.float64)
        w = np.asarray(weights)[:, None]
        self.mean = (X * w).sum(0) / w.sum()
        Xc = (X - self.mean) * np.sqrt(w)
        _, sv, vt = np.linalg.svd(Xc, full_matrices=False)
        self.axes = vt[:d]
        scale = sv[:d] / np.sqrt(w.sum())
        self.scale = np.where(scale > 0, scale, 1.0)
        self.explained = (sv[:d] ** 2 / (sv ** 2).sum()).tolist()

    def coords(self, log1p_cpm: np.ndarray) -> np.ndarray:
        x = np.nan_to_num(log1p_cpm, nan=0.0) - self.mean
        return ((self.axes @ x) / self.scale).astype(F32)


class LowRankBilinear:
    """Projected residual  U^T (y - s) = (W0 + sum_l phi_l(c) W_l) U^T s, by ridge.

    Every output coordinate shares one Gram matrix: with u = [1, phi, z, phi_1 z, ..., phi_d z]
    (z = U^T s), Theta = (A + lambda I)^-1 B, A = sum u u^T, B = sum u r^T. The leading
    [1, phi] block is a target-independent term (the common response of the context, modulated by
    its controls). ``d = 0`` is the context-free twin ([1, z] only), fitted on the same rows.
    """

    def __init__(self, U: np.ndarray, d: int, ridge: float):
        self.U, self.d, self.ridge = U.astype(F32), d, ridge
        self.k = U.shape[1]
        D = (self.k + 1) * (d + 1)
        self.A = np.zeros((D, D))
        self.B = np.zeros((D, self.k))
        self.n = 0

    def _u(self, z: np.ndarray, phi: np.ndarray) -> np.ndarray:
        ones = np.ones((len(z), 1), F32)
        lead = [ones] + [ones * phi[l] for l in range(self.d)]
        return np.concatenate(lead + [z] + [phi[l] * z for l in range(self.d)], 1)

    def add(self, resid_proj: np.ndarray, z: np.ndarray, phi: np.ndarray) -> None:
        u = self._u(z, phi).astype(np.float64)
        self.A += u.T @ u
        self.B += u.T @ resid_proj.astype(np.float64)
        self.n += len(z)

    def solve(self) -> None:
        reg = self.ridge * np.trace(self.A) / self.A.shape[0]
        self.theta = np.linalg.solve(self.A + reg * np.eye(self.A.shape[0]), self.B).astype(F32)

    def predict(self, s: np.ndarray, phi: np.ndarray) -> np.ndarray:
        s0 = np.nan_to_num(s, nan=0.0)
        z = s0 @ self.U
        corr = (self._u(z, phi) @ self.theta) @ self.U.T
        return np.where(np.isfinite(s), s + corr, np.nan).astype(F32)
