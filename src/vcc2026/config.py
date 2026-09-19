"""Challenge constants and filesystem paths, loaded from configs/config.yaml.

Data lives outside the repo: the Desktop is synced by OneDrive and the datasets
run to tens of GB. Everything goes through here, so relocating the data is a
one-line change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "config.yaml"


@dataclass(frozen=True)
class Challenge:
    """Official submission-format spec."""

    n_genes: int
    n_perturbations: int
    cells_per_pert: int
    n_control_cells_per_context: int
    n_ntc_guides: int
    contexts_validation: tuple[str, ...]
    contexts_test: tuple[str, ...]
    max_stored_entries: int
    max_counts_per_cell: int
    pert_col: str
    context_col: str
    ntc_label: str

    @property
    def n_cells_total(self) -> int:
        """Cells in a complete submission: 300 x 400 x 3 = 360,000."""
        return self.n_perturbations * self.cells_per_pert * len(self.contexts_validation)

    @property
    def max_stored_per_cell(self) -> int:
        """Average budget of stored values per cell (~13,200)."""
        return self.max_stored_entries // self.n_cells_total


@dataclass(frozen=True)
class Paths:
    """Filesystem roots. All under data_root, outside OneDrive."""

    data_root: Path

    @property
    def raw(self) -> Path:
        """Downloaded bundles, kept untouched (controls.zip and friends)."""
        return self.data_root / "raw"

    @property
    def interim(self) -> Path:
        """Intermediate transforms, all regenerable."""
        return self.data_root / "interim"

    @property
    def processed(self) -> Path:
        """Training-ready matrices."""
        return self.data_root / "processed"

    @property
    def predictions(self) -> Path:
        """Generated .h5ad and .vcc files."""
        return self.data_root / "predictions"

    @property
    def models(self) -> Path:
        """Checkpoints."""
        return self.data_root / "models"

    @property
    def external(self) -> Path:
        """Third-party public data (Replogle, Arc Atlas, H1 2025)."""
        return self.data_root / "external"

    def ensure(self) -> None:
        """Create every directory that is missing."""
        for p in (self.raw, self.interim, self.processed,
                  self.predictions, self.models, self.external):
            p.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def _load() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=1)
def paths() -> Paths:
    """Project paths. VCC2026_DATA_ROOT takes precedence over the config file."""
    root = os.environ.get("VCC2026_DATA_ROOT") or _load()["data_root"]
    return Paths(data_root=Path(root))


@lru_cache(maxsize=1)
def challenge() -> Challenge:
    """Challenge constants from the config file."""
    raw = dict(_load()["challenge"])
    raw["contexts_validation"] = tuple(raw["contexts_validation"])
    raw["contexts_test"] = tuple(raw["contexts_test"])
    return Challenge(**raw)


def contexts(phase: str = "validation") -> tuple[str, ...]:
    """Context labels for a phase: 'validation' -> A/B/C, 'test' -> D/E/F."""
    c = challenge()
    if phase == "validation":
        return c.contexts_validation
    if phase == "test":
        return c.contexts_test
    raise ValueError(f"unknown phase: {phase!r} (expected 'validation' or 'test')")


# --- Portable roots (added 2026-09-12) -------------------------------------
#
# The two roots below make a run relocatable: nothing downstream hardcodes a
# Windows path. `data_root` holds inputs (raw, external, interim); it may be a
# read-only mount on a remote machine. `artifact_root` holds everything a run
# writes -- signatures, predictions, manifests, reports -- so a remote job can
# send back one directory.

ARTIFACT_ENV = "VCC2026_ARTIFACT_ROOT"
DATA_ENV = "VCC2026_DATA_ROOT"


@lru_cache(maxsize=1)
def artifact_root() -> Path:
    """Root for run outputs. VCC2026_ARTIFACT_ROOT wins, else config, else data_root/artifacts."""
    env = os.environ.get(ARTIFACT_ENV)
    if env:
        return Path(env)
    configured = _load().get("artifact_root")
    if configured:
        return Path(configured)
    return paths().data_root / "artifacts"


_FORBIDDEN_RUN_CHARS = frozenset('/:*?"<>|') | {chr(92)}


def run_dir(run_id: str, *, create: bool = True) -> Path:
    """Directory for one named run, under the artifact root."""
    if not run_id or set(run_id) & _FORBIDDEN_RUN_CHARS or run_id in {".", ".."}:
        raise ValueError(f"invalid run_id: {run_id!r}")
    d = artifact_root() / run_id
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d

