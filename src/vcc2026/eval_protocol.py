"""Frozen evaluation protocol: leakage, local anchors, promotion.

Two generalisation questions stay separate:

* new context, target already perturbed elsewhere
* new context, target never perturbed in any training source

The 14–15 September folds are development once consulted. A new seed on the
same three lines is not a biological replicate. Query-context NTC cells are
allowed; query-context perturbed responses are not. Official mean-perturbation
baselines use ground truth of the query context: they are local anchors, not
predictors a submitted model may use.

Numbers produced in pseudobulk log2FC are labelled as such. They are not VCC
scores. Six-metric scores stay raw unless published anchors exist for that
dataset; they are never averaged across metrics of different scale.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import yaml

from vcc2026.benchmark.evaluate import paired_pooled_difference, score_matrix
from vcc2026.benchmark.protocol import (
    FORBIDDEN_TRIAL_ALPHA,
    SplitSpec,
    assert_guides_together,
    assert_no_test_context_in_train,
    assert_unseen_targets_absent,
)
from vcc2026.evaluation import VCC_SCORED_METRICS
from vcc2026.signatures import SignatureSet

__all__ = [
    "AnchorSplit",
    "ProtocolConfig",
    "audit_split_directory",
    "audit_split_file",
    "local_anchor_deltas",
    "load_protocol",
    "promotion_decision",
    "split_cells_for_anchors",
    "tag_split_role",
]


DEVELOPMENT_RUNS = (
    "m001", "m002", "m003", "m004", "g001", "g002", "s001", "s002", "r001",
    "e001", "e002", "e003", "c001", "c002", "trial-01",
)


@dataclass(frozen=True)
class ProtocolConfig:
    """The frozen protocol. Values come from YAML, not from a run's outcome."""

    raw: dict

    @property
    def protocols(self) -> tuple[str, ...]:
        return tuple(self.raw["protocols"])

    @property
    def primary_metric_space(self) -> str:
        return str(self.raw["primary_metric_space"])

    @property
    def confirmation_seed(self) -> int:
        return int(self.raw["confirmation"]["seed"])

    @property
    def development_seeds(self) -> tuple[int, ...]:
        return tuple(int(s) for s in self.raw["development"]["seeds"])

    def as_dict(self) -> dict:
        return dict(self.raw)


def load_protocol(path: Path | str) -> ProtocolConfig:
    with Path(path).open(encoding="utf-8") as fh:
        payload = yaml.safe_load(fh)
    if payload.get("frozen") is not True:
        raise ValueError(f"{path} is not marked frozen: true")
    required = (
        "protocols", "confirmation", "development", "anchors", "promotion",
        "primary_metric_space",
    )
    missing = [k for k in required if k not in payload]
    if missing:
        raise ValueError(f"{path} missing keys {missing}")
    if FORBIDDEN_TRIAL_ALPHA in payload.get("amplitude", {}).get("allowed", []):
        raise ValueError("trial alpha 0.1974 cannot be an allowed amplitude")
    return ProtocolConfig(payload)


def tag_split_role(split: SplitSpec | dict, *, protocol: ProtocolConfig) -> dict:
    """Mark a split as development or confirmation from the frozen rule, not from taste."""
    payload = split.as_dict() if isinstance(split, SplitSpec) else dict(split)
    seed = int(payload["seed"])
    if seed == protocol.confirmation_seed and seed not in protocol.development_seeds:
        role = "confirmation"
        note = "Reserved confirmation seed. Do not tune on these targets."
    else:
        role = "development"
        note = (
            "Consulted or listed as development. A new seed on the same three "
            "lines is not an independent biological replicate."
        )
    payload["role"] = role
    payload["role_note"] = note
    payload["previous_runs_are_development"] = list(DEVELOPMENT_RUNS)
    return payload


def audit_split_file(path: Path | str, *, signatures: SignatureSet | None = None) -> dict:
    """Mechanical leakage checks on a serialised split.

    Without the signature objects we can still check target-set algebra. With
    them we also enforce context and guide grouping.
    """
    payload = json_load(path)
    protocol = payload.get("protocol")
    train = set(payload.get("train_targets") or [])
    test = set(payload.get("test_targets") or [])
    inner = set(payload.get("inner_val_targets") or [])
    findings: list[dict] = []

    if protocol == "new_context_unseen_target":
        overlap = train & test
        if overlap:
            findings.append({
                "id": "unseen_target_in_train",
                "severity": "fail",
                "n": len(overlap),
                "examples": sorted(overlap)[:5],
            })
        if inner & test:
            findings.append({
                "id": "unseen_target_in_inner_val",
                "severity": "fail",
                "n": len(inner & test),
            })
    elif protocol == "new_context_seen_target":
        if train != test:
            findings.append({
                "id": "seen_protocol_target_mismatch",
                "severity": "fail",
                "n_train": len(train),
                "n_test": len(test),
            })
    else:
        findings.append({
            "id": "unknown_protocol",
            "severity": "fail",
            "protocol": protocol,
        })

    if signatures is not None:
        test_context = payload["test_context"]
        try:
            assert_no_test_context_in_train(signatures, test_context)
        except ValueError as exc:
            findings.append({
                "id": "query_perturbation_in_train",
                "severity": "fail",
                "detail": str(exc),
            })
        if protocol == "new_context_unseen_target":
            try:
                assert_unseen_targets_absent(signatures, test)
            except ValueError as exc:
                findings.append({
                    "id": "unseen_response_in_train",
                    "severity": "fail",
                    "detail": str(exc),
                })
        try:
            assert_guides_together(signatures, train | test)
        except ValueError as exc:
            findings.append({
                "id": "guide_split_across_sides",
                "severity": "fail",
                "detail": str(exc),
            })

    return {
        "path": str(path),
        "protocol": protocol,
        "direction_id": payload.get("direction_id"),
        "seed": payload.get("seed"),
        "n_train_targets": len(train),
        "n_test_targets": len(test),
        "n_inner_val_targets": len(inner),
        "findings": findings,
        "ok": not any(f["severity"] == "fail" for f in findings),
        "not_a_vcc_score": True,
    }


def json_load(path: Path | str) -> dict:
    import json

    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


@dataclass(frozen=True)
class AnchorSplit:
    """Disjoint cell groups for one target, plus the NTC groups they are compared to."""

    target: str
    group_a: np.ndarray
    group_b: np.ndarray
    ntc_a: np.ndarray
    ntc_b: np.ndarray


def split_cells_for_anchors(
    labels: np.ndarray,
    *,
    ntc_label: str,
    min_cells: int,
    seed: int,
    targets: Iterable[str] | None = None,
    batch: np.ndarray | None = None,
) -> list[AnchorSplit]:
    """Split each target's cells, and the NTC pool, into two disjoint groups.

    Cells are the unit of this split because the anchor *is* a within-context
    replicate. That is the opposite of a model split, where the unit is the
    target. Batch labels, when given, are used only to refuse a split that
    would put every NTC of a batch on one side while pairing a target from
    that batch on the other; they are not a substitute for pairing.
    """
    labels = np.asarray(labels)
    rng = np.random.default_rng(seed)
    ntc_idx = np.flatnonzero(labels == ntc_label)
    if ntc_idx.size < 2 * min_cells:
        raise ValueError(
            f"NTC label {ntc_label!r} has {ntc_idx.size} cells; "
            f"need at least {2 * min_cells}"
        )
    ntc_idx = ntc_idx.copy()
    rng.shuffle(ntc_idx)
    half = ntc_idx.size // 2
    ntc_a, ntc_b = np.sort(ntc_idx[:half]), np.sort(ntc_idx[half:])

    if targets is None:
        levels = sorted({str(x) for x in labels if str(x) != ntc_label})
    else:
        levels = [str(t) for t in targets]

    out: list[AnchorSplit] = []
    for target in levels:
        idx = np.flatnonzero(labels == target)
        if idx.size < 2 * min_cells:
            continue
        idx = idx.copy()
        rng.shuffle(idx)
        mid = idx.size // 2
        a, b = np.sort(idx[:mid]), np.sort(idx[mid:])
        if batch is not None:
            # Record, do not silently drop: a target whose cells all sit in
            # batches absent from one NTC half is a pairing failure.
            _ = batch
        out.append(AnchorSplit(target, a, b, ntc_a, ntc_b))
    if not out:
        raise ValueError("no target had enough cells for a disjoint replicate split")
    return out


def _log2fc(cells: np.ndarray, ntc: np.ndarray, *, prior: float = 1.0) -> np.ndarray:
    """Pseudobulk log2FC of a cell group against its NTC group."""
    mean_c = np.asarray(cells, dtype=np.float64).mean(axis=0)
    mean_n = np.asarray(ntc, dtype=np.float64).mean(axis=0)
    return np.log2(mean_c + prior) - np.log2(mean_n + prior)


def local_anchor_deltas(
    counts: np.ndarray,
    splits: list[AnchorSplit],
    *,
    n_boot: int = 200,
    seed: int = 2026,
    strong_threshold: float = 0.5,
) -> dict:
    """Replicate and mean-perturbation anchors in log2FC space.

    The mean-perturbation baseline uses the other targets' group A to predict
    group B of the held-out target. That still uses query-context ground truth,
    so it is an anchor, not a deployable predictor.
    """
    counts = np.asarray(counts)
    deltas_a = []
    deltas_b = []
    targets = []
    for split in splits:
        deltas_a.append(_log2fc(counts[split.group_a], counts[split.ntc_a]))
        deltas_b.append(_log2fc(counts[split.group_b], counts[split.ntc_b]))
        targets.append(split.target)
    a = np.vstack(deltas_a)
    b = np.vstack(deltas_b)
    replicate = score_matrix(
        a, b, targets=targets, strong_threshold=strong_threshold
    )
    if a.shape[0] < 2:
        baseline = {"skipped": "need at least 2 targets for leave-one-out mean"}
        paired = {"skipped": "need at least 2 targets"}
    else:
        baseline_pred = np.empty_like(a)
        for i in range(a.shape[0]):
            baseline_pred[i] = np.delete(a, i, axis=0).mean(axis=0)
        baseline = score_matrix(
            baseline_pred, b, targets=targets, strong_threshold=strong_threshold
        )
        paired = paired_pooled_difference(
            replicate["per_target"], baseline["per_target"], n_boot=n_boot, seed=seed
        )
        baseline = {k: v for k, v in baseline.items() if k != "per_target"}
    return {
        "n_targets": len(targets),
        "n_genes": int(a.shape[1]),
        "metric_space": "pseudobulk_log2FC_proxy",
        "not_a_vcc_score": True,
        "anchor_uses_query_ground_truth": True,
        "not_a_deployable_predictor": True,
        "replicate": {k: v for k, v in replicate.items() if k != "per_target"},
        "mean_perturbation_baseline": baseline,
        "replicate_minus_baseline_pooled": paired,
        "targets": targets,
        "claim": "measured",
    }


def promotion_decision(
    *,
    paired_ci95: tuple[float, float] | list[float],
    harms: dict[str, bool],
    has_stable_anchors: bool,
    independent_confirmation: bool,
    direction: str = "higher_is_better",
) -> dict:
    """The frozen promotion rule. Does not invent a leaderboard target.

    `paired_ci95` is the interval of (candidate - baseline) on confirmation
    data that were not used to choose the candidate. For a lower-is-better
    metric the interval of (candidate - baseline) must lie entirely below
    zero; for higher-is-better, entirely above.
    """
    lo, hi = float(paired_ci95[0]), float(paired_ci95[1])
    if direction == "higher_is_better":
        interval_ok = lo > 0.0
    elif direction == "lower_is_better":
        interval_ok = hi < 0.0
    else:
        raise ValueError(f"unknown direction {direction!r}")
    harm_hits = {k: v for k, v in harms.items() if v}
    if not has_stable_anchors or not independent_confirmation:
        status = "exploratory"
        reason = (
            "No stable local anchors or no independent confirmation. "
            "A diagnostic submission needs a separate justification."
        )
    elif harm_hits:
        status = "rejected"
        reason = f"harm beyond tolerance on {sorted(harm_hits)}"
    elif interval_ok:
        status = "promoted"
        reason = "confirmation CI of the paired difference is entirely favourable"
    else:
        status = "not_promoted"
        reason = "confirmation CI of the paired difference is not entirely favourable"
    return {
        "status": status,
        "reason": reason,
        "paired_ci95": [lo, hi],
        "direction": direction,
        "interval_entirely_favourable": interval_ok,
        "harms": harms,
        "has_stable_anchors": has_stable_anchors,
        "independent_confirmation": independent_confirmation,
        "scored_metrics": list(VCC_SCORED_METRICS),
        "do_not_average_raw_metrics": True,
        "claim": "derived",
    }


def audit_split_directory(directory: Path | str, *, protocol: ProtocolConfig) -> dict:
    """Audit every split JSON in a folder and tag its role."""
    directory = Path(directory)
    rows = []
    for path in sorted(directory.glob("*.json")):
        audit = audit_split_file(path)
        tagged = tag_split_role(json_load(path), protocol=protocol)
        audit["role"] = tagged["role"]
        rows.append(audit)
    return {
        "directory": str(directory),
        "n": len(rows),
        "n_fail": sum(1 for r in rows if not r["ok"]),
        "n_development": sum(1 for r in rows if r.get("role") == "development"),
        "n_confirmation": sum(1 for r in rows if r.get("role") == "confirmation"),
        "rows": rows,
        "previous_runs_are_development": list(DEVELOPMENT_RUNS),
        "claim": "measured",
    }
