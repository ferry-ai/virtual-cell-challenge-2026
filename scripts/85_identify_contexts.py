"""Stage 85: what kind of cells are the official contexts A, B and C?

The challenge names them A, B and C and ships only their control cells. Everything we
transfer comes from cell types we chose without knowing what we were transferring INTO:
K562 is a chronic myeloid leukaemia line, HepG2 a hepatoblastoma line. If the official
contexts are, say, pluripotent stem cells, a weak transfer is biology and not a defect.

This stage reads the control cells of each context once and reports, per marker panel,
the pooled CPM and the fraction of cells detecting the gene. Marker panels are lineage
markers taken from standard practice, listed in `PANELS` with their source line; a panel
lighting up is evidence about lineage, not a cell-line identification: two lines of the
same lineage share these genes, and a knocked-in reporter or a transformed line can carry
markers it "should not" have.

It also correlates the three contexts with each other in log CPM space, which says
whether A, B and C are three different cell types or one cell type in three conditions.

    python scripts/85_identify_contexts.py --out reports/contexts_2026-09-17
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config  # noqa: E402

#: lineage -> (marker genes, the line the panel is usually read on)
PANELS = {
    "pluripotency (iPSC / hESC, e.g. KOLF2.1J, H1)":
        ["POU5F1", "NANOG", "SOX2", "LIN28A", "DNMT3B", "TDGF1", "SALL4", "ZFP42", "L1TD1", "UTF1"],
    "erythroid / myeloid leukaemia (K562)":
        ["HBG1", "HBG2", "HBZ", "GATA1", "GYPA", "KLF1", "TFRC"],
    "hepatocyte (HepG2)":
        ["ALB", "APOA1", "APOB", "AFP", "TTR", "SERPINA1", "HNF4A"],
    "T lymphocyte (Jurkat)":
        ["CD3D", "CD3E", "CD2", "LCK", "TRAC", "PTPRC"],
    "epithelial (RPE1, HEK293)":
        ["KRT8", "KRT18", "CDH1", "EPCAM", "RPE65"],
    "neural":
        ["MAP2", "TUBB3", "NEFL", "SOX1", "PAX6", "NES"],
    "fibroblast / mesenchymal":
        ["COL1A1", "COL1A2", "FN1", "THY1", "VIM"],
    "monocyte / macrophage (THP-1)":
        ["CD14", "SPI1", "LYZ", "ITGAM"],
    "housekeeping (scale check)":
        ["ACTB", "GAPDH", "TUBB", "RPL13A"],
    "proliferation":
        ["MKI67", "TOP2A", "CCNB1"],
}


def gene_names(f: h5py.File) -> np.ndarray:
    idx = f["var/_index"]
    raw = idx["values"][:] if isinstance(idx, h5py.Group) else idx[:]
    return np.array([g.decode() if isinstance(g, bytes) else str(g) for g in raw], dtype=object)


def context_profile(path: Path, block: int) -> tuple[np.ndarray, np.ndarray, int, np.ndarray]:
    """(pooled CPM per gene, detection fraction per gene, n_cells, gene names), one pass."""
    with h5py.File(path, "r") as f:
        n_cells, n_genes = (int(s) for s in f["X"].attrs["shape"])
        genes = gene_names(f)
        indptr = f["X/indptr"][:]
        gsum = np.zeros(n_genes, dtype=np.float64)
        detect = np.zeros(n_genes, dtype=np.int64)
        total = 0.0
        for start in range(0, n_cells, block):
            stop = min(start + block, n_cells)
            lo, hi = int(indptr[start]), int(indptr[stop])
            data = f["X/data"][lo:hi].astype(np.float64)
            cols = f["X/indices"][lo:hi]
            gsum += np.bincount(cols, weights=data, minlength=n_genes)
            detect += np.bincount(cols[data > 0], minlength=n_genes)
            total += float(data.sum())
    return gsum / total * 1e6, detect / n_cells, n_cells, genes


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--controls-dir", type=Path, default=None)
    p.add_argument("--contexts", nargs="+", default=["A", "B", "C"])
    p.add_argument("--block", type=int, default=2000, help="cells per read block")
    args = p.parse_args()
    if (args.out / "contexts.json").exists():
        raise SystemExit(f"{args.out} already holds a report")
    args.out.mkdir(parents=True, exist_ok=True)
    cdir = args.controls_dir or config.paths().raw / "controls"

    cpm, det, meta, genes = {}, {}, {}, None
    for ctx in args.contexts:
        t0 = time.time()
        c, d, n, g = context_profile(cdir / f"context_{ctx}.h5ad", args.block)
        if genes is None:
            genes = g
        elif not np.array_equal(genes, g):
            raise SystemExit("contexts do not share the gene axis")
        cpm[ctx], det[ctx], meta[ctx] = c, d, {"n_cells": n, "seconds": time.time() - t0}
        print(f"[{ctx}] {n} cells, {time.time() - t0:.0f}s", flush=True)

    pos = pd.Index(np.asarray(genes).astype(str))
    rows = []
    for lineage, markers in PANELS.items():
        for m in markers:
            j = pos.get_indexer([m])[0]
            row = {"lineage": lineage, "gene": m, "found": bool(j >= 0)}
            for ctx in args.contexts:
                row[f"cpm_{ctx}"] = float(cpm[ctx][j]) if j >= 0 else None
                row[f"det_{ctx}"] = float(det[ctx][j]) if j >= 0 else None
            rows.append(row)
    table = pd.DataFrame(rows)
    table.to_csv(args.out / "markers.csv", index=False)

    summary = {}
    for lineage in PANELS:
        sub = table[(table["lineage"] == lineage) & table["found"]]
        summary[lineage] = {"n_found": int(len(sub)), "n_listed": len(PANELS[lineage])}
        for ctx in args.contexts:
            summary[lineage][f"median_cpm_{ctx}"] = float(sub[f"cpm_{ctx}"].median()) if len(sub) else None
            summary[lineage][f"median_det_{ctx}"] = float(sub[f"det_{ctx}"].median()) if len(sub) else None

    logs = {ctx: np.log1p(cpm[ctx]) for ctx in args.contexts}
    between = {}
    for i, a in enumerate(args.contexts):
        for b in args.contexts[i + 1:]:
            between[f"{a}-{b}"] = {
                "pearson_log1p_cpm": float(np.corrcoef(logs[a], logs[b])[0, 1]),
                "n_genes_2x_apart": int((np.abs(logs[a] - logs[b]) > np.log(2)).sum()),
            }

    payload = {
        "stage": "85_identify_contexts", "written_utc": datetime.now(timezone.utc).isoformat(),
        "controls_dir": str(cdir), "contexts": meta, "panels": summary, "between_contexts": between,
        "claim_type": ("measured: pooled CPM and detection fraction of lineage markers in the official "
                       "contexts' control cells. Evidence about LINEAGE; it does not identify a cell line, "
                       "and the marker panels are standard practice, not a validated classifier"),
    }
    (args.out / "contexts.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for lineage, v in summary.items():
        cells = "  ".join(f"{c}: {v[f'median_cpm_{c}']:8.1f} CPM / {v[f'median_det_{c}']:.0%} det"
                          for c in args.contexts if v[f"median_cpm_{c}"] is not None)
        print(f"{lineage:46s} {v['n_found']}/{v['n_listed']} geni   {cells}")
    print("\nfra contesti:", json.dumps(between, indent=1))


if __name__ == "__main__":
    main()
