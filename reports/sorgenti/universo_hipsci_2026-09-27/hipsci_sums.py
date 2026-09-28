"""Stream genes-by-cells HIPSCI CSV.gz counts into the kolf_sums archive format.

    scripts/py.cmd reports/sorgenti/universo_hipsci_2026-09-27/hipsci_sums.py --selftest
    scripts/py.cmd reports/sorgenti/universo_hipsci_2026-09-27/hipsci_sums.py \
        --counts FILE.csv.gz --metadata FILE.tsv.gz --out NEW_DIR --per-line

Libraries include every Gene-Expression row, including unmapped and duplicate rows.
Only the first row mapping to each axis gene supplies its count column. The CSV
reader holds at most --rows-per-batch numeric rows; maps are closed each batch.
"""
from __future__ import annotations

import argparse
from collections import Counter
import contextlib
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import zipfile

import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))
sys.path.insert(0, str(HERE.parent / "universo_kolf_2026-09-27"))
from kolf_sums import _publish  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.resources import peak_rss_bytes  # noqa: E402

ANNOTATION = Path("C:/Users/ferra/vcc2026-data/external/annotation/gene_coordinates_gencode_v50.tsv")
GUIDE = re.compile(r"^([^_]+)_([ACGT]+)$")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def count_batches(path: Path, n_cells: int, batch_size: int):
    """Stream CSV records without allocating a pandas/Arrow schema per cell column.

    A numeric batch plus one parsed CSV record bounds wide-row memory. CSV quoting
    is honored; short/long rows, nonintegers and int64 overflows fail explicitly.
    """
    with gzip.open(path, "rt", newline="") as f:
        reader = csv.reader(f)
        next(reader)
        while True:
            values = np.empty((batch_size, n_cells), dtype=np.int64)
            labels = []
            for j in range(batch_size):
                row = next(reader, None)
                if row is None:
                    break
                if len(row) != n_cells + 1:
                    raise ValueError(f"count row has {len(row) - 1} cells; expected {n_cells}")
                labels.append(row[0])
                values[j] = np.asarray(row[1:], dtype=np.int64)
                del row
            if not labels:
                return
            yield labels, values[:len(labels)]


def run(counts: Path, metadata: Path, out: Path, *, annotation: Path = ANNOTATION,
        pools: int = 8, per_line: bool = False, rows_per_batch: int = 4,
        axis=None, unassigned_as_control: bool = False) -> dict:
    """Write a new archive, group table, basal CPM table and completion manifest."""
    if out.exists():
        raise FileExistsError(out)
    if pools < 1 or not 1 <= rows_per_batch <= 16:
        raise ValueError("pools must be positive; rows-per-batch must be in 1..16")
    axis = np.asarray(official_axis().symbols if axis is None else axis, dtype=str)
    lookup = {g: i for i, g in enumerate(axis)}
    if len(lookup) != len(axis):
        raise ValueError("duplicate axis symbols")
    ids = {}
    ann = pd.read_csv(annotation, sep="\t", dtype=str, keep_default_na=False)
    for row in ann.itertuples(index=False):
        ids.setdefault(row.gene_id.split(".")[0], row.symbol)
    ids = {gene_id: lookup[symbol] for gene_id, symbol in ids.items() if symbol in lookup}
    del ann
    with gzip.open(counts, "rt", newline="") as f:
        header = next(csv.reader(f))
    cells = header[1:]
    if header[0] or len(set(cells)) != len(cells):
        raise ValueError("expected empty first header field and unique cell IDs")
    meta = pd.read_csv(metadata, sep="\t", dtype={"Cell_ID": str, "Batch": "category",
                                                "Guide_Call": "category", "Cell_Line": "category"},
                       keep_default_na=False)
    if meta.Cell_ID.duplicated().any():
        raise ValueError("duplicate metadata Cell_ID")
    prefixes = {v[:3] for v in meta.Cell_ID}
    if len(prefixes) != 1 or not prefixes <= {"MP-", "PC-"}:
        raise ValueError(f"unexpected metadata prefixes: {prefixes}")
    prefix = next(iter(prefixes))
    meta.index = meta.Cell_ID.str.slice(3)
    id_rule = "metadata prefix stripped"
    if not set(meta.index) & set(cells):
        # the targeted screen's count header drops the day: metadata PC-P4-D3_I73_<bc> is P4_I73_<bc> there
        stripped = meta.index.str.replace(r"^(P\d+)-D\d+_", r"\1_", regex=True)
        if stripped.is_unique and set(stripped) & set(cells):
            meta.index = stripped
            id_rule = "metadata prefix and day stripped (P<n>-D<d>_ -> P<n>_)"
    batches = sorted(set(meta.Batch))
    batch_pool = {b: i % pools for i, b in enumerate(batches)}
    absent_meta = sorted(set(cells) - set(meta.index))
    absent_counts = sorted(set(meta.index) - set(cells))
    absent_counts_ids = meta.loc[absent_counts, "Cell_ID"].tolist()
    aligned = meta.reindex(cells)
    targets_by_call = {}
    for value in meta.Guide_Call.cat.categories:
        call = GUIDE.fullmatch(value)
        if call is not None:
            targets_by_call[value] = "NTC" if call[1] == "NonTarget" else call[1]
    if unassigned_as_control:
        # the authors' own controls (13b_01 and others): control_tag <- c("unassigned", "NonTarget")
        targets_by_call["unassigned"] = "NTC"
    target = aligned.Guide_Call.astype(object).map(targets_by_call)
    valid = target.notna().to_numpy()
    unmatched = aligned.Cell_ID.isna().to_numpy()
    unassigned = (aligned.Guide_Call == "unassigned").to_numpy()
    dropped = {"no_metadata": int(unmatched.sum()),
               "unassigned": 0 if unassigned_as_control else int(unassigned.sum()),
               "invalid_guide_call": int((~valid & ~unmatched & ~unassigned).sum())}
    cell_rows = np.flatnonzero(valid)
    if not cell_rows.size:
        raise ValueError("no eligible cells")
    target_names, target_codes = np.unique(target.to_numpy()[valid], return_inverse=True)
    pool_codes = aligned.Batch.astype(object).map(batch_pool).to_numpy()[valid].astype(np.int64)
    group_codes = target_codes * pools + pool_codes
    context_names = np.array(["pooled"])
    if per_line:
        lines = aligned.Cell_Line.astype(object).to_numpy()[valid]
        if any(not isinstance(v, str) or not v or v == "pooled" for v in lines):
            raise ValueError("per-line requires nonempty Cell_Line distinct from 'pooled'")
        names, codes = np.unique(lines, return_inverse=True)
        context_names = np.concatenate([["pooled"], names])
        group_codes = np.concatenate([group_codes, (codes + 1) * len(target_names) * pools + group_codes])
        cell_rows = np.tile(cell_rows, 2)
    unique, inverse = np.unique(group_codes, return_inverse=True)
    keys = [(context_names[k // (len(target_names) * pools)], target_names[(k // pools) % len(target_names)],
             int(k % pools)) for k in unique]
    indicator = sp.csr_matrix((np.ones(len(inverse)), (cell_rows, inverse)), shape=(len(cells), len(keys)))
    groups = pd.DataFrame(keys, columns=["context", "target", "pool"])
    groups["n_cells"] = np.asarray(indicator.sum(axis=0)).ravel().astype(np.int64)
    del aligned, meta, header, target, valid, unmatched, unassigned, cell_rows, group_codes, inverse
    del target_codes, pool_codes
    if per_line:
        del lines, codes
    out.mkdir(parents=True, exist_ok=False)
    groups.to_csv(out / "groups.csv", index=False)
    pd.DataFrame({"Cell_ID": absent_counts_ids}).to_csv(out / "metadata_only.csv", index=False)
    pd.DataFrame({"Cell_ID": absent_meta}).to_csv(out / "counts_only.csv", index=False)
    columns = np.full(len(axis), -1, dtype=np.int64)
    library = np.zeros(len(cells), dtype=np.float64)
    rows = Counter()
    contexts = sorted(set(groups.context))
    basal = np.full((len(axis), len(contexts)), np.nan)
    with tempfile.TemporaryDirectory(prefix=".hipsci-", dir=out) as tmp:
        matrix = Path(tmp) / "sums.npy"
        mm = np.lib.format.open_memmap(matrix, mode="w+", dtype="<f4",
                                       shape=(len(keys), len(axis)), fortran_order=True)
        del mm
        # Closing each map bounds resident mapped pages, including during initialization.
        for start in range(0, len(axis), 16):
            mm = np.lib.format.open_memmap(matrix, mode="r+")
            mm[:, start:start + 16] = np.nan
            mm.flush()
            del mm
        position = 0
        reader = count_batches(counts, len(cells), rows_per_batch)
        with contextlib.closing(reader):
            for labels, values in reader:
                if values.shape[1] != len(cells) or (values < 0).any():
                    raise ValueError("invalid count row width or negative counts")
                keep, mapped = [], []
                for j, label in enumerate(labels):
                    parts = label.split(":")
                    rows["read"] += 1
                    if len(parts) != 3:
                        raise ValueError(f"invalid feature label: {label}")
                    if parts[2] != "Gene-Expression":
                        rows["non_gene_expression"] += 1
                        continue
                    keep.append(j)
                    rows["gene_expression"] += 1
                    idx = ids.get(parts[0].split(".")[0])
                    how = "mapped_by_id"
                    if idx is None:
                        idx = lookup.get(parts[1])
                        how = "mapped_by_symbol"
                    if idx is None:
                        rows["unmapped"] += 1
                    elif columns[idx] >= 0:
                        rows["duplicate_axis_gene"] += 1
                    else:
                        columns[idx] = position + j
                        rows[how] += 1
                        mapped.append((j, idx))
                if keep:
                    library += values[keep].sum(axis=0, dtype=np.float64)
                if mapped:
                    sums = indicator.T @ values[[j for j, _ in mapped]].T
                    mm = np.lib.format.open_memmap(matrix, mode="r+")
                    for j, (_, idx) in enumerate(mapped):
                        mm[:, idx] = sums[:, j]
                    mm.flush()
                    del mm, sums
                position += len(labels)
                if position % 1000 < rows_per_batch:
                    print(f"rows {position}; mapped {int((columns >= 0).sum())}", flush=True)
        totals = np.asarray(indicator.T @ library).ravel()
        for j, context in enumerate(contexts):
            ctrl = np.flatnonzero((groups.context == context) & (groups.target == "NTC"))
            denominator = totals[ctrl].sum()
            if denominator > 0:
                for start in range(0, len(axis), 16):
                    mm = np.lib.format.open_memmap(matrix, mode="r")
                    basal[start:start + 16, j] = 1e6 * mm[ctrl, start:start + 16].sum(axis=0, dtype=np.float64) / denominator
                    del mm
        table = {k: groups[k].to_numpy(dtype=str if k in ("target", "context") else np.int64)
                 for k in groups.columns}
        table.update(total_counts=totals, genes=axis, file_columns=columns,
                     missing_genes=axis[columns < 0], groups_sha256=digest(out / "groups.csv"),
                     url=counts.resolve().as_uri())
        _publish(out / "sums.npz", table, matrix)
    pd.DataFrame(basal, index=pd.Index(axis, name="gene_name"), columns=contexts).to_csv(out / "basal.csv")
    context_counts = {}
    for context in contexts:
        g = groups[groups.context == context]
        context_counts[context] = {"cells": int(g.n_cells.sum()),
                                   "ntc_cells": int(g.loc[g.target == "NTC", "n_cells"].sum()),
                                   "targets": int(g.loc[g.target != "NTC", "target"].nunique()),
                                   "groups_below_10_cells": int((g.n_cells < 10).sum())}
    manifest = {"inputs": {k: {"path": str(p), "bytes": p.stat().st_size, "sha256": digest(p)}
                           for k, p in [("counts", counts), ("metadata", metadata), ("annotation", annotation)]},
                "cells": {"read": len(cells), "matched": len(cells) - len(absent_meta),
                          "retained": len(cells) - sum(dropped.values()), "dropped_by_reason": dict(dropped),
                          "counts_only": len(absent_meta), "metadata_only": len(absent_counts)},
                "metadata_prefix": prefix, "id_rule": id_rule, "rows": dict(rows), "contexts": context_counts,
                "rows_kept_on_axis": int((columns >= 0).sum()),
                "rows_dropped_from_axis_by_reason": {k: rows[k] for k in
                    ("non_gene_expression", "unmapped", "duplicate_axis_gene")},
                "targets": sorted(set(groups.target)), "batch_to_pool": batch_pool,
                "options": {"pools": pools, "per_line": per_line, "rows_per_batch": rows_per_batch,
                            "controls": "NonTarget + unassigned (the authors' choice)" if unassigned_as_control
                            else "NonTarget only"},
                "library": "All Gene-Expression rows, including unmapped and duplicate rows; other feature types excluded",
                "duplicate_policy": "First annotation ID and first mapped source row win; symbol fallback",
                "peak_rss_bytes": peak_rss_bytes()}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(context_counts, indent=2), flush=True)
    return manifest


def selftest() -> int:
    results = []

    def check(name, ok):
        results.append(bool(ok))
        print(f"{'PASS' if ok else 'FAIL'} {name}", flush=True)

    with tempfile.TemporaryDirectory(prefix="hipsci-selftest-") as tmp:
        root = Path(tmp)
        counts, metadata, ann = root / "counts.csv.gz", root / "metadata.tsv.gz", root / "ann.tsv"
        cells = [f"MD-P1-D6_I1_CELL{i}-1" for i in range(7)]
        data = [[1, 2, 3, 4, 5, 6, 7], [2] * 7, [3] * 7, [100] * 7, [4] * 7]
        with gzip.open(counts, "wt", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([""] + cells)
            for label, row in zip(["ENSG1.7:WRONG:Gene-Expression", "UNKNOWN:B:Gene-Expression",
                                   "ENSG9:X:Gene-Expression", "ENSG2:B:Antibody-Capture",
                                   "ENSG1:A:Gene-Expression"], data):
                writer.writerow([label] + row)
        pd.DataFrame({"Cell_ID": ["MP-" + c for c in cells[:6]] + ["MP-extra"],
                      "Batch": [f"GenomeWideScreen_Pool1_Day6_Inlet{i % 2 + 1}" for i in range(7)],
                      "Guide_Call": ["NonTarget_ACGT", "NonTarget_TGCA", "T_ACGT", "T_TGCA",
                                     "unassigned", "bad_call", "T_ACGT"],
                      "Cell_Line": ["L1", "L2", "L1", "L2", "L1", "L2", "L1"]}).to_csv(metadata, sep="\t", index=False)
        pd.DataFrame({"symbol": ["A", "B", "B"], "gene_id": ["ENSG1.2", "ENSG2.1", "ENSG1.9"]}).to_csv(ann, sep="\t", index=False)
        with contextlib.redirect_stdout(io.StringIO()):
            man = run(counts, metadata, root / "out", annotation=ann, per_line=True, pools=1,
                      rows_per_batch=2, axis=["A", "B", "C"])
        with np.load(root / "out/sums.npz") as z:
            sums, total = z["sums"], z["total_counts"]
            keys = list(zip(z["context"], z["target"]))
            at = lambda c, t: keys.index((c, t))
            check("count sums and absent NaNs", np.array_equal(sums[at("pooled", "T"), :2], [7, 4]) and np.isnan(sums[:, 2]).all())
            check("libraries include unmapped and duplicate GE only", total[at("pooled", "T")] == 25 and total[at("pooled", "NTC")] == 21)
            check("pooled equals sum of lines", all(
                np.allclose(sums[at("pooled", t)], sums[at("L1", t)] + sums[at("L2", t)], equal_nan=True)
                and total[at("pooled", t)] == total[at("L1", t)] + total[at("L2", t)]
                and z["n_cells"][at("pooled", t)] == z["n_cells"][at("L1", t)] + z["n_cells"][at("L2", t)]
                for t in ["T", "NTC"]))
            check("mapping by versionless ID then symbol", man["rows"]["mapped_by_id"] == 1 and man["rows"]["mapped_by_symbol"] == 1 and z["file_columns"].tolist() == [0, 1, -1])
            with zipfile.ZipFile(root / "out/sums.npz") as archive:
                stored = archive.getinfo("sums.npy").compress_type == zipfile.ZIP_STORED
            check("Fortran float32 stored archive", sums.flags.f_contiguous and sums.dtype == np.float32 and stored)
        check("drops and unmatched both ways", man["cells"]["dropped_by_reason"] == {"unassigned": 1, "invalid_guide_call": 1, "no_metadata": 1} and man["cells"]["metadata_only"] == 1 and man["rows"]["non_gene_expression"] == 1 and man["rows"]["duplicate_axis_gene"] == 1)
        basal = pd.read_csv(root / "out/basal.csv").set_index("gene_name")
        check("basal uses context NTC library", np.isclose(basal.loc["A", "pooled"], 1e6 * 3 / 21))
        frame = pd.read_csv(metadata, sep="\t")
        frame.Cell_ID = frame.Cell_ID.str.replace("MP-", "PC-", regex=False)
        frame.to_csv(root / "pc.tsv.gz", sep="\t", index=False)
        with contextlib.redirect_stdout(io.StringIO()):
            pc = run(counts, root / "pc.tsv.gz", root / "pc", annotation=ann, pools=2,
                     rows_per_batch=1, axis=["A", "B", "C"])
        with np.load(root / "pc/sums.npz") as z:
            check("PC prefix and sorted batch pools", pc["metadata_prefix"] == "PC-"
                  and z["pool"].tolist() == [0, 1, 0, 1] and z["n_cells"].tolist() == [1] * 4
                  and set(z["context"]) == {"pooled"})
        try:
            run(counts, metadata, root / "out", annotation=ann, axis=["A"])
            refused = False
        except FileExistsError:
            refused = True
        check("never overwrite", refused)
        with contextlib.redirect_stdout(io.StringIO()):
            ua = run(counts, metadata, root / "ua", annotation=ann, pools=1, rows_per_batch=2,
                     axis=["A", "B", "C"], unassigned_as_control=True)
        with np.load(root / "ua/sums.npz") as z:
            ntc = list(z["target"]).index("NTC")
            check("unassigned as controls (added 27/09 night)", int(z["n_cells"][ntc]) == 3
                  and ua["cells"]["dropped_by_reason"]["unassigned"] == 0
                  and ua["options"]["controls"].startswith("NonTarget + unassigned"))
        day_counts = root / "day.csv.gz"
        day_cells = [f"P1_I1_CELL{i}-1" for i in range(7)]
        with gzip.open(day_counts, "wt", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([""] + day_cells)
            for label, row in zip(["ENSG1:A:Gene-Expression", "ENSG2:B:Gene-Expression"], data[:2]):
                writer.writerow([label] + row)
        day_meta = pd.read_csv(metadata, sep="\t")
        day_meta.Cell_ID = ["PC-P1-D3_I1_" + c.split("_I1_")[1] if "_I1_" in c else "PC-P1-D3_I1_extra"
                            for c in day_meta.Cell_ID]
        day_meta.to_csv(root / "day.tsv.gz", sep="\t", index=False)
        with contextlib.redirect_stdout(io.StringIO()):
            dm = run(day_counts, root / "day.tsv.gz", root / "day", annotation=ann, pools=1, rows_per_batch=2,
                     axis=["A", "B", "C"])
        check("day dropped from the targeted screen's ids (added 27/09 night)",
              dm["id_rule"].startswith("metadata prefix and day stripped") and dm["cells"]["counts_only"] == 1)
        wide = root / "wide.csv.gz"
        width = 200000
        with gzip.open(wide, "wt", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([""] + [f"cell{i}" for i in range(width)])
            for value in range(1, 4):
                writer.writerow([f"ENSG{value}:G{value}:Gene-Expression"] + [value] * width)
        shapes, total = [], 0
        for labels, values in count_batches(wide, width, 2):
            shapes.append(values.shape)
            total += int(values.sum())
        check("200000-cell-wide bounded batches", shapes == [(2, width), (1, width)] and total == 6 * width)
    print(f"selftest: {sum(results)} of {len(results)} checks passed")
    peak = peak_rss_bytes()
    print(f"peak working set: {peak / 2**20:.1f} MiB" if peak is not None else "peak working set: unavailable")
    return int(not all(results))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--counts", type=Path)
    ap.add_argument("--metadata", type=Path)
    ap.add_argument("--annotation", type=Path, default=ANNOTATION)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--pools", type=int, default=8)
    ap.add_argument("--rows-per-batch", type=int, default=4)
    ap.add_argument("--per-line", action="store_true")
    ap.add_argument("--unassigned-as-control", action="store_true",
                    help="cells without a guide call join the NonTarget cells as controls, as the authors did")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if any(x is None for x in (args.counts, args.metadata, args.out)):
        ap.error("--counts, --metadata and --out are required")
    run(args.counts, args.metadata, args.out, annotation=args.annotation, pools=args.pools,
        per_line=args.per_line, rows_per_batch=args.rows_per_batch,
        unassigned_as_control=args.unassigned_as_control)


if __name__ == "__main__":
    main()
