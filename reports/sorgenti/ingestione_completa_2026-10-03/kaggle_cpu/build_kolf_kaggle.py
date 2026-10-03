"""KOLF pan-genome parts as Kaggle CPU kernels: the code dataset and one kernel per range of cells.

- `code`: a tar.gz of the committed files the job needs (git archive of HEAD: the paths must be committed and clean)
  and the official axis, as the private dataset <owner>/<code-slug>. Kaggle unpacks the tar into `code_snapshot/`.
- `kernel`: one kernel per part. It checks every file of the unpacked snapshot against the members of the tar
  (sha256, as the Orion r2 kernels do), records the runtime, runs kolf/kolf_job.py for `--part i/n` and leaves the
  shards, their receipts and complete.json in /kaggle/working/<job>/. The buckets of the scan go to /tmp: about 6 bytes
  per value of the range (24 GB for half of the file); the adapter plans its passes on the free space it measures.

Every push is one command typed by the session (incident E-20261003-001); the CLI exits 0 on a refused push, so the
answer decides (see build_orion_kaggle_r2.py).

    python build_kolf_kaggle.py code --config-dir <dir> --owner davideferrante11 --stage <new dir> --axis <gene_names.csv>
    python build_kolf_kaggle.py kernel --config-dir <dir> --owner davideferrante11 --stage <new dir> \
        --code-stage <staged folder of the code dataset> --part 0/2 --slug vcc-kolf-pan-p0of2-r1 [--max-cells N]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))
from build_orion_kaggle_r2 import kaggle, sha256_file, snapshot_members  # noqa: E402

REPORT = "reports/sorgenti/ingestione_completa_2026-10-03"
CORPUS = "reports/sorgenti/corpus_cellulare_2026-09-30"
SNAPSHOT_PATHS = [f"{REPORT}/kolf/{f}" for f in ("kolf_job.py", "complete_adapters.py", "specs/kolf_pan_v1.json")] + \
    [f"{REPORT}/orion/common.py"] + \
    [f"{CORPUS}/{f}" for f in ("adapters.py", "contracts.py", "inspect_remote.py", "rlab_job.py", "validate_runtime.py")]

KERNEL = r'''
import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
P = json.loads(r"""__PARAMS__""")
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
PART, JOB = P["part"], P["job"]
t0 = time.time()


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def mount(slug):
    hits = [p for p in INPUT.glob(f"**/{slug}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{slug}: {len(hits)} mounts: {hits[:3]}")
    return hits[0]


DS = mount(P["code_slug"])
SRC = DS / "code_snapshot"
found = {p.relative_to(SRC).as_posix(): sha(p) for p in SRC.rglob("*") if p.is_file()}
bad = sorted(k for k in set(found) | set(P["members"]) if found.get(k) != P["members"].get(k))
if bad:
    raise SystemExit(f"the unpacked snapshot differs from the tar {P['snapshot_sha256']}: {bad[:10]}")
if sha(DS / "gene_names.csv") != P["axis_sha256"]:
    raise SystemExit("gene_names.csv differs from the staged axis")
work, code = Path("/tmp/w"), Path("/tmp/w/code")
work.mkdir(parents=True)
shutil.copytree(SRC, code)
K = code / "reports/sorgenti/ingestione_completa_2026-10-03/kolf"
V = code / "reports/sorgenti/corpus_cellulare_2026-09-30/validate_runtime.py"
out = OUT / JOB
out.mkdir()
log = {"job": JOB, "part": PART, "snapshot_sha256": P["snapshot_sha256"], "commit": P["commit"],
       "snapshot_check": f"{len(found)} files of the unpacked snapshot equal the members of the tar, by sha256",
       "axis_sha256": P["axis_sha256"], "tmp_free_bytes": shutil.disk_usage("/tmp").free, "pip": {}, "steps": {}}
print(json.dumps({"preflight": log["snapshot_check"], "tmp_free_bytes": log["tmp_free_bytes"]}), flush=True)


def run(args, name):
    t = time.time()
    with open(out / f"{name}.log", "w", encoding="utf-8") as fh:
        p = subprocess.Popen([sys.executable, *map(str, args)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True)
        for line in p.stdout:
            fh.write(line)
            print(f"[{name}] {line}", end="", flush=True)
        code_ = p.wait()
    log["steps"][name] = {"returncode": code_, "seconds": round(time.time() - t, 1)}
    print(json.dumps({name: log["steps"][name]}), flush=True)
    return code_ == 0


def close(ok):
    log["seconds"], log["ok"] = round(time.time() - t0, 1), ok
    log["output_bytes"] = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    (out / "kaggle_done.json").write_text(json.dumps(log, indent=1))
    print(json.dumps({"done": {k: log[k] for k in ("job", "ok", "seconds", "output_bytes")}}), flush=True)
    if not ok:
        raise SystemExit("a step failed: see the logs in the output")


for pkg in ("anndata", "h5py"):
    if subprocess.run([sys.executable, "-c", f"import {pkg}"], capture_output=True).returncode:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], capture_output=True, text=True)
        log["pip"][pkg] = {"returncode": r.returncode, "stderr": r.stderr[-2000:]}
os.environ.update(RLAB_SNAPSHOT_SHA256=P["snapshot_sha256"], RLAB_COMMIT=P["commit"], PYTHONHASHSEED="0",
                  PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
env = out / "environment_manifest_kaggle.json"
run([V, "--out", env, "--data-root", OUT], "runtime")      # exits 1 without the scorer: only the round trip decides
rt = json.loads(env.read_text()) if env.is_file() else {}
log["runtime"] = {"cpus": rt.get("cpus"), "memory": rt.get("memory"), "sparse_roundtrip": rt.get("sparse_roundtrip"),
                  "python": rt.get("python"), "packages": {k: (rt.get("packages") or {}).get(k)
                                                           for k in ("numpy", "scipy", "pandas", "anndata", "h5py")}}
print(json.dumps({"runtime": log["runtime"]}), flush=True)
if not (rt.get("sparse_roundtrip") or {}).get("ok"):
    close(False)
extra = ["--max-cells", P["max_cells"]] if P.get("max_cells") else []
ok = run([K / "kolf_job.py", "--spec", K / "specs/kolf_pan_v1.json", "--axis", DS / "gene_names.csv", "--stage",
          work / "stage", "--out", out / "shards", "--data-root", OUT, "--runtime-manifest", env, "--part", PART,
          *extra], "shards")
done = out / "shards" / "complete.json"
if done.is_file():
    log["complete"] = json.loads(done.read_text())
    print(json.dumps({"complete": log["complete"]}), flush=True)
close(ok and done.is_file())
'''


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c, k = sub.add_parser("code"), sub.add_parser("kernel")
    for q in (c, k):
        q.add_argument("--config-dir", required=True)
        q.add_argument("--owner", required=True)
        q.add_argument("--stage", type=Path, required=True)
        q.add_argument("--code-slug", default="vcc-ingest-code-kolf-r1")
        q.add_argument("--dry-run", action="store_true")
    c.add_argument("--axis", type=Path, required=True)
    k.add_argument("--code-stage", type=Path, required=True)
    k.add_argument("--part", required=True)
    k.add_argument("--slug", required=True)
    k.add_argument("--max-cells", help="smoke test: only the first N cells of the range")
    k.add_argument("--launch-log", type=Path, help="JSON lines, one per push, appended")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    if a.cmd == "code":
        if git("status", "--porcelain", "--", *SNAPSHOT_PATHS).strip():
            sys.exit("refusing: a file of the snapshot is not committed as it is")
        commit = git("rev-parse", "HEAD").strip()
        a.stage.mkdir(parents=True)
        tar = a.stage / "code_snapshot.tar.gz"
        subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar.gz", "-o", str(tar), commit, "--",
                        *SNAPSHOT_PATHS], check=True)
        if sorted(snapshot_members(tar)) != sorted(SNAPSHOT_PATHS):
            sys.exit("the archive does not hold exactly the files of the snapshot")
        shutil.copyfile(a.axis, a.stage / "gene_names.csv")
        (a.stage / "dataset-metadata.json").write_text(json.dumps(
            {"title": a.code_slug.replace("-", " "), "id": f"{a.owner}/{a.code_slug}", "licenses": [{"name": "other"}],
             "isPrivate": True}))
        (a.stage / "staged.json").write_text(json.dumps(
            {"code_snapshot.tar.gz": sha256_file(tar), "gene_names.csv": sha256_file(a.stage / "gene_names.csv"),
             "commit": commit, "files": SNAPSHOT_PATHS}, indent=1))
        print((a.stage / "staged.json").read_text())
        if not a.dry_run:
            kaggle(["datasets", "create", "-p", str(a.stage), "--dir-mode", "skip"], a.config_dir)
        return
    staged = json.loads((a.code_stage / "staged.json").read_text(encoding="utf-8"))
    tar = a.code_stage / "code_snapshot.tar.gz"
    if sha256_file(tar) != staged["code_snapshot.tar.gz"]:
        sys.exit("the staged tar is not the one its staged.json names")
    params = {"part": a.part, "job": a.slug.replace("-", "_"), "code_slug": a.code_slug, "commit": staged["commit"],
              "snapshot_sha256": staged["code_snapshot.tar.gz"], "members": snapshot_members(tar),
              "axis_sha256": staged["gene_names.csv"], "max_cells": a.max_cells}
    text = KERNEL.replace("__PARAMS__", json.dumps(params, indent=1))
    compile(text, "run.py", "exec")
    a.stage.mkdir(parents=True)
    (a.stage / "run.py").write_text(text, encoding="utf-8", newline="\n")
    (a.stage / "kernel-metadata.json").write_text(json.dumps(
        {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
         "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False, "enable_internet": True,
         "dataset_sources": [f"{a.owner}/{a.code_slug}"], "kernel_sources": [], "competition_sources": []}, indent=1))
    record = {"slug": f"{a.owner}/{a.slug}", "source": "kolf_pan_genome", "part": a.part, "max_cells": a.max_cells,
              "stage": a.stage.as_posix(), "run_sha256": sha256_file(a.stage / "run.py"),
              "snapshot_sha256": params["snapshot_sha256"], "commit": params["commit"]}
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed\n{json.dumps(record)}")
        return
    r = kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)
    answer = ((r.stdout or "") + (r.stderr or "")).strip()
    accepted = r.returncode == 0 and "successfully pushed" in answer
    record.update(pushed_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), returncode=r.returncode,
                  accepted=accepted, answer=answer[-600:])
    if a.launch_log:
        with open(a.launch_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    if not accepted:
        sys.exit("the push failed")


if __name__ == "__main__":
    main()
