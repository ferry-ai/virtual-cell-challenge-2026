"""Fresh private Kaggle pilot with both verified runtime-only repairs."""
import ast
import hashlib
import json
from pathlib import Path

from build_stack_resume_r2 import replace_once
from build_stack_resume_r3 import ROUNDTRIP

HERE = Path(__file__).resolve().parent


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    old = HERE / "stack_remote_receipt_r2/colab_stack_infer_r1.py"
    if hashlib.sha256(old.read_bytes()).hexdigest() != "a9acc828d79aae8c6edd638ab2cb6de6a91d35f1f0e597a371423f9008e5e26a":
        raise ValueError("Original complete runtime differs")
    original = old.read_text(encoding="utf-8")
    tree = ast.parse(original)
    last = tree.body[-1]
    payload, review = [ast.literal_eval(x) for x in last.value.args]
    runtime = "\n".join(original.splitlines()[:last.lineno - 1])
    runtime = replace_once(runtime,
        '        run([python, "-m", "pip", "check"], work / "pip_check.txt", cwd=code, env=env)',
        '        run([python, "-m", "pip", "install", "--no-cache-dir", "--no-deps", "--only-binary=:all:", "pooch==1.8.2"],\n'
        '            work / "pooch_install.log", cwd=code, env=env)\n'
        '        run([python, "-m", "pip", "check"], work / "pip_check.txt", cwd=code, env=env)')
    runtime = replace_once(runtime,
        'from pathlib import Path\nimport stack.model_loading as loading',
        'from pathlib import Path\nimport anndata as ad\nad.settings.allow_write_nullable_strings = True\nimport stack.model_loading as loading')
    runtime = replace_once(runtime,
        '        save(work / "resources_before_weights.json", available)\n',
        '        save(work / "resources_before_weights.json", available)\n'
        '        if available["MemAvailable_bytes"] < 6 * 1024**3:\n'
        '            raise RuntimeError("Weight download deferred: less than 6 GiB RAM available")\n')
    runtime = replace_once(runtime, '        model_dir = scratch / "official_model"',
        '        roundtrip_script = work / "serialization_roundtrip.py"\n'
        '        roundtrip_script.write_text(' + repr(ROUNDTRIP) + ', encoding="utf-8")\n'
        '        run([python, roundtrip_script, work / "serialization_roundtrip"],\n'
        '            work / "serialization_roundtrip.log", cwd=code, env=env)\n'
        '        model_dir = scratch / "official_model"')
    review["dataset"] = "davidmaisterx/vcc-stack-prompts-r1"
    review["kernel"] = "davidmaisterx/vcc-stack-pilot-r1"
    review["runtime_fixes"] = ["pooch==1.8.2 installed without dependency changes", "anndata.settings.allow_write_nullable_strings=True"]
    review["runtime_mode"] = "fresh isolated managed Python, no Colab paths or cache required"
    review["preflight_roundtrips"] = "two sparse H5AD files with nullable gene index and obs labels before weights"
    review["reference_failed_runs"] = ["Colab071 missing pooch before model load", "Colab072 completed 12 targets but failed nullable-string H5AD save"]
    cell = runtime + "\n\nmain(" + repr(payload) + ", " + repr(review) + ")\n"
    ast.parse(cell)
    out = HERE / "stack_kaggle_fresh_r1"
    out.mkdir()
    (out / "stack_kaggle_fresh_r1.py").write_bytes(cell.encode())
    notebook = {"nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "cells": [{"cell_type": "markdown", "id": "scope", "metadata": {}, "source": [
            "# Stack: stesso pilot congelato, runtime nuovo\n",
            "12 target development, prompt K562 e soli controlli HepG2. Nessun dato A/B/C, fine-tuning o scoring.\n"]},
            {"cell_type": "code", "id": "fresh-runtime", "metadata": {}, "execution_count": None,
             "outputs": [], "source": cell.splitlines(keepends=True)}]}
    save(out / "stack_pilot_r1.ipynb", notebook)
    save(out / "review_manifest.json", review)
    save(out / "kernel-metadata.json", {"id": review["kernel"], "title": "VCC Stack Pilot R1",
        "code_file": "stack_pilot_r1.ipynb", "language": "python", "kernel_type": "notebook",
        "is_private": True, "enable_gpu": True, "enable_tpu": False, "enable_internet": True,
        "machine_shape": "NvidiaTeslaT4", "dataset_sources": [review["dataset"]],
        "competition_sources": [], "kernel_sources": [], "model_sources": []})
    hashes = {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.iterdir())}
    save(out / "artifact_hashes.json", hashes)
    print(json.dumps(hashes, indent=2))


if __name__ == "__main__":
    main()
