"""The official 18,533-gene output axis.

**The official column order is the submission contract.** `gene_names.csv` holds
symbols, not Ensembl IDs, so ordering alone cannot be used to infer Ensembl
identifiers. Cross-source joins go through explicit symbol reconciliation.

The axis is read from `data_root/raw/controls/gene_names.csv` once per process.
(`align_to_axis`, which aligned a source onto it with a D-009 mask, left on
24 September 2026 with no live caller: docs/ARCHIVIO.md.)
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .config import challenge, paths

__all__ = ["GeneAxis", "official_axis"]


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
