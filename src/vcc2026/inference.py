"""From a predicted log2 fold change to the raw counts a submission contains.

The scorer reads counts (`input_type: counts`, `control_source: real`), so the
step from a response estimate to a submitted matrix is not a formality -- it
decides four of the six metrics through the dispersion it creates. Three things
in it are easy to get silently wrong, and each has an explicit answer here.

**The compositional constraint.** A predicted log2 fold change is a statement
about relative abundance, and a cell's counts are a composition: they cannot all
go up. Rescaling `basal * 2**delta` to a library size therefore divides out a
global factor, and that factor lands on *every* gene -- including the ones the
source never measured, which were supposed to carry no prediction at all. Left
alone, a source that measures 7,681 of 18,533 genes would quietly shift the
other 10,852 in one direction across all 300 perturbations. `compositional_shift`
solves for the scalar that keeps total mass fixed, in closed form, so the
unmeasured genes realise *exactly* zero change and the shift is absorbed by the
genes that do carry a prediction. The shift is reported per target rather than
hidden, because it is a real modification of the prediction.

**The no-effect fallback is not a measured zero (D-009).** A target no source
covers, and a gene no source measures, get zero predicted change because there
is nothing to predict from. That is a fallback. `SupportMask` carries the
distinction into the diagnostics so a report cannot describe missing evidence as
an observed null.

**Sampling from a pooled mean is not sampling a cell.** The mean profile over
18,400 control cells is far less sparse than any one of those cells, so Poisson
draws from it produce cells with more detected genes and less cell-to-cell
spread than the real thing. That is a systematic artefact of the generator,
present even when the predicted effect is exactly zero, and
`count_generation_diagnostics` measures it against the real control cells
instead of assuming it away.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import h5py
import numpy as np
import scipy.sparse as sp

__all__ = [
    "BasalProfile",
    "SupportMask",
    "read_basal_profile",
    "read_csr_rows",
    "compositional_shift",
    "predicted_profile",
    "count_generation_diagnostics",
    "profile_similarity",
    "nearest_basal_context",
]


@dataclass
class BasalProfile:
    """A context's unperturbed state, as the generator needs it.

    Attributes:
        context: official context label (A/B/C), read from the control file.
        profile: (n_genes,) summed counts over the control cells. Only ratios
            matter downstream, so a sum is kept rather than a mean.
        library_sizes: (n_cells,) per-cell total counts of the real controls.
            Resampled to give predicted cells the observed depth distribution.
        n_cells: control cells behind the profile.
        nnz_per_cell: (n_cells,) detected genes per real control cell, the
            reference the generated cells are compared against.
    """

    context: str
    profile: np.ndarray
    library_sizes: np.ndarray
    n_cells: int
    nnz_per_cell: np.ndarray
    source_path: str = ""

    @property
    def n_genes(self) -> int:
        return int(self.profile.size)

    def summary(self) -> dict:
        lib = self.library_sizes
        nnz = self.nnz_per_cell
        return {
            "context": self.context,
            "n_cells": self.n_cells,
            "n_genes": self.n_genes,
            "total_counts": float(self.profile.sum()),
            "median_library_size": float(np.median(lib)),
            "mean_library_size": float(lib.mean()),
            "median_nnz_per_cell": float(np.median(nnz)),
            "genes_with_any_count": int((self.profile > 0).sum()),
            "source_path": self.source_path,
        }


@dataclass
class SupportMask:
    """What the model could and could not speak to, kept out of the matrix.

    `covered_targets` are targets some source measured. `gene_observed` is the
    per-gene mask of the source's universe. Everything outside either is a
    no-effect *fallback*, never an observation (D-009).
    """

    requested_targets: tuple[str, ...]
    covered_targets: tuple[str, ...]
    gene_observed: np.ndarray
    per_target: dict = field(default_factory=dict)

    @property
    def uncovered_targets(self) -> tuple[str, ...]:
        covered = set(self.covered_targets)
        return tuple(t for t in self.requested_targets if t not in covered)

    def summary(self) -> dict:
        return {
            "n_requested_targets": len(self.requested_targets),
            "n_covered_targets": len(self.covered_targets),
            "n_uncovered_targets": len(self.uncovered_targets),
            "uncovered_targets": list(self.uncovered_targets),
            "n_genes_observed_by_source": int(self.gene_observed.sum()),
            "n_genes_unobserved_by_source": int((~self.gene_observed).sum()),
            "fallback_semantics": (
                "An uncovered target and an unobserved gene both receive a "
                "no-effect prediction because no evidence is available. This is "
                "a fallback, NOT a measured null effect (D-009)."
            ),
        }


def read_basal_profile(
    path: Path | str,
    *,
    context: str | None = None,
    block_rows: int = 2000,
) -> BasalProfile:
    """Summed profile, library sizes and detection counts of a control file.

    The matrix is read in row blocks and never materialised: one control file
    holds ~110M stored values, about 880 MB as an in-memory CSR, which does not
    fit beside anything else on a 7.8 GiB machine.
    """
    path = Path(path)
    with h5py.File(path, "r") as f:
        n_cells, n_genes = (int(v) for v in f["X"].attrs["shape"])
        indptr = f["X/indptr"][:].astype(np.int64)
        data_ds, idx_ds = f["X/data"], f["X/indices"]

        if context is None:
            cats = f["obs/context/categories"].asstr()[:]
            codes = f["obs/context/codes"][:]
            uniq = sorted({str(cats[c]) for c in np.unique(codes)})
            if len(uniq) != 1:
                raise ValueError(f"{path}: expected one context, found {uniq}")
            context = uniq[0]

        profile = np.zeros(n_genes, dtype=np.float64)
        lib = np.zeros(n_cells, dtype=np.int64)
        nnz = np.zeros(n_cells, dtype=np.int32)

        for start in range(0, n_cells, block_rows):
            stop = min(start + block_rows, n_cells)
            lo, hi = int(indptr[start]), int(indptr[stop])
            values = data_ds[lo:hi].astype(np.float64)
            columns = idx_ds[lo:hi]
            np.add.at(profile, columns, values)
            bounds = indptr[start : stop + 1] - lo
            for i in range(stop - start):
                seg = values[bounds[i] : bounds[i + 1]]
                lib[start + i] = int(seg.sum())
                nnz[start + i] = seg.size

    return BasalProfile(
        context=str(context),
        profile=profile,
        library_sizes=lib,
        n_cells=n_cells,
        nnz_per_cell=nnz,
        source_path=str(path),
    )


def read_csr_rows(
    path: Path | str, rows, n_genes: int, *, indptr: np.ndarray | None = None
) -> sp.csr_matrix:
    """Read the given rows of a CSR h5ad, in the order requested.

    Duplicates are allowed and preserved -- resampling real control cells with
    replacement is the point of the control baseline -- and the requested order
    is preserved, so a caller can record which source cell produced which
    output row.
    """
    rows = np.asarray(rows, dtype=np.int64)
    unique, inverse = np.unique(rows, return_inverse=True)
    with h5py.File(path, "r") as f:
        if indptr is None:
            indptr = f["X/indptr"][:].astype(np.int64)
        data_ds, idx_ds = f["X/data"], f["X/indices"]
        blocks, cols, lengths = [], [], np.empty(unique.size, dtype=np.int64)
        for i, r in enumerate(unique):
            lo, hi = int(indptr[r]), int(indptr[r + 1])
            blocks.append(data_ds[lo:hi])
            cols.append(idx_ds[lo:hi])
            lengths[i] = hi - lo

    uniq_indptr = np.zeros(unique.size + 1, dtype=np.int64)
    np.cumsum(lengths, out=uniq_indptr[1:])
    uniq_data = np.concatenate(blocks) if blocks else np.empty(0, dtype=np.float32)
    uniq_cols = np.concatenate(cols) if cols else np.empty(0, dtype=np.int32)

    out_lengths = lengths[inverse]
    out_indptr = np.zeros(rows.size + 1, dtype=np.int64)
    np.cumsum(out_lengths, out=out_indptr[1:])
    take = np.concatenate(
        [np.arange(uniq_indptr[j], uniq_indptr[j + 1]) for j in inverse]
    ) if rows.size else np.empty(0, dtype=np.int64)

    return sp.csr_matrix(
        (
            uniq_data[take].astype(np.float32),
            uniq_cols[take].astype(np.int32),
            out_indptr,
        ),
        shape=(rows.size, n_genes),
    )


def compositional_shift(
    basal: np.ndarray, delta: np.ndarray, observed: np.ndarray
) -> float:
    """The scalar log2 shift that preserves total mass on observed genes only.

    Counts are a composition, so `basal * 2**delta` renormalised to a library
    size realises `delta + c` for every gene, with `c` the global factor
    renormalisation removes. Solving for the `c` that keeps total mass fixed,

        sum_obs b_i * 2**(d_i + c) + sum_mask b_i = sum_all b_i

    reduces in closed form to

        c = log2( sum_obs b_i / sum_obs b_i * 2**d_i )

    after which an unobserved gene keeps its exact share of the composition --
    a realised log2 fold change of zero, not of `-c`. Returns 0.0 when no gene
    is observed or the observed mass is zero.
    """
    basal = np.asarray(basal, dtype=np.float64)
    observed = np.asarray(observed, dtype=bool)
    if not observed.any():
        return 0.0
    b = basal[observed]
    d = np.asarray(delta, dtype=np.float64)[observed]
    mass_flat = float(b.sum())
    mass_moved = float(np.sum(b * np.exp2(d)))
    if mass_flat <= 0 or mass_moved <= 0:
        return 0.0
    return float(np.log2(mass_flat / mass_moved))


def predicted_profile(
    basal: np.ndarray,
    delta: np.ndarray,
    observed: np.ndarray,
    *,
    clip_log2: float = 6.0,
) -> tuple[np.ndarray, dict]:
    """Apply a predicted log2 fold change to a basal profile.

    Args:
        basal: (n_genes,) summed control counts. Not modified.
        delta: (n_genes,) predicted log2 fold change.
        observed: (n_genes,) True where the prediction is supported by evidence.
        clip_log2: symmetric bound on |delta| before exponentiation. 2**6 = 64x
            is already far outside anything the calibrated transfer produces, so
            this guards against a numerical accident, not against biology; the
            count of clipped genes is reported.

    Returns:
        (profile, detail). `profile` is non-negative and sums to the same total
        as `basal`, so the composition of the unobserved genes is untouched.
    """
    basal = np.asarray(basal, dtype=np.float64)
    delta = np.asarray(delta, dtype=np.float64)
    observed = np.asarray(observed, dtype=bool)
    if not (basal.shape == delta.shape == observed.shape):
        raise ValueError(
            f"shape mismatch: {basal.shape} / {delta.shape} / {observed.shape}"
        )
    if np.any(basal < 0):
        raise ValueError("basal profile must be non-negative")

    effective = np.where(observed, delta, 0.0)
    n_clipped = int(np.sum(np.abs(effective) > clip_log2))
    effective = np.clip(effective, -clip_log2, clip_log2)

    shift = compositional_shift(basal, effective, observed)
    shifted = np.where(observed, effective + shift, 0.0)
    profile = basal * np.exp2(shifted)

    total_basal = float(basal.sum())
    total_pred = float(profile.sum())
    detail = {
        "compositional_shift_log2": shift,
        "n_genes_clipped": n_clipped,
        "clip_log2": clip_log2,
        "mass_ratio_pred_over_basal": (
            total_pred / total_basal if total_basal > 0 else None
        ),
        "realised_log2fc_on_unobserved": 0.0,
        "median_abs_effective_log2fc_observed": (
            float(np.median(np.abs(shifted[observed]))) if observed.any() else 0.0
        ),
        "max_abs_effective_log2fc_observed": (
            float(np.max(np.abs(shifted[observed]))) if observed.any() else 0.0
        ),
    }
    return profile, detail


def count_generation_diagnostics(
    generated: sp.csr_matrix, basal: BasalProfile
) -> dict:
    """Compare generated cells with the real control cells they imitate.

    The comparison that matters is not "are the counts whole" -- the writer
    already enforces that -- but whether the generator's cells look like cells.
    Poisson draws from a pooled mean lose two things at once: zero inflation
    (so more genes are detected) and between-cell biological spread (so the
    within-group variance the DE test is measured against is too small). Both
    are present when the predicted effect is exactly zero, which is why they are
    measured against the real controls rather than argued about.
    """
    generated = generated.tocsr()
    nnz_gen = np.asarray(generated.getnnz(axis=1), dtype=np.float64)
    lib_gen = np.asarray(generated.sum(axis=1), dtype=np.float64).ravel()
    nnz_real = np.asarray(basal.nnz_per_cell, dtype=np.float64)
    lib_real = np.asarray(basal.library_sizes, dtype=np.float64)

    def _cv(x):
        return float(x.std() / x.mean()) if x.size and x.mean() > 0 else None

    return {
        "n_cells_generated": int(generated.shape[0]),
        "median_nnz_generated": float(np.median(nnz_gen)) if nnz_gen.size else None,
        "median_nnz_real_controls": float(np.median(nnz_real)),
        "nnz_ratio_generated_over_real": (
            float(np.median(nnz_gen) / np.median(nnz_real))
            if nnz_gen.size and np.median(nnz_real) > 0
            else None
        ),
        "median_library_generated": float(np.median(lib_gen)) if lib_gen.size else None,
        "median_library_real_controls": float(np.median(lib_real)),
        "cv_library_generated": _cv(lib_gen),
        "cv_library_real_controls": _cv(lib_real),
        "cv_nnz_generated": _cv(nnz_gen),
        "cv_nnz_real_controls": _cv(nnz_real),
        "interpretation": (
            "A generated/real nnz ratio above 1 is the expected artefact of "
            "sampling from a pooled mean: the mean profile is less sparse than "
            "any single cell. It is present at zero predicted effect and is a "
            "property of the generator, not of the prediction."
        ),
    }


def profile_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity of two profiles on a log1p-CPM scale.

    CPM removes the depth difference between a pooled control profile and a
    block of 400 generated cells; log1p keeps a handful of very high-expression
    genes from deciding the answer on their own.
    """
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {a.shape} / {b.shape}")
    sa, sb = a.sum(), b.sum()
    if sa <= 0 or sb <= 0:
        return float("nan")
    la = np.log1p(1e6 * a / sa)
    lb = np.log1p(1e6 * b / sb)
    na, nb = np.linalg.norm(la), np.linalg.norm(lb)
    if na == 0 or nb == 0:
        return float("nan")
    return float(la @ lb / (na * nb))


def nearest_basal_context(
    observed_profile: np.ndarray, basals: dict[str, np.ndarray]
) -> tuple[str, dict[str, float]]:
    """Which context's basal state a block of predicted cells resembles most.

    Format validation cannot detect swapped context labels: the challenge FAQ
    states that if two contexts are exchanged "every metric degrades toward
    chance and the result looks like a weak model rather than a bug". Since
    every prediction here is built from one context's own controls, the nearest
    basal profile must be the context the block claims -- which makes this a
    real detector rather than a formality.
    """
    scores = {
        ctx: profile_similarity(observed_profile, prof) for ctx, prof in basals.items()
    }
    best = max(scores, key=lambda k: (-np.inf if np.isnan(scores[k]) else scores[k]))
    return best, scores
