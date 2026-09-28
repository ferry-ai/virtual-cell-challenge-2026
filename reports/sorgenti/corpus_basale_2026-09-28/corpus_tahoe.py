"""Tahoe-100M vehicle (DMSO) controls as a corpus of basal profiles, in the format of corpus_ours.py.

Input: the folder written by reports/sorgenti/tahoe_dmso_2026-09-28/extract_dmso.py (`pseudobulk.npz`: summed raw counts of
every DMSO cell per cell line x plate, `cells.npz`: a sample of DMSO cells per line, `metadata/`: the dataset's own
small metadata tables). One profile per line x plate with at least --min-cells cells (kind `pool`: all the DMSO cells
of that line on that plate), and, with --cells-per-subset > 0, profiles of random non-overlapping subsets of the
sampled cells of each line (kind `cells_subset`). Genes are mapped to the official axis by symbol (first occurrence
of a symbol, as corpus_ours.py does); axis genes absent from Tahoe's gene table are NaN.

Context `tahoe_<line name>`, family the same (each line its own family, as in the DepMap corpus), study `tahoe100m`,
platform `tahoe`. `cell_line` carries the line's name so the encoder's exclusion lists (corpus.PRESETS) find, e.g.,
HCT116 or K562 under any context name; `cellosaurus` and `tissue` are kept when the metadata give them. Lines in
--exclude-lines are left out here too and listed in the manifest (none by default: the encoder's presets exclude
per design).

    scripts/py.cmd reports/sorgenti/corpus_basale_2026-09-28/corpus_tahoe.py --tahoe <extract dir> --out <new dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.genes import official_axis  # noqa: E402

AXIS = np.asarray(official_axis().symbols)
COL = {g: i for i, g in enumerate(AXIS)}
NAME_COLUMNS = ("cell_name", "cell_line_name", "Cell_line", "cell_line", "name", "CellLineName")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def axis_map(symbols: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(positions in the Tahoe gene table, positions on the official axis), first occurrence of each symbol."""
    src, dst, seen = [], [], set()
    for i, s in enumerate(symbols.astype(str)):
        if s in COL and s not in seen:
            src.append(i)
            dst.append(COL[s])
            seen.add(s)
    return np.asarray(src, dtype=np.int64), np.asarray(dst, dtype=np.int64)


def line_names(tahoe: Path, ids: list[str], name_column: str | None) -> tuple[dict, dict, str]:
    path = tahoe / "metadata" / "cell_line_metadata.parquet"
    meta = pd.read_parquet(path)
    id_cols = [c for c in meta.columns if meta[c].astype(str).isin(ids).any()]
    if not id_cols:
        raise SystemExit(f"{path}: no column holds the pseudobulk's cell_line ids (e.g. {ids[:3]}); columns {list(meta.columns)}")
    idc = id_cols[0]
    if name_column is None:
        name_column = next((c for c in NAME_COLUMNS if c in meta.columns and c != idc), None)
    if name_column is None:
        raise SystemExit(f"{path}: pass --name-column (columns {list(meta.columns)})")
    first = meta.drop_duplicates(idc).set_index(idc)
    names = {i: str(first.at[i, name_column]) if i in first.index else i for i in ids}
    tissue_col = next((c for c in ("Organ", "organ", "tissue", "Tissue", "OncotreeLineage") if c in meta.columns), None)
    tissue = {i: (str(first.at[i, tissue_col]) if tissue_col and i in first.index else "") for i in ids}
    return names, tissue, f"id column {idc}, name column {name_column}, tissue column {tissue_col}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tahoe", type=Path, required=True, help="the output folder of extract_dmso.py")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--min-cells", type=int, default=50, help="line x plate profiles with fewer DMSO cells are left out")
    ap.add_argument("--cells-per-subset", type=int, default=0, help="also subsets of the sampled cells (0: off)")
    ap.add_argument("--seed", type=int, default=20260928)
    ap.add_argument("--name-column", default=None)
    ap.add_argument("--exclude-lines", default="")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    manifest_in = json.loads((args.tahoe / "manifest.json").read_text(encoding="utf-8"))
    pb = np.load(args.tahoe / "pseudobulk.npz", allow_pickle=False)
    lines, plates = pb["cell_line"].astype(str), pb["plate"].astype(str)
    ids = sorted(set(lines.tolist()))
    names, tissue, how = line_names(args.tahoe, ids, args.name_column)
    src, dst = axis_map(pb["gene_symbol"])
    ex = {norm(e) for e in args.exclude_lines.split(",") if e.strip()}
    counts, library, meta, dropped, small = [], [], [], [], []

    def add(x_tahoe: np.ndarray, lib: float, line: str, **m):
        row = np.full(AXIS.size, np.nan, dtype=np.float32)
        row[dst] = x_tahoe[src].astype(np.float64)
        counts.append(row)
        library.append(float(lib))
        nm = names[line]
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", nm)       # e.g. "HepG2/C3A", "COLO 205"
        meta.append({"profile_id": f"tahoe_{len(meta):06d}", "source": "tahoe", "context": f"tahoe_{safe}",
                     "family": f"tahoe_{safe}", "study": "tahoe100m", "platform": "tahoe", "cell_line": nm,
                     "cellosaurus": line, "tissue": tissue[line], **m})

    sums, n_cells, libs = pb["sums"], pb["n_cells"], pb["library"]
    for r in range(sums.shape[0]):
        line = lines[r]
        if norm(names[line]) in ex or norm(line) in ex:
            dropped.append(names[line])
            continue
        if n_cells[r] < args.min_cells:
            small.append({"line": names[line], "plate": plates[r], "n_cells": int(n_cells[r])})
            continue
        add(np.asarray(sums[r], dtype=np.float64), libs[r], line, kind="pool", n_cells=int(n_cells[r]),
            plate=plates[r])
    if args.cells_per_subset > 0:
        cz = np.load(args.tahoe / "cells.npz", allow_pickle=False)
        data, indices, indptr = cz["data"], cz["indices"], cz["indptr"]
        n_genes = int(cz["shape"][1])
        cl = cz["cell_line"].astype(str)
        rng = np.random.default_rng(args.seed)
        for line in ids:
            if norm(names[line]) in ex or norm(line) in ex:
                continue
            rows = rng.permutation(np.flatnonzero(cl == line))
            for k in range(rows.size // args.cells_per_subset):
                x = np.zeros(n_genes, dtype=np.float64)
                for i in rows[k * args.cells_per_subset:(k + 1) * args.cells_per_subset]:
                    a, b = indptr[i], indptr[i + 1]
                    np.add.at(x, indices[a:b], data[a:b].astype(np.float64))
                add(x, x.sum(), line, kind="cells_subset", n_cells=args.cells_per_subset, plate="")
    np.savez(args.out / "profiles.npz", counts=np.vstack(counts), library=np.asarray(library))
    m = pd.DataFrame(meta)
    m.to_csv(args.out / "meta.csv", index=False)
    per = m.groupby(["context", "kind"]).agg(profiles=("profile_id", "size"), cells=("n_cells", "sum")).reset_index()
    info = {"stage": "corpus_basale_2026-09-28/corpus_tahoe.py", "profiles": len(m), "input": str(args.tahoe),
            "input_revision": manifest_in.get("revision"), "input_complete": manifest_in.get("complete"),
            "names": how, "axis_genes_mapped": int(dst.size), "tahoe_genes": int(pb["gene_symbol"].size),
            "min_cells": args.min_cells, "cells_per_subset": args.cells_per_subset, "excluded_lines": sorted(set(dropped)),
            "small_groups_dropped": small, "per_context": per.to_dict(orient="records"),
            "claim_type": "data preparation; no model result"}
    with (args.out / "manifest.json").open("x", encoding="utf-8") as fh:
        json.dump(info, fh, indent=1, default=str)
    print(per.to_string(index=False))
    print(f"{len(m)} profiles, {m.context.nunique()} lines, {dst.size} axis genes mapped of {AXIS.size}; {how}")


if __name__ == "__main__":
    main()
