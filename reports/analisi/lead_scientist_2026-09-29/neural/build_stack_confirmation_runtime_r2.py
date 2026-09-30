"""Build one confirmation runtime after complete AB selection; never launch it.

A uses its original frozen confirmation contract. B requires a separately
reviewed adapter/protocol/scorer and a newly bound bundle manifest. The original
075/080 preparation and A runtime artifacts are never rewritten.
"""
from __future__ import annotations
import argparse
import ast
import base64
import io
import json
from pathlib import Path
import tarfile

import build_stack_confirmation_runtime as original
from build_stack_resume_r2 import replace_once
from build_stack_variant_b_runtime import sha, read_checked
from build_stack_kaggle_fresh_r1 import save
import stack_ab_selection_guard as guard

HERE, REL = original.HERE, original.REL


def build(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    selection_bytes = args.selection.read_bytes()
    if sha(selection_bytes) != args.selection_sha256:
        raise ValueError("Reviewed AB selection receipt changed")
    selection = json.loads(selection_bytes)
    comparison_bytes = {v: getattr(args, "comparison_" + v.lower()).read_bytes() for v in ("A", "B")}
    comparisons = {v: json.loads(b) for v, b in comparison_bytes.items()}
    selector_sha = sha((HERE / "select_stack_ab.py").read_bytes())
    selected = guard.validate(selection, comparisons, {v: sha(b) for v, b in comparison_bytes.items()}, selector_sha)
    if selected is None:
        raise ValueError("Neither candidate is eligible; no confirmation runtime")
    if sha((HERE / "PROTOCOLLO_STACK_AB.md").read_bytes()) != guard.AB_SHA:
        raise ValueError("AB protocol changed")
    contract = {"adapter": (args.adapter, args.adapter_sha256), "protocol": (args.protocol, args.protocol_sha256),
                "scorer": (args.scorer, args.scorer_sha256)}
    if selected == "A":
        expected = {"adapter": original.FROZEN["stack_confirmation_infer.py"],
                    "protocol": original.FROZEN["PROTOCOLLO_STACK_CONFERMA.md"],
                    "scorer": original.FROZEN["stack_confirmation_score.py"]}
        if any(contract[k][1] != v for k, v in expected.items()):
            raise ValueError("Selected A must keep its original confirmation contract")
    elif args.adapter_sha256 == original.FROZEN["stack_confirmation_infer.py"] or args.protocol_sha256 == original.FROZEN["PROTOCOLLO_STACK_CONFERMA.md"]:
        raise ValueError("Selected B needs a separate reviewed confirmation adapter and protocol")
    bundle_bytes = args.bundle_manifest.read_bytes()
    if sha(bundle_bytes) != args.bundle_manifest_sha256:
        raise ValueError("Confirmation bundle receipt changed")
    bundle = json.loads(bundle_bytes)
    if (bundle["targets"] != original.EXPECTED or bundle["status"] != "prepared_no_model_no_scores"
            or bundle["protocol_sha256"] != args.protocol_sha256
            or bundle["inference_adapter_sha256"] != args.adapter_sha256
            or bundle["scoring_code_sha256"] != args.scorer_sha256):
        raise ValueError("Bundle is not bound to the selected confirmation contract")
    expected_files = {"destination_controls.h5ad", "transfer.npz", *[f"source_{i:02d}.h5ad" for i in range(13)]}
    if set(bundle["files"]) != expected_files:
        raise ValueError("Confirmation bundle member list differs")
    _, files = original.merged_archive()
    for path, digest in contract.values():
        content = read_checked(path, digest)
        name = REL + "/" + path.name
        if name in files and files[name] != content:
            raise ValueError("Cannot replace historical confirmation code")
        files[name] = content
    additions = [HERE / "PROTOCOLLO_STACK_AB.md", HERE / "stack_ab_selection_guard.py", HERE / "select_stack_ab.py"]
    if selected == "B":
        for name, digest in (("stack_input_axis_pilot.py", "a85b752dbd5042fde45611e80a6a942733bb19de6c4a00a03ab71db33a90d2a4"),
                             ("score_stack_input_axis.py", "74607f249fc36642e74a374e45c32157391b875888efe715163642674045b28c")):
            files[REL + "/" + name] = read_checked(HERE / name, digest)
    for path in additions:
        files[REL + "/" + path.name] = path.read_bytes()
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as tar:
        for name, content in sorted(files.items()):
            item = tarfile.TarInfo(name)
            item.size, item.mode, item.mtime = len(content), 0o644, 0
            tar.addfile(item, io.BytesIO(content))
    payload = output.getvalue()
    old = HERE / "stack_kaggle_fresh_r2/stack_kaggle_fresh_r2.py"
    if sha(old.read_bytes()) != "c12d18225af1d22ad44abe11c670fa64f61f8397a646b4b3cef551ce62c6441c":
        raise ValueError("Reviewed fresh runtime changed")
    source = old.read_text()
    last = ast.parse(source).body[-1]
    _, review = [ast.literal_eval(x) for x in last.value.args]
    runtime = "\n".join(source.splitlines()[:last.lineno - 1])
    runtime = replace_once(runtime, '"/kaggle/working/lead_stack_r1"', '"/kaggle/working/lead_stack_confirmation_selected_r1"')
    runtime = replace_once(runtime, '"/tmp/lead_stack_scratch_r1"', '"/tmp/lead_stack_confirmation_selected_scratch_r1"')
    runtime = replace_once(runtime, 'report / "stack_pilot.py", "infer", "--bundle", bundle,',
                           'report / ' + repr(args.adapter.name) + ', "--bundle", bundle,')
    runtime = replace_once(runtime, '        env = os.environ.copy()',
        '        sys.path.insert(0, str(report))\n'
        '        import stack_ab_selection_guard\n'
        '        stack_ab_selection_guard.validate_embedded(review)\n'
        '        if manifest["inference_adapter_sha256"] != review["inference_adapter_sha256"] or manifest["protocol_sha256"] != review["protocol_sha256"]:\n'
        '            raise ValueError("Selected confirmation contract changed")\n'
        '        save(work / "ab_selection_receipt.json", json.loads(review["ab_selection_json"]))\n'
        '        env = os.environ.copy()')
    runtime = replace_once(runtime, '"status": "generated_no_scores"', '"status": "profiles_exported_no_cells_no_scores"')
    runtime = replace_once(runtime,
        '"claim": "12 development targets, no clean pretraining holdout claim, no VCC submission"',
        '"claim": "Only AB-selected candidate,12 distinct reserve targets, exact profiles only; no score or submission"')
    for key in ("registered_plan_sha256", "plan_equivalence", "reference_failed_runs"):
        review.pop(key, None)
    review.update(dataset=args.dataset, kernel=args.kernel, targets=original.EXPECTED,
        bundle_archive_sha256=args.bundle_archive_sha256, bundle_archive_bytes=args.bundle_archive_bytes,
        bundle_manifest_sha256=sha(bundle_bytes), bundle_files=sorted(expected_files | {"bundle.json"}),
        plan_sha256=bundle["plan_sha256"], code_archive_sha256=sha(payload),
        code_files=[{"path": k, "bytes": len(v), "sha256": sha(v)} for k, v in sorted(files.items())],
        inference_adapter_sha256=args.adapter_sha256, protocol_sha256=args.protocol_sha256,
        scoring_code_sha256=args.scorer_sha256, selected_variant=selected,
        ab_protocol_sha256=guard.AB_SHA, ab_selector_sha256=selector_sha,
        ab_selection_sha256=sha(selection_bytes), ab_selection_json=selection_bytes.decode(),
        ab_comparison_json={v: b.decode() for v, b in comparison_bytes.items()},
        execution_status="Prepared only; full source bytes and AB receipt rechecked before dependencies/weights")
    guard.validate_embedded(review)
    cell = runtime + "\n\nmain(" + repr(base64.b64encode(payload).decode()) + ", " + repr(review) + ")\n"
    ast.parse(cell)
    args.out.mkdir(parents=True)
    (args.out / "stack_confirmation_selected_r1.py").write_bytes(cell.encode())
    notebook = json.loads((HERE / "stack_kaggle_fresh_r2/stack_pilot_r2.ipynb").read_text())
    notebook["cells"][0]["source"] = ["# Stack: conferma unica del candidato selezionato\n", "Gate AB verificato; dodici target riserva, soli profili float64.\n"]
    notebook["cells"][1]["source"] = cell.splitlines(keepends=True)
    save(args.out / "stack_confirmation_selected_r1.ipynb", notebook)
    metadata = json.loads((HERE / "stack_kaggle_fresh_r2/kernel-metadata.json").read_text())
    metadata.update(id=args.kernel, title="VCC Stack Selected Confirmation R1", code_file="stack_confirmation_selected_r1.ipynb", dataset_sources=[args.dataset])
    save(args.out / "kernel-metadata.json", metadata)
    save(args.out / "review_manifest.json", review)
    (args.out / "code_snapshot.tar.gz").write_bytes(payload)
    save(args.out / "artifact_hashes.json", {p.name: {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in sorted(args.out.iterdir())})
    return review


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("selection", "comparison-a", "comparison-b", "bundle-manifest", "adapter", "protocol", "scorer", "out"):
        p.add_argument("--" + name, required=True, type=Path)
    for name in ("selection-sha256", "bundle-manifest-sha256", "adapter-sha256", "protocol-sha256", "scorer-sha256", "dataset", "kernel"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--bundle-archive-sha256")
    p.add_argument("--bundle-archive-bytes", type=int)
    args = p.parse_args()
    result = build(args)
    print(json.dumps({"out": str(args.out), "selected_variant": result["selected_variant"], "bundle_sha256": result["bundle_manifest_sha256"]}))


if __name__ == "__main__":
    main()
