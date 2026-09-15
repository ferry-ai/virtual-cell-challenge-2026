"""Gene universe actually measured in every compared source.

D-009: a gene a source did not measure is unmeasured, not unchanged. Filling it
with zero before an SVD invents a direction of "no effect". This module builds
the intersection of observed masks and records the coverage that intersection
throws away. It does not zero-fill.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vcc2026.genes import official_axis
from vcc2026.signatures import SignatureSet

__all__ = ["GeneUniverse", "common_measured_universe", "assert_no_zero_fill"]


@dataclass(frozen=True)
class GeneUniverse:
    """Boolean mask on the official axis, plus the coverage that was dropped."""

    observed: np.ndarray
    per_source_n: dict[str, int]
    n_official: int
    rule: str = "intersection_measured"

    @property
    def n_kept(self) -> int:
        return int(self.observed.sum())

    @property
    def n_dropped(self) -> int:
        return self.n_official - self.n_kept

    @property
    def coverage_kept(self) -> float:
        return self.n_kept / self.n_official if self.n_official else float("nan")

    def index(self) -> np.ndarray:
        return np.flatnonzero(self.observed)

    def slice(self, values: np.ndarray) -> np.ndarray:
        """Restrict the last axis to the universe. Never fills."""
        idx = self.index()
        if values.ndim == 1:
            return np.asarray(values)[idx]
        return np.asarray(values)[..., idx]

    def embed(self, values: np.ndarray) -> np.ndarray:
        """Place a universe-sized array back on the official axis (zeros elsewhere).

        The zeros are unobserved, not a claim of no effect. Callers must keep
        `observed` beside the result.
        """
        values = np.asarray(values)
        if values.ndim == 1:
            out = np.zeros(self.n_official, dtype=values.dtype)
            out[self.observed] = values
            return out
        out = np.zeros(values.shape[:-1] + (self.n_official,), dtype=values.dtype)
        out[..., self.observed] = values
        return out

    def as_dict(self) -> dict:
        return {
            "rule": self.rule,
            "n_official": self.n_official,
            "n_kept": self.n_kept,
            "n_dropped": self.n_dropped,
            "coverage_kept": self.coverage_kept,
            "per_source_n_measured": dict(self.per_source_n),
            "zero_fill_missing": False,
            "note": (
                "Kept genes are those every compared source actually measured. "
                "Dropped genes are unmeasured, not unchanged. Models train and "
                "are scored on the kept set only."
            ),
        }


def common_measured_universe(sets: dict[str, SignatureSet]) -> GeneUniverse:
    """AND of per-source observed masks. Raises if a source is empty."""
    n = len(official_axis())
    mask = np.ones(n, dtype=bool)
    per: dict[str, int] = {}
    for name, sigs in sets.items():
        if len(sigs) == 0:
            raise ValueError(f"{name}: no signatures, cannot form a universe")
        source_mask = np.ones(n, dtype=bool)
        for s in sigs:
            source_mask &= s.observed
        per[name] = int(source_mask.sum())
        mask &= source_mask
    if not mask.any():
        raise ValueError("intersection of measured genes is empty")
    return GeneUniverse(observed=mask, per_source_n=per, n_official=n)


def assert_no_zero_fill(universe: GeneUniverse, values: np.ndarray) -> None:
    """Values that will enter SVD/loss must already be restricted to the universe.

    A last-axis length equal to the official axis is the shape of the mistake
    LowRankRidge makes (zero-filling then factorising). Catch it here.
    """
    n_last = values.shape[-1]
    if n_last == universe.n_official and n_last != universe.n_kept:
        raise ValueError(
            "array still has the official-axis width; restrict it to the "
            "measured universe before SVD or a dense loss. Zero-filling "
            "unmeasured genes is not a neutral missing-data treatment."
        )
    if n_last != universe.n_kept:
        raise ValueError(
            f"last axis is {n_last}, universe keeps {universe.n_kept}"
        )
