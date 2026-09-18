"""Runtime inventory for local and remote jobs.

The operational plan's remote-notebook contract starts by recording what the
machine actually is, not what a vendor page claims. A Kaggle or Colab quota
is unknown until measured in that runtime. This module is that measurement.

Nothing here starts a download or a fit.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from vcc2026.evaluation import scorer_fingerprint
from vcc2026.resources import GiB, snapshot

__all__ = [
    "RuntimeInventory",
    "collect_inventory",
    "disk_peak_estimate",
]


_PACKAGES = (
    "numpy", "scipy", "pandas", "h5py", "anndata", "scanpy",
    "cell-eval2", "vcc-cli", "pyyaml", "httpx",
)


def _git_identity(repo: Path) -> dict:
    """Commit and dirty flag. Absence of git is recorded, not invented."""
    out: dict = {"repo": str(repo), "available": False}
    git = shutil.which("git")
    if git is None:
        out["why"] = "git is not on PATH"
        return out
    try:
        commit = subprocess.check_output(
            [git, "-C", str(repo), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, text=True, timeout=10,
        ).strip()
        status = subprocess.check_output(
            [git, "-C", str(repo), "status", "--porcelain"],
            stderr=subprocess.DEVNULL, text=True, timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        out["why"] = f"{type(exc).__name__}: {exc}"
        return out
    out["available"] = True
    out["commit"] = commit
    out["dirty"] = bool(status.strip())
    out["dirty_paths"] = [line[3:] for line in status.splitlines() if line.strip()][:50]
    return out


def _gpu() -> dict:
    """What a GPU library can see, not whether one is plugged in."""
    info: dict = {"torch_installed": False, "cuda_available": False}
    try:
        import torch  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        info["torch_import_error"] = f"{type(exc).__name__}: {exc}"[:200]
        return info
    info["torch_installed"] = True
    info["torch_version"] = getattr(torch, "__version__", None)
    try:
        info["cuda_available"] = bool(torch.cuda.is_available())
        if info["cuda_available"]:
            info["device_count"] = int(torch.cuda.device_count())
            info["device_name"] = torch.cuda.get_device_name(0)
            prop = torch.cuda.get_device_properties(0)
            info["total_memory_bytes"] = int(prop.total_memory)
    except Exception as exc:  # noqa: BLE001
        info["cuda_error"] = f"{type(exc).__name__}: {exc}"[:200]
    return info


@dataclass(frozen=True)
class RuntimeInventory:
    """One snapshot of the environment a job is about to run in."""

    recorded_utc: str
    python: dict
    platform: dict
    resources: dict
    packages: dict
    git: dict
    gpu: dict
    scorer: dict
    data_root: str
    persistent_paths: dict
    windows_paths_forbidden: bool

    def as_dict(self) -> dict:
        return {
            "recorded_utc": self.recorded_utc,
            "python": self.python,
            "platform": self.platform,
            "resources": self.resources,
            "packages": self.packages,
            "git": self.git,
            "gpu": self.gpu,
            "scorer": self.scorer,
            "data_root": self.data_root,
            "persistent_paths": self.persistent_paths,
            "windows_paths_forbidden": self.windows_paths_forbidden,
            "claim": "measured",
        }


def collect_inventory(
    *,
    repo: Path,
    data_root: Path,
    persistent: Path | None = None,
    forbid_windows_paths: bool = False,
) -> RuntimeInventory:
    """Measure the runtime. `forbid_windows_paths` is for remote jobs."""
    packages: dict[str, str | None] = {}
    for name in _PACKAGES:
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    res = snapshot(data_root)
    persistent = persistent or data_root
    persist_free = shutil.disk_usage(persistent).free
    return RuntimeInventory(
        recorded_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        python={
            "version": sys.version.split()[0],
            "executable": sys.executable,
            "implementation": platform.python_implementation(),
        },
        platform={
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        resources=res.as_dict(),
        packages=packages,
        git=_git_identity(repo),
        gpu=_gpu(),
        scorer=scorer_fingerprint(),
        data_root=str(data_root),
        persistent_paths={
            "path": str(persistent),
            "free_bytes": int(persist_free),
            "free_gib": persist_free / GiB,
            "note": (
                "A file that remains only on ephemeral scratch is not a delivery. "
                "Export and re-read from this path."
            ),
        },
        windows_paths_forbidden=forbid_windows_paths,
    )


def disk_peak_estimate(
    *,
    input_bytes: int,
    decompressed_bytes: int | None,
    derived_bytes: int | None,
    checkpoint_bytes: int = 0,
    export_bytes: int | None = None,
    margin: float = 0.25,
) -> dict:
    """Peak disk for one block: inputs + decompression + derived + export.

    Unknown sizes stay unknown. The 25% margin is a proposal of the operational
    plan, not a measurement of actual overhead.
    """
    if not 0.0 <= margin < 2.0:
        raise ValueError(f"margin {margin} is not a fraction")
    known = {
        "input_bytes": int(input_bytes),
        "decompressed_bytes": decompressed_bytes,
        "derived_bytes": derived_bytes,
        "checkpoint_bytes": int(checkpoint_bytes),
        "export_bytes": export_bytes,
    }
    missing = [k for k, v in known.items() if v is None]
    accounted = sum(int(v) for v in known.values() if v is not None)
    peak = int(round(accounted * (1.0 + margin))) if not missing else None
    return {
        "components": known,
        "accounted_bytes": accounted,
        "unknown_components": missing,
        "margin": margin,
        "margin_note": "proposed 25% overhead, not measured",
        "peak_bytes": peak,
        "peak_complete": not missing,
        "claim": "derived" if not missing else "incomplete",
    }
