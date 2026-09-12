"""Splits that answer the three generalisation questions separately.

The competition is zero-shot on both axes at once: unseen targets in unseen
contexts. A split that puts some cells of target `t` in train and the rest in
test measures nothing relevant -- it measures how well we can average cells.
So the unit of splitting is never the cell.

Three questions, three splitters:

* `held_out_targets` -- can we predict a target we have never perturbed?
  Splits whole targets, carrying every guide and every TSS row of a target to
  the same side. Guides of the same target are near-duplicates, and letting one
  guide of target `t` train while another tests is the same leak as splitting
  cells, one level up.
* `held_out_groups` -- can we predict in a donor, study or batch we have not
  seen? Splits on a metadata key.
* `held_out_context` -- can we predict in a cell context we have not seen?
  Splits on the signature's context.

Two rules are enforced rather than documented, because both have already been
recorded as project decisions and both are invisible once broken:

* **Weak and null targets stay in the test set** (D-011). Dropping targets whose
  effect was not detectable selects on the outcome, leaves only the easy cases
  and inflates every number that follows. `min_cells` filters what we are
  willing to call a *measurement*, and is applied when signatures are built; it
  is not a filter on what we are willing to be *scored* on.
* **The same biological material never lands on both sides.** `assert_disjoint`
  is called by every splitter and raises rather than warns.

Bootstrap resampling is over targets, guides or groups -- never over cells,
which are not independent replicates of a perturbation effect.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .signatures import SignatureSet

__all__ = [
    "Split",
    "held_out_targets",
    "held_out_groups",
    "held_out_context",
    "bootstrap_targets",
    "assert_disjoint",
]


@dataclass(frozen=True)
class Split:
    """One train/test division, described well enough to be reproduced."""

    train: SignatureSet
    test: SignatureSet
    kind: str
    fold: int
    n_folds: int
    seed: int | None = None

    def describe(self) -> dict:
        return {
            "kind": self.kind,
            "fold": self.fold,
            "n_folds": self.n_folds,
            "seed": self.seed,
            "n_train_signatures": len(self.train),
            "n_test_signatures": len(self.test),
            "n_train_targets": len(self.train.targets),
            "n_test_targets": len(self.test.targets),
        }


def assert_disjoint(split: Split) -> None:
    """Raise if any target appears on both sides. Never downgrade this to a warning."""
    overlap = set(split.train.targets) & set(split.test.targets)
    if overlap:
        raise ValueError(
            f"{split.kind} fold {split.fold}: {len(overlap)} target(s) on both "
            f"sides of the split, e.g. {sorted(overlap)[:5]}"
        )


def held_out_targets(
    signatures: SignatureSet, *, n_folds: int = 5, seed: int = 2026
) -> list[Split]:
    """K folds over whole targets. Every guide of a target moves together."""
    targets = list(signatures.targets)
    if len(targets) < n_folds:
        raise ValueError(f"{len(targets)} targets cannot make {n_folds} folds")
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(targets))
    assignment = {targets[int(t)]: i % n_folds for i, t in enumerate(order)}

    splits = []
    for fold in range(n_folds):
        test_t = {t for t, f in assignment.items() if f == fold}
        train_t = {t for t, f in assignment.items() if f != fold}
        split = Split(
            train=signatures.filter(targets=train_t),
            test=signatures.filter(targets=test_t),
            kind="held_out_target",
            fold=fold,
            n_folds=n_folds,
            seed=seed,
        )
        assert_disjoint(split)
        splits.append(split)
    return splits


def held_out_groups(
    signatures: SignatureSet, group_of, *, seed: int = 2026
) -> list[Split]:
    """Leave-one-group-out, where `group_of(signature)` names donor/study/batch.

    Targets may legitimately appear in several groups. That is the point of the
    split -- the question is whether a target's effect measured in donor 1
    transfers to donor 2 -- so `assert_disjoint` is not applied on targets here.
    """
    groups = sorted({group_of(s) for s in signatures})
    if len(groups) < 2:
        raise ValueError(f"need at least 2 groups to hold one out, got {groups}")
    splits = []
    for fold, g in enumerate(groups):
        train = SignatureSet([s for s in signatures if group_of(s) != g])
        test = SignatureSet([s for s in signatures if group_of(s) == g])
        splits.append(
            Split(train=train, test=test, kind=f"held_out_group:{g}",
                  fold=fold, n_folds=len(groups), seed=seed)
        )
    return splits


def held_out_context(signatures: SignatureSet, *, seed: int = 2026) -> list[Split]:
    """Leave-one-context-out: the closest analogue of the competition task."""
    return held_out_groups(signatures, lambda s: s.context, seed=seed)


def bootstrap_targets(
    targets, *, n_boot: int = 200, seed: int = 2026
) -> list[np.ndarray]:
    """Resample target labels with replacement.

    Targets, not cells. Cells within a perturbation share a guide, a batch and a
    knockdown efficiency; treating them as independent replicates produces
    confidence intervals that are far too narrow.
    """
    targets = list(targets)
    if not targets:
        raise ValueError("no targets to bootstrap")
    rng = np.random.default_rng(seed)
    return [rng.integers(0, len(targets), size=len(targets)) for _ in range(n_boot)]
