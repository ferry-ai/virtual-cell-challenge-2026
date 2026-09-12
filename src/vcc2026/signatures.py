"""Perturbation response signatures carrying uncertainty and numerosity.

A signature is one estimated response: for a given source, biological context,
and perturbed target, a log2 fold change per output gene, **with a standard
error and the cell count behind it**. Uncertainty is not decoration here. The
measured transfer correlation between K562 and RPE1 rises from 0.028 to 0.223
(median Pearson) as the source effect size grows
(`reports/transfer_ceiling/transfer_ceiling.json`,
`stratified_mean_removed_ontarget_masked.by_min_anderson_darling_counts`), so
an estimate's reliability is the difference between signal and noise, and any
combination rule that ignores it is averaging noise into the answer.

The standard error is a Poisson delta-method propagation through the CPM
transform. For a pseudobulk row with summed counts `c` over library size `L`,
and its matched control `c0`/`L0`:

    cpm  = 1e6 * c / L
    d    = log2((cpm + p) / (cpm0 + p))
    var(d) ~= (1/ln2)^2 * [ cpm * q / (cpm + p)^2  +  cpm0 * q0 / (cpm0 + p)^2 ]

where `q = 1e6 / L` is the CPM contributed by a single UMI. This is a sampling
floor, not a full error model: it ignores biological variation between cells and
between guides, so it understates the true uncertainty. Between-guide spread,
when several guides hit the same target, is the honest upper estimate, and
`SignatureSet.collapse_guides` reports both.

Missing genes stay masked throughout (D-009). A signature never claims a value
for an output gene its source did not measure.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .genes import AlignedMatrix, official_axis

__all__ = ["Signature", "SignatureSet", "delta_from_pseudobulk", "LN2"]

LN2 = float(np.log(2.0))


@dataclass(frozen=True)
class Signature:
    """One target's estimated response in one source context.

    Attributes:
        source: registry id of the dataset (e.g. "k562_gwps").
        context: biological context within the source -- cell line, donor,
            culture condition. Never pool across these.
        target: perturbed gene symbol.
        delta: (n_axis,) log2 fold change vs matched control.
        se: (n_axis,) standard error of `delta`.
        observed: (n_axis,) bool; False where the source does not measure.
        n_cells: cells behind the perturbed estimate.
        n_control_cells: cells behind the matched control.
        guide_id: guide identifier when the signature is guide-level.
        meta: free-form provenance kept with the estimate.
    """

    source: str
    context: str
    target: str
    delta: np.ndarray
    se: np.ndarray
    observed: np.ndarray
    n_cells: float
    n_control_cells: float
    guide_id: str | None = None
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = len(official_axis())
        for name in ("delta", "se", "observed"):
            arr = getattr(self, name)
            if arr.shape != (n,):
                raise ValueError(f"{name} has shape {arr.shape}, expected ({n},)")
        if np.any(self.se[self.observed] < 0):
            raise ValueError("standard errors must be non-negative")
        if self.n_cells < 0 or self.n_control_cells < 0:
            raise ValueError("cell counts must be non-negative")

    @property
    def key(self) -> tuple[str, str, str, str | None]:
        return (self.source, self.context, self.target, self.guide_id)

    def z(self, floor: float = 1e-9) -> np.ndarray:
        """delta / se, zero where unobserved. A crude per-gene signal-to-noise."""
        out = np.zeros_like(self.delta)
        m = self.observed & (self.se > floor)
        out[m] = self.delta[m] / self.se[m]
        return out

    def shrunk(self, prior_sd: float) -> np.ndarray:
        """James-Stein style shrinkage of `delta` toward zero.

        Each gene is scaled by `prior_sd^2 / (prior_sd^2 + se^2)`, the posterior
        mean under a zero-centred normal prior. A gene measured with a standard
        error far above the prior spread is shrunk hard; a well-measured one is
        left alone. Unobserved genes stay at zero **and stay masked** -- the
        caller must keep reading `observed`.
        """
        if prior_sd <= 0:
            raise ValueError("prior_sd must be positive")
        w = prior_sd**2 / (prior_sd**2 + np.square(self.se))
        out = np.zeros_like(self.delta)
        out[self.observed] = (self.delta * w)[self.observed]
        return out


@dataclass
class SignatureSet:
    """A collection of signatures, queryable by target and context."""

    signatures: list[Signature] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.signatures)

    def __iter__(self):
        return iter(self.signatures)

    def add(self, sig: Signature) -> None:
        self.signatures.append(sig)

    @property
    def targets(self) -> tuple[str, ...]:
        return tuple(sorted({s.target for s in self.signatures}))

    @property
    def contexts(self) -> tuple[str, ...]:
        return tuple(sorted({s.context for s in self.signatures}))

    def by_target(self, target: str) -> list[Signature]:
        return [s for s in self.signatures if s.target == target]

    def filter(self, *, source=None, context=None, targets=None) -> SignatureSet:
        out = self.signatures
        if source is not None:
            out = [s for s in out if s.source == source]
        if context is not None:
            out = [s for s in out if s.context == context]
        if targets is not None:
            keep = set(targets)
            out = [s for s in out if s.target in keep]
        return SignatureSet(list(out))

    def stack(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[str, ...]]:
        """(delta, se, observed, targets) as arrays, one row per signature."""
        if not self.signatures:
            n = len(official_axis())
            empty = np.zeros((0, n))
            return empty, empty, np.zeros((0, n), dtype=bool), ()
        delta = np.vstack([s.delta for s in self.signatures])
        se = np.vstack([s.se for s in self.signatures])
        obs = np.vstack([s.observed for s in self.signatures])
        return delta, se, obs, tuple(s.target for s in self.signatures)

    def collapse_guides(self, *, min_guides: int = 1) -> SignatureSet:
        """Combine guide-level signatures of the same target into one estimate.

        Genes are combined by inverse-variance weighting across guides. The
        returned standard error is the **larger** of

        * the inverse-variance standard error (the sampling floor), and
        * the standard error of the mean computed from the spread between
          guides (which absorbs off-target and guide-efficiency variation),

        so replication can only widen the interval, never narrow it below what
        the guides actually agree on. `meta["n_guides"]` and
        `meta["between_guide_sd"]` are kept for diagnostics.
        """
        out = SignatureSet()
        groups: dict[tuple[str, str, str], list[Signature]] = {}
        for s in self.signatures:
            groups.setdefault((s.source, s.context, s.target), []).append(s)

        for (source, context, target), members in sorted(groups.items()):
            if len(members) < min_guides:
                continue
            delta = np.vstack([m.delta for m in members])
            se = np.vstack([m.se for m in members])
            obs = np.vstack([m.observed for m in members])

            w = np.where(obs & (se > 0), 1.0 / np.maximum(np.square(se), 1e-24), 0.0)
            wsum = w.sum(axis=0)
            any_obs = wsum > 0

            comb = np.zeros(delta.shape[1])
            comb[any_obs] = (w * delta).sum(axis=0)[any_obs] / wsum[any_obs]

            se_iv = np.zeros(delta.shape[1])
            se_iv[any_obs] = np.sqrt(1.0 / wsum[any_obs])

            n_obs = obs.sum(axis=0)
            between = np.zeros(delta.shape[1])
            multi = n_obs > 1
            if multi.any():
                resid = np.where(obs, delta - comb[None, :], 0.0)
                ss = np.square(resid).sum(axis=0)
                between[multi] = np.sqrt(
                    ss[multi] / (n_obs[multi] - 1) / n_obs[multi]
                )

            combined_se = np.maximum(se_iv, between)
            out.add(
                Signature(
                    source=source,
                    context=context,
                    target=target,
                    delta=comb,
                    se=combined_se,
                    observed=any_obs,
                    n_cells=float(sum(m.n_cells for m in members)),
                    n_control_cells=float(
                        np.mean([m.n_control_cells for m in members])
                    ),
                    guide_id=None,
                    meta={
                        "n_guides": len(members),
                        "between_guide_sd": float(
                            np.median(between[multi]) if multi.any() else np.nan
                        ),
                        "guide_ids": [m.guide_id for m in members],
                    },
                )
            )
        return out

    def summary(self) -> dict:
        """Small JSON-safe description for a run manifest."""
        delta, se, obs, _ = self.stack()
        if len(self) == 0:
            return {"n_signatures": 0}
        finite = obs & np.isfinite(delta)
        return {
            "n_signatures": len(self),
            "n_targets": len(self.targets),
            "n_contexts": len(self.contexts),
            "sources": sorted({s.source for s in self.signatures}),
            "median_observed_genes": float(np.median(obs.sum(axis=1))),
            "median_abs_delta": float(np.median(np.abs(delta[finite]))) if finite.any() else None,
            "median_se": float(np.median(se[finite])) if finite.any() else None,
            "median_n_cells": float(np.median([s.n_cells for s in self.signatures])),
        }

    def write_npz(self, path: Path) -> Path:
        """Persist the set. Arrays go to .npz, the row table to a sidecar JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        delta, se, obs, _ = self.stack()
        np.savez_compressed(path, delta=delta, se=se, observed=obs)
        rows = [
            {
                "source": s.source,
                "context": s.context,
                "target": s.target,
                "guide_id": s.guide_id,
                "n_cells": s.n_cells,
                "n_control_cells": s.n_control_cells,
                "meta": s.meta,
            }
            for s in self.signatures
        ]
        path.with_suffix(".rows.json").write_text(
            json.dumps(rows, indent=2, default=str), encoding="utf-8"
        )
        return path

    @classmethod
    def read_npz(cls, path: Path) -> SignatureSet:
        path = Path(path)
        rows = json.loads(path.with_suffix(".rows.json").read_text(encoding="utf-8"))
        # Materialise each array ONCE. Indexing an NpzFile decompresses the whole
        # member on every access, so `arrays["delta"][i]` inside the loop would
        # decompress an (n x 18,533) matrix per signature -- minutes of CPU and a
        # transient allocation per row that exhausts an 8 GB machine.
        with np.load(path) as handle:
            delta = handle["delta"]
            se = handle["se"]
            observed = handle["observed"]
        out = cls()
        for i, row in enumerate(rows):
            out.add(
                Signature(
                    source=row["source"],
                    context=row["context"],
                    target=row["target"],
                    delta=delta[i],
                    se=se[i],
                    observed=observed[i],
                    n_cells=row["n_cells"],
                    n_control_cells=row["n_control_cells"],
                    guide_id=row.get("guide_id"),
                    meta=row.get("meta", {}),
                )
            )
        return out


def delta_from_pseudobulk(
    perturbed: AlignedMatrix,
    control_profile: np.ndarray,
    control_observed: np.ndarray,
    *,
    library_sizes: np.ndarray,
    control_library_size: float,
    pseudocount_cpm: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """log2 fold change and its Poisson standard error, on the official axis.

    Args:
        perturbed: aligned summed counts, one row per perturbation.
        control_profile: (n_axis,) summed counts of the matched control rows.
        control_observed: (n_axis,) bool mask of the control.
        library_sizes: (n_rows,) total counts of each perturbed row **in the
            source's own feature space**, not the axis subset. Using the source
            total keeps CPM comparable with the control, which is computed the
            same way.
        control_library_size: total counts of the control, same convention.
        pseudocount_cpm: added to both CPM values before the ratio.

    Returns:
        (delta, se, observed), each (n_rows, n_axis) except `observed` which is
        (n_axis,) -- the intersection of source and control coverage.
    """
    counts = perturbed.values
    lib = np.asarray(library_sizes, dtype=np.float64).reshape(-1, 1)
    if lib.shape[0] != counts.shape[0]:
        raise ValueError("one library size per perturbed row is required")
    if np.any(lib <= 0) or control_library_size <= 0:
        raise ValueError("library sizes must be positive")

    observed = perturbed.observed & control_observed

    q = 1e6 / lib                      # CPM per single UMI, perturbed
    q0 = 1e6 / control_library_size    # CPM per single UMI, control
    cpm = 1e6 * counts / lib
    cpm0 = 1e6 * np.asarray(control_profile, dtype=np.float64) / control_library_size

    denom = cpm + pseudocount_cpm
    denom0 = cpm0 + pseudocount_cpm
    delta = np.log2(denom / denom0[None, :])

    var = (cpm * q) / np.square(denom) + (cpm0 * q0) / np.square(denom0)[None, :]
    se = np.sqrt(np.maximum(var, 0.0)) / LN2

    delta = np.where(observed[None, :], delta, 0.0)
    se = np.where(observed[None, :], se, 0.0)
    return delta, se, observed
