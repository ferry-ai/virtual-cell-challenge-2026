"""Orion parts of the full ingestion as Kaggle CPU kernels (internet on), instead of a second Colab (owner, 3/10).

- `code`: create the private dataset <owner>/vcc-ingest-code-r1 with the code snapshot (the same tar.gz as the Colab
  jobs, one commit) and the official axis gene_names.csv.
- `kernel`: one kernel per (line, part). It unpacks the snapshot in /tmp, records the runtime, runs the three phases of
  orion_job.py (meta and the full sample again, deterministic, then the shards of the part) and leaves in
  /kaggle/working/<job>/ the sample, the shards with their receipts and complete.json, at most 20 GB (Kaggle's output
  limit; a HEK293T part of 8 holds about 28 GEM files). The sample's sha256 is written next to the one of the Colab
  meta job, so the two can be compared.

    python build_orion_kaggle.py code --config-dir <dir> --owner davideferrante11 --stage <new dir> \
        --snapshot <code_snapshot.tar.gz> --axis <gene_names.csv>
    python build_orion_kaggle.py kernel --config-dir <dir> --owner davideferrante11 --stage <new dir> \
        --line HEK293T --part 0/8 --slug vcc-orion-hek293t-p0of8-r1
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

KERNEL = r'''
import hashlib, json, os, subprocess, sys, tarfile, time
from pathlib import Path
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
LINE, PART, JOB, CODE_SLUG = {line}, {part}, {job}, {code_slug}
t0 = time.time()


def mount(slug):
    hits = [p for p in INPUT.glob(f"**/{{slug}}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{{slug}}: {{len(hits)}} mounts: {{hits[:3]}}")
    return hits[0]


DS = mount(CODE_SLUG)
work, code = Path("/tmp/w"), Path("/tmp/w/code")
code.mkdir(parents=True)
with tarfile.open(DS / "code_snapshot.tar.gz") as t:
    t.extractall(code)
C = code / "reports/sorgenti/ingestione_completa_2026-10-03/orion"
V = code / "reports/sorgenti/corpus_cellulare_2026-09-30/validate_runtime.py"
out = OUT / JOB
out.mkdir()
log = {{"job": JOB, "line": LINE, "part": PART, "snapshot_sha256": hashlib.sha256((DS / "code_snapshot.tar.gz").read_bytes()).hexdigest(),
        "steps": {{}}}}


def run(args, name):
    t = time.time()
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
    (out / f"{{name}}.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr[-20000:])
    log["steps"][name] = {{"returncode": r.returncode, "seconds": round(time.time() - t, 1)}}
    print(json.dumps({{name: log["steps"][name]}}), flush=True)
    return r.returncode == 0


subprocess.run([sys.executable, "-m", "pip", "install", "-q", "anndata"], capture_output=True)
os.environ.update(RLAB_SNAPSHOT_SHA256=log["snapshot_sha256"], RLAB_COMMIT={commit})
ok = run([V, "--out", out / "environment_manifest_kaggle.json", "--data-root", OUT], "runtime")
spec = C / "specs/orion_full_v1.json"
ok = run([C / "orion_job.py", "meta", "--spec", spec, "--line", LINE, "--out", work / "meta"], "meta")
if ok:
    ok = run([C / "orion_job.py", "sample", "--spec", spec, "--line", LINE, "--meta", work / "meta", "--out", out / "sample"], "sample")
if ok:
    ok = run([C / "orion_job.py", "shards", "--spec", spec, "--line", LINE, "--sample", out / "sample", "--axis",
              DS / "gene_names.csv", "--stage", work / "stage", "--out", out / "shards", "--data-root", OUT,
              "--runtime-manifest", out / "environment_manifest_kaggle.json", "--part", PART], "shards")
for f in (work / "meta").glob("*.json"):
    (out / f"meta_{{f.name}}").write_bytes(f.read_bytes())
log["seconds"] = round(time.time() - t0, 1)
log["ok"] = ok
(out / "kaggle_done.json").write_text(json.dumps(log, indent=1))
if not ok:
    raise SystemExit("a step failed: see the logs in the output")
'''


def kaggle(args, config_dir):
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    r = subprocess.run([exe, *args], env={**os.environ, "KAGGLE_CONFIG_DIR": config_dir}, capture_output=True, text=True)
    print((r.stdout or "")[-1500:], (r.stderr or "")[-1500:])
    return r


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c, k = sub.add_parser("code"), sub.add_parser("kernel")
    for q in (c, k):
        q.add_argument("--config-dir", required=True)
        q.add_argument("--owner", required=True)
        q.add_argument("--stage", type=Path, required=True)
        q.add_argument("--code-slug", default="vcc-ingest-code-r1")
        q.add_argument("--dry-run", action="store_true")
    c.add_argument("--snapshot", type=Path, required=True)
    c.add_argument("--axis", type=Path, required=True)
    k.add_argument("--line", choices=["HCT116", "HEK293T"], required=True)
    k.add_argument("--part", required=True)
    k.add_argument("--slug", required=True)
    k.add_argument("--commit", required=True)
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    a.stage.mkdir(parents=True)
    if a.cmd == "code":
        shutil.copyfile(a.snapshot, a.stage / "code_snapshot.tar.gz")
        shutil.copyfile(a.axis, a.stage / "gene_names.csv")
        (a.stage / "dataset-metadata.json").write_text(json.dumps(
            {"title": a.code_slug.replace("-", " "), "id": f"{a.owner}/{a.code_slug}", "licenses": [{"name": "other"}],
             "isPrivate": True}))
        (a.stage / "staged.json").write_text(json.dumps(
            {f: hashlib.sha256((a.stage / f).read_bytes()).hexdigest() for f in ("code_snapshot.tar.gz", "gene_names.csv")},
            indent=1))
        if not a.dry_run:
            kaggle(["datasets", "create", "-p", str(a.stage), "--dir-mode", "skip"], a.config_dir)
        return
    job = a.slug.replace("-", "_")
    text = KERNEL.format(line=repr(a.line), part=repr(a.part), job=repr(job), code_slug=repr(a.code_slug),
                         commit=repr(a.commit))
    compile(text, "run.py", "exec")
    (a.stage / "run.py").write_text(text, encoding="utf-8")
    (a.stage / "kernel-metadata.json").write_text(json.dumps(
        {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
         "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False, "enable_internet": True,
         "dataset_sources": [f"{a.owner}/{a.code_slug}"], "kernel_sources": [], "competition_sources": []}, indent=1))
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed")
        return
    kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)


if __name__ == "__main__":
    main()
