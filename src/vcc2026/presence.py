"""Per-gene presence in a context's unperturbed cells, and a graded weight from it.

A gene that is not transcribed in a context cannot be switched off further there,
so a predicted response on that gene should shrink toward zero. This module turns
a context's control cells into evidence for "transcribed" and that evidence into a
weight in [0, 1]. It reads no files: the basal profiles already have readers --
`inference.read_basal_profile` for an official control file, and
`benchmark.descriptors.extract_control_profile` / `load_control_profile_npz`
(written by scripts/55_control_profile.py) for an external source.

Why a pooled CPM and not a per-cell detection rate. On one cell a zero mixes "not
transcribed" with "not captured", and nothing separates the two. Pooled over a
whole context the arithmetic changes: 18,400 control cells at ~20,000 molecules
each is ~3.7e8 molecules, so a gene at one part per million is still counted
hundreds of times, and a pooled zero is biology far more often than dropout. What
stays grey is the band of low but non-zero genes, where "little" and "little
measured" do not separate. That is why the weight is a logistic in log10 CPM with a
midpoint and a slope -- never a threshold -- and why both are parameters to be
chosen on held-out targets rather than constants written here.

A gene the profile does not measure gets weight 1. Missing evidence is not evidence
of absence (D-009), and a gate must not act without evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = [
    "GenePresence",
    "combine_log10_presence",
    "logistic_weight",
    "gate_output",
    "gate_rows",
    "permute_among",
    "presence_summary",
]


@dataclass(frozen=True)
class GenePresence:
    """Pooled control CPM of one context on the official axis.

    `cpm` is NaN where the context's profile does not measure the gene, so an
    unmeasured gene can never be mistaken for a gene measured at zero.
    """

    context: str
    cpm: np.ndarray
    library: float
    n_cells: float
    provenance: str

    @property
    def measured(self) -> np.ndarray:
        return np.isfinite(self.cpm)

    def log10_cpm(self, pseudocount: float) -> np.ndarray:
        """log10(CPM + pseudocount), NaN kept where unmeasured."""
        if pseudocount <= 0:
            raise ValueError("pseudocount must be positive: log10(0) is not a presence")
        return np.log10(self.cpm + float(pseudocount))

    @classmethod
    def from_basal_profile(cls, basal) -> "GenePresence":
        """From `inference.BasalProfile`: summed counts over the official controls.

        The official control file measures every gene of the axis, so nothing is
        NaN here; a gene with no count in the whole context is a measured zero.
        """
        profile = np.asarray(basal.profile, dtype=np.float64)
        total = float(profile.sum())
        if total <= 0:
            raise ValueError(f"{basal.context}: control profile has no counts")
        return cls(
            context=str(basal.context),
            cpm=1e6 * profile / total,
            library=total,
            n_cells=float(basal.n_cells),
            provenance=(
                f"pooled counts of {basal.n_cells} control cells "
                f"({basal.source_path or 'official control file'}), CPM"
            ),
        )

    @classmethod
    def from_control_profile(cls, profile) -> "GenePresence":
        """From `benchmark.descriptors.ControlProfile`: log1p CPM plus a mask."""
        observed = np.asarray(profile.observed, dtype=bool)
        cpm = np.full(observed.shape, np.nan, dtype=np.float64)
        cpm[observed] = np.expm1(np.asarray(profile.log1p_cpm, dtype=np.float64)[observed])
        # expm1 of a float log1p can land a hair below zero for a true zero.
        cpm[observed] = np.maximum(cpm[observed], 0.0)
        return cls(
            context=str(profile.context),
            cpm=cpm,
            library=float(profile.library),
            n_cells=float(profile.n_cells),
            provenance=str(profile.provenance),
        )


def combine_log10_presence(vectors: list[np.ndarray]) -> np.ndarray:
    """Equal-weight mean of several contexts' log10 presence, ignoring NaN.

    A gene measured in one context and not in another takes the one measurement;
    a gene measured in none stays NaN, and so stays ungated.
    """
    if not vectors:
        raise ValueError("at least one presence vector is required")
    stack = np.vstack([np.asarray(v, dtype=np.float64) for v in vectors])
    finite = np.isfinite(stack)
    count = finite.sum(axis=0)
    total = np.where(finite, stack, 0.0).sum(axis=0)
    out = np.full(stack.shape[1], np.nan, dtype=np.float64)
    ok = count > 0
    out[ok] = total[ok] / count[ok]
    return out


def logistic_weight(
    log10_presence: np.ndarray, *, midpoint_cpm: float, slope_per_decade: float
) -> np.ndarray:
    """Weight in (0, 1): 0.5 at the midpoint, rising with presence. NaN -> 1.

    `slope_per_decade` is the logistic steepness per factor of ten in CPM. At slope
    2 the weight is 0.12 one decade below the midpoint and 0.88 one decade above.
    """
    if midpoint_cpm <= 0:
        raise ValueError("midpoint_cpm must be positive")
    if slope_per_decade <= 0:
        raise ValueError("slope_per_decade must be positive: a gate that falls with "
                         "expression is a different rule")
    x = np.asarray(log10_presence, dtype=np.float64)
    finite = np.isfinite(x)
    z = np.zeros_like(x)
    z[finite] = float(slope_per_decade) * (x[finite] - np.log10(float(midpoint_cpm)))
    w = np.ones_like(x)
    w[finite] = 1.0 / (1.0 + np.exp(-np.clip(z[finite], -700.0, 700.0)))
    return w


def gate_output(
    delta: np.ndarray, weight: np.ndarray, *, positive_attenuation: float = 1.0
) -> np.ndarray:
    """Gate each output gene of a (rows, genes) or (genes,) delta.

    The negative part is multiplied by `weight`. The positive part by
    `1 - positive_attenuation * (1 - weight)`: 1 is the symmetric gate, 0 leaves
    an increase untouched -- an absent gene cannot go down, but it can go up.
    """
    beta = float(positive_attenuation)
    if not 0.0 <= beta <= 1.0:
        raise ValueError("positive_attenuation must be in [0, 1]")
    delta = np.asarray(delta, dtype=np.float64)
    weight = np.asarray(weight, dtype=np.float64)
    if weight.shape != delta.shape[-1:]:
        raise ValueError(f"weight {weight.shape} does not match genes {delta.shape[-1:]}")
    positive_factor = 1.0 - beta * (1.0 - weight)
    return np.where(delta < 0.0, delta * weight, delta * positive_factor)


def gate_rows(delta: np.ndarray, row_weight: np.ndarray) -> np.ndarray:
    """Multiply each row (one target's response) by that row's weight."""
    delta = np.asarray(delta, dtype=np.float64)
    row_weight = np.asarray(row_weight, dtype=np.float64)
    if delta.ndim != 2 or row_weight.shape != (delta.shape[0],):
        raise ValueError(f"row weights {row_weight.shape} do not match rows {delta.shape}")
    return delta * row_weight[:, None]


def permute_among(values: np.ndarray, positions: np.ndarray, seed: int) -> np.ndarray:
    """Shuffle `values` among `positions` once, with a fixed seed.

    Everything outside `positions` is untouched, and the multiset of values inside
    is preserved exactly: the permuted control differs from the real one by which
    gene carries which value, and by nothing else.
    """
    values = np.asarray(values)
    positions = np.asarray(positions, dtype=np.int64)
    if np.unique(positions).size != positions.size:
        raise ValueError("positions must be distinct")
    out = values.copy()
    order = np.random.default_rng(int(seed)).permutation(positions.size)
    out[positions] = values[positions[order]]
    return out


def presence_summary(
    cpm: np.ndarray, *, thresholds=(1.0, 5.0, 10.0, 30.0, 100.0)
) -> dict:
    """How many genes sit below each CPM threshold, among the measured ones."""
    cpm = np.asarray(cpm, dtype=np.float64)
    finite = cpm[np.isfinite(cpm)]
    out = {
        "n_genes": int(cpm.size),
        "n_measured": int(finite.size),
        "n_unmeasured": int(cpm.size - finite.size),
    }
    if finite.size:
        out["cpm_quantiles"] = {
            q: float(np.percentile(finite, float(q.rstrip("%"))))
            for q in ("0%", "1%", "5%", "25%", "50%")
        }
        out["n_below_cpm"] = {str(t): int(np.sum(finite < float(t))) for t in thresholds}
    return out
