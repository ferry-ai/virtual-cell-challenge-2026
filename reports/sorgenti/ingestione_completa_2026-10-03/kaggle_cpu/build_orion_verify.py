"""Close an Orion line on Kaggle: the parts written by other kernels, re-read by a new one and reconciled.

One kernel per line mounts the outputs of its part kernels (r2 and r3) and the code dataset, and checks, with the rule
written here before any line was closed (3/10, 18:10):

- every part passes the rule of a part (build_orion_kaggle_r2.py, R3_TAIL): every boolean check of its unit other than
  `whole_line` is true, and its cells and shards are the selected cells and the files of the sample in the part;
- the shards of the parts are distinct and are exactly the files of the frozen list that have selected cells;
- the cells of the parts add up to the cells of the line in the spec;
- every shard, re-read on this runtime, has the bytes and the sha256 of its unit manifest (the independent re-read:
  a hash computed by the runtime that wrote a file can come from its cache, E-20260929-005).

It also counts, from the obs of every shard, the cells per (library, target, control kind): the inventory the sampling
levels of STRATEGIA_DATI_TRAINING.md are sized on. No count matrix is loaded for it.

Output: line_complete.json (or line_failed.json), shards.csv, inventory.parquet. `--partial` reports the parts given
without judging the line (a line still being written).

    python build_orion_verify.py --config-dir <dir> --owner davideferrante11 --stage <new dir> --line HCT116 \
        --parts vcc-orion-hct116-p0of4-r2 vcc-orion-hct116-p2of4-r2 ... --slug vcc-orion-hct116-verify-r1 [--partial]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_orion_kaggle_r2 import ORION, kaggle, sha256_file  # noqa: E402

KERNEL = r'''
import hashlib, json, subprocess, sys, time
from pathlib import Path
P = json.loads(r"""__PARAMS__""")
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
LINE, t0 = P["line"], time.time()
if subprocess.run([sys.executable, "-c", "import anndata"], capture_output=True).returncode:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "anndata"], capture_output=True)
import anndata as ad
import pandas as pd


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


frozen = json.loads((find(P["code_slug"]) / "code_snapshot" / P["files_manifest"]).read_text())
frozen = [f["name"] for f in frozen["files"] if "path" in f and "sha256" in f]
sample, parts, rows, inventory = None, [], [], []
for job in P["parts"]:
    root = find(job)
    unit = root / "shards" / P["unit"]
    m = json.loads((unit / "manifest.json").read_text())
    table = pd.read_parquet(root / "sample" / f"{LINE}.parquet", columns=["gem_file", "selected"])
    per_file = table[table["selected"]].groupby("gem_file").size()
    if sample is None:
        sample = per_file
    want = per_file.reindex(m["files_in_part"]).dropna()
    checks = {k: v for k, v in m["parity"].items() if isinstance(v, bool) and k not in ("ok", "whole_line")}
    part = {"job": job, "part": m.get("part"), "checks": checks, "whole_line": m["parity"].get("whole_line"),
            "cells": m["totals"]["cells"], "cells_selected_in_part": int(want.sum()), "shards": m["totals"]["shards"],
            "files_with_cells_in_part": int(len(want)), "bytes": m["totals"]["bytes"], "nnz": m["totals"]["nnz"],
            "counts": m["totals"]["counts"], "same_sample_as_first_part": bool(per_file.equals(sample)),
            "complete_json": (root / "shards" / "complete.json").is_file(),
            "part_complete_json": (root / "part_complete.json").is_file(), "unit_manifest_sha256": sha(unit / "manifest.json")}
    part["ok"] = bool(checks and all(checks.values()) and part["same_sample_as_first_part"]
                      and part["cells"] == part["cells_selected_in_part"]
                      and part["shards"] == part["files_with_cells_in_part"])
    for s in m["shards"]:
        path = unit / f"{s['shard']}.h5ad"
        here = {"bytes_here": path.stat().st_size, "sha256_here": sha(path)}
        rows.append({"job": job, "shard": s["shard"], "path": str(path), "bytes": s["bytes"], "sha256": s["sha256"],
                     "cells": s["cells"], "nnz": s["nnz"], "counts": s["sum_after"], **here,
                     "same": here["bytes_here"] == s["bytes"] and here["sha256_here"] == s["sha256"]})
        obs = ad.read_h5ad(path, backed="r").obs[["library", "target", "control_kind"]]
        n = obs.groupby(["library", "target", "control_kind"], observed=True).size().rename("cells").reset_index()
        if int(n["cells"].sum()) != s["cells"]:
            raise SystemExit(f"{s['shard']}: obs has {int(n['cells'].sum())} rows, the manifest {s['cells']} cells")
        inventory.append(n)
    parts.append(part)
    print(json.dumps({"part": part, "seconds": round(time.time() - t0)}), flush=True)
names = [r["shard"] for r in rows]
verdict = {"parts_ok": all(p["ok"] for p in parts), "bytes_and_sha256_reread": all(r["same"] for r in rows),
           "shards_distinct": len(names) == len(set(names))}
if not P["partial"]:
    verdict.update(shards_are_the_files_with_cells=set(names) == set(sample.index),
                   files_in_the_frozen_list=set(sample.index) <= set(frozen),
                   cells_equal_expected=sum(r["cells"] for r in rows) == P["expected_cells"])
ok = all(verdict.values())
totals = {k: int(sum(r[k] for r in rows)) for k in ("cells", "nnz", "counts", "bytes")}
doc = {"line": LINE, "partial": P["partial"], "ok": ok, "verdict": verdict, "totals": {"shards": len(rows), **totals},
       "expected": {"cells": P["expected_cells"], "files_in_frozen_list": len(frozen), "files_with_cells": int(len(sample))},
       "parts": parts, "seconds": round(time.time() - t0, 1), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
pd.DataFrame(rows).to_csv(OUT / "shards.csv", index=False)
inv = pd.concat(inventory, ignore_index=True)
inv.insert(0, "line", LINE)
inv.to_parquet(OUT / "inventory.parquet", index=False)
targeted = inv[inv["control_kind"] == "none"].groupby("target")["cells"].sum()
doc["inventory"] = {"rows": int(len(inv)), "targets": int(targeted.size), "targeted_cells": int(targeted.sum()),
                    "control_cells": int(inv.loc[inv["control_kind"] != "none", "cells"].sum()),
                    "targeted_cells_at_cap": {str(k): int(targeted.clip(upper=k).sum()) for k in (32, 64, 128)}}
name = ("partial" if P["partial"] else "line") + ("_complete.json" if ok else "_failed.json")
(OUT / name).write_text(json.dumps(doc, indent=1))
print(json.dumps({k: doc[k] for k in ("line", "partial", "ok", "verdict", "totals", "expected", "inventory", "seconds")}), flush=True)
if not ok:
    raise SystemExit("the line is not closed: see the verdict")
'''


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--code-slug", default="vcc-ingest-code-r1")
    p.add_argument("--line", choices=["HCT116", "HEK293T"], required=True)
    p.add_argument("--parts", nargs="+", required=True, help="slugs of the part kernels")
    p.add_argument("--slug", required=True)
    p.add_argument("--partial", action="store_true")
    p.add_argument("--launch-log", type=Path)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    line = json.loads((ORION / "specs/orion_full_v1.json").read_text(encoding="utf-8"))["lines"][a.line]
    params = {"line": a.line, "unit": line["unit"], "code_slug": a.code_slug, "files_manifest": line["files_manifest"],
              "expected_cells": line["expected"]["cells_pass_filter"], "partial": a.partial,
              "parts": [s.replace("-", "_") for s in a.parts]}
    text = KERNEL.replace("__PARAMS__", json.dumps(params, indent=1))
    compile(text, "run.py", "exec")
    a.stage.mkdir(parents=True)
    (a.stage / "run.py").write_text(text, encoding="utf-8", newline="\n")
    (a.stage / "kernel-metadata.json").write_text(json.dumps(
        {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
         "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False, "enable_internet": True,
         "dataset_sources": [f"{a.owner}/{a.code_slug}"], "kernel_sources": [f"{a.owner}/{s}" for s in a.parts],
         "competition_sources": []}, indent=1))
    record = {"slug": f"{a.owner}/{a.slug}", "line": a.line, "verify": True, "partial": a.partial, "parts": a.parts,
              "stage": a.stage.as_posix(), "run_sha256": sha256_file(a.stage / "run.py")}
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed\n{json.dumps(record)}")
        return
    r = kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)
    answer = ((r.stdout or "") + (r.stderr or "")).strip()
    accepted = r.returncode == 0 and "successfully pushed" in answer
    record.update(pushed_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), returncode=r.returncode,
                  accepted=accepted, answer=answer[-600:])
    if a.launch_log:
        with open(a.launch_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    if not accepted:
        sys.exit("the push failed")


if __name__ == "__main__":
    main()
