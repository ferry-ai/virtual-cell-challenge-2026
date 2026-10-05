"""A per-target log fold change, assembled from single-cell evidence.

Three components, each with its own amplitude so a bench can dose them
separately:

* **same-target transfer** -- the target's own effect in a source context
  (K562 genome-wide), estimated from per-cell fractions with a between-cell
  standard error and empirical-Bayes shrinkage (`sc_effects`);
* **cis prior** -- CRISPRi represses promoters near the target's. The effect is
  learned from the source as a function of TSS distance (median over all
  source targets per distance bin) and applied to every gene of the output axis
  near the target, including genes the source never measured;
* **measured neighbours** -- where the source DID measure a gene near the
  target, its own effect is used at a separate, larger amplitude. Measured on
  2026-09-17 (K562 genome-wide pseudobulk against HepG2 single cells, same
  targets): neighbours within 1 kb correlate 0.57 across the two contexts and
  keep their sign in 98% of pairs with |log2FC| > 0.5 in K562 (n = 122), against
  a cross-lineage correlation of ~0.09 for the rest of the signature (CP-0003);
* **shared response** -- the mean effect over a set of source targets (the
  panel), i.e. the part of the response that does not depend on which target
  was hit.

Everything is in natural-log units of the per-cell-fraction ratio. Genes the
source does not measure get no transfer term (D-009: no evidence is not a zero
effect, so nothing is invented for them), but can still get the cis term.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .sc_effects import FractionStats, eb_shrink, log_effect

__all__ = ["SourceEffects", "CisModel", "effects_from_bulk", "effects_from_group_stats", "assemble_log_fc", "load_coordinates"]

NTC = "non-targeting"


@dataclass
class SourceEffects:
    genes: np.ndarray            # source gene symbols (unique)
    targets: list[str]
    shrunk: np.ndarray           # targets x genes, EB posterior mean (ln)
    raw: np.ndarray              # targets x genes, observed ln effect
    se: np.ndarray               # targets x genes
    n_cells: np.ndarray          # per target
    control_mean: np.ndarray     # mean fraction per gene in the source control
    meta: dict = field(default_factory=dict)

    def index(self) -> dict[str, int]:
        return {t: i for i, t in enumerate(self.targets)}


def effects_from_group_stats(stats: dict, groups: pd.DataFrame, gene_names: np.ndarray, *,
                             targets: list[str] | None = None, min_cells: int = 20,
                             min_control_mean: float = 1e-6) -> SourceEffects:
    """Effects for every target symbol from stage-71 accumulators (groups merged by symbol)."""
    gene_names = np.asarray(gene_names).astype(str)
    _, first = np.unique(gene_names, return_index=True)
    keep = np.sort(first)
    genes = gene_names[keep]
    n = np.asarray(stats["n_cells"], dtype=np.float64)
    # Kept as stored (float32, 11,258 x 8,248 each): only the rows a target uses are summed in
    # float64. Converting both matrices up front cost ~3 GB on a 12 GB runtime.
    fs = stats["frac_sums"]
    fq = stats["frac_sq_sums"]
    sym = groups["gene"].astype(str).to_numpy()
    is_ntc = groups["is_ntc"].to_numpy().astype(bool)

    def pooled(mask) -> FractionStats:
        rows = np.flatnonzero(mask)
        tot = n[rows].sum()
        mean = fs[rows].sum(axis=0, dtype=np.float64)[keep] / tot
        var = fq[rows].sum(axis=0, dtype=np.float64)[keep] / tot - mean**2
        return FractionStats(mean, np.maximum(var * tot / max(tot - 1, 1), 0.0), int(tot))

    ctrl = pooled(is_ntc)
    usable = ctrl.mean >= min_control_mean
    want = sorted(set(sym[~is_ntc])) if targets is None else [t for t in targets if t in set(sym[~is_ntc])]
    rows_s, rows_r, rows_se, ncell, kept = [], [], [], [], []
    for t in want:
        mask = (sym == t) & ~is_ntc
        tot = int(n[mask].sum())
        if tot < min_cells:
            continue
        st = pooled(mask)
        eff, se = log_effect(st, ctrl)
        shr, _ = eb_shrink(eff, se, usable & (st.mean > 0))
        rows_s.append(shr.astype(np.float32))
        rows_r.append(np.where(usable, eff, 0.0).astype(np.float32))
        rows_se.append(se.astype(np.float32))
        ncell.append(tot)
        kept.append(t)
    return SourceEffects(genes, kept, np.vstack(rows_s), np.vstack(rows_r), np.vstack(rows_se),
                         np.array(ncell), ctrl.mean, {"n_control_cells": ctrl.n})


def load_coordinates(path) -> pd.DataFrame:
    frame = pd.read_csv(path, sep="\t")
    return frame.drop_duplicates("symbol").set_index("symbol")


@dataclass
class CisModel:
    """Median source effect of a gene as a function of its TSS distance to the target's."""

    edges: tuple = (0, 1000, 2000, 5000, 10000, 20000)
    by_bin: np.ndarray | None = None       # ln effect per bin
    n_by_bin: np.ndarray | None = None

    def fit(self, src: SourceEffects, coords: pd.DataFrame, *, min_control_mean: float = 2e-5) -> "CisModel":
        gpos = {g: i for i, g in enumerate(src.genes)}
        expressed = src.control_mean >= min_control_mean
        chrom = coords["chrom"].astype(str)
        per_bin: list[list[float]] = [[] for _ in range(len(self.edges) - 1)]
        by_chrom = {c: sub for c, sub in coords.groupby(chrom)}
        for ti, t in enumerate(src.targets):
            if t not in coords.index:
                continue
            c, tss = str(coords.at[t, "chrom"]), int(coords.at[t, "tss"])
            sub = by_chrom[c]
            d = (sub["tss"] - tss).abs()
            near = sub[(d < self.edges[-1]) & (sub.index != t)]
            for g, dist in zip(near.index, (near["tss"] - tss).abs()):
                j = gpos.get(g)
                if j is None or not expressed[j]:
                    continue
                b = np.searchsorted(self.edges, dist, side="right") - 1
                per_bin[b].append(float(src.raw[ti, j]))
        self.by_bin = np.array([np.median(v) if v else 0.0 for v in per_bin])
        self.n_by_bin = np.array([len(v) for v in per_bin])
        return self

    @classmethod
    def from_pairs(cls, pairs: pd.DataFrame, *, value: str = "log2fc", log_base: float = 2.0,
                   edges: tuple = (0, 1000, 2000, 5000, 10000, 20000)) -> "CisModel":
        """Bins from a precomputed (dist, effect) table, e.g. stage 77's K562 neighbour pairs.

        Effects given in log base ``log_base`` are converted to natural log.
        """
        model = cls(edges=edges)
        d = pairs["dist"].to_numpy()
        v = pairs[value].to_numpy() * np.log(log_base)
        b = np.searchsorted(edges, d, side="right") - 1
        keep = (b >= 0) & (b < len(edges) - 1)
        model.by_bin = np.array([np.median(v[keep & (b == k)]) if np.any(keep & (b == k)) else 0.0
                                 for k in range(len(edges) - 1)])
        model.n_by_bin = np.array([int(np.sum(keep & (b == k))) for k in range(len(edges) - 1)])
        return model

    def neighbours(self, target: str, axis: np.ndarray, coords: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """(positions on `axis`, TSS distances) of the genes inside the model's window."""
        if target not in coords.index:
            return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
        c, tss = str(coords.at[target, "chrom"]), int(coords.at[target, "tss"])
        sub = coords[(coords["chrom"].astype(str) == c) & ((coords["tss"] - tss).abs() < self.edges[-1])]
        pos = pd.Index(np.asarray(axis).astype(str)).get_indexer(sub.index)
        keep = (pos >= 0) & (sub.index != target)
        return pos[keep], (sub["tss"] - tss).abs().to_numpy()[keep]

    def prior(self, dist: np.ndarray) -> np.ndarray:
        return self.by_bin[np.searchsorted(self.edges, dist, side="right") - 1]

    def vector(self, target: str, axis: np.ndarray, coords: pd.DataFrame) -> np.ndarray:
        out = np.zeros(len(axis), dtype=np.float64)
        if self.by_bin is None:
            return out
        pos, dist = self.neighbours(target, axis, coords)
        out[pos] = self.prior(dist)
        return out


def common_from_bulk(path, axis: np.ndarray, *, exclude=(), block: int = 400) -> tuple[np.ndarray, dict]:
    """The response a source's knockdowns share: mean EB-shrunk effect over its targets, on `axis`.

    Reads a Replogle ``*_raw_bulk_01.h5ad``, leaves out every target in `exclude` (the targets
    being predicted, so none of their own signal enters), and averages the rest in blocks to
    bound memory. Genes the source did not measure get 0. The same vector serves the benches
    (stages 73, 75) and the submission generator (stage 76).
    """
    import h5py

    from .sc_stream import read_frame

    with h5py.File(path, "r") as f:
        labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
        means = f["X"][:]
        cells = f["obs/num_cells_filtered"][:]
        names = read_frame(f["var"])["gene_name"].astype(str).to_numpy()
    ntc = np.array(["non-targeting" in lab for lab in labels])
    sym = np.array(["non-targeting" if nt else lab.split("_")[1] for lab, nt in zip(labels, ntc)])
    targets = sorted(set(sym[~ntc]) - set(map(str, exclude)))
    total, n, genes = None, 0, None
    for i in range(0, len(targets), block):
        eff = effects_from_bulk(means, cells, sym, ntc, names, targets=targets[i:i + block])
        s = eff.shrunk.astype(np.float64).sum(axis=0)
        total = s if total is None else total + s
        n += len(eff.targets)
        genes = eff.genes
    if not n:
        raise ValueError(f"no target left in {path} after excluding {len(set(exclude))}")
    axis = np.asarray(axis).astype(str)
    vec = np.zeros(axis.size)
    pos = pd.Index(axis).get_indexer(genes)
    vec[pos[pos >= 0]] = (total / n)[pos >= 0]
    return vec, {"source": str(path), "n_targets": n, "n_excluded": len(set(sym[~ntc]) & set(map(str, exclude))),
                 "n_genes_on_axis": int((pos >= 0).sum()), "rms_on_axis": float(np.sqrt((vec ** 2).mean()))}


def derangement(items: list[str], seed: int) -> dict[str, str]:
    """Map every item to a DIFFERENT item, as a random permutation with no fixed point.

    The target-identity control of the transfer benches: each target receives another
    target's source effect, which keeps the source's effect sizes, its call volume and
    whatever response all targets share, and removes only which target it is.
    """
    items = list(items)
    if len(items) < 2:
        raise ValueError("a derangement needs at least two items")
    rng = np.random.default_rng(seed)
    idx = np.arange(len(items))
    while True:
        perm = rng.permutation(len(items))
        if not np.any(perm == idx):
            return {items[i]: items[j] for i, j in zip(idx, perm)}


def assemble_log_fc(target: str, axis: np.ndarray, *, src: SourceEffects | None = None, a_transfer: float = 0.0,
                    use_raw: bool = False, cis: CisModel | None = None, coords: pd.DataFrame | None = None,
                    a_cis: float = 0.0, cis_mode: str = "fill", a_cis_measured: float = 0.0,
                    cis_measured_window: int = 5000, shared: np.ndarray | None = None,
                    a_shared: float = 0.0, clip: float = 3.0) -> np.ndarray:
    """ln fold change on `axis` for one target.

    Transfer puts ``a_transfer`` x the source effect on every gene the source measured.
    Inside ``cis_measured_window`` bp of the target's TSS, a gene the source measured is
    instead given ``a_cis_measured`` x its RAW source effect (when ``a_cis_measured`` is
    non-zero). The distance prior ``a_cis`` x median-by-bin then goes where the source has
    no measurement (``cis_mode='fill'``) or on top of everything (``'add'``). ``shared``
    must already be on `axis`.
    """
    axis = np.asarray(axis).astype(str)
    out = np.zeros(axis.size)
    have = np.zeros(axis.size, dtype=bool)
    ti = src.index().get(target) if src is not None else None
    src_pos = pd.Index(axis).get_indexer(src.genes) if src is not None else None
    if ti is not None and a_transfer:
        ok = src_pos >= 0
        vals = (src.raw if use_raw else src.shrunk)[ti][ok]
        out[src_pos[ok]] += a_transfer * vals
    if ti is not None:
        have[src_pos[src_pos >= 0]] = True
    if cis is not None and coords is not None and cis.by_bin is not None:
        npos, ndist = cis.neighbours(target, axis, coords)
        if a_cis_measured and ti is not None and npos.size:
            raw_on_axis = np.zeros(axis.size)
            ok = src_pos >= 0
            raw_on_axis[src_pos[ok]] = src.raw[ti][ok]
            close = (ndist <= cis_measured_window) & have[npos]
            out[npos[close]] = a_cis_measured * raw_on_axis[npos[close]]
        if a_cis and npos.size:
            prior = cis.prior(ndist)
            mask = ~have[npos] if cis_mode == "fill" else np.ones(npos.size, dtype=bool)
            out[npos[mask]] += a_cis * prior[mask]
    if shared is not None and a_shared:
        out += a_shared * shared
    return np.clip(out, -clip, clip)


def effects_from_bulk(means: np.ndarray, n_cells: np.ndarray, symbols: np.ndarray, is_ntc: np.ndarray,
                      gene_names: np.ndarray, *, targets: list[str] | None = None, phi: float = 0.2,
                      min_control_mean: float = 1e-6) -> SourceEffects:
    """Effects from a per-cell-MEAN pseudobulk (the Replogle `*_raw_bulk_01.h5ad` files).

    A fallback for when the single-cell accumulators are not available. The mean
    fraction is the mean-count profile normalized to one (the pooled functional, not the
    per-cell one), and the standard error is quasi-Poisson rather than measured:
    ``se^2 ~ (1/(n * mu) + phi / n)`` per side, with ``mu`` the mean count per cell and a
    fixed overdispersion ``phi``. Shrinkage is therefore only as good as that assumption.
    """
    gene_names = np.asarray(gene_names).astype(str)
    _, first = np.unique(gene_names, return_index=True)
    keep = np.sort(first)
    genes = gene_names[keep]
    symbols = np.asarray(symbols).astype(str)
    is_ntc = np.asarray(is_ntc, dtype=bool)
    all_targets = sorted(set(symbols[~is_ntc]))
    want = all_targets if targets is None else [t for t in targets if t in set(all_targets)]
    rows = np.flatnonzero(is_ntc | np.isin(symbols, want))  # convert only what is used
    x = np.asarray(means[rows], dtype=np.float64)[:, keep]
    n = np.where(np.isfinite(n_cells[rows]), n_cells[rows], 0).astype(np.float64)
    symbols, is_ntc = symbols[rows], is_ntc[rows]
    ctrl_mu = x[is_ntc].mean(axis=0)
    ctrl_frac = ctrl_mu / ctrl_mu.sum()
    n_ctrl = max(float(n[is_ntc].sum()), 1000.0)
    usable = ctrl_frac >= min_control_mean
    rows_s, rows_r, rows_se, ncell, kept = [], [], [], [], []
    for t in want:
        m = (symbols == t) & ~is_ntc
        tot = n[m].sum()
        if tot <= 0:
            continue
        mu = (x[m] * n[m, None]).sum(axis=0) / tot
        frac = mu / mu.sum()
        eff = np.log(np.maximum(frac, 1e-7)) - np.log(np.maximum(ctrl_frac, 1e-7))
        se = np.sqrt(1.0 / (tot * np.maximum(mu, 1e-3)) + phi / tot
                     + 1.0 / (n_ctrl * np.maximum(ctrl_mu, 1e-3)) + phi / n_ctrl)
        shr, _ = eb_shrink(eff, se, usable & (mu > 0))
        rows_s.append(shr.astype(np.float32))
        rows_r.append(np.where(usable, eff, 0.0).astype(np.float32))
        rows_se.append(se.astype(np.float32))
        ncell.append(int(tot))
        kept.append(t)
    return SourceEffects(genes, kept, np.vstack(rows_s), np.vstack(rows_r), np.vstack(rows_se),
                         np.array(ncell), ctrl_frac, {"n_control_cells": int(n_ctrl), "se_model": f"quasi-Poisson phi={phi}"})
