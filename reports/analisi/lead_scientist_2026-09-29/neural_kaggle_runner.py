"""Runtime template: execute all five preregistered C folds, preserving failures.

The builder appends a main call with the frozen payload and review manifest.
No dataset upload, network request, package installation or production prediction.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import traceback


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write("\n")


def command_run(command, log_path, *, cwd, env):
    with log_path.open("x", encoding="utf-8") as log:
        with subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, bufsize=1) as child:
            for line in child.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
            return child.wait()


def main(payload64, review):
    os.environ.update({"CUDA_VISIBLE_DEVICES": "0", "OMP_NUM_THREADS": "2",
                       "OPENBLAS_NUM_THREADS": "2", "MKL_NUM_THREADS": "2",
                       "PYTHONHASHSEED": "0", "PYTHONUNBUFFERED": "1"})
    work = Path("/kaggle/working/neural_sources_r1")
    work.mkdir()
    save(work / "runtime_review.json", review)
    save(work / "started.json", {"utc": utc(), "status": "preflight"})
    payload = base64.b64decode(payload64, validate=True)
    if hashlib.sha256(payload).hexdigest() != review["payload_sha256"]:
        raise ValueError("Frozen code payload hash mismatch")
    code = work / "code"
    expected = {item["path"]: item for item in review["code_allowlist"]}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        members = archive.getmembers()
        if {m.name for m in members} != set(expected) or len(members) != len(expected):
            raise ValueError("Payload differs from the reviewed five-file allowlist")
        for member in members:
            target = (code / member.name).resolve()
            if not member.isfile() or not target.is_relative_to(code.resolve()):
                raise ValueError("Non-regular or escaping code archive entry")
            content = archive.extractfile(member).read()
            if hashlib.sha256(content).hexdigest() != expected[member.name]["sha256"]:
                raise ValueError(f"Code hash mismatch: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(content)
    dataset = Path("/kaggle/input/vcc-rete-contesti-r2")
    if not dataset.is_dir():
        candidates = [p for p in Path("/kaggle/input").rglob("manifest.json")
                      if "vcc-rete-contesti-r2" in p.parts]
        if len(candidates) != 1:
            raise FileNotFoundError("Cannot uniquely locate the reviewed existing dataset")
        dataset = candidates[0].parent
    if sha256(dataset / "manifest.json") != review["dataset_manifest_sha256"]:
        raise ValueError("Dataset manifest differs from the reviewed r2 snapshot")
    data_manifest = json.loads((dataset / "manifest.json").read_text())
    if data_manifest["format"] != "rete_contesti/1":
        raise ValueError("Unexpected dataset format")
    import numpy as np
    import pandas as pd
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("This reviewed run requires a free Kaggle CUDA GPU; CPU fallback is disabled")
    environment = {"utc": utc(), "python": sys.version, "platform": platform.platform(),
                   "cuda_visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
                   "torch_cuda": torch.version.cuda, "cuda_device_count_visible": torch.cuda.device_count(),
                   "gpu_name": torch.cuda.get_device_name(0), "versions": {}}
    for package in ("torch", "numpy", "pandas", "scipy", "kaggle"):
        try:
            environment["versions"][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            environment["versions"][package] = None
    save(work / "environment.json", environment)
    print(json.dumps(environment, indent=2), flush=True)
    files = []
    for name, expected_bytes in data_manifest["bytes"].items():
        path = dataset / name
        actual_bytes = path.stat().st_size
        if actual_bytes != expected_bytes:
            raise ValueError(f"Dataset file size mismatch: {name}")
        entry = {"name": name, "bytes": actual_bytes,
                 "sha256": sha256(path) if actual_bytes < 30_000_000 else None}
        if name.endswith(".npy"):
            array = np.load(path, mmap_mode="r", allow_pickle=False)
            entry.update({"shape": list(array.shape), "dtype": str(array.dtype),
                          "mmap": isinstance(array, np.memmap), "writeable": bool(array.flags.writeable)})
            if not entry["mmap"] or entry["writeable"]:
                raise ValueError(f"Read-only mmap requirement failed: {name}")
            if name in {"raw.npy", "se.npy", "shrunk.npy"}:
                if list(array.shape) != [data_manifest["counts"]["rows"], data_manifest["counts"]["genes"]]:
                    raise ValueError(f"Effect array dimensions differ: {name}")
            del array
        files.append(entry)
    save(work / "input_files.json", {"dataset": review["dataset"], "counts": data_manifest["counts"],
                                    "manifest_sha256": review["dataset_manifest_sha256"], "files": files,
                                    "large_array_identity": "immutable Kaggle dataset version, manifest, file sizes, shapes and dtypes"})
    report = code / "reports/analisi/lead_scientist_2026-09-29"
    families = review["fold_order"]
    outcomes = []
    for family in families:
        out = work / "folds" / f"C_{family}_s0"
        command = [sys.executable, str(report / "train_neural_sources.py"), "--data", str(dataset),
                   "--out", str(out), "--holdout", family, "--regime", "C", "--device", "cuda",
                   "--seed", "0", "--selection-seed", "20260929", "--steps", "1000",
                   "--eval-every", "50", "--patience", "5", "--batch", "16", "--gene-batch", "1024",
                   "--validation-genes", "2048", "--test-targets", "512", "--validation-targets", "128", "--lr", "0.001"]
        start = utc()
        save(work / f"start_{family}.json", {"started_utc": start, "family": family, "argv": command})
        try:
            rc = command_run(command, work / f"console_{family}.log", cwd=code, env=os.environ.copy())
            result = {"family": family, "returncode": rc, "started_utc": start, "finished_utc": utc(),
                      "out": str(out), "complete": rc == 0 and (out / "summary.json").is_file()
                                   and (out / "per_target.csv").is_file()}
        except Exception:
            result = {"family": family, "returncode": None, "started_utc": start, "finished_utc": utc(),
                      "out": str(out), "complete": False, "exception": traceback.format_exc()}
        outcomes.append(result)
        save(work / f"status_{family}.json", result)
        print(json.dumps(result), flush=True)
    all_five = len(outcomes) == 5 and all(item["complete"] for item in outcomes)
    readout_rc = None
    if all_five:
        command = [sys.executable, str(report / "read_neural_sources.py"), "--runs",
                   *[item["out"] for item in outcomes], "--out", str(work / "cross_family")]
        readout_rc = command_run(command, work / "cross_family.log", cwd=code, env=os.environ.copy())
    save(work / "completion.json", {"finished_utc": utc(), "folds": outcomes,
                                    "all_five_completed": all_five, "cross_family_returncode": readout_rc,
                                    "status": "complete" if all_five and readout_rc == 0 else "incomplete",
                                    "not_vcc_score": True, "submission_authorized_by_this_run": False})
    if not all_five or readout_rc != 0:
        raise RuntimeError("All five folds were attempted; inspect preserved status/log files. No partial-family verdict.")
