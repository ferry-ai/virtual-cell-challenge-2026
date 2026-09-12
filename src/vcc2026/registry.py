"""The source registry: what each dataset is, and how far it has been checked.

The registry exists because "we have a dataset" has meant six different things
in this project's history -- an accession that resolves, a file whose size we
read, a schema we inspected, values we sampled, a pilot we ingested, a usable
subset on disk. Those are not the same claim, and collapsing them is how a
verification turns into an assumption. So every source carries a
`VerificationLevel` and the evidence paths that justify it, and `verify()`
refuses a level whose evidence is missing.

Levels are ordered and strictly cumulative:

    declared          an accession or URL someone proposed; nothing checked
    metadata_verified the record is live and its file sizes were read
    schema_verified   the file's structure was read from its own bytes
    sample_verified   values were sampled and passed count/type checks
    pilot_ingested    a bounded extraction completed and was read back
    usable            enough data is locally available to train or evaluate on

A source at `sample_verified` is not a source you can train on. Coverage numbers
are recorded in three separate fields for the same reason -- library coverage,
observed targets, and targets with enough cells are three different quantities,
and the project has already conflated them once.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

import yaml

__all__ = ["VerificationLevel", "Coverage", "Source", "SourceRegistry", "load_registry"]

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "configs" / "sources.yaml"


class VerificationLevel(IntEnum):
    """How far a source has actually been checked. Ordered and cumulative."""

    DECLARED = 0
    METADATA_VERIFIED = 1
    SCHEMA_VERIFIED = 2
    SAMPLE_VERIFIED = 3
    PILOT_INGESTED = 4
    USABLE = 5

    @classmethod
    def parse(cls, text: str) -> "VerificationLevel":
        try:
            return cls[str(text).upper()]
        except KeyError:
            raise ValueError(
                f"unknown verification level {text!r}; "
                f"expected one of {[l.name.lower() for l in cls]}"
            ) from None

    @property
    def label(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class Coverage:
    """Three distinct quantities that must never be reported as one.

    Attributes:
        library_targets: panel targets present in the guide library *design*.
            A design claim. It says nothing about cells.
        observed_targets: panel targets with at least one usable cell observed.
        targets_min_cells: panel targets with at least `min_cells` cells --
            the only one of the three that bounds what can be estimated.
        min_cells: the threshold `targets_min_cells` was counted at.
        output_genes: source features intersecting the 18,533 official outputs.
            Genes outside this set are unmeasured, not unchanged (D-009).
    """

    library_targets: int | None = None
    observed_targets: int | None = None
    targets_min_cells: int | None = None
    min_cells: int | None = None
    output_genes: int | None = None

    def as_dict(self) -> dict:
        return {
            "library_targets": self.library_targets,
            "observed_targets": self.observed_targets,
            "targets_min_cells": self.targets_min_cells,
            "min_cells": self.min_cells,
            "output_genes": self.output_genes,
        }


@dataclass(frozen=True)
class Source:
    """One dataset, with its provenance, its limits and its verification state."""

    id: str
    title: str
    verification: VerificationLevel
    verified_on: str | None = None
    evidence: tuple[str, ...] = ()
    accession: str | None = None
    url: str | None = None
    version: str | None = None
    license: str | None = None
    assay: str | None = None
    modality: str | None = None
    cell_context: str | None = None
    cell_state: str | None = None
    timing: str | None = None
    count_schema: str | None = None
    guide_ids: str | None = None
    ntc_rule: str | None = None
    qc: str | None = None
    bytes_total: int | None = None
    checksum: str | None = None
    coverage: Coverage = field(default_factory=Coverage)
    ingestion_status: str = "not_started"
    enabled: bool = False
    role: str | None = None
    limits: tuple[str, ...] = ()
    local_path: str | None = None

    @property
    def is_trainable(self) -> bool:
        """Enabled and ingested far enough for its numbers to mean something."""
        return self.enabled and self.verification >= VerificationLevel.PILOT_INGESTED

    def verify(self, repo_root: Path) -> list[str]:
        """Return the problems with this entry. Empty list means consistent."""
        problems: list[str] = []
        if self.verification >= VerificationLevel.METADATA_VERIFIED:
            if not self.evidence:
                problems.append(
                    f"{self.id}: claims {self.verification.label} with no evidence path"
                )
            if not self.verified_on:
                problems.append(f"{self.id}: claims {self.verification.label} with no date")
        for rel in self.evidence:
            if not (repo_root / rel).exists():
                problems.append(f"{self.id}: evidence path does not exist: {rel}")
        if self.enabled and self.verification < VerificationLevel.SAMPLE_VERIFIED:
            problems.append(
                f"{self.id}: enabled at {self.verification.label}; a source may not be "
                f"enabled below sample_verified"
            )
        cov = self.coverage
        if cov.targets_min_cells is not None and cov.min_cells is None:
            problems.append(f"{self.id}: targets_min_cells given without min_cells")
        if (
            cov.observed_targets is not None
            and cov.library_targets is not None
            and cov.observed_targets > cov.library_targets
        ):
            problems.append(
                f"{self.id}: observed_targets ({cov.observed_targets}) exceeds "
                f"library_targets ({cov.library_targets})"
            )
        if (
            cov.targets_min_cells is not None
            and cov.observed_targets is not None
            and cov.targets_min_cells > cov.observed_targets
        ):
            problems.append(
                f"{self.id}: targets_min_cells ({cov.targets_min_cells}) exceeds "
                f"observed_targets ({cov.observed_targets})"
            )
        return problems


@dataclass(frozen=True)
class SourceRegistry:
    """All registered sources, plus the registry's own version."""

    version: str
    updated: str
    sources: tuple[Source, ...]

    def __len__(self) -> int:
        return len(self.sources)

    def __iter__(self):
        return iter(self.sources)

    def __getitem__(self, source_id: str) -> Source:
        for s in self.sources:
            if s.id == source_id:
                return s
        raise KeyError(f"unknown source {source_id!r}; known: {[s.id for s in self.sources]}")

    def enabled(self) -> tuple[Source, ...]:
        return tuple(s for s in self.sources if s.enabled)

    def at_least(self, level: VerificationLevel) -> tuple[Source, ...]:
        return tuple(s for s in self.sources if s.verification >= level)

    def verify(self, repo_root: Path | None = None) -> list[str]:
        root = repo_root or REGISTRY_PATH.resolve().parents[1]
        problems: list[str] = []
        seen: set[str] = set()
        for s in self.sources:
            if s.id in seen:
                problems.append(f"duplicate source id: {s.id}")
            seen.add(s.id)
            problems.extend(s.verify(root))
        return problems

    def table(self) -> list[dict]:
        """Flat rows for a report."""
        return [
            {
                "id": s.id,
                "verification": s.verification.label,
                "enabled": s.enabled,
                "role": s.role,
                "library": s.coverage.library_targets,
                "observed": s.coverage.observed_targets,
                "min_cells_targets": s.coverage.targets_min_cells,
                "output_genes": s.coverage.output_genes,
                "license": s.license,
                "status": s.ingestion_status,
            }
            for s in self.sources
        ]


def load_registry(path: Path | str | None = None) -> SourceRegistry:
    """Load and parse `configs/sources.yaml`."""
    path = Path(path) if path is not None else REGISTRY_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = []
    for entry in raw.get("sources", []):
        entry = dict(entry)
        cov = Coverage(**(entry.pop("coverage", None) or {}))
        sources.append(
            Source(
                verification=VerificationLevel.parse(entry.pop("verification")),
                evidence=tuple(entry.pop("evidence", ()) or ()),
                limits=tuple(entry.pop("limits", ()) or ()),
                coverage=cov,
                **entry,
            )
        )
    return SourceRegistry(
        version=str(raw.get("version", "0")),
        updated=str(raw.get("updated", "")),
        sources=tuple(sources),
    )
