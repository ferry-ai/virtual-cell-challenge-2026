"""No model or data: enforce receipt/gate binding and actual adapter CLI."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import build_stack_confirmation_runtime as builder


class RuntimeContract(unittest.TestCase):
    def test_gate_boundaries(self):
        good = {"proceed_to_distinct_confirmation": True, "delta_projection": .001, "delta_pds_raw": 0}
        self.assertTrue(builder.gate_passed(good))
        for bad in ({"delta_projection": 0}, {"delta_projection": float("nan")}, {"delta_pds_raw": -.001}, {"proceed_to_distinct_confirmation": False}):
            self.assertFalse(builder.gate_passed(good | bad))

    def test_built_runtime_binds_new_adapter_and_has_no_infer_subcommand(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = {"targets": builder.EXPECTED, "status": "prepared_no_model_no_scores",
                "protocol_sha256": builder.FROZEN["PROTOCOLLO_STACK_CONFERMA.md"],
                "inference_adapter_sha256": builder.FROZEN["stack_confirmation_infer.py"],
                "scoring_code_sha256": builder.FROZEN["stack_confirmation_score.py"],
                "plan_sha256": "synthetic-plan-only", "files": {n: "fixture" for n in ["destination_controls.h5ad", "transfer.npz", *[f"source_{i:02d}.h5ad" for i in range(13)]]}}
            comparison = {"proceed_to_distinct_confirmation": True, "delta_projection": .001, "delta_pds_raw": 0}
            for name, obj in (("bundle.json", bundle), ("comparison.json", comparison)):
                (root / name).write_text(json.dumps(obj))
            args = SimpleNamespace(bundle_manifest=root / "bundle.json", pilot_comparison=root / "comparison.json",
                bundle_manifest_sha256=builder.sha((root / "bundle.json").read_bytes()),
                pilot_comparison_sha256=builder.sha((root / "comparison.json").read_bytes()),
                out=root / "out", dataset="fixture/confirmation-input", kernel="fixture/confirmation-run",
                bundle_archive_sha256=None, bundle_archive_bytes=None)
            review = builder.build(args)
            source = (args.out / "stack_confirmation_r1.py").read_text()
            ast.parse(source)
            self.assertIn('report / "stack_confirmation_infer.py", "--bundle", bundle,', source)
            self.assertNotIn('report / "stack_pilot.py", "infer",', source)
            self.assertIn('"/kaggle/working/lead_stack_confirmation_r1"', source)
            self.assertEqual(review["pilot_comparison_sha256"], args.pilot_comparison_sha256)
            self.assertEqual(review["targets"], builder.EXPECTED)
            self.assertIsNone(review["bundle_archive_sha256"])
            names = {row["path"] for row in review["code_files"]}
            self.assertIn(builder.REL + "/requirements_stack.txt", names)
            self.assertIn(builder.REL + "/test_stack_pilot.py", names)
            self.assertIn(builder.REL + "/stack_confirmation_score.py", names)


if __name__ == "__main__":
    unittest.main()
