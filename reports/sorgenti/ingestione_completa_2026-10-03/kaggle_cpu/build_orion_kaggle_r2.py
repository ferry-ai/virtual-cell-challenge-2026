"""Orion parts as Kaggle CPU kernels, second build: the r1 kernels failed on the code snapshot (3/10, 16:37).

Kaggle unpacks an archive uploaded to a dataset: `vcc-ingest-code-r1` holds the folder `code_snapshot/`, not
`code_snapshot.tar.gz`, so r1 died on its first line (`esito_orion_r1/`). build_orion_kaggle.py stays as it ran; this
copy changes the kernel only:

- the snapshot is read from the unpacked folder, after every file is checked by sha256 against the members of the tar
  the Colab jobs use (the hashes are taken here, from the staged tar, and written into the kernel);
- the runtime manifest must report a sparse round trip that keeps integer counts (the scorer, absent on Kaggle, is
  not needed to ingest);
- the sample is compared with the one of the Colab meta job by its cells (number and a digest of the sorted
  identifiers of the selected ones), because the bytes of a parquet can change with the pyarrow version;
- the phases print to the kernel log (`kaggle kernels logs -f`) as well as to their files in the output.

The code dataset is the one of r1, unchanged. One kernel per (line, part); the output is /kaggle/working/<job>/ with
the sample, the shards, their receipts and complete.json, under Kaggle's 20 GB (a part of 4 of HCT116 is about 10 GB
at the 362 MB per shard measured on Colab, a part of 8 of HEK293T less).

Kaggle runs 5 batch CPU sessions at most (measured on 3/10 at 17:12) and its CLI exits 0 on a refused push: the push
counts only when the answer says so, and a refused stage is pushed again with --repush once a session is free. Every
push is one command typed by the session: no loop that pushes on its own (incident E-20261003-001).

    python build_orion_kaggle_r2.py --config-dir <dir> --owner davideferrante11 --stage <new dir> \
        --code-stage <staged folder of the code dataset> --line HEK293T --part 0/8 --slug vcc-orion-hek293t-p0of8-r2 \
        --commit <commit of the snapshot> [--launch-log <jsonl>] [--dry-run] [--repush]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORION = HERE.parent / "orion"
SPEC_IN_SNAPSHOT = "reports/sorgenti/ingestione_completa_2026-10-03/orion/specs/orion_full_v1.json"

KERNEL = r'''
import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
P = json.loads(r"""__PARAMS__""")
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
LINE, PART, JOB = P["line"], P["part"], P["job"]
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


# Kaggle unpacked the tar of the dataset into code_snapshot/: every file must be a member of the tar of the Colab jobs.
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
C = code / "reports/sorgenti/ingestione_completa_2026-10-03/orion"
V = code / "reports/sorgenti/corpus_cellulare_2026-09-30/validate_runtime.py"
out = OUT / JOB
out.mkdir()
log = {"job": JOB, "line": LINE, "part": PART, "snapshot_sha256": P["snapshot_sha256"],
       "snapshot_check": f"{len(found)} files of the unpacked snapshot equal the members of the tar, by sha256",
       "axis_sha256": P["axis_sha256"], "pip": {}, "steps": {}}
print(json.dumps({"preflight": log["snapshot_check"]}), flush=True)


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


for pkg in ("anndata", "pyarrow"):
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
                                                           for k in ("numpy", "scipy", "pandas", "anndata", "pyarrow", "h5py")}}
print(json.dumps({"runtime": log["runtime"]}), flush=True)
if not (rt.get("sparse_roundtrip") or {}).get("ok"):
    close(False)
spec = C / "specs/orion_full_v1.json"
ok = run([C / "orion_job.py", "meta", "--spec", spec, "--line", LINE, "--out", work / "meta"], "meta")
for f in (work / "meta").glob("*.json"):
    (out / f"meta_{f.name}").write_bytes(f.read_bytes())
if ok:
    ok = run([C / "orion_job.py", "sample", "--spec", spec, "--line", LINE, "--meta", work / "meta", "--out",
              out / "sample"], "sample")
if ok:
    import pandas as pd
    s = pd.read_parquet(out / "sample" / f"{LINE}.parquet", columns=["cell", "selected"])
    cells = sorted(s.loc[s["selected"], "cell"].astype(str))
    log["sample"] = {"sha256": sha(out / "sample" / f"{LINE}.parquet"), "sha256_colab": P["sample_sha256_colab"],
                     "rows": int(len(s)), "selected": len(cells), "expected_selected": P["expected_cells"],
                     "selected_cells_digest": hashlib.sha256("\n".join(cells).encode()).hexdigest()}
    log["sample"]["bytes_equal_colab"] = log["sample"]["sha256"] == P["sample_sha256_colab"]
    print(json.dumps({"sample": log["sample"]}), flush=True)
    del s, cells
    ok = log["sample"]["selected"] == P["expected_cells"]
if ok:
    ok = run([C / "orion_job.py", "shards", "--spec", spec, "--line", LINE, "--sample", out / "sample", "--axis",
              DS / "gene_names.csv", "--stage", work / "stage", "--out", out / "shards", "--data-root", OUT,
              "--runtime-manifest", env, "--part", PART], "shards")
done = out / "shards" / "complete.json"
if done.is_file():
    log["complete"] = json.loads(done.read_text())
    print(json.dumps({"complete": log["complete"]}), flush=True)
close(ok and done.is_file())
'''


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def kaggle(args, config_dir):
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    r = subprocess.run([exe, *args], env={**os.environ, "KAGGLE_CONFIG_DIR": config_dir}, capture_output=True, text=True)
    print((r.stdout or "")[-1500:], (r.stderr or "")[-1500:])
    return r


def snapshot_members(tar_path: Path) -> dict:
    with tarfile.open(tar_path) as t:
        return {m.name: hashlib.sha256(t.extractfile(m).read()).hexdigest() for m in t.getmembers() if m.isfile()}


def colab_sample_sha(line: str) -> str:
    """The sample of the Colab meta job, as the committed manifests of its shard jobs declare it (one value)."""
    found = set()
    for path in sorted((ORION / "jobs").glob(f"j16_orion_full_shards_{line.lower()}_*_manifest.json")):
        for i in json.loads(path.read_text(encoding="utf-8"))["inputs"]:
            if i["id"] == f"sample_{line}.parquet":
                found.add(i["sha256"])
    if len(found) != 1:
        sys.exit(f"{line}: {len(found)} sample hashes in the Colab manifests")
    return found.pop()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--code-stage", type=Path, required=True, help="the staged folder of the code dataset (r1)")
    p.add_argument("--code-slug", default="vcc-ingest-code-r1")
    p.add_argument("--line", choices=["HCT116", "HEK293T"], required=True)
    p.add_argument("--part", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--launch-log", type=Path, help="JSON lines, one per push, appended")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--repush", action="store_true",
                   help="push a stage built earlier and refused by Kaggle (5 batch CPU sessions at most): its files "
                        "must be the ones this build would write")
    a = p.parse_args()
    if a.stage.exists() and not a.repush:
        sys.exit(f"refusing: {a.stage} exists")
    staged = json.loads((a.code_stage / "staged.json").read_text(encoding="utf-8"))
    tar_path = a.code_stage / "code_snapshot.tar.gz"
    if sha256_file(tar_path) != staged["code_snapshot.tar.gz"]:
        sys.exit("the staged tar is not the one its staged.json names")
    members = snapshot_members(tar_path)
    spec_path = ORION / "specs/orion_full_v1.json"
    if sha256_file(spec_path) != members.get(SPEC_IN_SNAPSHOT):
        sys.exit("the spec in the repository is not the one in the snapshot")
    expected = json.loads(spec_path.read_text(encoding="utf-8"))["lines"][a.line]["expected"]["cells_pass_filter"]
    params = {"line": a.line, "part": a.part, "job": a.slug.replace("-", "_"), "code_slug": a.code_slug,
              "commit": a.commit, "snapshot_sha256": staged["code_snapshot.tar.gz"], "members": members,
              "axis_sha256": staged["gene_names.csv"], "expected_cells": expected,
              "sample_sha256_colab": colab_sample_sha(a.line)}
    text = KERNEL.replace("__PARAMS__", json.dumps(params, indent=1))
    compile(text, "run.py", "exec")
    metadata = json.dumps(
        {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
         "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False, "enable_internet": True,
         "dataset_sources": [f"{a.owner}/{a.code_slug}"], "kernel_sources": [], "competition_sources": []}, indent=1)
    if a.stage.exists():
        same = ((a.stage / "run.py").read_bytes() == text.encode("utf-8")
                and (a.stage / "kernel-metadata.json").read_text() == metadata)
        if not same:
            sys.exit(f"refusing: {a.stage} holds another build")
    else:
        a.stage.mkdir(parents=True)
        (a.stage / "run.py").write_text(text, encoding="utf-8", newline="\n")
        (a.stage / "kernel-metadata.json").write_text(metadata)
    record = {"slug": f"{a.owner}/{a.slug}", "line": a.line, "part": a.part, "stage": a.stage.as_posix(),
              "run_sha256": sha256_file(a.stage / "run.py"), "snapshot_sha256": params["snapshot_sha256"],
              "commit": a.commit}
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed\n{json.dumps(record)}")
        return
    r = kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)
    answer = ((r.stdout or "") + (r.stderr or "")).strip()
    # The CLI exits 0 also when Kaggle refuses the push ("Kernel push error: Maximum batch CPU session count of 5
    # reached", 3/10 17:12): only its sentence says whether the kernel started.
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
