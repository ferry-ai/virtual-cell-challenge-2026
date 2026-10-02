"""Effect-space indices of the bench (diagnostic, never a VCC score).

All indices compare a predicted ln fold change with the held-out table's measured one, on cube genes
measured in the truth, with the expression weight of the held-out controls (ctj convention,
w = 0.05 cpm / (1 + 0.05 cpm)), the target's own gene excluded:

* ``pds``       discrimination as in the official PDS: for each target, the normalised rank of its own
                truth among the truths of a block of at most 300 targets (stable hash blocks, the size
                of a competition panel), by weighted cosine; the genes of every target of the block are
                excluded, as the official PDS excludes the panel's targets. 1 = perfect, 0.5 = chance.
* ``cos``       weighted cosine between prediction and truth.
* ``cos_spec``  the same after removing, from truth and prediction, their mean over the table's
                evaluated targets: the target-specific part.
* ``mse_ratio`` sum w^2 (y - p)^2 / sum w^2 y^2 (1 = the null prediction).
* ``sign_sig``  share of truth-significant genes (|y| >= 3 SE) whose predicted sign is right (fidelity-like).
"""
from __future__ import annotations

import numpy as np

from splits import unit_hash

F32 = np.float32


def _wnorm(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return np.divide(x, n, out=np.zeros_like(x), where=n > 0)


def blocks_of(keys: list[str], size: int = 300, salt: str = 'pds-block') -> list[np.ndarray]:
    order = np.array(sorted(range(len(keys)), key=lambda i: unit_hash(keys[i], salt)))
    nb = max(1, int(np.ceil(len(keys) / size)))
    return [order[i::nb] for i in range(nb)]


def score_table(pred: np.ndarray, truth: np.ndarray, se: np.ndarray, w: np.ndarray, keys: list[str],
                target_gene_pos: np.ndarray, *, block_size: int = 300) -> dict[str, np.ndarray]:
    """Per-target indices for one held-out table. ``target_gene_pos`` is -1 where off the cube genes."""
    R, G = truth.shape
    ok = np.isfinite(truth) & np.isfinite(pred)
    own = np.zeros((R, G), bool)
    rows = np.flatnonzero(target_gene_pos >= 0)
    own[rows, target_gene_pos[rows]] = True
    ok &= ~own
    p = np.where(ok, pred, 0.0).astype(np.float64) * w[None, :]
    y = np.where(ok, truth, 0.0).astype(np.float64) * w[None, :]
    num = (p * y).sum(1)
    den = np.linalg.norm(p, axis=1) * np.linalg.norm(y, axis=1)
    cos = np.divide(num, den, out=np.full(R, np.nan), where=den > 0)
    mse = np.divide(((y - p) ** 2).sum(1), (y ** 2).sum(1), out=np.full(R, np.nan), where=(y ** 2).sum(1) > 0)
    # target-specific part: centre over the evaluated targets of this table
    pm = np.where(ok, pred, np.nan)
    ym = np.where(ok, truth, np.nan)
    pc = np.where(ok, pm - np.nanmean(pm, 0, keepdims=True), 0.0) * w[None, :]
    yc = np.where(ok, ym - np.nanmean(ym, 0, keepdims=True), 0.0) * w[None, :]
    den = np.linalg.norm(pc, axis=1) * np.linalg.norm(yc, axis=1)
    cos_spec = np.divide((pc * yc).sum(1), den, out=np.full(R, np.nan), where=den > 0)
    sig = ok & np.isfinite(se) & (se > 0) & (np.abs(np.nan_to_num(truth)) >= 3 * np.nan_to_num(se, nan=np.inf))
    agree = sig & (np.sign(np.nan_to_num(pred)) == np.sign(np.nan_to_num(truth))) & (np.nan_to_num(pred) != 0)
    nsig = sig.sum(1)
    sign_sig = np.divide(agree.sum(1), nsig, out=np.full(R, np.nan), where=nsig > 0)
    pds = np.full(R, np.nan)
    for blk in blocks_of(keys, block_size):
        if len(blk) < 2:
            continue
        cols = np.ones(G, bool)
        tg = target_gene_pos[blk]
        cols[tg[tg >= 0]] = False
        pb = np.where(ok[blk][:, cols], pred[blk][:, cols], 0.0) * w[None, cols]
        yb = np.where(np.isfinite(truth[blk][:, cols]), truth[blk][:, cols], 0.0) * w[None, cols]
        has = (np.abs(pb).sum(1) > 0) & (np.abs(yb).sum(1) > 0)
        S = _wnorm(pb) @ _wnorm(yb).T
        for i, r in enumerate(blk):
            if not has[i]:
                continue
            others = has.copy()
            s = S[i, others]
            mine = S[i, i]
            n = others.sum() - 1
            if n < 1:
                continue
            rank = (s > mine).sum() + ((s == mine).sum() - 1) / 2
            pds[r] = 1 - rank / n
    return dict(pds=pds, cos=cos, cos_spec=cos_spec, mse_ratio=mse, sign_sig=sign_sig, n_sig=nsig.astype(float))
