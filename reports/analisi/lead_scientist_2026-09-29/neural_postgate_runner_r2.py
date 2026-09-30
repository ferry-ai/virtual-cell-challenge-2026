"""Conditional seed-1 replication or production fit on frozen r2 inputs; no submission."""
import base64
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version, PackageNotFoundError
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import traceback

FAMILIES = ["k562", "cd4", "orion", "ipsc", "rpe1"]
TRAINING_OPTIONS = {"regime": "C", "selection_seed": 20260929, "steps": 1000,
                    "eval_every": 50, "patience": 5, "batch": 16, "gene_batch": 1024,
                    "validation_genes": 2048, "test_targets": 512, "validation_targets": 128,
                    "lr": .001, "predict_contexts": "", "predict_targets": None, "plan_only": False}
RUN_SPECIFIC_OPTIONS = {"data", "out", "holdout", "device", "seed"}


def validate_seed0_options(options):
    comparable = {key: value for key, value in options.items() if key not in RUN_SPECIFIC_OPTIONS}
    if comparable != TRAINING_OPTIONS or options.get("seed") != 0 or options.get("holdout") not in FAMILIES:
        raise ValueError("Seed-0 options differ from the frozen training command and defaults")
    return True


def validate_data_manifest(expected):
    if not isinstance(expected, dict) or "manifest.json" not in expected:
        raise ValueError("Missing seed-0 input identities")
    for name, entry in expected.items():
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("Input identity must use a simple file basename")
        size, digest = entry.get("bytes"), entry.get("sha256")
        if type(size) is not int or size < 0:
            raise ValueError("Missing or invalid seed-0 input size")
        if size < 30_000_000 and digest is None:
            raise ValueError("Small seed-0 input is missing its full hash")
        if digest is not None and (not isinstance(digest, str) or len(digest) != 64
                                   or any(char not in "0123456789abcdef" for char in digest)):
            raise ValueError("Malformed seed-0 input hash")


def check_dataset_identity(dataset, expected):
    validate_data_manifest(expected)
    actual_names = {path.name for path in dataset.iterdir() if path.is_file()}
    if actual_names != set(expected):
        raise ValueError("Input file set differs from the seed-0 dataset")
    actual = {}
    for name, entry in expected.items():
        path = dataset / name
        size = path.stat().st_size
        if size != entry["bytes"]:
            raise ValueError(f"Input size differs from seed-0: {name}")
        digest = sha(path) if entry["sha256"] is not None else None
        if digest != entry["sha256"]:
            raise ValueError(f"Input hash differs from seed-0: {name}")
        actual[name] = {"bytes": size, "sha256": digest}
    return actual


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, default=str, allow_nan=False)
        stream.write("\n")


def gate_passes(gate):
    if not gate or gate.get("verified_families") != FAMILIES or gate.get("seed") != 0:
        raise ValueError("Missing independently verified five-family seed-0 evidence")
    result = gate["verdict"]
    primary = result["contrasts"]["transfer"]
    if not (result["eligible_for_cell_scorer"] is True and result["regime"] == "C"
            and result["training_seed"] == 0 and primary["macro_family_delta"] >= .01
            and primary["ci95"][0] > 0 and set(primary["per_family"]) == set(FAMILIES)
            and min(primary["per_family"].values()) >= -.01):
        raise ValueError("Seed-0 readout failed the unchanged preregistered gate")
    if set(gate["fold_evidence"]) != set(FAMILIES):
        raise ValueError("Missing fold evidence hashes")
    validate_seed0_options(gate.get("seed0_options", {}))
    validate_data_manifest(gate.get("seed0_data_files"))
    return True


def run(command, log, code, env):
    with log.open("x", encoding="utf-8") as handle:
        with subprocess.Popen(command, cwd=code, env=env, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, bufsize=1) as process:
            for line in process.stdout:
                handle.write(line)
                handle.flush()
                print(line, end="", flush=True)
            return process.wait()


def train_command(report, dataset, out, holdout, seed):
    command = [sys.executable, str(report / "train_neural_sources.py"), "--data", str(dataset),
               "--out", str(out), "--holdout", holdout, "--device", "cuda", "--seed", str(seed)]
    for key, value in TRAINING_OPTIONS.items():
        if key not in {"predict_contexts", "predict_targets", "plan_only"}:
            command.extend(["--" + key.replace("_", "-"), str(value)])
    return command


def main(payload64, review, gate):
    gate_passes(gate)
    gate_bytes = json.dumps(gate, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if hashlib.sha256(gate_bytes).hexdigest() != review["seed0_gate_sha256"]:
        raise ValueError("Gate differs from the reviewed evidence")
    mode = review["mode"]
    if mode not in {"seed1", "production"}:
        raise ValueError("Unreviewed run mode")
    os.environ.update({"CUDA_VISIBLE_DEVICES": "0", "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2",
                       "MKL_NUM_THREADS": "2", "PYTHONHASHSEED": "0", "PYTHONUNBUFFERED": "1"})
    work = Path("/kaggle/working") / f"neural_{mode}_r1"
    work.mkdir()
    save(work / "seed0_gate.json", gate)
    save(work / "runtime_review.json", review)
    save(work / "started.json", {"utc": utc(), "mode": mode})
    payload = base64.b64decode(payload64, validate=True)
    if hashlib.sha256(payload).hexdigest() != review["payload_sha256"]:
        raise ValueError("Frozen runtime payload differs")
    code = work / "code"
    expected = {entry["path"]: entry for entry in review["allowlist"]}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        members = archive.getmembers()
        if len(members) != len(expected) or {m.name for m in members} != set(expected):
            raise ValueError("Unexpected source allowlist")
        for member in members:
            target = (code / member.name).resolve()
            if not member.isfile() or not target.is_relative_to(code.resolve()):
                raise ValueError("Unsafe archive entry")
            data = archive.extractfile(member).read()
            if hashlib.sha256(data).hexdigest() != expected[member.name]["sha256"]:
                raise ValueError("Source file hash mismatch")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
    matches = [path.parent for path in Path("/kaggle/input").rglob("manifest.json")
               if "vcc-rete-contesti-r2" in path.parts and sha(path) == review["dataset_manifest_sha256"]]
    if len(matches) != 1:
        raise ValueError("Cannot uniquely locate frozen private r2 dataset")
    dataset = matches[0]
    verified_data = check_dataset_identity(dataset, gate["seed0_data_files"])
    manifest = json.loads((dataset / "manifest.json").read_text())
    import numpy as np
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("Reviewed free Kaggle CUDA resource is required")
    files = []
    for name, size in manifest["bytes"].items():
        path = dataset / name
        if path.stat().st_size != size:
            raise ValueError(f"Input size differs: {name}")
        entry = {"name": name, **verified_data[name]}
        if path.suffix == ".npy":
            array = np.load(path, mmap_mode="r", allow_pickle=False)
            if not isinstance(array, np.memmap) or array.flags.writeable:
                raise ValueError("Input arrays must remain read-only memory maps")
            entry.update({"shape": list(array.shape), "dtype": str(array.dtype)})
            if name in {"raw.npy", "se.npy", "shrunk.npy"} and list(array.shape) != [109586, 13248]:
                raise ValueError("r2 effect dimensions differ")
            del array
        files.append(entry)
    save(work / "input_files.json", {"dataset_manifest_sha256": review["dataset_manifest_sha256"], "files": files,
         "compared_with_seed0": verified_data, "all_recorded_hashes_and_sizes_match_seed0": True})
    packages = {}
    for name in ("torch", "numpy", "scipy", "pandas"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    save(work / "environment.json", {"python": sys.version, "versions": packages,
         "gpu": torch.cuda.get_device_name(0), "torch_cuda": torch.version.cuda, "visible_gpus": torch.cuda.device_count()})
    report = code / "reports/analisi/lead_scientist_2026-09-29"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(code / "src")
    status = {"mode": mode, "not_vcc_score": True, "cellular_advantage_inherited": False, "submission": False,
              "all_training_code_identical_to_seed0": True, "status": "started", "folds": []}
    try:
        if mode == "seed1":
            for family in FAMILIES:
                out = work / "folds" / f"C_{family}_s1"
                command = train_command(report, dataset, out, family, 1)
                record = {"family": family, "started_utc": utc(), "command": command}
                try:
                    rc = run(command, work / f"console_{family}.log", code, env)
                    record.update({"returncode": rc, "complete": rc == 0 and (out / "summary.json").is_file()
                                   and (out / "per_target.csv").is_file()})
                except Exception:
                    record.update({"returncode": None, "complete": False, "exception": traceback.format_exc()})
                record["finished_utc"] = utc()
                status["folds"].append(record)
                save(work / f"status_{family}.json", record)
            if not all(row["complete"] for row in status["folds"]):
                raise RuntimeError("Incomplete seed-1 fold set; no cross-family verdict")
            read_command = [sys.executable, str(report / "read_neural_verified.py"), "--runs",
                            *[str(work / "folds" / f"C_{family}_s1") for family in FAMILIES],
                            "--out", str(work / "cross_family")]
            rc = run(read_command, work / "readout.log", code, env)
            if rc:
                raise RuntimeError("Complete-family readout failed; preserve all fold outputs")
            verdict = json.loads((work / "cross_family/verdict.json").read_text())
            save(work / "two_seed_summary.json", {"seed0": gate["verdict"], "seed1": verdict,
                 "both_seeds_pass_effect_proxy": verdict["eligible_for_cell_scorer"],
                 "independent_cellular_benchmark_still_required": True, "submission": False})
        else:
            out = work / "production_C_s0"
            command = train_command(report, dataset, out, "none", 0)
            save(work / "production_command.json", command)
            if run(command, work / "production.log", code, env):
                raise RuntimeError("Production fit failed")
            checkpoint = out / "model_true.pt"
            export = [sys.executable, str(report / "t25_source_adapter.py"), "export", "--checkpoint", str(checkpoint),
                      "--data", str(dataset), "--targets", str(report / "production_targets.txt"),
                      "--contexts", "A,B,C", "--device", "cuda", "--out", str(work / "t25_factors")]
            save(work / "export_command.json", export)
            if run(export, work / "export.log", code, env):
                raise RuntimeError("Modifier export failed")
            status.update({"checkpoint_sha256": sha(checkpoint),
                           "factor_manifest_sha256": sha(work / "t25_factors/manifest.json"),
                           "adapter_validation_inherited": False, "apply_t25_performed": False})
        status["status"] = "complete"
    except Exception:
        status.update({"status": "failed", "exception": traceback.format_exc()})
        raise
    finally:
        status["finished_utc"] = utc()
        save(work / "completion.json", status)
