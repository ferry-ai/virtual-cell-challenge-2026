"""The perturbation panel: the targets a prediction must cover, read from a bundle's pert_counts.csv.

The 2026 bundle's file is a bare list with one ``target_gene`` column. The official reader
(vcc-cli's `read_pert_counts`) also accepts a ``context`` column, which repeats each target once
per context, and an ``n_cells`` column. Stages 97, 98, 100 and 102 took the first column by
position, which would read a context label as a target if the final bundle put ``context``
first (dress rehearsal of 22 October, reports/invii/prova_generale_2026-09-28/, defect D2).
`read_panel` reads the column by name; the bare lists used until then give the same list.

`panel_sha256` names a panel by its targets and their order rather than by the bytes of the
file that listed them, so a cache built for a panel can record which one (defect D4) and a
stage reading the same targets from a re-saved file (CRLF, an ``n_cells`` column) still
recognises it. `write_cache_manifest` is how a panel cache records it: stages 98 and 106 write
the cache's ``manifest.json`` with ``targets_sha256``, the key stage 100 checks against the
panel it reads. `panel_record` is what every manifest says of the panel file a run read.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import challenge
from .manifest import file_fingerprint

__all__ = ["read_panel", "panel_sha256", "panel_record", "write_cache_manifest", "CACHE_MANIFEST"]

CACHE_MANIFEST = "manifest.json"   # in a panel cache's folder, beside its npz tables


def read_panel(path: Path | str) -> list[str]:
    """The targets of a panel file, in first-seen order, each once.

    The column is ``target_gene`` (the config's ``pert_col``) when the file has one; a file with
    a single column is read as a bare list under any header. The first line is always a header.
    Names are stripped and blank cells skipped, as vcc-cli does. Refused: a file with several
    columns and none named ``target_gene``, a panel that lists the control label (the config's
    ``ntc_label``: controls are never predicted), and an empty panel.
    """
    spec = challenge()
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if spec.pert_col in frame.columns:
        column = frame[spec.pert_col]
    elif frame.shape[1] == 1:
        column = frame.iloc[:, 0]
    else:
        raise ValueError(f"{path}: no {spec.pert_col!r} column among {list(frame.columns)}; "
                         f"a file with several columns must name its targets' column {spec.pert_col!r}")
    names = [name for name in (value.strip() for value in column.tolist()) if name]
    if spec.ntc_label in names:
        raise ValueError(f"{path}: lists the control label {spec.ntc_label!r} as a target; "
                         "a panel holds only the perturbations to predict")
    panel = list(dict.fromkeys(names))
    if not panel:
        raise ValueError(f"{path}: no target")
    return panel


def panel_sha256(panel: list[str]) -> str:
    """sha256 of a panel: its targets joined by newlines (no trailing newline), UTF-8."""
    return hashlib.sha256("\n".join(panel).encode("utf-8")).hexdigest()


def panel_record(path: Path | str, panel: list[str]) -> dict:
    """What a manifest records of the panel file a run read: its path and the sha256 of its bytes,
    and of the targets read from it `panel_sha256` and their number."""
    return {"path": str(path), "file_sha256": file_fingerprint(path, full=True)["sha256"],
            "panel_sha256": panel_sha256(panel), "n": len(panel)}


def write_cache_manifest(cache: Path, stage: str, targets_csv: Path | str, panel: list[str], sources: dict,
                         **fields) -> dict:
    """Write ``<cache>/manifest.json`` for a panel cache, and return it; an existing one is refused.

    ``targets_sha256`` is `panel_sha256` of ``panel``, the targets the cache was built for: stage 100
    refuses a cache whose value differs from the panel it reads (defect D4 of the dress rehearsal).
    ``targets`` is the `panel_record` of ``targets_csv``. ``sources`` maps each table of the cache to
    its record; the size and sha256 of ``<cache>/<name>.npz`` are added to each. ``fields`` go in as
    given, after ``argv`` and the time of writing."""
    cache = Path(cache)
    out = {"stage": stage, "written_utc": datetime.now(timezone.utc).isoformat(), "argv": list(sys.argv),
           "targets_sha256": panel_sha256(panel), "targets": panel_record(targets_csv, panel), **fields,
           "sources": {}}
    for name, info in sources.items():
        path = cache / f"{name}.npz"
        out["sources"][name] = {**info, "file": path.name, "bytes": path.stat().st_size,
                                "sha256": file_fingerprint(path, full=True)["sha256"]}
    with open(cache / CACHE_MANIFEST, "x", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)
    return out
