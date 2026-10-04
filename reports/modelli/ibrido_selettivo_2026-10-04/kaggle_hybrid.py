"""The rows and the lanes of the D-056 hybrid on a Kaggle CPU kernel (PROTOCOLLO.md §6–7), never on the laptop.

A copy of version 4's kaggle_lanes.py (reports/modelli/rete_ancorata_v4_2026-10-03) for hybrid_lanes.py:
- the code travels inside run.py as a zip of the repository files hybrid_lanes.py imports (src/vcc2026, configs,
  hybrid_lanes.py and anchors.py of this folder, the modules of risposta_contesto_2026-10-02, the bench protocol), with
  its sha256 checked before it is unpacked;
- the scorer is installed at the version of the project venv (cell-eval2, pinned) and checked before any step;
- `--mode rows` runs `hybrid_lanes.py rows`; `--mode lanes` runs laneA and laneB with the weights file given by
  --weights, embedded in run.py with its sha256 (selector.py wrote it before this push, from other lines only).
The kernel rebuilds the cube folder from the flat dataset rlead-bench-cube-r2 and points the protocol at its gene table.

    python kaggle_hybrid.py --config-dir <dir> --owner davideferrante11 --stage <new dir> --mode rows --held-group H1 \
        --train-kernel rcell-d056-train-h1-r1 --prepass-kernel rcell-prepass-h1-r1 --anchors-dir anchors_H1_all \
        --slug rcell-d056-rows-h1-r1 [--launch-log <jsonl>] [--dry-run]
    python kaggle_hybrid.py ... --mode lanes --real-kernel rcell-gen-h1-r3 --weights weights_H1.json --slug ...
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ME = "reports/modelli/ibrido_selettivo_2026-10-04"
RC = "reports/modelli/risposta_contesto_2026-10-02"
MY_FILES = ("hybrid_lanes.py", "anchors.py")
PROTOCOL = "reports/analisi/generalizzazione_contesti_2026-10-02/PROTOCOLLO.json"

KERNEL = r'''
import base64, hashlib, io, json, os, platform, shutil, subprocess, sys, time, zipfile
from pathlib import Path
P = json.loads(r"""__PARAMS__""")
SNAPSHOT = "__SNAPSHOT__"
WEIGHTS = "__WEIGHTS__"
INPUT = Path(os.environ.get("VCC_KAGGLE_INPUT", "/kaggle/input"))
OUT = Path(os.environ.get("VCC_KAGGLE_OUT", "/kaggle/working"))
t0 = time.time()


def mount(slug):
    for p in (INPUT / slug, INPUT / "datasets" / P["owner"] / slug, INPUT / "notebooks" / P["owner"] / slug):
        if p.is_dir():
            return p
    hits = [p for p in INPUT.glob(f"**/{slug}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{slug}: {len(hits)} mounts: {hits[:3]}")
    return hits[0]


raw = base64.b64decode(SNAPSHOT)
if hashlib.sha256(raw).hexdigest() != P["snapshot_sha256"]:
    raise SystemExit("the code snapshot inside run.py is not the launcher's")
repo = OUT / "repo"
zipfile.ZipFile(io.BytesIO(raw)).extractall(repo)
weights = None
if P["mode"] == "lanes":
    wraw = base64.b64decode(WEIGHTS)
    if hashlib.sha256(wraw).hexdigest() != P["weights_sha256"]:
        raise SystemExit("the weights inside run.py are not the launcher's")
    weights = OUT / "weights.json"
    weights.write_bytes(wraw)
if not os.environ.get("VCC_SKIP_PIP"):
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", f"cell-eval2=={P['scorer_version']}"],
                       capture_output=True, text=True)
    (OUT / "pip.log").write_text(r.stdout[-5000:] + "\n--- stderr ---\n" + r.stderr[-5000:])
import importlib.metadata as md
found = md.version("cell-eval2")
if found != P["scorer_version"]:
    raise SystemExit(f"cell-eval2 {found} in the runtime, {P['scorer_version']} in the project venv")
versions = {}
for pkg in ("cell-eval2", "numpy", "scipy", "pandas", "polars", "anndata", "h5py"):
    try:
        versions[pkg] = md.version(pkg)
    except Exception:
        versions[pkg] = None
(OUT / "env.json").write_text(json.dumps({"python": sys.version.split()[0], "cpus": os.cpu_count(),
                                          "platform": platform.platform(), "versions": versions,
                                          "local_versions": P["local_versions"]}, indent=1))
src = mount(P["cube_slug"])
cube = OUT / "cube_r2"
cube.mkdir()
for f in sorted(src.iterdir()):
    if not f.name.startswith("cube__"):
        continue
    rest = f.name[len("cube__"):]
    if "__" in rest:
        table, name = rest.split("__", 1)
        (cube / table).mkdir(exist_ok=True)
        dest = cube / table / name
    else:
        dest = cube / rest
    try:
        os.symlink(f, dest)
    except OSError:
        shutil.copy2(f, dest)
proto = json.loads((repo / P["protocol"]).read_text(encoding="utf-8"))
proto["parameters"]["gene_coordinates"] = str(src / "gene_coordinates_gencode_v50.tsv")
protocol = OUT / "PROTOCOLLO.json"
protocol.write_text(json.dumps(proto, indent=1), encoding="utf-8")
TRAIN = mount(P["train_kernel"]) / "train"
SPLITS = mount(P["prepass_kernel"]) / "prepass" / "splits.json"
MANIFEST = mount(P["anchors_kernel"]) / P["anchors_dir"] / "manifest.json"
KEYS = mount(P["code_slug"]) / "target_keys.json"
need = [TRAIN / "eval_groups.json", SPLITS, MANIFEST, KEYS]
for arm in ("ibrido", "ibrido_mean", "ancora_sola"):
    need.append(TRAIN / arm / "eval_shifts.npz")
REAL = None
if P["mode"] == "lanes":
    REAL = mount(P["real_kernel"])
    need += [REAL / P["real_file"], REAL / P["targets_file"]]
missing = [str(p) for p in need if not p.is_file()]
if missing:
    raise SystemExit(f"inputs missing: {missing}")
env = {**os.environ, "PYTHONPATH": str(repo / "src"), "VCC2026_DATA_ROOT": str(OUT / "data_root"),
       "PYTHONIOENCODING": "utf-8"}
(OUT / "data_root").mkdir()
me = repo / P["me"]
common = ["--run", TRAIN, "--cube", cube, "--protocol", protocol, "--target-keys", KEYS, "--held-group", P["held"],
          "--splits", SPLITS, "--anchors-manifest", MANIFEST]
if P["mode"] == "rows":
    steps = {"rows": ["hybrid_lanes.py", "rows", *common, "--out", OUT / "rows"]}
else:
    steps = {"laneA": ["hybrid_lanes.py", "laneA", *common, "--weights", weights, "--out", OUT / "laneA"],
             "laneB": ["hybrid_lanes.py", "laneB", *common, "--weights", weights, "--real", REAL / P["real_file"],
                       "--targets", REAL / P["targets_file"], "--out", OUT / "laneB"]}
done = {}
for name, args in steps.items():
    t1 = time.time()
    with open(OUT / f"{name}.log", "w") as fh:
        code = subprocess.run([sys.executable, *map(str, args)], cwd=me, env=env, stdout=fh,
                              stderr=subprocess.STDOUT).returncode
    done[name] = {"return_code": code, "seconds": round(time.time() - t1, 1)}
    print(json.dumps({name: done[name]}), flush=True)
shutil.rmtree(cube, ignore_errors=True)
shutil.rmtree(repo, ignore_errors=True)
(OUT / "kernel_done.json").write_text(json.dumps({"held": P["held"], "mode": P["mode"], "steps": done,
                                                   "versions": versions, "seconds": round(time.time() - t0, 1)},
                                                  indent=1))
if any(d["return_code"] for d in done.values()):
    raise SystemExit(f"a step failed: {done}")
'''


def snapshot() -> tuple[bytes, list]:
    names = sorted(p.relative_to(REPO).as_posix() for p in (REPO / "src" / "vcc2026").rglob("*.py"))
    names += sorted(p.relative_to(REPO).as_posix() for p in (REPO / "configs").rglob("*") if p.is_file())
    names += [f"{ME}/{f}" for f in MY_FILES]
    names += sorted(p.relative_to(REPO).as_posix() for p in (REPO / RC).glob("*.py"))
    names.append(PROTOCOL)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            info = zipfile.ZipInfo(n, date_time=(2026, 10, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, (REPO / n).read_bytes())
    return buf.getvalue(), names


def local_versions() -> dict:
    out = {}
    for pkg in ("cell-eval2", "numpy", "scipy", "pandas", "polars", "anndata", "h5py"):
        try:
            out[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            out[pkg] = None
    return out


def kaggle(args, config_dir):
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    return subprocess.run([exe, *args], env={**os.environ, "KAGGLE_CONFIG_DIR": config_dir}, capture_output=True,
                          text=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--mode", choices=["rows", "lanes"], required=True)
    p.add_argument("--held-group", required=True)
    p.add_argument("--train-kernel", required=True)
    p.add_argument("--prepass-kernel", required=True)
    p.add_argument("--anchors-kernel", default="rcell-v4-anchors-r1")
    p.add_argument("--anchors-dir", required=True)
    p.add_argument("--real-kernel", help="lanes: the kernel holding the real cells and targets of lane B")
    p.add_argument("--real-file", default="real_cells.npz")
    p.add_argument("--targets-file", default="targets.json")
    p.add_argument("--weights", type=Path, help="lanes: the weights file of selector.py")
    p.add_argument("--code-slug", default="rcell-d056-code-r1")
    p.add_argument("--cube-slug", default="rlead-bench-cube-r2")
    p.add_argument("--cube-owner", default=None, help="the account of the cube dataset (default --owner; the replica "
                                                       "reads davideferrante11's, shared as reader)")
    p.add_argument("--launch-log", type=Path)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    if a.mode == "lanes" and (not a.real_kernel or not a.weights):
        sys.exit("--mode lanes needs --real-kernel and --weights")
    raw, names = snapshot()
    wraw = a.weights.read_bytes() if a.mode == "lanes" else b""
    versions = local_versions()
    prm = {"owner": a.owner, "held": a.held_group, "mode": a.mode, "train_kernel": a.train_kernel,
           "prepass_kernel": a.prepass_kernel, "anchors_kernel": a.anchors_kernel, "anchors_dir": a.anchors_dir,
           "real_kernel": a.real_kernel, "real_file": a.real_file, "targets_file": a.targets_file,
           "code_slug": a.code_slug, "cube_slug": a.cube_slug, "me": ME, "protocol": PROTOCOL,
           "scorer_version": versions["cell-eval2"], "local_versions": versions,
           "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
           "weights_sha256": hashlib.sha256(wraw).hexdigest() if wraw else None}
    text = (KERNEL.replace("__PARAMS__", json.dumps(prm, indent=1))
            .replace("__SNAPSHOT__", base64.b64encode(raw).decode("ascii"))
            .replace("__WEIGHTS__", base64.b64encode(wraw).decode("ascii")))
    compile(text, "run.py", "exec")
    a.stage.mkdir(parents=True)
    (a.stage / "run.py").write_text(text, encoding="utf-8", newline="\n")
    (a.stage / "snapshot_files.json").write_text(json.dumps(
        {n: hashlib.sha256((REPO / n).read_bytes()).hexdigest() for n in names}, indent=1), encoding="utf-8")
    kernels = [a.train_kernel, a.prepass_kernel, a.anchors_kernel] + ([a.real_kernel] if a.mode == "lanes" else [])
    meta = {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": True,
            "dataset_sources": [f"{a.cube_owner or a.owner}/{a.cube_slug}", f"{a.owner}/{a.code_slug}"],
            "kernel_sources": [f"{a.owner}/{k}" for k in kernels], "competition_sources": []}
    (a.stage / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    record = {"slug": f"{a.owner}/{a.slug}", "held": a.held_group, "mode": a.mode, "stage": a.stage.as_posix(),
              "run_sha256": hashlib.sha256((a.stage / "run.py").read_bytes()).hexdigest(),
              "snapshot_sha256": prm["snapshot_sha256"], "weights_sha256": prm["weights_sha256"],
              "weights": str(a.weights) if a.weights else None, "scorer_version": prm["scorer_version"],
              "kernel_sources": meta["kernel_sources"], "dataset_sources": meta["dataset_sources"]}
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles ({len(text)} bytes); nothing pushed\n{json.dumps(record)}")
        return
    r = kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)
    answer = ((r.stdout or "") + (r.stderr or "")).strip()
    accepted = r.returncode == 0 and "successfully pushed" in answer and "not valid" not in answer
    record.update(pushed_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), returncode=r.returncode,
                  accepted=accepted, answer=answer[-600:])
    print(json.dumps({k: record[k] for k in ("slug", "accepted", "answer")}))
    if a.launch_log:
        with open(a.launch_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    if not accepted:
        sys.exit("the push failed or an input is not a valid source")


if __name__ == "__main__":
    main()
