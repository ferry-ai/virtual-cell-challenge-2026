"""Kaggle CPU kernels that build the compact twins of the corpus (build_fast.py), no GPU quota.

Why Kaggle CPU and not Colab (CLAUDE.md prefers Colab for CPU work): the 365 shards (53.3 GB) are Kaggle datasets of
davidmaisterx, and the twins are read by Kaggle GPU kernels, which mount kernel outputs directly. On Kaggle nothing is
transferred; on Colab the 53 GB would cross Drive twice.

- `data`: stage (and create) the private dataset <owner>/<code-slug> with fastshard.py, build_fast.py, cell_data.py
  and the H1 run's coverage.json (for the reconstruction of version 3's epoch sampler).
- `kernel`: a private kernel without internet mounting some corpus datasets (and, with --reconstruct, the H1 prepass
  kernel), running build_fast.py into /kaggle/working/twins.

    python kaggle_fast.py data --config-dir <dir> --owner davideferrante11 --stage <new dir> --coverage <json>
    python kaggle_fast.py kernel --config-dir <dir> --owner davideferrante11 --stage <new dir> --slug rcell-v4-fast-a-r1 \
        --datasets rlab-k562-gwps-r3 rlab-rpe1-r2 rlab-kolf-small [--glob DS=PATTERN] [--reconstruct]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ("fastshard.py", "build_fast.py", "cell_data.py")

KERNEL = r'''
import json, os, platform, subprocess, sys, time
from pathlib import Path
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
DATASETS, GLOBS, CODE_SLUG, RECONSTRUCT = {datasets}, {globs}, {code_slug}, {reconstruct}
t0 = time.time()


def mount(slug):
    for p in (INPUT / slug, INPUT / "datasets" / "davideferrante11" / slug, INPUT / "datasets" / "davidmaisterx" / slug,
              INPUT / "notebooks" / "davideferrante11" / slug, INPUT / "kernels" / "davideferrante11" / slug):
        if p.is_dir():
            return p
    hits = [p for p in INPUT.glob(f"**/{{slug}}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{{slug}}: {{len(hits)}} mounts: {{hits[:3]}}")
    return hits[0]


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()


env = {{"python": sys.version.split()[0], "cpus": os.cpu_count(), "platform": platform.platform(),
        "memory": sh("free -m"), "disk": sh("df -h /kaggle/working | tail -1"),
        "input_tree": sh("find /kaggle/input -maxdepth 4 -type d | head -40")}}
try:
    import pyarrow
    env["pyarrow"] = pyarrow.__version__
except ImportError as e:
    env["pyarrow"] = repr(e)
(OUT / "env.json").write_text(json.dumps(env, indent=1))
CODE = mount(CODE_SLUG)
cmd = [sys.executable, str(CODE / "build_fast.py"), "--input", str(INPUT), "--datasets", *DATASETS,
       "--out", str(OUT / "twins"), "--workers", str(os.cpu_count() or 1)]
for d, g in GLOBS.items():
    cmd += ["--glob", f"{{d}}={{g}}"]
if RECONSTRUCT:
    cmd += ["--reconstruct-prepass", str(mount("rcell-prepass-h1-r1") / "prepass"),
            "--reconstruct-receipt", str(CODE / "coverage_h1_r1.json")]
print(" ".join(cmd), flush=True)
with open(OUT / "build.log", "w") as fh:
    code = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode
(OUT / "kernel_done.json").write_text(json.dumps({{"return_code": code, "seconds": round(time.time() - t0, 1)}}))
if code:
    raise SystemExit(f"build failed with code {{code}}: see build.log")
'''


def kaggle(args, config_dir):
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    r = subprocess.run([exe, *args], env={**os.environ, "KAGGLE_CONFIG_DIR": config_dir}, capture_output=True, text=True)
    print((r.stdout or "")[-1500:], (r.stderr or "")[-1500:])
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("data")
    k = sub.add_parser("kernel")
    for q in (d, k):
        q.add_argument("--config-dir", required=True)
        q.add_argument("--owner", required=True)
        q.add_argument("--stage", type=Path, required=True)
        q.add_argument("--code-slug", default="rcell-v4-build-r1")
        q.add_argument("--dry-run", action="store_true")
    d.add_argument("--coverage", type=Path, required=True, help="train/coverage.json of rcell-anchored-train-h1-r1")
    k.add_argument("--slug", required=True)
    k.add_argument("--datasets", nargs="+", required=True)
    k.add_argument("--data-owner", default="davidmaisterx")
    k.add_argument("--glob", action="append", default=[], metavar="DATASET=PATTERN")
    k.add_argument("--reconstruct", action="store_true", help="also mount rcell-prepass-h1-r1 and replay version 3")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    a.stage.mkdir(parents=True)
    if a.cmd == "data":
        for f in FILES:
            shutil.copyfile(HERE / f, a.stage / f)
        shutil.copyfile(a.coverage, a.stage / "coverage_h1_r1.json")
        (a.stage / "dataset-metadata.json").write_text(json.dumps(
            {"title": a.code_slug.replace("-", " "), "id": f"{a.owner}/{a.code_slug}", "licenses": [{"name": "other"}],
             "isPrivate": True}))
        (a.stage / "staged.json").write_text(json.dumps(
            {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(a.stage.iterdir())
             if f.name not in ("staged.json", "dataset-metadata.json")}, indent=1))
        if a.dry_run:
            print(f"dry run: staged {a.stage}; nothing pushed")
            return
        kaggle(["datasets", "create", "-p", str(a.stage), "--dir-mode", "skip"], a.config_dir)
        return
    globs = dict(x.split("=", 1) for x in a.glob)
    text = KERNEL.format(datasets=json.dumps(a.datasets), globs=json.dumps(globs), code_slug=repr(a.code_slug),
                         reconstruct=repr(bool(a.reconstruct)))
    compile(text, "run.py", "exec")
    (a.stage / "run.py").write_text(text, encoding="utf-8")
    meta = {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False,
            "dataset_sources": [f"{a.owner}/{a.code_slug}"] + [f"{a.data_owner}/{x}" for x in a.datasets],
            "kernel_sources": [f"{a.owner}/rcell-prepass-h1-r1"] if a.reconstruct else [], "competition_sources": []}
    (a.stage / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed")
        return
    kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)


if __name__ == "__main__":
    main()
