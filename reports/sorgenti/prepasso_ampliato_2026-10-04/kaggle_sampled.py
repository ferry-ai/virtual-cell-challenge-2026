"""Kaggle CPU kernel of the sampled shards (build_sampled_shards.py, DECISIONE.md of this folder), no GPU quota.

The shards of the pilot corpus are Kaggle datasets of davidmaisterx (shared with davideferrante11 as reader); those of
the new sources (Orion, KOLF, CD4) are outputs of davideferrante11's ingestion kernels. A kernel mounts some of them
(--datasets, --kernels), runs build_sampled_shards.py, which travels inside run.py with its sha256 checked, and leaves
/kaggle/working/sampled/ (the shards, manifest.json), build.log, env.json and kernel_done.json. Every corpus a later
prepass reads must sit on one account, so the sampled shards of all sources are built on the account of the new
sources. A kernel keeps its output within the 20 GB of /kaggle/working: one kernel per source or unit.

    python kaggle_sampled.py --config-dir <dir> --owner davideferrante11 --stage <new dir> --slug <slug> \
        [--datasets rlab-...] [--kernels vcc-orion-hct116-p0of4-r3 ...] [--pattern "*.h5ad"] [--level 64] \
        [--workers 2] [--launch-log <jsonl>] [--dry-run]
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

KERNEL = r'''
import base64, hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path
P = json.loads(r"""__PARAMS__""")
CODE = "__CODE__"
INPUT = Path(os.environ.get("VCC_KAGGLE_INPUT", "/kaggle/input"))
OUT = Path(os.environ.get("VCC_KAGGLE_OUT", "/kaggle/working"))
t0 = time.time()
raw = base64.b64decode(CODE)
if hashlib.sha256(raw).hexdigest() != P["code_sha256"]:
    raise SystemExit("the builder inside run.py is not the launcher's")
(OUT / "build_sampled_shards.py").write_bytes(raw)


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()


if subprocess.run([sys.executable, "-c", "import anndata"], capture_output=True).returncode:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "anndata"], capture_output=True)
(OUT / "env.json").write_text(json.dumps({"python": sys.version.split()[0], "cpus": os.cpu_count(),
                                          "platform": platform.platform(), "memory": sh("free -m"),
                                          "disk": sh("df -h /kaggle/working | tail -1")}, indent=1))
roots = []
for slug in P["mounts"]:
    hits = [p for p in INPUT.glob(f"**/{slug}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{slug}: {len(hits)} mounts: {hits[:3]}")
    roots.append(str(hits[0]))
cmd = [sys.executable, str(OUT / "build_sampled_shards.py"), "--shard-roots", *roots, "--pattern", P["pattern"],
       "--out", str(OUT / "sampled"), "--level", str(P["level"]), "--levels", *map(str, P["levels"]),
       "--seed", str(P["seed"]), "--workers", str(P["workers"])]
with open(OUT / "build.log", "w") as fh:
    code = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode
(OUT / "build_sampled_shards.py").unlink()
(OUT / "kernel_done.json").write_text(json.dumps({"return_code": code, "seconds": round(time.time() - t0, 1),
                                                   "mounts": P["mounts"]}, indent=1))
if code:
    raise SystemExit(f"the builder failed with code {code}: see build.log")
'''


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--data-owner", default="davidmaisterx")
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--datasets", nargs="*", default=[])
    p.add_argument("--kernels", nargs="*", default=[])
    p.add_argument("--pattern", default="*.h5ad")
    p.add_argument("--level", type=int, default=64)
    p.add_argument("--levels", type=int, nargs="+", default=[32, 64, 128])
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--launch-log", type=Path)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    if not a.datasets and not a.kernels:
        sys.exit("give --datasets or --kernels")
    raw = (HERE / "build_sampled_shards.py").read_bytes()
    prm = {"mounts": [*a.datasets, *a.kernels], "pattern": a.pattern, "level": a.level, "levels": a.levels,
           "seed": a.seed, "workers": a.workers, "code_sha256": hashlib.sha256(raw).hexdigest()}
    text = KERNEL.replace("__PARAMS__", json.dumps(prm, indent=1)).replace("__CODE__", base64.b64encode(raw).decode())
    compile(text, "run.py", "exec")
    a.stage.mkdir(parents=True)
    (a.stage / "run.py").write_text(text, encoding="utf-8", newline="\n")
    meta = {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": True, "dataset_sources": [f"{a.data_owner}/{d}" for d in a.datasets],
            "kernel_sources": [f"{a.owner}/{k}" for k in a.kernels], "competition_sources": []}
    (a.stage / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    record = {"slug": f"{a.owner}/{a.slug}", "stage": a.stage.as_posix(), "params": prm,
              "run_sha256": hashlib.sha256((a.stage / "run.py").read_bytes()).hexdigest(),
              "dataset_sources": meta["dataset_sources"], "kernel_sources": meta["kernel_sources"]}
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed\n{json.dumps(record)}")
        return
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    r = subprocess.run([exe, "kernels", "push", "-p", str(a.stage)], env={**os.environ, "KAGGLE_CONFIG_DIR": a.config_dir},
                       capture_output=True, text=True)
    answer = ((r.stdout or "") + (r.stderr or "")).strip()
    accepted = r.returncode == 0 and "successfully pushed" in answer and "not valid" not in answer
    record.update(pushed_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), accepted=accepted,
                  answer=answer[-400:])
    print(json.dumps({k: record[k] for k in ("slug", "accepted", "answer")}))
    if a.launch_log:
        with open(a.launch_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    if not accepted:
        sys.exit("the push failed or an input is not a valid source")


if __name__ == "__main__":
    main()
