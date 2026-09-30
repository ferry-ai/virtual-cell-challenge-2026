"""Prepare an isolated vcc-cli overlay on the same Colab Python; never generate cells."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import venv

ARCHIVE_SHA = "f7324778e5d7225552734e2c7303353f46dee6c01e9d455703adce3b9b105860"
SCIENTIFIC = ("numpy", "scipy", "pandas", "h5py", "anndata", "PyYAML", "cell-eval2")


def canonical(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def inventory():
    versions = {}
    shadowed = {}
    for dist in metadata.distributions():
        name = canonical(dist.metadata["Name"])
        # A system-site-packages overlay can intentionally shadow the base CLI.
        # Match importlib's effective distribution rather than choosing the last entry.
        versions[name] = metadata.version(dist.metadata["Name"])
        if dist.version != versions[name]:
            shadowed.setdefault(name, []).append(dist.version)
    return {"python": sys.version, "python_major_minor": list(sys.version_info[:2]),
            "executable": sys.executable, "prefix": sys.prefix, "base_prefix": sys.base_prefix,
            "versions": versions, "shadowed_distribution_versions": shadowed}


def check_scientific(expected, actual):
    expected_versions = {canonical(k): v for k, v in expected["versions"].items()}
    actual_versions = {canonical(k): v for k, v in actual["versions"].items()}
    for package in SCIENTIFIC:
        name = canonical(package)
        if not expected_versions.get(name) or actual_versions.get(name) != expected_versions[name]:
            raise ValueError(f"Scientific version differs from completed benchmark: {package}")
    if actual["python_major_minor"] != [3, 13] or not expected["python"].startswith("3.13."):
        raise ValueError("This reviewed bootstrap requires the same Python 3.13 runtime")


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write("\n")


def run(command, logfile):
    with logfile.open("x", encoding="utf-8") as log:
        completed = subprocess.run(command, text=True, stdout=log, stderr=subprocess.STDOUT)
    if completed.returncode:
        raise RuntimeError(f"Preflight command failed ({completed.returncode}); see {logfile.name}")


def check_cli_requirements():
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version
    dist = metadata.distribution("vcc-cli")
    if dist.version != "0.2.0":
        raise ValueError("Wrong vcc-cli version")
    if Version(".".join(map(str, sys.version_info[:3]))) not in SpecifierSet(dist.metadata["Requires-Python"]):
        raise ValueError("CLI Requires-Python is incompatible")
    requirements = []
    for text in dist.requires or []:
        req = Requirement(text)
        if req.marker and not req.marker.evaluate({"extra": ""}):
            continue
        installed = metadata.version(req.name)
        if Version(installed) not in req.specifier:
            raise ValueError(f"Unsatisfied CLI dependency: {req.name}")
        requirements.append({"requirement": text, "installed": installed})
    return requirements


def verify(args):
    expected = json.loads(args.expected_environment.read_text())
    actual = inventory()
    check_scientific(expected, actual)
    if sys.prefix == sys.base_prefix:
        raise ValueError("Verification did not run inside the new venv")
    packages = {"numpy": "numpy", "scipy": "scipy", "pandas": "pandas", "h5py": "h5py",
                "anndata": "anndata", "PyYAML": "yaml", "cell-eval2": "cell_eval2"}
    origins = {}
    for package, module_name in packages.items():
        module = importlib.import_module(module_name)
        origins[package] = str(Path(module.__file__).resolve())
    import numpy as np
    import scipy.sparse as sp
    import anndata as ad
    from vcc import prep, sizing, vccfile
    from vcc._version import __version__
    if __version__ != "0.2.0" or tuple(prep.REQUIRED_CONTEXTS) != ("A", "B", "C"):
        raise ValueError("Unexpected official CLI contract")
    vcc_origin = Path(importlib.import_module("vcc").__file__).resolve()
    if not vcc_origin.is_relative_to(Path(sys.prefix).resolve()):
        raise ValueError("CLI is not installed inside the isolated venv")
    with tempfile.TemporaryDirectory(dir=args.out) as tmp:
        path = Path(tmp) / "abi_roundtrip.h5ad"
        matrix = sp.csr_matrix(np.array([[1, 0, 2], [0, 3, 1]], dtype=np.int32))
        ad.AnnData(matrix).write_h5ad(path)
        loaded = ad.read_h5ad(path)
        if not np.array_equal(loaded.X.toarray(), matrix.toarray()):
            raise ValueError("Scientific ABI / HDF5 roundtrip failed")
    actual.update({"module_origins": origins, "vcc_module": str(vcc_origin),
                   "vcc_cli_requirements": check_cli_requirements(), "h5ad_roundtrip": "passed"})
    save(args.out / "venv_verified.json", actual)
    print("PASS: same scientific versions, imports, tiny HDF5 roundtrip, vcc-cli 0.2.0 in isolated venv")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", choices=["plan", "create", "verify"], default="plan")
    p.add_argument("--expected-environment", type=Path, required=True)
    p.add_argument("--code-archive", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.phase == "verify":
        verify(args)
        return
    expected = json.loads(args.expected_environment.read_text())
    base = inventory()
    check_scientific(expected, base)
    if args.out.exists():
        raise FileExistsError("Use a fresh environment directory")
    if args.code_archive is None or hashlib.sha256(args.code_archive.read_bytes()).hexdigest() != ARCHIVE_SHA:
        raise ValueError("Requires the frozen r3 code archive")
    if args.phase == "plan":
        print(json.dumps({"base": {k: base[k] for k in ("python", "executable", "prefix")},
                          "scientific_versions_match_benchmark": True, "proposed_venv": str(args.out / "venv"),
                          "same_interpreter": True, "system_site_packages": True,
                          "install": "vcc-cli==0.2.0 inside venv; all inherited versions constrained",
                          "generation": False}, indent=2))
        return
    if os.name != "posix":
        raise ValueError("Reviewed creation phase targets Colab Linux, not the laptop")
    args.out.mkdir(parents=True)
    save(args.out / "base_before.json", base)
    venv_path = args.out / "venv"
    venv.EnvBuilder(system_site_packages=True, with_pip=True).create(venv_path)
    python = venv_path / "bin/python"
    constraints = args.out / "base_constraints.txt"
    with constraints.open("x", encoding="utf-8") as stream:
        for name, value in sorted(base["versions"].items()):
            if name not in {"vcc-cli", "pip", "setuptools", "wheel"}:
                stream.write(f"{name}=={value}\n")
    # --isolated ignores pip user configuration; -I ignores Python user-site/PYTHONPATH.
    # The first pass installs only the exact CLI inside this venv even if inherited globally.
    common = [str(python), "-I", "-m", "pip", "--isolated", "install", "--index-url", "https://pypi.org/simple",
              "--only-binary=:all:"]
    run(common + ["--no-deps", "--ignore-installed", "vcc-cli==0.2.0"], args.out / "install_cli.log")
    run(common + ["--constraint", str(constraints), "vcc-cli==0.2.0"], args.out / "install_dependencies.log")
    after = inventory()
    save(args.out / "base_after.json", after)
    if base != after:
        raise ValueError("Base interpreter metadata changed; do not generate")
    run([str(python), "-I", str(Path(__file__).resolve()), "--phase", "verify", "--out", str(args.out),
         "--expected-environment", str(args.expected_environment)], args.out / "verify.log")
    code = args.out / "code_r3"
    code.mkdir()
    with tarfile.open(args.code_archive, "r:gz") as tar:
        for member in tar.getmembers():
            target = (code / member.name).resolve()
            if not member.isfile() or not target.is_relative_to(code.resolve()):
                raise ValueError("Unsafe frozen archive member")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(tar.extractfile(member).read())
    for stage in ("45_generate_prediction.py", "48_package_prediction.py"):
        run([str(python), "-I", str(code / "scripts" / stage), "--help"], args.out / f"{stage}.help.log")
    save(args.out / "ready.json", {"verified_utc": datetime.now(timezone.utc).isoformat(),
         "python_for_both_stages": str(python), "code_archive_sha256": ARCHIVE_SHA,
         "base_environment_unchanged": True, "generation_started": False,
         "next": "Use this same venv python for the reviewed generate_candidate.py only after confirmation and registration"})
    print(f"READY: {python}; no cells generated, no package, no submission")


if __name__ == "__main__":
    main()
