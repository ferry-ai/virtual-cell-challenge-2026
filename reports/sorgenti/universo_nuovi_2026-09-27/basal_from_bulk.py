"""Basal CPM of more Replogle-format contexts (per-cell-mean pseudobulk h5ad), appended to the basal table.

The K562 column of `processed/basal_sources_2026-09-26.csv` was built by
`reports/trasferimento/trasferimento_appreso_2026-09-26/basal_profiles.py` from the non-targeting rows of the genome-wide
per-cell-mean pseudobulk: their means weighted by cells, to CPM on the file's genes, then onto the official axis.
This applies the same function (imported, not rewritten) to other files of that format (RPE1, K562 essential),
and writes a NEW table: the base table's columns unchanged, one column per `--bulk NAME=FILE` added.

    scripts/py.cmd reports/sorgenti/universo_nuovi_2026-09-27/basal_from_bulk.py \
        --base C:/Users/ferra/vcc2026-data/processed/basal_sources_2026-09-27.csv \
        --bulk rpe1=C:/Users/ferra/vcc2026-data/external/rpe1_raw_bulk_01.h5ad \
        --out C:/Users/ferra/vcc2026-data/processed/basal_sources_2026-09-27_r2.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "trasferimento" / "trasferimento_appreso_2026-09-26"))

from basal_profiles import cpm, read_frame, to_axis  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--bulk", action="append", required=True, metavar="NAME=FILE")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    axis = np.asarray(official_axis().symbols)
    table = pd.read_csv(args.base).set_index("gene_name")
    if list(table.index) != list(axis):
        raise SystemExit("the base table is not on the official axis in order")
    info = {}
    for spec in args.bulk:
        name, _, path = spec.partition("=")
        if name in table.columns:
            raise SystemExit(f"column {name} exists")
        with h5py.File(path, "r") as f:
            labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
            ntc = np.flatnonzero(np.array(["non-targeting" in lab for lab in labels]))
            means = f["X"][ntc]
            cells = np.nan_to_num(f["obs/num_cells_filtered"][:][ntc])
            names = read_frame(f["var"])["gene_name"].astype(str).to_numpy()
        prof = (means * cells[:, None]).sum(axis=0) / cells.sum()
        table[name] = to_axis(cpm(prof), names, axis)
        info[name] = {"file": path, "control_rows": int(ntc.size), "cells": float(cells.sum()),
                      "genes_measured": int(np.isfinite(table[name]).sum())}
        print(f"{name}: {ntc.size} control rows, {cells.sum():.0f} cells, {info[name]['genes_measured']} genes", flush=True)
    table.reset_index().to_csv(args.out, index=False)
    with args.out.with_suffix(".json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "universo_nuovi_2026-09-27/basal_from_bulk.py", "base": str(args.base), "added": info,
                   "method": "basal_profiles.py's K562 method (non-targeting rows, cell-weighted means, CPM)"}, fh,
                  indent=1)


if __name__ == "__main__":
    main()
