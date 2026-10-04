"""The anchors of version 4 on Kaggle CPU (no GPU quota), for the pilot's three held-out lines and the source rules.

D-056 copy (reports/modelli/ibrido_selettivo_2026-10-04): `kernel --line LINE=PREPASS_KERNEL` (repeatable) names the
held-out lines and their prepass kernels, for the confirmation lines of PROTOCOLLO.md §3 (Jurkat); without it the
three lines of version 4. The code dataset is version 4's (rcell-v4-anchor-code-r1, anchors.py unchanged).

A copy of version 3's launcher (reports/modelli/rete_ancorata_2026-10-03/kaggle_anchors.py) with version 4's anchors.py:
regime-J table means, and one output per (line, source rule): anchors_<line>_<rule>/ with rule in cells, all,
production (anchors.py). The training of the pilot reads the 'all' anchors (PROTOCOLLO.md); 'cells' and 'production'
are the references of the comparison of anchor sources.

- `data`: stage (and create) the private dataset <owner>/<code-slug> with anchors.py and the reconciled target keys of
  the trainings (the same bytes as version 3's: target_keys.json).
- `kernel`: a private CPU kernel without internet that rebuilds the bench cube from the dataset
  <owner>/rlead-bench-cube-r2 (flat files: cube__*, code__*, protocol__*), mounts the prepass states of the r1 prepass
  kernels and runs anchors.py once per (line, rule) into /kaggle/working/anchors_<line>_<rule>/.

    python kaggle_anchors.py data --config-dir <dir> --owner davideferrante11 --stage <new dir> --target-keys <json>
    python kaggle_anchors.py kernel --config-dir <dir> --owner davideferrante11 --stage <new dir> --slug rcell-v4-anchors-r1
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
LINES = {"H1": "rcell-prepass-h1-r1", "HepG2": "rcell-prepass-hepg2-r1", "RPE1": "rcell-prepass-rpe1-r1"}
RULES = ("all", "cells", "production")

KERNEL = r'''
import json, os, shutil, subprocess, sys, time
from pathlib import Path
INPUT, OUT, OWNER = Path("/kaggle/input"), Path("/kaggle/working"), {owner}
LINES, RULES, RANK, CODE_SLUG = {lines}, {rules}, {rank}, {code_slug}
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


CUBE_DS, CODE = mount("rlead-bench-cube-r2"), mount(CODE_SLUG)
cube, bench = OUT / "cube_r2", OUT / "bench_code"
cube.mkdir()
bench.mkdir()
for f in sorted(CUBE_DS.iterdir()):
    if f.name.startswith("code__"):
        shutil.copy2(f, bench / f.name[len("code__"):])
    elif f.name.startswith("cube__"):
        rest = f.name[len("cube__"):]
        if "__" in rest:
            table, name = rest.split("__", 1)
            (cube / table).mkdir(exist_ok=True)
            dest = cube / table / name
        else:
            dest = cube / rest
        try:
            os.symlink(f, dest)           # /kaggle/input is read-only and on another file system
        except OSError:
            shutil.copy2(f, dest)
proto = json.loads((CUBE_DS / "protocol__PROTOCOLLO.json").read_text(encoding="utf-8"))
proto["parameters"]["gene_coordinates"] = str(CUBE_DS / "gene_coordinates_gencode_v50.tsv")
(OUT / "PROTOCOLLO.json").write_text(json.dumps(proto, indent=1), encoding="utf-8")
log = {{"mounts": {{"cube": str(CUBE_DS), "code": str(CODE)}}, "runs": {{}}}}
print(json.dumps({{"t": round(time.time() - t0, 1), "msg": "layout ready"}}), flush=True)
for line, prepass_kernel in LINES.items():
    pre = mount(prepass_kernel) / "prepass"
    for rule in RULES:
        t = time.time()
        name = f"anchors_{{line}}_{{rule}}"
        r = subprocess.run([sys.executable, str(CODE / "anchors.py"), "--prepass", str(pre), "--cube", str(cube),
                            "--protocol", str(OUT / "PROTOCOLLO.json"), "--target-keys", str(CODE / "target_keys.json"),
                            "--sources", rule, "--bench-code", str(bench), "--rank", str(RANK), "--out",
                            str(OUT / name)], capture_output=True, text=True)
        (OUT / f"{{name}}.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr[-20000:], encoding="utf-8")
        log["runs"][name] = {{"prepass": str(pre), "returncode": r.returncode, "seconds": round(time.time() - t, 1)}}
        print(json.dumps({{name: log["runs"][name]}}), flush=True)
shutil.rmtree(cube, ignore_errors=True)
shutil.rmtree(bench, ignore_errors=True)
log["seconds"] = round(time.time() - t0, 1)
(OUT / "anchors_done.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
if any(v["returncode"] for v in log["runs"].values()):
    raise SystemExit("an anchors run failed: see its log")
'''


def kaggle(args, config_dir):
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
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
        q.add_argument("--code-slug", default="rcell-v4-anchor-code-r1")
        q.add_argument("--dry-run", action="store_true")
    d.add_argument("--target-keys", type=Path, required=True)
    k.add_argument("--slug", required=True)
    k.add_argument("--rank", type=int, default=32)
    k.add_argument("--line", action="append", default=[], metavar="LINE=PREPASS_KERNEL",
                   help="D-056: a held-out line and its prepass kernel (repeatable; default the three of version 4)")
    a = p.parse_args()
    lines = dict(x.split("=", 1) for x in a.line) if getattr(a, "line", None) else LINES
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    a.stage.mkdir(parents=True)
    if a.cmd == "data":
        shutil.copyfile(HERE / "anchors.py", a.stage / "anchors.py")
        shutil.copyfile(a.target_keys, a.stage / "target_keys.json")
        (a.stage / "dataset-metadata.json").write_text(json.dumps(
            {"title": a.code_slug.replace("-", " "), "id": f"{a.owner}/{a.code_slug}", "licenses": [{"name": "other"}],
             "isPrivate": True}))
        (a.stage / "staged.json").write_text(json.dumps(
            {f: hashlib.sha256((a.stage / f).read_bytes()).hexdigest() for f in ("anchors.py", "target_keys.json")},
            indent=1))
        if not a.dry_run:
            kaggle(["datasets", "create", "-p", str(a.stage), "--dir-mode", "skip"], a.config_dir)
        return
    text = KERNEL.format(owner=repr(a.owner), lines=json.dumps(lines), rules=json.dumps(list(RULES)), rank=a.rank,
                         code_slug=repr(a.code_slug))
    compile(text, "run.py", "exec")
    (a.stage / "run.py").write_text(text, encoding="utf-8")
    meta = {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False,
            "dataset_sources": [f"{a.owner}/rlead-bench-cube-r2", f"{a.owner}/{a.code_slug}"],
            "kernel_sources": [f"{a.owner}/{k_}" for k_ in lines.values()], "competition_sources": []}
    (a.stage / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed")
        return
    kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)


if __name__ == "__main__":
    main()
