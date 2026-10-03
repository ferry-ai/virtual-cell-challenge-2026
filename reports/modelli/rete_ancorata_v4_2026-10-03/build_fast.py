"""Build the compact twins of the corpus shards (fastshard.py) on a CPU runtime, with their package manifest.

    python build_fast.py --input /kaggle/input --datasets rlab-a549 rlab-h1-vcc2025-trainval ... \
        [--glob rlab-tian-norman="norman2019__*.h5ad|tian2021_*.h5ad"] --out /kaggle/working/twins --workers 4 \
        [--reconstruct-prepass <dir with prepass.pkl> --reconstruct-receipt <coverage.json of the run>]

For every chosen shard of every dataset (files.json of publish_kaggle.py lists file, bytes, sha256 and cells): the
shard's bytes and sha256 are checked against files.json, the twin is written and decoded again block by block and
compared exactly with the shard (fastshard.encode). fast_manifest.json lists every receipt; the profile sums, per
stage, the seconds of the raw read (with the sha256), of h5py's read and gzip decompression, of the encoding and of
the decoding with comparison, and derives MB/s. A shard that fails any check fails the build (exit code 1), and its
twin is not kept.

--reconstruct-prepass: version 3's epoch sampler replayed on the prepass state of the H1 run (no count read): the
roles, the order in which each role loads its shards, and the draws per key up to the step where the run stopped.
Its draws are compared with the run's coverage.json, so the cause of the missing Neuron cells is shown on the real
layout rather than argued (diagnosi_r1/DIAGNOSI.md).
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fastshard as FS  # noqa: E402


def mount(input_root: Path, slug: str) -> Path:
    for p in (input_root / slug, input_root / "datasets" / "davidmaisterx" / slug,
              input_root / "datasets" / "davideferrante11" / slug, input_root / "notebooks" / "davideferrante11" / slug):
        if p.is_dir():
            return p
    hits = [p for p in input_root.glob(f"**/{slug}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{slug}: {len(hits)} mounts below {input_root}: {hits[:3]}")
    return hits[0]


def one(task):
    src, dst, expect = task
    try:
        rec = FS.encode(src, dst)
    except Exception as e:                    # noqa: BLE001 - a failed shard is reported, never silently skipped
        return {"name": Path(src).name, "error": repr(e)[:500], "verified": False}
    rec["files_json"] = {"bytes": expect["bytes"], "sha256": expect["sha256"], "cells": expect.get("cells")}
    rec["matches_files_json"] = (rec["source_bytes"] == expect["bytes"] and rec["source_sha256"] == expect["sha256"]
                                 and (expect.get("cells") is None or rec["n_rows"] == expect["cells"]))
    if not rec["matches_files_json"]:
        Path(dst).unlink(missing_ok=True)
        rec["verified"] = False
    return rec


def roles_of(train_rows_sizes, W):
    """train_cellnet.roles_of of versions 2-4: shards with training rows split into W roles, greedily by size."""
    import numpy as np
    parts, load = [[] for _ in range(W)], np.zeros(W)
    for sid in sorted((i for i, n in enumerate(train_rows_sizes) if n), key=lambda i: (-train_rows_sizes[i], i)):
        r = int(np.argmin(load))
        parts[r].append(sid)
        load[r] += train_rows_sizes[sid]
    return parts


def reconstruct(prepass: Path, receipt: Path, W=3, buffer=4, seed=0, batch=256) -> dict:
    """Version 3's batch stream replayed without counts on a prepass state, until the step of the run's receipt."""
    import pickle
    import numpy as np
    import cell_data as CD
    with open(prepass / "prepass.pkl", "rb") as fh:
        st = pickle.load(fh)
    cov = json.loads(receipt.read_text(encoding="utf-8"))
    steps = int(cov["steps"])
    shards = st["shards"]
    sizes = [len(s["train_rows"]) for s in shards]
    parts = roles_of(sizes, W)
    draws, loaded_at = Counter(), {}
    for r in range(W):
        sampler = CD.EpochSampler([(sid, shards[sid]["train_rows"]) for sid in parts[r]], buffer, seed=seed * 1000 + r)
        local = -(-(steps - r) // W)                      # batches of role r among global steps 0..steps-1
        for j in range(local):
            before = set(sampler.loaded())
            for sid, row in sampler.batch(batch):
                draws[st["key_names"][int(shards[sid]["key"][row])]] += 1
            for sid in set(sampler.loaded()) - before:
                loaded_at.setdefault(sid, j * W + r)
            if j == 0:
                for sid in before:
                    loaded_at.setdefault(sid, r)
    by_key_run = {e["key"]: e["draws"] for e in cov["by_key"]}
    keys = sorted(set(by_key_run) | set(draws))
    mismatch = {k: [draws.get(k, 0), by_key_run.get(k, 0)] for k in keys if draws.get(k, 0) != by_key_run.get(k, 0)}
    per_key_shards = defaultdict(list)
    for sid, s in enumerate(shards):
        if sizes[sid]:
            ks = np.unique(np.asarray(s["key"])[s["train_rows"]])
            for k in ks:
                per_key_shards[st["key_names"][int(k)]].append(
                    {"shard": s["name"], "role": next(r for r in range(W) if sid in parts[r]),
                     "first_loaded_at_step": loaded_at.get(sid)})
    return {"steps": steps, "roles": W, "buffer": buffer, "seed": seed, "batch": batch,
            "draws_equal_to_the_run": not mismatch, "draws_mismatch": mismatch,
            "keys_never_drawn": sorted(k for k in by_key_run if draws.get(k, 0) == 0),
            "shards_of_tian2021": {k: v for k, v in per_key_shards.items() if k.startswith("tian2021")},
            "shards_never_loaded_by_the_stop": sum(1 for sid, n in enumerate(sizes) if n and sid not in loaded_at),
            "shards_with_training_rows": sum(1 for n in sizes if n)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", type=Path, default=Path("/kaggle/input"))
    p.add_argument("--datasets", nargs="+", required=True)
    p.add_argument("--glob", action="append", default=[], metavar="DATASET=PATTERN")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    p.add_argument("--reconstruct-prepass", type=Path)
    p.add_argument("--reconstruct-receipt", type=Path)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    a.out.mkdir(parents=True)
    t0 = time.time()
    globs = dict(x.split("=", 1) for x in a.glob)
    tasks, chosen = [], {}
    for d in a.datasets:
        root = mount(a.input, d)
        files = json.loads((root / "files.json").read_text(encoding="utf-8"))
        pick = [f for f in files if any(fnmatch.fnmatch(f["file"], g) for g in globs.get(d, "*.h5ad").split("|"))]
        chosen[d] = {"files": len(files), "chosen": len(pick), "bytes": sum(f["bytes"] for f in pick),
                     "mount": str(root)}
        tasks += [(str(root / f["file"]), str(a.out / FS.twin_name(Path(f["file"]).name)), f) for f in pick]
    names = [Path(t[0]).name for t in tasks]
    if len(set(names)) != len(names):
        raise SystemExit("two shards share a file name: their twins would collide")
    print(json.dumps({"msg": "start", "shards": len(tasks), "datasets": chosen, "workers": a.workers}), flush=True)
    receipts = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for rec in ex.map(one, tasks, chunksize=1):
            receipts.append(rec)
            print(json.dumps({"msg": "shard", "name": rec["name"], "verified": rec.get("verified"),
                              "seconds": rec.get("seconds"), "error": rec.get("error")}), flush=True)
    ok = [r for r in receipts if r.get("verified")]
    bad = [r for r in receipts if not r.get("verified")]
    prof = defaultdict(float)
    for r in ok:
        for k, v in r["seconds"].items():
            prof[k] += v
    src_mb = sum(r["source_bytes"] for r in ok) / 2**20
    twin_mb = sum(r["twin_bytes"] for r in ok) / 2**20
    profile = {"seconds_summed_over_processes": {k: round(v, 1) for k, v in prof.items()},
               "source_mb": round(src_mb, 1), "twin_mb": round(twin_mb, 1),
               "twin_over_source": round(twin_mb / src_mb, 4) if src_mb else None,
               "mb_per_s_per_process_of_source": {k: round(src_mb / v, 2) for k, v in prof.items() if v > 0},
               "values": int(sum(r["nnz"] for r in ok)), "cells": int(sum(r["n_rows"] for r in ok)),
               "wall_seconds": round(time.time() - t0, 1), "workers": a.workers, "cpus": os.cpu_count(),
               "note": "per-stage seconds summed over the worker processes that ran concurrently; MB/s per process "
                       "= source MB / summed seconds of the stage"}
    manifest = {"format": FS.FORMAT, "version": FS.FORMAT_VERSION, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                time.gmtime()), "datasets": chosen, "globs": globs, "shards": ok, "failed": bad, "profile": profile,
                "rule": "fastshard.encode: source bytes and sha256 equal to files.json, twin decoded again and compared "
                        "exactly with the shard's arrays (rows sorted by feature index)"}
    if a.reconstruct_prepass:
        manifest["reconstruction_v3_h1"] = reconstruct(a.reconstruct_prepass, a.reconstruct_receipt)
    (a.out / "fast_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps({"msg": "done", "verified": len(ok), "failed": len(bad), "profile": profile}), flush=True)
    if bad:
        raise SystemExit(f"{len(bad)} shards failed: {[r['name'] for r in bad][:5]}")


if __name__ == "__main__":
    main()
