"""Run manifests: what went in, what came out, and what it was run with.

A result without a manifest cannot be reproduced or trusted, and this project
has already been bitten by the weaker version of the problem -- a script
existing being read as evidence it ran. A manifest closes that gap: it records
input paths with their sizes and hashes, output paths with theirs, the resolved
configuration, the seed, and the versions of every package whose behaviour the
numbers depend on.

Two conventions are enforced:

* **Manifests are never overwritten.** `RunManifest.write` refuses an existing
  path, mirroring `scripts/25_ingest_cd4_pilot.py`. A re-run goes to a new
  destination, so a superseded result stays readable as what was true that day.
* **Hashes are of bytes, not of intent.** Large inputs are hashed by a bounded
  head/tail sample with the size, because hashing a 44 GB file to record that we
  read 20 MB of it wastes hours; the manifest says which mode was used, so a
  sampled hash is never mistaken for a full one.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

__all__ = [
    "RunManifest",
    "file_fingerprint",
    "environment_fingerprint",
]

_SAMPLE_LIMIT = 64 * 1024**2  # hash in full below this; sample above it
_SAMPLE_BLOCK = 8 * 1024**2

_TRACKED_PACKAGES = (
    "cell-eval2", "vcc-cli", "anndata", "numpy", "scipy", "pandas",
    "h5py", "scanpy", "scikit-learn", "pyarrow",
)


def file_fingerprint(path: Path | str, *, full: bool | None = None) -> dict:
    """Size, mtime and sha256 of a file. Large files are sampled, and say so."""
    path = Path(path)
    if not path.exists():
        return {"path": str(path), "exists": False}
    size = path.stat().st_size
    if full is None:
        full = size <= _SAMPLE_LIMIT

    h = hashlib.sha256()
    with path.open("rb") as fh:
        if full:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        else:
            h.update(fh.read(_SAMPLE_BLOCK))
            fh.seek(max(0, size - _SAMPLE_BLOCK))
            h.update(fh.read(_SAMPLE_BLOCK))
    return {
        "path": str(path),
        "exists": True,
        "bytes": size,
        "mtime_utc": datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).isoformat(),
        "sha256": h.hexdigest(),
        "sha256_mode": "full" if full else "head+tail sample (64 MiB blocks)",
    }


def environment_fingerprint() -> dict:
    """Interpreter, platform and the package versions results depend on."""
    packages = {}
    for name in _TRACKED_PACKAGES:
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "hostname": socket.gethostname(),
        "cpu_count": os.cpu_count(),
        "packages": packages,
        "env_overrides": {
            k: os.environ[k] for k in ("VCC2026_DATA_ROOT", "VCC2026_ARTIFACT_ROOT")
            if k in os.environ
        },
    }


@dataclass
class RunManifest:
    """Everything needed to re-run one pipeline stage and get the same answer."""

    run_id: str
    stage: str
    config: dict = field(default_factory=dict)
    seed: int | None = None
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    started_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    finished_utc: str | None = None

    def add_input(self, name: str, path: Path | str, **extra) -> "RunManifest":
        self.inputs[name] = {**file_fingerprint(path), **extra}
        return self

    def add_output(self, name: str, path: Path | str, **extra) -> "RunManifest":
        self.outputs[name] = {**file_fingerprint(path), **extra}
        return self

    def note(self, text: str) -> "RunManifest":
        """Record a caveat next to the number it qualifies, not in a README."""
        self.notes.append(text)
        return self

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "stage": self.stage,
            "started_utc": self.started_utc,
            "finished_utc": self.finished_utc
            or datetime.now(timezone.utc).isoformat(),
            "seed": self.seed,
            "config": self.config,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metrics": self.metrics,
            "notes": self.notes,
            "environment": environment_fingerprint(),
        }

    def write(self, path: Path | str, *, allow_overwrite: bool = False) -> Path:
        """Write the manifest. Refuses to clobber an existing one by default."""
        path = Path(path)
        if path.exists() and not allow_overwrite:
            raise FileExistsError(
                f"{path} exists; manifests are evidence. Write to a new --out "
                f"instead of overwriting a previous run."
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        self.finished_utc = datetime.now(timezone.utc).isoformat()
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(self.as_dict(), indent=2, default=str), encoding="utf-8"
        )
        os.replace(tmp, path)
        return path
