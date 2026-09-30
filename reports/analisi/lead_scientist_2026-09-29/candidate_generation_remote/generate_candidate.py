"""Reviewable remote stage-45/48 launcher. No VCC submission command exists here."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import traceback


ARCHIVE_SHA = "f7324778e5d7225552734e2c7303353f46dee6c01e9d455703adce3b9b105860"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write("\n")


def checked_file(path, expected_hash, expected_bytes=None):
    if expected_bytes is not None and path.stat().st_size != expected_bytes:
        raise ValueError(f"Input size mismatch: {path}")
    if sha256(path) != expected_hash:
        raise ValueError(f"Input full SHA256 mismatch: {path}")


def safe_child(root, relative):
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes input root: {relative}")
    return candidate


def check_confirmation(selection, phi):
    if selection.get("truth") != "full":
        raise ValueError("Confirmation truth is not full")
    eligible = [c for c in selection["comparisons"]
                if c["amplitude"] == 1.5 and c["phi_scale"] == phi and c["generator"] == "pooled"]
    if len(eligible) != 1:
        raise ValueError("Requested amplitude/dispersion is absent or duplicated in confirmation")
    row = eligible[0]
    if not (row["passes_confirmation"] is True and row["delta_projection"] >= 0.005
            and len(row["per_seed_delta"]) == 3 and all(v > 0 for v in row["per_seed_delta"])
            and row["paired_target_bootstrap_interval"][0] > 0):
        raise ValueError("Requested candidate did not pass preregistered confirmation")
    return row


def run(command, log, *, cwd, env):
    print("COMMAND", json.dumps(command), flush=True)
    with log.open("x", encoding="utf-8") as stream:
        with subprocess.Popen(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, bufsize=1) as child:
            for line in child.stdout:
                stream.write(line)
                stream.flush()
                print(line, end="", flush=True)
            rc = child.wait()
    if rc:
        raise subprocess.CalledProcessError(rc, command)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/vcc2026"))
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--manifest-sha256", required=True)
    p.add_argument("--confirmation", type=Path, required=True)
    p.add_argument("--confirmation-sha256", required=True)
    p.add_argument("--registration", type=Path, required=True)
    p.add_argument("--registration-sha256", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--phi-scale", required=True, type=float, choices=[0.5, 1.0])
    p.add_argument("--scratch-root", type=Path, default=Path("/content"))
    p.add_argument("--destination", required=True, help="New path relative to the project Drive root")
    p.add_argument("--execute", action="store_true", help="Run only after explicit review and authorization")
    args = p.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.run_id):
        raise ValueError("Unsafe run ID")
    for path, expected in [(args.manifest, args.manifest_sha256),
                           (args.confirmation, args.confirmation_sha256),
                           (args.registration, args.registration_sha256)]:
        checked_file(path, expected)
    inputs = json.loads(args.manifest.read_text(encoding="utf-8"))
    selection = json.loads(args.confirmation.read_text(encoding="utf-8"))
    registration = json.loads(args.registration.read_text(encoding="utf-8"))
    if not isinstance(registration, dict) or not registration:
        raise ValueError("Prediction preregistration is empty")
    confirmed = check_confirmation(selection, args.phi_scale)
    archive_info = inputs["code_archive"]
    if archive_info["sha256"] != ARCHIVE_SHA:
        raise ValueError("Manifest must refer to the reviewed r3 archive")
    archive = safe_child(args.drive_root, archive_info["drive_relative"])
    checked_file(archive, ARCHIVE_SHA, archive_info["bytes"])
    sources = []
    for entry in inputs["files"]:
        source = safe_child(args.drive_root, entry["drive_relative"])
        checked_file(source, entry["sha256"], entry["bytes"])
        sources.append((source, entry))
    destination = safe_child(args.drive_root, args.destination)
    scratch = args.scratch_root / f"lead_candidate_{args.run_id}"
    if destination.exists() or scratch.exists():
        raise FileExistsError("Use a new destination and run ID; no overwrites or cleanup")
    command45 = [sys.executable, "scripts/45_generate_prediction.py", "--run-id", args.run_id + "gen",
                 "--trial", "trial-ext-profile", "--out", str(scratch / "gen"),
                 "--controls-dir", str(scratch / "data/raw/controls"), "--contexts", "A,B,C",
                 "--cells-per-pert", "400", "--seed", "20260912", "--effects-scale", "1.5",
                 "--gene-dispersion", "--gene-dispersion-scale", str(args.phi_scale)]
    for context in "ABC":
        command45 += ["--effects", f"{context}={scratch / 'data/processed/effects_t25_2026-09-27' / f'effects_{context}.npz'}"]
    command48 = [sys.executable, "scripts/48_package_prediction.py", "--run-id", args.run_id + "pack",
                 "--prediction", str(scratch / "gen/prediction.h5ad"), "--out", str(scratch / "pack"),
                 "--workdir", str(scratch / "pack/temp"), "--contexts", "A,B,C",
                 "--genes", str(scratch / "data/raw/controls/gene_names.csv"),
                 "--perts", str(scratch / "data/raw/controls/pert_counts.csv"), "--zstd-threads", "2"]
    review = {"created_utc": datetime.now(timezone.utc).isoformat(), "run_id": args.run_id,
              "manifest_sha256": args.manifest_sha256, "confirmation_sha256": args.confirmation_sha256,
              "registration_sha256": args.registration_sha256, "confirmed_candidate": confirmed,
              "code_archive_sha256": ARCHIVE_SHA, "commands": [command45, command48],
              "destination": str(destination), "scratch": str(scratch), "submission": False}
    print(json.dumps(review, indent=2), flush=True)
    if not args.execute:
        print("PREFLIGHT ONLY: no code extraction, data copy, generation, packaging or Drive write")
        return
    if version("vcc-cli") != "0.2.0":
        raise ValueError("Install the reviewed vcc-cli==0.2.0 before executing this launcher")
    if shutil.disk_usage(args.scratch_root).free < 20 * 1024**3:
        raise ValueError("Less than 20 GiB scratch space; stage checks remain enabled too")
    scratch.mkdir()
    destination.mkdir(parents=True)
    status = {"status": "started", "submission": False}
    try:
        save(scratch / "launch_review.json", review)
        for label, path in [("input_manifest", args.manifest), ("confirmation_selection", args.confirmation),
                            ("prediction_registration", args.registration)]:
            shutil.copyfile(path, scratch / f"{label}.json")
        environment = {"python": sys.version, "versions": {pkg: version(pkg) for pkg in
                       ("vcc-cli", "numpy", "scipy", "pandas", "h5py", "anndata", "PyYAML", "zstandard")}}
        save(scratch / "environment.json", environment)
        code = scratch / "code"
        code.mkdir()
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar.getmembers():
                target = safe_child(code, member.name)
                if not member.isfile():
                    raise ValueError("Only regular files are allowed in the frozen source archive")
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output:
                    shutil.copyfileobj(tar.extractfile(member), output)
        copied = []
        for source, entry in sources:
            target = safe_child(scratch, entry["drive_relative"])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            checked_file(target, entry["sha256"], entry["bytes"])
            copied.append({"source": str(source), "local": str(target), "sha256": entry["sha256"], "bytes": entry["bytes"]})
        save(scratch / "copied_inputs.json", copied)
        env = os.environ.copy()
        env.update({"VCC2026_DATA_ROOT": str(scratch / "data"), "PYTHONPATH": str(code / "src"),
                    "PYTHONUNBUFFERED": "1", "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2",
                    "MKL_NUM_THREADS": "2"})
        run(command45, scratch / "stage45.log", cwd=code, env=env)
        prediction_sha = sha256(scratch / "gen/prediction.h5ad")
        command48 += ["--expect-sha256", prediction_sha]
        run(command48, scratch / "stage48.log", cwd=code, env=env)
        packaging = json.loads((scratch / "pack/packaging.json").read_text())
        verification = packaging["verification"]
        if packaging["exit_code"] != 0 or verification["official_container_validator"] != "passed":
            raise ValueError("Package did not pass official container verification")
        if not isinstance(verification["payload_vs_input"], dict):
            raise ValueError("Missing successful bit-for-bit payload verification")
        vcc = scratch / "pack/prediction.vcc"
        checked_file(vcc, verification["archive_sha256"], verification["archive_bytes"])
        partial = destination / "prediction.vcc.partial"
        shutil.copyfile(vcc, partial)
        checked_file(partial, verification["archive_sha256"], verification["archive_bytes"])
        partial.rename(destination / "prediction.vcc")
        save(destination / "transfer_verification.json", {"sha256": verification["archive_sha256"],
              "bytes": verification["archive_bytes"], "local_vs_drive_full_sha256": "identical",
              "payload_vs_generation": "bit-identical, verified by stage 48", "submission": False})
        status.update({"status": "complete", "prediction_sha256": prediction_sha,
                       "vcc_sha256": verification["archive_sha256"]})
    except Exception:
        status.update({"status": "failed", "exception": traceback.format_exc()})
        raise
    finally:
        status["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save(scratch / "completion.json", status)
        # Preserve bounded diagnostics even if a stage fails; never copy the multi-GB h5ad.
        for parent in [scratch, scratch / "gen", scratch / "pack"]:
            if parent.exists():
                target_dir = destination if parent == scratch else destination / parent.name
                target_dir.mkdir(exist_ok=True)
                for source in parent.iterdir():
                    if source.is_file() and source.suffix in {".json", ".log", ".txt"}:
                        target = target_dir / source.name
                        if target.exists():
                            raise FileExistsError(target)
                        shutil.copyfile(source, target)


if __name__ == "__main__":
    main()
