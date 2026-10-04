"""Sampled contract shards of the expanded corpus (DECISIONE.md of this folder): nested levels chosen from metadata only.

For every (study, context, target) group of labelled perturbed cells of the given shards (control_kind 'none', target
not NTC / UNASSIGNED / MISSING / DRUG:*):
- strata: (library, guides) from the obs; a missing guides column counts as one stratum per library;
- order: within each stratum the cells sorted by sha256(seed|cell_key); the strata interleaved round-robin by rank, the
  strata ordered by sha256(seed|stratum); so the first k cells cover as many strata as possible. It is the order of
  reports/modelli/rete_ancorata_v4_2026-10-03/nested_samples.py, applied to the obs before any prepass;
- levels: a cell belongs to the smallest level c of --levels with its rank < c (nested: 32 in 64 in 128); a group with
  at most c cells keeps them all at level c.
Kept in the sampled shards: the perturbed cells of level <= --level, and every control cell (control_kind NTC).
Dropped, and counted: unassigned or unlabelled cells, and perturbed cells above the level.
Nothing reads a count before the selection is fixed: no response, fold or held-out line can move it.

Each source shard gives one sampled shard (<name>__L<level>.h5ad) with the source's obs columns, var and uns, the
selected rows only (counts bit for bit), and uns.rows / uns.parity / uns.writer describing the selection.
manifest.json: rule, parameters, per shard (source name, bytes, sha256, rows kept by kind, nnz and counts of the kept
rows before and after writing, output sha256 and bytes), per group (cells, kept at each level), totals.

    python build_sampled_shards.py --shard-roots <dirs> [--pattern "*.h5ad"] --out <new dir> [--level 64]
        [--levels 32 64 128] [--seed 2026] [--workers 2]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

NOT_TARGETS = ("NTC", "UNASSIGNED", "MISSING", "", "none", "nan")
OBS_NEEDED = ("cell_key", "study", "context", "target", "control_kind", "library")


def h64(texts, seed: int) -> np.ndarray:
    return np.array([int.from_bytes(hashlib.sha256(f"{seed}|{t}".encode()).digest()[:8], "little") for t in texts],
                    dtype=np.uint64)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(16 << 20), b""):
            h.update(block)
    return h.hexdigest()


def text_column(group, name):
    import h5py
    if name not in group:
        return None
    node = group[name]
    if isinstance(node, h5py.Group) and "categories" in node:          # as cellnet.h5_column reads it
        cats = np.asarray([c.decode() if isinstance(c, bytes) else str(c) for c in node["categories"][:]], dtype=object)
        codes = node["codes"][:].astype(np.int64)
        return np.where(codes >= 0, cats[np.clip(codes, 0, None)], "MISSING").astype(object)
    if isinstance(node, h5py.Group) and "values" in node:              # nullable string array
        node = node["values"]
    vals = node[:]
    return np.asarray([v.decode() if isinstance(v, bytes) else str(v) for v in vals], dtype=object)


def read_obs(path: Path) -> dict:
    import h5py
    with h5py.File(path, "r") as f:
        obs = f["obs"]
        out = {c: text_column(obs, c) for c in (*OBS_NEEDED, "guides")}
    missing = [c for c in OBS_NEEDED if out[c] is None]
    if missing:
        raise ValueError(f"{path.name}: obs lacks {missing}")
    if out["guides"] is None:
        out["guides"] = np.full(len(out["cell_key"]), "MISSING", dtype=object)
    return out


def is_perturbed(obs) -> np.ndarray:
    t = obs["target"].astype(str)
    return (obs["control_kind"].astype(str) == "none") & ~np.isin(t, NOT_TARGETS) & ~np.char.startswith(
        t.astype("U"), "DRUG:")


def plan(obs_by_shard: dict, levels, seed: int):
    """Per shard: the level of each row (0 = not a sampled perturbed cell); per group: its cells and kept counts."""
    rows = defaultdict(list)                       # group -> [(shard, row, stratum, cell_key)]
    for name, obs in obs_by_shard.items():
        pert = np.flatnonzero(is_perturbed(obs))
        for r in pert:
            g = (obs["study"][r], obs["context"][r], obs["target"][r])
            rows[g].append((name, int(r), f"{obs['library'][r]}|{obs['guides'][r]}", obs["cell_key"][r]))
    level_of = {name: np.zeros(len(obs["cell_key"]), np.int32) for name, obs in obs_by_shard.items()}
    groups = {}
    for g, items in rows.items():
        strata = defaultdict(list)
        for it in items:
            strata[it[2]].append(it)
        sh = {s: int(h64([s], seed)[0]) for s in strata}
        ordered = []
        for s in strata:
            cells = strata[s]
            hk = h64([c[3] for c in cells], seed)
            strata[s] = [cells[i] for i in np.argsort(hk, kind="stable")]
        depth = max(len(v) for v in strata.values())
        for k in range(depth):                                     # round robin by rank, strata by hash
            for s in sorted(strata, key=lambda s: sh[s]):
                if k < len(strata[s]):
                    ordered.append(strata[s][k])
        for rank, (name, r, _, _) in enumerate(ordered):
            lv = next((c for c in sorted(levels) if rank < c), 0)
            level_of[name][r] = lv
        groups[g] = {"cells": len(ordered), "kept": {str(c): min(len(ordered), c) for c in sorted(levels)},
                     "strata": len(strata)}
    return level_of, groups


def write_one(task):
    """Write the sampled shard of one source shard; returns its manifest row.

    Revision of 4/10 04:45, after vcc-sampled-hct116-l64-r2 died at the 46th of 109 Orion shards with an empty log
    (hypothesis: memory, as E-20261004-001): the source is opened backed and only the kept rows of X are read
    (anndata reads the row slices of the CSR); the check re-reads the written X with h5py and compares it with the
    kept rows in memory, and the kept rows' lengths with the source's row pointer; each shard runs in a fresh process
    (main: spawn, max_tasks_per_child=1) and prints one line when done."""
    import anndata as ad
    import h5py
    import scipy.sparse as sp
    src, out_dir, keep_rows, level, rule, meta = task
    t0 = time.time()
    keep = np.asarray(keep_rows, np.int64)
    a = ad.read_h5ad(src, backed="r")
    n_src = int(a.n_obs)
    b = a[keep].to_memory()
    a.file.close()
    sub = b.X if sp.issparse(b.X) else sp.csr_matrix(b.X)
    sub = sub.tocsr()
    with h5py.File(src, "r") as f:
        indptr = f["X"]["indptr"][:]
    want_len = (indptr[keep + 1] - indptr[keep]).astype(np.int64)
    src_nnz = int(indptr[-1])
    del indptr
    uns = dict(b.uns)
    uns["rows"] = {"rule": rule, "level": level, "source_shard": src.name, "source_rows": n_src,
                   "kept_rows": int(len(keep))}
    uns["parity"] = {"kept_cells": int(len(keep)), "kept_nnz": int(sub.nnz), "kept_counts": int(sub.sum()),
                     "source_cells": n_src, "source_nnz": src_nnz}
    uns["writer"] = meta
    b.uns = uns
    b.X = sub
    dest = out_dir / f"{src.stem}__L{level}.h5ad"
    b.write_h5ad(dest)
    with h5py.File(dest, "r") as f:
        g = f["X"]
        same = (np.array_equal(g["indptr"][:], sub.indptr) and np.array_equal(g["indices"][:], sub.indices)
                and np.array_equal(g["data"][:], sub.data))
    same = bool(same and np.array_equal(np.diff(sub.indptr), want_len))
    row = {"source": src.name, "source_bytes": src.stat().st_size, "source_sha256": sha256_file(src),
           "output": dest.name, "output_bytes": dest.stat().st_size, "output_sha256": sha256_file(dest),
           "kept_rows": int(len(keep)), "kept_nnz": int(sub.nnz), "kept_counts": int(sub.sum()),
           "reread_equal": same, "seconds": round(time.time() - t0, 2), "peak_rss_mb": peak_rss_mb()}
    print(json.dumps({"msg": "shard", **{k: row[k] for k in ("source", "kept_rows", "reread_equal", "seconds",
                                                             "peak_rss_mb")}}), flush=True)
    return row


def peak_rss_mb():
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
    except Exception:                                   # Windows: no resource module
        return None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--shard-roots", nargs="+", required=True, type=Path)
    p.add_argument("--pattern", default="*.h5ad", help="glob of the shards under the roots (alternatives with |)")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--level", type=int, default=64)
    p.add_argument("--levels", type=int, nargs="+", default=[32, 64, 128])
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--workers", type=int, default=2)
    a = p.parse_args()
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    if a.level not in a.levels:
        sys.exit("--level must be one of --levels")
    shards = []
    for root in a.shard_roots:
        for pat in a.pattern.split("|"):
            shards += sorted(Path(root).rglob(pat))
    names = [s.name for s in shards]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        sys.exit(f"shards with the same name under the roots: {dup[:3]}")
    if not shards:
        sys.exit("no shard found")
    t0 = time.time()
    obs_by_shard = {s.name: read_obs(s) for s in shards}
    level_of, groups = plan(obs_by_shard, a.levels, a.seed)
    a.out.mkdir(parents=True)
    rule = (f"metadata-only nested levels {sorted(a.levels)} per (study, context, target), strata (library, guides) "
            f"in sha256 order with seed {a.seed}, round robin; kept: perturbed cells of level <= {a.level} and every "
            "control (control_kind NTC)")
    meta = {"script": "reports/sorgenti/prepasso_ampliato_2026-10-04/build_sampled_shards.py",
            "script_sha256": sha256_file(Path(__file__)), "python": sys.version.split()[0]}
    tasks, counts = [], defaultdict(int)
    for s in shards:
        obs = obs_by_shard[s.name]
        lv = level_of[s.name]
        ctrl = obs["control_kind"].astype(str) == "NTC"
        pert = is_perturbed(obs)
        keep = np.flatnonzero(ctrl | (pert & (lv > 0) & (lv <= a.level)))
        counts["controls_kept"] += int(ctrl.sum())
        counts["perturbed_total"] += int(pert.sum())
        counts["perturbed_kept"] += int((pert & (lv > 0) & (lv <= a.level)).sum())
        counts["dropped_unlabelled_or_unassigned"] += int((~ctrl & ~pert).sum())
        tasks.append((s, a.out, keep.astype(np.int64), a.level, rule, meta))
    del obs_by_shard, level_of
    print(json.dumps({"msg": "start", "shards": len(tasks), **counts, "groups": len(groups),
                      "seconds_plan": round(time.time() - t0, 1)}), flush=True)
    rows = []
    if a.workers > 1:
        import multiprocessing as mp
        # a fresh process per shard, started clean: no memory carried from one shard to the next (E-20261004-001)
        with ProcessPoolExecutor(max_workers=a.workers, mp_context=mp.get_context("spawn"),
                                 max_tasks_per_child=1) as ex:
            rows = list(ex.map(write_one, tasks))
    else:
        rows = [write_one(t) for t in tasks]
    bad = [r["source"] for r in rows if not r["reread_equal"]]
    manifest = {"rule": rule, "parameters": {"level": a.level, "levels": sorted(a.levels), "seed": a.seed,
                                             "workers": a.workers, "pattern": a.pattern},
                "writer": meta, "shards": rows, "totals": dict(counts), "groups": len(groups),
                "groups_detail": [{"study": g[0], "context": g[1], "target": g[2], **v} for g, v in sorted(groups.items())],
                "reread_failures": bad, "seconds": round(time.time() - t0, 1)}
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps({"shards": len(rows), **counts, "groups": len(groups), "reread_failures": len(bad)}))
    if bad:
        sys.exit(f"sampled shards that do not re-read equal: {bad[:3]}")


if __name__ == "__main__":
    main()
