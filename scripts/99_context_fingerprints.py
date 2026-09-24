"""Stage 99: what the official control cells say about assay and cell line, beyond markers.

Stage 85 read lineage from marker panels. This stage adds three readings that marker
panels cannot give, all from the control bundles alone:

1. **Assay.** The organisers state CRISPRi read out with 10x Flex, a probe-based assay
   (Arc Institute, 2026). The official axis is tested against that: its size, and the gene
   classes a probe panel leaves out and a 3' whole-transcriptome axis always carries --
   ribosomal proteins (RPL/RPS), HLA, XIST, MALAT1, NEAT1, lncRNAs.
2. **Platform gap.** Correlation of log2(CPM+1) control profiles between A/B/C and the
   Replogle non-targeting profiles (3' chemistry) on their shared genes. If lineage
   dominated, the T-lymphoid context A would sit nearer to K562 than to squamous C.
3. **Genetic fingerprints.** Sex (Y-linked genes), homozygous deletions (genes at exactly
   zero in 18,400 cells that are expressed in another context), and arm-level expression
   shifts of each context against the median of the three (inferCNV-style; with three
   contexts one of them is always the median, so a shift reads RELATIVE to the others).

Everything here is an interpretation aid. Line identities stay hypotheses until matched
against reference profiles (e.g. CCLE/DepMap copy number and expression).

    python scripts/99_context_fingerprints.py --out reports/context_fingerprints_2026-09-22
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import log  # noqa: E402

DATA_ROOT = Path("C:/Users/ferra/vcc2026-data")
# GRCh38 centromere midpoints in Mb (approximate; arm assignment only)
CEN = {"chr1": 123.4, "chr2": 93.9, "chr3": 90.9, "chr4": 50.0, "chr5": 48.8, "chr6": 59.8, "chr7": 60.1,
       "chr8": 45.2, "chr9": 43.0, "chr10": 39.8, "chr11": 53.4, "chr12": 35.5, "chr13": 17.7, "chr14": 17.2,
       "chr15": 19.0, "chr16": 36.8, "chr17": 25.1, "chr18": 18.5, "chr19": 26.2, "chr20": 28.1, "chr21": 12.0,
       "chr22": 15.0, "chrX": 60.6, "chrY": 10.4}
FLEX_V1_GENES = 18532            # Chromium Human Transcriptome Probe Set v1.0.1 (10x Genomics)
Y_GENES = ["RPS4Y1", "DDX3Y", "UTY", "KDM5D", "EIF1AY", "ZFY", "USP9Y"]
WATCH = ["CDKN2A", "CDKN2B", "MTAP", "PTEN", "TP53", "RB1", "TERT", "LIN28B", "MITF", "PAX6", "LHX2",
         "EPCAM", "CDH1", "VIM", "KRT7", "KRT17", "KRT5", "TP63", "SOX2", "CD3E", "DNTT", "TAL1"]


def dec(a):
    return np.array([x.decode() if isinstance(x, bytes) else str(x) for x in a])


def context_totals(path: Path, chunk: int = 2_000_000):
    with h5py.File(path, "r") as f:
        genes = dec(f["var/_index/values"][:])
        idx, dat = f["X/indices"], f["X/data"]
        tot = np.zeros(len(genes))
        for s in range(0, idx.shape[0], chunk):
            tot += np.bincount(idx[s:s + chunk], weights=dat[s:s + chunk], minlength=len(genes))
        n_cells = int(f["X/indptr"].shape[0] - 1)
    return genes, tot, n_cells


def replogle_ntc(path: Path):
    with h5py.File(path, "r") as f:
        labels = dec(f["obs/gene_transcript"][:])
        cats = dec(f["var/__categories/gene_name"][:])
        codes = f["var/gene_name"][:]
        genes = np.where(codes >= 0, cats[np.clip(codes, 0, None)], "")
        rows = np.flatnonzero(["non-targeting" in s for s in labels])
        w = f["obs/num_cells_unfiltered"][:][rows].astype(float)
        prof = (f["X"][rows, :] * w[:, None]).sum(0)
    return genes, prof


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--controls-dir", type=Path, default=DATA_ROOT / "raw/controls")
    p.add_argument("--contexts", nargs="+", default=["A", "B", "C"])
    p.add_argument("--external", type=Path, default=DATA_ROOT / "external")
    p.add_argument("--coords", type=Path, default=DATA_ROOT / "external/annotation/gene_coordinates_gencode_v50.tsv")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.out / "fingerprints.json").exists():
        raise FileExistsError(args.out / "fingerprints.json")
    args.out.mkdir(parents=True, exist_ok=True)

    ctxs = tuple(args.contexts)

    # 1. assay
    axis = [r[0] for r in csv.reader(open(args.controls_dir / "gene_names.csv"))][1:]
    classes = {k: [g for g in axis if re.search(pat, g)] for k, pat in {
        "ribosomal_RPL_RPS": r"^RP[LS]\d", "HLA": r"^HLA-", "LINC": r"^LINC", "antisense_AS": r"-AS\d",
        "mitochondrial_MT": r"^MT-", "legacy_histone_symbols": r"^HIST\d|^H2AF|^H3F3"}.items()}
    assay = {"axis_genes": len(axis), "flex_v1_probe_set_genes": FLEX_V1_GENES,
             "counts": {k: len(v) for k, v in classes.items()},
             "examples": {k: v[:6] for k, v in classes.items()},
             "absent": [g for g in ("XIST", "MALAT1", "NEAT1") if g not in set(axis)]}
    log(f"assay: {assay['counts']}, absent {assay['absent']}")

    # 2. platform gap
    totals, n_cells = {}, {}
    for c in ctxs:
        g, t, n = context_totals(args.controls_dir / f"context_{c}.h5ad")
        totals[c], n_cells[c] = dict(zip(g, t)), n
        genes_abc, tot_abc = g, None
    profiles = dict(totals)
    for name, fn in [("K562", "K562_gwps_raw_bulk_01.h5ad"), ("RPE1", "rpe1_raw_bulk_01.h5ad")]:
        g, t = replogle_ntc(args.external / fn)
        profiles[name] = dict(zip(g, t))
    names = list(profiles)
    shared = sorted(set.intersection(*[{k for k in pr if k} for pr in profiles.values()]))
    M = np.array([[profiles[n][g] for g in shared] for n in names])
    L = np.log2(M / M.sum(1, keepdims=True) * 1e6 + 1)
    r = np.corrcoef(L)
    platform = {"shared_genes": len(shared),
                "pearson_log2cpm": {f"{a}~{b}": float(r[i, j]) for i, a in enumerate(names)
                                    for j, b in enumerate(names) if i < j}}
    log(f"platform: {platform['pearson_log2cpm']}")

    # 3. fingerprints
    cpm = np.vstack([np.array([totals[c][g] for g in genes_abc]) for c in ctxs])
    cpm = cpm / cpm.sum(1, keepdims=True) * 1e6
    pos = {g: i for i, g in enumerate(genes_abc)}
    watch = {g: {c: round(float(cpm[i, pos[g]]), 2) for i, c in enumerate(ctxs)} for g in WATCH if g in pos}
    sex = {c: {g: round(float(cpm[i, pos[g]]), 2) for g in Y_GENES if g in pos} for i, c in enumerate(ctxs)}
    zero_elsewhere = {}
    for i, c in enumerate(ctxs):
        z = (cpm[i] == 0) & (np.delete(cpm, i, axis=0) >= 20).all(axis=0)
        zero_elsewhere[c] = sorted(genes_abc[z].tolist())
    coords = {}
    with open(args.coords) as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row["chrom"] in CEN:
                coords[row["symbol"]] = (row["chrom"], int(row["tss"]) / 1e6)
    keep = (cpm > 20).all(0) & np.array([g in coords for g in genes_abc])
    Lk = np.log2(cpm[:, keep] + 1)
    dev = Lk - np.median(Lk, axis=0)
    chrom = np.array([coords[g][0] for g in genes_abc[keep]])
    mb = np.array([coords[g][1] for g in genes_abc[keep]])
    arm = np.array([f"{ch[3:]}{'p' if x < CEN[ch] else 'q'}" for ch, x in zip(chrom, mb)])
    arms = {}
    for a in dict.fromkeys(arm):
        m = arm == a
        if m.sum() >= 15:
            arms[a] = {"n_genes": int(m.sum()), **{c: round(float(np.median(dev[i, m])), 3) for i, c in enumerate(ctxs)}}
    distal10q = (chrom == "chr10") & (mb > 62)
    fingerprints = {
        "sex_y_linked_cpm": sex, "watch_genes_cpm": watch,
        "zero_here_expressed_elsewhere_ge20cpm": zero_elsewhere,
        "arm_median_log2_shift_vs_median_context": arms,
        "chr10q_distal_gt62Mb": {c: round(float(np.median(dev[i, distal10q])), 3) for i, c in enumerate(ctxs)},
        "genes_used_for_arms": int(keep.sum()),
    }
    payload = {"stage": "99_context_fingerprints", "written_utc": datetime.now(timezone.utc).isoformat(),
               "claim_type": "measurement on the official controls; line identities are hypotheses",
               "n_cells": n_cells, "assay": assay, "platform": platform, "fingerprints": fingerprints}
    with open(args.out / "fingerprints.json", "x", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    log(f"wrote {args.out / 'fingerprints.json'}")


if __name__ == "__main__":
    main()
