"""Frozen context, target and joint generalisation benchmarks in effect space."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .multisource import AxisTable, mix


def file_hash(path: Path) -> str:
    """SHA256 of input bytes, streamed in bounded memory."""
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def frozen_splits(sources: dict[str, AxisTable], contexts: dict[str, str],
                  hashes: dict[str, str], regime: str, folds: int = 5, seed: int = 0,
                  existing: Path | None = None) -> dict:
    """Create splits or validate and return the exact saved experiment specification."""
    targets = sorted({t for s in sources.values() for t in s.targets})
    labels = sorted(set(contexts.values()))
    if regime not in ('C', 'T', 'J') or len(labels) < 2:
        raise ValueError('C/T/J and at least two contexts are required')
    if set(contexts) != set(sources):
        raise ValueError('Map every source to a context')
    if existing is not None:
        saved = json.loads(Path(existing).read_text(encoding='utf-8'))
        if (saved['hashes'] != hashes or saved['contexts'] != contexts
                or saved['sources'] != sorted(sources) or saved['regime'] != regime
                or sorted(saved['target_folds']) != targets):
            raise ValueError('Frozen inputs, contexts or regime differ')
        return saved
    if not 2 <= folds <= len(targets):
        raise ValueError('Use 2 <= folds <= target count')
    rng = np.random.default_rng(seed)
    assignment = {t: int(i % folds) for i, t in enumerate(rng.permutation(targets))}
    splits = []
    for context in labels:
        for fold in ([None] if regime == 'C' else range(folds)):
            splits.append(dict(context=context, fold=fold,
                               held_out_contexts=[] if regime == 'T' else [context],
                               swap=str(rng.choice([c for c in labels if c != context]))))
    return dict(version=1, regime=regime, sources=sorted(sources), contexts=contexts,
                hashes=hashes, seed=seed, folds=folds, target_folds=assignment, splits=splits)


def training_sources(sources: dict[str, AxisTable], spec: dict, split: dict) -> dict[str, AxisTable]:
    """Remove entire held-out contexts and T/J target rows before any fitting."""
    held = {t for t, f in spec['target_folds'].items() if f == split['fold']}
    train = {}
    for name, tab in sources.items():
        if spec['contexts'][name] in split['held_out_contexts']:
            continue
        keep = [i for i, t in enumerate(tab.targets) if t not in held]
        train[name] = AxisTable(name, [tab.targets[i] for i in keep],
                               tab.shrunk[keep].copy(), tab.raw[keep].copy(),
                               tab.se[keep].copy(), tab.n_cells[keep].copy(), {})
    return train


def finite_mean(rows: np.ndarray) -> np.ndarray:
    """Per-column mean, zero only when no training observation exists."""
    count = np.isfinite(rows).sum(axis=0)
    return np.divide(np.nansum(rows, axis=0), count,
                     out=np.zeros(rows.shape[1], np.float32), where=count > 0)


class Predictor:
    """Shared fit/predict API; context is a label into supplied log1p basal vectors.

    Linear models use pooled training-target PCA, with missing centered values zero.
    Context regression adds diag(log1p CPM) G W2 with a shared fitted gene intercept.
    Missing observations are imputed by the pooled training gene mean.
    Normal equations exploit the separable gene/target design (no gigantic design).
    """

    def __init__(self, name: str, genes: list[str], contexts: dict[str, str],
                 basal: dict[str, np.ndarray], k: int = 8, ridge: float = 0.01,
                 gamma: float = 0.0, reliability_scale: float = 100.0):
        if name not in ('null', 'common', 'transfer', 'linear_embedding', 'context_linear'):
            raise ValueError(name)
        if not 1 <= k <= 32 or ridge <= 0 or reliability_scale < 0:
            raise ValueError('Require 1 <= k <= 32, ridge > 0, reliability >= 0')
        self.name, self.genes = name, list(genes)
        self.contexts, self.basal = contexts, basal
        self.k, self.ridge = k, ridge
        self.gamma, self.reliability_scale = gamma, reliability_scale

    def fit(self, train_sources: dict[str, AxisTable], context: str) -> Predictor:
        self.tables = list(train_sources.values())
        targets = sorted({t for s in self.tables for t in s.targets})
        if not targets:
            raise ValueError('Split has no training targets')
        pooled = np.zeros((len(targets), len(self.genes)), np.float32)
        counts = np.zeros_like(pooled)
        for tab in self.tables:
            rows = tab.rows(targets)
            ok = np.isfinite(rows)
            pooled += np.where(ok, rows, 0)
            counts += ok
        pooled = np.divide(pooled, counts, out=np.full_like(pooled, np.nan), where=counts > 0)
        self.b = finite_mean(pooled)
        if self.name in ('null', 'common', 'transfer'):
            return self
        axis = {g: i for i, g in enumerate(self.genes)}
        if any(t not in axis for t in targets):
            raise ValueError('Training target missing from gene axis')
        y = np.nan_to_num(pooled - self.b).T
        # Target Gram eigendecomposition avoids a full genes-by-genes PCA.
        vals, vecs = np.linalg.eigh(y.T @ y)
        take = np.argsort(vals)[::-1][:min(self.k, len(targets))]
        take = take[vals[take] > max(float(vals.max()), 1.0) * 1e-7]
        self.g = (y @ vecs[:, take]) / np.sqrt(vals[take])
        k = self.g.shape[1]
        blocks = 2 if self.name == 'context_linear' else 1
        gram = np.zeros((blocks*k*k, blocks*k*k), np.float32)
        rhs = np.zeros(blocks*k*k, np.float32)
        design_sums = []
        residual_sum = np.zeros(len(self.genes), np.float32)
        regressions = ([(tab.targets, tab.shrunk, self.contexts[tab.name]) for tab in self.tables]
                       if blocks == 2 else [(targets, pooled, None)])
        observations = sum(len(ts) for ts, _, _ in regressions)
        for ts, effects, label in regressions:
            z = self.g[[axis[t] for t in ts]]
            yc = np.nan_to_num(effects - self.b).T
            designs = [self.g]
            if blocks == 2:
                designs.append(self.g * self.basal[label][:, None])
            design_sums.append((designs, z.sum(axis=0)))
            residual_sum += yc.sum(axis=1)
            for a, ga in enumerate(designs):
                sa = slice(a*k*k, (a+1)*k*k)
                rhs[sa] += (ga.T @ yc @ z).ravel()
                for b, gb in enumerate(designs):
                    sb = slice(b*k*k, (b+1)*k*k)
                    gram[sa, sb] += np.kron(ga.T @ gb, z.T @ z)
        # Eliminate the unpenalized per-gene intercept by a Schur complement.
        for designs, zsum in design_sums:
            for a, ga in enumerate(designs):
                sa = slice(a*k*k, (a+1)*k*k)
                rhs[sa] -= np.outer(ga.T @ residual_sum, zsum).ravel() / observations
                for other, other_zsum in design_sums:
                    for b, gb in enumerate(other):
                        sb = slice(b*k*k, (b+1)*k*k)
                        gram[sa, sb] -= np.kron(ga.T @ gb, np.outer(zsum, other_zsum)) / observations
        gram.flat[::len(gram)+1] += self.ridge
        self.coef = np.linalg.solve(gram, rhs).reshape(blocks, k, k)
        self.b += residual_sum / observations
        for designs, zsum in design_sums:
            for a, ga in enumerate(designs):
                self.b -= (ga @ self.coef[a] @ zsum) / observations
        return self

    def predict(self, targets: list[str], context: str) -> np.ndarray:
        shape = (len(targets), len(self.genes))
        if self.name == 'null':
            return np.zeros(shape, np.float32)
        if self.name == 'common':
            return np.broadcast_to(self.b, shape).copy()
        if self.name == 'transfer':
            out, den = mix(self.tables, targets, gamma=self.gamma,
                           reliability_scale=self.reliability_scale)
            return np.where(den > 0, out, np.nan).astype(np.float32)
        axis = {g: i for i, g in enumerate(self.genes)}
        out = np.full(shape, np.nan, np.float32)
        valid = [i for i, t in enumerate(targets) if t in axis]
        z = self.g[[axis[targets[i]] for i in valid]]
        pred = self.g @ self.coef[0] @ z.T
        if self.name == 'context_linear':
            pred += self.basal[context][:, None] * (self.g @ self.coef[1] @ z.T)
        out[valid] = pred.T + self.b
        return out


def score_targets(pred: np.ndarray, truth: np.ndarray, se: np.ndarray,
                  targets: list[str], genes: list[str], basal_cpm: np.ndarray,
                  excluded: tuple | list = (), n: int = 100) -> list[dict]:
    """Effect metrics; missing predictions remain unscored, PDS singleton is NaN.

    PDS uses pairwise measured intersections and w-weighted vectors (w squared
    in dot products). Precision uses measured genes, excluding the target and
    explicit exclusions; reach additionally requires finite positive SE and z>=3.
    """
    if n < 1:
        raise ValueError('precision n must be positive')
    w = 0.05 * np.asarray(basal_cpm, np.float32)
    w = w / (1 + w)
    allowed = ~np.isin(genes, list(excluded))
    result = []
    for i, target in enumerate(targets):
        ok = allowed & np.isfinite(pred[i]) & np.isfinite(truth[i])
        scores = np.full(len(targets), np.nan)
        for j in range(len(targets)):
            mask = allowed & np.isfinite(pred[i]) & np.isfinite(truth[j])
            if mask.any():
                a, b = pred[i, mask] * w[mask], truth[j, mask] * w[mask]
                norm = np.linalg.norm(a) * np.linalg.norm(b)
                scores[j] = float(a @ b / norm) if norm else 0.0
        finite = np.isfinite(scores)
        pds = np.nan
        if finite[i] and finite.sum() > 1:
            rank = np.sum(scores[finite] > scores[i]) + (np.sum(scores[finite] == scores[i])-1)/2
            pds = 1 - rank / (finite.sum()-1)
        den = np.sum((w[ok]*truth[i, ok])**2)
        mse = np.sum((w[ok]*(truth[i, ok]-pred[i, ok]))**2) / den if den > 0 else np.nan
        ok &= np.asarray(genes) != target
        order = np.flatnonzero(ok)
        order = order[np.argsort(-np.abs(pred[i, order]), kind='stable')]
        matches = np.sign(pred[i, order]) == np.sign(truth[i, order])
        precision = float(matches[:n].mean()) if len(order) else np.nan
        sig = np.isfinite(se[i, order]) & (se[i, order] > 0)
        sig &= np.abs(truth[i, order]) >= 3 * se[i, order]
        hits = matches[sig]
        prefixes = np.flatnonzero(np.cumsum(hits) >= 0.9*np.arange(1, len(hits)+1)) + 1
        reach = float(prefixes.max(initial=0)/len(hits)) if len(hits) else np.nan
        result.append(dict(target=target, pds=pds, reach=reach, precision_at_n=precision, mse_ratio=float(mse)))
    return result


def paired_bootstrap(a, b, seed: int = 0, draws: int = 1000) -> dict:
    """Mean paired a-b difference and percentile 95% interval over finite targets."""
    delta = np.asarray(a, float) - np.asarray(b, float)
    delta = delta[np.isfinite(delta)]
    if not len(delta):
        return dict(difference=None, low=None, high=None, targets=0)
    rng = np.random.default_rng(seed)
    samples = np.array([rng.choice(delta, len(delta), replace=True).mean() for _ in range(draws)])
    return dict(difference=float(delta.mean()), low=float(np.quantile(samples, .025)),
                high=float(np.quantile(samples, .975)), targets=len(delta))
