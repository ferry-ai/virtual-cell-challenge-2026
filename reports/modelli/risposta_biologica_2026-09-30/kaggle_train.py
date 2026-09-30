"""Run the R-LAB cell network on Kaggle (account with GPU: davidmaisterx), in the stages of train_cellnet.py.

- `code`: create or version the private dataset <owner>/rlab-cellnet-code with cellnet.py, cell_data.py,
  train_cellnet.py, the official axis and the target descriptors.
- `kernel`: push a private kernel without internet (everything it reads is attached) that
  1. verifies the shards it will read against the sha256 and bytes of each dataset's files.json (published by
     publish_kaggle.py), four files at a time;
  2. runs the prepass on CPU when --prepass-args is given (no GPU quota: use --cpu), or reads the prepass state from
     the output of an earlier kernel (--prepass-from);
  3. runs the training arms at once, one per GPU (cuda:0, cuda:1), each with its own budget and checkpoints;
  4. with --cycle S1 S2 (a check on few shards): an arm stopped at step S1 and resumed to S2 must end in the state of
     an arm run straight to S2 (resume_check.json), then the first arm is trained to its end and evaluated.
  Outputs stay in /kaggle/working: verify.json, prepass/, one folder per arm, their logs.

    python kaggle_train.py code --config-dir ~/.kaggle --stage <new dir> --descriptors <dir> --axis gene_names.csv \
        --version-note "..."
    python kaggle_train.py kernel --config-dir ~/.kaggle --stage <new dir> --slug rlab-prepass-r1 --cpu \
        --datasets rlab-hepg2-nadig ... --prepass-args="--holdout-context HepG2"
    python kaggle_train.py kernel --config-dir ~/.kaggle --stage <new dir> --slug rlab-cellnet-r1 --datasets ... \
        --prepass-from rlab-prepass-r1 --arm desc="--target-code descriptors ..." --arm ident="--target-code identity ..."
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWNER = "davidmaisterx"
CODE_FILES = ("cellnet.py", "cell_data.py", "train_cellnet.py")

KERNEL = r'''
import fnmatch, hashlib, json, os, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
CODE = Path("/kaggle/input/rlab-cellnet-code")
OUT = Path("/kaggle/working")
DATASETS = {datasets}
GLOBS = {globs}
PREPASS_ARGS = {prepass_args}
PREPASS_FROM = {prepass_from}
ARMS = {arms}
CYCLE = {cycle}
GPU = {gpu}
t0 = time.time()
report = {{"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "datasets": {{}}, "bad": []}}


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


chosen = {{}}
for d in DATASETS:
    root = Path("/kaggle/input") / d
    files = json.loads((root / "files.json").read_text())
    chosen[d] = [f for f in files if fnmatch.fnmatch(f["file"], GLOBS.get(d, "*.h5ad"))]
    report["datasets"][d] = {{"files": len(files), "chosen": len(chosen[d]),
                              "cells": sum(f["cells"] for f in chosen[d])}}
shards = [str(Path("/kaggle/input") / d / f["file"]) for d in DATASETS for f in chosen[d]]


def verify():
    """Every chosen shard against the bytes and sha256 of its files.json, four at a time."""
    for d in DATASETS:
        root = Path("/kaggle/input") / d
        with ThreadPoolExecutor(4) as ex:
            got = list(ex.map(lambda f: ((root / f["file"]).stat().st_size if (root / f["file"]).is_file() else -1,
                                         digest(root / f["file"]) if (root / f["file"]).is_file() else None), chosen[d]))
        report["bad"] += [f"{{d}}/{{f['file']}}" for f, (size, h) in zip(chosen[d], got)
                          if size != f["bytes"] or h != f["sha256"]]
    report["verify_seconds"] = round(time.time() - t0, 1)
    report["verified"] = not report["bad"]
    (OUT / "verify.json").write_text(json.dumps(report, indent=1))


if GPU and PREPASS_ARGS is None:      # the GPU does not wait: shards are hashed while the arms start
    checker = threading.Thread(target=verify)
    checker.start()
else:                                  # CPU kernels hash before reading anything
    checker = None
    verify()
    if report["bad"]:
        raise SystemExit(f"shards differ from files.json: {{report['bad'][:5]}}")
PY, TC = sys.executable, str(CODE / "train_cellnet.py")


def run(cmd, log):
    print(" ".join(map(str, cmd)), flush=True)
    with open(OUT / log, "w") as fh:
        return subprocess.Popen(list(map(str, cmd)), stdout=fh, stderr=subprocess.STDOUT)


if PREPASS_ARGS is not None:
    p = run([PY, TC, "prepass", "--shards", *shards, "--axis", CODE / "gene_names.csv", "--out", OUT / "prepass",
             *PREPASS_ARGS], "prepass.log")
    if p.wait() != 0:
        raise SystemExit("prepass failed: see prepass.log")
    prepass = OUT / "prepass"
else:
    prepass = Path("/kaggle/input") / PREPASS_FROM / "prepass"
train = lambda name, args, dev: [PY, TC, "train", "--prepass", prepass, "--out", OUT / name, "--descriptors", CODE,
                                 "--device", dev, *args]
if CYCLE:
    s1, s2 = CYCLE
    name, args = ARMS[0]
    dev = "cuda:0" if GPU else "cpu"
    checks = {{}}
    for tag, extra in (("ref", ["--stop-after-steps", s2]), ("a", ["--stop-after-steps", s1]),
                       ("b", ["--resume", OUT / f"{{name}}_cycle_a", "--stop-after-steps", s2])):
        rc = run(train(f"{{name}}_cycle_{{tag}}", args, dev) + list(map(str, extra)), f"{{name}}_cycle_{{tag}}.log").wait()
        checks[tag] = rc
    import torch
    ref = torch.load(OUT / f"{{name}}_cycle_ref" / "checkpoints" / f"ckpt_{{s2:07d}}.pt", weights_only=False)
    res = torch.load(OUT / f"{{name}}_cycle_b" / "checkpoints" / f"ckpt_{{s2:07d}}.pt", weights_only=False)
    checks["model_equal"] = all(torch.equal(ref["model"][k], res["model"][k]) for k in ref["model"])
    checks["optimizer_equal"] = all(torch.equal(ref["opt"]["state"][k]["exp_avg"], res["opt"]["state"][k]["exp_avg"])
                                    for k in ref["opt"]["state"])
    checks["seen_equal"] = bool((ref["seen"] == res["seen"]).all())
    checks["draws_equal"] = ref["draws"] == res["draws"]
    (OUT / "resume_check.json").write_text(json.dumps(checks, indent=1, default=str))
    print("resume check", checks, flush=True)
procs = [run(train(name, args, f"cuda:{{i}}" if GPU else "cpu"), f"{{name}}.log") for i, (name, args) in enumerate(ARMS)]
stopped = False
while any(p.poll() is None for p in procs):
    if checker is not None and not checker.is_alive() and report["bad"] and not stopped:
        for p in procs:
            p.terminate()
        stopped = True
    time.sleep(10)
if checker is not None:
    checker.join()
codes = [p.wait() for p in procs]
(OUT / "kernel_done.json").write_text(json.dumps({{"arms": [a[0] for a in ARMS], "return_codes": codes,
                                                   "verified": not report["bad"], "stopped_for_bad_shards": stopped,
                                                   "seconds": round(time.time() - t0, 1)}}, indent=1))
if report["bad"]:
    raise SystemExit(f"shards differ from files.json: {{report['bad'][:5]}}")
if any(codes):
    raise SystemExit(f"an arm failed: {{codes}}")
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
    k = sub.add_parser("kernel")
    k.add_argument("--config-dir", required=True)
    k.add_argument("--stage", required=True, type=Path)
    k.add_argument("--slug", required=True)
    k.add_argument("--datasets", nargs="+", required=True)
    k.add_argument("--glob", action="append", default=[], metavar="DATASET=PATTERN",
                   help="shards of a dataset to read (default all *.h5ad)")
    k.add_argument("--prepass-args", default=None, help="run the prepass here with these arguments (one string)")
    k.add_argument("--prepass-from", default=None, help="kernel slug whose output holds prepass/")
    k.add_argument("--arm", action="append", default=[], metavar="NAME=ARGS", help="a training arm (one string)")
    k.add_argument("--cycle", nargs=2, type=int, metavar=("S1", "S2"))
    k.add_argument("--cpu", action="store_true", help="no GPU (no GPU quota): the prepass, or a check on few shards")
    k.add_argument("--dry-run", action="store_true", help="write the stage and compile run.py, push nothing")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    a.stage.mkdir(parents=True)
    if a.cmd == "code":
        for f in CODE_FILES:
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
    if (a.prepass_args is None) == (a.prepass_from is None):
        sys.exit("give either --prepass-args or --prepass-from")
    if a.cycle and not a.arm:
        sys.exit("--cycle needs an arm")
    arms = [[x.split("=", 1)[0], shlex.split(x.split("=", 1)[1])] for x in a.arm]
    globs = dict(x.split("=", 1) for x in a.glob)
    text = KERNEL.format(datasets=json.dumps(a.datasets), globs=json.dumps(globs),
                         prepass_args=json.dumps(shlex.split(a.prepass_args)) if a.prepass_args is not None else "None",
                         prepass_from=repr(a.prepass_from), arms=json.dumps(arms),
                         cycle=json.dumps(a.cycle) if a.cycle else "None", gpu="False" if a.cpu else "True")
    (a.stage / "run.py").write_text(text, encoding="utf-8")
    meta = {"id": f"{OWNER}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": not a.cpu, "enable_tpu": False,
            "enable_internet": False,
            "dataset_sources": [f"{OWNER}/rlab-cellnet-code"] + [f"{OWNER}/{d}" for d in a.datasets],
            "kernel_sources": [f"{OWNER}/{a.prepass_from}"] if a.prepass_from else [], "competition_sources": []}
    if not a.cpu:
        meta["machine_shape"] = "NvidiaTeslaT4"
    (a.stage / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    compile(text, "run.py", "exec")
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed")
        return
    kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)


if __name__ == "__main__":
    main()
