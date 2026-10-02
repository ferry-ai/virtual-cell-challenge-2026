"""Run the corrected R-LEAD cell network on Kaggle from the teammate's account, in the stages of train_cellnet.py.

Copy of reports/modelli/risposta_biologica_2026-09-30/kaggle_train.py (commit 1f086cb) with four changes:
- two owners: the code dataset and the kernels belong to --owner (the account whose token runs the CLI); the shard
  datasets and the assets (official axis, target descriptors) stay with --data-owner (davidmaisterx), shared with
  --owner, and are attached read-only. The original pushed everything as davidmaisterx;
- the code dataset is <owner>/rlead-cellnet-code and holds only this folder's cellnet.py, cell_data.py and
  train_cellnet.py with their sha256 (code_manifest.json): the original uploaded its own, uncorrected copies;
- the axis and the descriptors are read from the data owner's rlab-cellnet-code (--assets), never re-uploaded;
- the arm `generic` (step A) is accepted.

- `code`: create or version the private dataset <owner>/rlead-cellnet-code.
- `kernel`: push a private kernel without internet (everything it reads is attached) that
  1. verifies the shards it will read against the sha256 and bytes of each dataset's files.json (published by
     publish_kaggle.py), four files at a time;
  2. runs the prepass on CPU when --prepass-args is given (no GPU quota: use --cpu), or reads the prepass state from
     the output of an earlier kernel (--prepass-from);
  3. runs one training process whose arms (--arm NAME=TARGET_CODE, one per GPU: cuda:0, cuda:1) share the batch
     stream, the loader processes, the budget and the checkpoints (1/10, incident E-20261001-001: one process per arm
     read every shard twice and filled the memory);
  4. with --cycle S1 S2: a run stopped at step S1 and resumed to S2 must end in the state of a run straight to S2, for
     every arm (resume_check.json); then the training runs to its end and is evaluated.
  Outputs stay in /kaggle/working: verify.json, prepass/, train/ (one folder per arm inside), the logs.

    python kaggle_train.py code --config-dir ~/.kaggle --owner <you> --stage <new dir> [--version-note "..."]
    python kaggle_train.py kernel --config-dir ~/.kaggle --owner <you> --stage <new dir> --slug rlead-prepass-r1 \
        --cpu --datasets rlab-hepg2-nadig ... --prepass-args="--holdout-context HepG2"
    python kaggle_train.py kernel --config-dir ~/.kaggle --owner <you> --stage <new dir> --slug rlead-cellnet-r1 \
        --datasets ... --prepass-from rlead-prepass-r1 --arm desc=descriptors --arm gen=generic --train-args="..."
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_OWNER = "davidmaisterx"
CODE_SLUG, ASSETS_SLUG = "rlead-cellnet-code", "rlab-cellnet-code"
CODE_FILES = ("cellnet.py", "cell_data.py", "train_cellnet.py")
ARM_CODES = ("descriptors", "identity", "both", "generic")

KERNEL = r'''
import fnmatch, hashlib, json, os, platform, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
OWNERS = {owners}
CODE_SLUG, ASSETS_SLUG = {code_slug}, {assets_slug}
DATASETS = {datasets}
GLOBS = {globs}
PREPASS_ARGS = {prepass_args}
PREPASS_FROM = {prepass_from}
ARMS = {arms}
TRAIN_ARGS = {train_args}
CYCLE = {cycle}
GPU = {gpu}
t0 = time.time()


def mount(slug):
    """Where Kaggle mounted an input: /kaggle/input/<slug>, /kaggle/input/datasets/<owner>/<slug> (seen on 29/09),
    /kaggle/input/notebooks/<owner>/<slug>, for either owner, or the one folder of that name below /kaggle/input."""
    for p in [INPUT / slug] + [INPUT / kind / o / slug for o in OWNERS for kind in ("datasets", "notebooks", "kernels")]:
        if p.is_dir():
            return p
    hits = [p for p in INPUT.glob(f"**/{{slug}}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{{slug}}: {{len(hits)}} mounts below {{INPUT}}: {{hits[:3]}}")
    return hits[0]


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()


env = {{"python": sys.version.split()[0], "cpus": os.cpu_count(), "platform": platform.platform(),
        "gpus": sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader"), "memory": sh("free -m"),
        "disk": sh("df -h /kaggle/working | tail -1"), "input_tree": sh("find /kaggle/input -maxdepth 4 -type d | head -40")}}
try:
    import torch
    env["torch"], env["cuda"] = torch.__version__, torch.cuda.is_available()
except ImportError:
    pass
(OUT / "env.json").write_text(json.dumps(env, indent=1))
if GPU and not env.get("cuda"):
    # 2/10: rlead-training-r1 v1 asked for a GPU and got a CPU-only runtime (torch +cpu, no nvidia-smi); the
    # training died on its first CUDA tensor and the cycle check then on a missing checkpoint
    raise SystemExit(f"a GPU was asked for and this runtime has none: torch {{env.get('torch')}}, {{env['gpus']}}")
CODE, ASSETS = mount(CODE_SLUG), mount(ASSETS_SLUG)
roots = {{d: mount(d) for d in DATASETS}}
report = {{"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mounts": {{d: str(r) for d, r in roots.items()}},
           "code": str(CODE), "assets": str(ASSETS), "datasets": {{}}, "bad": []}}


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


code_manifest = json.loads((CODE / "code_manifest.json").read_text())
report["code_files"] = code_manifest["files"]
report["bad"] += [f"{{CODE_SLUG}}/{{f}}" for f, h in code_manifest["files"].items() if digest(CODE / f) != h]
chosen = {{}}
for d, root in roots.items():
    files = json.loads((root / "files.json").read_text())
    # a pattern may hold alternatives separated by "|" (1/10: the units of one dataset kept apart from the others)
    chosen[d] = [f for f in files if any(fnmatch.fnmatch(f["file"], p) for p in GLOBS.get(d, "*.h5ad").split("|"))]
    report["datasets"][d] = {{"files": len(files), "chosen": len(chosen[d]), "cells": sum(f["cells"] for f in chosen[d])}}
shards = [str(roots[d] / f["file"]) for d in DATASETS for f in chosen[d]]
if PREPASS_ARGS is not None:
    # the prepass reads every chosen shard: hash them all against files.json first (CPU, no GPU quota at stake)
    for d, root in roots.items():
        with ThreadPoolExecutor(4) as ex:
            got = list(ex.map(lambda f: ((root / f["file"]).stat().st_size if (root / f["file"]).is_file() else -1,
                                         digest(root / f["file"]) if (root / f["file"]).is_file() else None), chosen[d]))
        report["bad"] += [f"{{d}}/{{f['file']}}" for f, (size, h) in zip(chosen[d], got)
                          if size != f["bytes"] or h != f["sha256"]]
    report["verify_seconds"] = round(time.time() - t0, 1)
(OUT / "verify.json").write_text(json.dumps(report, indent=1))
if report["bad"]:
    raise SystemExit(f"code or shards differ from their manifests: {{report['bad'][:5]}}")
PY, TC = sys.executable, str(CODE / "train_cellnet.py")


def run(cmd, log):
    print(" ".join(map(str, cmd)), flush=True)
    with open(OUT / log, "w") as fh:
        return subprocess.Popen(list(map(str, cmd)), stdout=fh, stderr=subprocess.STDOUT)


if PREPASS_ARGS is not None:
    if run([PY, TC, "prepass", "--shards", *shards, "--axis", ASSETS / "gene_names.csv", "--out", OUT / "prepass",
            *PREPASS_ARGS], "prepass.log").wait() != 0:
        raise SystemExit("prepass failed: see prepass.log")
    prepass = OUT / "prepass"
else:
    prepass = mount(PREPASS_FROM) / "prepass"
# training finds the shards of the prepass state by name and size below /kaggle/input and hashes them against the
# state in a background thread (train_cellnet.resolve_shards, HashCheck): the GPU does not wait on it
ARM_FLAGS = []
for i, (name, code) in enumerate(ARMS):
    ARM_FLAGS += ["--arm", f"{{name}}={{code}}@" + (f"cuda:{{i}}" if GPU else "cpu")]
train = lambda out, extra=(): [PY, TC, "train", "--prepass", prepass, "--out", OUT / out,
                               *(["--descriptors", ASSETS] if (ASSETS / "descriptors.npy").is_file() else []),
                               "--shard-roots", INPUT, *ARM_FLAGS, *TRAIN_ARGS, *extra]
if CYCLE:
    s1, s2 = CYCLE
    checks = {{"arms": ARM_FLAGS, "steps": [s1, s2]}}
    for tag, extra in (("ref", ["--stop-after-steps", s2]), ("a", ["--stop-after-steps", s1]),
                       ("b", ["--resume", OUT / "cycle_a", "--stop-after-steps", s2])):
        # the short runs of the cycle skip the shard hashes: the training that follows checks them
        checks[f"rc_{{tag}}"] = run(train(f"cycle_{{tag}}", list(map(str, extra)) + ["--no-verify"]),
                                   f"cycle_{{tag}}.log").wait()
    import torch
    ref = torch.load(OUT / "cycle_ref" / "checkpoints" / f"ckpt_{{s2:07d}}.pt", map_location="cpu", weights_only=False)
    res = torch.load(OUT / "cycle_b" / "checkpoints" / f"ckpt_{{s2:07d}}.pt", map_location="cpu", weights_only=False)
    pairs = [(ref["models"][m][k], res["models"][m][k]) for m in ref["models"] for k in ref["models"][m]]
    diff = max(float((u.float() - v.float()).abs().max()) for u, v in pairs)
    scale = max(float(u.float().abs().max()) for u, _ in pairs)
    checks.update({{"batch_chain_equal": ref["batch_chain"] == res["batch_chain"],
                   "seen_equal": bool((ref["seen"] == res["seen"]).all()), "draws_equal": ref["draws"] == res["draws"],
                   "n_drawn_equal": ref["n_drawn"] == res["n_drawn"],
                   "models_compared": sorted(ref["models"]), "model_max_abs_diff": diff, "model_max_abs": scale,
                   "model_equal": all(torch.equal(u, v) for u, v in pairs),
                   "rule": "the data sequence must be equal; parameters within 1e-5 of the largest parameter on CPU "
                           "(sums over several threads: cycle r2 of 1/10 differed by 7.2e-7 on 74.5) and within 1e-3 "
                           "on GPU (atomic sums are not deterministic)"}})
    checks["passed"] = (checks["batch_chain_equal"] and checks["seen_equal"] and checks["draws_equal"]
                        and checks["n_drawn_equal"] and diff <= (1e-3 if GPU else 1e-5) * scale)
    (OUT / "resume_check.json").write_text(json.dumps(checks, indent=1, default=str))
    print("resume check", checks, flush=True)
    if not checks["passed"]:
        raise SystemExit("the resume check failed: see resume_check.json")
code = run(train("train"), "train.log").wait() if ARMS else None      # a prepass kernel trains nothing
(OUT / "kernel_done.json").write_text(json.dumps({{"arms": ARMS, "return_code": code,
                                                   "seconds": round(time.time() - t0, 1)}}, indent=1))
if code:
    raise SystemExit(f"the training failed with code {{code}}: see train.log")
'''


def kaggle(args, config_dir):
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    r = subprocess.run([exe, *args], env={**os.environ, "KAGGLE_CONFIG_DIR": config_dir}, capture_output=True, text=True)
    print((r.stdout or "")[-1500:], (r.stderr or "")[-1500:])
    return r


def code_manifest():
    """sha256 and bytes of the files the code dataset carries: the kernel checks them before it runs anything."""
    files = {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in CODE_FILES}
    return {"what": "the corrected R-LEAD network, reports/modelli/cellnet_rlead_2026-10-01", "files": files,
            "bytes": {f: (HERE / f).stat().st_size for f in CODE_FILES}}


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config-dir", required=True, help="the folder of the Kaggle credentials of --owner")
    common.add_argument("--owner", required=True, help="the Kaggle account that owns the code dataset and kernels")
    common.add_argument("--data-owner", default=DATA_OWNER, help="the account that shares the shards and assets")
    common.add_argument("--stage", required=True, type=Path)
    common.add_argument("--dry-run", action="store_true", help="write the stage (and compile run.py), push nothing")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("code", parents=[common])
    c.add_argument("--version-note", default=None)
    k = sub.add_parser("kernel", parents=[common])
    k.add_argument("--slug", required=True)
    k.add_argument("--assets", default=ASSETS_SLUG, help="dataset with gene_names.csv (and the descriptors, if any)")
    k.add_argument("--assets-owner", default=None, help="owner of --assets (default: --data-owner)")
    k.add_argument("--datasets", nargs="+", required=True)
    k.add_argument("--glob", action="append", default=[], metavar="DATASET=PATTERN",
                   help="shards of a dataset to read (default all *.h5ad; alternatives separated by |)")
    k.add_argument("--prepass-args", default=None, help="run the prepass here with these arguments (one string)")
    k.add_argument("--prepass-from", default=None, help="kernel slug of --owner whose output holds prepass/")
    k.add_argument("--arm", action="append", default=[], metavar="NAME=TARGET_CODE",
                   help="an arm of the one training process, on the next GPU (repeatable)")
    k.add_argument("--train-args", default="", help="the training arguments every arm shares (one string)")
    k.add_argument("--cycle", nargs=2, type=int, metavar=("S1", "S2"))
    k.add_argument("--cpu", action="store_true", help="no GPU (no GPU quota): the prepass, or a check on few shards")
    a = p.parse_args()
    if a.owner == a.data_owner:
        sys.exit("--owner is the account of the token running the CLI, not the data owner")
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    a.stage.mkdir(parents=True)
    if a.cmd == "code":
        for f in CODE_FILES:
            shutil.copyfile(HERE / f, a.stage / f)
        (a.stage / "code_manifest.json").write_text(json.dumps(code_manifest(), indent=1))
        (a.stage / "dataset-metadata.json").write_text(json.dumps(
            {"title": "rlead cellnet code", "id": f"{a.owner}/{CODE_SLUG}", "licenses": [{"name": "other"}]}))
        if a.dry_run:
            print(f"dry run: {a.stage} written; nothing pushed")
        elif a.version_note:
            kaggle(["datasets", "version", "-p", str(a.stage), "-m", a.version_note, "--dir-mode", "skip"], a.config_dir)
        else:
            kaggle(["datasets", "create", "-p", str(a.stage), "--dir-mode", "skip"], a.config_dir)
        return
    if (a.prepass_args is None) == (a.prepass_from is None):
        sys.exit("give either --prepass-args or --prepass-from")
    if a.cycle and not a.arm:
        sys.exit("--cycle needs an arm")
    arms = [x.split("=", 1) for x in a.arm]
    if any(len(x) != 2 or x[1] not in ARM_CODES for x in arms):
        sys.exit("--arm NAME=" + "|".join(ARM_CODES))
    globs = dict(x.split("=", 1) for x in a.glob)
    text = KERNEL.format(owners=repr([a.owner, a.data_owner]), code_slug=repr(CODE_SLUG), assets_slug=repr(a.assets),
                         datasets=json.dumps(a.datasets), globs=json.dumps(globs),
                         prepass_args=json.dumps(shlex.split(a.prepass_args)) if a.prepass_args is not None else "None",
                         prepass_from=repr(a.prepass_from), arms=json.dumps(arms),
                         train_args=json.dumps(shlex.split(a.train_args)),
                         cycle=json.dumps(a.cycle) if a.cycle else "None", gpu="False" if a.cpu else "True")
    (a.stage / "run.py").write_text(text, encoding="utf-8")
    meta = {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": not a.cpu, "enable_tpu": False,
            "enable_internet": False,
            "dataset_sources": [f"{a.owner}/{CODE_SLUG}", f"{a.assets_owner or a.data_owner}/{a.assets}"]
                               + [f"{a.data_owner}/{d}" for d in a.datasets],
            "kernel_sources": [f"{a.owner}/{a.prepass_from}"] if a.prepass_from else [], "competition_sources": []}
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
