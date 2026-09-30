"""Launch a cell-network training run on a Kaggle GPU session (account with GPU: davidmaisterx).

Two steps, both refusing to overwrite:
- `code`: create (or version) the private dataset <owner>/rlab-cellnet-code with cellnet.py, train_cellnet.py, the
  official axis and the target descriptors;
- `run`: push a kernel that verifies every shard of the attached datasets against the sha256 in its files.json
  (published by publish_kaggle.py), then runs train_cellnet.py on them and writes its outputs to /kaggle/working.
The kernel has no internet: everything it reads is in the attached datasets.

    python kaggle_train.py code --config-dir ~/.kaggle --stage <new dir> --descriptors <dir> --axis gene_names.csv
    python kaggle_train.py run --config-dir ~/.kaggle --stage <new dir> --run cellnet-r1-desc \
        --datasets rlab-hepg2-nadig rlab-jurkat-nadig ... --holdout-context HepG2 --target-code descriptors
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWNER = "davidmaisterx"

KERNEL = r'''
import hashlib, json, os, subprocess, sys, time
from pathlib import Path
CODE = Path("/kaggle/input/rlab-cellnet-code")
ARGS = {args}
DATASETS = {datasets}
t0 = time.time()
report = {{"datasets": {{}}, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}}
shard_dirs = []
for d in DATASETS:
    root = Path("/kaggle/input") / d
    files = json.loads((root / "files.json").read_text())
    bad = []
    for f in files:
        p = root / f["file"]
        if not p.is_file() or p.stat().st_size != f["bytes"]:
            bad.append(f["file"]); continue
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for b in iter(lambda: fh.read(16 << 20), b""):
                h.update(b)
        if h.hexdigest() != f["sha256"]:
            bad.append(f["file"])
    report["datasets"][d] = {{"files": len(files), "cells": sum(f["cells"] for f in files), "bad": bad}}
    print(d, len(files), "files", "bad:", bad, flush=True)
    if bad:
        raise SystemExit(f"{{d}}: shards differ from files.json: {{bad[:5]}}")
    shard_dirs.append(str(root))
report["verify_seconds"] = round(time.time() - t0, 1)
Path("/kaggle/working/verify.json").write_text(json.dumps(report, indent=1))
cmd = [sys.executable, str(CODE / "train_cellnet.py"), "--shards", *shard_dirs, "--axis", str(CODE / "gene_names.csv"),
       "--descriptors", str(CODE), "--out", "/kaggle/working/run", *ARGS]
print(" ".join(cmd), flush=True)
subprocess.run(cmd, check=True)
'''


def kaggle(args, config_dir):
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    r = subprocess.run([exe, *args], env={**os.environ, "KAGGLE_CONFIG_DIR": config_dir}, capture_output=True, text=True)
    print((r.stdout or "")[-1500:], (r.stderr or "")[-1500:])
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("code")
    c.add_argument("--config-dir", required=True)
    c.add_argument("--stage", required=True, type=Path)
    c.add_argument("--descriptors", required=True, type=Path)
    c.add_argument("--axis", required=True, type=Path)
    c.add_argument("--version-note", default=None)
    r = sub.add_parser("run")
    r.add_argument("--config-dir", required=True)
    r.add_argument("--stage", required=True, type=Path)
    r.add_argument("--run", required=True)
    r.add_argument("--datasets", nargs="+", required=True)
    r.add_argument("--train-args", nargs=argparse.REMAINDER, default=[])
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    a.stage.mkdir(parents=True)
    if a.cmd == "code":
        for f in ("cellnet.py", "cell_data.py", "train_cellnet.py"):
            shutil.copyfile(HERE / f, a.stage / f)
        shutil.copyfile(a.axis, a.stage / "gene_names.csv")
        for f in ("descriptors.npy", "genes.txt", "manifest.json"):
            shutil.copyfile(a.descriptors / f, a.stage / f)
        (a.stage / "dataset-metadata.json").write_text(json.dumps(
            {"title": "rlab cellnet code", "id": f"{OWNER}/rlab-cellnet-code", "licenses": [{"name": "other"}]}))
        if a.version_note:
            kaggle(["datasets", "version", "-p", str(a.stage), "-m", a.version_note, "--dir-mode", "skip"], a.config_dir)
        else:
            kaggle(["datasets", "create", "-p", str(a.stage), "--dir-mode", "skip"], a.config_dir)
        return
    (a.stage / "run.py").write_text(KERNEL.format(args=json.dumps(a.train_args), datasets=json.dumps(a.datasets)),
                                    encoding="utf-8")
    meta = {"id": f"{OWNER}/rlab-{a.run}", "title": f"rlab {a.run}", "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": False,
            "dataset_sources": [f"{OWNER}/rlab-cellnet-code"] + [f"{OWNER}/{d}" for d in a.datasets],
            "kernel_sources": [], "competition_sources": []}
    (a.stage / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)


if __name__ == "__main__":
    main()
