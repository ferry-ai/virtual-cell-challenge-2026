"""Freeze a fresh confirmation GPU runtime only after the pilot's positive gate.

Reads small reviewed manifests and frozen code, never expression matrices or
weights. This builder performs no upload, model download or remote execution.
"""
from __future__ import annotations
import argparse
import ast
import base64
import hashlib
import io
import json
import math
from pathlib import Path
import tarfile

from build_stack_resume_r2 import replace_once
from build_stack_kaggle_fresh_r1 import save
from stack_confirmation_pack import EXPECTED

HERE = Path(__file__).resolve().parent
REL = "reports/analisi/lead_scientist_2026-09-29/neural"
FROZEN = {"stack_confirmation_infer.py": "a6147fd5dc0aea614de9101a14c13fd4c627fcecab27c93971b81e89429c6b30",
          "stack_confirmation_score.py": "c69d41aac1aa4bc14bcb9239b39cea675430c944ea1e7c1078f659b483a6df71",
          "PROTOCOLLO_STACK_CONFERMA.md": "2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2"}


def sha(content):
    return hashlib.sha256(content).hexdigest()


def gate_passed(value):
    delta, pds = value.get("delta_projection", float("nan")), value.get("delta_pds_raw", float("nan"))
    return (value.get("proceed_to_distinct_confirmation") is True
            and math.isfinite(delta) and math.isfinite(pds) and delta > 0 and pds >= 0)


def merged_archive():
    files = {}
    for path, expected in [(HERE / "stack_setup_r1/code_snapshot.tar.gz", "a2e407961e2aefacd634f17541440bfd1e7035a036658f63cb655a33a9926698"),
                           (HERE / "stack_expansion_setup_r2/code_snapshot.tar.gz", "344e204b77c2712a8e510cc30acdda87f2d299e6a24fd14b65e602c79630ee72")]:
        content = path.read_bytes()
        if sha(content) != expected:
            raise ValueError("Frozen runtime source archive changed")
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tar:
            for m in tar.getmembers():
                if not m.isfile():
                    raise ValueError("Unexpected frozen archive member")
                data = tar.extractfile(m).read()
                if m.name in files and files[m.name] != data:
                    raise ValueError("Scientific dependency conflict: " + m.name)
                files[m.name] = data
    for name, expected in FROZEN.items():
        if sha(files[REL + "/" + name]) != expected:
            raise ValueError("Frozen confirmation scientific code changed")
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as tar:
        for name, content in sorted(files.items()):
            item = tarfile.TarInfo(name)
            item.size, item.mode, item.mtime = len(content), 0o644, 0
            tar.addfile(item, io.BytesIO(content))
    return output.getvalue(), files


def build(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    bundle_bytes = args.bundle_manifest.read_bytes()
    if sha(bundle_bytes) != args.bundle_manifest_sha256:
        raise ValueError("Confirmation bundle receipt changed")
    bundle = json.loads(bundle_bytes)
    if (bundle["targets"] != EXPECTED or bundle["status"] != "prepared_no_model_no_scores"
            or bundle["protocol_sha256"] != FROZEN["PROTOCOLLO_STACK_CONFERMA.md"]
            or bundle["inference_adapter_sha256"] != FROZEN["stack_confirmation_infer.py"]
            or bundle["scoring_code_sha256"] != FROZEN["stack_confirmation_score.py"]):
        raise ValueError("Confirmation bundle does not match the frozen protocol/code/target registration")
    expected_files = {"destination_controls.h5ad", "transfer.npz", *[f"source_{i:02d}.h5ad" for i in range(13)]}
    if set(bundle["files"]) != expected_files:
        raise ValueError("Confirmation bundle member list differs")
    comparison_bytes = args.pilot_comparison.read_bytes()
    if sha(comparison_bytes) != args.pilot_comparison_sha256:
        raise ValueError("Pilot comparison receipt changed")
    comparison = json.loads(comparison_bytes)
    if not gate_passed(comparison):
        raise ValueError("Pilot gate did not pass; confirmation runtime remains blocked")
    old = HERE / "stack_kaggle_fresh_r2/stack_kaggle_fresh_r2.py"
    if sha(old.read_bytes()) != "c12d18225af1d22ad44abe11c670fa64f61f8397a646b4b3cef551ce62c6441c":
        raise ValueError("Reviewed fresh runtime changed")
    original = old.read_text()
    last = ast.parse(original).body[-1]
    _, review = [ast.literal_eval(a) for a in last.value.args]
    runtime = "\n".join(original.splitlines()[:last.lineno - 1])
    runtime = replace_once(runtime, '"/kaggle/working/lead_stack_r1"', '"/kaggle/working/lead_stack_confirmation_r1"')
    runtime = replace_once(runtime, '"/tmp/lead_stack_scratch_r1"', '"/tmp/lead_stack_confirmation_scratch_r1"')
    runtime = replace_once(runtime, 'report / "stack_pilot.py", "infer", "--bundle", bundle,',
                           'report / "stack_confirmation_infer.py", "--bundle", bundle,')
    runtime = replace_once(runtime, '"status": "generated_no_scores"', '"status": "profiles_exported_no_cells_no_scores"')
    runtime = replace_once(runtime,
        '"claim": "12 development targets, no clean pretraining holdout claim, no VCC submission"',
        '"claim": "12 distinct reserve targets; exact float64 profiles only; no clean pretraining holdout claim; no VCC submission"')
    runtime = replace_once(runtime, '        if bundle_archive is None:',
        '        gate = review["pilot_gate"]\n'
        '        if not (gate["proceed_to_distinct_confirmation"] is True and gate["delta_projection"] > 0 and gate["delta_pds_raw"] >= 0):\n'
        '            raise ValueError("Frozen pilot did not authorize prospective confirmation")\n'
        '        if bundle_archive is None:')
    runtime = replace_once(runtime, '        if manifest["plan_sha256"] != review["plan_sha256"]:',
        '        if manifest["inference_adapter_sha256"] != review["inference_adapter_sha256"] or manifest["protocol_sha256"] != review["protocol_sha256"]:\n'
        '            raise ValueError("Frozen confirmation identity differs")\n'
        '        if manifest["plan_sha256"] != review["plan_sha256"]:')
    payload, files = merged_archive()
    for key in ("registered_plan_sha256", "plan_equivalence", "reference_failed_runs"):
        review.pop(key, None)
    review.update(dataset=args.dataset, kernel=args.kernel, targets=EXPECTED,
        bundle_archive_sha256=args.bundle_archive_sha256,
        bundle_archive_bytes=args.bundle_archive_bytes,
        bundle_manifest_sha256=sha(bundle_bytes), bundle_files=sorted(expected_files | {"bundle.json"}),
        plan_sha256=bundle["plan_sha256"], code_archive_sha256=sha(payload),
        code_files=[{"path": k, "bytes": len(v), "sha256": sha(v)} for k, v in sorted(files.items())],
        inference_adapter_sha256=FROZEN["stack_confirmation_infer.py"],
        protocol_sha256=FROZEN["PROTOCOLLO_STACK_CONFERMA.md"],
        scoring_code_sha256=FROZEN["stack_confirmation_score.py"],
        pilot_gate={k: comparison[k] for k in ("proceed_to_distinct_confirmation", "delta_projection", "delta_pds_raw")},
        pilot_comparison_sha256=sha(comparison_bytes),
        claim="Receipt-bound confirmation runtime; local validation from receipt, all data bytes verified before weights; no remote execution by builder")
    cell = runtime + "\n\nmain(" + repr(base64.b64encode(payload).decode()) + ", " + repr(review) + ")\n"
    ast.parse(cell)
    args.out.mkdir(parents=True)
    (args.out / "stack_confirmation_r1.py").write_bytes(cell.encode())
    notebook = json.loads((HERE / "stack_kaggle_fresh_r2/stack_pilot_r2.ipynb").read_text())
    notebook["cells"][0]["source"] = ["# Stack: conferma prospettica\n", "Dodici target riserva distinti; profili esatti, nessuno scoring o dato A/B/C.\n"]
    notebook["cells"][1]["source"] = cell.splitlines(keepends=True)
    save(args.out / "stack_confirmation_r1.ipynb", notebook)
    metadata = json.loads((HERE / "stack_kaggle_fresh_r2/kernel-metadata.json").read_text())
    metadata.update(id=args.kernel, title="VCC Stack Confirmation R1", code_file="stack_confirmation_r1.ipynb", dataset_sources=[args.dataset])
    save(args.out / "kernel-metadata.json", metadata)
    save(args.out / "review_manifest.json", review)
    (args.out / "code_snapshot.tar.gz").write_bytes(payload)
    save(args.out / "artifact_hashes.json", {p.name: {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in sorted(args.out.iterdir())})
    return review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle-manifest", "pilot-comparison", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("bundle-manifest-sha256", "pilot-comparison-sha256", "dataset", "kernel"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--bundle-archive-sha256")
    parser.add_argument("--bundle-archive-bytes", type=int)
    args = parser.parse_args()
    result = build(args)
    print(json.dumps({"out": str(args.out), "bundle_sha256": result["bundle_manifest_sha256"], "code_sha256": result["code_archive_sha256"]}))


if __name__ == "__main__":
    main()
