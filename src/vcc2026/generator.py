"""A learned generative model of one context's control cells.

The generator of trial-01 drew Poisson counts from ONE mean profile. Every cell
was the same cell up to depth, so the scorer's Wilcoxon test -- which compares
the predicted cells with the real control cells, gene by gene -- found shape
differences everywhere: 4-6% more detected genes at zero predicted effect
(`reports/trial_2026-09-12/q01pilot_generation_diagnostics.json`) and, on
HepG2, a no-effect prediction reading 1.154 on the normalized MSE where 1.0 is
"predicted the control" (`reports/hepg2_2026-09-14/generator_x_predictor.json`).

This model keeps the three things that one-profile sampling throws away:

* **cell state.** PCA of the controls' log-normalized highly variable genes,
  and a Gaussian mixture over (state, log library size), so a new cell's depth
  stays coupled to its composition -- the covariance that separates the DE
  log2FC functional from the pseudobulk one (cell_eval2 #286);
* **the composition for a state**, decoded as the mean composition of the
  control cells nearest to the sampled state (a kernel regression). The
  sampled state is new, and the output is an average of many cells with fresh
  count noise on top: no control cell is copied into a prediction, which is the
  rule's wording ("model inputs only");
* **gene-level overdispersion**, as a per-gene Gamma multiplier fitted so that
  the generated zero fraction (or, for genes that are almost never zero, the
  variance) matches the controls.

A predicted effect enters as a per-gene fold change on the rate. The library
is not renormalized: knocking a gene down removes its molecules and leaves the
others' absolute rates alone, so their share rises exactly as it does in a real
cell.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

__all__ = ["ControlModel", "bulk_lognorm", "per_cell_cpm_mean"]


def bulk_lognorm(counts: sp.csr_matrix | np.ndarray, target_sum: float = 5e4) -> np.ndarray:
    """The scorer's v2 expression comparator for one group: log1p(T * sum_g / sum)."""
    col = np.asarray(counts.sum(axis=0), dtype=np.float64).ravel()
    tot = col.sum()
    return np.log1p(target_sum * col / tot) if tot > 0 else np.zeros_like(col)


def per_cell_cpm_mean(counts: sp.csr_matrix) -> np.ndarray:
    """Mean over cells of per-cell CPM: the functional the DE log2FC uses."""
    counts = sp.csr_matrix(counts, dtype=np.float64)
    lib = np.asarray(counts.sum(axis=1)).ravel()
    lib[lib == 0] = 1.0
    norm = sp.diags(1e6 / lib) @ counts
    return np.asarray(norm.mean(axis=0)).ravel()


def _row_normalize(x: sp.csr_matrix) -> tuple[sp.csr_matrix, np.ndarray]:
    lib = np.asarray(x.sum(axis=1), dtype=np.float64).ravel()
    safe = np.where(lib > 0, lib, 1.0)
    return (sp.diags((1.0 / safe).astype(np.float32)) @ x).tocsr().astype(np.float32), lib


@dataclass
class ControlModel:
    n_hvg: int = 3000
    n_pcs: int = 20
    n_components: int = 30
    knn: int = 30
    state: str = "gmm"          # "gmm" or "kde"
    kde_scale: float = 0.5      # bandwidth as a fraction of the per-PC nearest-neighbour spread
    max_phi: float = 200.0
    n_draw: int = 4000          # simulated cells used to fit the dispersion
    seed: int = 0
    # fitted
    comp: sp.csr_matrix | None = field(default=None, repr=False)
    lib: np.ndarray | None = field(default=None, repr=False)
    hvg: np.ndarray | None = field(default=None, repr=False)
    z: np.ndarray | None = field(default=None, repr=False)
    phi: np.ndarray | None = field(default=None, repr=False)
    mean_fix: np.ndarray | None = field(default=None, repr=False)
    diagnostics: dict = field(default_factory=dict)

    # ---- fitting -----------------------------------------------------------------------
    def fit(self, counts: sp.csr_matrix, *, log=print) -> "ControlModel":
        from sklearn.decomposition import PCA
        from sklearn.mixture import GaussianMixture
        from sklearn.neighbors import NearestNeighbors

        counts = sp.csr_matrix(counts, dtype=np.float32)
        n, g = counts.shape
        self.comp, self.lib = _row_normalize(counts)
        # HVG on log1p(1e4 * fraction), ranked by variance within detection-rate bins. Moments
        # come straight from the CSR arrays (zeros contribute log1p(0) = 0), with no copy of
        # the matrix: at 18,400 x 18,533 two copies were ~2.6 GB of transient memory.
        logdata = np.log1p(1e4 * self.comp.data.astype(np.float64))
        mean = np.bincount(self.comp.indices, weights=logdata, minlength=g) / n
        var = np.bincount(self.comp.indices, weights=logdata**2, minlength=g) / n - mean**2
        del logdata
        detect = np.bincount(self.comp.indices, minlength=g) / n
        ok = detect >= 0.02
        bins = np.digitize(mean, np.quantile(mean[ok], np.linspace(0, 1, 21)[1:-1]))
        score = np.full(g, -np.inf)
        for b in np.unique(bins[ok]):
            m = ok & (bins == b)
            v = var[m]
            score[m] = (v - v.mean()) / (v.std() + 1e-12)
        self.hvg = np.sort(np.argsort(score)[::-1][: self.n_hvg])
        dense = self.comp[:, self.hvg].toarray()
        np.log1p(1e4 * dense, out=dense)
        pca = PCA(n_components=self.n_pcs, random_state=self.seed, svd_solver="randomized")
        self.z = pca.fit_transform(dense).astype(np.float32)
        self._pca_var = float(pca.explained_variance_ratio_.sum())
        del dense
        self._nn = NearestNeighbors(n_neighbors=self.knn).fit(self.z)
        loglib = np.log(np.maximum(self.lib, 1.0))
        if self.state == "gmm":
            self._gmm = GaussianMixture(
                n_components=self.n_components, covariance_type="full",
                random_state=self.seed, reg_covar=1e-4, max_iter=300,
            ).fit(np.column_stack([self.z, loglib]))
        elif self.state == "kde":
            d, _ = NearestNeighbors(n_neighbors=2).fit(self.z).kneighbors(self.z)
            self._bw = self.kde_scale * float(np.median(d[:, 1]))
            self._loglib = loglib
        else:
            raise ValueError(f"unknown state model {self.state!r}")
        log(f"  fit: {n} cells, {len(self.hvg)} HVG, PCA var {self._pca_var:.3f}, state={self.state}")
        self._fit_dispersion(counts, log=log)
        return self

    def sample_states(self, n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
        if self.state == "gmm":
            # sklearn's sampler draws with its own seed; drive it from ours.
            self._gmm.random_state = int(rng.integers(2**31 - 1))
            s, _ = self._gmm.sample(n)
            s = s[rng.permutation(n)]
            return s[:, :-1].astype(np.float32), np.exp(s[:, -1])
        pick = rng.integers(0, self.z.shape[0], size=n)
        z = self.z[pick] + rng.normal(0.0, self._bw, size=(n, self.z.shape[1])).astype(np.float32)
        return z, np.exp(self._loglib[pick])

    def decode(self, z: np.ndarray) -> np.ndarray:
        _, idx = self._nn.kneighbors(z)
        n = z.shape[0]
        w = sp.csr_matrix(
            (np.full(idx.size, 1.0 / self.knn, dtype=np.float32),
             idx.ravel(), np.arange(0, idx.size + 1, self.knn)),
            shape=(n, self.comp.shape[0]),
        )
        rho = (w @ self.comp).toarray()
        if self.mean_fix is not None:
            rho *= self.mean_fix[None, :]
        return rho

    def _rates(self, n: int, rng: np.random.Generator) -> np.ndarray:
        z, lib = self.sample_states(n, rng)
        return self.decode(z) * lib[:, None].astype(np.float32)

    def _fit_dispersion(self, counts: sp.csr_matrix, *, n_draw: int | None = None, log=print) -> None:
        rng = np.random.default_rng(self.seed + 1)
        n = counts.shape[0]
        n_draw = n_draw or self.n_draw
        real_mean = np.asarray(counts.mean(axis=0), dtype=np.float64).ravel()
        real_var = np.bincount(counts.indices, weights=counts.data.astype(np.float64) ** 2,
                               minlength=counts.shape[1]) / n - real_mean**2
        real_p0 = 1.0 - np.bincount(counts.indices, minlength=counts.shape[1]) / n
        lam = self._rates(n_draw, rng).astype(np.float64)
        gen_mean = lam.mean(axis=0)
        # Mean correction: the kernel regression and the sampled depths should reproduce
        # the control mean; whatever they miss is removed gene by gene.
        fix = np.where(gen_mean > 0, real_mean / np.where(gen_mean > 0, gen_mean, 1.0), 1.0)
        self.mean_fix = np.clip(fix, 0.5, 2.0).astype(np.float32)
        lam *= self.mean_fix[None, :]
        v_lam = lam.var(axis=0)
        s2 = (lam**2).mean(axis=0)
        m = lam.mean(axis=0)
        phi_var = np.clip((real_var - m - v_lam) / np.maximum(s2, 1e-12), 0.0, self.max_phi)
        # Zero-fraction matching where zeros carry the shape: bisection on log phi.
        target = real_p0
        use_zero = (target > 0.02) & (target < 0.995) & (m > 0)
        cols = np.flatnonzero(use_zero)
        sub = lam[: min(1500, n_draw)][:, cols]
        p0_pois = np.exp(-sub).mean(axis=0)
        lo = np.full(cols.size, -8.0)
        hi = np.full(cols.size, np.log(self.max_phi))
        for _ in range(28):
            mid = 0.5 * (lo + hi)
            ph = np.exp(mid)
            p0 = np.exp(-np.log1p(ph[None, :] * sub) / ph[None, :]).mean(axis=0)
            too_few = p0 < target[cols]
            lo = np.where(too_few, mid, lo)
            hi = np.where(too_few, hi, mid)
        phi_zero = np.exp(0.5 * (lo + hi))
        phi_zero[p0_pois >= target[cols]] = 0.0  # Poisson alone already has enough zeros
        phi = phi_var.copy()
        phi[cols] = phi_zero
        self.phi = phi.astype(np.float32)
        self.diagnostics["dispersion"] = {
            "n_zero_matched": int(cols.size),
            "phi_median_expressed": float(np.median(phi[m > 0.05])) if np.any(m > 0.05) else None,
            "mean_fix_q01_q99": [float(np.quantile(self.mean_fix[real_mean > 0], q)) for q in (0.01, 0.99)],
        }
        log(f"  dispersion: {cols.size} genes zero-matched, median phi (mean>0.05) "
            f"{self.diagnostics['dispersion']['phi_median_expressed']}")

    # ---- sampling ----------------------------------------------------------------------
    def sample(
        self,
        n: int,
        rng: np.random.Generator,
        *,
        fold_change: np.ndarray | None = None,
        max_stored_per_cell: int | None = None,
        max_counts_per_cell: int = 1_000_000,
    ) -> sp.csr_matrix:
        lam = self._rates(n, rng)
        if fold_change is not None:
            lam *= np.asarray(fold_change, dtype=np.float32)[None, :]
        cols = np.flatnonzero(lam.max(axis=0) > 0)
        sub = lam[:, cols]
        ph = self.phi[cols]
        over = ph > 0
        if over.any():
            shape = 1.0 / ph[over]
            sub[:, over] *= rng.gamma(shape[None, :], ph[over][None, :], size=(n, int(over.sum()))).astype(np.float32)
        counts = rng.poisson(sub).astype(np.float32)
        tot = counts.sum(axis=1)
        hot = tot > max_counts_per_cell
        if hot.any():
            counts[hot] = np.floor(counts[hot] * (max_counts_per_cell / tot[hot])[:, None])
        if max_stored_per_cell is not None:
            nnz = (counts > 0).sum(axis=1)
            for i in np.flatnonzero(nnz > max_stored_per_cell):
                keep = np.argpartition(counts[i], -max_stored_per_cell)[-max_stored_per_cell:]
                row = np.zeros_like(counts[i])
                row[keep] = counts[i][keep]
                counts[i] = row
        r, c = np.nonzero(counts)
        full = sp.csr_matrix((counts[r, c], (r, cols[c])), shape=(n, lam.shape[1]), dtype=np.float32)
        full.sort_indices()
        return full
