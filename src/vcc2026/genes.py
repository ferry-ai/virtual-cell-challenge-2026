"""The official 18,533-gene output axis, and alignment of any source onto it.

Two rules are enforced here rather than left to each caller, because both have
already been recorded as decisions and both fail silently when broken:

* **D-009 -- a gene a source does not measure gets a mask, not a zero.** Every
  aligned array therefore travels with a boolean `observed` mask. Filling an
  unmeasured gene with zero invents evidence in the worst direction, because
  "no effect" is a plausible prediction a model would learn as an observation.
* **The official column order is the submission contract.** `gene_names.csv`
  holds symbols, not Ensembl IDs, so ordering alone cannot be used to infer
  Ensembl identifiers. Cross-source joins go through explicit symbol
  reconciliation, and duplicate symbols are resolved before alignment, never
  after.

The axis is read from `data_root/raw/controls/gene_names.csv` once per process.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .config import challenge, paths

__all__ = ["GeneAxis", "official_axis", "AlignedMatrix", "align_to_axis"]


@dataclass(frozen=True)
class GeneAxis:
    """The ordered output gene symbols a submission must use."""

    symbols: tuple[str, ...]

    def __len__(self) -> int:
        return len(self.symbols)

    @property
    def index(self) -> pd.Index:
        return pd.Index(self.symbols, name="gene_name")

    @lru_cache(maxsize=1)
    def position(self) -> dict[str, int]:
        """symbol -> column index."""
        return {s: i for i, s in enumerate(self.symbols)}

    def positions_of(self, symbols) -> np.ndarray:
        """Column index for each symbol, -1 where the symbol is not on the axis."""
        pos = self.position()
        return np.fromiter((pos.get(s, -1) for s in symbols), dtype=np.int64,
                           count=len(symbols))


@lru_cache(maxsize=1)
def official_axis(path: Path | None = None) -> GeneAxis:
    """Load and validate the official output axis.

    Raises:
        FileNotFoundError: the control bundle has not been unpacked.
        ValueError: the file does not match the challenge spec (18,533 unique
            symbols in a single column).
    """
    csv = Path(path) if path is not None else paths().raw / "controls" / "gene_names.csv"
    if not csv.exists():
        raise FileNotFoundError(
            f"official gene axis not found at {csv}; unpack the control bundle first"
        )
    frame = pd.read_csv(csv)
    if frame.shape[1] != 1:
        raise ValueError(f"{csv}: expected one column, got {list(frame.columns)}")
    symbols = frame.iloc[:, 0].astype(str).tolist()
    expected = challenge().n_genes
    if len(symbols) != expected:
        raise ValueError(f"{csv}: {len(symbols)} symbols, expected {expected}")
    if len(set(symbols)) != len(symbols):
        dupes = frame.iloc[:, 0][frame.iloc[:, 0].duplicated()].unique()[:5]
        raise ValueError(f"{csv}: duplicate symbols on the official axis, e.g. {list(dupes)}")
    return GeneAxis(symbols=tuple(symbols))


@dataclass(frozen=True)
class AlignedMatrix:
    """Source values placed on the official axis, with an explicit observed mask.

    Attributes:
        values: (n_rows, n_axis_genes) float array. Entries where `observed`
            is False are meaningless and must never be read as zero effect.
        observed: (n_axis_genes,) bool. True where the source measured the gene.
        row_labels: label per row (a perturbation target, a guide, a cell).
        dropped: source symbols that are not on the official axis.
        collapsed: source symbols that appeared more than once and how they
            were resolved.
    """

    values: np.ndarray
    observed: np.ndarray
    row_labels: tuple[str, ...]
    dropped: tuple[str, ...]
    collapsed: dict[str, int]

    def __post_init__(self) -> None:
        # Validate self-consistency, not agreement with the global axis: the
        # object must be constructible against whichever axis produced it
        # (a test axis, or a future second axis), and reaching for the module
        # singleton here made that impossible.
        if self.observed.ndim != 1:
            raise ValueError(f"observed must be 1-D, got {self.observed.shape}")
        if self.values.shape != (len(self.row_labels), self.observed.shape[0]):
            raise ValueError(
                f"values {self.values.shape} does not match "
                f"({len(self.row_labels)}, {self.observed.shape[0]})"
            )

    @property
    def n_observed(self) -> int:
        return int(self.observed.sum())

    def coverage(self) -> float:
        """Fraction of the official axis this source measures."""
        return self.n_observed / len(self.observed)


def align_to_axis(
    values: np.ndarray,
    source_symbols,
    row_labels,
    *,
    duplicate_policy: str = "sum",
    axis: GeneAxis | None = None,
) -> AlignedMatrix:
    """Place a source matrix onto the official gene axis.

    Args:
        values: (n_rows, n_source_genes) numeric array.
        source_symbols: gene symbol for each source column.
        row_labels: label for each row.
        duplicate_policy: how to resolve a symbol appearing in several source
            columns -- "sum" (counts), "mean" (rates, log-ratios) or "error".
        axis: override the official axis (tests).

    Returns:
        An AlignedMatrix. Unmeasured axis genes hold 0.0 in `values` but are
        False in `observed`; read them only through the mask.
    """
    axis = axis or official_axis()
    values = np.asarray(values, dtype=np.float64)
    source_symbols = [str(s) for s in source_symbols]
    row_labels = tuple(str(r) for r in row_labels)

    if values.ndim != 2:
        raise ValueError(f"values must be 2-D, got shape {values.shape}")
    if values.shape[1] != len(source_symbols):
        raise ValueError(
            f"{values.shape[1]} columns but {len(source_symbols)} source symbols"
        )
    if values.shape[0] != len(row_labels):
        raise ValueError(f"{values.shape[0]} rows but {len(row_labels)} labels")
    if duplicate_policy not in {"sum", "mean", "error"}:
        raise ValueError(f"unknown duplicate_policy: {duplicate_policy!r}")

    col_of = axis.positions_of(source_symbols)
    on_axis = col_of >= 0
    dropped = tuple(sorted({s for s, keep in zip(source_symbols, on_axis) if not keep}))

    out = np.zeros((len(row_labels), len(axis)), dtype=np.float64)
    hits = np.zeros(len(axis), dtype=np.int64)

    kept_cols = np.flatnonzero(on_axis)
    kept_targets = col_of[kept_cols]
    # np.add.at handles repeated targets (duplicate symbols) correctly.
    np.add.at(out, (slice(None), kept_targets), values[:, kept_cols])
    np.add.at(hits, kept_targets, 1)

    collapsed = {
        axis.symbols[i]: int(hits[i]) for i in np.flatnonzero(hits > 1)
    }
    if collapsed and duplicate_policy == "error":
        raise ValueError(
            f"{len(collapsed)} duplicate source symbols, e.g. "
            f"{sorted(collapsed)[:5]}; pass duplicate_policy='sum' or 'mean'"
        )
    if collapsed and duplicate_policy == "mean":
        multi = np.flatnonzero(hits > 1)
        out[:, multi] /= hits[multi]

    observed = hits > 0
    return AlignedMatrix(
        values=out,
        observed=observed,
        row_labels=row_labels,
        dropped=dropped,
        collapsed=collapsed,
    )
