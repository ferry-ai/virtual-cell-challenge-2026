"""Queue again the two verifications of the cloud archive that a lost Colab runtime cut short on 3/10 (jobs 130 and 131,
built by reports/sorgenti/archivio_cloud_2026-10-02/build_verify_jobs.py; last heartbeat 13:21 UTC).

Jobs 133 (manifest B) and 134 (manifest A) read the same manifests from the r1 setup folder on Drive and the receipts
the r1 runs wrote before the loss (--already of verify_resume.py): a file already "verified" with the same expected
bytes and sha256 is not read again. Everything they consume is declared with its sha256 (docs/ERRORI.md) and checked
on the runtime before any read; they write only new folders (setup r2, out_<b|a>_r2). Manifest A must still hash as
the upload marker UPLOAD_COMPLETE_r1.json says. Nothing in the r1 folder is changed.

    py.cmd requeue_verify.py            (refuses if the setup r2 folder or a queue number exists)
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
G_RUNS = Path(r"G:\Il mio Drive\vcc2026\runs")
R_RUNS = "/content/drive/MyDrive/vcc2026/runs"
R1, R2 = "archivio_verify_2026-10-02_r1", "archivio_verify_2026-10-03_r2"
STAGE = Path(r"C:\Users\ferra\vcc2026-data\processed\ingestione_completa_2026-10-03\setup_verify_r2")
LOCAL_PY = r"C:\Users\ferra\vcc2026-data\.venv\Scripts\python.exe"
PREFLIGHT = REPO / "reports/analisi/lead_scientist_2026-09-29/learning/preflight.py"
JOBS = {"b": ("133", "manifests_b", "b_drive_preesistente_r2", 2, 600),
        "a": ("134", "manifests_a", "a_specchio_r1", 3, 600)}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(8 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def item(id_: str, folder: str, rel: str, local: Path) -> dict:
    return {"id": id_, "paths": {"local": str(G_RUNS / folder / rel), "runtime": f"{R_RUNS}/{folder}/{rel}"},
            "bytes": local.stat().st_size, "sha256": sha(local)}


def main() -> None:
    if STAGE.exists() or (G_RUNS / R2).exists():
        sys.exit(f"refusing: {STAGE} or {G_RUNS / R2} exists")
    taken = [p for n, *_ in JOBS.values() for q in ("queue", "queue2") for p in (G_RUNS / q).glob(f"{n}_*")]
    if taken:
        sys.exit(f"refusing: queue numbers taken {taken}")
    marker = json.loads((G_RUNS / R1 / "UPLOAD_COMPLETE_r1.json").read_text(encoding="utf-8"))
    if sha(G_RUNS / R1 / "manifests_a" / marker["manifest"]) != marker["manifest_sha256"]:
        sys.exit("manifest A does not hash as the upload marker says")
    STAGE.mkdir(parents=True)
    shutil.copy2(HERE / "verify_resume.py", STAGE / "verify_resume.py")
    shutil.copy2(PREFLIGHT, STAGE / "preflight.py")
    (G_RUNS / R2).mkdir()                    # the local preflight checks the Drive copies: they go there first
    for f in ("verify_resume.py", "preflight.py"):
        shutil.copy2(STAGE / f, G_RUNS / R2 / f)
    code = [item("verify_resume", R2, "verify_resume.py", STAGE / "verify_resume.py"),
            item("preflight", R2, "preflight.py", STAGE / "preflight.py")]
    built = {}
    for tag, (number, mdir, mname, rounds, wait) in JOBS.items():
        r1_inputs = [item(f"manifest_{tag}", R1, f"{mdir}/{mname}.json", G_RUNS / R1 / mdir / f"{mname}.json"),
                     item(f"manifest_{tag}_sidecar", R1, f"{mdir}/{mname}.sha256", G_RUNS / R1 / mdir / f"{mname}.sha256"),
                     item(f"receipts_{tag}_r1", R1, f"out_{tag}_r1/verify_receipts.jsonl",
                          G_RUNS / R1 / f"out_{tag}_r1" / "verify_receipts.jsonl")]
        out = f"out_{tag}_r2"
        manifest = {"schema_version": 1, "job_id": f"archivio_verify_{tag}_r2",
                    "incident_ids": ["E-20260929-003", "E-20260929-005", "E-20260929-007"],
                    "inputs": code + r1_inputs,
                    "outputs": [{"id": "receipts", "paths": {"local": str(G_RUNS / R2 / out), "runtime": f"{R_RUNS}/{R2}/{out}"},
                                 "must_be_absent": True}],
                    "target_checks": [],
                    "environment": {"python": {"paths": {"local": LOCAL_PY, "runtime": "/usr/bin/python3"}},
                                    "packages": {"h5py": None, "numpy": None, "pandas": None},
                                    "imports": ["h5py", "numpy"], "probes": []},
                    "declared_limits": "the data files are the objects under test, not inputs; the r1 receipts are "
                                       "inputs: a file they list as verified with the same expected sha256 is not read "
                                       "again (verify_resume.py --already)"}
        (STAGE / f"job_manifest_{tag}.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        shutil.copy2(STAGE / f"job_manifest_{tag}.json", G_RUNS / R2 / f"job_manifest_{tag}.json")
        receipt = STAGE / f"preflight_local_{tag}.json"
        pre = subprocess.run([LOCAL_PY, str(PREFLIGHT), "validate", "--manifest", str(STAGE / f"job_manifest_{tag}.json"),
                              "--site", "local", "--receipt", str(receipt)], capture_output=True, text=True)
        if pre.returncode:
            sys.exit(f"local preflight failed for {tag}: {pre.stdout[-400:]} {pre.stderr[-400:]}")
        sums = [f"{x['sha256']}  {x['paths']['runtime']}" for x in manifest["inputs"]]
        sums.append(f"{sha(STAGE / f'job_manifest_{tag}.json')}  {R_RUNS}/{R2}/job_manifest_{tag}.json")
        job = f"{number}_archivio_verify_{tag}_r2"
        text = f"""#!/usr/bin/env bash
# Cloud archive verify_{tag}_r2: job {'130' if tag == 'b' else '131'} again after the lost runtime of 3/10, resuming from its receipts.
# Built by reports/sorgenti/ingestione_completa_2026-10-03/requeue_verify.py. Do not edit by hand.
# Reads data on Drive and writes only a new receipt folder; no training, no download, no upload elsewhere.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
R1="{R_RUNS}/{R1}"
SETUP="{R_RUNS}/{R2}"
PY=/usr/bin/python3
echo "job {job} start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1; df -h /content/drive | tail -1
test -x "$PY"; test ! -e "$SETUP/{out}"; test ! -e "$SETUP/preflight_runtime_verify_{tag}_r2.json"
bootstrap_ready() {{
  sha256sum -c --quiet - <<'SUMS' || return 1
{chr(10).join(sums)}
SUMS
}}
for attempt in $(seq 1 45); do
  if bootstrap_ready; then break; fi
  echo "waiting for the setup files by hash, attempt $attempt/45"; sleep 20
done
bootstrap_ready
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/job_manifest_{tag}.json" --site runtime --receipt "$SETUP/preflight_runtime_verify_{tag}_r2.json" --attempts 3 --interval-seconds 20
"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata
"$PY" "$SETUP/verify_resume.py" --manifest-dir "$R1/{mdir}" --data-root "$DRIVE/data" --out "$SETUP/{out}" --rounds {rounds} --wait-s {wait} --already "$R1/out_{tag}_r1/verify_receipts.jsonl"
echo "job {job} end $(date -u +%FT%TZ)"
"""
        (STAGE / f"{job}.sh").write_bytes(text.encode("utf-8"))
        built[job] = sha(STAGE / f"{job}.sh")
    for job in built:
        shutil.copyfile(STAGE / f"{job}.sh", G_RUNS / "queue" / f"{job}.sh")
    (STAGE / "build.json").write_text(json.dumps({"jobs": built, "setup": str(G_RUNS / R2),
                                                  "files": {p.name: sha(p) for p in sorted(STAGE.iterdir()) if p.is_file()}},
                                                 indent=1), encoding="utf-8")
    print(json.dumps(built, indent=1))


if __name__ == "__main__":
    main()
