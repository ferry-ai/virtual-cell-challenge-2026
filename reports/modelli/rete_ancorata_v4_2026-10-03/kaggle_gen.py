"""Kaggle kernel of lane B, version 4 (PROTOCOLLO.md §6): after a training, generate the cells of every trained arm for
the targets of the r3 lane B, where the model, the prepass state and the anchors already are (CPU, no GPU quota).

A copy of version 3's launcher (reports/modelli/rete_ancorata_2026-10-03/kaggle_gen.py), changed where its own review
asked (PROTOCOLLO.md §9 of version 3: "a complete fixture of the generation package before pushing"):
- the targets are those of the r3 lane B (targets.json of out_gen_h1_r3, out_gen_hepg2_r3b, out_gen_rpe1_r3b), shipped in
  the generation dataset as targets_<line>.json: the truth of lane B does not change, so no target choice and no
  extraction of real cells here;
- the dataset carries every module the generator imports, train_cellnet.py's balanced.py and fastshard.py included;
- the anchors folder is named (--anchors-dir, version 4: anchors_<line>_all);
- INPUT and OUT can be moved by environment variables (VCC_KAGGLE_INPUT, VCC_KAGGLE_OUT), so test_generation_v4.py runs
  the kernel's own run.py on a mock input tree.

- `data`: stage (and create) the private dataset <owner>/<gen-slug>.
- `kernel`: a kernel reading the training's output (train/<arm>/model.pt), the prepass state, the anchors and the code
  dataset (descriptors); writes cells_<arm>.npz, their sidecars and gen_done.json to the output.

    python kaggle_gen.py data --config-dir <dir> --owner davideferrante11 --stage <new dir> --targets H1=<json> ...
    python kaggle_gen.py kernel --config-dir <dir> --owner davideferrante11 --stage <new dir> --held-group HepG2 \
        --train-kernel rcell-v4-train-hepg2-r1 --prepass-kernel rcell-prepass-hepg2-r1 \
        --anchors-kernel rcell-v4-anchors-r1 --anchors-dir anchors_HepG2_all --slug rcell-v4-gen-hepg2-r1
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
FILES = ("generate_cells.py", "cellnet.py", "cell_data.py", "train_cellnet.py", "balanced.py", "fastshard.py")

KERNEL = r'''
import json, os, subprocess, sys, time
from pathlib import Path
INPUT = Path(os.environ.get("VCC_KAGGLE_INPUT", "/kaggle/input"))
OUT = Path(os.environ.get("VCC_KAGGLE_OUT", "/kaggle/working"))
OWNER = {owner}
HELD, ARMS, N, EXTRA = {held}, {arms}, {n}, {extra}
t0 = time.time()


def mount(slug):
    for p in (INPUT / slug, INPUT / "datasets" / OWNER / slug, INPUT / "notebooks" / OWNER / slug,
              INPUT / "kernels" / OWNER / slug):
        if p.is_dir():
            return p
    hits = [p for p in INPUT.glob(f"**/{{slug}}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{{slug}}: {{len(hits)}} mounts: {{hits[:3]}}")
    return hits[0]


GEN, CODE = mount({gen_slug}), mount({code_slug})
TRAIN, PRE = mount({train_kernel}) / "train", mount({prepass_kernel}) / "prepass"
ANCHORS = mount({anchors_kernel}) / {anchors_dir}
TARGETS = GEN / f"targets_{{HELD}}.json"
missing = [str(p) for p in [TARGETS, ANCHORS / "manifest.json", PRE / "prepass.pkl"] + [TRAIN / a / "model.pt" for a in ARMS]
           if not p.is_file()]
if missing:
    raise SystemExit(f"inputs missing: {{missing}}")
log = {{"mounts": {{"gen": str(GEN), "code": str(CODE), "train": str(TRAIN), "prepass": str(PRE),
                   "anchors": str(ANCHORS)}}, "targets": str(TARGETS)}}


def run(args, name):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
    (OUT / f"{{name}}.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr[-20000:])
    log[name] = {{"returncode": r.returncode, "seconds": round(time.time() - t0, 1)}}
    print(json.dumps({{name: log[name]}}), flush=True)
    return r.returncode == 0


ok = True
for arm in ARMS:
    ok &= run([GEN / "generate_cells.py", "--prepass", PRE, "--arm-dir", TRAIN / arm, "--descriptors", CODE,
               "--targets", TARGETS, "--n", N, "--anchors", ANCHORS, "--out", OUT / f"cells_{{arm}}.npz", *EXTRA],
              f"generate_{{arm}}")
(OUT / "gen_done.json").write_text(json.dumps(log, indent=1))
if not ok:
    raise SystemExit("a generation failed: see its log")
'''


def kaggle(args, config_dir):
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    import os
    r = subprocess.run([exe, *args], env={**os.environ, "KAGGLE_CONFIG_DIR": config_dir}, capture_output=True, text=True)
    print((r.stdout or "")[-1500:], (r.stderr or "")[-1500:])
    return r


def stage_data(stage: Path, owner: str, gen_slug: str, targets: dict):
    """The generation dataset: the modules of FILES and targets_<line>.json, with staged.json."""
    for f in FILES:
        shutil.copyfile(HERE / f, stage / f)
    for line, path in targets.items():
        shutil.copyfile(path, stage / f"targets_{line}.json")
    (stage / "dataset-metadata.json").write_text(json.dumps(
        {"title": gen_slug.replace("-", " "), "id": f"{owner}/{gen_slug}", "licenses": [{"name": "other"}],
         "isPrivate": True}))
    (stage / "staged.json").write_text(json.dumps(
        {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(stage.iterdir())
         if p.name not in ("staged.json", "dataset-metadata.json")}, indent=1))


def kernel_text(a) -> str:
    text = KERNEL.format(owner=repr(a.owner), held=repr(a.held_group), arms=json.dumps(a.arms), n=a.n,
                         extra=json.dumps(a.extra), code_slug=repr(a.code_slug), train_kernel=repr(a.train_kernel),
                         prepass_kernel=repr(a.prepass_kernel), gen_slug=repr(a.gen_slug),
                         anchors_kernel=repr(a.anchors_kernel), anchors_dir=repr(a.anchors_dir))
    compile(text, "run.py", "exec")
    return text


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
        q.add_argument("--gen-slug", default="rcell-v4-gen-r1", help="the dataset of the generation code")
    d.add_argument("--targets", nargs="+", required=True, metavar="LINE=JSON")
    k.add_argument("--held-group", required=True)
    k.add_argument("--train-kernel", required=True)
    k.add_argument("--prepass-kernel", required=True)
    k.add_argument("--anchors-kernel", required=True)
    k.add_argument("--anchors-dir", required=True)
    k.add_argument("--slug", required=True)
    k.add_argument("--code-slug", default="rcell-v4-code-r1")
    k.add_argument("--arms", nargs="+", default=["ancorata", "ancorata_mean"])
    k.add_argument("--n", type=int, default=32)
    k.add_argument("--extra", nargs="*", default=[], help="more arguments of generate_cells.py (tests)")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    a.stage.mkdir(parents=True)
    if a.cmd == "data":
        stage_data(a.stage, a.owner, a.gen_slug, dict(x.split("=", 1) for x in a.targets))
        if not a.dry_run:
            kaggle(["datasets", "create", "-p", str(a.stage), "--dir-mode", "skip"], a.config_dir)
        return
    (a.stage / "run.py").write_text(kernel_text(a), encoding="utf-8")
    meta = {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False,
            "dataset_sources": [f"{a.owner}/{a.gen_slug}", f"{a.owner}/{a.code_slug}"],
            "kernel_sources": [f"{a.owner}/{a.train_kernel}", f"{a.owner}/{a.prepass_kernel}",
                               f"{a.owner}/{a.anchors_kernel}"],
            "competition_sources": []}
    (a.stage / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed")
        return
    kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)


if __name__ == "__main__":
    main()
