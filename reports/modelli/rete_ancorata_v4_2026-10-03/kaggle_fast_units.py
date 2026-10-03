"""Kaggle CPU kernel that builds the compact twins of shards left in kernel outputs (build_fast_units.py), no GPU quota.

For the expanded corpus (D-053): the Orion parts, KOLF pan-genome and the CD4 parts are outputs of ingestion kernels of
davideferrante11, not datasets with files.json. The kernel mounts those part kernels and the build code dataset
(rcell-v4-build-r1: fastshard.py, build_fast.py, cell_data.py), checks the two modules it imports against the sha256 the
launcher read from this folder, writes build_fast_units.py out of run.py with its sha256 checked, and runs it into
/kaggle/working/twins. Kaggle keeps 20 GB of output per kernel: choose the parts so that their twins fit (about 40% of
the shards' bytes on the pilot corpus).

    python kaggle_fast_units.py --config-dir <dir> --owner davideferrante11 --stage <new dir> \
        --slug rcell-v4-fast-hek293t-a-r1 --parts vcc-orion-hek293t-p0of8-r3 ... [--launch-log <jsonl>] [--dry-run]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE_FILES = ("fastshard.py", "build_fast.py")

KERNEL = r'''
import base64, hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path
P = json.loads(r"""__PARAMS__""")
INPUT = Path(os.environ.get("VCC_KAGGLE_INPUT", "/kaggle/input"))
OUT = Path(os.environ.get("VCC_KAGGLE_OUT", "/kaggle/working"))
t0 = time.time()


def mount(slug):
    for p in (INPUT / slug, INPUT / "datasets" / P["owner"] / slug):
        if p.is_dir():
            return p
    hits = [p for p in INPUT.glob(f"**/{slug}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{slug}: {len(hits)} mounts: {hits[:3]}")
    return hits[0]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(16 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()


env = {"python": sys.version.split()[0], "cpus": os.cpu_count(), "platform": platform.platform(),
       "memory": sh("free -m"), "disk": sh("df -h . | tail -1")}
try:
    import pyarrow
    env["pyarrow"] = pyarrow.__version__
except ImportError as e:
    env["pyarrow"] = repr(e)
(OUT / "env.json").write_text(json.dumps(env, indent=1))
CODE = mount(P["code_slug"])
problems = [f"code dataset: {n} is not the launcher's file" for n, want in P["code_sha256"].items()
            if not (CODE / n).is_file() or sha(CODE / n) != want]
source = base64.b64decode(P["builder_b64"])
if hashlib.sha256(source).hexdigest() != P["builder_sha256"]:
    problems.append("build_fast_units.py inside run.py is not the launcher's file")
if problems:
    (OUT / "preflight_failed.json").write_text(json.dumps(problems, indent=1))
    raise SystemExit(f"preflight failed, nothing built: {problems}")
work = OUT / "code"
work.mkdir()
(work / "build_fast_units.py").write_bytes(source)
cmd = [sys.executable, str(work / "build_fast_units.py"), "--input", str(INPUT), "--jobs", *P["jobs"],
       "--out", str(OUT / "twins"), "--workers", str(P["workers"] or os.cpu_count() or 1)]
print(" ".join(cmd), flush=True)
with open(OUT / "build.log", "w") as fh:
    code = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                          env={**os.environ, "PYTHONPATH": str(CODE)}).returncode
(OUT / "kernel_done.json").write_text(json.dumps({"return_code": code, "seconds": round(time.time() - t0, 1)}))
if code:
    raise SystemExit(f"build failed with code {code}: see build.log")
'''


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def params(owner, code_slug, parts, workers) -> dict:
    source = (HERE / "build_fast_units.py").read_bytes()
    return {"owner": owner, "code_slug": code_slug, "jobs": [s.replace("-", "_") for s in parts], "workers": workers,
            "code_sha256": {f: sha256_file(HERE / f) for f in CODE_FILES},
            "builder_sha256": hashlib.sha256(source).hexdigest(), "builder_b64": base64.b64encode(source).decode("ascii")}


def kernel_text(p: dict) -> str:
    text = KERNEL.replace("__PARAMS__", json.dumps(p, indent=1))
    compile(text, "run.py", "exec")
    return text


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
    p.add_argument("--code-slug", default="rcell-v4-build-r1")
    p.add_argument("--parts", nargs="+", required=True, help="slugs of the kernels whose output holds the shards")
    p.add_argument("--workers", type=int, default=0, help="0 = the CPUs of the runtime")
    p.add_argument("--launch-log", type=Path)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    prm = params(a.owner, a.code_slug, a.parts, a.workers)
    text = kernel_text(prm)
    a.stage.mkdir(parents=True)
    (a.stage / "run.py").write_text(text, encoding="utf-8", newline="\n")
    meta = {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False, "dataset_sources": [f"{a.owner}/{a.code_slug}"],
            "kernel_sources": [f"{a.owner}/{s}" for s in a.parts], "competition_sources": []}
    (a.stage / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    record = {"slug": f"{a.owner}/{a.slug}", "stage": a.stage.as_posix(), "run_sha256": sha256_file(a.stage / "run.py"),
              "builder_sha256": prm["builder_sha256"], "code_sha256": prm["code_sha256"], "parts": a.parts}
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed\n{json.dumps(record)}")
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
        sys.exit("the push failed or a part is not a valid source")


if __name__ == "__main__":
    main()
