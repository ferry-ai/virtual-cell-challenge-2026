"""The scorer's own differential-expression call, usable outside a full scoring run.

Four of the six scored metrics are read off one DE table per side: Wilcoxon on
log1p(CPM) of a perturbation's cells against the REAL control pool, per-target
BH, a reference-only 5-CPM gene gate, and a log2FC of per-cell CPM means
(`cell_eval2.de_compute.compute_de`, called by `run.py` with the parameters of
`configs/vcc2026.yaml`). Everything this project wants to know about a
generator or a predictor before spending a submission -- how many genes it
makes significant, with which sign, at what p-value -- is a property of that
table, so this module computes exactly that table and nothing else.

The CPU backend concatenates the perturbation cells with the control cells,
which is what the scorer does on a machine without CUDA. `backend` is recorded
beside every number because the engines do not agree to the last digit (D-014).
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
import scipy.sparse as sp

__all__ = ["ReferencePool", "bh", "scanpy_cpm", "de_frame", "fast_scorer_de", "scorer_config", "scorer_de", "summarize_de"]

CONTROL = "non-targeting"


@lru_cache(maxsize=1)
def scorer_config():
    from vcc2026.evaluation import load_eval_config

    return load_eval_config("vcc2026")


def scorer_de(
    cells: sp.csr_matrix,
    labels: np.ndarray,
    control: sp.csr_matrix,
    genes: np.ndarray,
    *,
    backend: str = "scanpy",
    threads: int = -1,
):
    """DE table (polars) for `cells` grouped by `labels`, each group against `control`."""
    import anndata as ad
    from cell_eval2.de_compute import compute_de

    cfg = scorer_config()
    labels = np.asarray(labels).astype(str)
    if CONTROL in set(labels):
        raise ValueError("a perturbation group may not carry the control label")
    x = sp.vstack([sp.csr_matrix(cells, dtype=np.float32), sp.csr_matrix(control, dtype=np.float32)]).tocsr()
    obs = pd.DataFrame(
        {cfg.pert_col: pd.Categorical(np.concatenate([labels, np.full(control.shape[0], CONTROL)]))},
        index=pd.Index([f"c{i}" for i in range(x.shape[0])]),
    )
    adata = ad.AnnData(X=x, obs=obs, var=pd.DataFrame(index=pd.Index(np.asarray(genes).astype(str))))
    return compute_de(
        adata, backend=backend, groupby=cfg.pert_col, reference=cfg.control,
        mean_calc=cfg.de.mean_calc, epsilon=cfg.de.epsilon, input_type="counts",
        target_sum=cfg.target_sum, clip_value=cfg.de.clip_value, fdr_scope=cfg.de.fdr_scope,
        filter_gene_min_cpm_cell=cfg.filter.filter_gene_min_cpm_cell, threads=threads,
    )


def de_frame(table) -> pd.DataFrame:
    """A polars DE table as pandas, without requiring pyarrow."""
    if isinstance(table, pd.DataFrame):
        return table
    return pd.DataFrame({c: table[c].to_numpy() for c in table.columns})


def summarize_de(table, *, alpha: float = 0.05, exclude: dict[str, str] | None = None) -> pd.DataFrame:
    """Per target: tested genes, significant genes, and the sign mix of the significant ones."""
    df = de_frame(table)
    if exclude:
        own = df["target"].map(exclude)
        df = df[df["feature"].astype(str) != own.astype(str)]
    sig = df[df["p_adj"] < alpha]
    lfc = sig["log2_fold_change"]
    out = pd.DataFrame({
        "n_tested": df.groupby("target").size(),
        "n_sig": sig.groupby("target").size(),
        "n_sig_up": sig[lfc > 0].groupby("target").size(),
        "median_abs_lfc_sig": sig.assign(a=lfc.abs()).groupby("target")["a"].median(),
        "mean_lfc_all": df.groupby("target")["log2_fold_change"].mean(),
    }).fillna({"n_sig": 0, "n_sig_up": 0})
    out["frac_up"] = out["n_sig_up"] / out["n_sig"].where(out["n_sig"] > 0)
    return out


def scanpy_cpm(counts: sp.csr_matrix) -> sp.csr_matrix:
    """CPM with scanpy's own arithmetic, ``x / (library / 1e6)``.

    The scorer normalizes through `sc.pp.normalize_total`, and the tie structure the
    Wilcoxon variance depends on is a property of the exact floating-point values: two
    cells with mathematically equal ratios can round to equal or to different floats
    depending on whether the library is divided or its reciprocal multiplied. Measured
    on a 300-cell fixture: the reciprocal form found 20,070 tie units where scanpy's
    division finds 20,538.
    """
    m = sp.csr_matrix(counts, dtype=np.float64, copy=True)
    lib = np.add.reduceat(m.data, m.indptr[:-1]) if m.nnz else np.zeros(m.shape[0])
    lib = np.where(np.diff(m.indptr) > 0, lib, 0.0)
    scale = lib / 1e6
    m.data = m.data / np.repeat(scale, np.diff(m.indptr))
    return m


class ReferencePool:
    """The control pool, pre-sorted once, for rank-sum tests of many groups against it.

    `compute_de`'s CPU path ranks every group together with the whole reference, gene by
    gene, so its cost is (groups x reference cells x genes). Against a FIXED reference the
    Mann-Whitney statistic of a group only needs, for each of its values, how many
    reference values lie below it and how many tie with it. Keying every value as the
    complex number ``gene_index + 1j * value`` makes the column-sorted reference one
    globally sorted vector (numpy orders complex numbers lexicographically), so a single
    `searchsorted` answers every (cell, gene) of a group at once -- without the precision a
    real-valued offset would cost: an offset of ``20 * j`` merged values scanpy keeps one
    ulp apart and moved p-values by up to 4e-4 in log10 on the validation fixture. Ties --
    zeros above all -- enter the variance exactly as scanpy's ``tie_correct=True`` counts
    them over the combined sample.
    """

    def __init__(self, control: sp.csr_matrix, genes: np.ndarray, *, cpm_gate: float = 5.0,
                 epsilon: float = 1e-9) -> None:
        self.genes = np.asarray(genes).astype(str)
        self.n_c, self.n_genes = control.shape
        cpm = scanpy_cpm(control)
        self.ref_mean = np.asarray(cpm.mean(axis=0)).ravel()
        self.kept = np.flatnonzero(self.ref_mean > cpm_gate)
        self.epsilon = epsilon
        dense = np.log1p(cpm[:, self.kept].toarray())
        dense.sort(axis=0)
        keys = np.empty(dense.shape, dtype=np.complex128)
        keys.real = np.arange(self.kept.size, dtype=np.float64)[None, :]
        keys.imag = dense
        del dense
        self._sorted = np.ascontiguousarray(keys.T).ravel()  # gene 0 block, gene 1 block, ...
        del keys
        self._tie_c = self._tie_sums(self._sorted, self.n_c)

    def _tie_sums(self, flat: np.ndarray, n_per_gene: int) -> np.ndarray:
        """Per kept gene, sum over tie runs of (t^3 - t)."""
        k = self.kept.size
        start = np.ones(flat.size, dtype=bool)
        start[1:] = flat[1:] != flat[:-1]
        idx = np.flatnonzero(start)
        lengths = np.diff(np.append(idx, flat.size)).astype(np.float64)
        gene = idx // n_per_gene
        return np.bincount(gene, weights=lengths**3 - lengths, minlength=k)

    def test(self, cells: sp.csr_matrix) -> tuple[np.ndarray, np.ndarray]:
        """(p_value, log2FC) over the kept genes for one group of cells."""
        from scipy.special import ndtr

        n_g = cells.shape[0]
        k = self.kept.size
        cpm = scanpy_cpm(cells)
        grp_mean = np.asarray(cpm.mean(axis=0)).ravel()[self.kept]
        vals = np.log1p(cpm[:, self.kept].toarray())
        vals.sort(axis=0)
        keys = np.empty(vals.shape, dtype=np.complex128)
        keys.real = np.arange(k, dtype=np.float64)[None, :]
        keys.imag = vals
        flat = np.ascontiguousarray(keys.T).ravel()
        left = np.searchsorted(self._sorted, flat, side="left")
        right = np.searchsorted(self._sorted, flat, side="right")
        gene_of = np.repeat(np.arange(k), n_g)
        less = left - gene_of * self.n_c
        eq = right - left
        r_sum = n_g * (n_g + 1) / 2.0 + np.bincount(gene_of, weights=less + 0.5 * eq, minlength=k)
        # tie term over the combined sample
        start = np.ones(flat.size, dtype=bool)
        start[1:] = flat[1:] != flat[:-1]
        idx = np.flatnonzero(start)
        g_len = np.diff(np.append(idx, flat.size)).astype(np.float64)
        c_len = eq[idx].astype(np.float64)
        run_gene = gene_of[idx]
        f = lambda t: t**3 - t  # noqa: E731
        tie = self._tie_c + np.bincount(run_gene, weights=f(c_len + g_len) - f(c_len), minlength=k)
        n = n_g + self.n_c
        tie_factor = 1.0 - tie / (n**3 - n)
        sd = np.sqrt(np.maximum(tie_factor, 0.0) * n_g * self.n_c * (n + 1) / 12.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            z = (r_sum - n_g * (n + 1) / 2.0) / sd
        z = np.where(sd > 0, z, 0.0)  # scanpy: scores[np.isnan(scores)] = 0
        p = 2.0 * ndtr(-np.abs(z))
        lfc = np.log2((grp_mean + self.epsilon) / (self.ref_mean[self.kept] + self.epsilon))
        return p, lfc


def bh(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values."""
    n = p.size
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(adj, 1.0)
    return out


def fast_scorer_de(cells: sp.csr_matrix, labels: np.ndarray, pool: ReferencePool):
    """The scorer's CPU DE table (target, feature, log2FC, p_value, p_adj) via `ReferencePool`."""
    import polars as pl

    labels = np.asarray(labels).astype(str)
    cells = sp.csr_matrix(cells)
    order = np.argsort(labels, kind="stable")
    uniq, starts = np.unique(labels[order], return_index=True)
    bounds = np.append(starts, labels.size)
    feats = pool.genes[pool.kept]
    frames = []
    for i, t in enumerate(uniq):
        rows = order[bounds[i]:bounds[i + 1]]
        p, lfc = pool.test(cells[rows])
        frames.append(pl.DataFrame({
            "target": np.full(feats.size, t), "feature": feats,
            "log2_fold_change": lfc, "p_value": p, "p_adj": bh(p),
        }))
    return pl.concat(frames, how="vertical")
