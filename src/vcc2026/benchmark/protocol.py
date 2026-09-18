"""Uniform interfaces: descriptors, splits, fit/predict/save, no leakage.

Two generalisation questions are kept separate on purpose:

* `new_context_seen_target` — the target was perturbed in training contexts;
  the test *context* is new. Same-target guides stay together because the unit
  is the target, not the cell.
* `new_context_unseen_target` — that target's perturbative responses are
  excluded from every training source, including internal calibration.

Leave-one-context-out with two perturbed contexts leaves a single training
context. That is a transfer test, not a demonstration that the model learned
a general context dependence. The split records that limitation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
import yaml

from vcc2026.signatures import SignatureSet

__all__ = [
    "DeltaModel",
    "FeatureSpec",
    "SplitSpec",
    "TrainArrays",
    "load_yaml_config",
    "assert_no_test_context_in_train",
    "assert_unseen_targets_absent",
    "assert_guides_together",
    "make_split",
    "FORBIDDEN_TRIAL_ALPHA",
]


FORBIDDEN_TRIAL_ALPHA = 0.1974


@dataclass(frozen=True)
class FeatureSpec:
    """One descriptor column, with where it came from and when it is allowed."""

    name: str
    provenance: str
    derived_from_perturbative_response: bool
    uses_query_ntc: bool
    allowed_in_unseen_target: bool


@dataclass
class SplitSpec:
    """One train/test division, serialisable, with the limitation written down."""

    protocol: str
    direction_id: str
    train_context: str
    test_context: str
    train_sources: tuple[str, ...]
    test_source: str
    train_targets: tuple[str, ...]
    test_targets: tuple[str, ...]
    inner_val_targets: tuple[str, ...]
    seed: int
    n_train_contexts: int
    context_dependence_identifiable: bool
    uses_query_ntc: bool
    note: str
    internal_dest_source: str | None = None

    def as_dict(self) -> dict:
        return {
            "protocol": self.protocol,
            "direction_id": self.direction_id,
            "train_context": self.train_context,
            "test_context": self.test_context,
            "train_sources": list(self.train_sources),
            "test_source": self.test_source,
            "n_train_targets": len(self.train_targets),
            "n_test_targets": len(self.test_targets),
            "n_inner_val_targets": len(self.inner_val_targets),
            "train_targets": list(self.train_targets),
            "test_targets": list(self.test_targets),
            "inner_val_targets": list(self.inner_val_targets),
            "seed": self.seed,
            "n_train_contexts": self.n_train_contexts,
            "context_dependence_identifiable": self.context_dependence_identifiable,
            "uses_query_ntc": self.uses_query_ntc,
            "internal_dest_source": self.internal_dest_source,
            "note": self.note,
            "limitation": (
                "A test that holds out one of two perturbed contexts leaves a "
                "single training context. That measures transfer, not general "
                "learning of context dependence."
                if self.n_train_contexts < 2
                else "Training sees more than one biological context."
            ),
        }


@dataclass
class TrainArrays:
    """Dense arrays already restricted to the measured gene universe."""

    X: np.ndarray
    Y: np.ndarray
    targets: tuple[str, ...]
    feature_names: tuple[str, ...]
    feature_specs: tuple[FeatureSpec, ...]
    uses_context_features: bool
    n_unique_context_rows: int

    def __post_init__(self) -> None:
        if self.X.shape[0] != self.Y.shape[0] or self.X.shape[0] != len(self.targets):
            raise ValueError("X, Y and targets must share the row axis")
        if self.X.shape[1] != len(self.feature_names):
            raise ValueError("X columns must match feature_names")


class DeltaModel(Protocol):
    """Fit, predict, persist. Every compared arm implements this."""

    name: str
    uses_context: bool

    def fit(self, arrays: TrainArrays) -> "DeltaModel":
        ...

    def predict_delta(self, X: np.ndarray) -> np.ndarray:
        ...

    def save(self, path: Path) -> None:
        ...

    def parameter_counts(self) -> dict:
        ...


def load_yaml_config(path: Path | str) -> dict:
    with Path(path).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def assert_no_test_context_in_train(train: SignatureSet, test_context: str) -> None:
    leaked = [s for s in train if s.context == test_context]
    if leaked:
        raise ValueError(
            f"{len(leaked)} training signature(s) carry test context "
            f"{test_context!r}; perturbed responses of the query context "
            f"must not be used for fitting or selection"
        )


def assert_unseen_targets_absent(train: SignatureSet, unseen: set[str]) -> None:
    leaked = set(train.targets) & set(unseen)
    if leaked:
        raise ValueError(
            f"{len(leaked)} unseen-protocol target(s) still in training, "
            f"e.g. {sorted(leaked)[:5]}"
        )


def assert_guides_together(sigs: SignatureSet, side_targets: set[str]) -> None:
    """Every guide of a target is on the same side, or the split is broken."""
    for s in sigs:
        if s.target in side_targets:
            continue
        raise ValueError(
            f"guide {s.guide_id!r} of target {s.target!r} is not with its target"
        )


def _partition(targets: list[str], fraction: float, seed: int, *, salt: int) -> tuple[list[str], list[str]]:
    if not 0.0 < fraction < 1.0:
        raise ValueError("fraction must be in (0, 1)")
    rng = np.random.default_rng(int(seed) + salt)
    order = rng.permutation(len(targets))
    n_hold = max(1, int(round(len(targets) * fraction)))
    n_hold = min(n_hold, len(targets) - 1)
    hold = [targets[int(i)] for i in order[:n_hold]]
    keep = [targets[int(i)] for i in order[n_hold:]]
    return sorted(keep), sorted(hold)


def make_split(
    *,
    protocol: str,
    direction: dict,
    shared_targets: list[str],
    seed: int,
    unseen_fraction: float,
    inner_val_fraction: float,
    uses_query_ntc: bool = True,
) -> SplitSpec:
    """Build a split. Target assignment is seed-controlled and effect-blind."""
    if protocol not in {"new_context_seen_target", "new_context_unseen_target"}:
        raise ValueError(f"unknown protocol: {protocol!r}")
    shared = list(shared_targets)
    if len(shared) < 10:
        raise ValueError(f"need at least 10 shared targets, got {len(shared)}")

    if protocol == "new_context_seen_target":
        train_t = sorted(shared)
        test_t = sorted(shared)
        note = (
            "Same targets in train and test; the split is the context. "
            "Test-context perturbed responses are not in training."
        )
    else:
        train_t, test_t = _partition(shared, unseen_fraction, seed, salt=11)
        note = (
            "Test targets are excluded from every training response, including "
            "internal calibration. Descriptors derived from those responses "
            "are forbidden."
        )

    fit_t, val_t = _partition(train_t, inner_val_fraction, seed, salt=23)
    # Inner val stays inside training targets; the model may refit on all
    # train_t after selection. fit_t is recorded as inner_val's complement
    # via inner_val_targets only.
    _ = fit_t

    return SplitSpec(
        protocol=protocol,
        direction_id=str(direction["id"]),
        train_context=str(direction["train_context"]),
        test_context=str(direction["test_context"]),
        train_sources=tuple(direction["train_sources"]),
        test_source=str(direction["test_source"]),
        train_targets=tuple(train_t),
        test_targets=tuple(test_t),
        inner_val_targets=tuple(val_t),
        seed=seed,
        n_train_contexts=int(direction.get("n_train_contexts", 1)),
        context_dependence_identifiable=bool(
            direction.get("context_dependence_identifiable", False)
        ),
        uses_query_ntc=uses_query_ntc,
        note=note + " " + str(direction.get("note", "")),
        internal_dest_source=direction.get("internal_dest_source"),
    )


def reject_forbidden_alpha(alpha: float, *, forbidden: float = FORBIDDEN_TRIAL_ALPHA) -> None:
    """The trial alpha saw both K562 and RPE1. It must not enter a LOCO fold."""
    if abs(float(alpha) - float(forbidden)) < 1e-9:
        raise ValueError(
            f"alpha={alpha} is the trial value calibrated on K562→RPE1 using "
            f"both contexts. It is forbidden in a fold that holds one of them "
            f"out. Use a predetermined rule or an internal pair that does not "
            f"include the test context."
        )
