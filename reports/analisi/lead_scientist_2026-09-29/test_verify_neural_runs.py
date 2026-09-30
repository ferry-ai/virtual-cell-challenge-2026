import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from verify_neural_runs import verify, CONTEXTS, ARMS
from read_neural_sources import readout


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.runs = []
        contexts = sorted(c for v in CONTEXTS.values() for c in v) + ["a549"]
        hashes = {n: "frozen" for n in ["PROTOCOLLO_NEURALE.md", "neural_sources.py", "train_neural_sources.py", "pool.py"]}
        for family, members in CONTEXTS.items():
            folder = self.root / family
            folder.mkdir()
            self.runs.append(folder)
            plan = {"hidden_contexts": [contexts.index(c) for c in members],
                    "test": {str(contexts.index(c)): [contexts.index(c) * 10, contexts.index(c) * 10 + 1] for c in members},
                    "validation": {"0": [900, 901]}, "train": [1000, 1001], "refit": [900, 901, 1000, 1001], "validation_family": "inner"}
            manifest = {"options": {"holdout": family, "plan_only": False, "steps": 1000, "seed": 0,
                                    "regime": "C", "selection_seed": 20260929, "test_targets": 512},
                        "design": plan, "data_files": {"raw.npy": {"bytes": 99, "sha256": None}}, "code_hashes": hashes,
                        "context_names": contexts, "family_names": sorted(CONTEXTS), "prior_columns": ["p_string_deg"]}
            (folder / "manifest.json").write_text(json.dumps(manifest))
            table = [{"family": family, "context": c, "target": t, "arm": a, "rank": .5}
                     for c in members for t in ["t0", "t1"] for a in ARMS]
            pd.DataFrame(table).to_csv(folder / "per_target.csv", index=False)

    def tearDown(self):
        self.tmp.cleanup()

    def mutate_manifest(self, update):
        path = self.runs[0] / "manifest.json"
        manifest = json.loads(path.read_text())
        update(manifest)
        path.write_text(json.dumps(manifest))

    def test_full_snapshot_and_coverage(self):
        self.assertTrue(verify(self.runs)["verified"])

    def test_corrected_reader_keeps_literal_null_and_na_target(self):
        for run in self.runs:
            path = run / "per_target.csv"
            table = pd.read_csv(path, keep_default_na=False)
            table.loc[table.target == "t0", "target"] = "NA"
            table.to_csv(path, index=False)
        verify(self.runs)
        result, table = readout(self.runs)
        self.assertIn("null", result["contrasts"])
        self.assertIn("NA", set(table.target))
        self.assertFalse(result["eligible_for_cell_scorer"])

    def test_changed_code_is_not_combined(self):
        self.mutate_manifest(lambda m: m["code_hashes"].update({"neural_sources.py": "changed"}))
        with self.assertRaisesRegex(ValueError, "differ across folds"):
            verify(self.runs)

    def test_one_removed_target_is_refused(self):
        path = self.runs[0] / "per_target.csv"
        table = pd.read_csv(path, keep_default_na=False)
        table.iloc[1:].to_csv(path, index=False)
        with self.assertRaisesRegex(ValueError, "lost frozen"):
            verify(self.runs)

    def test_leaked_test_row_is_refused(self):
        self.mutate_manifest(lambda m: m["design"]["train"].append(next(iter(m["design"]["test"].values()))[0]))
        with self.assertRaisesRegex(ValueError, "test row entered"):
            verify(self.runs)

    def test_missing_family_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Incomplete family"):
            verify(self.runs[:-1])


if __name__ == "__main__":
    unittest.main()
