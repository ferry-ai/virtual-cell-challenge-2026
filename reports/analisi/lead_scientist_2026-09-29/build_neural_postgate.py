"""Freeze offline follow-up code; create notebooks only after all five seed-0 folds pass."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REPORT = HERE.relative_to(REPO).as_posix()
FAMILIES = ["k562", "cd4", "orion", "ipsc", "rpe1"]
R1_SHA = "283d4f592f87fcd969a4dec80d2138ce1568eeef1ac2c4dd0485e641185780bf"
R3_SHA = "f7324778e5d7225552734e2c7303353f46dee6c01e9d455703adce3b9b105860"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def members(data):
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        result = {}
        for member in archive.getmembers():
            if not member.isfile() or member.name in result or Path(member.name).is_absolute() or ".." in Path(member.name).parts:
                raise ValueError("Unexpected code archive member")
            result[member.name] = archive.extractfile(member).read()
        return result


def archive_bytes(files):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, data in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size, member.mode, member.mtime = len(data), 0o644, 0
            archive.addfile(member, io.BytesIO(data))
    return gzip.compress(stream.getvalue(), mtime=0)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def freeze(out, r3_archive, panel_path):
    original = (HERE / "kaggle_neural_r1/review/runtime_payload.tar.gz").read_bytes()
    if digest(original) != R1_SHA:
        raise ValueError("Original r1 runtime archive changed")
    files = members(original)
    old_reader = files[f"{REPORT}/read_neural_sources.py"]
    files[f"{REPORT}/neural_reader/r1/read_neural_sources.py"] = old_reader
    extras = ["read_neural_sources.py", "read_neural_verified.py", "verify_neural_runs.py",
              "EMENDAMENTO_LETTORE_NEURALE_01.md", "t25_source_adapter.py", "test_t25_source_adapter.py",
              "ADATTATORE_T25.md", "neural_postgate_runner.py"]
    for name in extras:
        files[f"{REPORT}/{name}"] = (HERE / name).read_bytes()
    if digest(files[f"{REPORT}/read_neural_sources.py"]) != "21b936b387ec734e0aaeb4b85f982f127a465a84fb3a77dc89917190881a8243":
        raise ValueError("Corrected reader differs from its documented mechanical fix")
    r3 = r3_archive.read_bytes()
    if digest(r3) != R3_SHA:
        raise ValueError("Library dependency snapshot differs from r3")
    for name, data in members(r3).items():
        if name.startswith("src/vcc2026/") and name.endswith(".py"):
            files[name] = data
    import csv
    with panel_path.open(encoding="utf-8-sig", newline="") as stream:
        targets = list(dict.fromkeys(row["target_gene"] for row in csv.DictReader(stream)))
    if len(targets) != 300 or "non-targeting" in targets:
        raise ValueError("Production target axis is not the official 300-target panel")
    files[f"{REPORT}/production_targets.txt"] = ("\n".join(targets) + "\n").encode()
    payload = archive_bytes(files)
    reference = json.loads((HERE / "kaggle_neural_r1/review/review_manifest.json").read_text())
    manifest = {"prepared_utc": datetime.now(timezone.utc).isoformat(), "state": "frozen plan, no notebook and no launch",
                "original_r1_payload_sha256": R1_SHA, "source_dependency_r3_sha256": R3_SHA,
                "payload_sha256": digest(payload), "payload_bytes": len(payload),
                "dataset": reference["dataset"], "dataset_manifest_sha256": reference["dataset_manifest_sha256"],
                "official_panel_source_sha256": digest(panel_path.read_bytes()), "official_targets": len(targets),
                "allowlist": [{"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(files.items())],
                "proposed_kernels": {"seed1": "davidmaisterx/vcc-lead-neural-seed1-r1",
                                     "production": "davidmaisterx/vcc-lead-neural-production-r1"},
                "requires_positive_verified_seed0_gate": True, "new_large_data_upload": False,
                "production_adapter_cellular_advantage_inherited": False}
    out.mkdir(parents=True, exist_ok=False)
    with (out / "runtime_payload.tar.gz").open("xb") as stream:
        stream.write(payload)
    save(out / "plan_manifest.json", manifest)
    return manifest, payload


def verified_gate(runs, plan, frozen_files):
    # Read using only the reviewed mechanical reader correction and guard.
    for name in ("read_neural_sources.py", "verify_neural_runs.py"):
        if (HERE / name).read_bytes() != frozen_files[f"{REPORT}/{name}"]:
            raise ValueError(f"Local gate implementation changed: {name}")
    guard = load_module(HERE / "verify_neural_runs.py", "postgate_verify")
    reader = load_module(HERE / "read_neural_sources.py", "postgate_read")
    provenance = guard.verify(runs)
    verdict, _ = reader.readout(runs)
    expected_code = {name.rsplit("/", 1)[-1]: digest(frozen_files[name]) for name in frozen_files
                     if name.rsplit("/", 1)[-1] in {"neural_sources.py", "train_neural_sources.py", "PROTOCOLLO_NEURALE.md", "pool.py"}}
    evidence = {}
    for run in runs:
        manifest = json.loads((run / "manifest.json").read_text())
        family = manifest["options"]["holdout"]
        if manifest["options"]["seed"] != 0 or manifest["options"]["regime"] != "C":
            raise ValueError("Gate must come from the original seed-0 C regime")
        if guard.canonical_code(manifest["code_hashes"]) != expected_code:
            raise ValueError("Gate training code differs from frozen r1")
        if manifest["data_files"]["manifest.json"]["sha256"] != plan["dataset_manifest_sha256"]:
            raise ValueError("Gate dataset differs from the frozen r2")
        evidence[family] = {}
        for name in ("manifest.json", "per_target.csv", "summary.json"):
            path = run / name
            evidence[family][name] = {"bytes": path.stat().st_size, "sha256": digest(path.read_bytes())}
    gate = {"created_utc": datetime.now(timezone.utc).isoformat(), "verified_families": FAMILIES,
            "seed": 0, "verdict": verdict, "provenance": provenance, "fold_evidence": evidence,
            "reader_sha256": digest(frozen_files[f"{REPORT}/read_neural_sources.py"]),
            "guard_sha256": digest(frozen_files[f"{REPORT}/verify_neural_runs.py"])}
    runner = load_module(HERE / "neural_postgate_runner.py", "postgate_runtime_guard")
    if (HERE / "neural_postgate_runner.py").read_bytes() != frozen_files[f"{REPORT}/neural_postgate_runner.py"]:
        raise ValueError("Runtime gate code changed after plan freeze")
    runner.gate_passes(gate)
    return gate


def build(out, plan, payload, runs):
    frozen_files = members(payload)
    gate = verified_gate(runs, plan, frozen_files)
    out.mkdir(parents=True, exist_ok=False)
    save(out / "seed0_gate.json", gate)
    gate_sha = digest(json.dumps(gate, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
    runner = frozen_files[f"{REPORT}/neural_postgate_runner.py"].decode("utf-8")
    for mode, kernel in plan["proposed_kernels"].items():
        folder = out / mode
        folder.mkdir()
        review = {"kernel": kernel, "mode": mode, "private": True, "dataset": plan["dataset"],
                  "dataset_manifest_sha256": plan["dataset_manifest_sha256"], "allowlist": plan["allowlist"],
                  "payload_sha256": plan["payload_sha256"], "seed0_gate_sha256": gate_sha,
                  "same_training_as_seed0": True, "only_training_difference": "seed1" if mode == "seed1" else "holdout none",
                  "accelerator": "NvidiaTeslaT4", "new_large_data_upload": False,
                  "no_network_or_installs_in_runtime": True, "submission": False}
        cell = runner + "\n\nmain(" + repr(base64.b64encode(payload).decode()) + ", " + repr(review) + ", " + repr(gate) + ")\n"
        compile(cell, "postgate_notebook", "exec")
        filename = kernel.split("/")[1] + ".ipynb"
        nb = {"nbformat": 4, "nbformat_minor": 5,
              "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
              "cells": [{"cell_type": "code", "id": "conditional-run", "metadata": {}, "execution_count": None,
                         "outputs": [], "source": cell.splitlines(keepends=True)}]}
        save(folder / filename, nb)
        save(folder / "kernel-metadata.json", {"id": kernel, "title": "VCC Lead Neural " + mode,
             "code_file": filename, "language": "python", "kernel_type": "notebook", "is_private": True,
             "enable_gpu": True, "enable_tpu": False, "enable_internet": False, "machine_shape": "NvidiaTeslaT4",
             "dataset_sources": [plan["dataset"]], "kernel_sources": [], "competition_sources": [], "model_sources": []})
        save(folder / "review_manifest.json", review)
        save(folder / "artifact_hashes.json", {p.name: digest(p.read_bytes()) for p in folder.iterdir() if p.is_file()})
    print(json.dumps({"out": str(out), "gate_passed": True, "pushed": False, "kernels": plan["proposed_kernels"]}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--freeze-plan", action="store_true")
    p.add_argument("--r3-archive", type=Path)
    p.add_argument("--panel", type=Path)
    p.add_argument("--frozen-plan", type=Path)
    p.add_argument("--seed0-runs", nargs=5, type=Path)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    if args.freeze_plan:
        if args.r3_archive is None or args.panel is None or args.seed0_runs or args.frozen_plan:
            p.error("Freeze requires only archive and panel; no outcome-dependent notebook is created")
        plan, _ = freeze(args.out, args.r3_archive, args.panel)
        print(json.dumps({"out": str(args.out), "payload_sha256": plan["payload_sha256"], "notebooks_created": False,
                          "files": len(plan["allowlist"]), "push_ready": False}))
    else:
        if args.frozen_plan is None or args.seed0_runs is None:
            p.error("Notebook creation requires frozen plan and all five completed seed-0 runs")
        plan = json.loads((args.frozen_plan / "plan_manifest.json").read_text())
        payload = (args.frozen_plan / "runtime_payload.tar.gz").read_bytes()
        if digest(payload) != plan["payload_sha256"]:
            raise ValueError("Frozen plan payload changed")
        build(args.out, plan, payload, args.seed0_runs)


if __name__ == "__main__":
    main()
