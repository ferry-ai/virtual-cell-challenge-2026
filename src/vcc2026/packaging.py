"""Validate and package a prediction into a ``.vcc`` in bounded memory.

Why this exists. `vcc prep` 0.2.0 is the authority on the submission format, and
this module does not try to replace it: it calls the official validators wherever
they take small data, and mirrors the rest check for check. What it does not do is
`ad.read_h5ad(path)`. That single line in `vcc/prep.py` materialises the whole
matrix before any validation runs, which on trial-01 means an 8.07 GiB allocation
for the indices array alone -- measured, on a 7.81 GiB machine, as
``Unable to allocate 8.07 GiB for an array with shape (2167562410,)``
(CP-0004 §3.5). The prediction is not too dense to score: at 2.167e9 stored entries
it is at 45.6% of the official cap. It is only too large to *read whole*.

So every pass here is a row-block pass over the CSR arrays, and the payload is
built by copying the input's X datasets dataset-to-dataset rather than through an
in-memory AnnData.

**What is preserved exactly.** The three X datasets -- ``data``, ``indices``,
``indptr`` -- are copied block by block with their dtypes and their HDF5 filters
intact. Their contents are bit-identical to the input's.

**What is transformed, and why.** Official prep slims the AnnData before writing:
obs keeps only the perturbation column, an optional cell-type column and the
context column, and its index is *replaced* with ``"0".."n-1"``; var keeps only the
gene index; ``layers``, ``obsm``, ``varm``, ``obsp``, ``varp``, ``uns`` and ``raw``
are dropped. This module applies exactly the same transformation, by rebuilding obs
and var through anndata's own writer so the encodings cannot drift from what
anndata produces. `payload_transformations()` returns the list, and the parity
tests assert our payload and the official payload read back identical.

**One documented divergence.** Official prep writes the payload through
``AnnData.write_h5ad``, which emits contiguous, unfiltered datasets: for trial-01
that is a ~19 GiB intermediate file before compression. Copying the input's
chunked, gzip-filtered datasets instead keeps the intermediate at roughly the input
size. Both decode to the same arrays -- ``assert_payloads_equivalent`` checks
exactly that -- and the density the server cares about is the stored-entry count,
which is unchanged and is what ``meta.json`` reports.

**What is refused rather than approximated.** A dense or non-CSR X, a dtype that
would need casting, genes out of order, a missing or extra gene, the
log-normalisation path, a cell-type column. Each raises with the reason and the
official tool as the alternative. A first implementation that silently
approximated any of these would be worse than one that stops.

Nothing here uploads anything.
"""

from __future__ import annotations

import json
import tarfile
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

__all__ = [
    "PackagingError",
    "LayoutReport",
    "ValidationReport",
    "PackageResult",
    "inspect_layout",
    "read_obs_frame",
    "validate_prediction",
    "write_payload",
    "archive_payload",
    "package_prediction",
    "payload_transformations",
    "assert_payloads_equivalent",
    "assert_payload_matches_input",
    "official",
]

# Stored values pulled into memory per block. 16Mi float32 values is 64 MiB for
# `data` and another 64 MiB for `indices`; the row-total and label-total
# accumulators are negligible beside them. Bounded on purpose: the whole point of
# this module is that peak memory does not scale with the prediction.
VALUES_PER_BLOCK = 1 << 24

_SUPPORTED_X_ENCODING = "csr_matrix"
_DROPPABLE_ATTRS = ("layers", "obsm", "varm", "obsp", "varp", "uns", "raw")


class PackagingError(Exception):
    """Input this module refuses to package, with the reason and the next step."""


def official():
    """The installed official modules, imported lazily.

    Imported through a function so this module can be inspected, and its pure
    helpers tested, on a machine where `vcc-cli` is not installed -- and so that
    the version actually in use is resolved at call time rather than at import.
    """
    from vcc import prep as prep_mod
    from vcc import sizing as sizing_mod
    from vcc import vccfile as vccfile_mod
    from vcc._version import __version__ as cli_version

    return prep_mod, vccfile_mod, sizing_mod, cli_version


def payload_transformations() -> list[str]:
    """Every way the packaged payload differs from the input file.

    Kept as data rather than prose so a report cannot claim "lossless" while a
    transformation goes unmentioned.
    """
    return [
        "obs index replaced with '0'..'n-1' (official prep rebuilds obs with a "
        "positional index; the original cell names are not carried into a .vcc)",
        "obs reduced to the perturbation column and the context column, in that "
        "order, written through anndata's own DataFrame writer",
        "var reduced to the gene index, with no columns",
        "layers, obsm, varm, obsp, varp, uns and raw dropped (official prep drops "
        "them too, and reports them)",
        "X datasets copied verbatim, preserving dtype and HDF5 filters. Official "
        "prep rewrites them contiguous and unfiltered; the decoded arrays are "
        "identical either way",
    ]


@dataclass
class LayoutReport:
    """The structural facts read from the file's header, before any pass."""

    path: str
    n_obs: int
    n_vars: int
    nnz: int
    data_dtype: str
    indices_dtype: str
    indptr_dtype: str
    data_chunks: tuple | None
    data_compression: str | None
    data_compression_opts: object
    indices_chunks: tuple | None
    indices_compression: str | None
    indices_compression_opts: object
    obs_columns: list[str]
    var_index_name: str
    droppable_present: list[str]
    file_bytes: int

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["data_chunks"] = list(self.data_chunks) if self.data_chunks else None
        d["indices_chunks"] = list(self.indices_chunks) if self.indices_chunks else None
        return d


@dataclass
class ValidationReport:
    """What every check saw. Empty `failures` is the only pass condition."""

    layout: LayoutReport
    n_obs: int
    n_vars: int
    nnz: int
    min_value: float
    max_value: float
    all_integer: bool
    n_nonfinite: int
    max_counts_per_cell_observed: float
    cells_per_context: dict
    n_targets_per_context: dict
    empty_perturbations: list[str]
    csr_checks: dict = field(default_factory=dict)
    checks: dict = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    seconds: float = 0.0
    peak_rss_bytes: int | None = None

    @property
    def ok(self) -> bool:
        return not self.failures

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "layout"}
        d["layout"] = self.layout.as_dict()
        d["ok"] = self.ok
        return d


@dataclass
class PackageResult:
    input_path: str
    output_path: str
    payload_bytes: int
    archive_bytes: int
    nnz: int
    n_obs: int
    n_vars: int
    meta: dict
    transformations: list[str]
    seconds: float
    peak_rss_bytes: int | None
    peak_disk_bytes: int
    validation: ValidationReport | None = None

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["validation"] = self.validation.as_dict() if self.validation else None
        return d


# --- reading -----------------------------------------------------------------


def _attr_str(group: h5py.Group, name: str) -> str | None:
    value = group.attrs.get(name)
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def inspect_layout(path: Path | str) -> LayoutReport:
    """Read the structure and refuse anything this module would have to guess at.

    Raises:
        PackagingError: for a layout that is valid AnnData but that packaging
            here cannot carry through unchanged -- dense X, a non-CSR sparse
            format, a dtype needing a cast. The message names `vcc prep` as the
            tool that does handle it, because it does, on a big enough machine.
    """
    path = Path(path)
    if not path.exists():
        raise PackagingError(f"Input file not found: {path}")
    if path.is_dir():
        raise PackagingError(f"'{path}' is a directory, not an .h5ad prediction.")

    with h5py.File(path, "r") as f:
        if "X" not in f:
            raise PackagingError(
                f"'{path.name}' has no X group, so there are no predictions to package."
            )
        x = f["X"]
        if not isinstance(x, h5py.Group):
            raise PackagingError(
                f"'{path.name}' stores X as a dense array. This packager copies CSR "
                "datasets verbatim and will not densify or convert. Regenerate the "
                "prediction as sparse CSR, or use `vcc prep` on a machine with enough "
                "RAM to hold the dense matrix."
            )
        encoding = _attr_str(x, "encoding-type")
        if encoding != _SUPPORTED_X_ENCODING:
            raise PackagingError(
                f"'{path.name}' stores X as '{encoding}', not '{_SUPPORTED_X_ENCODING}'. "
                "Only CSR is supported here; converting a CSC matrix means rebuilding "
                "it, which is exactly the whole-matrix operation this packager exists "
                "to avoid. Use `vcc prep` for other layouts."
            )
        for name in ("data", "indices", "indptr"):
            if name not in x:
                raise PackagingError(f"'{path.name}': X/{name} is missing.")
        shape = x.attrs.get("shape")
        if shape is None or len(tuple(shape)) != 2:
            raise PackagingError(
                f"'{path.name}': X has no usable 2-D shape attribute."
            )
        n_obs, n_vars = (int(v) for v in shape)

        data, indices, indptr = x["data"], x["indices"], x["indptr"]
        if not np.issubdtype(data.dtype, np.floating):
            raise PackagingError(
                f"'{path.name}': X/data has dtype {data.dtype}. A submission is written "
                "as float32; casting here would rewrite every stored value, which this "
                "packager does not do. Use `vcc prep`, which casts."
            )
        if data.dtype != np.float32:
            raise PackagingError(
                f"'{path.name}': X/data is {data.dtype}, but the .vcc encoding is "
                "float32. Casting would change the bytes this packager promises to "
                "preserve. Regenerate as float32, or use `vcc prep -e 32`."
            )
        for name, ds in (("indices", indices), ("indptr", indptr)):
            if not np.issubdtype(ds.dtype, np.integer):
                raise PackagingError(
                    f"'{path.name}': X/{name} has non-integer dtype {ds.dtype}."
                )

        if "obs" not in f or not isinstance(f["obs"], h5py.Group):
            raise PackagingError(f"'{path.name}': obs is missing or not a dataframe.")
        obs_group = f["obs"]
        obs_columns = [k for k in obs_group.keys() if k != "_index"]
        var_index_name = _attr_str(f["var"], "_index") if "var" in f else None
        if var_index_name is None:
            raise PackagingError(f"'{path.name}': var is missing or has no index.")

        droppable = []
        for attr in _DROPPABLE_ATTRS:
            node = f.get(attr)
            if node is None:
                continue
            if isinstance(node, h5py.Group):
                keys = [k for k in node.keys()]
                droppable.extend(f"{attr}[{k}]" for k in keys)
            else:
                droppable.append(attr)

        return LayoutReport(
            path=str(path),
            n_obs=n_obs,
            n_vars=n_vars,
            nnz=int(indptr[-1]),
            data_dtype=str(data.dtype),
            indices_dtype=str(indices.dtype),
            indptr_dtype=str(indptr.dtype),
            data_chunks=data.chunks,
            data_compression=data.compression,
            data_compression_opts=data.compression_opts,
            indices_chunks=indices.chunks,
            indices_compression=indices.compression,
            indices_compression_opts=indices.compression_opts,
            obs_columns=obs_columns,
            var_index_name=var_index_name,
            droppable_present=droppable,
            file_bytes=path.stat().st_size,
        )


def read_obs_frame(path: Path | str) -> pd.DataFrame:
    """The obs table, read through anndata's own reader.

    obs for a full submission is 360,000 rows of two categorical columns -- a few
    megabytes -- so it is read whole. That is what makes it possible to hand the
    official metadata validators a real DataFrame instead of a reimplementation.
    """
    from anndata.io import read_elem

    with h5py.File(Path(path), "r") as f:
        return read_elem(f["obs"])


def read_var_names(path: Path | str) -> list[str]:
    from anndata.io import read_elem

    with h5py.File(Path(path), "r") as f:
        index = read_elem(f["var"]).index
    return [str(v) for v in index]


class _ObsView:
    """The slice of the AnnData interface the official metadata checks touch.

    `validate_contexts` and `validate_targets` read `adata.obs` and nothing else.
    Handing them this instead of an AnnData is what makes the context, target and
    cell-count checks *the official ones* rather than a second implementation that
    could drift.
    """

    def __init__(self, obs: pd.DataFrame, n_vars: int) -> None:
        self.obs = obs
        self.shape = (len(obs), n_vars)

    @property
    def n_obs(self) -> int:
        return len(self.obs)


# --- streamed passes ---------------------------------------------------------


def _row_blocks(indptr: np.ndarray, values_per_block: int):
    """Yield (row_start, row_stop) so each block holds ~`values_per_block` values.

    A block always ends on a row boundary, so per-cell sums never straddle two
    reads. A single row wider than the budget still gets its own block rather
    than being split -- correctness first, and no real cell is that wide.
    """
    n_rows = indptr.size - 1
    start = 0
    while start < n_rows:
        budget = int(indptr[start]) + values_per_block
        stop = int(np.searchsorted(indptr, budget, side="right")) - 1
        if stop <= start:
            stop = start + 1
        stop = min(stop, n_rows)
        yield start, stop
        start = stop


def _check_csr_integrity(
    layout: LayoutReport, indptr: np.ndarray, data_len: int, indices_len: int
) -> dict:
    """Structural checks on the CSR arrays themselves.

    None of these are in `vcc prep`: it lets scipy build the matrix and inherits
    whatever scipy accepts. They are here because this packager copies the arrays
    instead of rebuilding them, so a malformed offset array would be carried
    through intact -- and because a submission at realistic density sits within 3%
    of int32's ceiling, where a wrapped offset array still opens as a valid h5ad
    (CP-0004 §3.6).
    """
    checks: dict = {}
    checks["indptr_length_is_n_obs_plus_1"] = indptr.size == layout.n_obs + 1
    checks["indptr_starts_at_zero"] = bool(indptr.size and int(indptr[0]) == 0)
    checks["indptr_non_negative"] = bool(indptr.size and int(indptr.min()) >= 0)
    checks["indptr_monotonic"] = bool(np.all(np.diff(indptr) >= 0))
    checks["indptr_end_matches_data_length"] = (
        bool(indptr.size) and int(indptr[-1]) == data_len
    )
    checks["data_and_indices_same_length"] = data_len == indices_len
    nnz = int(indptr[-1]) if indptr.size else 0
    checks["nnz_representable_in_indptr_dtype"] = nnz <= int(
        np.iinfo(np.dtype(layout.indptr_dtype)).max
    )
    checks["n_vars_representable_in_indices_dtype"] = layout.n_vars - 1 <= int(
        np.iinfo(np.dtype(layout.indices_dtype)).max
    )
    return checks


def validate_prediction(
    path: Path | str,
    *,
    genes_path: Path | str,
    perts_path: Path | str | None = None,
    pert_col: str | None = None,
    context_col: str | None = None,
    ntc_name: str | None = None,
    required_contexts: tuple[str, ...] | None = None,
    cells_per_pert: int | None = None,
    expected_gene_dim: int | None = None,
    max_cell_dim: int | None = None,
    max_nnz: int | None = None,
    max_counts_per_cell: int | None = None,
    verify_targets: bool = True,
    check_cell_counts: bool = True,
    reject_controls: bool = True,
    values_per_block: int = VALUES_PER_BLOCK,
) -> ValidationReport:
    """Run every check `vcc prep` runs, without holding the matrix.

    The metadata checks are the official functions, called on a real obs
    DataFrame. The matrix checks are streamed equivalents of
    `validate_matrix_values` and `_require_counts`, in the same order and with the
    same thresholds, plus the CSR structural checks official prep has no need for.

    Returns a report rather than raising, so a caller can record every failure
    instead of only the first. `package_prediction` refuses to write unless the
    report is clean.
    """
    from vcc2026.resources import peak_rss_bytes

    prep, _vccfile, sizing, _version = official()
    pert_col = pert_col or prep.DEFAULT_PERT_COL
    context_col = context_col or prep.DEFAULT_CONTEXT_COL
    ntc_name = ntc_name or prep.DEFAULT_NTC_NAME
    required_contexts = (
        prep.REQUIRED_CONTEXTS if required_contexts is None else required_contexts
    )
    cells_per_pert = (
        prep.EXPECTED_CELLS_PER_PERT if cells_per_pert is None else cells_per_pert
    )
    expected_gene_dim = (
        prep.EXPECTED_GENE_DIM if expected_gene_dim is None else expected_gene_dim
    )
    max_cell_dim = prep.MAX_CELL_DIM if max_cell_dim is None else max_cell_dim
    max_nnz = prep.MAX_NNZ if max_nnz is None else max_nnz
    max_counts_per_cell = (
        prep.MAX_COUNTS_PER_CELL if max_counts_per_cell is None else max_counts_per_cell
    )

    started = time.perf_counter()
    path = Path(path)
    layout = inspect_layout(path)
    failures: list[str] = []
    notes: list[str] = []
    checks: dict = {}

    def fail(message: str) -> None:
        failures.append(message)

    # --- gene axis (official reader, official comparison) --------------------
    genelist = prep.read_gene_list(str(genes_path))
    if expected_gene_dim and len(genelist) != expected_gene_dim:
        notes.append(
            f"Gene list length {len(genelist)} differs from the expected "
            f"{expected_gene_dim}; adopting the list's length, as prep does."
        )
        expected_gene_dim = len(genelist)

    var_names = read_var_names(path)
    checks["var_names_unique"] = len(set(var_names)) == len(var_names)
    if not checks["var_names_unique"]:
        fail("Duplicate gene names in var_names.")
    checks["gene_order_matches_list"] = var_names == genelist
    if not checks["gene_order_matches_list"]:
        missing = set(genelist) - set(var_names)
        extra = set(var_names) - set(genelist)
        if not missing and not extra:
            fail(
                "Genes are present but OUT OF ORDER. Official prep reorders them, "
                "which rebuilds the matrix column by column -- the whole-matrix "
                "operation this packager avoids. Regenerate the prediction with the "
                "genes in gene_names.csv order, or use `vcc prep`."
            )
        else:
            fail(prep._gene_mismatch_message(missing, extra))
    checks["gene_dim_matches_expected"] = (
        not expected_gene_dim or layout.n_vars == expected_gene_dim
    )
    if not checks["gene_dim_matches_expected"]:
        fail(
            f"Gene dimension {layout.n_vars} does not match the expected "
            f"dimension {expected_gene_dim}."
        )

    # --- obs: shape, columns, controls, contexts, targets --------------------
    obs = read_obs_frame(path)
    view = _ObsView(obs, layout.n_vars)
    checks["has_cells"] = layout.n_obs > 0
    if not checks["has_cells"]:
        fail("The prediction contains 0 cells.")
    checks["cell_dim_within_cap"] = not max_cell_dim or layout.n_obs <= max_cell_dim
    if not checks["cell_dim_within_cap"]:
        fail(
            f"Cell count {layout.n_obs} exceeds the maximum of {max_cell_dim}."
        )
    checks["pert_column_present"] = pert_col in obs.columns
    if not checks["pert_column_present"]:
        fail(
            f"Perturbation column '{pert_col}' is missing from obs. "
            f"Available: {list(obs.columns)}"
        )

    cells_per_context: dict = {}
    n_targets_per_context: dict = {}
    if checks["pert_column_present"] and checks["has_cells"]:
        n_control = int((obs[pert_col].astype(str) == ntc_name).sum())
        checks["no_control_rows"] = not (reject_controls and n_control)
        if not checks["no_control_rows"]:
            fail(
                f"Submission contains {n_control} '{ntc_name}' control cell(s); "
                "controls must NOT be submitted."
            )

        if required_contexts:
            try:
                cells_per_context = prep.validate_contexts(
                    view, context_col, pert_col, ntc_name, required_contexts
                )
                checks["contexts_complete"] = True
            except prep.PrepError as exc:
                checks["contexts_complete"] = False
                fail(str(exc))

        if verify_targets:
            if not perts_path:
                fail("Missing perturbation list, so target labels cannot be verified.")
                checks["targets_match_official_list"] = False
            elif required_contexts and context_col not in obs.columns:
                # Official prep raises out of `validate_contexts` and never reaches
                # the target check. This report keeps going so a caller sees every
                # failure at once, which means the later check has to be told that
                # the column it groups by is not there -- otherwise it dies on a
                # KeyError and the report is lost along with the real diagnosis.
                checks["targets_match_official_list"] = False
                notes.append(
                    "Target labels were not checked: the context column is missing, "
                    "so there is nothing to group them by."
                )
            else:
                expected = prep.read_pert_counts(
                    str(perts_path),
                    prep.DEFAULT_PERT_COL,
                    prep.DEFAULT_CONTEXT_COL,
                    prep.DEFAULT_NTC_NAME,
                    default_n_cells=cells_per_pert,
                )
                try:
                    prep.validate_targets(
                        view,
                        expected,
                        context_col,
                        pert_col,
                        ntc_name,
                        required_contexts,
                        check_cell_counts=check_cell_counts,
                    )
                    checks["targets_match_official_list"] = True
                except prep.PrepError as exc:
                    checks["targets_match_official_list"] = False
                    fail(str(exc))
                except Exception as exc:  # noqa: BLE001 - see below
                    # A validator that crashes must still produce a failure, not a
                    # traceback: this report is what a caller acts on, and "the
                    # check could not run" is itself a reason to refuse to package.
                    checks["targets_match_official_list"] = False
                    fail(
                        f"Target validation could not run ({type(exc).__name__}: "
                        f"{exc}); refusing to package."
                    )
        else:
            notes.append("Target labels were NOT verified (--no-verify-targets).")

        if required_contexts and context_col in obs.columns:
            ctx = obs[context_col].astype(str)
            labels_all = obs[pert_col].astype(str)
            for context in required_contexts:
                sel = ctx == context
                n_targets_per_context[context] = int(
                    labels_all[sel].nunique() if sel.any() else 0
                )

    # --- matrix: one streamed pass over every stored value -------------------
    checks["density_within_cap"] = not max_nnz or layout.nnz <= max_nnz
    if not checks["density_within_cap"]:
        fail(sizing.too_dense_message(layout.nnz, layout.n_obs))

    min_value = 0.0
    max_value = 0.0
    all_integer = True
    n_nonfinite = 0
    max_total = 0.0
    empty_perturbations: list[str] = []
    csr_checks: dict = {}

    with h5py.File(path, "r") as f:
        x = f["X"]
        indptr = x["indptr"][:].astype(np.int64)
        data_ds, idx_ds = x["data"], x["indices"]
        csr_checks = _check_csr_integrity(
            layout, indptr, int(data_ds.shape[0]), int(idx_ds.shape[0])
        )
        for name, ok in csr_checks.items():
            if not ok:
                fail(f"CSR integrity check failed: {name}.")

        structurally_sound = all(csr_checks.values())
        if structurally_sound:
            labels = (
                obs[pert_col].astype(str).to_numpy()
                if pert_col in obs.columns
                else np.array([""] * layout.n_obs)
            )
            uniques, label_codes = np.unique(labels, return_inverse=True)
            label_totals = np.zeros(uniques.size, dtype=np.float64)
            stored_min = np.inf
            stored_max = -np.inf
            n_bad_indices = 0

            for start, stop in _row_blocks(indptr, values_per_block):
                lo, hi = int(indptr[start]), int(indptr[stop])
                if hi > lo:
                    values = data_ds[lo:hi]
                    columns = idx_ds[lo:hi]
                    bad = ~np.isfinite(values)
                    n_bad_indices += int(
                        ((columns < 0) | (columns >= layout.n_vars)).sum()
                    )
                    n_bad = int(bad.sum())
                    n_nonfinite += n_bad
                    finite = values[~bad] if n_bad else values
                    if finite.size:
                        stored_min = min(stored_min, float(finite.min()))
                        stored_max = max(stored_max, float(finite.max()))
                        if all_integer and prep._has_fractional_values(finite):
                            all_integer = False
                    bounds = indptr[start : stop + 1] - lo
                    safe = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
                    totals = np.add.reduceat(
                        safe, np.minimum(bounds[:-1], max(safe.size - 1, 0))
                    )
                    lengths = np.diff(bounds)
                    totals = np.where(lengths > 0, totals, 0.0)
                else:
                    totals = np.zeros(stop - start, dtype=np.float64)
                if totals.size:
                    max_total = max(max_total, float(totals.max()))
                np.add.at(label_totals, label_codes[start:stop], totals)

            checks["column_indices_in_range"] = n_bad_indices == 0
            if n_bad_indices:
                fail(
                    f"{n_bad_indices} column index(es) fall outside "
                    f"[0, {layout.n_vars})."
                )
            min_value = 0.0 if not np.isfinite(stored_min) else float(stored_min)
            max_value = 0.0 if not np.isfinite(stored_max) else float(stored_max)
            # A structural zero is a real value, so a positive-only stored array
            # still has a minimum of 0 whenever any zero is implied. Mirrors
            # prep._min_value_of.
            if layout.nnz < layout.n_obs * layout.n_vars:
                min_value = min(min_value, 0.0)
            empty_perturbations = sorted(
                str(u) for u, t in zip(uniques, label_totals) if not t
            )
        else:
            notes.append(
                "CSR structure is unsound, so the value passes were skipped: their "
                "results would describe a matrix that cannot be read."
            )

    checks["counts_finite"] = n_nonfinite == 0
    if n_nonfinite:
        fail(f"Prediction matrix contains {n_nonfinite} non-finite value(s).")
    checks["counts_non_negative"] = min_value >= 0
    if not checks["counts_non_negative"]:
        fail("Submission contains NEGATIVE values, but counts must be non-negative.")
    checks["counts_are_whole_numbers"] = all_integer
    if not all_integer:
        fail("Submission values are FRACTIONAL, but counts must be whole numbers.")
    checks["max_counts_per_cell_within_cap"] = (
        not max_counts_per_cell or max_total <= max_counts_per_cell
    )
    if not checks["max_counts_per_cell_within_cap"]:
        fail(
            f"A cell totals {max_total:,.0f} counts, above the maximum of "
            f"{max_counts_per_cell:,}."
        )
    checks["no_all_zero_perturbation"] = not empty_perturbations
    if empty_perturbations:
        shown = ", ".join(empty_perturbations[:10])
        fail(
            f"{len(empty_perturbations)} perturbation(s) have all-zero predictions "
            f"across every gene and every cell: {shown}."
        )

    if layout.droppable_present:
        notes.append(
            "Dropped (not carried into the .vcc): "
            + ", ".join(layout.droppable_present)
        )

    return ValidationReport(
        layout=layout,
        n_obs=layout.n_obs,
        n_vars=layout.n_vars,
        nnz=layout.nnz,
        min_value=min_value,
        max_value=max_value,
        all_integer=all_integer,
        n_nonfinite=n_nonfinite,
        max_counts_per_cell_observed=max_total,
        cells_per_context=cells_per_context,
        n_targets_per_context=n_targets_per_context,
        empty_perturbations=empty_perturbations,
        csr_checks=csr_checks,
        checks=checks,
        failures=failures,
        notes=notes,
        seconds=time.perf_counter() - started,
        peak_rss_bytes=peak_rss_bytes(),
    )


# --- writing -----------------------------------------------------------------


def _copy_dataset(src: h5py.Dataset, dst_group: h5py.Group, name: str, block: int):
    """Copy one dataset block by block, preserving dtype, chunking and filters.

    `h5py.Group.copy` would do this in one call, but it offers no control over
    how much it buffers; an explicit loop is what makes the peak a property of
    `block` rather than of the prediction.
    """
    out = dst_group.create_dataset(
        name,
        shape=src.shape,
        dtype=src.dtype,
        chunks=src.chunks,
        compression=src.compression,
        compression_opts=src.compression_opts,
        shuffle=src.shuffle,
    )
    total = src.shape[0]
    for start in range(0, total, block):
        stop = min(start + block, total)
        out[start:stop] = src[start:stop]
    return out


def _sanitized_like_anndata(obs: pd.DataFrame, var: pd.DataFrame):
    """Apply AnnData's own obs/var sanitization, without materialising a matrix.

    `AnnData.__init__` converts string columns to categoricals, and that is why
    an official `.vcc` encodes `obs/target_gene` as `categorical`. The rule has a
    heuristic in it (anndata only converts when the conversion pays for itself),
    so reimplementing it would be a guess that drifts. Constructing an AnnData
    over an (n_obs x 0) sparse matrix runs the real thing for the price of an
    empty array.
    """
    import anndata as ad
    import scipy.sparse as sp

    shell = ad.AnnData(
        X=sp.csr_matrix((len(obs), 0), dtype=np.float32),
        obs=obs,
        var=pd.DataFrame(index=pd.Index([], dtype=str)),
    )
    shell.strings_to_categoricals()
    sanitized_obs = shell.obs
    # var here carries only an index, so sanitization has nothing to do to it;
    # it is passed through unchanged and returned for symmetry at the call site.
    return sanitized_obs, var


def write_payload(
    input_path: Path | str,
    payload_path: Path | str,
    *,
    pert_col: str | None = None,
    context_col: str | None = None,
    output_pert_col: str | None = None,
    output_context_col: str | None = None,
    required_contexts: tuple[str, ...] | None = None,
    values_per_block: int = VALUES_PER_BLOCK,
) -> dict:
    """Write the slimmed payload .h5ad, streaming X and rebuilding obs/var.

    obs and var go through `anndata.io.write_elem` on small in-memory frames, so
    their encodings are anndata's, not this module's guess at anndata's.
    """
    from anndata.io import write_elem

    prep, _vccfile, _sizing, _version = official()
    pert_col = pert_col or prep.DEFAULT_PERT_COL
    context_col = context_col or prep.DEFAULT_CONTEXT_COL
    output_pert_col = output_pert_col or prep.DEFAULT_PERT_COL
    output_context_col = output_context_col or prep.DEFAULT_CONTEXT_COL
    required_contexts = (
        prep.REQUIRED_CONTEXTS if required_contexts is None else required_contexts
    )

    input_path, payload_path = Path(input_path), Path(payload_path)
    obs = read_obs_frame(input_path)
    var_names = read_var_names(input_path)
    n_obs = len(obs)

    # Exactly prep's `new_obs`: the perturbation column, then the context column,
    # with a positional string index.
    new_obs = pd.DataFrame(
        {output_pert_col: obs[pert_col].to_numpy()},
        index=np.arange(n_obs).astype(str),
    )
    if required_contexts:
        new_obs[output_context_col] = obs[context_col].astype(str).to_numpy()
    new_var = pd.DataFrame(index=pd.Index(var_names))

    # Official prep hands these frames to `ad.AnnData(...)`, whose constructor
    # sanitizes string columns into categoricals -- so the .vcc's obs columns are
    # encoded `categorical`, not `nullable-string-array`. Writing the frames
    # straight through `write_elem` skips that step and produces a payload that
    # decodes to the same labels through a different encoding. Rather than
    # reimplement anndata's sanitization heuristic, run it: an AnnData over a
    # zero-column matrix costs nothing and is the same code path prep uses.
    new_obs, new_var = _sanitized_like_anndata(new_obs, new_var)

    with h5py.File(input_path, "r") as src, h5py.File(payload_path, "w") as dst:
        dst.attrs["encoding-type"] = "anndata"
        dst.attrs["encoding-version"] = "0.1.0"

        src_x = src["X"]
        x = dst.create_group("X")
        x.attrs["encoding-type"] = "csr_matrix"
        x.attrs["encoding-version"] = "0.1.0"
        x.attrs["shape"] = np.asarray(src_x.attrs["shape"], dtype=np.int64)
        _copy_dataset(src_x["data"], x, "data", values_per_block)
        _copy_dataset(src_x["indices"], x, "indices", values_per_block)
        _copy_dataset(src_x["indptr"], x, "indptr", values_per_block)

        write_elem(dst, "obs", new_obs)
        write_elem(dst, "var", new_var)
        for empty in ("layers", "obsm", "varm", "obsp", "varp", "uns"):
            write_elem(dst, empty, {})

    return {
        "payload_path": str(payload_path),
        "payload_bytes": payload_path.stat().st_size,
        "n_obs": n_obs,
        "n_vars": len(var_names),
    }


def archive_payload(
    payload_path: Path | str,
    output_path: Path | str,
    *,
    nnz: int,
    n_obs: int,
    n_vars: int,
    zstd_level: int = 3,
    zstd_threads: int | None = None,
    keep_intermediate: bool = False,
    temp_dir: Path | str | None = None,
) -> dict:
    """Compress the payload and write the .vcc, mirroring `_write_vcc`.

    Same archive as official prep: an uncompressed tar with `meta.json` first and
    `pred.h5ad.zst` second, member metadata normalised to uid/gid 0, empty
    user/group names and mtime 0. The zstd stream is written to a temporary file
    because tar needs the member size in its header; the intermediate is removed
    as soon as it is in the archive, which is what keeps peak disk at roughly two
    copies rather than three.
    """
    import zstandard as zstd

    prep, vccfile, _sizing, cli_version = official()
    payload_path, output_path = Path(payload_path), Path(output_path)
    threads = prep._zstd_worker_count() if zstd_threads is None else zstd_threads

    meta = {
        "schema": vccfile.META_SCHEMA,
        "nnz": int(nnz),
        "n_obs": int(n_obs),
        "n_vars": int(n_vars),
        "cli_version": cli_version,
    }

    started = time.perf_counter()
    peak_disk = 0
    # The compressed payload is a transient the size of the archive itself. On a
    # host with a small persisted-output budget and a large scratch disk --
    # Kaggle grants 19.5 GiB of saved output against about a terabyte of working
    # filesystem -- it has to be possible to put it somewhere other than next to
    # the output.
    scratch = str(temp_dir) if temp_dir else str(output_path.parent)
    Path(scratch).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as tmp:
        tmp = Path(tmp)
        zst_path = tmp / vccfile.PRED_MEMBER
        meta_path = tmp / vccfile.META_MEMBER
        meta_path.write_text(json.dumps(meta, sort_keys=True), encoding="utf-8")

        cctx = zstd.ZstdCompressor(level=zstd_level, threads=threads)
        with payload_path.open("rb") as src, zst_path.open("wb") as dst:
            cctx.copy_stream(src, dst)
        compressed_bytes = zst_path.stat().st_size
        peak_disk = payload_path.stat().st_size + compressed_bytes

        if not keep_intermediate:
            payload_path.unlink()

        def _normalize(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
            tarinfo.uid = tarinfo.gid = 0
            tarinfo.uname = tarinfo.gname = ""
            tarinfo.mtime = 0
            return tarinfo

        with tarfile.open(output_path, "w") as tar:
            tar.add(str(meta_path), arcname=vccfile.META_MEMBER, filter=_normalize)
            tar.add(str(zst_path), arcname=vccfile.PRED_MEMBER, filter=_normalize)
        peak_disk = max(peak_disk, compressed_bytes + output_path.stat().st_size)

    return {
        "output_path": str(output_path),
        "archive_bytes": output_path.stat().st_size,
        "compressed_payload_bytes": compressed_bytes,
        "meta": meta,
        "zstd_level": zstd_level,
        "zstd_threads": threads,
        "seconds": time.perf_counter() - started,
        "peak_disk_bytes": peak_disk,
    }


def package_prediction(
    input_path: Path | str,
    output_path: Path | str,
    *,
    genes_path: Path | str,
    perts_path: Path | str,
    workdir: Path | str | None = None,
    temp_dir: Path | str | None = None,
    validate: bool = True,
    zstd_level: int = 3,
    zstd_threads: int | None = None,
    values_per_block: int = VALUES_PER_BLOCK,
    force: bool = False,
    **validate_kwargs,
) -> PackageResult:
    """Validate, then package. Refuses to write unless validation is clean.

    Raises:
        PackagingError: on any validation failure, listing every one of them --
            a caller fixing a prediction should see the whole list, not the first
            item of it.
    """
    from vcc2026.resources import peak_rss_bytes

    prep, _vccfile, _sizing, _version = official()
    input_path, output_path = Path(input_path), Path(output_path)
    if output_path.exists() and not force:
        raise PackagingError(
            f"Output already exists: {output_path}. Choose a new path; this "
            "packager does not overwrite an artifact."
        )
    prep.assert_output_distinct_from_inputs(
        str(output_path),
        [
            ("input .h5ad", str(input_path)),
            ("gene list", str(genes_path)),
            ("perturbation list", str(perts_path)),
        ],
    )

    started = time.perf_counter()
    report = None
    if validate:
        report = validate_prediction(
            input_path,
            genes_path=genes_path,
            perts_path=perts_path,
            values_per_block=values_per_block,
            **validate_kwargs,
        )
        if not report.ok:
            raise PackagingError(
                f"{len(report.failures)} validation failure(s); nothing was written:\n"
                + "\n".join(f"  - {f}" for f in report.failures)
            )
    layout = report.layout if report else inspect_layout(input_path)

    workdir = Path(workdir) if workdir else output_path.parent
    workdir.mkdir(parents=True, exist_ok=True)
    payload_path = workdir / (output_path.stem + ".payload.h5ad")
    if payload_path.exists() and not force:
        raise PackagingError(f"Intermediate already exists: {payload_path}")

    written = write_payload(
        input_path, payload_path, values_per_block=values_per_block
    )
    archived = archive_payload(
        payload_path,
        output_path,
        nnz=layout.nnz,
        n_obs=written["n_obs"],
        n_vars=written["n_vars"],
        zstd_level=zstd_level,
        zstd_threads=zstd_threads,
        temp_dir=temp_dir or workdir,
    )

    return PackageResult(
        input_path=str(input_path),
        output_path=str(output_path),
        payload_bytes=written["payload_bytes"],
        archive_bytes=archived["archive_bytes"],
        nnz=layout.nnz,
        n_obs=written["n_obs"],
        n_vars=written["n_vars"],
        meta=archived["meta"],
        transformations=payload_transformations(),
        seconds=time.perf_counter() - started,
        peak_rss_bytes=peak_rss_bytes(),
        peak_disk_bytes=max(written["payload_bytes"], archived["peak_disk_bytes"]),
        validation=report,
    )


# --- verification ------------------------------------------------------------


@contextmanager
def extracted_payload(vcc_path: Path | str, workdir: Path | str):
    """Stream-decompress a .vcc's prediction member to a file, and clean up.

    Streamed because the point of the exercise is that nothing on this path
    needs the matrix in memory -- including the verification of it.
    """
    import zstandard as zstd

    _prep, vccfile, _sizing, _version = official()
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / "pred.h5ad"
    try:
        with tarfile.open(Path(vcc_path), "r:*") as tar:
            member = tar.extractfile(vccfile.PRED_MEMBER)
            if member is None:
                raise PackagingError(
                    f"{vcc_path}: missing member {vccfile.PRED_MEMBER}"
                )
            with out.open("wb") as dst:
                zstd.ZstdDecompressor().copy_stream(member, dst)
        yield out
    finally:
        if out.exists():
            out.unlink()


def assert_payload_matches_input(
    input_path: Path | str,
    payload_path: Path | str,
    *,
    pert_col: str | None = None,
    context_col: str | None = None,
    values_per_block: int = VALUES_PER_BLOCK,
) -> dict:
    """Check an extracted payload against the INPUT it was built from.

    This is the verification that matters for a real run, and it is deliberately
    not a comparison against a re-derived payload: re-deriving would test the
    writer against itself, and would cost a second full-size temporary on a
    machine where disk is the binding constraint.

    The X arrays are asserted **bit-identical** to the input's, block by block.
    obs and var are asserted equal in the way the documented transformation
    allows: same gene axis, same perturbation and context labels in the same
    order, and an obs index that has been replaced by '0'..'n-1' -- which is
    checked positively, so the transformation is confirmed rather than ignored.

    Raises:
        AssertionError: naming the first difference found.
    """
    from anndata.io import read_elem

    prep, _vccfile, _sizing, _version = official()
    pert_col = pert_col or prep.DEFAULT_PERT_COL
    context_col = context_col or prep.DEFAULT_CONTEXT_COL
    input_path, payload_path = Path(input_path), Path(payload_path)

    with h5py.File(input_path, "r") as fi, h5py.File(payload_path, "r") as fp:
        si = tuple(int(v) for v in fi["X"].attrs["shape"])
        sp_ = tuple(int(v) for v in fp["X"].attrs["shape"])
        assert si == sp_, f"shape differs: input {si} vs payload {sp_}"

        pi = fi["X/indptr"][:].astype(np.int64)
        pp = fp["X/indptr"][:].astype(np.int64)
        assert np.array_equal(pi, pp), "CSR indptr differs from the input"

        di, dp = fi["X/data"], fp["X/data"]
        ii, ip = fi["X/indices"], fp["X/indices"]
        assert di.shape == dp.shape, (
            f"stored-entry count differs: input {di.shape} vs payload {dp.shape}"
        )
        assert di.dtype == dp.dtype, f"data dtype differs: {di.dtype} vs {dp.dtype}"
        assert ii.dtype == ip.dtype, (
            f"indices dtype differs: {ii.dtype} vs {ip.dtype}"
        )
        total = int(di.shape[0])
        for start in range(0, total, values_per_block):
            stop = min(start + values_per_block, total)
            assert np.array_equal(di[start:stop], dp[start:stop]), (
                f"stored values differ from the input in [{start}, {stop})"
            )
            assert np.array_equal(ii[start:stop], ip[start:stop]), (
                f"column indices differ from the input in [{start}, {stop})"
            )

        vi = [str(v) for v in read_elem(fi["var"]).index]
        vp = [str(v) for v in read_elem(fp["var"]).index]
        assert vi == vp, "gene axis differs from the input"

        oi, op = read_elem(fi["obs"]), read_elem(fp["obs"])
        assert list(op.columns) == [pert_col, context_col], (
            f"payload obs columns are {list(op.columns)}, expected "
            f"{[pert_col, context_col]}"
        )
        for col in (pert_col, context_col):
            assert np.array_equal(
                oi[col].astype(str).to_numpy(), op[col].astype(str).to_numpy()
            ), f"obs column '{col}' differs from the input"
        expected_index = np.arange(si[0]).astype(str)
        assert np.array_equal(op.index.astype(str).to_numpy(), expected_index), (
            "payload obs index is not the positional index prep writes"
        )
        index_was_rewritten = not np.array_equal(
            oi.index.astype(str).to_numpy(), expected_index
        )

    return {
        "matches_input": True,
        "n_obs": si[0],
        "n_vars": si[1],
        "nnz": int(pi[-1]),
        "x_arrays_bit_identical": True,
        "obs_index_rewritten": bool(index_was_rewritten),
        "compared": [
            "X.data (bitwise)", "X.indices (bitwise)", "X.indptr (bitwise)",
            "X dtypes", "var index", f"obs['{pert_col}']", f"obs['{context_col}']",
            "obs index is positional",
        ],
    }


def assert_payloads_equivalent(
    a: Path | str, b: Path | str, *, values_per_block: int = VALUES_PER_BLOCK
) -> dict:
    """Compare two payload .h5ad files by content, not by bytes.

    Byte equality is the wrong test: HDF5 layout, filters and allocation order
    differ between a streamed dataset copy and `AnnData.write_h5ad`, while the
    arrays they decode to are the thing a submission is made of. So this compares
    the decoded arrays exactly, in blocks, plus the gene axis and both obs
    columns.

    Raises:
        AssertionError: naming the first difference found.
    """
    from anndata.io import read_elem

    a, b = Path(a), Path(b)
    with h5py.File(a, "r") as fa, h5py.File(b, "r") as fb:
        sa = tuple(int(v) for v in fa["X"].attrs["shape"])
        sb = tuple(int(v) for v in fb["X"].attrs["shape"])
        assert sa == sb, f"shape differs: {sa} vs {sb}"

        ia = fa["X/indptr"][:].astype(np.int64)
        ib = fb["X/indptr"][:].astype(np.int64)
        assert np.array_equal(ia, ib), "CSR indptr differs"

        da, db = fa["X/data"], fb["X/data"]
        xa, xb = fa["X/indices"], fb["X/indices"]
        assert da.shape == db.shape, f"data length differs: {da.shape} vs {db.shape}"
        total = int(da.shape[0])
        for start in range(0, total, values_per_block):
            stop = min(start + values_per_block, total)
            assert np.array_equal(da[start:stop], db[start:stop]), (
                f"stored values differ in [{start}, {stop})"
            )
            assert np.array_equal(xa[start:stop], xb[start:stop]), (
                f"column indices differ in [{start}, {stop})"
            )

        va = [str(v) for v in read_elem(fa["var"]).index]
        vb = [str(v) for v in read_elem(fb["var"]).index]
        assert va == vb, "gene axis differs"

        oa, ob = read_elem(fa["obs"]), read_elem(fb["obs"])
        assert list(oa.columns) == list(ob.columns), (
            f"obs columns differ: {list(oa.columns)} vs {list(ob.columns)}"
        )
        for col in oa.columns:
            assert np.array_equal(
                oa[col].astype(str).to_numpy(), ob[col].astype(str).to_numpy()
            ), f"obs column '{col}' differs"
        assert list(oa.index.astype(str)) == list(ob.index.astype(str)), (
            "obs index differs"
        )

    return {
        "equivalent": True,
        "n_obs": sa[0],
        "n_vars": sa[1],
        "nnz": int(ia[-1]),
        "compared": ["X.data", "X.indices", "X.indptr", "var index", "obs columns",
                     "obs index"],
    }
