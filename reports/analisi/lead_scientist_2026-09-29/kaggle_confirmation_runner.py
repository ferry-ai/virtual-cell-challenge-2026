"""Private Kaggle confirmation runner. Requires the completed development bundle.

This file is embedded in the notebook; importing it does not execute a job.
It never prepares new splits, runs development or changes the selected finalists.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

EXPECTED_CODE_SHA256 = "f7324778e5d7225552734e2c7303353f46dee6c01e9d455703adce3b9b105860"
DATASET_SLUG = "vcc-lead-generator-inputs-r1"
PACKAGES = ("cell-eval2", "numpy", "scipy", "pandas", "h5py", "anndata", "scanpy",
            "scikit-learn", "polars", "pyarrow", "PyYAML", "numba", "vcc-cli")


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            value.update(block)
    return value.hexdigest()


def write_json(path, obj):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(obj, stream, indent=2, default=str)
        stream.write("\n")


def extract_files(archive, destination):
    destination = destination.resolve()
    with tarfile.open(archive) as stream:
        for member in stream.getmembers():
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination) or not member.isfile():
                raise ValueError(f"Unsupported archive entry: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with stream.extractfile(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)


def versions():
    result = {}
    for name in PACKAGES:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def main():
    dataset = Path("/kaggle/input") / DATASET_SLUG
    if not dataset.exists():
        matches = list(Path("/kaggle/input").glob(f"**/{DATASET_SLUG}"))
        if len(matches) != 1:
            raise FileNotFoundError(f"Expected one private dataset mount: {matches}")
        dataset = matches[0]
    manifest = json.loads((dataset / "input_manifest.json").read_text())
    if manifest["code_archive"]["sha256"] != EXPECTED_CODE_SHA256:
        raise ValueError("Unapproved source snapshot")
    # Version 1 intentionally cannot compute: the completed selection is required.
    development_meta = json.loads((dataset / "development_bundle_manifest.json").read_text())
    if development_meta["code_archive_sha256"] != EXPECTED_CODE_SHA256:
        raise ValueError("Development used another source snapshot")
    workspace = Path("/kaggle/working/lead_confirmation_r1")
    workspace.mkdir()
    code = workspace / "code"
    code_archive = dataset / manifest["code_archive"]["upload_name"]
    if digest(code_archive) != EXPECTED_CODE_SHA256:
        raise ValueError("Source archive checksum mismatch")
    extract_files(code_archive, code)
    for item in manifest["code_files"]:
        if digest(code / item["relative_path"]) != item["sha256"]:
            raise ValueError(f"Code checksum mismatch: {item['relative_path']}")
    data = workspace / "data"
    for item in manifest["data_files"]:
        source = dataset / item["upload_name"]
        if source.stat().st_size != item["bytes"] or digest(source) != item["sha256"]:
            raise ValueError(f"Data checksum mismatch: {item['relative_path']}")
        target = data / item["relative_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source)
    development_archive = dataset / development_meta["archive"]["upload_name"]
    if digest(development_archive) != development_meta["archive"]["sha256"]:
        raise ValueError("Development bundle checksum mismatch")
    extract_files(development_archive, workspace)
    for item in development_meta["files"]:
        if digest(workspace / item["relative_path"]) != item["sha256"]:
            raise ValueError(f"Development checksum mismatch: {item['relative_path']}")
    out = workspace / "generator_r1"
    prepared = json.loads((out / "target_manifest.json").read_text())
    selection = json.loads((out / "development/selection.json").read_text())
    if prepared["design"] != "joint_14_arms_amendment_02" or prepared["truth"] != "full":
        raise ValueError("Unexpected preregistered design")
    if set(prepared["development"]) & set(prepared["confirmation"]):
        raise ValueError("Overlapping development and confirmation targets")
    finalists = selection["shortlist"]
    if not finalists:
        write_json(workspace / "confirmation_not_run.json", {"reason": "No finalist selected on development"})
        print("No positive finalist: confirmation not run.")
        return
    if len(finalists) > 2:
        raise ValueError("Too many finalists")
    expected_versions = dict(prepared["versions"])
    environment_file = out / "development_environment.json"
    if environment_file.exists():
        expected_versions.update(json.loads(environment_file.read_text())["versions"])
    if expected_versions.get("cell-eval2") != "0.16.0":
        raise ValueError("Development must use cell-eval2==0.16.0")
    requirements = ["cell-eval2==0.16.0"]
    for name in PACKAGES:
        if name in ("cell-eval2", "vcc-cli"):
            continue
        version = expected_versions.get(name)
        requirements.append(f"{name}=={version}" if version else name)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *requirements], check=True)
    actual = versions()
    discrepancies = {name: {"development": value, "confirmation": actual.get(name)}
                     for name, value in expected_versions.items()
                     if value is not None and actual.get(name) != value}
    write_json(workspace / "confirmation_environment.json", {
        "python": sys.version, "versions": actual, "development_versions": expected_versions,
        "discrepancies": discrepancies, "code_archive_sha256": EXPECTED_CODE_SHA256})
    if actual["cell-eval2"] != "0.16.0":
        raise ValueError("Scorer version differs from required 0.16.0")
    if discrepancies:
        print("WARNING: package differences recorded:", json.dumps(discrepancies), flush=True)
    arms = ["1:0"]
    for amplitude, phi_scale, generator in finalists:
        arms.append(f"bins:{amplitude:g}" if generator == "bins" else f"{amplitude:g}:{phi_scale:g}")
    os.environ.update({"VCC2026_DATA_ROOT": str(data), "PYTHONPATH": str(code / "src"),
                       "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2", "MKL_NUM_THREADS": "2"})
    command = [sys.executable, str(code / "reports/analisi/lead_scientist_2026-09-29/generator_bench.py"),
               "--phase", "run", "--data-root", str(data), "--out", str(out),
               "--split", "confirmation", "--arms", *arms]
    write_json(workspace / "confirmation_command.json", {"argv": command})
    subprocess.run(command, cwd=code, env=os.environ, check=True)


if __name__ == "__main__":
    main()
