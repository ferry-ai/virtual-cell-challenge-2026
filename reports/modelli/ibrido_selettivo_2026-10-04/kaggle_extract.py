"""Real cells and targets of lane B for a confirmation line (PROTOCOLLO.md §7), on a Kaggle CPU kernel, before training.

The lane B targets of the development lines are those of the r3 lane B (kernels rcell-gen-<line>-r3*). A confirmation
line gets them by the same rule and code: choose_targets.py (C groups of the held-out keys, a usable row of the held
line's cube table with at least 50 cells and of another cell group, ordered by sha256 with the salt 'six-member', 150)
and extract_cells.py (at most 64 cells per target and 2048 controls, seed 2026), both from the r3 code dataset
rcell-gen-r1. choose_targets reads only the class, key and symbol of each evaluation group, which the prepass state
already holds: the kernel writes eval_groups.json from the state (the same fields the training would write), so the
cells are extracted before the network is trained and cannot depend on it. Nothing here reads an effect.

    python kaggle_extract.py --config-dir <dir> --owner davideferrante11 --stage <new dir> --held-group Jurkat \
        --prepass-kernel rcell-prepass-jurkat-r1 --shard-datasets rlab-jurkat-nadig --slug rcell-d056-extract-jurkat-r1
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

KERNEL = r'''
import json, os, pickle, subprocess, sys, time
from pathlib import Path
INPUT, OUT, OWNER = Path("/kaggle/input"), Path("/kaggle/working"), {owner}
HELD, TARGETS = {held}, {targets}
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


GEN, CODE, CUBE = mount("rcell-gen-r1"), mount({code_slug}), mount("rlead-bench-cube-r2")
PRE = mount({prepass_kernel}) / "prepass"
sys.path.insert(0, str(GEN))
with open(PRE / "prepass.pkl", "rb") as fh:
    st = pickle.load(fh)
if st.get("holdout_group") != HELD:
    raise SystemExit(f"prepass of {{st.get('holdout_group')}}, not {{HELD}}")
groups = [{{"class": g["class"], "key": g["key"], "symbol": g["symbol"], "admitted_cells": g.get("admitted_cells")}}
          for g in st["eval_groups"]]
(OUT / "eval_groups.json").write_text(json.dumps(groups, indent=0))
cube = OUT / "cube_rows"
cube.mkdir()
(cube / "manifest.json").write_bytes((CUBE / "cube__manifest.json").read_bytes())
for f in CUBE.glob("cube__*__rows.csv"):
    table = f.name[len("cube__"):-len("__rows.csv")]
    (cube / table).mkdir()
    (cube / table / "rows.csv").write_bytes(f.read_bytes())
log = {{"mounts": {{"gen": str(GEN), "code": str(CODE), "cube": str(CUBE), "prepass": str(PRE)}},
        "eval_groups": {{c: sum(g["class"] == c for g in groups) for c in ("C", "J", "T")}}}}


def run(args, name):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
    (OUT / f"{{name}}.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr[-20000:])
    log[name] = {{"returncode": r.returncode, "seconds": round(time.time() - t0, 1)}}
    print(json.dumps({{name: log[name]}}), flush=True)
    return r.returncode == 0


ok = run([GEN / "choose_targets.py", "--eval-groups", OUT / "eval_groups.json", "--cube", cube, "--target-keys",
          CODE / "target_keys.json", "--held-group", HELD, "--targets", TARGETS, "--out", OUT / "targets.json"], "choose")
if ok:
    ok = run([GEN / "extract_cells.py", "--prepass", PRE, "--targets", OUT / "targets.json", "--shard-roots", INPUT,
              "--cap", 64, "--max-controls", 2048, "--seed", 2026, "--out", OUT / "real_cells.npz"], "extract")
import shutil
shutil.rmtree(cube, ignore_errors=True)
log["ok"] = bool(ok)
(OUT / "gen_done.json").write_text(json.dumps(log, indent=1))
if not ok:
    raise SystemExit("choose or extract failed: see the logs")
'''


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--data-owner", default="davidmaisterx")
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--held-group", required=True)
    p.add_argument("--prepass-kernel", required=True)
    p.add_argument("--shard-datasets", nargs="+", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--code-slug", default="rcell-code-r1")
    p.add_argument("--targets", type=int, default=150)
    p.add_argument("--launch-log", type=Path)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    text = KERNEL.format(owner=repr(a.owner), held=repr(a.held_group), targets=a.targets, code_slug=repr(a.code_slug),
                         prepass_kernel=repr(a.prepass_kernel))
    compile(text, "run.py", "exec")
    a.stage.mkdir(parents=True)
    (a.stage / "run.py").write_text(text, encoding="utf-8", newline="\n")
    meta = {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False,
            "dataset_sources": [f"{a.owner}/rcell-gen-r1", f"{a.owner}/{a.code_slug}", f"{a.owner}/rlead-bench-cube-r2"]
            + [f"{a.data_owner}/{d}" for d in a.shard_datasets],
            "kernel_sources": [f"{a.owner}/{a.prepass_kernel}"], "competition_sources": []}
    (a.stage / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed")
        return
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    r = subprocess.run([exe, "kernels", "push", "-p", str(a.stage)], env={**os.environ, "KAGGLE_CONFIG_DIR": a.config_dir},
                       capture_output=True, text=True)
    answer = ((r.stdout or "") + (r.stderr or "")).strip()
    accepted = r.returncode == 0 and "successfully pushed" in answer and "not valid" not in answer
    record = {"slug": f"{a.owner}/{a.slug}", "held": a.held_group, "stage": a.stage.as_posix(), "accepted": accepted,
              "answer": answer[-400:], "pushed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "dataset_sources": meta["dataset_sources"], "kernel_sources": meta["kernel_sources"]}
    print(json.dumps({k: record[k] for k in ("slug", "accepted", "answer")}))
    if a.launch_log:
        with open(a.launch_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    if not accepted:
        sys.exit("the push failed or an input is not a valid source")


if __name__ == "__main__":
    main()
