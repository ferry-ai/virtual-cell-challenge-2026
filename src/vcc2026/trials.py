"""Trial definitions, read from `configs/trials.yaml`.

A trial is one submission-shaped run: a prediction rule, the data it may read,
the seed it draws with, and what it is for. Keeping them in a config rather than
in each script's defaults means the freeze, the generator and the packager all
read the same object, and a run cannot silently disagree with the trial it
claims to be.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from .config import REPO_ROOT

__all__ = ["TRIALS_PATH", "load_trial", "trial_ids", "load_spec"]

TRIALS_PATH = REPO_ROOT / "configs" / "trials.yaml"


@lru_cache(maxsize=1)
def load_spec(path: Path | None = None) -> dict:
    target = Path(path) if path is not None else TRIALS_PATH
    return yaml.safe_load(target.read_text(encoding="utf-8"))


def trial_ids(path: Path | None = None) -> list[str]:
    return [t["id"] for t in load_spec(path)["trials"]]


def load_trial(trial_id: str, path: Path | None = None) -> dict:
    """One trial with the file's defaults merged underneath it.

    Raises:
        KeyError: the id is not defined, naming the ids that are.
    """
    spec = load_spec(path)
    for trial in spec["trials"]:
        if trial["id"] == trial_id:
            merged = dict(spec.get("defaults", {}))
            merged.update(trial)
            merged["_trials_version"] = spec.get("version")
            return merged
    raise KeyError(
        f"unknown trial {trial_id!r}; defined: {[t['id'] for t in spec['trials']]}"
    )
