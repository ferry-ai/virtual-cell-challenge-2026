"""Build a reviewed resume: add missing pooch only; preserve CUDA and pilot."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Expected runtime fragment is not unique")
    return text.replace(old, new, 1)


def main():
    old = HERE / "stack_remote_receipt_r2" / "colab_stack_infer_r1.py"
    if hashlib.sha256(old.read_bytes()).hexdigest() != "a9acc828d79aae8c6edd638ab2cb6de6a91d35f1f0e597a371423f9008e5e26a":
        raise ValueError("Original reviewed launcher changed")
    source = old.read_text(encoding="utf-8")
    source = replace_once(source,
        'if work.exists() or scratch.exists():\n        raise FileExistsError("Runtime paths must be new; preserve any previous attempt")',
        'if work.exists() or not scratch.is_dir():\n        raise FileExistsError("Resume requires new output and the existing r1 scratch")')
    source = replace_once(source,
        '''        scratch.mkdir(parents=True)
        save(work / "resources_before_install.json", resources(scratch))
        if shutil.disk_usage(scratch).free < 16 * 1024**3:
            raise RuntimeError("Need 16 GiB free for isolated CUDA dependencies and pinned checkpoint")''',
        '''        save(work / "resources_before_repair.json", resources(scratch))''')
    source = replace_once(source,
        '''        extract_exact(payload, code, {r["path"]: r["sha256"] for r in review["code_files"]})
        extract_exact(Path(bundle_archive).read_bytes(), bundle,
                      {name: None for name in review["bundle_files"]})''',
        '''        for record in review["code_files"]:
            if sha(code / record["path"]) != record["sha256"]:
                raise ValueError("Reused frozen code differs: " + record["path"])
        if sorted(p.name for p in bundle.iterdir()) != sorted(review["bundle_files"]):
            raise ValueError("Reused bundle file allowlist differs")''')
    source = replace_once(source,
        '''        python = create_managed_runtime(scratch, work, code, env)
        run([python, "-m", "pip", "install", "--no-cache-dir", "-r", report / "requirements_stack.txt"],
            work / "installation.log", cwd=code, env=env)''',
        '''        previous = work.parent / "lead_stack_infer_2026-09-29_r1"
        python = scratch / "venv/bin/python"
        managed = json.loads((previous / "managed_python.json").read_text(encoding="utf-8"))
        if not python.resolve().is_relative_to((scratch / "python").resolve()):
            raise ValueError("Reused Python escaped the isolated managed installation")
        if sha(python.resolve()) != managed["managed_base_sha256"]:
            raise ValueError("Reused managed Python binary differs")
        run([python, "-c", "import sys; assert sys.version_info[:3] == (3,11,13); print(sys.version)"],
            work / "reused_python.log", cwd=code, env=env)
        run([python, "-m", "pip", "freeze"], work / "pip_freeze_before.txt", cwd=code, env=env)
        before = set((work / "pip_freeze_before.txt").read_text().splitlines())
        expected = set((previous / "pip_freeze.txt").read_text().splitlines())
        if before != expected:
            raise ValueError("Reused environment differs from failed r1 freeze; no automatic repair")
        # The real traceback is a missing eager import. No dependencies or CUDA change.
        run([python, "-m", "pip", "install", "--no-cache-dir", "--no-deps", "--only-binary=:all:", "pooch==1.8.2"],
            work / "runtime_repair.log", cwd=code, env=env)
        save(work / "managed_python.json", managed | {"reused_from": str(previous), "new_dependency": "pooch==1.8.2"})''')
    source = replace_once(source,
        '''        run([python, "-m", "pip", "freeze"], work / "pip_freeze.txt", cwd=code, env=env)
        run([python, report / "test_stack_pilot.py"]''',
        '''        run([python, "-m", "pip", "freeze"], work / "pip_freeze.txt", cwd=code, env=env)
        after = set((work / "pip_freeze.txt").read_text().splitlines())
        if after - before != {"pooch==1.8.2"} or before - after:
            raise ValueError("Runtime repair changed packages beyond the approved pooch addition")
        save(work / "runtime_repair_diff.json", {"added": sorted(after - before), "removed": sorted(before - after)})
        run([python, report / "test_stack_pilot.py"]''')
    source = replace_once(source,
        '''        save(work / "resources_before_weights.json", available)
        if available["disk_free_bytes"]''',
        '''        save(work / "resources_before_weights.json", available)
        if available["MemAvailable_bytes"] < 6 * 1024**3:
            raise RuntimeError("Weight download deferred: less than 6 GiB RAM available")
        if available["disk_free_bytes"]''')
    source = replace_once(source,
        "work='/content/drive/MyDrive/vcc2026/runs/lead_stack_infer_2026-09-29_r1'",
        "work='/content/drive/MyDrive/vcc2026/runs/lead_stack_infer_2026-09-29_r2'")
    ast.parse(source)
    out = HERE / "stack_resume_r2"
    out.mkdir()
    content = source.encode("utf-8")
    (out / "colab_stack_infer_r2.py").write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    shell = f'''#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_infer_setup_2026-09-29_r2"
test ! -e "$DRIVE/runs/lead_stack_infer_2026-09-29_r2"
test -x /content/lead_stack_scratch_r1/venv/bin/python
echo "{digest}  $SETUP/colab_stack_infer_r2.py" | sha256sum -c -
python -u "$SETUP/colab_stack_infer_r2.py"
'''
    (out / "072_lead_stack_infer_r2.sh").write_bytes(shell.encode())
    manifest = {"status": "resume_prepared_not_executed", "previous_launcher_sha256": hashlib.sha256(old.read_bytes()).hexdigest(),
        "only_environment_addition": "pooch==1.8.2", "cuda_reinstalled": False,
        "bundle_plan_adapter_checkpoint_genelist_unchanged": True,
        "previous_work_preserved": "runs/lead_stack_infer_2026-09-29_r1",
        "new_work": "runs/lead_stack_infer_2026-09-29_r2", "reused_scratch": "/content/lead_stack_scratch_r1",
        "runtime_guard": "6 GiB available RAM before weights and immediately before loader; 2 GiB disk reserve",
        "files": {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.iterdir())}}
    (out / "review_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
