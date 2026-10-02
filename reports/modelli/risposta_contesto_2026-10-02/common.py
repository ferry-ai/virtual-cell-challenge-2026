"""Shared helpers of the R-LEAD context-response study: paths, hashes, manifests, h5ad columns."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'src'))

STUDY = 'generalizzazione_contesti_2026-10-02'
REPORT = REPO / 'reports' / 'analisi' / STUDY


def data_root() -> Path:
    from vcc2026.config import paths
    return Path(paths().data_root)


def coords_path(value: str) -> Path:
    """A protocol path: absolute as given (Kaggle), otherwise relative to the data root."""
    p = Path(value)
    return p if p.is_absolute() else data_root() / p


def heavy_root() -> Path:
    """Bulky outputs of this study live outside the repository (D-001, D-048)."""
    return data_root() / 'processed' / STUDY


def sha256(path: Path, block: int = 4 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(block), b''):
            h.update(b)
    return h.hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def git_state() -> dict:
    def run(*args):
        try:
            return subprocess.run(['git', *args], cwd=REPO, capture_output=True, text=True,
                                  timeout=60).stdout.strip()
        except Exception as exc:  # recorded, never fatal
            return f'error: {exc}'
    return dict(head=run('rev-parse', 'HEAD'), branch=run('rev-parse', '--abbrev-ref', 'HEAD'),
                status_short=run('status', '--short').splitlines())


def environment() -> dict:
    import importlib.metadata as md
    versions = {}
    for pkg in ('numpy', 'scipy', 'pandas', 'anndata', 'h5py', 'cell-eval2', 'polars', 'scanpy'):
        try:
            versions[pkg] = md.version(pkg)
        except Exception:
            versions[pkg] = None
    return dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
                machine=platform.node(), versions=versions)


def write_json(path: Path, obj) -> None:
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=_default), encoding='utf-8')


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))


def h5_column(node) -> np.ndarray:
    """An AnnData obs/var column as strings (categorical or plain)."""
    import h5py
    if isinstance(node, h5py.Group):
        cats = np.array([x.decode() if isinstance(x, bytes) else str(x) for x in node['categories'][:]])
        return cats[node['codes'][:]]
    a = node[:]
    if a.dtype.kind in 'SO':
        return np.array([x.decode() if isinstance(x, bytes) else str(x) for x in a])
    return a


class Timer:
    def __init__(self):
        self.t0 = time.time()

    def __call__(self) -> float:
        return round(time.time() - self.t0, 1)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)
