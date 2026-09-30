"""Publish the shards of one finished R-LAB unit as a private Kaggle dataset of the training account.

Kaggle notebooks cannot read Google Drive, so the corpus that Colab writes on Drive reaches the GPU training this way.
Only a finished job is published: its `complete.json` must exist. For one unit of the job this builds a flat staging
folder of symbolic links to the shards on Drive (`<unit>__<shard>.h5ad`, nothing is copied or changed), the unit's
manifest, one file with all its shard receipts and the job's `complete.json`; then `kaggle datasets create` (or a new
version when the dataset exists), and it waits until Kaggle reports the dataset ready. The receipt lists every file
with the sha256 of its receipt, so the training kernel can verify each shard before it reads it.

The API token is read from --config-dir (KAGGLE_CONFIG_DIR); it is never printed or copied.

    python publish_kaggle.py --job-dir <Drive>/data/processed/corpus_cellulare_2026-09-30/j01_hepg2_r1 \
        --unit hepg2_nadig --owner davideferrante11 --slug rlab-j01-hepg2-nadig \
        --config-dir <Drive>/runs/rlab_secrets --stage /content/work/publish_j01 --receipt <new json>
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def kaggle(args: list[str], config_dir: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "KAGGLE_CONFIG_DIR": config_dir}
    exe = shutil.which("kaggle") or [sys.executable, "-m", "kaggle"]
    cmd = ([exe] if isinstance(exe, str) else exe) + args
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--job-dir", required=True, type=Path)
    p.add_argument("--unit", required=True, help="a unit of the job, or ALL for every unit in complete.json")
    p.add_argument("--owner", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--stage", required=True, type=Path)
    p.add_argument("--receipt", required=True, type=Path)
    p.add_argument("--wait-minutes", type=float, default=90)
    a = p.parse_args()
    if a.receipt.exists():
        sys.exit(f"refusing: {a.receipt} exists")
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    complete = a.job_dir / "complete.json"
    if not complete.is_file():
        sys.exit(f"refusing: {complete} is absent, the job did not finish")
    units = list(json.loads(complete.read_text(encoding="utf-8"))["units"]) if a.unit == "ALL" else [a.unit]
    a.stage.mkdir(parents=True)
    files = []
    for unit in units:
        unit_dir = a.job_dir / unit
        manifest = json.loads((unit_dir / "manifest.json").read_text(encoding="utf-8"))
        if not manifest["parity"]["ok"]:
            sys.exit(f"refusing: unit {unit} did not pass its parity")
        receipts = []
        for shard in manifest["shards"]:
            src = Path(shard["path"]) if Path(shard["path"]).is_file() else unit_dir / f"{shard['shard']}.h5ad"
            if not src.is_file():
                sys.exit(f"refusing: shard {src} is missing")
            if src.stat().st_size != shard["bytes"]:
                sys.exit(f"refusing: {src} has {src.stat().st_size} bytes, the manifest says {shard['bytes']}")
            name = f"{unit}__{shard['shard']}.h5ad"
            os.symlink(src, a.stage / name)
            receipt = unit_dir / "receipts" / f"{shard['shard']}.json"
            receipts.append(json.loads(receipt.read_text(encoding="utf-8")) if receipt.is_file() else {"shard": shard["shard"]})
            files.append({"file": name, "unit": unit, "bytes": shard["bytes"], "sha256": shard["sha256"],
                          "cells": shard["cells"]})
        shutil.copyfile(unit_dir / "manifest.json", a.stage / f"{unit}__manifest.json")
        (a.stage / f"{unit}__receipts.json").write_text(json.dumps(receipts, indent=1), encoding="utf-8")
    shutil.copyfile(complete, a.stage / "complete.json")
    ref = f"{a.owner}/{a.slug}"
    (a.stage / "dataset-metadata.json").write_text(json.dumps(
        {"title": f"rlab {a.slug}"[:50], "id": ref, "licenses": [{"name": "other"}]}), encoding="utf-8")
    (a.stage / "files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    t0 = time.time()
    exists = kaggle(["datasets", "status", ref], a.config_dir)
    if exists.returncode == 0 and "ready" in exists.stdout.lower():
        run = kaggle(["datasets", "version", "-p", str(a.stage), "-m", f"shards of {','.join(units)}", "--dir-mode", "skip"],
                     a.config_dir)
    else:
        run = kaggle(["datasets", "create", "-p", str(a.stage), "--dir-mode", "skip"], a.config_dir)
    print(run.stdout[-2000:], run.stderr[-2000:], flush=True)
    if run.returncode != 0:
        sys.exit(f"kaggle upload failed with code {run.returncode}")
    status = ""
    while time.time() - t0 < a.wait_minutes * 60:
        status = kaggle(["datasets", "status", ref], a.config_dir).stdout.strip()
        if "ready" in status.lower():
            break
        time.sleep(30)
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    with open(a.receipt, "x", encoding="utf-8") as fh:
        json.dump({"dataset": ref, "status": status, "units": units, "job_dir": str(a.job_dir),
                   "files": files, "cells": sum(f["cells"] for f in files), "bytes": sum(f["bytes"] for f in files),
                   "seconds": round(time.time() - t0, 1), "utc": datetime.now(timezone.utc).isoformat()}, fh, indent=1)
    print(f"{ref}: {status}; {len(files)} shards", flush=True)
    if "ready" not in status.lower():
        sys.exit("the dataset did not become ready in time; its receipt records the last status")


if __name__ == "__main__":
    main()
