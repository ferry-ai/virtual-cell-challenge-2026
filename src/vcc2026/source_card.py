"""Mandatory per-source card. Missing fields stay missing.

The operational plan requires one card per candidate source before any
acquisition decision. A filled-in guess is worse than a null: it looks like
evidence. Every field is therefore either a measured/cited value with a
provenance, or None.

This module does not download data and does not declare coverage from study
scale. Coverage of the 300-gene panel is recorded only when an actual target
list was read.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "Field",
    "SourceCard",
    "empty_card",
    "validate_card",
]


CLAIM_TYPES = ("measured", "cited", "derived", "assumed", "missing")
PERTURBATION_CLASSES = (
    "CRISPRi", "CRISPR_KO", "CRISPRa", "drug", "combo_genetic_chemical",
    "observational", "unknown",
)


@dataclass(frozen=True)
class Field:
    """One card entry: a value, or an explicit absence, never both implied."""

    value: Any
    claim: str
    source: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if self.claim not in CLAIM_TYPES:
            raise ValueError(f"unknown claim type {self.claim!r}")
        if self.claim == "missing" and self.value is not None:
            raise ValueError("a missing field cannot carry a value")
        if self.claim != "missing" and self.value is None:
            raise ValueError(f"{self.claim} field needs a value, or claim='missing'")

    def as_dict(self) -> dict:
        return {
            "value": self.value,
            "claim": self.claim,
            "source": self.source,
            "note": self.note,
        }


def _missing(note: str | None = None) -> Field:
    return Field(value=None, claim="missing", source=None, note=note)


@dataclass
class SourceCard:
    """The audit sheet required before a source may be acquired or adopted.

    Acquisition (file on disk, NTC pairing, budget) is not the same as
    adoption (ablation with vs without the source on frozen splits).
    """

    source_id: str
    title: str
    study_id: Field
    version: Field
    primary_url: Field
    license: Field
    perturbation_class: Field
    cell_context: Field
    donor_state_batch: Field
    n_targets: Field
    id_mapping: Field
    count_kind: Field
    ntc_field: Field
    guides: Field
    cells_per_target: Field
    n_genes_measured: Field
    remote_bytes: Field
    temporary_bytes: Field
    checksum: Field
    panel_overlap: Field
    training_overlap: Field
    extra_target_sample: Field = field(default_factory=lambda: _missing(
        "no extra-target sample retained"
    ))
    decision: str = "pending"
    decision_note: str = ""
    recorded_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    def __post_init__(self) -> None:
        if self.decision not in {
            "pending", "probe", "acquire", "defer", "exclude", "adopt",
        }:
            raise ValueError(f"unknown decision {self.decision!r}")
        pert = self.perturbation_class
        if pert.claim != "missing" and pert.value not in PERTURBATION_CLASSES:
            raise ValueError(
                f"perturbation_class {pert.value!r} not in {PERTURBATION_CLASSES}"
            )

    def as_dict(self) -> dict:
        out = asdict(self)
        for key, val in list(out.items()):
            if isinstance(val, dict) and "claim" in val:
                continue
            if hasattr(getattr(self, key), "as_dict"):
                out[key] = getattr(self, key).as_dict()
        return out


def empty_card(source_id: str, title: str) -> SourceCard:
    """A card with every scientific field marked missing. Fill from evidence."""
    return SourceCard(
        source_id=source_id,
        title=title,
        study_id=_missing(),
        version=_missing(),
        primary_url=_missing(),
        license=_missing(),
        perturbation_class=_missing(),
        cell_context=_missing(),
        donor_state_batch=_missing(),
        n_targets=_missing("do not infer from study scale"),
        id_mapping=_missing(),
        count_kind=_missing(),
        ntc_field=_missing(),
        guides=_missing(),
        cells_per_target=_missing(),
        n_genes_measured=_missing(),
        remote_bytes=_missing(),
        temporary_bytes=_missing(),
        checksum=_missing(),
        panel_overlap=_missing(
            "count only against an actual target list; otherwise leave missing"
        ),
        training_overlap=_missing(),
    )


def validate_card(card: SourceCard) -> list[str]:
    """Structural problems, not scientific ones. Empty list = form is usable."""
    errors: list[str] = []
    if not card.source_id:
        errors.append("source_id is empty")
    if card.panel_overlap.claim != "missing":
        val = card.panel_overlap.value
        if not isinstance(val, dict) or "list_source" not in val:
            errors.append(
                "panel_overlap must name the target-list source in value.list_source"
            )
    if card.decision == "adopt" and card.panel_overlap.claim == "missing":
        errors.append("adoption requires a measured panel overlap or an explicit deferral")
    return errors
