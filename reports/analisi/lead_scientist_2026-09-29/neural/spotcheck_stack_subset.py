"""Two complete K562 source rows: verify CSR counts/IDs against original raw file."""
import argparse
import json
from pathlib import Path

import h5py
import numpy as np


def value(group, column, row):
    node = group[column]
    if isinstance(node, h5py.Group):
        if "categories" in node:
            result = node["categories"][int(node["codes"][row])]
        elif "values" in node:
            if "mask" in node and bool(node["mask"][row]):
                return None
            result = node["values"][row]
        else:
            raise ValueError(f"Unsupported metadata encoding: {column} / {list(node)}")
    elif "__categories" in group and column in group["__categories"]:
        result = group["__categories"][column][int(node[row])]
    else:
        result = node[row]
    return result.decode() if isinstance(result, bytes) else str(result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["source", "original", "out"]:
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    report = json.loads((a.source / "report.json").read_text())
    results = []
    with h5py.File(a.original, "r") as raw:
        if raw["X"].shape != (1989578, 8248) or raw["X"].dtype != np.dtype("float32"):
            raise ValueError("Unexpected original matrix layout")
        index = raw["obs"].attrs.get("_index", "_index")
        if isinstance(index, bytes):
            index = index.decode()
        if index not in raw["obs"]:
            index = "index"
        for part in ["cells_part000.h5ad", "cells_part007.h5ad"]:
            with h5py.File(a.source / part, "r") as f:
                row = 0
                original_row = int(f["obs/source_row"][row])
                start, end = map(int, f["X/indptr"][row:row + 2])
                data = f["X/data"][start:end]
                columns = f["X/indices"][start:end]
                dense = np.zeros(8248, dtype=np.float32)
                dense[columns] = data
                original_dense = raw["X"][original_row, :]
                gene, raw_gene = value(f["obs"], "gene", row), value(raw["obs"], "gene", original_row)
                barcode = value(f["obs"], "barcode", row)
                raw_barcode = value(raw["obs"], index, original_row)
                item = {"part": part, "subset_row": row, "source_row": original_row,
                        "gene": gene, "original_gene": raw_gene, "gene_match": gene == raw_gene,
                        "barcode_match": barcode == raw_barcode, "count_columns": len(dense),
                        "counts_equal_all_columns": bool(np.array_equal(dense, original_dense)),
                        "sample_counts_integral_nonnegative": bool(np.isfinite(data).all() and (data >= 0).all()
                                                                   and (data == np.floor(data)).all()),
                        "library_size": float(dense.sum()), "nonzero": len(data)}
                if not all(item[k] for k in ["gene_match", "barcode_match", "counts_equal_all_columns", "sample_counts_integral_nonnegative"]):
                    raise ValueError(f"Subset spot check failed: {item}")
                results.append(item)
    result = {"claim": "two selected K562 rows exactly verified; not a whole-file equivalence proof",
        "original_bytes_current": a.original.stat().st_size, "historical_extraction_md5": report["md5"],
        "historical_size_matches": a.original.stat().st_size == report["bytes"],
        "whole_file_hash_recomputed": False, "checks": results}
    with a.out.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
