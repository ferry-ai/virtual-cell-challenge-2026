"""Build reviewable Stack inference notebook from the *finished* prompt bundle.

No dataset upload, checkpoint download, inference or quota use occurs here.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepared", type=Path, required=True, help="Colab folder containing bundle/ and bundle.tar.gz")
    p.add_argument("--out", type=Path, required=True, help="New review folder; contains no dataset matrices")
    p.add_argument("--stage-data", type=Path, help="Optional NEW data staging folder outside repository")
    p.add_argument("--owner", default="davideferante")
    p.add_argument("--use-preparation-receipt", action="store_true",
                   help="Freeze trusted preparation hashes; runtime still verifies all archive/file bytes before loading weights")
    a = p.parse_args()
    if a.out.exists() or (a.stage_data is not None and a.stage_data.exists()):
        raise FileExistsError("Outputs must be new")
    setup = HERE / "stack_setup_r1"
    snapshot = json.loads((setup / "setup_manifest.json").read_text())
    code_archive = setup / "code_snapshot.tar.gz"
    if sha(code_archive) != snapshot["code_archive_sha256"]:
        raise ValueError("Frozen preparation code archive changed")
    allow = json.loads((HERE / "STACK_ALLOWLIST.json").read_text())
    bundle_archive, bundle = a.prepared / "bundle.tar.gz", a.prepared / "bundle"
    manifest = json.loads((bundle / "bundle.json").read_text())
    registered = json.loads((HERE / "stack_plan_r1.json").read_text())
    realized = json.loads((a.prepared / "plan.json").read_text())
    if realized != registered or sha(a.prepared / "plan.json") != manifest["plan_sha256"]:
        raise ValueError("Preparation did not use the reviewed plan fields")
    if sorted(p.name for p in bundle.iterdir()) != sorted(allow["inference_bundle_files"]):
        raise ValueError("Prepared bundle has unexpected files")
    if a.use_preparation_receipt:
        receipt = {}
        for line in (a.prepared / "bundle_hashes.txt").read_text(encoding="utf-8").splitlines():
            checksum, path = line.split(maxsplit=1)
            receipt[Path(path).name] = checksum
        if receipt.get("bundle.json") != sha(bundle / "bundle.json"):
            raise ValueError("Trusted preparation receipt does not match bundle manifest")
        bundle_digest = receipt["bundle.tar.gz"]
        if len(bundle_digest) != 64 or any(c not in "0123456789abcdef" for c in bundle_digest):
            raise ValueError("Invalid preparation archive checksum")
    else:
        for name, expected in manifest["files"].items():
            if sha(bundle / name) != expected:
                raise ValueError(f"Prepared file changed: {name}")
        with tarfile.open(bundle_archive, "r:gz") as archive:
            members = [m for m in archive.getmembers() if not m.isdir()]
            names = [m.name.removeprefix("./") for m in members]
            if len(names) != len(set(names)) or set(names) != set(allow["inference_bundle_files"]):
                raise ValueError("Prepared archive list mismatch")
            for member, name in zip(members, names):
                if not member.isfile() or hashlib.sha256(archive.extractfile(member).read()).hexdigest() != sha(bundle / name):
                    raise ValueError("Archive and prepared directory differ")
        bundle_digest = sha(bundle_archive)
    review = {"dataset": f"{a.owner}/vcc-stack-prompts-r1", "kernel": f"{a.owner}/vcc-stack-pilot-r1",
              "private": True, "bundle_archive_sha256": bundle_digest,
              "freeze_verification": "trusted preparation receipt; full bytes checked remotely before weights" if a.use_preparation_receipt else "all bytes verified locally and remotely",
              "bundle_archive_bytes": bundle_archive.stat().st_size,
              "bundle_manifest_sha256": sha(bundle / "bundle.json"), "bundle_files": allow["inference_bundle_files"],
              "plan_sha256": manifest["plan_sha256"], "registered_plan_sha256": snapshot["plan_sha256"],
              "plan_equivalence": "Every JSON field equals frozen registration; platform line endings may differ",
              "targets": manifest["targets"],
              "code_archive_sha256": snapshot["code_archive_sha256"], "code_files": snapshot["files"],
              "model_repository": allow["model_repository"], "model_revision": allow["model_revision"],
              "model_files": allow["model_files"], "batch_size": 1, "device": "cuda:0",
              "isolated_python": "3.11.13", "python_bootstrap": "Astral uv==0.8.22 in isolated pip --target directory; uv venv --seed",
              "resource_guards": {"ram_available_immediately_before_loader_bytes": 6 * 1024**3,
                                   "disk_reserve_before_loader_bytes": 2 * 1024**3,
                                   "initial_free_disk_bytes": 16 * 1024**3},
              "model_download_and_dependency_install_required": True,
              "download_authorization": "User confirmed personal noncommercial entry; root verified FAQ applicability",
              "source_destination_truth_in_inference": False}
    payload64 = base64.b64encode(code_archive.read_bytes()).decode("ascii")
    runner = (HERE / "stack_remote_runner.py").read_text()
    cell = runner + "\n\nmain(" + repr(payload64) + ", " + repr(review) + ")\n"
    compile(cell, "stack_kaggle.py", "exec")
    a.out.mkdir(parents=True)
    notebook = {"nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "cells": [{"cell_type": "markdown", "id": "scope", "metadata": {}, "source": [
            "# Stack: pilot privato su 12 target development\n",
            "Prompt K562 e soli controlli HepG2. Pesi pubblici congelati, nessun fine-tuning o scoring.\n"]},
            {"cell_type": "code", "id": "inference", "metadata": {}, "execution_count": None,
             "outputs": [], "source": cell.splitlines(keepends=True)}]}
    metadata = {"id": review["kernel"], "title": "VCC Stack Pilot R1", "code_file": "stack_pilot_r1.ipynb",
                "language": "python", "kernel_type": "notebook", "is_private": True,
                "enable_gpu": True, "enable_tpu": False, "enable_internet": True,
                "machine_shape": "NvidiaTeslaT4", "dataset_sources": [review["dataset"]],
                "competition_sources": [], "kernel_sources": [], "model_sources": []}
    save(a.out / metadata["code_file"], notebook)
    save(a.out / "kernel-metadata.json", metadata)
    save(a.out / "review_manifest.json", review)
    # Same frozen payload, explicit mounted paths; no Kaggle dependency.
    colab = runner + "\n\nmain(" + repr(payload64) + ", " + repr(review) + ", " + (
        "bundle_archive='/content/drive/MyDrive/vcc2026/runs/lead_stack_2026-09-29_r2/bundle.tar.gz', "
        "work='/content/drive/MyDrive/vcc2026/runs/lead_stack_infer_2026-09-29_r1', "
        "scratch='/content/lead_stack_scratch_r1')\n")
    with (a.out / "colab_stack_infer_r1.py").open("x", encoding="utf-8", newline="\n") as f:
        f.write(colab)
    if a.stage_data is not None:
        a.stage_data.mkdir(parents=True)
        shutil.copyfile(bundle_archive, a.stage_data / "bundle.tar.gz")
        save(a.stage_data / "input_manifest.json", {k: review[k] for k in [
            "dataset", "private", "bundle_archive_sha256", "bundle_archive_bytes", "bundle_manifest_sha256", "targets"]})
        save(a.stage_data / "dataset-metadata.json", {"id": review["dataset"], "title": "VCC Stack Prompts R1",
            "licenses": [{"name": "other"}], "isPrivate": True,
            "description": "Private pilot: selected public K562 cells, HepG2 controls and frozen transfer effects. "
                           "Original licenses apply. No destination perturbation truth or credentials.",
            "resources": [{"path": "bundle.tar.gz"}, {"path": "input_manifest.json"}]})
    save(a.out / "artifact_hashes.json", {p.name: {"bytes": p.stat().st_size, "sha256": sha(p)}
                                        for p in sorted(a.out.iterdir()) if p.is_file()})
    print(json.dumps({"review": str(a.out), "stage_data": str(a.stage_data),
                      "bundle_sha256": review["bundle_archive_sha256"], "private": True}))


if __name__ == "__main__":
    main()
