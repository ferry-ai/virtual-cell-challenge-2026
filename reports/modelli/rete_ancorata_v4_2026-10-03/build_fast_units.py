"""Compact twins of shards written by unit jobs (Orion parts, KOLF, CD4), for the expanded corpus (D-053).

build_fast.py reads datasets published with files.json. The ingestion kernels of 3/10 leave their shards in the kernel
output instead, as <job>/shards/<unit>/<shard>.h5ad with a manifest.json per unit (shard, bytes, sha256, cells). This
builder takes its tasks from those manifests and encodes with the same function (build_fast.one, fastshard.encode): the
shard's bytes and sha256 are checked against the unit manifest, the twin is decoded again and compared exactly, and
fast_manifest.json has the format the training resolves twins with (train_cellnet.resolve_twins).

    python build_fast_units.py --input /kaggle/input --jobs vcc_orion_hek293t_p0of8_r3 ... --out /kaggle/working/twins \
        [--workers 4]

--jobs are the folder names the part kernels write in their output (the slug with underscores). A shard that fails any
check fails the build (exit code 1), and its twin is not kept.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fastshard as FS  # noqa: E402
from build_fast import one  # noqa: E402


def find(input_root: Path, job: str) -> Path:
    hits = [p for p in input_root.glob(f"**/{job}") if p.is_dir() and (p / "shards").is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{job}: {len(hits)} folders with shards below {input_root}: {hits[:3]}")
    return hits[0]


def tasks_of(input_root: Path, jobs, out: Path):
    tasks, chosen = [], {}
    for job in jobs:
        root = find(input_root, job) / "shards"
        units = sorted(p for p in root.iterdir() if (p / "manifest.json").is_file())
        if not units:
            raise SystemExit(f"{job}: no unit manifest under {root}")
        n = b = 0
        for unit in units:
            m = json.loads((unit / "manifest.json").read_text(encoding="utf-8"))
            for s in m["shards"]:
                src = unit / f"{s['shard']}.h5ad"
                tasks.append((str(src), str(out / FS.twin_name(src.name)),
                              {"bytes": s["bytes"], "sha256": s["sha256"], "cells": s["cells"]}))
                n, b = n + 1, b + s["bytes"]
        chosen[job] = {"units": [u.name for u in units], "chosen": n, "bytes": b, "mount": str(root)}
    names = [Path(t[0]).name for t in tasks]
    if len(set(names)) != len(names):
        raise SystemExit("two shards share a file name: their twins would collide")
    return tasks, chosen


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", type=Path, default=Path("/kaggle/input"))
    p.add_argument("--jobs", nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    t0 = time.time()
    tasks, chosen = tasks_of(a.input, a.jobs, a.out)
    a.out.mkdir(parents=True)
    print(json.dumps({"msg": "start", "shards": len(tasks), "jobs": chosen, "workers": a.workers}), flush=True)
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
               "values": int(sum(r["nnz"] for r in ok)), "cells": int(sum(r["n_rows"] for r in ok)),
               "wall_seconds": round(time.time() - t0, 1), "workers": a.workers, "cpus": os.cpu_count()}
    manifest = {"format": FS.FORMAT, "version": FS.FORMAT_VERSION,
                "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "jobs": chosen, "shards": ok,
                "failed": bad, "profile": profile,
                "rule": "fastshard.encode: source bytes, sha256 and cells equal to the unit manifest of the job that "
                        "wrote the shard, twin decoded again and compared exactly with the shard's arrays"}
    (a.out / "fast_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps({"msg": "done", "verified": len(ok), "failed": len(bad), "profile": profile}), flush=True)
    if bad:
        raise SystemExit(f"{len(bad)} shards failed: {[r['name'] for r in bad][:5]}")


if __name__ == "__main__":
    main()
