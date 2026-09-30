"""Build the R-LAB jobs J01-J03 for the Colab dispatcher: specs, fetch lists, preflight manifests, launchers.

Everything a job consumes is declared with its laptop path, its runtime path, bytes and sha256:
the locators and hashes of the downloads come from the manifests written when the same files
reached the laptop (HIPSCI on 27/09, Jurkat on 24/09; HepG2 from its fetch record on Drive). The
launchers follow docs/ERRORI.md: they wait for the setup files by hash, measure the runtime,
stage or download the inputs to the runtime's disk, run the shared preflight on the runtime, and
only then start rlab_job.py. Nothing is overwritten: the output folder must be new.

    python build_jobs.py --snapshot <code_snapshot.tar.gz> --commit <sha> --out jobs_r1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REPORT = HERE.relative_to(REPO).as_posix()
DATA = Path("C:/Users/ferra/vcc2026-data")
GDRIVE = "G:/Il mio Drive/vcc2026"
DRIVE = "/content/drive/MyDrive/vcc2026"
SETUP_NAME = "rlab_setup_2026-09-30_r1"
SETUP_RT, SETUP_LOCAL = f"{DRIVE}/runs/{SETUP_NAME}", f"{GDRIVE}/runs/{SETUP_NAME}"
OUT_RT = f"{DRIVE}/data/processed/corpus_cellulare_2026-09-30"
PY_RT = "/usr/bin/python3"
AXIS_SHA = "25bfa66715e186bebabce7ac788bbcea47e2bf59ca70be1f8f3a06f2f0e47201"
INCIDENTS = ["E-20260929-002", "E-20260929-003", "E-20260929-005", "E-20260929-007"]
GUARDS = {
    "E-20260929-002": "shards write object-dtype strings; validate_runtime.py round-trips an h5ad on the runtime first",
    "E-20260929-003": "every shard is copied to Drive and hashed as soon as it is written, with its receipt",
    "E-20260929-005": "the launcher waits for every setup file by sha256; the preflight hashes every input on the runtime",
    "E-20260929-007": "inputs are copied or downloaded to the runtime's disk and hashed there; the job never reads them from the mount",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def item(ident, local, runtime, size, digest):
    return {"id": ident, "paths": {"local": str(local), "runtime": runtime}, "bytes": int(size), "sha256": digest}


def hipsci_files() -> dict:
    manifest = json.loads((DATA / "external/hipsci/manifest.json").read_text(encoding="utf-8"))
    files = {}
    for record in manifest["records"]:
        for f in record["files"]:
            files[f["name"]] = {**f, "license": record["license"], "article": record["article"]}
    return files


def jurkat_files() -> dict:
    files = {}
    for m in sorted((DATA / "external/jurkat_gse249595/channels").glob("manifest*.json")):
        for f in json.loads(m.read_text(encoding="utf-8"))["files"]:
            files.setdefault(f["file"], f)
    return files


def environment() -> dict:
    return {"python": {"paths": {"local": sys.executable, "runtime": PY_RT}},
            "packages": {"anndata": None, "h5py": None, "numpy": None, "pandas": None, "scipy": None},
            "imports": ["anndata", "h5py", "scipy.sparse"], "probes": [],
            "probes_note": "no nullable-string probe: the shards write object-dtype strings, and "
                           "validate_runtime.py round-trips a real shard-like h5ad before the preflight"}


def axis_input(work: str) -> dict:
    return item("official_axis", DATA / "raw/controls/gene_names.csv", f"{work}/in/gene_names.csv",
                (DATA / "raw/controls/gene_names.csv").stat().st_size, AXIS_SHA)


def job_j01(work: str) -> tuple[dict, list, list, dict]:
    src = DATA / "raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad"
    fetch = json.loads(Path(f"{GDRIVE}/data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad.fetch.json").read_text())
    unit = {"name": "hepg2_nadig", "adapter": "h5ad",
            "kwargs": {"path": "{IN}/NadigOConner2024_hepg2.h5ad", "study": "hepg2_nadig", "context": "HepG2",
                       "chemistry": "10x 3'", "modality": "CRISPRi", "axis_csv": "{AXIS}", "block": 20000},
            "source": {"id": "hepg2_nadig", "license": "see Zenodo 13350497",
                       "files": [{"role": "counts h5ad", "locator": fetch["url"], "bytes": fetch["expected_bytes"],
                                  "sha256": fetch["sha256"]}]},
            "expect": {"cells": 145473}}
    spec = {"job_id": "j01_hepg2_r1", "min_free_out_bytes": 3 << 30, "units": [unit]}
    inputs = [item("hepg2_h5ad", src, f"{work}/in/NadigOConner2024_hepg2.h5ad", fetch["expected_bytes"],
                   fetch["sha256"]), axis_input(work)]
    stage = ['copy "$DRIVE/data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad" "$WORK/in/"']
    return spec, inputs, stage, {}


def job_j02(work: str) -> tuple[dict, list, list, dict]:
    files = hipsci_files()
    units, inputs, fetch = [], [], []
    screens = [("hipsci_gw_fitness", "GenomeWideScreen_FitnessGenes"),
               ("hipsci_gw_nonfitness", "GenomeWideScreen_NonFitnessGenes"),
               ("hipsci_targeted_19", "TargetedScreen")]
    for study, stem in screens:
        roles = {"counts": f"{stem}_RNA-UMI-Counts.csv.gz", "metadata": f"{stem}_Cell-Metadata.tsv.gz"}
        src_files = []
        for role, name in roles.items():
            f = files[name]
            if f["size"] != (DATA / "external/hipsci" / name).stat().st_size:
                sys.exit(f"{name}: local size differs from the download manifest")
            fetch.append({"url": f["download_url"], "bytes": f["size"], "sha256": f["local_sha256"],
                          "dest": f"{work}/in/{name}"})
            inputs.append(item(name, DATA / "external/hipsci" / name, f"{work}/in/{name}", f["size"], f["local_sha256"]))
            src_files.append({"role": role, "locator": f["download_url"], "bytes": f["size"],
                              "sha256": f["local_sha256"], "md5": f["computed_md5"]})
        units.append({"name": study, "adapter": "hipsci",
                      "kwargs": {"counts": "{IN}/" + roles["counts"], "metadata": "{IN}/" + roles["metadata"],
                                 "study": study, "axis_csv": "{AXIS}", "work": "{WORK}/buckets/" + study,
                                 "block": 20000, "cells_per_pass": 600000},
                      "source": {"id": study, "release": "Figshare 27989294 v1", "license": "MIT",
                                 "files": src_files}})
    spec = {"job_id": "j02_hipsci_r1", "min_free_out_bytes": 32 << 30, "min_free_stage_bytes": 6 << 30,
            "units": units}
    stage = ['"$PY" "$C/fetch.py" --list "$SETUP/j02_hipsci_r1_fetch.json" --receipt "$REC/fetch.json"']
    return spec, inputs + [axis_input(work)], stage, {"j02_hipsci_r1_fetch.json": fetch}


def job_j03(work: str) -> tuple[dict, list, list, dict]:
    files = jurkat_files()
    channels = sorted({n.split("_transcriptome_")[0] for n in files if "_transcriptome_matrix" in n},
                      key=lambda s: int(s.split("channel")[1]))
    if len(channels) != 16:
        sys.exit(f"expected 16 channels, found {len(channels)}")
    local_dir = DATA / "external/jurkat_gse249595"
    panel = local_dir / "table_s2_panel.csv"
    units, inputs, fetch = [], [], []
    for ch in channels:
        src_files = []
        for kind in ("transcriptome", "guides", "labels"):
            for part in ("matrix.mtx.gz", "features.tsv.gz", "barcode.tsv.gz"):
                name = f"{ch}_{kind}_{part}"
                f = files[name]
                if f["bytes"] != (local_dir / "channels" / name).stat().st_size:
                    sys.exit(f"{name}: local size differs from the download manifest")
                fetch.append({"url": f["url"], "bytes": f["bytes"], "sha256": f["sha256"], "dest": f"{work}/in/{name}"})
                inputs.append(item(name, local_dir / "channels" / name, f"{work}/in/{name}", f["bytes"], f["sha256"]))
                src_files.append({"role": f"{kind} {part}", "locator": f["url"], "bytes": f["bytes"],
                                  "sha256": f["sha256"]})
        units.append({"name": ch, "adapter": "mtx10x",
                      "kwargs": {"prefix": "{IN}/" + ch, "study": "jurkat_gse249595", "context": "Jurkat",
                                 "axis_csv": "{AXIS}", "panel_csv": "{IN}/table_s2_panel.csv", "min_umi": 100,
                                 "block": 20000},
                      "source": {"id": "jurkat_gse249595", "release": "GEO GSE249595", "license": "GEO, public",
                                 "files": src_files}})
    inputs.append(item("table_s2_panel", panel, f"{work}/in/table_s2_panel.csv", panel.stat().st_size, sha256(panel)))
    spec = {"job_id": "j03_jurkat_r1", "min_free_out_bytes": 5 << 30, "units": units}
    stage = ['"$PY" "$C/fetch.py" --list "$SETUP/j03_jurkat_r1_fetch.json" --receipt "$REC/fetch.json"',
             'cp "$SETUP/table_s2_panel.csv" "$WORK/in/"']
    return spec, inputs + [axis_input(work)], stage, {"j03_jurkat_r1_fetch.json": fetch}


LAUNCHER = """#!/usr/bin/env bash
# R-LAB {job}: {title}. Built by {report}/build_jobs.py at commit {commit}; do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE={drive}
SETUP="{setup}"
WORK=/content/work/rlab_{job}
OUT="{out}"
REC="$SETUP/receipts/{job}"
PY={py}
echo "job {job} start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1; df -h /content/drive 2>/dev/null | tail -1 || true
test -x "$PY"; test ! -e "$OUT"; test ! -e "$WORK"; test ! -e "$REC"
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
copy() {{  # a read from the Drive mount can fail (E-20260929-007): retry, the preflight hashes the copy
  for i in 1 2 3 4 5; do cp "$1" "$2" && return 0; echo "copy of $1 failed, attempt $i"; sleep 30; done; return 1
}}
mkdir -p "$WORK/code" "$WORK/in" "$REC"
tar -xzf "$SETUP/code_snapshot.tar.gz" -C "$WORK/code"
C="$WORK/code/{report}"
export RLAB_SNAPSHOT_SHA256={snapshot_sha} RLAB_COMMIT={commit}
"$PY" "$C/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
{stage}
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/{job}_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
"$PY" "$C/rlab_job.py" --spec "$SETUP/{job}_spec.json" --stage "$WORK/stage" --out "$OUT" --runtime-manifest "$REC/environment_manifest_colab.json" --set IN="$WORK/in" AXIS="$WORK/in/gene_names.csv" WORK="$WORK"
rm -rf "$WORK"
echo "job {job} end $(date -u +%FT%TZ)"
"""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--snapshot", required=True, type=Path)
    p.add_argument("--commit", required=True)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--preflight", type=Path,
                   default=REPO / "reports/analisi/lead_scientist_2026-09-29/learning/preflight.py")
    a = p.parse_args()
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    a.out.mkdir(parents=True)
    jobs = [("086", "j01_hepg2_r1", "HepG2 Nadig h5ad from Drive to contract shards", job_j01),
            ("087", "j03_jurkat_r1", "Jurkat GSE249595, 16 channels from GEO to contract shards", job_j03),
            ("088", "j02_hipsci_r1", "HIPSCI three screens from Figshare to contract shards", job_j02)]
    built = {"commit": a.commit, "snapshot": {"bytes": a.snapshot.stat().st_size, "sha256": sha256(a.snapshot)},
             "preflight_sha256": sha256(a.preflight), "setup_runtime": SETUP_RT, "setup_local": SETUP_LOCAL,
             "jobs": {}}
    for number, job, title, fn in jobs:
        work = f"/content/work/rlab_{job}"
        spec, inputs, stage, fetch = fn(work)
        (a.out / f"{job}_spec.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
        setup_files = [f"{job}_spec.json", *fetch]
        for name, listed in fetch.items():
            (a.out / name).write_text(json.dumps(listed, indent=1), encoding="utf-8")
        if job == "j03_jurkat_r1":
            setup_files.append("table_s2_panel.csv")
        declared = [item("code_snapshot", f"{SETUP_LOCAL}/code_snapshot.tar.gz", f"{SETUP_RT}/code_snapshot.tar.gz",
                         a.snapshot.stat().st_size, sha256(a.snapshot))]
        for name in setup_files:
            local = a.out / name if name != "table_s2_panel.csv" else DATA / "external/jurkat_gse249595" / name
            declared.append(item(f"setup:{name}", f"{SETUP_LOCAL}/{name}", f"{SETUP_RT}/{name}",
                                 local.stat().st_size, sha256(local)))
        manifest = {"schema_version": 1, "job_id": job, "incident_ids": INCIDENTS, "guards": GUARDS,
                    "inputs": declared + inputs,
                    "outputs": [{"id": "shards", "paths": {"local": f"{GDRIVE}/data/processed/corpus_cellulare_2026-09-30/{job}",
                                                          "runtime": f"{OUT_RT}/{job}"}, "must_be_absent": True},
                                {"id": "stage", "paths": {"local": str(DATA / f"processed/corpus_cellulare_2026-09-30/unused_{job}/stage"),
                                                         "runtime": f"{work}/stage"}, "must_be_absent": True},
                                {"id": "buckets", "paths": {"local": str(DATA / f"processed/corpus_cellulare_2026-09-30/unused_{job}/buckets"),
                                                           "runtime": f"{work}/buckets"}, "must_be_absent": True}],
                    "target_checks": [], "environment": environment()}
        (a.out / f"{job}_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        sums = [f"{sha256(a.preflight)}  {SETUP_RT}/preflight.py",
                f"{sha256(a.out / f'{job}_manifest.json')}  {SETUP_RT}/{job}_manifest.json"]
        sums += [f"{d['sha256']}  {d['paths']['runtime']}" for d in declared]
        launcher = LAUNCHER.format(job=job, title=title, report=REPORT, commit=a.commit, drive=DRIVE, setup=SETUP_RT,
                                   out=f"{OUT_RT}/{job}", py=PY_RT, sums="\n".join(sums),
                                   snapshot_sha=sha256(a.snapshot), stage="\n".join(stage))
        script = a.out / f"{number}_rlab_{job}.sh"
        script.write_bytes(launcher.encode("utf-8"))  # LF line endings: bash on the runtime
        built["jobs"][job] = {"queue_file": script.name, "units": len(spec["units"]), "inputs": len(manifest["inputs"]),
                              "input_bytes": sum(i["bytes"] for i in manifest["inputs"]),
                              "setup_files": setup_files, "out": f"{OUT_RT}/{job}",
                              "min_free_out_bytes": spec["min_free_out_bytes"]}
    (a.out / "build.json").write_text(json.dumps(built, indent=1), encoding="utf-8")
    print(json.dumps(built["jobs"], indent=1))


if __name__ == "__main__":
    main()
