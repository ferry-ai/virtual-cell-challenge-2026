"""Basal expression (CPM of the controls) of new source contexts, from their sums archives, appended to the basal table.

`reports/trasferimento_appreso_2026-09-26/basal_profiles.py` wrote the table the benches read
(`processed/basal_sources_2026-09-26.csv`: official-axis `gene_name` x contexts, CPM of each context's control rows,
the denominator being the controls' counts over all the source's genes). For sources ingested as sums archives
(`kolf_sums.py`, `h5ad_sums.py`, `hipsci_sums.py`, `r_sums_pack.py`), the same quantity is 1e6 x the `NTC` groups'
summed counts / their summed `total_counts`, which cover all genes of the file. This reads only the control rows,
through a memory map of the uncompressed matrix (`kolf_effects.Sums` checks the archive), and writes a NEW table:
the old columns unchanged, one column per `--sums NAME=FILE[:CONTEXT]` added (CONTEXT selects a context of an
archive that has a `context` key). Axis genes absent from a file stay NaN.

    scripts/py.cmd reports/universo_nuovi_2026-09-27/basal_from_sums.py \
        --base C:/Users/ferra/vcc2026-data/processed/basal_sources_2026-09-26.csv \
        --sums kolf=C:/Users/ferra/vcc2026-data/interim/kolf_sums/sums.npz \
        --out C:/Users/ferra/vcc2026-data/processed/basal_sources_2026-09-27.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "universo_kolf_2026-09-27"))

from kolf_effects import Sums  # noqa: E402


def control_cpm(path: Path, context: str | None) -> tuple[np.ndarray, np.ndarray, dict]:
    s = Sums(path)
    ntc = s.target == "NTC"
    if context is not None:
        if s.context is None:
            raise SystemExit(f"{path} has no context key")
        ntc &= s.context == context
    rows = np.flatnonzero(ntc)
    if not rows.size:
        raise SystemExit(f"{path}: no NTC group" + (f" in context {context!r}" if context else ""))
    mm = np.memmap(path, dtype="<f4", mode="r", offset=s.data_offset, shape=(s.ng, s.na), order="F")
    counts = np.asarray(mm[rows, :], dtype=np.float64).sum(axis=0)
    total = float(s.total[rows].sum())
    cpm = counts / total * 1e6                      # NaN where the file lacks the gene
    info = {"file": str(path), "context": context, "ntc_groups": int(rows.size),
            "ntc_cells": int(s.n_cells[rows].sum()), "ntc_library": total,
            "genes_measured": int(np.isfinite(cpm).sum()),
            "share_of_library_on_axis": float(np.nansum(counts) / total)}
    return np.asarray(s.genes, dtype=str), cpm, info


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--sums", action="append", required=True, metavar="NAME=FILE[:CONTEXT]")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    table = pd.read_csv(args.base).set_index("gene_name")
    infos = {}
    for spec in args.sums:
        name, _, rest = spec.partition("=")
        file, context = (rest.rsplit(":", 1) if rest.count(":") > 1 else (rest, None))  # keep a drive letter
        if name in table.columns:
            raise SystemExit(f"column {name} exists in the base table")
        genes, cpm, info = control_cpm(Path(file), context)
        table[name] = pd.Series(cpm, index=genes).reindex(table.index)
        infos[name] = info
        print(f"{name}: {info['ntc_cells']} control cells, {info['genes_measured']} genes, "
              f"{info['share_of_library_on_axis']:.3f} of the library on the axis", flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.reset_index().to_csv(args.out, index=False)
    with args.out.with_suffix(".json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "universo_nuovi_2026-09-27/basal_from_sums.py", "base": str(args.base),
                   "added": infos, "columns": list(table.columns)}, fh, indent=1)


if __name__ == "__main__":
    main()
