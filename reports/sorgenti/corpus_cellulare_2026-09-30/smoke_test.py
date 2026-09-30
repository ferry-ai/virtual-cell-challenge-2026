"""Local smoke test of the three adapters and of rlab_job.py, on small cut-outs of the real files.

The laptop cannot hold the jobs (1.7 GB of free disk, under 1 GB of free RAM on 30/09), so each
schema is exercised on a cut-out that keeps its format:
- HepG2: the published h5ad itself, first 1,500 cells (`--max-cells`);
- HIPSCI: a genes x cells CSV.gz made of the first 400 feature rows and the first 1,200 cells of the
  fitness screen, read in three passes of 500 cells with blocks of 250 (the real parsing path);
- Jurkat: channel 16 restricted to its first 60,000 barcodes (every matrix entry of those
  barcodes kept, header dimensions rewritten), with the real feature files and panel.
Then HepG2 is run again with `--reuse` on the first attempt: every shard must be reused.

    python smoke_test.py --data-root C:/Users/ferra/vcc2026-data --out <new dir>
"""
from __future__ import annotations

import argparse
import gzip
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def cut_hipsci(src: Path, dest: Path, rows: int, cells: int) -> None:
    with gzip.open(src, "rt") as fh, gzip.open(dest, "wt") as out:
        for i, line in enumerate(fh):
            if i > rows:
                break
            out.write(",".join(line.rstrip("\n").split(",", cells + 1)[:cells + 1]) + "\n")


def cut_mtx(src: Path, dest: Path, max_col: int) -> None:
    """Keep the entries of the first max_col barcodes; the files are sorted by barcode."""
    kept, header = [], None
    with gzip.open(src, "rt") as fh:
        for line in fh:
            if line.startswith("%"):
                continue
            if header is None:
                header = line.split()
                continue
            r, c, v = line.split()
            if int(c) > max_col:
                break
            kept.append(line)
    with gzip.open(dest, "wt") as out:
        out.write("%%MatrixMarket matrix coordinate integer general\n%\n")
        out.write(f"{header[0]} {max_col} {len(kept)}\n")
        out.writelines(kept)


def cut_lines(src: Path, dest: Path, n: int) -> None:
    with gzip.open(src, "rt") as fh, gzip.open(dest, "wt") as out:
        for i, line in enumerate(fh):
            if i >= n:
                break
            out.write(line)


def spec(units: list) -> dict:
    return {"job_id": "smoke", "min_free_out_bytes": 0, "min_free_stage_bytes": 200 << 20, "units": units}


def source(sid: str, path: Path) -> dict:
    return {"id": sid, "files": [{"role": "cut-out for the smoke test", "locator": str(path),
                                  "bytes": path.stat().st_size, "sha256": "not hashed in the smoke test"}]}


def run(py: str, spec_path: Path, out: Path, stage: Path, extra: list[str]) -> int:
    cmd = [py, str(HERE / "rlab_job.py"), "--spec", str(spec_path), "--stage", str(stage), "--out", str(out), *extra]
    print(" ".join(cmd), flush=True)
    return subprocess.run(cmd).returncode


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    d = a.data_root
    cut = a.out / "cut"
    cut.mkdir(parents=True)
    axis = d / "raw/controls/gene_names.csv"
    py = sys.executable

    # HIPSCI cut-out
    hip = d / "external/hipsci"
    cut_hipsci(hip / "GenomeWideScreen_FitnessGenes_RNA-UMI-Counts.csv.gz", cut / "hipsci_fit_cut.csv.gz", 400, 1200)
    # Jurkat cut-out
    ch = d / "external/jurkat_gse249595/channels"
    pre = "GSM7951428_channel16"
    for k in ("transcriptome", "guides", "labels"):
        cut_mtx(ch / f"{pre}_{k}_matrix.mtx.gz", cut / f"{pre}_{k}_matrix.mtx.gz", 60000)
        cut_lines(ch / f"{pre}_{k}_barcode.tsv.gz", cut / f"{pre}_{k}_barcode.tsv.gz", 60000)
        shutil.copyfile(ch / f"{pre}_{k}_features.tsv.gz", cut / f"{pre}_{k}_features.tsv.gz")

    units = [
        {"name": "hepg2_nadig", "adapter": "h5ad",
         "kwargs": {"path": str(d / "raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad"), "study": "hepg2_nadig",
                    "context": "HepG2", "chemistry": "10x 3'", "modality": "CRISPRi", "axis_csv": str(axis),
                    "block": 500},
         "source": source("hepg2_nadig", d / "raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad")},
        {"name": "hipsci_fit_cut", "adapter": "hipsci",
         "kwargs": {"counts": str(cut / "hipsci_fit_cut.csv.gz"),
                    "metadata": str(hip / "GenomeWideScreen_FitnessGenes_Cell-Metadata.tsv.gz"),
                    "study": "hipsci_gw_fitness", "axis_csv": str(axis), "work": "{WORK}/buckets/hipsci_fit_cut",
                    "block": 250, "cells_per_pass": 500, "min_free_bytes": 100 << 20},
         "source": source("hipsci_gw_fitness", cut / "hipsci_fit_cut.csv.gz")},
        {"name": "jurkat_ch16_cut", "adapter": "mtx10x",
         "kwargs": {"prefix": str(cut / pre), "study": "jurkat_gse249595", "context": "Jurkat",
                    "axis_csv": str(axis), "panel_csv": str(d / "external/jurkat_gse249595/table_s2_panel.csv"),
                    "min_umi": 100, "block": 2000},
         "source": source("jurkat_gse249595", cut / f"{pre}_transcriptome_matrix.mtx.gz")},
    ]
    results = {}
    # HepG2 alone with --max-cells (the source-level parity does not apply to a prefix of the file)
    s1 = a.out / "spec_hepg2.json"
    s1.write_text(json.dumps(spec(units[:1])), encoding="utf-8")
    results["hepg2"] = run(py, s1, a.out / "hepg2_a", a.out / "stage_a", ["--max-cells", "1500"])
    results["hepg2_reuse"] = run(py, s1, a.out / "hepg2_b", a.out / "stage_b",
                                 ["--max-cells", "1500", "--reuse", str(a.out / "hepg2_a")])
    # the two cut-outs are whole files: their source-level parity applies
    s2 = a.out / "spec_cuts.json"
    s2.write_text(json.dumps(spec(units[1:])), encoding="utf-8")
    results["cuts"] = run(py, s2, a.out / "cuts", a.out / "stage_c", ["--set", f"WORK={a.out / 'work'}"])
    print(json.dumps(results))
    sys.exit(0 if not any(results.values()) else 1)


if __name__ == "__main__":
    main()
