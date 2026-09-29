"""Helpers shared by the rehearsal scripts of this folder (dress rehearsal of 22 October).

Nothing here is a stage and nothing here is imported by the live tree: the rehearsal scripts
(`estrazione.py`, `bundle_finto.py`, `assembla_cache.py`, `cpm_contesti.py`, `diagnostica.py`,
`misura.py`) put this folder on `sys.path` and import it. Data paths come from
`vcc2026.config.paths()`, so `VCC2026_DATA_ROOT` points every script at another root (the tests
use a temporary one).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from vcc2026 import config  # noqa: E402

CONTROL_LABEL = "non-targeting"

# The four sources of the t22 recipe, as registered in RISULTATI.md: K562 of 26/09, CD4 and Orion
# `_me1` (t25's rule). Name -> universe folder under <data_root>/processed.
SOURCES_ME1 = {
    "k562": "universe_k562_2026-09-26",
    "cd4_mix": "universe_cd4_2026-09-27_me1",
    "orion_hct116": "universe_orion_hct116_2026-09-27_me1",
    "orion_hek293t": "universe_orion_hek293t_2026-09-27_me1",
}
# The same sources as the 26/09 universes (the ones r5 and t22 match).
SOURCES_U26 = {
    "k562": "universe_k562_2026-09-26",
    "cd4_mix": "universe_cd4_2026-09-26",
    "orion_hct116": "universe_orion_hct116_2026-09-26",
    "orion_hek293t": "universe_orion_hek293t_2026-09-26",
}


def data_root() -> Path:
    return config.paths().data_root


def sha256_file(path: Path | str, block: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(block), b""):
            h.update(chunk)
    return h.hexdigest()


def free_bytes(path: Path | str) -> int:
    """Free bytes on the volume holding ``path`` (or its nearest existing parent)."""
    p = Path(path)
    while not p.exists() and p != p.parent:
        p = p.parent
    return shutil.disk_usage(p).free


def require_free(path: Path | str, need_bytes: int, floor_bytes: int = int(1.5 * 1024**3)) -> int:
    """Refuse (SystemExit) unless ``need_bytes`` fit on the volume and ``floor_bytes`` stay free."""
    free = free_bytes(path)
    if free - need_bytes < floor_bytes:
        raise SystemExit(f"REFUSING: {free / 1024**3:.2f} GiB free at {path}; this step writes about "
                         f"{need_bytes / 1024**3:.2f} GiB and must leave {floor_bytes / 1024**3:.2f} GiB free")
    return free


def write_new_text(path: Path, text: str) -> Path:
    """Write ``text`` (LF line ends) to a file that must not exist yet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


def write_new_json(path: Path, obj) -> Path:
    return write_new_text(path, json.dumps(obj, indent=1, default=str) + "\n")


def read_targets(path: Path | str) -> list[str]:
    """Targets of a panel file: the ``target_gene`` column by name if present, else the first column
    (what stages 98 and 100 read); first-seen order, duplicates, blanks and the control label dropped."""
    frame = pd.read_csv(path)
    col = frame["target_gene"] if "target_gene" in frame.columns else frame.iloc[:, 0]
    out, seen = [], set()
    for v in col:
        if pd.isna(v):
            continue
        t = str(v).strip()
        if not t or t == CONTROL_LABEL or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def read_index(universe: Path) -> pd.DataFrame:
    """A universe's ``index.csv`` with a ``file`` column: the chunk npz of each target that has effects.

    Two formats exist: K562 and Orion name the chunk file (empty when the target has no effects);
    CD4 gives an integer group, whose files are ``<table>_<group:03d>.npz`` for each table
    (``cd4_mix``, ``cd4_Rest``, ...). For the integer format ``file`` holds the group number."""
    ix = pd.read_csv(universe / "index.csv", dtype={"target": str})
    if "chunk" not in ix.columns:
        raise ValueError(f"{universe}/index.csv has no chunk column")
    ix = ix[ix["chunk"].notna() & (ix["chunk"].astype(str).str.strip() != "")].copy()
    ix["target"] = ix["target"].astype(str)
    return ix


def chunk_path(universe: Path, table: str, chunk) -> Path:
    """The npz holding a target of ``table``: a file name as given, or ``<table>_<NNN>.npz`` for a group."""
    s = str(chunk).strip()
    if s.endswith(".npz"):
        return universe / s
    return universe / f"{table}_{int(float(s)):03d}.npz"


def universe_targets(universe: Path) -> set[str]:
    return set(read_index(universe)["target"])


def official_axis_symbols() -> np.ndarray:
    from vcc2026.genes import official_axis

    return np.asarray(official_axis().symbols).astype(str)
