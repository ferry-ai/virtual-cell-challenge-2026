"""Build and queue one generic R-LAB Colab job: ingest units into contract shards, then publish them on Kaggle.

The job is a JSON spec for rlab_job.py (units with adapter and arguments; paths may use {IN}, {AXIS}, {WORK}, {DRIVE})
plus optional publications (Kaggle dataset slugs of the training account). This writes, never over an existing file:
- in the Drive setup folder: the code snapshot (if absent), preflight.py (if absent), the spec and the preflight
  manifest of the job;
- the launcher, in this report's jobs folder and in the chosen Drive queue (`queue` or `queue2`).

The launcher follows docs/ERRORI.md: it waits for every setup file by sha256, measures the runtime, runs the shared
preflight on the runtime, then rlab_job.py, then publish_kaggle.py for each publication. Sources read by HTTP byte
ranges cannot be hashed whole before the run without downloading them: for those the declared limit is the one of the
plan (§6.5), an ETag checked on every range and a sha256 of every shard written. A job with --publish-only publishes
the shards of an earlier job and runs nothing else. --reuse passes an earlier job's folder to rlab_job.py, which
skips the shards whose receipt and sha256 still match. --stop builds a launcher that only stops, on the runtime of
its queue, the rlab_job.py process of an earlier job (the dispatchers have no stop command; 30/09, job 106).
The local preflight of the manifest runs before the launcher is queued, and a failure refuses the queue (docs/ERRORI.md).

    python colab_job.py --job j04_h1_trainval_r1 --number 093 --queue queue2 --spec spec.json \
        --snapshot <tar.gz> --commit <sha> --setup rlab_setup_2026-09-30_r3 --publish ALL=rlab-h1-vcc2025-trainval
    python colab_job.py --job p01_hepg2_r1 --number 091 --queue queue --publish-only <Drive job dir> ...
    python colab_job.py --job s01_stop_j07_r4 --number 107 --queue queue2 --stop j07_replogle_ess_rpe1_r4
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
REPO = HERE.parents[2]
REPORT = HERE.relative_to(REPO).as_posix()
GDRIVE = "G:/Il mio Drive/vcc2026"
DRIVE = "/content/drive/MyDrive/vcc2026"
OUT_ROOT = "data/processed/corpus_cellulare_2026-09-30"
OWNER = "davideferrante11"
PREFLIGHT = REPO / "reports/analisi/lead_scientist_2026-09-29/learning/preflight.py"
INCIDENTS = ["E-20260929-002", "E-20260929-003", "E-20260929-005", "E-20260929-007"]

LAUNCHER = """#!/usr/bin/env bash
# R-LAB {job}. Built by {report}/colab_job.py; code snapshot of commit {commit}. Do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE={drive}
SETUP="$DRIVE/runs/{setup}"
WORK=/content/work/rlab_{job}
OUT="$DRIVE/{out_root}/{job}"
REC="$SETUP/receipts/{job}"
PY=/usr/bin/python3
echo "job {job} start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1
test -x "$PY"; test ! -e "$WORK"; test ! -e "$REC"
{out_test}
bootstrap_ready() {{
  sha256sum -c --quiet - <<'SUMS' || return 1
{sums}
SUMS
}}
for attempt in $(seq 1 45); do
  if bootstrap_ready; then break; fi
  echo "waiting for the setup files by hash, attempt $attempt/45"; sleep 20
done
bootstrap_ready
copy() {{ for i in 1 2 3 4 5; do cp "$1" "$2" && return 0; echo "copy of $1 failed, attempt $i"; sleep 30; done; return 1; }}
mkdir -p "$WORK/code" "$WORK/in" "$REC"
tar -xzf "$SETUP/code_snapshot.tar.gz" -C "$WORK/code"
C="$WORK/code/{report}"
export RLAB_SNAPSHOT_SHA256={snapshot_sha} RLAB_COMMIT={commit}
"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata
command -v kaggle >/dev/null || "$PY" -m pip install -q kaggle
"$PY" "$C/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/{job}_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
{run}
{publish}
rm -rf "$WORK"
echo "job {job} end $(date -u +%FT%TZ)"
"""


STOP = """#!/usr/bin/env bash
# R-LAB {job}: stop the rlab_job.py process of job {target} on this runtime, if it runs. Built by {report}/colab_job.py.
# Reason: {reason}
set -uo pipefail
PAT='rlab_job[.]py --spec [^ ]*/{target}_spec[.]json'
echo "job {job} start $(date -u +%FT%TZ) host=$(hostname)"
ps -eo pid,etimes,rss,args | grep -E "$PAT" | grep -v grep || echo "no process of {target} on this runtime"
if pkill -TERM -f "$PAT"; then echo "TERM sent"; sleep 30; pkill -KILL -f "$PAT" && echo "KILL sent"; fi
ps -eo pid,etimes,rss,args | grep -E "$PAT" | grep -v grep || echo "{target}: not running"
free -g | head -2
echo "job {job} end $(date -u +%FT%TZ)"
"""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def place(src: Path, dest: Path) -> str:
    """Copy src to dest unless dest already holds the same bytes; refuse different bytes under the same name."""
    digest = sha256(src)
    if dest.exists():
        if sha256(dest) != digest:
            sys.exit(f"refusing: {dest} exists with different bytes")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    return digest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--job", required=True)
    p.add_argument("--number", required=True)
    p.add_argument("--queue", choices=["queue", "queue2"], required=True)
    p.add_argument("--spec", type=Path)
    p.add_argument("--publish-only", help="Drive-relative folder of an earlier job whose shards are published")
    p.add_argument("--publish", action="append", default=[], metavar="UNIT=SLUG", help="UNIT may be ALL")
    p.add_argument("--reuse", action="append", default=[],
                   help="Drive-relative folder of an earlier job whose verified shards are reused (repeatable)")
    p.add_argument("--stop", metavar="JOB_ID", help="build a launcher that only stops this job's rlab_job.py")
    p.add_argument("--reason", default="", help="with --stop: why, written in the launcher")
    p.add_argument("--snapshot", type=Path)
    p.add_argument("--commit")
    p.add_argument("--setup")
    p.add_argument("--jobs-dir", type=Path, default=HERE / "jobs_colab")
    p.add_argument("--owner", default=OWNER, help="Kaggle account that receives the datasets")
    p.add_argument("--secrets", default="rlab_secrets", help="Drive folder under runs/ holding that account's token")
    a = p.parse_args()
    number_is_free(a)
    if a.stop:
        write_and_queue(a, STOP.format(job=a.job, target=a.stop, report=REPORT, reason=a.reason or "not given"))
        return
    if not (a.snapshot and a.commit and a.setup):
        sys.exit("give --snapshot, --commit and --setup")
    if bool(a.spec) == bool(a.publish_only):
        sys.exit("give either --spec or --publish-only")
    setup_local = Path(GDRIVE) / "runs" / a.setup
    setup_rt = f"{DRIVE}/runs/{a.setup}"
    snap_sha = place(a.snapshot, setup_local / "code_snapshot.tar.gz")
    pre_sha = place(PREFLIGHT, setup_local / "preflight.py")
    declared = [{"id": "code_snapshot", "paths": {"local": str(setup_local / "code_snapshot.tar.gz"),
                                                   "runtime": f"{setup_rt}/code_snapshot.tar.gz"},
                 "bytes": a.snapshot.stat().st_size, "sha256": snap_sha}]
    sums = [f"{pre_sha}  {setup_rt}/preflight.py", f"{snap_sha}  {setup_rt}/code_snapshot.tar.gz"]
    work = f"/content/work/rlab_{a.job}"
    outputs = [{"id": "stage", "paths": {"local": f"C:/Users/ferra/vcc2026-data/unused/{a.job}/stage",
                                        "runtime": f"{work}/stage"}, "must_be_absent": True}]
    if a.spec:
        spec_name = f"{a.job}_spec.json"
        spec_sha = place(a.spec, setup_local / spec_name)
        declared.append({"id": "spec", "paths": {"local": str(setup_local / spec_name), "runtime": f"{setup_rt}/{spec_name}"},
                         "bytes": a.spec.stat().st_size, "sha256": spec_sha})
        sums.append(f"{spec_sha}  {setup_rt}/{spec_name}")
        outputs.append({"id": "shards", "paths": {"local": f"{GDRIVE}/{OUT_ROOT}/{a.job}",
                                                 "runtime": f"{DRIVE}/{OUT_ROOT}/{a.job}"}, "must_be_absent": True})
        reuse = (" --reuse " + " ".join(f'"$DRIVE/{r}"' for r in a.reuse)) if a.reuse else ""
        run = (f'"$PY" "$C/rlab_job.py" --spec "$SETUP/{spec_name}" --stage "$WORK/stage" --out "$OUT" '
               f'--runtime-manifest "$REC/environment_manifest_colab.json"{reuse} --set IN="$WORK/in" '
               f'AXIS="$WORK/in/gene_names.csv" WORK="$WORK" DRIVE="$DRIVE"')
        out_test, job_dir = 'test ! -e "$OUT"', '"$OUT"'
    else:
        run, out_test, job_dir = "# publish only: the shards of an earlier job", "", f'"$DRIVE/{a.publish_only}"'
        done = Path(GDRIVE) / a.publish_only / "complete.json"
        if not done.is_file():
            sys.exit(f"refusing: {done} is absent")
        declared.append({"id": "earlier_complete", "paths": {"local": str(done),
                                                             "runtime": f"{DRIVE}/{a.publish_only}/complete.json"},
                         "bytes": done.stat().st_size, "sha256": sha256(done)})
    publish = []
    for item in a.publish:
        unit, slug = item.split("=", 1)
        publish.append(f'"$PY" "$C/publish_kaggle.py" --job-dir {job_dir} --unit {unit} --owner {a.owner} --slug {slug} '
                       f'--config-dir "$DRIVE/runs/{a.secrets}" --stage "$WORK/publish_{slug}" '
                       f'--receipt "$REC/publish_{slug}.json"')
    manifest = {"schema_version": 1, "job_id": a.job, "incident_ids": INCIDENTS, "inputs": declared, "outputs": outputs,
                "target_checks": [],
                "environment": {"python": {"paths": {"local": sys.executable, "runtime": "/usr/bin/python3"}},
                                "packages": {"h5py": None, "numpy": None, "pandas": None, "scipy": None},
                                "imports": ["h5py", "scipy.sparse"], "probes": []},
                "declared_limits": "sources read by HTTP byte ranges are not hashed whole before the run: every range "
                                   "is checked against the ETag of the file, every shard is hashed (plan §6.5); "
                                   "anndata and kaggle are installed on the runtime when absent"}
    man_path = a.jobs_dir / f"{a.job}_manifest.json"
    a.jobs_dir.mkdir(parents=True, exist_ok=True)
    if man_path.exists():
        sys.exit(f"refusing: {man_path} exists")
    man_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    man_sha = place(man_path, setup_local / f"{a.job}_manifest.json")
    sums.insert(1, f"{man_sha}  {setup_rt}/{a.job}_manifest.json")
    receipt = a.jobs_dir / "receipts_local" / f"{a.job}_preflight_local.json"
    pre = subprocess.run([sys.executable, str(PREFLIGHT), "validate", "--manifest", str(man_path), "--site", "local",
                          "--receipt", str(receipt)], capture_output=True, text=True)
    print(pre.stdout.strip()[-400:])
    if pre.returncode != 0:
        sys.exit(f"refusing to queue: the local preflight failed ({pre.stderr.strip()[-400:]})")
    text = LAUNCHER.format(job=a.job, report=REPORT, commit=a.commit, drive=DRIVE, setup=a.setup, out_root=OUT_ROOT,
                           out_test=out_test, sums="\n".join(sums), snapshot_sha=snap_sha, run=run,
                           publish="\n".join(publish) if publish else "# no publication")
    write_and_queue(a, text)


def number_is_free(a) -> None:
    """A queue number is used once across both queues, their retired folders and this report's launchers."""
    places = [a.jobs_dir] + [Path(GDRIVE) / "runs" / q / sub for q in ("queue", "queue2") for sub in ("", "ritirati")]
    taken = sorted(str(q) for d in places if d.is_dir() for q in d.glob(f"{a.number}_*"))
    if taken:
        sys.exit(f"refusing: queue number {a.number} is taken: {taken}")


def write_and_queue(a, text: str) -> None:
    script = a.jobs_dir / f"{a.number}_rlab_{a.job}.sh"
    queue = Path(GDRIVE) / "runs" / a.queue / script.name
    a.jobs_dir.mkdir(parents=True, exist_ok=True)
    script.write_bytes(text.encode("utf-8"))
    shutil.copyfile(script, queue)
    print(f"queued {queue} ({sha256(queue)[:16]})")


if __name__ == "__main__":
    main()
