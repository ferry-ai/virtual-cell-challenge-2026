"""Nested training samples of the cell corpus and what they lose (R-DATI; D-053; PROTOCOLLO §10 of this folder).

For every (key, target) group of admitted single-target perturbed cells of a prepass state:
- strata: (library, guide), from the shards' obs ('library', 'guides': the vector's guide string);
- order: within each stratum the cells sorted by sha256(seed|cell_key), stable when shards are re-cut; the strata
  interleaved round-robin by rank (strata ordered by hash), so the first k cells cover as many strata as possible;
- levels: the first min(n, c) cells of that order for every c in --caps (32, 64, 128 by default): nested by
  construction (32 in 64 in 128); a group with n <= c keeps all its cells at that level (rare units whole);
- inclusion probability of a cell at level c: cells of its stratum kept at c over cells of its stratum.
Controls are not sampled here: they enter a training through its own reservoir, reported apart.

What a level loses, per group, from the counts of the compact twins (fastshard.py), on the key's measured genes:
- the sample's mean proportion profile against the full group's, as shifts against the key's admitted controls (log of
  mean proportions; genes where the full group's and the controls' means are both above --min-prop): Pearson r, sign
  agreement and overlap on the full group's 200 largest shifts, RMSE;
- the same between two halves of the full group (cells split by the parity of their hash): the noise floor;
- coverage: strata, libraries and guides present at each level over the group's.
Outputs (a new --out): summary.json (per unit and level, totals, rule), groups.csv.gz (one row per group),
selection/<shard>.npz (per row: the smallest level holding it, 0 = not a sampled perturbed cell; and its inclusion
probability at each level), manifest.json (inputs with sha256, parameters).

    python nested_samples.py --prepass <dir with prepass.pkl> --shard-roots <dirs with the h5ad> \
        --fast-roots <dirs with the twins and fast_manifest.json> --out <new dir> [--caps 32 64 128] [--workers 4]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cellnet as CN  # noqa: E402
import fastshard as FS  # noqa: E402

TOP = 200


def h64(texts, seed: int) -> np.ndarray:
    """First 8 bytes of sha256(seed|text) as uint64, per text."""
    return np.array([int.from_bytes(hashlib.sha256(f"{seed}|{t}".encode()).digest()[:8], "little") for t in texts],
                    dtype=np.uint64)


def order_group(strata: np.ndarray, cell_h: np.ndarray, stratum_h: dict) -> np.ndarray:
    """Positions of a group's cells in sampling order: within a stratum by cell hash, strata dealt round-robin by rank,
    strata ordered by their own hash. Returns rank[i] = position of cell i in the order."""
    n = strata.size
    within = np.empty(n, np.int64)
    sh = np.array([stratum_h[s] for s in strata], np.uint64)
    for s in np.unique(strata):
        idx = np.flatnonzero(strata == s)
        within[idx[np.argsort(cell_h[idx], kind="stable")]] = np.arange(idx.size)
    order = np.lexsort((sh, within))                 # by rank within stratum, then by stratum hash
    rank = np.empty(n, np.int64)
    rank[order] = np.arange(n)
    return rank


def plan(st, obs_of, caps, seed):
    """Levels and inclusion probabilities of every sampled cell, from the state and the shards' obs.
    obs_of(sid) -> (cell_keys, libraries, guides). Returns per shard {level, prob} arrays and the groups' table."""
    rows_of_group = defaultdict(list)
    meta = {}
    for sid, s in enumerate(st["shards"]):
        adm = np.asarray(s["admitted"], bool) & ~np.asarray(s["control"], bool) & (np.asarray(s["tgt"]) >= 0)
        r = np.flatnonzero(adm)
        if not r.size:
            continue
        keys, libs, guides = obs_of(sid)
        meta[sid] = (keys, libs, guides)
        for row in r:
            rows_of_group[(int(s["key"][row]), int(s["tgt"][row]))].append((sid, int(row)))
    caps = sorted(caps)
    level = {sid: np.zeros(len(s["admitted"]), np.uint8) for sid, s in enumerate(st["shards"])}
    prob = {sid: np.zeros((len(s["admitted"]), len(caps)), np.float32) for sid, s in enumerate(st["shards"])}
    half = {sid: np.zeros(len(s["admitted"]), np.uint8) for sid, s in enumerate(st["shards"])}
    groups = []
    for (k, t), items in sorted(rows_of_group.items()):
        sids = np.array([a for a, _ in items])
        rows = np.array([b for _, b in items])
        ck = [meta[a][0][b] for a, b in items]
        strata = np.array([f"{meta[a][1][b]}|{meta[a][2][b]}" for a, b in items], dtype=object)
        cell_h = h64(ck, seed)
        uniq = list(dict.fromkeys(strata.tolist()))
        stratum_h = dict(zip(uniq, h64([f"{k}|{t}|{u}" for u in uniq], seed + 1)))
        rank = order_group(strata, cell_h, stratum_h)
        n = rank.size
        for i, (a, b) in enumerate(zip(sids, rows)):
            lv = next((j + 1 for j, c in enumerate(caps) if rank[i] < c), len(caps) + 1)
            level[a][b] = lv
            half[a][b] = 1 + int(cell_h[i] & np.uint64(1))
        for s in uniq:
            idx = np.flatnonzero(strata == s)
            for j, c in enumerate(caps):
                kept = int((rank[idx] < c).sum())
                for a, b in zip(sids[idx], rows[idx]):
                    prob[a][b, j] = kept / idx.size
        libs = {str(meta[a][1][b]) for a, b in items}
        guides = {str(meta[a][2][b]) for a, b in items}
        cov = {}
        for j, c in enumerate(caps):
            sel = rank < c
            cov[c] = {"strata": len(set(strata[sel].tolist())), "libraries": len({str(meta[a][1][b]) for (a, b), m
                                                                               in zip(items, sel) if m}),
                      "guides": len({str(meta[a][2][b]) for (a, b), m in zip(items, sel) if m})}
        groups.append({"key": k, "tgt": t, "n": n, "strata": len(uniq), "libraries": len(libs), "guides": len(guides),
                       "coverage": cov})
    return level, prob, half, groups


def key_task(task):
    """Sums of mean proportions per group and accumulator (full, each level, two halves) and the key's control mean,
    for one key, from the twins of its shards."""
    st_small, k, shard_paths, caps, levels, halves = (task[n] for n in ("st", "key", "paths", "caps", "level", "half"))
    G = st_small["G"]
    mask = st_small["key_mask"]
    acc, nacc = {}, defaultdict(int)
    cols = np.flatnonzero(mask)
    csum, cn = np.zeros(cols.size), 0
    n_acc = len(caps) + 3                              # full, levels..., half A, half B
    for sid, path in shard_paths.items():
        s = st_small["shards"][sid]
        x, _ = CN.read_csr(path, s["official_index"], s["measured"], st_small["gene_of_axis"], G)
        keyrows = np.flatnonzero(np.asarray(s["key"]) == k)
        if not keyrows.size:
            continue
        xk = x[keyrows][:, cols]
        L = np.asarray(xk.sum(1)).ravel()
        ok = L > 0
        prop = xk.multiply(1.0 / np.maximum(L, 1)[:, None]).tocsr()
        adm = np.asarray(s["admitted"], bool)[keyrows] & ok
        ctrl = adm & np.asarray(s["control"], bool)[keyrows]
        if ctrl.any():
            csum += np.asarray(prop[ctrl].sum(0)).ravel()
            cn += int(ctrl.sum())
        lv = levels[sid][keyrows]
        hv = halves[sid][keyrows]
        tg = np.asarray(s["tgt"])[keyrows]
        pert = adm & (lv > 0)
        for t in np.unique(tg[pert]):
            sel_t = pert & (tg == t)
            parts = [sel_t] + [sel_t & (lv <= j + 1) for j in range(len(caps))] + [sel_t & (hv == 1), sel_t & (hv == 2)]
            vec = np.zeros((n_acc, cols.size), np.float32)
            for i, m in enumerate(parts):
                if m.any():
                    vec[i] = np.asarray(prop[m].sum(0)).ravel()
                    nacc[(int(t), i)] += int(m.sum())
            if int(t) in acc:
                acc[int(t)] += vec
            else:
                acc[int(t)] = vec
    return {"key": k, "acc": acc, "n": dict(nacc), "ctrl_sum": csum, "ctrl_n": cn, "genes": int(cols.size)}


def metrics(s_full, s_x):
    ok = np.isfinite(s_full) & np.isfinite(s_x)
    if ok.sum() < 3:
        return {"r": None, "sign_top": None, "overlap_top": None, "rmse": None}
    a, b = s_full[ok], s_x[ok]
    top = np.argsort(-np.abs(a))[:TOP]
    topx = set(np.argsort(-np.abs(b))[:TOP].tolist())
    r = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else None
    return {"r": r, "sign_top": float(np.mean(np.sign(a[top]) == np.sign(b[top]))),
            "overlap_top": len(set(top.tolist()) & topx) / max(1, min(TOP, a.size)),
            "rmse": float(np.sqrt(np.mean((a - b) ** 2)))}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prepass", type=Path, required=True)
    p.add_argument("--shard-roots", nargs="+", required=True)
    p.add_argument("--fast-roots", nargs="+", required=True)
    p.add_argument("--caps", nargs="+", type=int, default=[32, 64, 128])
    p.add_argument("--min-prop", type=float, default=1e-5)
    p.add_argument("--seed", type=int, default=20261003)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    t0 = time.time()
    import train_cellnet as TC
    with open(a.prepass / "prepass.pkl", "rb") as fh:
        st = pickle.load(fh)
    h5 = TC.resolve_shards(st["shards"], a.shard_roots)
    twins = TC.resolve_twins(st["shards"], a.fast_roots)
    import h5py

    def obs_of(sid):
        with h5py.File(h5[sid], "r") as f:
            o = f["obs"]
            return (CN.h5_column(o, "cell_key").astype(str), CN.h5_column(o, "library").astype(str),
                    CN.h5_column(o, "guides").astype(str) if "guides" in o else np.full(len(st["shards"][sid]["key"]),
                                                                                       "MISSING", dtype=object))
    level, prob, half, groups = plan(st, obs_of, a.caps, a.seed)
    print(json.dumps({"msg": "planned", "groups": len(groups), "seconds": round(time.time() - t0, 1)}), flush=True)
    keys = sorted({g["key"] for g in groups})
    shards_of_key = defaultdict(dict)
    for sid, s in enumerate(st["shards"]):
        for k in np.unique(np.asarray(s["key"])):
            if int(k) in keys:
                shards_of_key[int(k)][sid] = twins[sid][0]
    tasks = []
    for k in keys:
        sids = list(shards_of_key[k])
        small = {"G": st["G"], "gene_of_axis": st["gene_of_axis"], "key_mask": np.asarray(st["key_mask"][k], bool),
                 "shards": {sid: {f: st["shards"][sid][f] for f in ("official_index", "measured", "key", "admitted",
                                                                   "control", "tgt")} for sid in sids}}
        tasks.append({"st": small, "key": k, "paths": shards_of_key[k], "caps": a.caps,
                      "level": {sid: level[sid] for sid in sids}, "half": {sid: half[sid] for sid in sids}})
    rows = []
    ex = ProcessPoolExecutor(max_workers=a.workers) if a.workers > 1 else None
    results = ex.map(key_task, tasks) if ex else map(key_task, tasks)
    gmeta = {(g["key"], g["tgt"]): g for g in groups}
    for res in results:
        k = res["key"]
        if res["ctrl_n"] == 0:
            continue
        mc = res["ctrl_sum"] / res["ctrl_n"]
        for t, vec in res["acc"].items():
            n = [res["n"].get((t, i), 0) for i in range(len(a.caps) + 3)]
            if n[0] == 0:
                continue
            means = [vec[i] / n[i] if n[i] else np.full(vec.shape[1], np.nan) for i in range(vec.shape[0])]
            ok = (means[0] > a.min_prop) & (mc > a.min_prop)
            shift = [np.where(ok, np.log(np.maximum(m, 1e-12)) - np.log(np.maximum(mc, 1e-12)), np.nan) for m in means]
            g = gmeta[(k, t)]
            row = {"key": st["key_names"][k], "unit": st["unit_of_key"].get(st["key_names"][k]), "target":
                   st["symbols"][t], "cells": n[0], "strata": g["strata"], "libraries": g["libraries"],
                   "guides": g["guides"], "genes_compared": int(ok.sum())}
            for j, c in enumerate(a.caps):
                m = metrics(shift[0], shift[1 + j])
                row.update({f"cells_{c}": n[1 + j], f"r_{c}": m["r"], f"sign_top_{c}": m["sign_top"],
                            f"overlap_top_{c}": m["overlap_top"], f"rmse_{c}": m["rmse"],
                            f"strata_{c}": g["coverage"][c]["strata"], f"guides_{c}": g["coverage"][c]["guides"]})
            hm = metrics(shift[-2], shift[-1])
            row.update({"r_halves": hm["r"], "sign_top_halves": hm["sign_top"]})
            rows.append(row)
    if ex:
        ex.shutdown()
    import pandas as pd
    df = pd.DataFrame(rows)
    a.out.mkdir(parents=True)
    (a.out / "selection").mkdir()
    df.to_csv(a.out / "groups.csv.gz", index=False, compression="gzip")
    for sid, s in enumerate(st["shards"]):
        np.savez_compressed(a.out / "selection" / f"{s['name']}.npz", level=level[sid], prob=prob[sid].astype(np.float16),
                            caps=np.array(a.caps))
    summary = {"rule": __doc__.split("\n\n")[1].replace("\n", " "), "caps": a.caps, "seed": a.seed,
               "groups": int(len(df)), "cells_full": int(df["cells"].sum()) if len(df) else 0}
    by_unit = {}
    for u, sub in df.groupby("unit"):
        e = {"groups": int(len(sub)), "cells": int(sub["cells"].sum()),
             "r_halves_median": float(sub["r_halves"].median()) if sub["r_halves"].notna().any() else None}
        for c in a.caps:
            e[str(c)] = {"cells": int(sub[f"cells_{c}"].sum()), "share_of_cells": float(sub[f"cells_{c}"].sum() /
                                                                                       max(1, sub["cells"].sum())),
                         "groups_whole": int((sub["cells"] <= c).sum()),
                         "r_median": float(sub[f"r_{c}"].median()) if sub[f"r_{c}"].notna().any() else None,
                         "r_p10": float(sub[f"r_{c}"].quantile(0.1)) if sub[f"r_{c}"].notna().any() else None,
                         "sign_top_median": float(sub[f"sign_top_{c}"].median())
                         if sub[f"sign_top_{c}"].notna().any() else None,
                         "guides_kept_share": float(sub[f"guides_{c}"].sum() / max(1, sub["guides"].sum()))}
        by_unit[str(u)] = e
    summary["by_unit"] = by_unit
    summary["totals"] = {str(c): int(df[f"cells_{c}"].sum()) for c in a.caps} if len(df) else {}
    summary["seconds"] = round(time.time() - t0, 1)
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    manifest = {"prepass_sha256": TC.sha(a.prepass / "prepass.pkl"), "caps": a.caps, "seed": a.seed,
                "min_prop": a.min_prop, "twins": "checked by train_cellnet.resolve_twins against fast_manifest.json",
                "outputs": {"groups.csv.gz": TC.sha(a.out / "groups.csv.gz"), "summary.json": TC.sha(a.out / "summary.json")}}
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps({"msg": "done", "groups": len(df), "totals": summary["totals"], "seconds": summary["seconds"]}),
          flush=True)


if __name__ == "__main__":
    main()
