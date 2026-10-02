"""Build the two Colab verification jobs of the cloud archive (setup folder, preflight manifests, queue scripts).

Job 130 verifies, right away, what was only on Drive before the migration (manifest B). Job 131 waits for the
marker UPLOAD_COMPLETE_r1.json, written by the watcher when the laptop upload ends, checks that manifest A has
the sha256 the marker names, then verifies the Drive mirror (manifest A) with retries for uploads in flight.
Both only read data and write new receipt folders. Files are staged locally first; nothing is overwritten.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parents[2]
RUN = Path(r"C:\Users\ferra\vcc2026-data\processed\archivio_cloud_2026-10-02\r1")
STAGE = RUN / "setup_verify_r1"
NAME = "archivio_verify_2026-10-02_r1"
G_SETUP = Path(r"G:\Il mio Drive\vcc2026\runs") / NAME
R_SETUP = f"/content/drive/MyDrive/vcc2026/runs/{NAME}"
LOCAL_PY = r"C:\Users\ferra\vcc2026-data\.venv\Scripts\python.exe"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def item(id_: str, rel: str) -> dict:
    p = STAGE / rel
    return {"id": id_, "paths": {"local": str(G_SETUP / rel), "runtime": f"{R_SETUP}/{rel}"},
            "bytes": p.stat().st_size, "sha256": sha(p)}


def job_manifest(job_id: str, inputs: list[dict], out: str) -> dict:
    return {"schema_version": 1, "job_id": job_id,
            "incident_ids": ["E-20260929-003", "E-20260929-005", "E-20260929-007"],
            "inputs": inputs,
            "outputs": [{"id": "receipts", "paths": {"local": str(G_SETUP / out), "runtime": f"{R_SETUP}/{out}"},
                         "must_be_absent": True}],
            "target_checks": [],
            "environment": {"python": {"paths": {"local": LOCAL_PY, "runtime": "/usr/bin/python3"}},
                            "packages": {"h5py": None, "numpy": None, "pandas": None}, "imports": ["h5py", "numpy"],
                            "probes": []},
            "declared_limits": "the data files are the objects under test, not inputs: their expected sha256 come from "
                               "the manifests, whose integrity verify_drive.py checks against a sidecar; anndata is "
                               "installed on the runtime when absent, only to open samples"}


BOOT = """bootstrap_ready() {{
  sha256sum -c --quiet - <<'SUMS' || return 1
{sums}
SUMS
}}
for attempt in $(seq 1 45); do
  if bootstrap_ready; then break; fi
  echo "waiting for the setup files by hash, attempt $attempt/45"; sleep 20
done
bootstrap_ready
"""

HEAD = """#!/usr/bin/env bash
# Cloud archive {tag}. Built by reports/sorgenti/archivio_cloud_2026-10-02/build_verify_jobs.py. Do not edit by hand.
# Reads data on Drive and writes only a new receipt folder; no training, no download, no upload elsewhere.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="{setup}"
PY=/usr/bin/python3
echo "job {job} start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1
test -x "$PY"; test ! -e "$SETUP/{out}"; test ! -e "$SETUP/preflight_runtime_{tag}.json"
"""


def main() -> None:
    if STAGE.exists() or G_SETUP.exists():
        sys.exit(f"refusing: {STAGE} or {G_SETUP} exists")
    (STAGE / "manifests_b").mkdir(parents=True)
    (STAGE / "manifests_a").mkdir()
    shutil.copy2(HERE / "verify_drive.py", STAGE / "verify_drive.py")
    shutil.copy2(REPO / "reports/analisi/lead_scientist_2026-09-29/learning/preflight.py", STAGE / "preflight.py")
    for f in ("b_drive_preesistente_r2.json", "b_drive_preesistente_r2.sha256"):
        shutil.copy2(RUN / "manifests" / f, STAGE / "manifests_b" / f)
    code = [item("verify_drive", "verify_drive.py"), item("preflight", "preflight.py")]
    jm_b = job_manifest("archivio_verify_b_r1", code + [item("manifest_b", "manifests_b/b_drive_preesistente_r2.json"),
                                                         item("manifest_b_sidecar", "manifests_b/b_drive_preesistente_r2.sha256")],
                        "out_b_r1")
    jm_a = job_manifest("archivio_verify_a_r1", code, "out_a_r1")
    for name, jm in (("job_manifest_b.json", jm_b), ("job_manifest_a.json", jm_a)):
        (STAGE / name).write_text(json.dumps(jm, indent=1), encoding="utf-8")
    sums_b = "\n".join(f"{sha(STAGE / r)}  {R_SETUP}/{r}" for r in
                       ("verify_drive.py", "preflight.py", "job_manifest_b.json",
                        "manifests_b/b_drive_preesistente_r2.json", "manifests_b/b_drive_preesistente_r2.sha256"))
    sums_a = "\n".join(f"{sha(STAGE / r)}  {R_SETUP}/{r}" for r in ("verify_drive.py", "preflight.py", "job_manifest_a.json"))
    job_b = (HEAD.format(tag="verify_b_r1", setup=R_SETUP, job="130_archivio_verify_b_r1", out="out_b_r1")
             + BOOT.format(sums=sums_b) +
             '"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/job_manifest_b.json" --site runtime '
             '--receipt "$SETUP/preflight_runtime_verify_b_r1.json" --attempts 3 --interval-seconds 20\n'
             '"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata\n'
             '"$PY" "$SETUP/verify_drive.py" --manifest-dir "$SETUP/manifests_b" --data-root "$DRIVE/data" '
             '--out "$SETUP/out_b_r1" --rounds 2 --wait-s 600\n'
             'echo "job 130_archivio_verify_b_r1 end $(date -u +%FT%TZ)"\n')
    job_a = (HEAD.format(tag="verify_a_r1", setup=R_SETUP, job="131_archivio_verify_a_r1", out="out_a_r1")
             + BOOT.format(sums=sums_a) +
             '"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/job_manifest_a.json" --site runtime '
             '--receipt "$SETUP/preflight_runtime_verify_a_r1.json" --attempts 3 --interval-seconds 20\n'
             '# The laptop upload ends with the marker; it names the sha256 of manifest A.\n'
             'while [ ! -f "$SETUP/UPLOAD_COMPLETE_r1.json" ]; do echo "$(date -u +%T) waiting for the upload marker"; sleep 300; done\n'
             'for attempt in $(seq 1 60); do\n'
             '  if "$PY" - "$SETUP" <<\'PYEOF\'\n'
             'import hashlib, json, pathlib, sys\n'
             's = pathlib.Path(sys.argv[1]); m = json.loads((s / "UPLOAD_COMPLETE_r1.json").read_text())\n'
             'p = s / "manifests_a" / m["manifest"]\n'
             'sys.exit(0 if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == m["manifest_sha256"] '
             'and (s / "manifests_a" / m["sidecar"]).is_file() else 1)\n'
             'PYEOF\n'
             '  then break; fi\n'
             '  echo "waiting for manifest A to match the marker, attempt $attempt/60"; sleep 60\n'
             'done\n'
             '"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata\n'
             '"$PY" "$SETUP/verify_drive.py" --manifest-dir "$SETUP/manifests_a" --data-root "$DRIVE/data" '
             '--out "$SETUP/out_a_r1" --rounds 24 --wait-s 900\n'
             'echo "job 131_archivio_verify_a_r1 end $(date -u +%FT%TZ)"\n')
    for name, text in (("130_archivio_verify_b_r1.sh", job_b), ("131_archivio_verify_a_r1.sh", job_a)):
        (STAGE / name).write_bytes(text.encode("utf-8"))  # LF line endings for bash
    build = {"stage": str(STAGE), "drive_setup": str(G_SETUP), "runtime_setup": R_SETUP,
             "files": {str(p.relative_to(STAGE)).replace("\\", "/"): sha(p) for p in sorted(STAGE.rglob("*")) if p.is_file()}}
    (STAGE / "build.json").write_text(json.dumps(build, indent=1), encoding="utf-8")
    print(json.dumps(build, indent=1))


if __name__ == "__main__":
    main()
