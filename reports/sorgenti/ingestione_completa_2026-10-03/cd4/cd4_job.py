"""CD4 T cells of Marson 2025 (CRISPRi, Flex) into contract shards: every eligible cell of a range of rows of one file.

The 12 files (4 donors x 3 conditions, 1.74 TB, CSR, measured in corpus_cellulare_2026-09-30/p1_r4/remote/) are read
by HTTP ranges with Codex's adapter (kolf/complete_adapters.py, h5rows_cd4): eligibility is decided on the obs columns
before any count is read, the excluded rows are counted by reason and by lane, and the eligible rows are read and
written, all of them. No sampling at this level: the samples of a training are cut later from this archive.
`--part i/n` gives this runtime the i-th of n contiguous ranges of the rows of the file, cut at multiples of the block:
the rows of a CSR file are contiguous in its data, so a part reads only its own bytes.

A part is judged as a part: the rows counted are the declared range, raw = eligible + excluded, and the eligible rows
are the cells in its shards. That the parts make the file is a later reconciliation.

    python cd4_job.py --spec specs/cd4_v1.json --file D1_Rest --axis gene_names.csv --stage <local dir> --out <new dir> \
        --data-root <root of out> [--runtime-manifest <json>] [--part i/n] [--max-cells N] [--readahead 8] \
        [--source <local D1_Rest.assigned_guide.h5ad>]
"""
from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "kolf"))
import kolf_job as kj  # noqa: E402  (part_range, count_http, heartbeat; it also puts orion/common.py on the path)
from kolf_job import ca, common  # noqa: E402

REQUIRED = ["low_quality", "guide_group", "guide_type", "perturbed_gene_id", "guide_id", "lane_id"]


def precheck(url, axis: Path, n_cells: int, lo: int) -> dict:
    """Fail before reading counts: the matrix, the gene axis and the obs columns the adapter needs."""
    with ca.base._h5_open(url) as f:
        node = f["X"]
        enc = node.attrs.get("encoding-type", "")
        enc = enc.decode() if isinstance(enc, bytes) else str(enc)
        shape = [int(v) for v in node.attrs["shape"]]
        if enc != "csr_matrix" or shape[0] != n_cells:
            sys.exit(f"precheck: X is {enc} of shape {shape}, the spec says CSR with {n_cells} cells")
        absent = sorted(c for c in ("gene_name", "gene_ids") if c not in f["var"])
        absent += sorted(c for c in REQUIRED if c not in f["obs"])
        if absent:
            sys.exit(f"precheck: the file lacks {absent}")
        var = ca.axis_frame(f["var"], str(axis), "gene_name", "gene_ids")
        mapped = int((var["official_index"].to_numpy() >= 0).sum())
        if len(var) != shape[1] or mapped < min(1000, len(var) // 2):
            sys.exit(f"precheck: {len(var)} genes for {shape[1]} columns, {mapped} on the official axis")
        stop = min(n_cells, lo + 1000)
        cols = {c: ca.column(f["obs"], c, lo, stop, required=True) for c in REQUIRED}
        reason, control = ca.cd4_eligibility(cols)
    seen = {"shape": shape, "genes_on_official_axis": mapped, "rows_read": [lo, stop],
            "eligible_in_rows_read": int((reason == "").sum()), "controls_in_rows_read": int(((reason == "") & control).sum())}
    print(f"precheck: {seen}", flush=True)
    return seen


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--file", required=True, help="one of the files of the spec, e.g. D1_Rest")
    p.add_argument("--axis", type=Path, required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--data-root", type=Path)
    p.add_argument("--runtime-manifest", type=Path)
    p.add_argument("--part", help="i/n: the i-th of n contiguous ranges of rows")
    p.add_argument("--max-cells", type=int, help="smoke test: only the first N rows of the range")
    p.add_argument("--source", help="read this file instead of the locator of the spec (fixtures)")
    p.add_argument("--heartbeat-seconds", type=float, default=120.0)
    p.add_argument("--readahead", type=int, default=0,
                   help="read N blocks ahead with N threads (lettura/prefetch.py); 0 = one block at a time")
    a = p.parse_args()
    spec = common.load_json(a.spec)
    src, u, entry = spec["source"], spec["unit"], spec["files"][a.file]
    url = a.source or entry["locator"]
    remote = str(url).startswith(("http://", "https://"))
    http = kj.count_http()
    if a.readahead:
        sys.path.insert(0, str(HERE.parent / "lettura"))
        import prefetch  # noqa: PLC0415
        prefetch.install(ca.base, ahead=a.readahead, threads=a.readahead)
    etag = common.MISSING
    if remote:
        head = common.head(url)
        if head["bytes"] != entry["bytes"]:
            sys.exit(f"{a.file}: {head['bytes']} bytes on the host, {entry['bytes']} in the spec")
        etag = head["etag"]
        threading.Thread(target=kj.heartbeat, args=(http, a.heartbeat_seconds), daemon=True).start()
    lo, hi = kj.part_range(entry["cells"], u["block"], a.part)
    if a.max_cells is not None:
        hi = min(hi, lo + a.max_cells)
    checked = precheck(url, a.axis, entry["cells"], lo)
    common.new_dir(a.out)
    common.new_dir(a.stage)
    unit_name = f"cd4_{a.file}"
    source = common.source_record(src["id"], src["release"], src["license"],
                                  [{"locator": str(url), "bytes": entry["bytes"], "etag": etag}])
    bind = {"spec_sha256": common.sha256_file(a.spec), "file": a.file, "row_range": f"{lo}:{hi}",
            "complete_adapters_sha256": common.sha256_file(HERE.parent / "kolf" / "complete_adapters.py")}
    sink = common.ShardSink(a.out, a.stage, unit_name, source, common.writer_record(Path(__file__), a.runtime_manifest),
                            require=bind)
    exclusions = a.out / unit_name / "exclusions.json"
    for name, x, obs, var, uns in ca.h5rows_cd4(url, u["study"], str(a.axis), exclusions, block=u["block"],
                                                cell_range=(lo, hi), chemistry=u["chemistry"], context=u["context"],
                                                max_gap=u["max_gap"]):
        sink.put(name, x, obs, var, uns)
    report = common.load_json(exclusions)
    unit = sink.finish(
        {"selection_parity": report["raw"] == hi - lo == report["eligible"] + report["excluded"]
         and report["eligible"] == report["emitted"],
         "cells_equal_eligible": sum(s["cells"] for s in sink.shards) == report["eligible"],
         "range_as_declared": report["cell_range"] == [lo, hi] and report["source_rows"] == entry["cells"],
         "one_version_of_the_file": len(http["etags"] | ({etag} if remote and etag != common.MISSING else set())) <= 1},
        {"scope": f"rows {lo}:{hi} of {entry['cells']} of {a.file}", "part": a.part, "smoke_max_cells": a.max_cells,
         "precheck": checked, "readahead": a.readahead, "donor": report["donor"], "condition": report["condition"],
         "rows": {"raw": report["raw"], "eligible": report["eligible"], "excluded": report["excluded"]},
         "by_reason": report["by_reason"], "exclusions_sha256": common.sha256_file(exclusions),
         "http": {"bytes": http["bytes"], "requests": http["requests"], "etags": sorted(http["etags"])}, **bind})
    tag = f"{spec['job_id']}_{a.file}_rows{lo}_{hi}" + ("_smoke" if a.max_cells is not None else "")
    ok = common.complete(a.out, tag, [unit], a.data_root, {"scope": unit["scope"], "part": a.part})
    print("complete" if ok else "PARITY FAILED", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
