"""F1 of R-V2: the CD4 genome-wide source (GSE314342 pseudobulk) for EVERY target, not only the panel.

Reads the local copy of GWCD4i.pseudobulk_merged.h5ad (44.6 GB under external/cd4_gw/, URL, bytes and
sha256 in the manifest beside it) in chunks of targets, along stage 97's and stage 98's own path:
* rows as stage 97 selects them for the panel: every targeting row of a target, all guides, author
  flags NOT applied (filtering on observed guide efficacy selects on the outcome), and the same 2,400
  non-targeting rows (200 per donor x condition, seed 2026, in stage 97's order); every row checked
  against its own total_counts;
* effects as stage 98: `effects_from_pseudobulk` per culture condition (controls of the same donor),
  `AxisTable.from_source` on the official axis, and cd4_mix = the reliability-weighted mean of the
  three conditions (gamma 0; shrunk and raw mixed separately; SE left NaN as in the cache).
Writes, per chunk, cd4_Rest_<c>.npz, cd4_Stim8hr_<c>.npz, cd4_Stim48hr_<c>.npz and cd4_mix_<c>.npz in
stage-98 format, index.csv and manifest.json; with --panel-first the first chunk holds the panel targets
and parity with the stage-98 cache is checked on them.

    scripts/py.cmd reports/universo_2026-09-26/cd4_universe.py \
        --out C:/Users/ferra/vcc2026-data/processed/universe_cd4_2026-09-26 --report reports/universo_2026-09-26/r2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.multisource import AxisTable, effects_from_pseudobulk, mix  # noqa: E402

DATA = config.paths().data_root
CONDS = ("Rest", "Stim8hr", "Stim48hr")


def categorical(obs, key):
    node = obs[key]
    cats = node["categories"].asstr()[:]
    codes = node["codes"][:]
    return np.where(codes >= 0, cats[np.clip(codes, 0, None)], "")


def read_rows(f, indptr, rows, n_genes, totals):
    data, idx, ptr = [], [], [0]
    dset, iset = f["X/data"], f["X/indices"]
    for r in rows:
        a, b = int(indptr[r]), int(indptr[r + 1])
        data.append(dset[a:b].astype(np.float32))     # counts < 2**24: exact in float32
        idx.append(iset[a:b].astype(np.int32))
        ptr.append(ptr[-1] + (b - a))
    data = np.concatenate(data) if data else np.zeros(0, dtype=np.float32)
    idx = np.concatenate(idx) if idx else np.zeros(0, dtype=np.int32)
    if (data < 0).any() or (data != np.rint(data)).any():
        raise ValueError("non-count values in rows")
    sums = np.bincount(np.repeat(np.arange(len(rows)), np.diff(ptr)), weights=data, minlength=len(rows))
    if not np.allclose(sums, totals, rtol=0, atol=0.5):
        raise ValueError("rows do not sum to their total_counts")
    X = sp.csr_matrix((data, idx, np.asarray(ptr, dtype=np.int64)),
                      shape=(len(rows), n_genes))
    X.sum_duplicates()
    return X


def tables_for(X, obs, var_names, targets, axis):
    tabs = {}
    for cond in CONDS:
        src = effects_from_pseudobulk(X, obs, var_names, targets=targets, condition=cond)
        tabs[f"cd4_{cond}"] = AxisTable.from_source(f"cd4_{cond}", src, axis)
    conds = [f"cd4_{c}" for c in CONDS]
    eff, w = mix([tabs[n] for n in conds], targets, gamma=0.0)
    have = (w > 0).any(axis=1)
    cells = np.array([sum(tabs[n].n_cells[tabs[n].index()[t]] for n in conds if t in tabs[n].index()) for t in targets])
    mixed = np.where(w > 0, eff, np.nan).astype(np.float32)[have]
    raw_tabs = [AxisTable(n, tabs[n].targets, tabs[n].raw, tabs[n].raw, tabs[n].se, tabs[n].n_cells) for n in conds]
    eff_raw, w_raw = mix(raw_tabs, targets, gamma=0.0)
    mixed_raw = np.where(w_raw > 0, eff_raw, np.nan).astype(np.float32)[have]
    tabs["cd4_mix"] = AxisTable("cd4_mix", [t for t, h in zip(targets, have) if h], mixed, mixed_raw,
                                np.full_like(mixed, np.nan), cells[have],
                                {"from": conds, "how": "reliability-weighted mean of the conditions, gamma 0; "
                                                       "shrunk and raw mixed separately"})
    return tabs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--h5ad", type=Path, default=DATA / "external/cd4_gw/GWCD4i.pseudobulk_merged.h5ad")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--chunk", type=int, default=150)
    ap.add_argument("--max-chunks", type=int, default=0, help="pilot: stop after N chunks")
    ap.add_argument("--panel-first", action="store_true", help="first chunk = the panel targets, with a parity check")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    args.report.mkdir(parents=True, exist_ok=False)
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:7.0f}s] {m}", flush=True)  # noqa: E731
    axis = np.asarray(official_axis().symbols)
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    f = h5py.File(args.h5ad, "r")
    obs = f["obs"]
    target = categorical(obs, "perturbed_gene_name")
    gtype = categorical(obs, "guide_type")
    donor = categorical(obs, "donor_id")
    cond = categorical(obs, "culture_condition")
    n_cells = obs["n_cells"][:]
    totals = obs["total_counts"][:]
    indptr = f["X/indptr"][:]
    genes = f["var/gene_name"].asstr()[:]
    import anndata as ad
    var_names = ad.utils.make_index_unique(pd.Index(genes))
    rng = np.random.default_rng(2026)
    ntc_rows = []
    frame = pd.DataFrame({"row": np.flatnonzero(gtype == "non-targeting"), "d": donor[gtype == "non-targeting"],
                          "c": cond[gtype == "non-targeting"]})
    for (_, _), grp in frame.groupby(["d", "c"]):
        rows = grp.row.to_numpy()
        ntc_rows.extend(rng.choice(rows, size=min(200, len(rows)), replace=False).tolist())
    ntc_rows = np.sort(np.array(ntc_rows, dtype=np.int64))
    X_ntc = read_rows(f, indptr, ntc_rows, len(genes), totals[ntc_rows])
    log(f"{len(target):,} rows, {len(genes):,} genes; {len(ntc_rows)} non-targeting rows read")
    targeting = gtype == "targeting"
    rows_of = pd.Series(np.flatnonzero(targeting)).groupby(target[targeting]).apply(lambda s: s.to_numpy())
    all_targets = sorted(rows_of.index)
    order = ([t for t in panel if t in rows_of.index] + [t for t in all_targets if t not in set(panel)]
             if args.panel_first else all_targets)
    chunks = [order[i:i + args.chunk] for i in range(0, len(order), args.chunk)]
    if args.panel_first:
        n_panel = sum(t in rows_of.index for t in panel)
        rest = [t for t in order[n_panel:]]
        chunks = [order[:n_panel]] + [rest[i:i + args.chunk] for i in range(0, len(rest), args.chunk)]
    index, files, parity = [], [], None
    for c, part in enumerate(chunks):
        if args.max_chunks and c >= args.max_chunks:
            break
        rows = np.concatenate([rows_of[t] for t in part])
        Xt = read_rows(f, indptr, rows, len(genes), totals[rows])
        X = sp.vstack([Xt, X_ntc], format="csr")
        all_rows = np.concatenate([rows, ntc_rows])
        ob = pd.DataFrame({"target": np.where(gtype[all_rows] == "non-targeting", "non-targeting", target[all_rows]),
                           "donor": donor[all_rows], "condition": cond[all_rows], "n_cells": n_cells[all_rows]},
                          index=[f"cd4pb:{r}" for r in all_rows])
        tabs = tables_for(X, ob, var_names, part, axis)
        for name, tab in tabs.items():
            path = args.out / f"{name}_{c:03d}.npz"
            np.savez_compressed(path, targets=np.array(tab.targets), shrunk=tab.shrunk, raw=tab.raw, se=tab.se,
                                n_cells=tab.n_cells, meta=json.dumps(tab.meta, default=str))
            files.append({"file": path.name, "targets": len(tab.targets), "bytes": path.stat().st_size,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        mixtab = tabs["cd4_mix"]
        index += [{"target": t, "chunk": c, "n_cells": float(n), "in_panel": t in set(panel), "on_official_axis": t in set(axis)}
                  for t, n in zip(mixtab.targets, mixtab.n_cells)]
        if args.panel_first and c == 0:
            parity = {}
            for name, tab in tabs.items():
                ref = np.load(args.cache / f"{name}.npz", allow_pickle=False)
                rix = {t: i for i, t in enumerate(ref["targets"].astype(str))}
                common = [t for t in tab.targets if t in rix]
                a = np.array([tab.index()[t] for t in common])
                b = np.array([rix[t] for t in common])
                entry = {"targets_compared": len(common)}
                for key in ("raw", "shrunk", "se"):
                    x, y = getattr(tab, key)[a], ref[key][b]
                    both = np.isfinite(x) & np.isfinite(y)
                    entry[f"{key}_max_abs_diff"] = float(np.abs(x[both] - y[both]).max()) if both.any() else None
                    entry[f"{key}_nan_pattern_equal"] = bool(np.array_equal(np.isfinite(x), np.isfinite(y)))
                parity[name] = entry
            log(f"parity on the panel: {json.dumps(parity)}")
        log(f"chunk {c}: {len(part)} targets, {len(rows)} rows")
        del X, Xt, tabs
    f.close()
    pd.DataFrame(index).to_csv(args.out / "index.csv", index=False)
    manifest = {"script": "reports/universo_2026-09-26/cd4_universe.py", "written_utc": datetime.now(timezone.utc).isoformat(),
                "source": str(args.h5ad), "source_manifest": json.loads(Path(str(args.h5ad) + ".manifest.json").read_text()),
                "targets": len(index), "in_panel": int(sum(r["in_panel"] for r in index)),
                "median_cells": float(np.median([r["n_cells"] for r in index])) if index else None,
                "ntc_rows": int(len(ntc_rows)), "chunks_written": len({r["chunk"] for r in index}),
                "parity_with_panel_cache": parity, "files": files, "seconds": round(time.time() - t0, 1)}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (args.report / "manifest.json").write_text(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=1),
                                               encoding="utf-8")
    pd.DataFrame(index).to_csv(args.report / "index.csv", index=False)
    log(f"wrote {args.out}: {len(index)} targets")


if __name__ == "__main__":
    main()
