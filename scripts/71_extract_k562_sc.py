"""Stage 71: one sequential pass over the K562 genome-wide raw single-cell file.

No run has read this file's contents yet: the 2026-09-15 download recorded a
matching md5, and its QC step then failed on a code error (catalog_run.json of
that run). This stage opens it, refuses to continue unless X is a dense contiguous float32 matrix
(`vcc2026.sc_stream.dense_layout`), and then reads it front to back once:

* the md5 of the bytes actually read, compared with the catalog value;
* per-perturbation sums of counts, of per-cell fractions and of detections for
  EVERY perturbation -- the pseudobulk in both functionals the scorer uses;
* the cells of the 300-target panel (all of them), a seeded subsample of
  non-targeting cells, and all cells of a seeded sample of other targets, copied
  into sparse part files.

It never overwrites: `--out` must not already hold a `report.json`. Work is cut
into segments; each segment closes its own part file and checkpoints the
accumulator, so `--resume` restarts after the last finished segment (without
md5, which is then reported as not computed).

    python scripts/71_extract_k562_sc.py \
        --src "/content/drive/MyDrive/.../K562_gwps_raw_singlecell_01.h5ad" \
        --out /content/drive/MyDrive/vcc2026/data/processed/k562_gwps_sc/x001 \
        --work /content/work/x001
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import log  # noqa: E402
from vcc2026.sc_stream import (  # noqa: E402
    CsrAppendWriter,
    GroupAccumulator,
    dense_layout,
    read_frame,
    stream_dense_rows,
)

CATALOG_MD5 = "887e3e6a8c8df6eadf7a3030a53c9546"
CATALOG_BYTES = 65830941948
NTC = "non-targeting"


def target_symbols(obs: pd.DataFrame, group_col: str) -> np.ndarray:
    """Target gene symbol per cell: the `gene` column, else parsed from `gene_transcript`."""
    if "gene" in obs.columns:
        return obs["gene"].astype(str).to_numpy()
    labels = obs[group_col].astype(str).to_numpy()
    out = []
    for lab in labels:
        if NTC in lab:
            out.append(NTC)
            continue
        parts = lab.split("_")
        out.append(parts[1] if len(parts) >= 3 and parts[0].isdigit() else parts[0])
    return np.array(out, dtype=object)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--work", type=Path, default=None, help="local scratch; parts are copied to --out")
    p.add_argument("--panel", type=Path, default=None, help="CSV with a target_gene column")
    p.add_argument("--ntc-cells", type=int, default=20000)
    p.add_argument("--other-targets", type=int, default=400)
    p.add_argument("--min-cells-other", type=int, default=50)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--segment-rows", type=int, default=250_000)
    p.add_argument("--block-mib", type=int, default=256)
    p.add_argument("--no-md5", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--max-rows", type=int, default=None, help="smoke tests only")
    p.add_argument("--expect-md5", default=CATALOG_MD5)
    p.add_argument("--expect-bytes", type=int, default=CATALOG_BYTES)
    args = p.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    if (out / "report.json").exists():
        raise SystemExit(f"{out} already holds a finished report; choose a new --out")
    work = args.work or out
    work.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    size = args.src.stat().st_size
    log(f"src {args.src} bytes={size:,} expected={args.expect_bytes:,} match={size == args.expect_bytes}")
    layout = dense_layout(args.src)
    log(f"layout {layout.as_dict()}")

    with h5py.File(args.src, "r") as f:
        obs = read_frame(f["obs"])
        var = read_frame(f["var"])
    log(f"obs {obs.shape} columns={list(obs.columns)}")
    log(f"var {var.shape} columns={list(var.columns)}")
    if len(obs) != layout.n_obs or len(var) != layout.n_vars:
        raise SystemExit("obs/var lengths do not match X")

    if "gene_transcript" in obs.columns:
        group_col = "gene_transcript"
        group_labels = obs[group_col].astype(str).to_numpy()
    else:
        group_col = "group_label"
        group_labels = obs.index.astype(str).to_numpy()
        obs = obs.copy()
        obs[group_col] = group_labels
    symbols = target_symbols(obs, group_col)
    groups, codes = np.unique(group_labels, return_inverse=True)
    group_symbol = pd.Series(symbols).groupby(codes).first().to_numpy()
    n_groups = groups.size
    log(f"group column {group_col!r}: {n_groups:,} groups")

    panel_path = args.panel
    if panel_path is None:
        from vcc2026 import config
        panel_path = config.paths().raw / "controls" / "pert_counts.csv"
    panel = set(pd.read_csv(panel_path)["target_gene"].astype(str))

    rng = np.random.default_rng(args.seed)
    is_ntc_group = np.array([s == NTC or NTC in g for s, g in zip(group_symbol, groups)])
    in_panel_group = np.isin(group_symbol, list(panel))
    cells_per_group = np.bincount(codes, minlength=n_groups)
    eligible_other = np.flatnonzero(~is_ntc_group & ~in_panel_group & (cells_per_group >= args.min_cells_other))
    k_other = min(args.other_targets, eligible_other.size)
    other_pick = np.zeros(n_groups, dtype=bool)
    other_pick[rng.choice(eligible_other, size=k_other, replace=False)] = True

    select = in_panel_group[codes] | other_pick[codes]
    ntc_rows = np.flatnonzero(is_ntc_group[codes])
    k_ntc = min(args.ntc_cells, ntc_rows.size)
    select[rng.choice(ntc_rows, size=k_ntc, replace=False)] = True

    group_table = pd.DataFrame({
        "group": groups,
        "gene": group_symbol,
        "is_ntc": is_ntc_group,
        "in_panel": in_panel_group,
        "other_sample": other_pick,
        "n_cells_obs": cells_per_group,
        "n_selected": np.bincount(codes[select], minlength=n_groups),
    })
    group_table.to_csv(out / "groups.csv", index=False)
    var.to_csv(out / "var.csv")
    panel_found = sorted(set(group_symbol[in_panel_group]))
    log(f"panel targets found {len(panel_found)}/{len(panel)}; ntc cells {ntc_rows.size:,} (keep {k_ntc:,}); "
        f"other targets {k_other}; selected cells {int(select.sum()):,}")

    stop_all = layout.n_obs if args.max_rows is None else min(args.max_rows, layout.n_obs)
    acc = GroupAccumulator(n_groups, layout.n_vars)
    start_row = 0
    parts_done: list[dict] = []
    ckpt = work / "accumulator.npz"
    if args.resume and ckpt.exists():
        acc, start_row = GroupAccumulator.load(ckpt)
        state = json.loads((work / "parts.json").read_text())
        parts_done = state["parts"]
        log(f"resuming at row {start_row:,} with {len(parts_done)} finished parts")
    use_md5 = not args.no_md5 and start_row == 0 and args.max_rows is None
    stream_info: dict = {}

    var_frame = pd.DataFrame(index=var.index.astype(str))
    for col in var.columns:
        var_frame[col] = var[col].to_numpy()

    segment_edges = list(range(start_row, stop_all, args.segment_rows)) + [stop_all]
    # One stream for the whole remaining file keeps the md5 sequential; segments are
    # cut inside it.
    stream = stream_dense_rows(
        layout, block_bytes=args.block_mib * 1024**2, md5=use_md5,
        start_row=start_row, stop_row=None if use_md5 else stop_all,
        log=log, result=stream_info,
    )
    seg_i = 0
    seg_lo, seg_hi = segment_edges[0], segment_edges[1]
    part_idx = len(parts_done)

    def open_part(k: int):
        path = work / f"cells_part{k:03d}.h5ad"
        return path, CsrAppendWriter(path, var_frame)

    part_path, writer = open_part(part_idx)
    part_rows: list[np.ndarray] = []

    def close_part(lo: int, hi: int) -> None:
        nonlocal part_idx, part_path, writer, part_rows
        rows_sel = np.concatenate(part_rows) if part_rows else np.empty(0, dtype=np.int64)
        part_obs = obs.iloc[rows_sel].copy()
        # Barcodes can repeat across gem groups; the source row makes the index unique.
        part_obs.insert(0, "barcode", part_obs.index.astype(str))
        part_obs.index = pd.Index([f"r{r}" for r in rows_sel])
        for col in part_obs.columns:
            if part_obs[col].dtype == object:
                part_obs[col] = part_obs[col].astype(str)
        part_obs["source_row"] = rows_sel
        writer.close(part_obs)
        acc.save(work, rows_done=hi)
        dest = out / part_path.name
        if work.resolve() != out.resolve():
            shutil.copy2(part_path, dest)
            part_path.unlink()
        parts_done.append({"part": part_path.name, "rows": [lo, hi], "n_cells": int(rows_sel.size)})
        (work / "parts.json").write_text(json.dumps({"parts": parts_done}, indent=1))
        log(f"segment {lo:,}-{hi:,} closed: {rows_sel.size:,} cells -> {dest}")
        part_idx += 1
        part_rows = []

    for row0, rows in stream:
        row1 = row0 + rows.shape[0]
        if row0 >= stop_all:
            if not use_md5:
                break
            continue  # md5 pass reads on; nothing else to do past a smoke-test stop
        take_hi = min(row1, stop_all)
        pos = 0
        cur = row0
        while cur < take_hi:
            hi = min(take_hi, seg_hi)
            sub = rows[pos:pos + (hi - cur)]
            acc.add(codes[cur:hi], sub)
            sel = np.flatnonzero(select[cur:hi])
            if sel.size:
                writer.add(sub[sel])
                part_rows.append(sel.astype(np.int64) + cur)
            pos += hi - cur
            cur = hi
            if cur == seg_hi:
                close_part(seg_lo, seg_hi)
                seg_i += 1
                if seg_i + 1 < len(segment_edges):
                    seg_lo, seg_hi = segment_edges[seg_i], segment_edges[seg_i + 1]
                    part_path, writer = open_part(part_idx)
    if seg_i + 1 < len(segment_edges):  # stream ended early (should not happen)
        raise SystemExit(f"stream ended at segment {seg_i} before row {stop_all}")

    # float32 is exact for count sums below 2**24 per (group, gene), far above any group here.
    if acc.sums.max() >= 2**24:
        raise SystemExit("a group sum exceeds float32's exact-integer range")
    np.savez(out / "group_stats.npz", sums=acc.sums.astype(np.float32),
             frac_sums=acc.frac_sums.astype(np.float32),
             frac_sq_sums=acc.frac_sq_sums.astype(np.float32), detect=acc.detect,
             n_cells=acc.n_cells, lib_sum=acc.lib_sum, lib_sq_sum=acc.lib_sq_sum)
    obs_counts_match = bool(np.array_equal(acc.n_cells, np.bincount(codes[:stop_all], minlength=n_groups)))
    report = {
        "stage": "71_extract_k562_sc",
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "src": str(args.src),
        "bytes": size,
        "bytes_match_catalog": size == args.expect_bytes,
        "layout": layout.as_dict(),
        "stream": stream_info,
        "md5": stream_info.get("md5"),
        "md5_expected": args.expect_md5,
        "md5_match": (stream_info.get("md5") == args.expect_md5) if stream_info.get("md5") else None,
        "md5_note": None if stream_info.get("md5") else "not computed (resumed, --no-md5 or --max-rows)",
        "rows_processed": stop_all,
        "rows_total": layout.n_obs,
        "group_column": group_col,
        "n_groups": int(n_groups),
        "obs_columns": list(obs.columns),
        "var_columns": list(var.columns),
        "n_vars": layout.n_vars,
        "panel_file": str(panel_path),
        "panel_targets_found": len(panel_found),
        "panel_targets_missing": sorted(panel - set(panel_found)),
        "ntc_cells_total": int(ntc_rows.size),
        "ntc_cells_kept": int(k_ntc),
        "other_targets": int(k_other),
        "seed": args.seed,
        "selected_cells": int(select[:stop_all].sum()),
        "parts": parts_done,
        "cell_counts_match_obs": obs_counts_match,
        "seconds_total": time.time() - t_start,
        "outputs": ["groups.csv", "var.csv", "group_stats.npz"] + [d["part"] for d in parts_done],
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    log(f"done in {report['seconds_total']:.0f}s; md5_match={report['md5_match']}")


if __name__ == "__main__":
    main()
