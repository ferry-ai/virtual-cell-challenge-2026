"""Run the R-LAB cell network on Kaggle, in the stages of train_cellnet.py.

Version 5 (4/10, reports/modelli/ibrido_selettivo_2026-10-04, D-056): the code dataset also carries guards.py; the
options of the D-056 network go through --train-args (PROTOCOLLO.md §4). Otherwise the launcher of version 4.

Version 4 (3/10, reports/modelli/rete_ancorata_v4_2026-10-03): --fast-kernels <slugs> mounts the outputs of the build
kernels of the compact twins (kaggle_fast.py) instead of the corpus datasets and passes --fast-roots to the training,
which checks every twin against the package manifests; --anchors-dir names the folder of the anchors kernel's output
(version 4 writes anchors_<line>_<rule>/); the code dataset also carries balanced.py and fastshard.py.

Version 3 (3/10, reports/modelli/rete_ancorata_2026-10-03): --anchors-from <slug> --anchors-line <line> mounts the
output of the anchors kernel (kaggle_anchors.py) and passes anchors_<line>/ to the training (train --anchors).

Version 2 (3/10, reports/modelli/rete_cellulare_2026-10-03): kernels and code on --owner (the GPU account,
davideferrante11), corpus datasets on --data-owner (davidmaisterx, shared with the GPU account as reader); the code
dataset also carries line_groups.json and target_keys.json, and a prepass argument written @CODE/<file> is that file
of the code dataset; arms are NAME=TARGET_CODE[/CONTEXT][@DEVICE] (train_cellnet.parse_arms), spread over the GPUs
when no device is given.

- `code`: create or version the private dataset <owner>/rlab-cellnet-code with cellnet.py, cell_data.py,
  train_cellnet.py, the official axis and the target descriptors.
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

    python kaggle_train.py code --config-dir ~/.kaggle --stage <new dir> --descriptors <dir> --axis gene_names.csv \
        --version-note "..."
    python kaggle_train.py kernel --config-dir ~/.kaggle --stage <new dir> --slug rlab-prepass-r1 --cpu \
        --datasets rlab-hepg2-nadig ... --prepass-args="--holdout-context HepG2"
    python kaggle_train.py kernel --config-dir ~/.kaggle --stage <new dir> --slug rlab-cellnet-r2 --datasets ... \
        --prepass-from rlab-prepass-r1 --arm desc=descriptors --arm ident=identity --train-args="--epochs 10 ..."
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
OWNER = "davidmaisterx"                  # version 1 default; version 2 passes --owner and --data-owner
CODE_FILES = ("cellnet.py", "cell_data.py", "train_cellnet.py", "balanced.py", "fastshard.py",    # version 4: + 2
              "guards.py")                                                         # version 5 (D-056): + guards.py
CONFIG_FILES = ("line_groups.json",)

KERNEL = r'''
import fnmatch, hashlib, json, os, platform, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
INPUT, OUT, OWNER, DATA_OWNER = Path("/kaggle/input"), Path("/kaggle/working"), {owner}, {data_owner}
CODE_SLUG = {code_slug}
DATASETS = {datasets}
GLOBS = {globs}
PREPASS_ARGS = {prepass_args}
PREPASS_FROM = {prepass_from}
ARMS = {arms}
TRAIN_ARGS = {train_args}
CYCLE = {cycle}
GPU = {gpu}
ANCHORS_FROM, ANCHORS_LINE = {anchors_from}, {anchors_line}
ANCHORS_DIR, FAST = {anchors_dir}, {fast}
t0 = time.time()


def mount(slug):
    """Where Kaggle mounted an input: /kaggle/input/<slug>, /kaggle/input/datasets/<owner>/<slug> (seen on 29/09),
    /kaggle/input/notebooks/<owner>/<slug>, or the one folder of that name below /kaggle/input."""
    for p in (INPUT / slug, INPUT / "datasets" / OWNER / slug, INPUT / "datasets" / DATA_OWNER / slug,
              INPUT / "notebooks" / OWNER / slug, INPUT / "kernels" / OWNER / slug):
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
CODE = mount(CODE_SLUG)
PREPASS_ARGS = None if PREPASS_ARGS is None else [str(CODE / a[6:]) if a.startswith("@CODE/") else a
                                                  for a in PREPASS_ARGS]
roots = {{d: mount(d) for d in DATASETS}}
report = {{"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mounts": {{d: str(r) for d, r in roots.items()}},
           "code": str(CODE), "datasets": {{}}, "bad": []}}


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


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
    raise SystemExit(f"shards differ from files.json: {{report['bad'][:5]}}")
PY, TC = sys.executable, str(CODE / "train_cellnet.py")


def run(cmd, log):
    print(" ".join(map(str, cmd)), flush=True)
    with open(OUT / log, "w") as fh:
        return subprocess.Popen(list(map(str, cmd)), stdout=fh, stderr=subprocess.STDOUT)


if PREPASS_ARGS is not None:
    if run([PY, TC, "prepass", "--shards", *shards, "--axis", CODE / "gene_names.csv", "--out", OUT / "prepass",
            *PREPASS_ARGS], "prepass.log").wait() != 0:
        raise SystemExit("prepass failed: see prepass.log")
    prepass = OUT / "prepass"
else:
    prepass = mount(PREPASS_FROM) / "prepass"
# version 3: the anchors of this line, from the output of the anchors kernel (anchors.py, checked again by the training);
# version 4: the folder is named by --anchors-dir (anchors_<line>_<rule>)
anchors = (mount(ANCHORS_FROM) / (ANCHORS_DIR or f"anchors_{{ANCHORS_LINE}}")) if ANCHORS_FROM else None
if anchors is not None and not (anchors / "manifest.json").is_file():
    raise SystemExit(f"no anchors manifest in {{anchors}}")
# training finds the shards of the prepass state by name and size below /kaggle/input and hashes them against the
# state in a background thread (train_cellnet.resolve_shards, HashCheck): the GPU does not wait on it
ARM_FLAGS = []
n_gpu = 0
if GPU:
    try:
        import torch
        n_gpu = torch.cuda.device_count()
    except ImportError:
        pass
for i, spec in enumerate(ARMS):
    # version 2: NAME=TARGET_CODE[/CONTEXT][@DEVICE]; without a device, the arms go round the GPUs
    dev = ("" if "@" in spec else "@" + (f"cuda:{{i % max(n_gpu, 1)}}" if GPU and n_gpu else "cpu"))
    ARM_FLAGS += ["--arm", spec + dev]
# version 4: with the build kernels mounted, the training reads the compact twins (--fast-roots) and checks each against
# the package manifests; otherwise it finds the h5ad shards by name and size (--shard-roots)
train = lambda out, extra=(): [PY, TC, "train", "--prepass", prepass, "--out", OUT / out, "--descriptors", CODE,
                               *(["--fast-roots", INPUT] if FAST else ["--shard-roots", INPUT]), *ARM_FLAGS,
                               *TRAIN_ARGS, *(["--anchors", anchors] if anchors else []), *extra]
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


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("code")
    c.add_argument("--config-dir", required=True)
    c.add_argument("--stage", required=True, type=Path)
    c.add_argument("--descriptors", required=True, type=Path)
    c.add_argument("--axis", required=True, type=Path)
    c.add_argument("--target-keys", type=Path, help="version 2: the JSON of target_keys.py, shipped as target_keys.json")
    c.add_argument("--version-note", default=None)
    for q in (c,):
        q.add_argument("--owner", default=OWNER)
        q.add_argument("--code-slug", default="rlab-cellnet-code")
        q.add_argument("--dry-run", action="store_true", help="stage the files, push nothing")
    k = sub.add_parser("kernel")
    k.add_argument("--config-dir", required=True)
    k.add_argument("--stage", required=True, type=Path)
    k.add_argument("--slug", required=True)
    k.add_argument("--owner", default=OWNER, help="the account of the kernel and of the code dataset")
    k.add_argument("--data-owner", default=OWNER, help="the account of the corpus datasets")
    k.add_argument("--code-slug", default="rlab-cellnet-code")
    k.add_argument("--datasets", nargs="*", default=[], help="corpus datasets (not needed with --fast-kernels)")
    k.add_argument("--glob", action="append", default=[], metavar="DATASET=PATTERN",
                   help="shards of a dataset to read (default all *.h5ad; alternatives separated by |)")
    k.add_argument("--prepass-args", default=None, help="run the prepass here with these arguments (one string)")
    k.add_argument("--prepass-from", default=None, help="kernel slug whose output holds prepass/")
    k.add_argument("--arm", action="append", default=[], metavar="NAME=TARGET_CODE",
                   help="an arm of the one training process, on the next GPU (repeatable)")
    k.add_argument("--train-args", default="", help="the training arguments every arm shares (one string)")
    k.add_argument("--cycle", nargs=2, type=int, metavar=("S1", "S2"))
    k.add_argument("--anchors-from", default=None, help="version 3: kernel slug whose output holds anchors_<line>/")
    k.add_argument("--anchors-line", default=None, help="version 3: the held-out line of the anchors")
    k.add_argument("--anchors-dir", default=None, help="version 4: the anchors folder in the kernel's output "
                                                       "(anchors_<line>_<rule>)")
    k.add_argument("--fast-kernels", nargs="*", default=[],
                   help="version 4: slugs of the build kernels whose outputs hold the compact twins")
    k.add_argument("--cpu", action="store_true", help="no GPU (no GPU quota): the prepass, or a check on few shards")
    k.add_argument("--dry-run", action="store_true", help="write the stage and compile run.py, push nothing")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    a.stage.mkdir(parents=True)
    if a.cmd == "code":
        import hashlib
        for f in CODE_FILES + CONFIG_FILES:
            shutil.copyfile(HERE / f, a.stage / f)
        shutil.copyfile(a.axis, a.stage / "gene_names.csv")
        if a.target_keys:
            shutil.copyfile(a.target_keys, a.stage / "target_keys.json")
        for f in ("descriptors.npy", "genes.txt", "manifest.json"):
            shutil.copyfile(a.descriptors / f, a.stage / f)
        (a.stage / "dataset-metadata.json").write_text(json.dumps(
            {"title": a.code_slug.replace("-", " "), "id": f"{a.owner}/{a.code_slug}", "licenses": [{"name": "other"}],
             "isPrivate": True}))
        (a.stage / "staged.json").write_text(json.dumps(
            {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.stage.iterdir())
             if p.name not in ("staged.json", "dataset-metadata.json")}, indent=1))
        if a.dry_run:
            print(f"dry run: staged {a.stage}; nothing pushed")
        elif a.version_note:
            kaggle(["datasets", "version", "-p", str(a.stage), "-m", a.version_note, "--dir-mode", "skip"], a.config_dir)
        else:
            kaggle(["datasets", "create", "-p", str(a.stage), "--dir-mode", "skip"], a.config_dir)
        return
    if (a.prepass_args is None) == (a.prepass_from is None):
        sys.exit("give either --prepass-args or --prepass-from")
    if a.cycle and not a.arm:
        sys.exit("--cycle needs an arm")
    import cellnet as CN
    for spec in a.arm:                   # NAME=TARGET_CODE[/CONTEXT][@DEVICE], as train_cellnet.parse_arms reads it
        name, sep, rest = spec.partition("=")
        code, _, ctx = rest.partition("@")[0].partition("/")
        if not sep or not name or code not in CN.TARGET_CODES or (ctx or "cells") not in CN.CONTEXT_MODES:
            sys.exit(f"--arm {spec}")
    globs = dict(x.split("=", 1) for x in a.glob)
    text = KERNEL.format(owner=repr(a.owner), data_owner=repr(a.data_owner), code_slug=repr(a.code_slug),
                         datasets=json.dumps(a.datasets), globs=json.dumps(globs),
                         prepass_args=json.dumps(shlex.split(a.prepass_args)) if a.prepass_args is not None else "None",
                         prepass_from=repr(a.prepass_from), arms=json.dumps(a.arm),
                         train_args=json.dumps(shlex.split(a.train_args)),
                         cycle=json.dumps(a.cycle) if a.cycle else "None", gpu="False" if a.cpu else "True",
                         anchors_from=repr(a.anchors_from), anchors_line=repr(a.anchors_line),
                         anchors_dir=repr(a.anchors_dir), fast=repr(bool(a.fast_kernels)))
    if bool(a.anchors_from) != bool(a.anchors_line):
        sys.exit("give --anchors-from and --anchors-line together")
    if not a.datasets and not a.fast_kernels:
        sys.exit("give the corpus --datasets or the --fast-kernels of the compact twins")
    if a.fast_kernels and a.prepass_args is not None:
        sys.exit("the prepass reads the h5ad shards: --fast-kernels serves the training only")
    (a.stage / "run.py").write_text(text, encoding="utf-8")
    meta = {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": not a.cpu, "enable_tpu": False,
            "enable_internet": False,
            "dataset_sources": [f"{a.owner}/{a.code_slug}"] + [f"{a.data_owner}/{d}" for d in a.datasets],
            "kernel_sources": ([f"{a.owner}/{a.prepass_from}"] if a.prepass_from else [])
            + ([f"{a.owner}/{a.anchors_from}"] if a.anchors_from else [])
            + [f"{a.owner}/{s}" for s in a.fast_kernels], "competition_sources": []}
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
