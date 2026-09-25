"""F1 of R-V2: the K562 genome-wide source for EVERY target, not only the 300 of the panel.

The stage-98 cache holds each source for the panel targets only. Models for new targets (the
final set brings 300 of them) need the whole universe of a source, both to train on and to look
new targets up. This builds it for the K562 genome-wide pseudobulk (Replogle 2022, local file),
with stage 98's own `k562_table` (quasi-Poisson SE, z-shrinkage as every other source), in
chunks of targets so that it runs in about 0.4 GB. Each chunk is a stage-98-format npz on the
official axis (keys targets, shrunk, raw, se, n_cells, meta), readable by stage 100's
`load_table` once concatenated or selected; `index.csv` says which chunk holds which target.

    scripts/py.cmd reports/universo_2026-09-26/k562_universe.py \
        --out C:/Users/ferra/vcc2026-data/processed/universe_k562_2026-09-26 --report reports/universo_2026-09-26/r1
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402

_spec = importlib.util.spec_from_file_location("stage98", REPO / "scripts" / "98_multisource_effects.py")
stage98 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage98)

DATA = config.paths().data_root
CHUNK = 600


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bulk", type=Path, default=DATA / "external/K562_gwps_raw_bulk_01.h5ad")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    args.report.mkdir(parents=True, exist_ok=False)
    t0 = time.time()
    axis = np.asarray(official_axis().symbols)
    with h5py.File(args.bulk, "r") as f:
        labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
    is_ntc = np.array(["non-targeting" in lab for lab in labels])
    symbols = np.array(["non-targeting" if nt else lab.split("_")[1] for lab, nt in zip(labels, is_ntc)])
    targets = sorted(set(symbols[~is_ntc]))
    panel = set(pd.read_csv(args.panel).iloc[:, 0].astype(str))
    on_axis = set(axis)
    index, chunks = [], []
    for c, start in enumerate(range(0, len(targets), CHUNK)):
        part = targets[start:start + CHUNK]
        tab = stage98.k562_table(args.bulk, part, axis)
        path = args.out / f"k562_{c:02d}.npz"
        np.savez_compressed(path, targets=np.array(tab.targets), shrunk=tab.shrunk, raw=tab.raw, se=tab.se,
                            n_cells=tab.n_cells, meta=json.dumps(tab.meta, default=str))
        chunks.append({"file": path.name, "targets": len(tab.targets),
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        index += [{"target": t, "chunk": path.name, "n_cells": int(n), "in_panel": t in panel,
                   "on_official_axis": t in on_axis} for t, n in zip(tab.targets, tab.n_cells)]
        print(f"chunk {c}: {len(tab.targets)} targets, {time.time() - t0:.0f} s", flush=True)
        del tab
    idx = pd.DataFrame(index)
    idx.to_csv(args.out / "index.csv", index=False)
    summary = {"targets": int(len(idx)), "in_panel": int(idx["in_panel"].sum()),
               "on_official_axis": int(idx["on_official_axis"].sum()),
               "median_cells": float(idx["n_cells"].median()), "rows_in_bulk": int(labels.size),
               "control_rows": int(is_ntc.sum()), "seconds": round(time.time() - t0, 1)}
    manifest = {"stage": "universo_2026-09-26/k562_universe.py", "written_utc": datetime.now(timezone.utc).isoformat(),
                "bulk": str(args.bulk), "out": str(args.out), "chunk_size": CHUNK, "chunks": chunks, "summary": summary,
                "claim_type": "effect tables (ln fold change, quasi-Poisson SE, z-shrinkage), as stage 98's k562 source"}
    for where in (args.out / "manifest.json", args.report / "manifest.json"):
        with where.open("x", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=1)
    idx.to_csv(args.report / "index.csv", index=False)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
