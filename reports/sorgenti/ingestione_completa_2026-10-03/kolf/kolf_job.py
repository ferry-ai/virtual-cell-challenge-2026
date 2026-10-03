"""KOLF2.1J pan-genome cells (Figshare+ 27261219) into contract shards, one contiguous range of cells per runtime.

The source is one h5ad of 189.4 GB whose counts are a CSC layer (2,659,209 x 37,567, 7.87 billion values, measured in
corpus_cellulare_2026-09-30/p1_r5/remote_kolf/): the cells of a range can only be taken by scanning the whole layer.
Codex's adapter does it once per pass, into compact buckets (complete_adapters.py: a byte copy of
adattatori_codex/complete_adapters.py of 3/10, 16:14). `--part i/n` gives this runtime the i-th of n contiguous ranges,
cut at multiples of the block from cell 0: the n parts are disjoint, their union is the file, and their shards are the
ones a single job would write. Shards, receipts, the unit manifest and complete.json go through orion/common.py
(ShardSink), as for Orion.

A part is judged as a part: its cells are the declared range, contiguous, and the counts parsed in the scan equal the
counts in its shards. That the parts make the whole file is a later reconciliation, never a check of one part (the
whole-line flag of orion_job.py made every part end as a parity failure, 3/10).

    python kolf_job.py --spec specs/kolf_pan_v1.json --axis gene_names.csv --stage <local dir> --out <new dir> \
        --data-root <root of out> [--runtime-manifest <json>] [--part i/n] [--max-cells N] [--source <local h5ad>]
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "orion"))
import common  # noqa: E402
sys.path.insert(0, str(HERE))
import complete_adapters as ca  # noqa: E402


def part_range(n_cells: int, block: int, part: str | None) -> tuple[int, int]:
    """The i-th of n contiguous ranges of [0, n_cells), cut at multiples of `block`."""
    if part is None:
        return 0, n_cells
    i, n = (int(v) for v in part.split("/"))
    if not 0 <= i < n:
        raise ValueError(f"part {part}: need 0 <= i < n")
    blocks = -(-n_cells // block)
    lo, hi = (min(n_cells, blocks * j // n * block) for j in (i, i + 1))
    if lo >= hi:
        raise ValueError(f"part {part}: no cells (the file has {blocks} blocks)")
    return lo, hi


def precheck(url, unit: dict, axis: Path, n_cells: int, lo: int) -> dict:
    """Fail before the scan, not after it. The adapter reads the gene axis and the obs columns only when it yields
    its first block, an hour or more into the scan: a wrong column name or axis would cost the whole pass."""
    kw = unit["kwargs"]
    with ca.base._h5_open(url) as f:
        layer = kw.get("layer", "X")
        node = f[layer] if layer in f else f["layers"][layer]
        enc = node.attrs.get("encoding-type", "")
        enc = enc.decode() if isinstance(enc, bytes) else str(enc)
        shape = [int(v) for v in node.attrs["shape"]]
        if enc != "csc_matrix" or shape[0] != n_cells:
            sys.exit(f"precheck: {layer} is {enc} of shape {shape}, the spec says CSC with {n_cells} cells")
        var = ca.axis_frame(f["var"], str(axis), kw.get("var_symbol_col"), kw.get("feature_id_col"))
        mapped = int((var["official_index"].to_numpy() >= 0).sum())
        if len(var) != shape[1] or mapped < min(1000, len(var) // 2):      # the guard of rlab_job.run_unit
            sys.exit(f"precheck: {len(var)} genes for {shape[1]} columns, {mapped} on the official axis")
        og, stop = f["obs"], min(n_cells, lo + 1000)
        names = {k: kw.get(k) for k in ("target_col", "guides_col", "library_col", "target_id_col", "published_depth",
                                        "context_col", "donor_col")}
        names["index"] = ca.index_name(og)
        absent = sorted(v for v in names.values() if v is not None and v not in og)
        if absent:
            sys.exit(f"precheck: obs lacks {absent}")
        target = ca.column(og, names["target_col"], lo, stop, required=True)
        controls = int(sum(t in kw.get("control_values", ()) for t in target))
        ca.column(og, names["index"], lo, stop, required=True)
    seen = {"layer": layer, "shape": shape, "genes_on_official_axis": mapped, "rows_read": [lo, stop],
            "controls_in_rows_read": controls, "targets_in_rows_read": len(set(target))}
    print(f"precheck: {seen}", flush=True)
    return seen


def count_http():
    """Count the bytes, the requests and the ETags of every HTTP range the adapters read (the scan of a CSC layer
    prints nothing for an hour or more: without this a slow host and a dead job look the same)."""
    _, _, _, inspect_remote = common.corpus()
    state, lock, fetch = {"bytes": 0, "requests": 0, "etags": set()}, threading.Lock(), inspect_remote.RangeFile._fetch

    def counted(self, url, lo, hi):
        body, etag = fetch(self, url, lo, hi)
        with lock:
            state["bytes"] += len(body)
            state["requests"] += 1
            if etag:
                state["etags"].add(etag)
        return body, etag

    inspect_remote.RangeFile._fetch = counted
    return state


def heartbeat(state: dict, every: float) -> None:
    t0, last = time.time(), 0
    while True:
        time.sleep(every)
        now = state["bytes"]
        print(f"http: {now / 1e9:.2f} GB in {state['requests']} ranges, {(now - last) / 1e6 / every:.1f} MB/s now, "
              f"{time.time() - t0:.0f}s", flush=True)
        last = now


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--axis", type=Path, required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--data-root", type=Path)
    p.add_argument("--runtime-manifest", type=Path)
    p.add_argument("--part", help="i/n: the i-th of n contiguous ranges of cells")
    p.add_argument("--max-cells", type=int, help="smoke test: only the first N cells of the range")
    p.add_argument("--source", help="read this file instead of the locator of the spec (fixtures)")
    p.add_argument("--heartbeat-seconds", type=float, default=120.0)
    a = p.parse_args()
    spec = common.load_json(a.spec)
    src, u = spec["source"], spec["unit"]
    url = a.source or src["locator"]
    remote = str(url).startswith(("http://", "https://"))
    http = count_http()
    etag = common.MISSING
    if remote:
        head = common.head(url)
        if head["bytes"] != src["bytes"]:
            sys.exit(f"{src['id']}: {head['bytes']} bytes on the host, {src['bytes']} in the spec")
        etag = head["etag"]
        threading.Thread(target=heartbeat, args=(http, a.heartbeat_seconds), daemon=True).start()
    lo, hi = part_range(src["cells"], u["block"], a.part)
    if a.max_cells is not None:
        hi = min(hi, lo + a.max_cells)
    checked = precheck(url, u, a.axis, src["cells"], lo)
    common.new_dir(a.out)
    common.new_dir(a.stage)
    source = common.source_record(src["id"], src["release"], src["license"],
                                  [{"locator": str(url), "bytes": src["bytes"], "md5": src.get("md5"), "etag": etag}])
    bind = {"spec_sha256": common.sha256_file(a.spec), "cell_range": f"{lo}:{hi}",
            "complete_adapters_sha256": common.sha256_file(HERE / "complete_adapters.py")}
    sink = common.ShardSink(a.out, a.stage, u["name"], source, common.writer_record(Path(__file__), a.runtime_manifest),
                            require=bind)
    seen = []
    for name, x, obs, var, uns in ca.h5csc_shards(url, u["study"], u["context"], u["chemistry"], u["modality"],
                                                  str(a.axis), a.stage / "buckets", block=u["block"],
                                                  cell_range=(lo, hi), **u["kwargs"]):
        if uns["rows"]["of"] != src["cells"]:
            sys.exit(f"{src['id']}: {uns['rows']['of']} cells in the file, {src['cells']} in the spec")
        seen.append(uns)
        sink.put(name, x, obs, var, uns)
    passes = {}
    for s, uns in zip(sink.shards, seen):
        e = passes.setdefault(uns["read"]["pass_range"], {"parsed": uns["read"]["pass_sum_before"], "in_shards": 0,
                                                          "parsed_nnz": uns["read"]["pass_selected_nnz"],
                                                          "nnz_in_shards": 0})
        e["in_shards"] += s["sum_after"]
        e["nnz_in_shards"] += s["nnz"]
    ranges = sorted(tuple(int(v) for v in uns["rows"]["range"].split(":")) for uns in seen)
    unit = sink.finish(
        {"parsed_sum_equals_shards": bool(passes) and all(e["parsed"] == e["in_shards"] for e in passes.values()),
         "covers_declared_rows": bool(ranges) and ranges[0][0] == lo and ranges[-1][1] == hi
         and all(x[1] == y[0] for x, y in zip(ranges, ranges[1:])),
         "cells_equal_declared": sum(s["cells"] for s in sink.shards) == hi - lo,
         "one_version_of_the_file": len(http["etags"] | ({etag} if remote and etag != common.MISSING else set())) <= 1},
        {"scope": f"cells {lo}:{hi} of {src['cells']}", "part": a.part, "smoke_max_cells": a.max_cells,
         "precheck": checked, "passes": passes, "http": {"bytes": http["bytes"], "requests": http["requests"], "etags": sorted(http["etags"])},
         **bind})
    tag = f"{spec['job_id']}_cells{lo}_{hi}" + ("_smoke" if a.max_cells is not None else "")
    ok = common.complete(a.out, tag, [unit], a.data_root, {"scope": unit["scope"], "part": a.part})
    print("complete" if ok else "PARITY FAILED", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
