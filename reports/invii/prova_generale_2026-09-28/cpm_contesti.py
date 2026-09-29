"""Step 4 of the dress rehearsal: each context's control CPM on the official axis, from its own controls.

For each label of ``--contexts``, ``<controls-dir>/context_<label>.h5ad`` is read in row blocks
(never the whole matrix). The CPM written is the mean over control cells of each cell's CPM, the
definition of ``interim/basal_cpm_by_context.csv`` (measured on A on 28/09: max relative difference
9e-14). The pooled CPM of `vcc2026.inference.read_basal_profile` (summed counts / grand total), which
the protocol named, differs from that file by up to 83% on low-count genes; that reader is still run,
for the label inside the file (stage 45 refuses a file whose label differs from its name), the cells
and the library sizes. Genes go on the official axis by the file's own names (NaN for an axis gene
the file lacks). Per context the JSON also records the median library size, which amplitude rule
R-E uses in place of the fixed 20,000 UMI of `transfer_model.detectable_threshold`.

Writes ``--out`` (a new CSV: ``gene_name`` and one column per context, the layout of
``interim/basal_cpm_by_context.csv``) and ``<out stem>.json`` beside it. With ``--parity-with`` each
column is compared with a reference CSV's column under ``--mapping`` (D=B E=A F=C; by default the
draw's mapping in ``estrazione.json`` for labels the reference lacks, the same label otherwise). The
registered rule (protocol, step 4) is a relative difference of at most 1e-9 on every gene,
|a - b| <= 1e-9 max(|a|, |b|), with NaN only where both are NaN.

    scripts/py.cmd reports/invii/prova_generale_2026-09-28/cpm_contesti.py ^
        --controls-dir <data_root>/raw/controls_prova_2026-09-28 --contexts D E F ^
        --out <data_root>/interim/prova_generale_2026-09-28/basal_cpm_DEF.csv ^
        --parity-with <data_root>/interim/basal_cpm_by_context.csv

Memory: one block of 1,000 cells at a time (two passes per file), plus a few vectors per context;
measured on A (18,400 cells), about 270 MiB peak and 10-20 s.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import h5py  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from comune import HERE, data_root, sha256_file, write_new_json, write_new_text  # noqa: E402
from vcc2026.inference import read_basal_profile  # noqa: E402
from vcc2026.resources import peak_rss_bytes  # noqa: E402

RULE_REL = 1e-9


def file_genes(path: Path) -> np.ndarray:
    """The var index, read by anndata's own element reader (whatever its on-disk encoding)."""
    from anndata.io import read_elem

    with h5py.File(path, "r") as f:
        return np.asarray(read_elem(f["var"]).index).astype(str)


def mean_cell_cpm(path: Path, block_rows: int = 1000) -> tuple[np.ndarray, int, int]:
    """(mean over cells of each cell's CPM, cells, cells with no counts), streamed in row blocks.

    This is the definition of ``interim/basal_cpm_by_context.csv`` (measured 28/09 on A: max relative
    difference 9e-14), not the pooled sum of `read_basal_profile`, which differs by up to 83%."""
    with h5py.File(path, "r") as f:
        n_cells, n_genes = (int(v) for v in f["X"].attrs["shape"])
        indptr = f["X/indptr"][:].astype(np.int64)
        acc = np.zeros(n_genes, dtype=np.float64)
        empty = 0
        for a in range(0, n_cells, block_rows):
            b = min(a + block_rows, n_cells)
            lo, hi = int(indptr[a]), int(indptr[b])
            values = f["X/data"][lo:hi].astype(np.float64)
            columns = f["X/indices"][lo:hi]
            rows = np.repeat(np.arange(b - a), np.diff(indptr[a:b + 1]))
            lib = np.bincount(rows, weights=values, minlength=b - a)
            empty += int((lib <= 0).sum())
            scale = np.divide(1e6, lib, out=np.zeros_like(lib), where=lib > 0)
            np.add.at(acc, columns, values * scale[rows])
    return acc / n_cells, n_cells, empty


def context_cpm(path: Path, label: str, axis: np.ndarray, block_rows: int = 1000) -> tuple[np.ndarray, dict]:
    """(CPM on ``axis``, facts) of one control file: the mean per-cell CPM, plus stage 45's reader for
    the label, the cells and the library sizes."""
    prof = read_basal_profile(path, block_rows=block_rows)
    genes = file_genes(path)
    if genes.size != prof.profile.size:
        raise SystemExit(f"{path}: {genes.size} gene names for {prof.profile.size} columns")
    values, n_cells, empty = mean_cell_cpm(path, block_rows)
    cpm = pd.Series(values, index=pd.Index(genes))
    if cpm.index.duplicated().any():
        raise SystemExit(f"{path}: a gene name appears twice")
    on_axis = cpm.reindex(axis).to_numpy(dtype=np.float64)
    pooled = prof.profile / float(prof.profile.sum()) * 1e6
    big = np.maximum(np.abs(pooled), np.abs(values))
    rel = np.divide(np.abs(pooled - values), big, out=np.zeros_like(big), where=big > 0)
    facts = {"path": str(path), "label_in_file": prof.context, "label_ok": prof.context == label,
             "cells": int(prof.n_cells), "cells_without_counts": empty, "total_counts": float(prof.profile.sum()),
             "median_library_size": float(np.median(prof.library_sizes)),
             "genes_in_file": int(genes.size), "axis_genes_missing": int(np.isnan(on_axis).sum()),
             "genes_at_5_cpm_or_more": int((on_axis >= 5).sum()),
             "pooled_cpm_max_rel_diff_from_written": float(rel.max()) if rel.size else 0.0}
    if n_cells != prof.n_cells:
        raise SystemExit(f"{path}: two readers disagree on the cells ({n_cells} vs {prof.n_cells})")
    return on_axis, facts


def parity(mine: np.ndarray, ref: np.ndarray, rel: float = RULE_REL) -> dict:
    a, b = np.asarray(mine, dtype=np.float64), np.asarray(ref, dtype=np.float64)
    na, nb = np.isnan(a), np.isnan(b)
    both = ~na & ~nb
    scale = np.maximum(np.abs(a[both]), np.abs(b[both]))
    diff = np.abs(a[both] - b[both])
    r = np.divide(diff, scale, out=np.zeros_like(diff), where=scale > 0)
    out = {"nan_mismatches": int((na != nb).sum()), "max_abs_diff": float(diff.max()) if diff.size else 0.0,
           "max_rel_diff": float(r.max()) if r.size else 0.0, "genes_above_rule": int((r > rel).sum()),
           "rule_rel": rel}
    out["rule_passed"] = out["nan_mismatches"] == 0 and out["genes_above_rule"] == 0
    return out


def parse_mapping(specs: list[str], contexts: list[str], ref_columns: list[str], estrazione: Path) -> dict:
    if specs:
        pairs = [s.split("=", 1) for s in specs]
        if any(len(p) != 2 for p in pairs):
            raise SystemExit(f"--mapping wants NEW=OLD pairs, got {specs}")
        return dict(pairs)
    drawn = {}
    if estrazione.exists():
        drawn = json.loads(estrazione.read_text(encoding="utf-8")).get("mapping_new_to_old", {})
    return {c: (c if c in ref_columns else drawn.get(c)) for c in contexts}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    root = data_root()
    ap.add_argument("--controls-dir", type=Path, required=True)
    ap.add_argument("--contexts", nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--axis", type=Path, default=None,
                    help="a gene_names.csv giving the axis (default: vcc2026.genes.official_axis)")
    ap.add_argument("--parity-with", type=Path, default=None,
                    help=f"reference CSV, e.g. {root / 'interim' / 'basal_cpm_by_context.csv'}")
    ap.add_argument("--mapping", nargs="*", default=[], metavar="NEW=OLD")
    ap.add_argument("--estrazione", type=Path, default=HERE / "estrazione.json")
    args = ap.parse_args()
    t0 = time.time()
    side = args.out.with_suffix(".json")
    for p in (args.out, side):
        if p.exists():
            raise SystemExit(f"{p} exists; choose a new --out")
    contexts = [c.strip() for part in args.contexts for c in part.split(",") if c.strip()]
    if args.axis is not None:
        axis = pd.read_csv(args.axis).iloc[:, 0].astype(str).to_numpy()
    else:
        from vcc2026.genes import official_axis

        axis = np.asarray(official_axis().symbols).astype(str)

    columns, facts = {}, {}
    for c in contexts:
        path = args.controls_dir / f"context_{c}.h5ad"
        columns[c], facts[c] = context_cpm(path, c, axis)
        facts[c]["sha256"] = sha256_file(path)
        print(f"{c}: {facts[c]['cells']} cells, median library {facts[c]['median_library_size']:.0f}, "
              f"{facts[c]['genes_at_5_cpm_or_more']} genes >= 5 CPM, label ok {facts[c]['label_ok']}", flush=True)
    frame = pd.DataFrame(columns, index=pd.Index(axis, name="gene_name"))

    summary = {"script": "reports/invii/prova_generale_2026-09-28/cpm_contesti.py",
               "controls_dir": str(args.controls_dir), "contexts": contexts, "axis_genes": int(axis.size),
               "definition": "summed control counts / grand total x 1e6 (vcc2026.inference.read_basal_profile)",
               "per_context": facts}
    if args.parity_with is not None:
        ref = pd.read_csv(args.parity_with).set_index("gene_name").reindex(axis)
        mapping = parse_mapping(args.mapping, contexts, list(ref.columns), args.estrazione)
        summary["parity"] = {"reference": str(args.parity_with), "reference_sha256": sha256_file(args.parity_with),
                             "mapping_new_to_reference": mapping, "per_context": {}}
        for c in contexts:
            old = mapping.get(c)
            if old not in ref.columns:
                summary["parity"]["per_context"][c] = {"reference_column": old, "missing": True, "rule_passed": False}
                continue
            summary["parity"]["per_context"][c] = {"reference_column": old,
                                                   **parity(frame[c].to_numpy(), ref[old].to_numpy())}
        summary["parity"]["rule_passed"] = all(v["rule_passed"] for v in summary["parity"]["per_context"].values())
        for c, v in summary["parity"]["per_context"].items():
            print(f"parity {c} vs {v['reference_column']}: passed {v['rule_passed']}, "
                  f"max rel {v.get('max_rel_diff', float('nan')):.3g}, NaN mismatches {v.get('nan_mismatches')}")

    write_new_text(args.out, frame.to_csv(lineterminator="\n"))
    summary.update({"out": str(args.out), "out_sha256": sha256_file(args.out),
                    "written_utc": datetime.now(timezone.utc).isoformat(), "seconds": round(time.time() - t0, 1),
                    "peak_rss_bytes": peak_rss_bytes()})
    write_new_json(side, summary)
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
