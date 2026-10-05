"""Native reimplementation of the VCC ``prep`` pipeline.

Produces a ``.vcc`` (an uncompressed tar carrying ``meta.json`` and ``pred.h5ad.zst``)
from a raw ``.h5ad`` of predicted single-cell expression. This is functionally
equivalent to ``cell-eval prep`` but does **not** import cell-eval or scanpy — the
validate → slim → normalize → package logic is ported here, and zstd/tar are
vendored (``zstandard`` + stdlib ``tarfile``) so there is no shelling out to
system binaries (requirement P1).

cell-eval's ``src/cell_eval/_cli/_prep.py`` (``strip_anndata`` / ``_convert_to_normlog``)
and ``utils.guess_is_lognorm`` are the reference spec this module matches;
``.vcc`` output parity is guarded by tests.

Heavy imports (anndata/numpy/scipy/pandas/zstandard) live at module top on
purpose: this module is imported lazily, only when ``vcc prep`` runs, so it never
slows ``vcc --help`` / ``vcc version``.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tarfile
from dataclasses import dataclass, field
from tempfile import TemporaryDirectory
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
import zstandard as zstd
from scipy.sparse import csr_matrix, issparse

logger = logging.getLogger(__name__)

# --- Defaults (match cell-eval, except MAX_CELL_DIM — see below) -------------
DEFAULT_PERT_COL = "target_gene"
DEFAULT_CELLTYPE_COL = "celltype"
DEFAULT_NTC_NAME = "non-targeting"

# 2026 gene axis (was 18,080 in 2025). Must match gene_names.csv shipped in the
# controls bundle; a mismatch only warns and adopts the gene list's length.
EXPECTED_GENE_DIM = 18533

# --- 2026 cell contexts -------------------------------------------------------
# A submission is ONE file covering every cell context. Each cell carries the
# context it was predicted for, reusing the label from the control files — that
# round-trip is what lets the scorer pair a prediction with the right ground
# truth. Enforced here so a participant finds out before a multi-GB upload, and
# again server-side during scoring, because prep runs on their machine.
DEFAULT_CONTEXT_COL = "context"
REQUIRED_CONTEXTS = ("A", "B", "C")

# Matches a construct's guide suffix (`ADNP-1`). Used ONLY to recognise the most
# common wrong-label mistake and say so by name — prep never strips it, since the
# published labels are already gene symbols.
_GUIDE_SUFFIX = re.compile(r"-\d$")

# 3 contexts x 300 constructs x 400 cells = 360,000 perturbed cells. The 2025 cap
# of 100,000 would reject every valid 2026 submission. Set --max-cell-dim -1 to
# disable.
#
# ⚠️ 400,000 was sized against the EARLIER 200x500 panel (300,000 cells) and left
# 33% headroom; against the approved 300x400 panel it leaves 11%. Still correct,
# but it is now much closer to the real shape than the number suggests — re-check
# before shrinking it, and note participants may legitimately include their own
# control cells (prep rejects those, but the cap is checked first).
MAX_CELL_DIM = 400000

# The panel's uniform per-perturbation cell count. `pert_counts.csv` is now a bare
# list of the 300 perturbations, so this is where the number lives on the client.
#
# ⚠️ It is a hardcoded panel constant, which is exactly what this file used to avoid:
# the panel moved 500 -> 400 during design, and a hardcoded 500 would have rejected
# every correct submission while telling participants to emit the wrong count. Two
# things keep that from happening again, and BOTH must stay:
#   1. `scripts/prepare_competition_data.py` computes the real per-construct count
#      from the archives and FAILS THE BUNDLE BUILD if it is not this number
#      (`EXPECTED_CELLS_PER_PERT` there) — months before a participant sees it.
#   2. `--cells-per-pert N` overrides it, so a panel change needs a flag, not a CLI
#      release.
# The authority is still the held-out data: the scoring job derives its expectation
# from the ground truth and never reads this file.
# An explicit `n_cells` column in a perts file still wins over this constant, so a
# pre-2026 three-column file keeps behaving exactly as it did.
EXPECTED_CELLS_PER_PERT = 400
VALID_ENCODINGS = (32, 64)
from vcc import sizing
from vcc import __version__
from vcc.vccfile import (  # shared with submit-side validation
    META_MEMBER,
    META_SCHEMA,
    PRED_MEMBER,
)

# Density ceiling, the SERVER'S number (see vcc/sizing.py and scoring-limits.json).
# Separate from MAX_CELL_DIM because memory tracks nonzeros, not cells.
MAX_NNZ = sizing.HARD_CAP_NNZ

# Per-cell count cap: cell_eval2's `max_counts_per_cell` (its vcc2026 preset sets it
# to 1e6). Scoring rejects any submission whose per-cell TOTAL — the sum of counts
# over all genes in one cell — exceeds this, via `check_scale_limit`. Nothing about
# such a matrix looks wrong (values are integral, finite, in range); a model emitting
# a plausible-but-too-large library size crosses it silently, so it is the least
# obvious of the rules and the one that most needs catching locally rather than after
# a multi-GB upload and a scoring run. The bound is `>`, so a cell totalling exactly
# 1e6 is allowed. `--max-counts-per-cell -1` disables it.
MAX_COUNTS_PER_CELL = 1_000_000


def _matrix_nnz(adata: "ad.AnnData") -> int | None:
    """Stored nonzeros in X once packaged, or None when it cannot be established.

    None means "do not judge" rather than 0, and a wrong REJECTION here is worse than a
    missed one — the server checks again from the file header.

    ⚠️ For a DENSE X this counts the NONZERO ELEMENTS, not ``x.size``. Packaging converts
    dense input to CSR (``X.tocsr() if issparse(X) else csr_matrix(X)``), and
    ``csr_matrix`` drops zeros, so the stored count in the resulting `.vcc` is
    ``count_nonzero`` — often far below the element count. Returning ``x.size`` would
    overstate a full dense panel as 6.67e9 "nonzeros" against a 4.75e9 cap and refuse a
    submission that packages to a fraction of that.

    This used to return None for any dense X, which meant such submissions skipped the
    density cap AND gave the server no size to route on. One pass over the array is
    cheap next to the write that follows it.
    """
    x = getattr(adata, "X", None)
    if x is None:
        return None
    nnz = getattr(x, "nnz", None)
    if nnz is not None:
        return int(nnz)
    try:
        return int(np.count_nonzero(np.asarray(x)))
    except (TypeError, ValueError):
        # An exotic array-like that numpy will not take: unknown beats a wrong number.
        return None

# AnnData attributes dropped during slimming; surfaced to the user (P5) so the
# data loss is never silent.
_DROPPABLE_ATTRS = ("layers", "obsm", "varm", "obsp", "varp", "uns")


class PrepError(Exception):
    """A user-facing validation/prep failure (bad input, not a bug).

    Raised with an actionable message; the CLI prints it without a traceback.
    """


@dataclass
class PrepResult:
    """Structured summary of a prep run (drives human and --json output)."""

    input: str
    output: str | None
    n_cells: int
    n_genes: int
    encoding: int
    pert_col: str
    output_pert_col: str
    celltype_col: str | None
    normalization: str  # "counts-preserved" | "already-lognorm" | "normalized-log1p" | "skipped-discrete"
    # Stored nonzeros in the prediction. Sent with the launch request, where it selects
    # the scoring machine -- memory tracks nonzeros, and neither the cell count nor the
    # compressed size predicts it. Counted for a dense X too, since packaging converts
    # it to CSR; None only when X is absent or numpy cannot read it.
    nnz: int | None = None
    context_col: str | None = None
    cells_per_context: dict[str, int] = field(default_factory=dict)
    verified_targets: bool = False
    dropped: list[str] = field(default_factory=list)
    reordered_genes: bool = False
    dry_run: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input": self.input,
            "output": self.output,
            "n_cells": self.n_cells,
            "nnz": self.nnz,
            "n_genes": self.n_genes,
            "encoding": self.encoding,
            "pert_col": self.pert_col,
            "output_pert_col": self.output_pert_col,
            "celltype_col": self.celltype_col,
            "normalization": self.normalization,
            "context_col": self.context_col,
            "cells_per_context": self.cells_per_context,
            "verified_targets": self.verified_targets,
            "dropped": self.dropped,
            "reordered_genes": self.reordered_genes,
            "dry_run": self.dry_run,
            # No "watermark" key: the member it reported no longer exists. The
            # archive is identified by carrying `pred.h5ad.zst`.
            "vcc_member": PRED_MEMBER,
            "notes": self.notes,
        }


# --- Normalization (ported from cell-eval / scanpy defaults) -----------------

def guess_is_lognorm(
    adata: ad.AnnData,
    epsilon: float = 1e-3,
    max_threshold: float = 15.0,
    validate: bool = True,
) -> bool:
    """Return True if X looks log-normalized already, False if integer counts.

    Educated guess based on whether stored values have a fractional component.
    Faithful port of cell-eval ``utils.guess_is_lognorm``: raises when decimals
    are present but the range is invalid (min < 0, or — when ``validate`` — max
    >= ``max_threshold``), which signals mixed/raw scales.
    """
    X = adata.X
    if X is None:
        raise PrepError("Input AnnData has no expression matrix (adata.X is None).")

    # An integer dtype cannot carry a fractional part, so skip the modf pass —
    # on a large dense matrix that pass allocates a full float copy.
    if np.issubdtype(getattr(X, "dtype", np.dtype(float)), np.integer):
        logger.info("Data has an integer dtype, so it is counts (no decimals possible).")
        return False

    if issparse(X):
        # Only CSR/CSC expose a numeric numpy `.data`. Check the format rather
        # than duck-typing `.data`: lil_matrix.data IS an ndarray, but of dtype
        # object (an array of lists), so an isinstance check passes and np.modf
        # then fails. AnnData only accepts CSR/CSC today, so this is defensive.
        if getattr(X, "format", None) not in ("csr", "csc"):
            X = X.tocsr()
        frac, _ = np.modf(X.data)
    elif getattr(adata, "is_view", False):
        frac, _ = np.modf(X.toarray() if hasattr(X, "toarray") else np.asarray(X))
    else:
        frac, _ = np.modf(np.asarray(X))

    has_decimals = bool(np.any(frac > epsilon))
    if not has_decimals:
        logger.info("Data appears to be integer counts (no decimal values detected).")
        return False

    if issparse(X):
        # Guard against an all-zero / empty stored-data matrix.
        max_val = float(X.data.max()) if X.data.size else 0.0
        min_val = float(X.data.min()) if X.data.size else 0.0
    else:
        arr = np.asarray(X.toarray() if hasattr(X, "toarray") else X)
        max_val = float(np.max(arr))
        min_val = float(np.min(arr))

    if min_val < 0:
        raise PrepError(
            f"Invalid scale: minimum value {min_val:.2f} is negative. "
            "Counts and log1p-normalized data must be >= 0."
        )
    if validate and max_val >= max_threshold:
        raise PrepError(
            f"Invalid scale: maximum value {max_val:.2f} exceeds the log1p threshold "
            f"of {max_threshold}. Expected log1p-normalized values in [0, {max_threshold}); "
            "values this large look like raw counts or a mixed scale. If your data is "
            "raw integer counts, prep will normalize it for you; if it is intentionally "
            "discrete, pass --allow-discrete."
        )
    logger.info(
        "Data appears to be log1p-normalized (decimals detected, range "
        f"[{min_val:.2f}, {max_val:.2f}])."
    )
    return True


def _normalize_total_to_median(X: csr_matrix) -> csr_matrix:
    """Scale each cell to the median total count (scanpy normalize_total default).

    Operates on a CSR matrix, preserving dtype. Cells with zero total are left
    untouched (they are all-zero rows). Matches scanpy's ``normalize_total`` with
    ``target_sum=None`` (target = median of per-cell totals over cells with count > 0).
    """
    counts = np.asarray(X.sum(axis=1)).ravel()
    nonzero = counts[counts > 0]
    if nonzero.size == 0:
        return X
    target = np.median(nonzero)
    safe = counts.copy()
    safe[safe == 0] = 1  # avoid divide-by-zero on empty cells
    scale = (target / safe).astype(X.dtype)
    # Row-scale by repeating each row's multiplier across its stored entries.
    per_row = np.diff(X.indptr)
    X.data *= np.repeat(scale, per_row)
    return X


def validate_contexts(
    adata: ad.AnnData,
    context_col: str,
    pert_col: str,
    ntc_name: str,
    required_contexts: tuple[str, ...],
) -> dict[str, int]:
    """Check the submission covers every cell context, and return the cell counts.

    The scorer evaluates each context against its own ground truth, so a missing
    context is not a partial score — it is an unscoreable submission. Catching it
    here saves the participant a multi-GB upload that would fail server-side.

    `ntc_name` is accepted for signature stability but no longer used: controls
    are rejected outright by `run_prep`, not required per context.
    """
    if context_col not in adata.obs:
        raise PrepError(
            f"Context column '{context_col}' is missing from adata.obs. Every cell must "
            f"carry the cell context it was predicted for ({', '.join(required_contexts)}), "
            "using the same labels as the `context` column in the control files you "
            "downloaded.\n"
            f"Available columns: {list(adata.obs.columns)}\n"
            "If your context column has a different name, pass --context-col."
        )

    values = adata.obs[context_col].astype(str)
    present = set(values.unique())

    unknown = sorted(present - set(required_contexts))
    if unknown:
        raise PrepError(
            f"Unknown context label(s) in '{context_col}': {', '.join(unknown)}.\n"
            f"Valid labels are {', '.join(required_contexts)} — reuse the labels from the "
            "control files exactly."
        )

    missing = [c for c in required_contexts if c not in present]
    if missing:
        raise PrepError(
            f"Submission is missing predictions for context(s): {', '.join(missing)}.\n"
            f"One .vcc must cover all {len(required_contexts)} contexts "
            f"({', '.join(required_contexts)}); found only {', '.join(sorted(present)) or 'none'}."
        )

    # Controls are NOT submitted (see the reject_controls check in run_prep): the
    # scorer pairs each context with the held-out data's own control cells. So the
    # only per-context requirement is that the context predicts something at all.
    counts: dict[str, int] = {}
    for context in required_contexts:
        mask = values == context
        n = int(mask.sum())
        if n == 0:
            raise PrepError(f"Context {context} has no cells.")
        counts[context] = n
    return counts


def _convert_to_normlog(adata: ad.AnnData, allow_discrete: bool) -> str:
    """Apply median normalize_total + log1p in place if X is integer counts.

    Returns the decision label. Mirrors cell-eval ``_convert_to_normlog``:
    - already log-norm  -> skip ("already-lognorm")
    - integer + allow_discrete -> skip ("skipped-discrete")
    - integer otherwise -> normalize_total(median) + log1p ("normalized-log1p")
    """
    if guess_is_lognorm(adata, validate=not allow_discrete):
        return "already-lognorm"
    if allow_discrete:
        logger.info("Discovered integer data; --allow-discrete set, skipping normalization.")
        return "skipped-discrete"

    logger.info("Discovered integer data; converting to norm-log (normalize_total + log1p).")
    X = adata.X
    X = X.tocsr() if issparse(X) else csr_matrix(X)
    # log1p writes back in place through out=X.data, which needs a FLOAT buffer.
    # The packaging path hands us X already cast to the float output encoding (the
    # astype in encode/slim), but the low-memory dry-run path (#476) validates the
    # ORIGINAL matrix — so an integer-dtype input reaches here still integer, and
    # both _normalize_total_to_median (which casts its scale back to X.dtype) and
    # np.log1p(out=X.data) then refuse the float→int same_kind cast (UFuncTypeError,
    # surfaced as an uncaught internal_error). Upcast integer data first: this is
    # exactly the float buffer packaging already gets, so it changes nothing there
    # (its X is float) and fixes --no-require-counts --dry-run on integer input.
    if np.issubdtype(X.data.dtype, np.integer):
        X = X.astype(np.float32)
    X = _normalize_total_to_median(X)
    np.log1p(X.data, out=X.data)  # natural log, in place (X.data is float here)
    adata.X = X
    return "normalized-log1p"


def _has_fractional_values(data: np.ndarray, epsilon: float = 1e-6) -> bool:
    """True if any value in ``data`` has a fractional part exceeding ``epsilon``.

    Scans in fixed-size blocks and early-exits on the first fractional value, so
    it never allocates a temporary the size of the whole array. ``np.modf`` over
    the full array allocates a SECOND full-length array (whose integral part is
    then discarded) — on a multi-GB prediction that is a full matrix copy, and
    part of what OOM-kills prep (#476). A value is whole iff it equals its
    truncation toward zero, which is exactly what modf's fractional part measures,
    so this returns the same answer at a bounded, block-sized memory cost.
    """
    block = 1 << 22  # 4Mi elements (~16 MB per bounded float32 temporary)
    for start in range(0, data.size, block):
        chunk = data[start : start + block]
        if np.any(np.abs(chunk - np.trunc(chunk)) > epsilon):
            return True
    return False


def _all_values_integer_of(X) -> bool:
    """True if every stored value in matrix ``X`` is a whole number.

    Mirrors cell_eval2 ``norm._is_all_integer``: an integer dtype short-circuits (it
    cannot carry a fractional part), and sparse implicit zeros are integers, so only
    the stored values matter. Deliberately about VALUES, not dtype — the ground-truth
    archives are ``float32`` holding whole numbers, and so is prep's own output.

    Takes the ALREADY-MATERIALIZED matrix rather than the AnnData so a caller
    validating a reordered AnnData view can read ``adata.X`` once and share it
    across checks — a view's ``.X`` re-materializes on every access, so re-fetching
    it per helper is a full extra matrix copy on the dry-run reorder path (#480).
    """
    if X is None:
        raise PrepError("Input AnnData has no expression matrix (adata.X is None).")
    if np.issubdtype(getattr(X, "dtype", np.dtype(float)), np.integer):
        return True
    if issparse(X):
        data = X.data if getattr(X, "format", None) in ("csr", "csc") else X.tocsr().data
    else:
        data = np.asarray(X.toarray() if hasattr(X, "toarray") else X).reshape(-1)
    if data.size == 0:
        return True
    # Chunked scan rather than np.modf over the whole array, which allocates a
    # second full-length array — a full matrix copy on a large prediction (#476).
    return not _has_fractional_values(data)


def _all_values_integer(adata: ad.AnnData) -> bool:
    """AnnData wrapper around :func:`_all_values_integer_of` (kept for existing
    call sites and tests). Prefer passing the materialized matrix when validating
    a view, so ``adata.X`` isn't re-materialized (#480)."""
    return _all_values_integer_of(adata.X)


def _min_value_of(X) -> float:
    """Smallest value in matrix ``X``, counting sparse implicit zeros.

    Takes the materialized matrix (see :func:`_all_values_integer_of`) so a view's
    ``.X`` is read once by the caller and shared, not re-materialized per check.
    """
    if issparse(X):
        data = X.data if getattr(X, "format", None) in ("csr", "csc") else X.tocsr().data
        if data.size == 0:
            return 0.0
        # An implicit zero is a real value, so a positive-only stored array still has
        # a minimum of 0 whenever any zero is implied.
        stored_min = float(data.min())
        return min(stored_min, 0.0) if data.size < (X.shape[0] * X.shape[1]) else stored_min
    arr = np.asarray(X.toarray() if hasattr(X, "toarray") else X)
    return float(arr.min()) if arr.size else 0.0


def _min_value(adata: ad.AnnData) -> float:
    """AnnData wrapper around :func:`_min_value_of` (kept for existing call sites
    and tests)."""
    return _min_value_of(adata.X)


def _require_counts(adata: ad.AnnData) -> str:
    """Assert X is raw counts and leave it untouched.

    This is a deliberate MIRROR of cell_eval2's ``norm.validate_input_type`` under
    ``input_type="counts"`` — the same two rejections, in the same order:

    1. any negative value              -> reject
    2. any non-whole value             -> reject (counts must be whole numbers)

    Matching matters because the scoring job runs cell_eval2 with
    ``allow_fractional_counts=False``, so anything prep lets through on these two
    rules is rejected server-side instead — after a multi-GB upload, as an opaque
    ``ValueError: declared input_type='counts' but values are fractional``.

    It replaces a ``guess_is_lognorm`` call, which was wrong in both directions:

    - It missed NEGATIVE integer counts entirely. ``guess_is_lognorm`` returns early
      (``return False``) when a matrix has no decimals, and its ``min < 0`` test sits
      *after* that return — so a matrix of whole numbers containing ``-3`` was
      reported as valid counts and shipped. Verified against the real function.
    - It called every fractional matrix "log-normalized", which is a guess prep cannot
      actually make: a model emitting 2.7 counts and a log1p matrix are
      indistinguishable by value inspection. That is exactly why cell_eval2 makes the
      caller DECLARE ``input_type`` and only validates consistency. The message now
      says what is true — the values are not whole — and names log-normalization as
      the likely cause rather than asserting it.
    """
    # Materialize X ONCE and hand it to both checks. A reordered AnnData is a
    # VIEW whose `.X` re-materializes the whole matrix on every access, so reading
    # it per-helper (as `_min_value(adata)` + `_all_values_integer(adata)` would)
    # is a second full matrix copy — exactly what the low-memory dry-run path is
    # meant to avoid on the gene-reorder path (#480).
    X = adata.X
    if X is None:
        raise PrepError("Input AnnData has no expression matrix (adata.X is None).")
    if _min_value_of(X) < 0:
        raise PrepError(
            "Submission contains NEGATIVE values, but counts must be non-negative.\n"
            "Scoring rejects a negative matrix outright (cell_eval2 `validate_input_type`).\n"
            "Clip or drop the negative predictions before prepping."
        )
    if not _all_values_integer_of(X):
        raise PrepError(
            "Submission values are FRACTIONAL, but submissions must be RAW INTEGER COUNTS.\n"
            "Scoring runs in counts space against counts ground truth and rejects a "
            "fractional matrix declared as counts.\n"
            "The usual cause is submitting log-normalized data — if so, submit the raw "
            "count matrix (e.g. adata.raw, or the layer you normalized from).\n"
            "If your model emits continuous values, round them to whole counts before prepping."
        )
    logger.info("Input is integer counts; preserving as-is (2026 scores in counts space).")
    return "counts-preserved"


# --- Gene list / input IO ----------------------------------------------------

# Header tokens tolerated as the first row of a gene list. No real gene symbol
# collides with these, so recognising them cannot silently drop a gene.
_GENE_LIST_HEADERS = frozenset({"gene_name", "gene", "gene_symbol", "gene_names", "genes"})


def read_gene_list(path: str) -> list[str]:
    """Read a CSV of expected gene symbols (first column, in order).

    Accepts the file with or without a header row. The 2026 `gene_names.csv`
    shipped in the controls bundle HAS one (`gene_name`); read headerless it
    would yield 18,534 "genes" with the literal string `gene_name` first, and
    every submission would then fail the gene-set match with a baffling report.
    """
    if not os.path.exists(path):
        raise PrepError(f"Gene list not found: {path}")
    try:
        series = pd.read_csv(path, header=None).iloc[:, 0]
    except Exception as exc:  # noqa: BLE001 — EmptyDataError, ParserError, decode errors…
        raise PrepError(
            f"Could not read the gene list '{path}': {exc}.\n"
            "It must be a CSV with one gene symbol per row."
        ) from exc
    if series.empty:
        raise PrepError(f"The gene list '{path}' is empty.")
    genes = series.astype(str).tolist()
    if genes and genes[0].strip().lower() in _GENE_LIST_HEADERS:
        genes = genes[1:]
    if not genes:
        raise PrepError(f"The gene list '{path}' contains only a header row.")
    # Reject duplicates. A duplicated symbol whose set still matches the input
    # makes the reorder branch select that column twice (`adata[:, genelist]`),
    # producing a wrong-dimension .vcc with non-unique var_names — reported as
    # success, with a leaked AnnData UserWarning, and rejected only server-side
    # (#388). The input AnnData's own var_names are dedup-checked in run_prep; the
    # gene list must be too.
    seen: set[str] = set()
    dups = sorted({g for g in genes if g in seen or seen.add(g)})
    if dups:
        shown = ", ".join(dups[:10])
        more = f", … (+{len(dups) - 10} more)" if len(dups) > 10 else ""
        raise PrepError(
            f"The gene list '{path}' has {len(dups)} duplicate gene symbol(s): {shown}{more}.\n"
            "Each gene must appear exactly once, in order. Use the official gene_names.csv "
            "from `vcc datasets download controls`."
        )
    return genes


def read_pert_counts(
    path: str,
    pert_col: str = DEFAULT_PERT_COL,
    context_col: str = DEFAULT_CONTEXT_COL,
    ntc_name: str = DEFAULT_NTC_NAME,
    default_n_cells: int | None = EXPECTED_CELLS_PER_PERT,
) -> dict[str | None, dict[str, int | None]]:
    """Read the official perturbation list from ``pert_counts.csv``.

    Returns ``{context: {target_gene: n_cells}}``. The 2026 file is a bare list of
    the 300 perturbations — one ``target_gene`` column, no ``context`` and no
    ``n_cells`` — which yields a single ``None`` key that the caller applies to
    every context, with ``default_n_cells`` as each perturbation's count.

    A file that DOES state ``n_cells`` still wins: an explicit column is honoured
    per row (and a blank / non-positive value there still means "no expectation",
    unchanged), so a pre-2026 three-column file behaves exactly as it did. Pass
    ``default_n_cells=None`` to make a count-less file impose no expectation —
    which turns the cell-count check off, silently, for every perturbation.

    The control label is excluded — controls are not submitted at all.
    """
    if not os.path.exists(path):
        raise PrepError(
            f"Perturbation list not found: {path}\n"
            "Pass --perts with pert_counts.csv from the controls bundle "
            "(`vcc datasets download controls`)."
        )
    try:
        frame = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001 — EmptyDataError, ParserError, decode errors…
        raise PrepError(
            f"Could not read the perturbation list '{path}': {exc}.\n"
            "It must be a CSV with a '{pert_col}' column (and, for 2026, a "
            f"'{context_col}' column)."
        ) from exc

    if pert_col not in frame.columns:
        raise PrepError(
            f"Perturbation list '{path}' has no '{pert_col}' column. "
            f"Found: {list(frame.columns)}"
        )

    has_counts = "n_cells" in frame.columns

    def _rows(group) -> dict[str, int | None]:
        out: dict[str, int | None] = {}
        for _, row in group.iterrows():
            # Skip NaN/blank BEFORE stringifying: `str(nan)` is the string "nan",
            # which would become a perturbation named "nan" that no submission
            # can contain — so a single trailing comma or blank line in a
            # hand-edited pert_counts.csv would reject every valid submission.
            value = row[pert_col]
            if pd.isna(value):
                continue
            name = str(value).strip()
            if not name or name == ntc_name:
                continue
            # No n_cells column: the panel's uniform count stands in, so the check
            # stays ON. Leaving it None would skip _report_cell_count_mismatch for
            # every perturbation — the check would silently do nothing.
            n: int | None = default_n_cells
            if has_counts:
                try:
                    raw = row["n_cells"]
                    n = None if pd.isna(raw) else int(float(raw))
                except (TypeError, ValueError, OverflowError):
                    # OverflowError: int(float("1e309")) is int(inf). Non-finite
                    # n_cells otherwise escaped as a raw traceback (#421); treat it
                    # as "no usable count", same as an unparseable value.
                    n = None
            out[name] = n
        return out

    expected: dict[str | None, dict[str, int | None]] = {}
    if context_col in frame.columns:
        for context, group in frame.groupby(frame[context_col].astype(str)):
            expected[str(context)] = _rows(group)
    else:
        expected[None] = _rows(frame)

    if not any(expected.values()):
        raise PrepError(f"Perturbation list '{path}' contains no perturbations.")
    return expected


def validate_targets(
    adata: ad.AnnData,
    expected: dict[str | None, dict[str, int | None]],
    context_col: str,
    pert_col: str,
    ntc_name: str,
    required_contexts: tuple[str, ...],
    check_cell_counts: bool = True,
) -> None:
    """Check each context predicts exactly its official perturbations, at the
    stated number of cells each.

    Label set — both directions matter: a *missing* perturbation means an
    unscoreable hole in the submission, and an *unexpected* one is usually a sign
    the wrong column or the wrong label vocabulary was used (e.g. construct ids
    like ``ADNP-1`` instead of the gene symbol ``ADNP``), which would score as
    all-missing.

    Cell counts — the scorer computes differential expression for each predicted
    perturbation against the held-out controls, and compares that to the ground
    truth's own DE, which uses the panel's per-perturbation cell count
    (`EXPECTED_CELLS_PER_PERT`, or whatever an `n_cells` column states). Submitting
    a different number changes the statistical power of *one* side of that
    comparison, which moves the significance-based metrics. Since the submitter
    chooses it, it is a lever on their own score, so it is enforced rather than
    advertised.
    """
    if not required_contexts:
        # No contexts in play: validate the whole file against the single set.
        pool = expected.get(None) or {k: v for m in expected.values() for k, v in m.items()}
        observed = set(adata.obs[pert_col].astype(str)) - {ntc_name}
        _report_target_mismatch(None, observed, set(pool))
        return

    labels = adata.obs[pert_col].astype(str)
    values = adata.obs[context_col].astype(str)
    for context in required_contexts:
        want = expected.get(context, expected.get(None))
        if want is None:
            raise PrepError(
                f"The perturbation list has no entries for context {context}. "
                "Check you are using the pert_counts.csv from this season's controls bundle."
            )
        in_context = values == context
        observed = set(labels[in_context]) - {ntc_name}
        _report_target_mismatch(context, observed, set(want))

        if check_cell_counts:
            actual = labels[in_context].value_counts()
            _report_cell_count_mismatch(context, actual, want, ntc_name)


def _report_cell_count_mismatch(
    context: str,
    actual: "pd.Series",
    want: dict[str, int | None],
    ntc_name: str,
) -> None:
    """Report perturbations whose cell count differs from the official one."""
    wrong: list[tuple[str, int, int]] = []
    for gene, n_expected in sorted(want.items()):
        # A non-positive n_cells in a file that states one is not a usable
        # expectation — a perturbation cannot be predicted with 0 or -1 cells.
        # `vcc sample` also falls back to its own count for those rows, so holding
        # the submission to them would contradict the file the reference came from.
        # None only reaches here via --cells-per-pert -1 on a file with no n_cells
        # column; every other path has a concrete count (the panel constant).
        if n_expected is None or n_expected < 1 or gene == ntc_name:
            continue
        n_actual = int(actual.get(gene, 0))
        if n_actual != n_expected:
            wrong.append((gene, n_actual, n_expected))
    if not wrong:
        return

    shown = ", ".join(f"{g} has {a} (expected {e})" for g, a, e in wrong[:8])
    more = f", … (+{len(wrong) - 8} more)" if len(wrong) > 8 else ""
    expected_values = sorted({e for _, _, e in wrong})
    raise PrepError(
        f"Context {context}: {len(wrong)} perturbation(s) have the wrong number of cells.\n"
        f"  {shown}{more}\n"
        f"  Predict exactly {'/'.join(str(v) for v in expected_values)} cells for every "
        "perturbation in pert_counts.csv. The scorer compares your "
        "differential expression against the held-out data's, and a different cell count "
        "changes the statistical power of your side of that comparison."
    )


def _report_target_mismatch(context: str | None, observed: set[str], expected: set[str]) -> None:
    missing = expected - observed
    unexpected = observed - expected
    if not missing and not unexpected:
        return

    def sample(s: set[str], k: int = 10) -> str:
        items = sorted(s)[:k]
        more = f", … (+{len(s) - k} more)" if len(s) > k else ""
        return ", ".join(items) + more

    where = f"Context {context}: " if context else ""
    lines = [f"{where}perturbation labels do not match the official list."]
    if missing:
        lines.append(f"  {len(missing)} expected perturbation(s) not predicted: {sample(missing)}")
    if unexpected:
        lines.append(f"  {len(unexpected)} unexpected perturbation(s) present: {sample(unexpected)}")
    # The single most common cause, worth naming rather than leaving to guesswork.
    if unexpected and any(_GUIDE_SUFFIX.search(u) for u in unexpected):
        lines.append(
            "  Some labels look like construct ids (e.g. 'ADNP-1'). Submit the GENE SYMBOL "
            "('ADNP') — the guide suffix is not part of the label."
        )
    lines.append("  Each context must predict exactly the perturbations listed for it.")
    raise PrepError("\n".join(lines))


def validate_matrix_values(
    adata: ad.AnnData, pert_col: str, max_counts_per_cell: int | None = MAX_COUNTS_PER_CELL
) -> None:
    """Reject a prediction matrix that cannot produce a meaningful score.

    Both of these are silent killers: they upload and score fine, then come back
    as an unexplained bad number, so they are caught here instead.

    1. **NaN / inf.** Poisons every metric computed over the affected cells.
    2. **An all-zero perturbation.** Every cell zero across all genes for some
       perturbation almost always means the model did not actually run for it,
       rather than a real prediction of "no expression anywhere".

    A globally all-zero matrix is caught by (2) as well, since every perturbation
    in it is all-zero.
    """
    X = adata.X
    data = X.data if issparse(X) else np.asarray(X).ravel()

    # Sparse matrices only store non-zeros, so scanning .data is enough: a
    # structural zero is neither NaN nor inf.
    if data.size:
        bad = ~np.isfinite(data)
        n_bad = int(bad.sum())
        if n_bad:
            n_nan = int(np.isnan(data).sum())
            n_inf = n_bad - n_nan
            rows = _rows_with_nonfinite(X)
            where = ", ".join(str(r) for r in rows[:10])
            more = f" (and {len(rows) - 10} more)" if len(rows) > 10 else ""
            raise PrepError(
                f"Prediction matrix contains {n_bad} non-finite value(s): "
                f"{n_nan} NaN, {n_inf} inf.\n"
                f"First affected cell row(s): {where}{more}.\n"
                "Every metric computed over those cells would be meaningless, so this "
                "is refused before upload. Check the model output for divide-by-zero "
                "or an un-masked missing value."
            )

    # Per-cell totals (sum over genes), computed once and reused: the all-zero
    # perturbation check needs them, and so does the per-cell count cap below.
    totals = np.asarray(X.sum(axis=1)).ravel() if issparse(X) else np.asarray(X).sum(axis=1)

    # Per-cell count cap. Scoring rejects any cell whose total exceeds
    # `max_counts_per_cell` (cell_eval2's check_scale_limit); catch it here so a
    # too-large library size fails locally rather than after upload. The bound is
    # strict (`>`), matching scoring, so a cell at exactly the cap is allowed.
    if max_counts_per_cell and totals.size:
        worst = float(totals.max())
        if worst > max_counts_per_cell:
            over = int((totals > max_counts_per_cell).sum())
            worst_row = int(np.argmax(totals))
            # Keep a fractional part if there is one: this check runs before the
            # counts (integral) check, so a fractional total that is just over the
            # cap would otherwise round to the cap itself (e.g. 1000000.1 -> the
            # message reads "1,000,000", which looks like it is exactly at the cap).
            # 6 decimals so even a tiny overage still reads as over — finer than that
            # is below float precision near 1e6 and physically meaningless for counts.
            worst_fmt = f"{worst:,.6f}".rstrip("0").rstrip(".")
            raise PrepError(
                f"{over} cell(s) have a per-cell count total above the maximum of "
                f"{max_counts_per_cell:,} (worst: cell row {worst_row} totals "
                f"{worst_fmt} counts across all genes).\n"
                "Scoring rejects any cell whose counts sum above this cap, so it is "
                "refused before upload. Scale down the prediction (e.g. normalize each "
                "cell to a library size at or below the cap), or pass "
                "--max-counts-per-cell -1 to disable this check."
            )

    # A perturbation whose every cell is all-zero.
    labels = adata.obs[pert_col].astype(str).to_numpy()
    empty = sorted({lab for lab in np.unique(labels) if not totals[labels == lab].any()})
    if empty:
        shown = ", ".join(empty[:10])
        more = f" (and {len(empty) - 10} more)" if len(empty) > 10 else ""
        raise PrepError(
            f"{len(empty)} perturbation(s) have all-zero predictions across every gene "
            f"and every cell: {shown}{more}.\n"
            "That almost always means the model did not run for those perturbations. "
            "Re-run them, or drop them if they are not required."
        )


def _rows_with_nonfinite(X) -> list[int]:
    """Cell row indices holding a non-finite value, for the error message.

    Both branches already yield sorted, unique indices -- ``np.unique`` sorts, and
    ``np.nonzero`` over a per-row boolean returns each row at most once -- so no
    set/sort round-trip is needed.
    """
    if issparse(X):
        csr = X.tocsr()
        # Map each stored value back to its row via the CSR row pointers.
        rows = np.repeat(np.arange(csr.shape[0]), np.diff(csr.indptr))
        return np.unique(rows[~np.isfinite(csr.data)]).tolist()
    dense_bad = ~np.isfinite(np.asarray(X))
    return np.nonzero(dense_bad.any(axis=1))[0].tolist()


def read_h5ad(path: str) -> ad.AnnData:
    if not os.path.exists(path):
        raise PrepError(f"Input file not found: {path}")
    # Checked before opening: HDF5 does not fail cleanly on a directory. It
    # reports the errno inside a multi-line diagnostic carrying a file
    # descriptor, a timestamp and an internal buffer ADDRESS ("buf =
    # 0x16f24c2b0"), which then got wrapped and shown to the user as the CLI's
    # error message (#385). Everything else here is a one-liner, so match that.
    if os.path.isdir(path):
        raise PrepError(
            f"'{path}' is a directory, not a file. Pass the path to your .h5ad prediction."
        )
    try:
        return ad.read_h5ad(path)
    except Exception as exc:  # noqa: BLE001 — surface any read failure cleanly
        # Keep the first line only. h5py/HDF5 errors run to many lines of
        # internal detail; the first line is the actionable part.
        detail = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
        raise PrepError(f"Failed to read '{path}' as an .h5ad AnnData file: {detail}") from exc


def default_output_path(input_path: str) -> str:
    """Mirror cell-eval's default: ``<input>.h5ad`` -> ``<input>.prep.vcc``."""
    if input_path.endswith(".h5ad"):
        return input_path[: -len(".h5ad")] + ".prep.vcc"
    return input_path + ".prep.vcc"


def assert_output_distinct_from_inputs(
    output_path: str, inputs: list[tuple[str, str | None]]
) -> None:
    """Refuse an output path that resolves to one of the run's own inputs (#404).

    The exists-guard is bypassed by ``--force``, so ``-o pred.h5ad -f`` would
    irreversibly overwrite the very file being read — and the overwrite message is
    what tells the user to pass ``--force``. Compares real (symlink / ``..``
    resolved) paths, and is raised unconditionally: overwriting an input is never
    intended, so ``--force`` does not override it. Shared by ``prep`` and
    ``sample`` (single source of truth; also tolerates a realpath ``OSError``).
    """
    try:
        out_real = os.path.realpath(output_path)
    except OSError:
        return  # unresolvable path — the normal write path will report it
    for label, path in inputs:
        if not path:
            continue
        try:
            # `samefile` compares inode (st_dev/st_ino), so it catches a HARD LINK
            # alias and a case-only difference on a case-insensitive filesystem
            # (macOS APFS, Windows) that `realpath` string-comparison misses and
            # would let destroy the input. Fall back to the realpath comparison for
            # the common case where the output doesn't exist yet (samefile needs
            # both paths to exist). Raised in review (#404).
            same = (
                os.path.samefile(path, output_path)
                if os.path.exists(path) and os.path.exists(output_path)
                else os.path.realpath(path) == out_real
            )
        except OSError:
            continue
        if same:
            raise PrepError(
                f"Refusing to write the output over your {label} ({path}): the -o/--output "
                "path is the same file as an input, so it would be destroyed.\n"
                "Choose a different -o/--output path."
            )


# --- Packaging (vendored zstd + stdlib tar) ----------------------------------

# Past the process's real core count, zstd gains no throughput but costs a jobSize
# buffer per worker, so bound the worker count even on a genuinely large affinity mask.
_ZSTD_MAX_WORKERS = 8


def _zstd_worker_count() -> int:
    """Worker threads for zstd, bounded by the process's actual CPU affinity.

    ``os.sched_getaffinity`` reflects the affinity mask / cgroup that ``os.cpu_count``
    (what ``threads=-1`` uses) ignores; it's Linux-only, so fall back to ``cpu_count``
    on macOS/Windows. Capped at ``_ZSTD_MAX_WORKERS`` — each worker adds a jobSize
    buffer with no throughput gain past the real core count (#476).
    """
    try:
        available = len(os.sched_getaffinity(0))  # type: ignore[attr-defined]
    except AttributeError:
        available = os.cpu_count() or 1
    return max(1, min(available, _ZSTD_MAX_WORKERS))


def _write_vcc(minimal: ad.AnnData, output_path: str) -> int | None:
    """Write the ``.vcc``: tar( meta.json, pred.h5ad.zst ), and return the count written.

    A ``watermark.txt`` member holding the literal ``vcc-prep`` used to be written
    alongside the prediction. It was dropped: written by this same function, it only
    ever confirmed that prep had run -- which the presence of the prediction already
    says -- while giving a genuine submission an extra way to be rejected.

    ``meta.json`` is a different thing and earns its place: it carries the prediction's
    SHAPE, which is what the server sizes the scoring machine from. Without it the
    server must bound ``nnz`` from the h5ad header (a 256 KiB ranged read that
    overstates the count by ~50% for int64-indexed submissions) or, before that
    existed, simply escalate to its largest tier -- which is what 605 of 625 production
    jobs did.

    Written FIRST, deliberately, so it is readable from the first few KiB without
    touching the multi-GB payload. Nothing depends on member order:
    ``vccfile.validate_vcc`` and the scoring job's extractor both look the prediction
    up by NAME, and the server's probe walks the tar headers.

    ``nnz`` is counted from ``minimal`` -- the object actually being packaged -- rather
    than passed in from the caller's earlier count of the INPUT. Genes may have been
    dropped or reordered in between, and a figure that disagrees with the bytes in the
    archive is worse than none.

    It is RETURNED for the same reason. ``PrepResult.nnz`` is what `vcc submit` puts on
    the wire when prep and submit run in one invocation, and it used to carry the input
    count -- so the sidecar got the careful number and the launch request got the one this
    docstring argues against. They agree for the common sparse case and not always: the
    dense branch counts nonzeros at the INPUT dtype, while packaging does
    ``csr_matrix(np.asarray(X).astype(np.float32))``, and a float64 input with subnormal
    values loses them on the cast. One number, counted once, from the bytes that shipped.
    """
    with TemporaryDirectory() as tmp:
        h5ad_path = os.path.join(tmp, "pred.h5ad")
        zst_path = os.path.join(tmp, "pred.h5ad.zst")
        meta_path = os.path.join(tmp, META_MEMBER)

        minimal.write_h5ad(h5ad_path)

        packaged_nnz = _matrix_nnz(minimal)
        meta = {
            "schema": META_SCHEMA,
            "nnz": packaged_nnz,
            "n_obs": int(minimal.n_obs),
            "n_vars": int(minimal.n_vars),
            "cli_version": __version__,
        }
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, sort_keys=True)

        # zstd compress (vendored). Level/threads only affect the compressed
        # bytes, never the decompressed content the server reads. threads=-1 maps
        # (python-zstandard) to os.cpu_count(), which is NOT affinity- or cgroup-
        # aware: on a many-core shared node it spins one worker per logical CPU,
        # each holding a jobSize buffer — ~1.7 GB of peak on a 192-core box for no
        # throughput past the real core count, and the largest single allocation
        # left on the packaging path once #476 removed the redundant matrix copies.
        cctx = zstd.ZstdCompressor(level=3, threads=_zstd_worker_count())
        with open(h5ad_path, "rb") as src, open(zst_path, "wb") as dst:
            cctx.copy_stream(src, dst)
        os.remove(h5ad_path)

        # Uncompressed tar with the prediction at the archive root.
        #
        # Normalize the member metadata: tarfile would otherwise record the local
        # uid/gid, username, group name and mtime, which leaks the submitter's
        # account name into an uploaded artifact and makes the .vcc differ
        # byte-for-byte between machines for identical predictions.
        def _normalize(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
            tarinfo.uid = tarinfo.gid = 0
            tarinfo.uname = tarinfo.gname = ""
            tarinfo.mtime = 0
            return tarinfo

        with tarfile.open(output_path, "w") as tar:
            tar.add(meta_path, arcname=META_MEMBER, filter=_normalize)
            tar.add(zst_path, arcname=PRED_MEMBER, filter=_normalize)

    return packaged_nnz


# --- Orchestration -----------------------------------------------------------

def run_prep(
    *,
    input_path: str,
    genes_path: str,
    output_path: str | None = None,
    perts_path: str | None = None,
    verify_targets: bool = True,
    check_cell_counts: bool = True,
    cells_per_pert: int | None = EXPECTED_CELLS_PER_PERT,
    pert_col: str = DEFAULT_PERT_COL,
    celltype_col: str | None = None,
    ntc_name: str = DEFAULT_NTC_NAME,
    output_pert_col: str = DEFAULT_PERT_COL,
    output_celltype_col: str = DEFAULT_CELLTYPE_COL,
    context_col: str = DEFAULT_CONTEXT_COL,
    output_context_col: str = DEFAULT_CONTEXT_COL,
    required_contexts: tuple[str, ...] = REQUIRED_CONTEXTS,
    encoding: int = 32,
    allow_discrete: bool = False,
    require_counts: bool = True,
    reject_controls: bool = True,
    expected_gene_dim: int | None = EXPECTED_GENE_DIM,
    max_cell_dim: int | None = MAX_CELL_DIM,
    max_nnz: int | None = MAX_NNZ,
    max_counts_per_cell: int | None = MAX_COUNTS_PER_CELL,
    dry_run: bool = False,
    force: bool = False,
) -> PrepResult:
    """Validate, slim, normalize, and package an .h5ad into a .vcc.

    Returns a :class:`PrepResult`. Raises :class:`PrepError` on invalid input.
    """
    if encoding not in VALID_ENCODINGS:
        raise PrepError(f"Encoding must be one of {list(VALID_ENCODINGS)}, got {encoding}.")
    if cells_per_pert is not None and cells_per_pert < 1:
        # The CLI maps --cells-per-pert -1 to None (no built-in expectation); any
        # other non-positive value would quietly disable the check instead.
        raise PrepError("--cells-per-pert must be >= 1, or -1 for no built-in expectation.")
    if max_counts_per_cell is not None and max_counts_per_cell < 1:
        # The CLI maps --max-counts-per-cell -1 to None (disabled). Any OTHER
        # non-positive value would otherwise either silently disable the cap (0 is
        # falsy in the `if max_counts_per_cell` check below) or reject every cell
        # against a nonsense negative maximum, so reject it up front. Mirrors the
        # --cells-per-pert guard above.
        raise PrepError("--max-counts-per-cell must be >= 1, or -1 to disable the cap.")

    out = output_path or default_output_path(input_path)
    assert_output_distinct_from_inputs(
        out,
        [("input .h5ad", input_path), ("gene list", genes_path), ("perturbation list", perts_path)],
    )
    if not dry_run and os.path.exists(out) and not force:
        raise PrepError(
            f"Output already exists: {out}. Re-run with --force to overwrite, "
            "or choose a different -o/--output path."
        )

    adata = read_h5ad(input_path)
    if adata.X is None:
        raise PrepError(
            f"'{os.path.basename(input_path)}' has no expression matrix (adata.X is None), "
            "so there are no predictions to submit."
        )
    # Capture the input matrix's dtype + sparsity now, while `adata` is the real
    # backing object — a gene reorder below turns it into a VIEW whose `.X`
    # re-materializes on access, so reading these later would be a full matrix
    # copy. Used to size the memory warning: packaging only makes a second
    # matrix copy when the astype actually copies (see `will_copy` below).
    input_dtype = getattr(adata.X, "dtype", None)
    input_is_sparse = issparse(adata.X)

    genelist = read_gene_list(genes_path)

    notes: list[str] = []

    # Force var index to string (cell-eval does this first).
    adata.var.index = adata.var.index.astype(str)
    if adata.var_names.duplicated().any():
        raise PrepError("Duplicate gene names found in the input AnnData var_names.")

    # --- Validation (order matches cell-eval) ---
    # Check the shape first: with 0 cells the perturbation-column and NTC checks
    # below fail with a confusing message about a missing control label, when the
    # real problem is that there is nothing to submit.
    if adata.shape[0] == 0:
        raise PrepError(
            f"'{os.path.basename(input_path)}' contains 0 cells, so there is nothing to submit. "
            "Check that the file is the prediction you meant to prep."
        )
    if pert_col not in adata.obs:
        raise PrepError(
            f"Perturbation column '{pert_col}' is missing from adata.obs. "
            f"Available columns: {list(adata.obs.columns)}"
        )
    if celltype_col and celltype_col not in adata.obs:
        raise PrepError(
            f"Cell-type column '{celltype_col}' is missing from adata.obs. "
            f"Available columns: {list(adata.obs.columns)}"
        )
    perts = adata.obs[pert_col].unique()  # already a Series; no re-wrapping
    if reject_controls:
        # 2026: control cells must NOT be submitted. The scorer runs with
        # control_source="real" -- it substitutes the ground truth's own control
        # cells and uses only the prediction's non-control cells -- so submitted
        # controls are never read. Rejecting them here (rather than dropping them
        # quietly) keeps the contract honest: a participant who ships 10,500
        # predicted control cells per context would otherwise pay to upload
        # ~30,000 cells that are silently discarded, and might reasonably think
        # they were being scored on them.
        n_control = int((adata.obs[pert_col].astype(str) == ntc_name).sum())
        if n_control:
            raise PrepError(
                f"Submission contains {n_control} '{ntc_name}' control cell(s), but controls "
                "must NOT be submitted.\n"
                "Scoring uses the control cells from the held-out data, not yours, so predicted "
                "controls are never read.\n"
                f"Drop every cell whose '{pert_col}' is '{ntc_name}' and submit only your "
                "perturbation predictions."
            )
    elif ntc_name not in perts:
        raise PrepError(
            f"Negative-control label '{ntc_name}' not found in adata.obs['{pert_col}']. "
            f"Found {len(perts)} unique perturbations; expected one of them to be the control."
        )

    # Context coverage. Checked before the (expensive) gene reindex and encode so
    # a submission missing a context fails in seconds.
    cells_per_context: dict[str, int] = {}
    if required_contexts:
        cells_per_context = validate_contexts(
            adata, context_col, pert_col, ntc_name, required_contexts
        )

    # Perturbation labels, against the official list. Requires the reference file;
    # without it we would be checking nothing, so an omitted -p is an error rather
    # than a silently weaker prep (--no-verify-targets is the explicit opt-out).
    verified_targets = False
    if verify_targets:
        if not perts_path:
            raise PrepError(
                "Missing perturbation list, so target labels cannot be verified.\n"
                "Pass --perts with pert_counts.csv from the controls bundle "
                "(`vcc datasets download controls`), or --no-verify-targets to skip "
                "the check."
            )
        validate_targets(
            adata,
            # pert_counts.csv has a FIXED schema (`target_gene` + `context`, control
            # row `non-targeting`), so it is read with the official column names AND
            # the official control label — NOT the h5ad's -p/--pert-col, --context-col
            # or --ntc-name, which name things in the *prediction*. Passing the h5ad's
            # column made the official CSV unusable for anyone whose h5ad didn't call
            # its column `target_gene` (#399); passing the h5ad's control label left
            # the CSV's `non-targeting` row unfiltered under `--ntc-name NTC`, so it
            # became a required perturbation and failed a valid submission (#427).
            read_pert_counts(
                perts_path,
                DEFAULT_PERT_COL,
                DEFAULT_CONTEXT_COL,
                DEFAULT_NTC_NAME,
                # The 2026 file lists perturbations only; this is the count each
                # one must carry (--cells-per-pert overrides it, -1 drops it).
                default_n_cells=cells_per_pert,
            ),
            context_col,
            pert_col,
            ntc_name,
            required_contexts,
            check_cell_counts=check_cell_counts,
        )
        verified_targets = True
    else:
        notes.append(
            "Target labels were NOT verified against the official perturbation list "
            "(--no-verify-targets). A wrong label vocabulary will score as all-missing."
        )

    # Gene dimension: a genelist whose length disagrees with expected_gene_dim
    # just warns and adopts the genelist length (matches cell-eval).
    if expected_gene_dim and len(genelist) != expected_gene_dim:
        msg = (
            f"Provided gene list length ({len(genelist)}) does not match the expected "
            f"gene dimension ({expected_gene_dim}); using {len(genelist)}."
        )
        logger.warning(msg)
        notes.append(msg)
        expected_gene_dim = len(genelist)

    # Gene names must equal the list; same set in the wrong order is reordered,
    # missing/extra genes are a hard error (with a helpful report — P3).
    reordered = False
    if adata.var_names.tolist() != genelist:
        var_set = set(adata.var_names.tolist())
        gene_set = set(genelist)
        missing = gene_set - var_set  # expected but absent
        extra = var_set - gene_set  # present but unexpected
        if not missing and not extra:
            adata = adata[:, list(genelist)]
            reordered = True
            notes.append("Genes were present but out of order; reordered to match the gene list.")
            logger.info("Reordering genes to match the provided gene list.")
        else:
            raise PrepError(_gene_mismatch_message(missing, extra))

    if expected_gene_dim and adata.shape[1] != expected_gene_dim:
        raise PrepError(
            f"Gene dimension {adata.shape[1]} does not match the expected "
            f"dimension {expected_gene_dim}."
        )
    if max_cell_dim and adata.shape[0] > max_cell_dim:
        raise PrepError(
            f"Cell count {adata.shape[0]} exceeds the maximum of {max_cell_dim}. "
            "Subsample your prediction or pass --max-cell-dim -1 to disable the cap."
        )

    n_cells, n_genes = int(adata.shape[0]), int(adata.shape[1])

    # DENSITY, which is a SEPARATE ceiling from the cell count and not implied by it.
    # Scoring's memory tracks total NONZEROS: the submission that forced this check had
    # exactly the same 360,000 cells as every valid one — comfortably inside the cap
    # above — but twice the density, and it OOM-killed the scoring job four times over
    # while reporting nothing at all. Checked here so it costs a local subtraction
    # rather than a multi-GB upload and a 25-minute run.
    nnz = _matrix_nnz(adata)
    if max_nnz and nnz is not None and nnz > max_nnz:
        raise PrepError(sizing.too_dense_message(nnz, n_cells))

    # Heads-up (not a refusal) when packaging this prediction is likely to need
    # more RAM than the machine has, so a probable OOM-SIGKILL comes with a
    # message and a workaround rather than a silent death (#476). Emitted here,
    # before the value-touching validation and the encode/slim below, so the
    # warning precedes the memory-heavy work.
    if nnz is not None:
        # Packaging makes a second full-matrix copy UNLESS the astype can alias:
        # that only happens for a sparse, require_counts (2026 default) input whose
        # dtype already matches the output encoding — the common float32 case the
        # #476 fix made free (measured ~1.18x, not ~2x). Every other path (dtype
        # cast, dense→CSR conversion, or the in-place lognorm mutation) allocates a
        # real copy. Size the warning accordingly so a no-copy job isn't told it
        # needs ~2x the matrix and sent to a bigger machine for nothing (#480).
        target_dtype = np.dtype(np.float32 if encoding == 32 else np.float64)
        will_copy = not (
            input_is_sparse and require_counts and input_dtype == target_dtype
        )
        # A reordered input packages through an AnnData view whose materialization
        # adds a transient the copy term alone doesn't cover (#480); size for it so a
        # reordered submission near the RAM limit still gets the heads-up (#476).
        mem_warning = sizing.prep_memory_warning(
            nnz, n_cells, casts=will_copy, reordered=reordered
        )
        if mem_warning:
            logger.warning(mem_warning)

    # Matrix contents. Last of the hard checks, because it is the only one that
    # has to touch every stored value -- the cheap structural checks above have
    # already rejected the common mistakes by this point.
    #
    # The per-cell count cap mirrors cell_eval2's `check_scale_limit` for
    # `input_type="counts"`, so it only applies when the OUTPUT is raw counts
    # (`require_counts`, the 2026 default). Under `--no-require-counts` the matrix
    # is log-normalized ~40 lines below, so the submitted per-cell totals are ~log1p
    # values (single digits), nowhere near 1e6 — capping the RAW input there would
    # reject a submission whose actual output is five orders of magnitude under the
    # cap, and tell the user to "normalize each cell" when prep is about to do
    # exactly that. So the cap is gated off on the lognorm path (scoring's own
    # lognorm check compares expm1'd totals, not raw sums, anyway). The finite and
    # all-zero checks in validate_matrix_values still run in both modes.
    validate_matrix_values(adata, pert_col, max_counts_per_cell if require_counts else None)

    # --- Report data that slimming will drop (P5) ---
    dropped: list[str] = []
    for attr in _DROPPABLE_ATTRS:
        # Skip a None key: some anndata versions expose the implicit X "layer"
        # as a None key in adata.layers — that is not a dropped field.
        keys = [k for k in (getattr(adata, attr, {}) or {}) if k is not None]
        dropped.extend(f"{attr}[{k}]" for k in keys)
    if getattr(adata, "raw", None) is not None:
        dropped.append("raw")
    if dropped:
        logger.warning("Dropping (not carried into the .vcc): %s", ", ".join(dropped))

    # --- Scale validation ---
    # 2026 scores in counts space, so the default is to REQUIRE counts and leave
    # X alone; `require_counts=False` restores the historical log-normalizing
    # behaviour for prior-season data.
    #
    # On a DRY RUN, validate on the ORIGINAL matrix and return BEFORE the encode/
    # slim below, where packaging's astype copy + second AnnData roughly double
    # peak memory. This lowers the PACKAGING overhead, not the read: the file is
    # already fully resident by here, so a machine that OOMs during the read
    # itself is not helped — but it makes format-checking far lighter for the
    # common case where reading fits and only packaging doesn't (#476). Validating
    # on `adata` (not the float-cast copy) also lets the integer short-circuit in
    # _all_values_integer fire for genuine integer-count inputs.
    if dry_run:
        if require_counts:
            normalization = _require_counts(adata)
        else:
            normalization = _convert_to_normlog(adata, allow_discrete=allow_discrete)
        logger.info("Dry run: validated input, not writing output.")
        return PrepResult(
            input=input_path,
            output=None,
            n_cells=n_cells,
            n_genes=n_genes,
            nnz=nnz,
            encoding=encoding,
            pert_col=pert_col,
            output_pert_col=output_pert_col,
            celltype_col=celltype_col,
            normalization=normalization,
            context_col=context_col if required_contexts else None,
            cells_per_context=cells_per_context,
            verified_targets=verified_targets,
            dropped=dropped,
            reordered_genes=reordered,
            dry_run=True,
            notes=notes,
        )

    # --- Encode + slim (packaging only) ---
    dtype = np.float32 if encoding == 32 else np.float64
    X = adata.X
    # copy=False avoids duplicating the matrix when it is ALREADY the target dtype
    # (the common float32 case): `.astype` defaults to copy=True, a full extra
    # matrix in memory for no benefit (#476). We keep the copy ONLY on the lognorm
    # path, which mutates minimal.X in place (_convert_to_normlog) — copying there
    # means the mutation can never write through to the aliased adata.X, so
    # correctness is enforced at the mutation site rather than resting on adata
    # being discarded. The require_counts path (2026 default) never mutates X, so
    # it safely aliases and gets the full saving.
    copy_x = not require_counts
    new_x = (
        X.astype(dtype, copy=copy_x)
        if issparse(X)
        else csr_matrix(np.asarray(X).astype(dtype, copy=copy_x))
    )

    # adata.obs is a DataFrame, so these are already Series — no re-wrapping.
    new_obs = pd.DataFrame(
        {output_pert_col: adata.obs[pert_col].to_numpy()},
        index=np.arange(n_cells).astype(str),
    )
    if celltype_col:
        new_obs[output_celltype_col] = adata.obs[celltype_col].to_numpy()
    # The context label is load-bearing for scoring, so it is carried into the
    # .vcc rather than dropped with the rest of obs during slimming.
    if required_contexts:
        new_obs[output_context_col] = adata.obs[context_col].astype(str).to_numpy()
    new_var = pd.DataFrame(index=adata.var.index.values)

    minimal = ad.AnnData(X=new_x, obs=new_obs, var=new_var)

    if require_counts:
        normalization = _require_counts(minimal)
    else:
        normalization = _convert_to_normlog(minimal, allow_discrete=allow_discrete)

    try:
        packaged_nnz = _write_vcc(minimal, out)
    except OSError as exc:
        # Disk full, permission denied, read-only mount: report the path and the
        # reason instead of a traceback (R1 — every error names the next action).
        raise PrepError(
            f"Could not write '{out}': {exc}.\n"
            "Check the destination is writable and has enough free space, or pass a "
            "different -o/--output path."
        ) from exc

    return PrepResult(
        input=input_path,
        output=out,
        n_cells=n_cells,
        n_genes=n_genes,
        # The count that went INTO the archive, not the one taken off the input above.
        # Those are the same number for the common sparse case and not always (see
        # _write_vcc), and this one is both what the sidecar says and what `vcc submit`
        # sends to the launch endpoint -- so there is exactly one figure describing the
        # bytes a participant uploaded. Falls back to the input count only if the
        # packaged matrix could not be counted at all.
        nnz=packaged_nnz if packaged_nnz is not None else nnz,
        encoding=encoding,
        pert_col=pert_col,
        output_pert_col=output_pert_col,
        celltype_col=celltype_col,
        normalization=normalization,
        context_col=context_col if required_contexts else None,
        cells_per_context=cells_per_context,
        verified_targets=verified_targets,
        dropped=dropped,
        reordered_genes=reordered,
        dry_run=False,
        notes=notes,
    )


def _gene_mismatch_message(missing: set[str], extra: set[str]) -> str:
    """Actionable gene-mismatch report with counts and a small sample (P3)."""
    def sample(s: set[str], k: int = 10) -> str:
        items = sorted(s)[:k]
        more = f", … (+{len(s) - k} more)" if len(s) > k else ""
        return ", ".join(items) + more

    lines = ["Provided gene list does not match the AnnData gene names."]
    if missing:
        lines.append(f"  {len(missing)} expected gene(s) missing from the input: {sample(missing)}")
    if extra:
        lines.append(f"  {len(extra)} unexpected gene(s) present in the input: {sample(extra)}")
    lines.append(
        "  The input must contain exactly the genes in the list (order is fixed up automatically)."
    )
    return "\n".join(lines)
