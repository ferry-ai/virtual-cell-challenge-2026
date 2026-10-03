"""Kaggle kernel of lane B (PROTOCOLLO.md §5): after a pilot training, choose the held-out line's targets by rule and
generate the cells of every arm where the model and the prepass state already are (CPU, no GPU quota).

- `data`: stage (and create) the private dataset <owner>/rcell-gen-r1 with generate_cells.py, choose_targets.py and
  the cellnet.py / cell_data.py they import (the same bytes as the code dataset of the trainings).
- `kernel`: a kernel reading the training's output (train/<arm>/model.pt, train/eval_groups.json), the prepass state,
  the code dataset (descriptors, target keys) and the bench cube's row tables; writes targets.json, cells_<arm>.npz
  and their sidecars to /kaggle/working.

    python kaggle_gen.py data --config-dir <dir> --owner davideferrante11 --stage <new dir>
    python kaggle_gen.py kernel --config-dir <dir> --owner davideferrante11 --stage <new dir> --held-group HepG2
        --train-kernel rcell-train-hepg2-r1 --prepass-kernel rcell-prepass-hepg2-r1 --slug rcell-gen-hepg2-r1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# version 3: train_cellnet.py too (generate_cells.py loads and checks the anchors with its load_anchors)
FILES = ("generate_cells.py", "choose_targets.py", "extract_cells.py", "cellnet.py", "cell_data.py", "train_cellnet.py")

KERNEL = r'''
import json, os, subprocess, sys, time
from pathlib import Path
INPUT, OUT, OWNER = Path("/kaggle/input"), Path("/kaggle/working"), {owner}
HELD, ARMS, N, TARGETS = {held}, {arms}, {n}, {targets}
t0 = time.time()


def mount(slug):
    for p in (INPUT / slug, INPUT / "datasets" / OWNER / slug, INPUT / "notebooks" / OWNER / slug,
              INPUT / "kernels" / OWNER / slug, INPUT / "datasets" / "davidmaisterx" / slug):
        if p.is_dir():
            return p
    hits = [p for p in INPUT.glob(f"**/{{slug}}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{{slug}}: {{len(hits)}} mounts: {{hits[:3]}}")
    return hits[0]


GEN, CODE, CUBE = mount({gen_slug}), mount({code_slug}), mount("rlead-bench-cube-r2")
TRAIN, PRE = mount({train_kernel}) / "train", mount({prepass_kernel}) / "prepass"
# version 3: the anchors the arms were trained with (anchors kernel output), passed to the generator
ANCHORS = mount({anchors_kernel}) / f"anchors_{{HELD}}" if {anchors_kernel} else None
cube = OUT / "cube_rows"
cube.mkdir()
(cube / "manifest.json").write_bytes((CUBE / "cube__manifest.json").read_bytes())
for f in CUBE.glob("cube__*__rows.csv"):
    table = f.name[len("cube__"):-len("__rows.csv")]
    (cube / table).mkdir()
    (cube / table / "rows.csv").write_bytes(f.read_bytes())
log = {{"mounts": {{"gen": str(GEN), "code": str(CODE), "cube": str(CUBE), "train": str(TRAIN), "prepass": str(PRE)}}}}


def run(args, name):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
    (OUT / f"{{name}}.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr[-20000:])
    log[name] = {{"returncode": r.returncode, "seconds": round(time.time() - t0, 1)}}
    print(json.dumps({{name: log[name]}}), flush=True)
    return r.returncode == 0


ok = run([GEN / "choose_targets.py", "--eval-groups", TRAIN / "eval_groups.json", "--cube", cube, "--target-keys",
          CODE / "target_keys.json", "--held-group", HELD, "--targets", TARGETS, "--out", OUT / "targets.json"], "choose")
if ok:
    # the real cells of the same targets and the key's controls, for the six members computed elsewhere
    run([GEN / "extract_cells.py", "--prepass", PRE, "--targets", OUT / "targets.json", "--shard-roots", INPUT,
         "--cap", 64, "--max-controls", 2048, "--seed", 2026, "--out", OUT / "real_cells.npz"], "extract")
    for arm in ARMS:
        run([GEN / "generate_cells.py", "--prepass", PRE, "--arm-dir", TRAIN / arm, "--descriptors", CODE,
             "--targets", OUT / "targets.json", "--n", N, "--out", OUT / f"cells_{{arm}}.npz",
             *(["--anchors", ANCHORS] if ANCHORS else [])], f"generate_{{arm}}")
import shutil
shutil.rmtree(cube, ignore_errors=True)
(OUT / "gen_done.json").write_text(json.dumps(log, indent=1))
'''


def kaggle(args, config_dir):
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    import os
    r = subprocess.run([exe, *args], env={**os.environ, "KAGGLE_CONFIG_DIR": config_dir}, capture_output=True, text=True)
    print((r.stdout or "")[-1500:], (r.stderr or "")[-1500:])
    return r


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("data")
    k = sub.add_parser("kernel")
    for q in (d, k):
        q.add_argument("--config-dir", required=True)
        q.add_argument("--owner", required=True)
        q.add_argument("--stage", type=Path, required=True)
        q.add_argument("--dry-run", action="store_true")
    k.add_argument("--held-group", required=True)
    k.add_argument("--train-kernel", required=True)
    k.add_argument("--prepass-kernel", required=True)
    k.add_argument("--slug", required=True)
    k.add_argument("--code-slug", default="rcell-code-r1")
    k.add_argument("--arms", nargs="+", default=["cells", "mean", "generic"])
    k.add_argument("--n", type=int, default=32)
    k.add_argument("--targets", type=int, default=150)
    k.add_argument("--data-owner", default="davidmaisterx")
    k.add_argument("--shard-datasets", nargs="+", required=True, help="the corpus datasets of the held-out line")
    k.add_argument("--anchors-kernel", default=None, help="version 3: kernel slug whose output holds anchors_<line>/")
    for q in (d, k):
        q.add_argument("--gen-slug", default="rcell-gen-r1", help="the dataset of the generation code")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    a.stage.mkdir(parents=True)
    if a.cmd == "data":
        for f in FILES:
            shutil.copyfile(HERE / f, a.stage / f)
        (a.stage / "dataset-metadata.json").write_text(json.dumps(
            {"title": a.gen_slug.replace("-", " "), "id": f"{a.owner}/{a.gen_slug}", "licenses": [{"name": "other"}],
             "isPrivate": True}))
        (a.stage / "staged.json").write_text(json.dumps(
            {f: hashlib.sha256((a.stage / f).read_bytes()).hexdigest() for f in FILES}, indent=1))
        if not a.dry_run:
            kaggle(["datasets", "create", "-p", str(a.stage), "--dir-mode", "skip"], a.config_dir)
        return
    text = KERNEL.format(owner=repr(a.owner), held=repr(a.held_group), arms=json.dumps(a.arms), n=a.n,
                         targets=a.targets, code_slug=repr(a.code_slug), train_kernel=repr(a.train_kernel),
                         prepass_kernel=repr(a.prepass_kernel), gen_slug=repr(a.gen_slug),
                         anchors_kernel=repr(a.anchors_kernel))
    compile(text, "run.py", "exec")
    (a.stage / "run.py").write_text(text, encoding="utf-8")
    meta = {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False,
            "dataset_sources": [f"{a.owner}/{a.gen_slug}", f"{a.owner}/{a.code_slug}", f"{a.owner}/rlead-bench-cube-r2"]
            + [f"{a.data_owner}/{d}" for d in a.shard_datasets],
            "kernel_sources": [f"{a.owner}/{a.train_kernel}", f"{a.owner}/{a.prepass_kernel}"]
            + ([f"{a.owner}/{a.anchors_kernel}"] if a.anchors_kernel else []),
            "competition_sources": []}
    (a.stage / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed")
        return
    kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)


if __name__ == "__main__":
    main()
