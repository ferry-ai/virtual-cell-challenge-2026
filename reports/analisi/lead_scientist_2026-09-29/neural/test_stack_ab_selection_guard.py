"""Both comparisons and one frozen choice must survive builder/runtime checks."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import build_stack_confirmation_runtime_r2 as builder
import stack_ab_selection_guard as guard


def receipt(a=.02, b=.01):
    comparisons = {"A": {"delta_projection": a, "delta_pds_raw": 0., "proceed_to_distinct_confirmation": a > 0},
                   "B": {"delta_projection": b, "delta_pds_raw": 0., "proceed_to_distinct_confirmation": b > 0}}
    blobs = {v: json.dumps(r).encode() for v, r in comparisons.items()}
    hashes = {v: builder.sha(s) for v, s in blobs.items()}
    candidates = {v: {"comparison_sha256": hashes[v], "eligible": r["proceed_to_distinct_confirmation"],
                      "delta_projection": r["delta_projection"], "delta_pds_raw": r["delta_pds_raw"]} for v, r in comparisons.items()}
    selected = None if max(a, b) <= 0 else ("B" if b > a else "A")
    selection = {"status": "selection_complete", "ab_protocol_sha256": guard.AB_SHA,
        "selector_sha256": builder.sha((builder.HERE / "select_stack_ab.py").read_bytes()),
        "candidates": candidates, "selected_variant": selected,
        "input_files": {v + "/pilot_comparison.json": {"sha256": hashes[v]} for v in hashes},
        "checks": dict.fromkeys(("four_arm_eligibility_identical", "transfer_metric_values_exact", "controls_exact_common_bundle",
                                 "transfer_counts_axes_exact", "scoring_environment_identical", "selection_uses_original_float64"), True)}
    return selection, comparisons, blobs, hashes


class GuardTests(unittest.TestCase):
    def test_exact_choice_and_receipt_mismatches(self):
        s, c, _, h = receipt()
        self.assertEqual(guard.validate(s, c, h, s["selector_sha256"]), "A")
        for changed in (s | {"selected_variant": "B"}, s | {"status": "partial"}, s | {"ab_protocol_sha256": "bad"},
                        s | {"checks": s["checks"] | {"four_arm_eligibility_identical": False}}):
            with self.assertRaises(ValueError):
                guard.validate(changed, c, h, s["selector_sha256"])
        with self.assertRaises(ValueError):
            guard.validate(s, c, h | {"B": "bad"}, s["selector_sha256"])

    def test_b_or_null_never_silently_becomes_a(self):
        for a, b, expected in ((.01, .02, "B"), (.01, .01, "A"), (-.01, 0., None)):
            s, c, _, h = receipt(a, b)
            self.assertEqual(guard.validate(s, c, h, s["selector_sha256"]), expected)

    def test_actual_a_builder_embeds_and_rechecks_both_reports(self):
        s, c, blobs, _ = receipt()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "selection.json").write_text(json.dumps(s))
            for v in blobs:
                (root / (v + ".json")).write_bytes(blobs[v])
            frozen = builder.original.FROZEN
            bundle = {"targets": builder.original.EXPECTED, "status": "prepared_no_model_no_scores", "plan_sha256": "fixtureplan",
                "protocol_sha256": frozen["PROTOCOLLO_STACK_CONFERMA.md"], "inference_adapter_sha256": frozen["stack_confirmation_infer.py"],
                "scoring_code_sha256": frozen["stack_confirmation_score.py"],
                "files": dict.fromkeys(["destination_controls.h5ad", "transfer.npz", *[f"source_{i:02d}.h5ad" for i in range(13)]], "fixtureonly")}
            (root / "bundle.json").write_text(json.dumps(bundle))
            args = SimpleNamespace(selection=root / "selection.json", selection_sha256=builder.sha((root / "selection.json").read_bytes()),
                comparison_a=root / "A.json", comparison_b=root / "B.json", bundle_manifest=root / "bundle.json",
                bundle_manifest_sha256=builder.sha((root / "bundle.json").read_bytes()),
                adapter=builder.HERE / "stack_confirmation_infer.py", adapter_sha256=frozen["stack_confirmation_infer.py"],
                protocol=builder.HERE / "PROTOCOLLO_STACK_CONFERMA.md", protocol_sha256=frozen["PROTOCOLLO_STACK_CONFERMA.md"],
                scorer=builder.HERE / "stack_confirmation_score.py", scorer_sha256=frozen["stack_confirmation_score.py"],
                dataset="fixture/input", kernel="fixture/confirmation", bundle_archive_sha256=None, bundle_archive_bytes=None,
                out=root / "out")
            review = builder.build(args)
            self.assertEqual(guard.validate_embedded(review), "A")
            runtime = (args.out / "stack_confirmation_selected_r1.py").read_text()
            self.assertLess(runtime.index("stack_ab_selection_guard.validate_embedded(review)"), runtime.index("python = create_managed_runtime"))
            self.assertIn("report / 'stack_confirmation_infer.py', \"--bundle\", bundle,", runtime)
            broken = review | {"ab_comparison_json": review["ab_comparison_json"] | {"B": blobs["B"].decode() + " "}}
            with self.assertRaises(ValueError):
                guard.validate_embedded(broken)


if __name__ == "__main__":
    unittest.main()
