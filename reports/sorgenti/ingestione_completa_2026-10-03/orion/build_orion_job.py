"""Build and queue one Colab job of the full Orion ingestion (orion_job.py), with the launcher rules of docs/ERRORI.md.

Two kinds:
- `meta`: for one line, the metadata pass (identity and guide columns by HTTP ranges, parity with the pass of 26/09)
  and the sample of the full design (specs/orion_full_v1.json), into <out>/meta and <out>/sample;
- `shards`: for one line, the counts of the GEM files of one part (--part i/n) or of the first N files (--max-files,
  a smoke test), from the sample folder of a finished `meta` job, declared by the sha256 of its files.

Everything a job consumes is declared with its sha256 in a preflight manifest checked locally before queueing and on
the runtime before any read; outputs must not exist. The code is a snapshot (git archive) of one commit.

    python build_orion_job.py --kind meta --line HCT116 --job j16_orion_full_meta_hct116_r1 --number 135 \
        --queue queue2 --setup orion_full_setup_2026-10-03_r1 --commit <sha> --snapshot <tar.gz>
    python build_orion_job.py --kind shards --line HCT116 --part 0/2 --sample-dir <Drive-relative sample dir> ...
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
REPO = HERE.parents[3]
REPORT = HERE.relative_to(REPO).as_posix()
GDRIVE = Path(r"G:\Il mio Drive\vcc2026")
DRIVE = "/content/drive/MyDrive/vcc2026"
OUT_ROOT = "data/processed/ingestione_completa_2026-10-03"
PREFLIGHT = REPO / "reports/analisi/lead_scientist_2026-09-29/learning/preflight.py"
LOCAL_PY = sys.executable
INCIDENTS = ["E-20260929-002", "E-20260929-003", "E-20260929-005", "E-20260929-007"]
SNAPSHOT_PATHS = [f"{REPORT}/{f}" for f in ("orion_job.py", "common.py", "campionamento_v2.py",
                                              "specs/orion_full_v1.json")] + \
    [f"reports/sorgenti/corpus_cellulare_2026-09-30/{f}" for f in
     ("adapters.py", "contracts.py", "fetch.py", "inspect_remote.py", "publish_kaggle.py", "rlab_job.py",
      "validate_runtime.py")] + \
    [f"reports/sorgenti/universo_2026-09-26/orion_{x}/manifest.json" for x in ("hct116", "hek293t")]

LAUNCHER = """#!/usr/bin/env bash
# Full ingestion, Orion {kind} {job}. Built by {report}/build_orion_job.py; code snapshot of commit {commit}.
# Do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE={drive}
SETUP="$DRIVE/runs/{setup}"
WORK=/content/work/{job}
OUT="$DRIVE/{out_root}/{job}"
REC="$SETUP/receipts/{job}"
PY=/usr/bin/python3
echo "job {job} start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1; df -h /content/drive | tail -1
test -x "$PY"; test ! -e "$WORK"; test ! -e "$REC"; test ! -e "$OUT"
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
"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata
"$PY" -c "import pyarrow" 2>/dev/null || "$PY" -m pip install -q pyarrow
"$PY" "$WORK/code/reports/sorgenti/corpus_cellulare_2026-09-30/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/{job}_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
mkdir -p "$OUT"
{run}
rm -rf "$WORK"
echo "job {job} end $(date -u +%FT%TZ)"
"""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def place(src: Path, dest: Path) -> str:
    digest = sha256(src)
    if dest.exists():
        if sha256(dest) != digest:
            sys.exit(f"refusing: {dest} exists with different bytes")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    return digest


def item(id_: str, local: Path, runtime: str) -> dict:
    return {"id": id_, "paths": {"local": str(local), "runtime": runtime}, "bytes": local.stat().st_size,
            "sha256": sha256(local)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kind", choices=["meta", "shards"], required=True)
    p.add_argument("--line", choices=["HCT116", "HEK293T"], required=True)
    p.add_argument("--job", required=True)
    p.add_argument("--number", required=True)
    p.add_argument("--queue", choices=["queue", "queue2"], required=True)
    p.add_argument("--setup", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--part", help="shards: i/n")
    p.add_argument("--max-files", type=int, help="shards: a smoke test on the first N files of the part")
    p.add_argument("--sample-dir", help="shards: Drive-relative folder holding <LINE>.parquet, .sha256 and .json")
    p.add_argument("--jobs-dir", type=Path, default=HERE / "jobs")
    a = p.parse_args()
    taken = [q for d in (a.jobs_dir, GDRIVE / "runs" / "queue", GDRIVE / "runs" / "queue2") if d.is_dir()
             for q in d.glob(f"{a.number}_*")]
    if taken:
        sys.exit(f"refusing: queue number {a.number} is taken: {taken}")
    with __import__("tarfile").open(a.snapshot) as t:
        names = set(t.getnames())
    missing = [s for s in SNAPSHOT_PATHS if s not in names]
    if missing:
        sys.exit(f"the snapshot lacks {missing}")
    setup_l, setup_r = GDRIVE / "runs" / a.setup, f"{DRIVE}/runs/{a.setup}"
    place(a.snapshot, setup_l / "code_snapshot.tar.gz")
    place(PREFLIGHT, setup_l / "preflight.py")
    inputs = [item("code_snapshot", setup_l / "code_snapshot.tar.gz", f"{setup_r}/code_snapshot.tar.gz"),
              item("preflight", setup_l / "preflight.py", f"{setup_r}/preflight.py")]
    spec = f'"$C/specs/orion_full_v1.json"'
    out_rt = f"{DRIVE}/{OUT_ROOT}/{a.job}"
    if a.kind == "meta":
        run = (f'"$PY" "$C/orion_job.py" meta --spec {spec} --line {a.line} --out "$OUT/meta"\n'
               f'"$PY" "$C/orion_job.py" sample --spec {spec} --line {a.line} --meta "$OUT/meta" --out "$OUT/sample"')
    else:
        if not a.sample_dir:
            sys.exit("shards needs --sample-dir")
        sd = GDRIVE / a.sample_dir
        for f in (f"{a.line}.parquet", f"{a.line}.parquet.sha256", f"{a.line}.json"):
            if not (sd / f).is_file():
                sys.exit(f"{sd / f} is absent")
            inputs.append(item(f"sample_{f}", sd / f, f"{DRIVE}/{a.sample_dir}/{f}"))
        extra = (f" --part {a.part}" if a.part else "") + (f" --max-files {a.max_files}" if a.max_files else "")
        run = (f'"$PY" "$C/orion_job.py" shards --spec {spec} --line {a.line} --sample "$DRIVE/{a.sample_dir}" '
               f'--axis "$WORK/in/gene_names.csv" --stage "$WORK/stage" --out "$OUT/shards" --data-root "$DRIVE/data" '
               f'--runtime-manifest "$REC/environment_manifest_colab.json"{extra}')
    manifest = {"schema_version": 1, "job_id": a.job, "incident_ids": INCIDENTS, "inputs": inputs,
                "outputs": [{"id": "out", "paths": {"local": str(GDRIVE / OUT_ROOT / a.job), "runtime": out_rt},
                             "must_be_absent": True}],
                "target_checks": [],
                "environment": {"python": {"paths": {"local": LOCAL_PY, "runtime": "/usr/bin/python3"}},
                                "packages": {"numpy": None, "pandas": None, "scipy": None},
                                "imports": ["numpy", "pandas", "scipy.sparse"], "probes": []},
                "declared_limits": "the Orion parquet files are read from Hugging Face: the meta phase by byte ranges "
                                   "with the ETag checked, the shards phase whole, with size and LFS sha256 of the "
                                   "list frozen on 26/09; anndata and pyarrow are installed when absent"}
    a.jobs_dir.mkdir(parents=True, exist_ok=True)
    man = a.jobs_dir / f"{a.job}_manifest.json"
    if man.exists():
        sys.exit(f"refusing: {man} exists")
    man.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    man_sha = place(man, setup_l / f"{a.job}_manifest.json")
    pre = subprocess.run([LOCAL_PY, str(PREFLIGHT), "validate", "--manifest", str(man), "--site", "local",
                          "--receipt", str(a.jobs_dir / f"{a.job}_preflight_local.json")], capture_output=True, text=True)
    if pre.returncode:
        sys.exit(f"refusing to queue: local preflight failed: {pre.stdout[-400:]} {pre.stderr[-400:]}")
    sums = [f"{x['sha256']}  {x['paths']['runtime']}" for x in inputs] + [f"{man_sha}  {setup_r}/{a.job}_manifest.json"]
    text = LAUNCHER.format(kind=a.kind, job=a.job, report=REPORT, commit=a.commit, drive=DRIVE, setup=a.setup,
                           out_root=OUT_ROOT, sums="\n".join(sums), run=run)
    script = a.jobs_dir / f"{a.number}_{a.job}.sh"
    script.write_bytes(text.encode("utf-8"))
    shutil.copyfile(script, GDRIVE / "runs" / a.queue / script.name)
    print(f"queued {GDRIVE / 'runs' / a.queue / script.name} ({sha256(script)[:16]})")


if __name__ == "__main__":
    main()
