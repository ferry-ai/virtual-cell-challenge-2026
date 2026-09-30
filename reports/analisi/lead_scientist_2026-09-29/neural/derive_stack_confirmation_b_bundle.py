"""Rebind identical prepared inputs only after selected B and its final protocol.

No data-model selection or inference is performed. Output is a new bundle;
every old data member is copied byte-identically and only bundle.json changes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil

import stack_pilot as pilot
from stack_confirmation_pack import EXPECTED
import stack_ab_selection_guard as guard

HERE = Path(__file__).resolve().parent
A_INFER = "a6147fd5dc0aea614de9101a14c13fd4c627fcecab27c93971b81e89429c6b30"
A_SCORE = "c69d41aac1aa4bc14bcb9239b39cea675430c944ea1e7c1078f659b483a6df71"
A_PROTOCOL = "2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2"


def rebind(old, selection_bytes, comparison_bytes, *, source_sha, selector_sha, adapter_sha, scorer_sha, protocol_sha):
    selection = json.loads(selection_bytes)
    comparisons = {v: json.loads(content) for v, content in comparison_bytes.items()}
    import hashlib
    digest = lambda value: hashlib.sha256(value).hexdigest()
    chosen = guard.validate(selection, comparisons, {v: digest(b) for v, b in comparison_bytes.items()}, selector_sha)
    if chosen != "B":
        raise ValueError("B was not the unique prospective selection; no B bundle")
    if (old["targets"] != EXPECTED or old["inference_adapter_sha256"] != A_INFER
            or old["scoring_code_sha256"] != A_SCORE or old["protocol_sha256"] != A_PROTOCOL
            or old["status"] != "prepared_no_model_no_scores"):
        raise ValueError("Expected unchanged original A preparation contract")
    if protocol_sha == A_PROTOCOL or adapter_sha == A_INFER or scorer_sha == A_SCORE:
        raise ValueError("B requires separate reviewed adapter, scorer and final protocol")
    result = old | {"source_bundle_manifest_sha256": source_sha, "source_protocol_sha256": A_PROTOCOL,
        "inference_adapter_sha256": adapter_sha, "scoring_code_sha256": scorer_sha, "protocol_sha256": protocol_sha,
        "selected_variant": "B", "ab_selector_sha256": selector_sha, "ab_protocol_sha256": guard.AB_SHA,
        "ab_selection_sha256": digest(selection_bytes), "ab_selection_json": selection_bytes.decode(),
        "ab_comparison_json": {v: b.decode() for v, b in comparison_bytes.items()},
        "derivation": "Only manifest rebound after selection B; all data members byte-identical"}
    guard.validate_embedded(result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source-bundle", "selection", "comparison-a", "comparison-b", "out"):
        p.add_argument("--" + name, required=True, type=Path)
    for name in ("source-bundle-sha256", "selection-sha256", "adapter-sha256", "scorer-sha256", "protocol-sha256"):
        p.add_argument("--" + name, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    source_path = a.source_bundle / "bundle.json"
    for path, expected in ((source_path, a.source_bundle_sha256), (a.selection, a.selection_sha256),
                           (HERE / "stack_confirmation_b_infer.py", a.adapter_sha256),
                           (HERE / "stack_confirmation_b_score.py", a.scorer_sha256),
                           (HERE / "PROTOCOLLO_STACK_CONFERMA_B.md", a.protocol_sha256)):
        if pilot.sha(path) != expected:
            raise ValueError("Reviewed B derivation identity changed: " + str(path))
    if pilot.sha(HERE / "PROTOCOLLO_STACK_AB.md") != guard.AB_SHA:
        raise ValueError("AB protocol changed")
    old = json.loads(source_path.read_text())
    result = rebind(old, a.selection.read_bytes(), {"A": a.comparison_a.read_bytes(), "B": a.comparison_b.read_bytes()},
        source_sha=a.source_bundle_sha256, selector_sha=pilot.sha(HERE / "select_stack_ab.py"),
        adapter_sha=a.adapter_sha256, scorer_sha=a.scorer_sha256, protocol_sha=a.protocol_sha256)
    expected_files = {"destination_controls.h5ad", "transfer.npz", *[f"source_{i:02d}.h5ad" for i in range(13)]}
    if set(old["files"]) != expected_files:
        raise ValueError("Original prepared member list differs")
    for name, expected in old["files"].items():
        if pilot.sha(a.source_bundle / name) != expected:
            raise ValueError("Prepared data changed: " + name)
    a.out.mkdir(parents=True)
    for name, expected in old["files"].items():
        shutil.copyfile(a.source_bundle / name, a.out / name)
        if pilot.sha(a.out / name) != expected:
            raise ValueError("Data copy differs: " + name)
    pilot.write_json(a.out / "bundle.json", result)
    print(json.dumps({"out": str(a.out), "bundle_sha256": pilot.sha(a.out / "bundle.json"),
                      "selected_variant": "B", "all_data_members_byte_identical": True}))


if __name__ == "__main__":
    main()
