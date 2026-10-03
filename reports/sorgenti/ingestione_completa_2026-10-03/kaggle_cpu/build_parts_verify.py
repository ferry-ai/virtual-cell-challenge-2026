"""Close a source written in parts by kolf_job.py or cd4_job.py: the parts re-read by a new kernel and reconciled.

One kernel mounts the outputs of the part kernels and checks, per unit (the KOLF file, or one CD4 file), with the rule
written here before any source was closed (3/10, 18:40):

- every part ended complete (complete.json, unit parity ok);
- the ranges of the parts are contiguous and cover the rows of the unit from 0 to the number in the spec;
- the cells add up: for KOLF the cells are the rows; for CD4 raw = eligible + excluded per part, and the cells are
  the eligible rows;
- every shard, re-read on this runtime, has the bytes and the sha256 of its unit manifest (E-20260929-005).

It also counts, from the obs of every shard, the cells per (context, donor, condition, library, guide, target, control
kind): the inventory the sampling levels of STRATEGIA_DATI_TRAINING.md are sized on. No count matrix is loaded for it.

Output: source_complete.json (or source_failed.json), shards.csv, inventory.parquet.

    python build_parts_verify.py --config-dir <dir> --owner davideferrante11 --stage <new dir> \
        --units kolf_pan_genome=2659209 --parts vcc-kolf-pan-p0of2-r2 vcc-kolf-pan-p1of2-r1 --slug vcc-kolf-pan-verify-r1
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_orion_kaggle_r2 import kaggle, sha256_file  # noqa: E402

KERNEL = r'''
import hashlib, json, subprocess, sys, time
from pathlib import Path
P = json.loads(r"""__PARAMS__""")
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
t0 = time.time()
if subprocess.run([sys.executable, "-c", "import anndata"], capture_output=True).returncode:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "anndata"], capture_output=True)
import anndata as ad
import pandas as pd

KEYS = ["study", "context", "donor_or_clone", "condition", "modality", "library", "guides", "target", "control_kind"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def find(name):
    hits = [p for p in INPUT.glob(f"**/{name}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{name}: {len(hits)} mounts: {hits[:3]}")
    return hits[0]


parts, rows, inventory = [], [], []
for job in P["parts"]:
    root = find(job) / "shards"
    done = json.loads((root / "complete.json").read_text()) if (root / "complete.json").is_file() else {}
    for unit_dir in sorted(p for p in root.iterdir() if (p / "manifest.json").is_file()):
        m = json.loads((unit_dir / "manifest.json").read_text())
        lo, hi = (int(v) for v in (m.get("cell_range") or m.get("row_range")).split(":"))
        raw = m.get("rows", {}).get("raw", m["totals"]["cells"])
        part = {"job": job, "unit": m["unit"], "range": [lo, hi], "rows": raw, "cells": m["totals"]["cells"],
                "excluded": m.get("rows", {}).get("excluded", 0), "by_reason": m.get("by_reason"),
                "shards": m["totals"]["shards"], "bytes": m["totals"]["bytes"], "nnz": m["totals"]["nnz"],
                "counts": m["totals"]["counts"], "smoke": m.get("smoke_max_cells"),
                "complete": done.get("status") == "complete" and bool(m["parity"].get("ok")),
                "unit_manifest_sha256": sha(unit_dir / "manifest.json")}
        part["ok"] = bool(part["complete"] and part["smoke"] is None and raw == hi - lo
                          and part["cells"] + part["excluded"] == raw)
        for s in m["shards"]:
            path = unit_dir / f"{s['shard']}.h5ad"
            here = {"bytes_here": path.stat().st_size, "sha256_here": sha(path)}
            rows.append({"job": job, "unit": m["unit"], "shard": s["shard"], "path": str(path), "bytes": s["bytes"],
                         "sha256": s["sha256"], "cells": s["cells"], "nnz": s["nnz"], "counts": s["sum_after"], **here,
                         "same": here["bytes_here"] == s["bytes"] and here["sha256_here"] == s["sha256"]})
            obs = ad.read_h5ad(path, backed="r").obs[KEYS]
            n = obs.groupby(KEYS, observed=True).size().rename("cells").reset_index()
            if int(n["cells"].sum()) != s["cells"]:
                raise SystemExit(f"{s['shard']}: obs has {int(n['cells'].sum())} rows, the manifest {s['cells']} cells")
            inventory.append(n.assign(unit=m["unit"]))
        parts.append(part)
        print(json.dumps({"part": part, "seconds": round(time.time() - t0)}), flush=True)
units = {}
for unit, expected in P["units"].items():
    mine = sorted((p for p in parts if p["unit"] == unit), key=lambda p: p["range"][0])
    ranges = [p["range"] for p in mine]
    units[unit] = {"parts": len(mine), "expected_rows": expected, "rows": sum(p["rows"] for p in mine),
                   "cells": sum(p["cells"] for p in mine), "excluded": sum(p["excluded"] for p in mine),
                   "bytes": sum(p["bytes"] for p in mine), "nnz": sum(p["nnz"] for p in mine),
                   "counts": sum(p["counts"] for p in mine),
                   "covers_the_unit": bool(ranges) and ranges[0][0] == 0 and ranges[-1][1] == expected
                   and all(a[1] == b[0] for a, b in zip(ranges, ranges[1:]))}
names = [(r["unit"], r["shard"]) for r in rows]
verdict = {"parts_ok": bool(parts) and all(p["ok"] for p in parts),
           "no_part_of_another_unit": {p["unit"] for p in parts} == set(P["units"]),
           "units_covered": all(u["covers_the_unit"] for u in units.values()),
           "bytes_and_sha256_reread": all(r["same"] for r in rows), "shards_distinct": len(names) == len(set(names))}
ok = all(verdict.values())
inv = pd.concat(inventory, ignore_index=True)
inv = inv.groupby(["unit"] + KEYS, observed=True)["cells"].sum().reset_index()
pd.DataFrame(rows).to_csv(OUT / "shards.csv", index=False)
inv.to_parquet(OUT / "inventory.parquet", index=False)
combo = inv[inv["control_kind"] == "none"].groupby(["context", "target"], observed=True)["cells"].sum()
doc = {"ok": ok, "verdict": verdict, "units": units,
       "totals": {"shards": len(rows), **{k: int(sum(r[k] for r in rows)) for k in ("cells", "nnz", "counts", "bytes")}},
       "inventory": {"rows": int(len(inv)), "contexts": sorted(map(str, inv["context"].unique())),
                     "context_target_combinations": int(combo.size), "targeted_cells": int(combo.sum()),
                     "control_cells": int(inv.loc[inv["control_kind"] != "none", "cells"].sum()),
                     "targeted_cells_at_cap": {str(k): int(combo.clip(upper=k).sum()) for k in (32, 64, 128)}},
       "parts": parts, "seconds": round(time.time() - t0, 1), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
(OUT / ("source_complete.json" if ok else "source_failed.json")).write_text(json.dumps(doc, indent=1))
print(json.dumps({k: doc[k] for k in ("ok", "verdict", "units", "totals", "inventory", "seconds")}), flush=True)
if not ok:
    raise SystemExit("the source is not closed: see the verdict")
'''


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--units", nargs="+", required=True, help="unit=rows, e.g. kolf_pan_genome=2659209")
    p.add_argument("--parts", nargs="+", required=True, help="slugs of the part kernels")
    p.add_argument("--slug", required=True)
    p.add_argument("--launch-log", type=Path)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    params = {"units": {u.split("=")[0]: int(u.split("=")[1]) for u in a.units},
              "parts": [s.replace("-", "_") for s in a.parts]}
    text = KERNEL.replace("__PARAMS__", json.dumps(params, indent=1))
    compile(text, "run.py", "exec")
    a.stage.mkdir(parents=True)
    (a.stage / "run.py").write_text(text, encoding="utf-8", newline="\n")
    (a.stage / "kernel-metadata.json").write_text(json.dumps(
        {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
         "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False, "enable_internet": True,
         "dataset_sources": [], "kernel_sources": [f"{a.owner}/{s}" for s in a.parts], "competition_sources": []},
        indent=1))
    record = {"slug": f"{a.owner}/{a.slug}", "verify": True, "units": params["units"], "parts": a.parts,
              "stage": a.stage.as_posix(), "run_sha256": sha256_file(a.stage / "run.py")}
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed\n{json.dumps(record)}")
        return
    r = kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)
    answer = ((r.stdout or "") + (r.stderr or "")).strip()
    accepted = r.returncode == 0 and "successfully pushed" in answer and "not valid kernel sources" not in answer
    record.update(pushed_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), returncode=r.returncode,
                  accepted=accepted, answer=answer[-600:])
    if a.launch_log:
        with open(a.launch_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    if not accepted:
        sys.exit("the push failed or a part is not a valid source")


if __name__ == "__main__":
    main()
