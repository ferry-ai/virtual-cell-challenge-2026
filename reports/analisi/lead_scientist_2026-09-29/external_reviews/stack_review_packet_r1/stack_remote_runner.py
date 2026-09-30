"""Portable reviewed runtime: isolated Stack install, pinned weights, inference only.

The builder embeds this file with a frozen code archive and a bundle hash. This
file does not upload data or start a remote job. Scoring remains a separate job.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import traceback
import urllib.request


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write("\n")


def resources(path):
    info = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        fields = line.split()
        if fields[0] in {"MemAvailable:", "MemTotal:"}:
            info[fields[0][:-1] + "_bytes"] = int(fields[1]) * 1024
    disk = shutil.disk_usage(path)
    return info | {"disk_free_bytes": disk.free, "disk_total_bytes": disk.total,
                   "path": str(path), "utc": datetime.now(timezone.utc).isoformat()}


def extract_exact(payload, destination, expected):
    """No links, directories, duplicate names, escaping paths or extra files."""
    destination = Path(destination).resolve()
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        members = archive.getmembers()
        files = [m for m in members if not m.isdir()]
        names = [m.name.removeprefix("./") for m in files]
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("Archive file list differs from the reviewed allowlist")
        for member, name in zip(files, names):
            target = (destination / name).resolve()
            if not member.isfile() or not target.is_relative_to(destination):
                raise ValueError("Non-regular or escaping archive member")
            content = archive.extractfile(member).read()
            if expected[name] is not None and hashlib.sha256(content).hexdigest() != expected[name]:
                raise ValueError(f"Archived file hash differs: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(content)


def run(command, log_path, *, cwd, env):
    with Path(log_path).open("x", encoding="utf-8") as log:
        with subprocess.Popen([str(x) for x in command], cwd=cwd, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, bufsize=1) as child:
            for line in child.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
            rc = child.wait()
    if rc:
        raise RuntimeError(f"Command failed with status {rc}; see {Path(log_path).name}")


def download_pinned(url, path, expected_bytes, expected_sha):
    path = Path(path)
    with urllib.request.urlopen(url, timeout=120) as response, path.open("xb") as out:
        h, total = hashlib.sha256(), 0
        for block in iter(lambda: response.read(4 * 1024**2), b""):
            total += len(block)
            if total > expected_bytes:
                raise ValueError("Model download exceeded pinned byte count")
            h.update(block)
            out.write(block)
    if total != expected_bytes or h.hexdigest() != expected_sha:
        raise ValueError("Official model download failed size/hash verification")


def create_managed_runtime(scratch, work, code, env):
    """Dedicated CPython3.11.13; never replaces the host/Colab interpreter."""
    # Colab's host ensurepip is unavailable. --target writes only this folder.
    boot = scratch / "bootstrap_site"
    run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "--no-deps", "--ignore-installed",
         "--target", boot, "uv==0.8.22"],
        work / "uv_install.log", cwd=code, env=env)
    env.update({"UV_PYTHON_INSTALL_DIR": str(scratch / "python"),
                "UV_PYTHON_BIN_DIR": str(scratch / "python_bin"),
                "UV_CACHE_DIR": str(scratch / "uv_cache"), "UV_NO_MODIFY_PATH": "1"})
    uv = boot / "bin/uv"
    if not uv.is_file():
        raise FileNotFoundError("Pinned uv wheel did not provide its isolated executable")
    run([uv, "python", "install", "3.11.13"], work / "python_install.log", cwd=code, env=env)
    managed = subprocess.check_output([str(uv), "python", "find", "--managed-python", "3.11.13"],
                                      cwd=code, env=env, text=True).strip()
    managed_path = Path(managed).resolve()
    if not managed_path.is_relative_to((scratch / "python").resolve()):
        raise ValueError("Managed interpreter escaped the dedicated scratch directory")
    runtime = scratch / "venv"
    run([uv, "venv", "--python", managed_path, "--seed", runtime], work / "venv.log", cwd=code, env=env)
    python = runtime / "bin/python"
    version = subprocess.check_output([str(python), "-c", "import sys; print(sys.version); "
                                      "assert sys.version_info[:3] == (3,11,13)"], text=True).strip()
    save(work / "managed_python.json", {"version": version, "python_executable": str(python),
        "managed_base": str(managed_path), "managed_base_sha256": sha(managed_path),
        "uv_version": "0.8.22", "host_python_unchanged": sys.executable,
        "provenance": "Astral uv pinned download catalog and python-build-standalone checksums"})
    return python


def main(payload64, review, *, bundle_archive=None, work=None, scratch=None):
    """Kaggle defaults; Colab can supply the three explicit paths."""
    os.environ.update({"CUDA_VISIBLE_DEVICES": "0", "OMP_NUM_THREADS": "2",
                       "OPENBLAS_NUM_THREADS": "2", "MKL_NUM_THREADS": "2",
                       "PYTHONHASHSEED": "20260929", "PYTHONUNBUFFERED": "1",
                       "WANDB_MODE": "disabled", "HF_HUB_DISABLE_TELEMETRY": "1"})
    work = Path(work or "/kaggle/working/lead_stack_r1")
    scratch = Path(scratch or "/tmp/lead_stack_scratch_r1")
    if work.exists() or scratch.exists():
        raise FileExistsError("Runtime paths must be new; preserve any previous attempt")
    work.mkdir(parents=True)
    save(work / "runtime_review.json", review)
    save(work / "started.json", {"utc": datetime.now(timezone.utc).isoformat(),
                                "python": sys.version, "platform": platform.platform()})
    try:
        if bundle_archive is None:
            matches = list(Path("/kaggle/input").rglob("bundle.tar.gz"))
            matches = [p for p in matches if review["dataset"].split("/")[-1] in p.parts]
            if len(matches) != 1:
                raise ValueError("Cannot uniquely locate reviewed private prompt bundle")
            bundle_archive = matches[0]
        if sha(bundle_archive) != review["bundle_archive_sha256"]:
            raise ValueError("Input bundle differs from the reviewed preparation")
        scratch.mkdir(parents=True)
        save(work / "resources_before_install.json", resources(scratch))
        if shutil.disk_usage(scratch).free < 16 * 1024**3:
            raise RuntimeError("Need 16 GiB free for isolated CUDA dependencies and pinned checkpoint")
        payload = base64.b64decode(payload64, validate=True)
        if hashlib.sha256(payload).hexdigest() != review["code_archive_sha256"]:
            raise ValueError("Frozen code archive changed")
        code, bundle = scratch / "code", scratch / "bundle"
        extract_exact(payload, code, {r["path"]: r["sha256"] for r in review["code_files"]})
        extract_exact(Path(bundle_archive).read_bytes(), bundle,
                      {name: None for name in review["bundle_files"]})
        if sha(bundle / "bundle.json") != review["bundle_manifest_sha256"]:
            raise ValueError("Prepared bundle manifest changed")
        manifest = json.loads((bundle / "bundle.json").read_text())
        for name, digest in manifest["files"].items():
            if name not in review["bundle_files"] or sha(bundle / name) != digest:
                raise ValueError(f"Input checksum failed: {name}")
        if manifest["plan_sha256"] != review["plan_sha256"]:
            raise ValueError("Target plan differs from preregistered pilot")
        report = code / "reports/analisi/lead_scientist_2026-09-29/neural"
        if sha(report / "stack_pilot.py") != manifest["adapter_sha256"]:
            raise ValueError("Inference adapter differs from prepared adapter")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(code / "src")
        python = create_managed_runtime(scratch, work, code, env)
        run([python, "-m", "pip", "install", "--no-cache-dir", "-r", report / "requirements_stack.txt"],
            work / "installation.log", cwd=code, env=env)
        run([python, "-m", "pip", "check"], work / "pip_check.txt", cwd=code, env=env)
        run([python, "-m", "pip", "freeze"], work / "pip_freeze.txt", cwd=code, env=env)
        run([python, report / "test_stack_pilot.py"], work / "contract_tests.log", cwd=code, env=env)
        run([python, "-c", "from stack.model_loading import load_model_from_checkpoint; "
             "from scvi.distributions import NegativeBinomial; print('Stack/scvi imports OK')"],
            work / "model_imports.log", cwd=code, env=env)
        gpu_probe = ("import json,torch; assert torch.cuda.is_available(), 'CUDA required'; "
                     "print(json.dumps({'torch':torch.__version__,'cuda':torch.version.cuda,"
                     "'gpu':torch.cuda.get_device_name(0),'vram_bytes':torch.cuda.get_device_properties(0).total_memory}))")
        run([python, "-c", gpu_probe], work / "gpu.json", cwd=code, env=env)
        model_dir = scratch / "official_model"
        model_dir.mkdir()
        available = resources(scratch)
        save(work / "resources_before_weights.json", available)
        if available["disk_free_bytes"] < sum(x["bytes"] for x in review["model_files"]) + 2 * 1024**3:
            raise RuntimeError("Not enough disk for pinned weights plus 2 GiB working reserve")
        for model_file in review["model_files"]:
            url = (f"https://huggingface.co/{review['model_repository']}/resolve/"
                   f"{review['model_revision']}/{model_file['path']}")
            print(f"Downloading pinned public model file: {model_file['path']}", flush=True)
            download_pinned(url, model_dir / model_file["path"], model_file["bytes"], model_file["sha256"])
        save(work / "verified_model_files.json", review["model_files"])
        prediction = work / "prediction"
        # Wrap only the loader entry point, after torch/Stack imports and directly
        # before torch.load. Adapter bytes, model operations and RNG are unchanged.
        guarded_entry = r'''import json, runpy, shutil, sys
from datetime import datetime, timezone
from pathlib import Path
import stack.model_loading as loading
original = loading.load_model_from_checkpoint
resource_path, disk_path, adapter = map(Path, sys.argv[1:4])
def guarded_load(*args, **kwargs):
    info = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        words = line.split()
        if words[0] in ('MemAvailable:', 'MemTotal:'):
            info[words[0][:-1] + '_bytes'] = int(words[1]) * 1024
    info.update(disk_free_bytes=shutil.disk_usage(disk_path).free,
                utc=datetime.now(timezone.utc).isoformat(),
                minimum_available_bytes=6 * 1024**3, guard='immediately before checkpoint loader')
    with resource_path.open('x', encoding='utf-8') as f:
        json.dump(info, f, indent=2)
    if info['MemAvailable_bytes'] < 6 * 1024**3:
        raise RuntimeError('Checkpoint load deferred: less than 6 GiB RAM available')
    if info['disk_free_bytes'] < 2 * 1024**3:
        raise RuntimeError('Checkpoint load deferred: less than 2 GiB disk reserve')
    return original(*args, **kwargs)
loading.load_model_from_checkpoint = guarded_load
sys.argv = [str(adapter), *sys.argv[4:]]
runpy.run_path(str(adapter), run_name='__main__')
'''
        run([python, "-u", "-c", guarded_entry, work / "resources_before_checkpoint_load.json", scratch,
             report / "stack_pilot.py", "infer", "--bundle", bundle,
             "--checkpoint", model_dir / "bc_large_aligned.ckpt",
             "--genelist", model_dir / "basecount_1000per_15000max.pkl",
             "--out", prediction, "--device", "cuda", "--batch-size", "1"],
            work / "stdout.log", cwd=code, env=env)
        if not (prediction / "finished.json").exists():
            raise RuntimeError("Inference returned without a completion manifest")
        save(work / "prediction_hashes.json", {p.name: {"bytes": p.stat().st_size, "sha256": sha(p)}
             for p in sorted(prediction.iterdir()) if p.is_file()})
        with tarfile.open(work / "prediction.tar.gz", "w:gz") as archive:
            for path in sorted(prediction.iterdir()):
                archive.add(path, arcname=path.name, recursive=False)
        save(work / "completion.json", {"status": "generated_no_scores",
            "utc": datetime.now(timezone.utc).isoformat(),
            "prediction_archive_sha256": sha(work / "prediction.tar.gz"),
            "claim": "12 development targets, no clean pretraining holdout claim, no VCC submission"})
    except Exception:
        save(work / "failure.json", {"utc": datetime.now(timezone.utc).isoformat(),
                                    "traceback": traceback.format_exc(), "status": "incomplete"})
        raise
