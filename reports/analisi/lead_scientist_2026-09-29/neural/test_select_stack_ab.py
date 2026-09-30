"""Selection boundaries, row-level eligibility, provenance and exact cell identity."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

import select_stack_ab as selector


def candidate(delta, pds=0):
    return {"delta_projection": float(delta), "delta_pds_raw": float(pds),
            "proceed_to_distinct_confirmation": bool(delta > 0 and pds >= 0)}


def fixtures():
    targets = [f"T{i:02d}" for i in range(12)]
    baseline = pd.DataFrame(np.ones((12, 5)), columns=selector.FIVE, index=targets)
    baseline.iloc[2, 1] = np.nan
    tables = {v: {"transfer": baseline.copy(), "stack": baseline + .06} for v in ("A", "B")}
    anchors = {m: {"baseline": 0, "replicate": 1} for m in selector.FIVE}
    comparisons = {}
    for v in ("A", "B"):
        a, b = tables[v]["stack"].to_numpy(), tables[v]["transfer"].to_numpy()
        comparisons[v] = candidate(float(np.nanmean((a-b)/6, axis=0).sum()), float(np.nanmean(a[:, 0]-b[:, 0])))
        comparisons[v]["raw"] = {arm: {m: float(tables[v][arm][m].mean()) for m in selector.FIVE} for arm in ("transfer", "stack")}
        comparisons[v]["truth_cells_per_target"] = dict.fromkeys(targets, 50)
    return tables, comparisons, anchors


class SelectionTests(unittest.TestCase):
    def test_exact_tie_a_and_next_float_b(self):
        self.assertEqual(selector.choose({"A": candidate(.1), "B": candidate(.1)}), "A")
        self.assertEqual(selector.choose({"A": candidate(.1), "B": candidate(np.nextafter(.1, 1.))}), "B")
        self.assertEqual(selector.choose({"A": candidate(.1, -.00001), "B": candidate(.01)}), "B")
        self.assertIsNone(selector.choose({"A": candidate(0), "B": candidate(-.1)}))

    def test_incomplete_or_inconsistent_or_nonfinite_gate_rejected(self):
        for values in ({"A": candidate(.1)}, {"A": candidate(.1), "B": candidate(float("nan"))},
                       {"A": candidate(.1), "B": candidate(0) | {"proceed_to_distinct_confirmation": True}}):
            with self.assertRaises(ValueError):
                selector.choose(values)

    def test_valid_metrics_and_changed_comparison_rejected(self):
        tables, comparisons, anchors = fixtures()
        result = selector.verify_tables(tables, comparisons, anchors)
        self.assertTrue(result["four_arm_eligibility_identical"])
        comparisons["B"]["delta_projection"] += .001
        with self.assertRaisesRegex(ValueError, "reconstructed"):
            selector.verify_tables(tables, comparisons, anchors)

    def test_equal_eligibility_counts_different_targets_rejected(self):
        tables, comparisons, anchors = fixtures()
        tables["B"]["stack"].iloc[2, 1] = 1.06
        tables["B"]["stack"].iloc[3, 1] = np.nan
        with self.assertRaisesRegex(ValueError, "Per-target/member"):
            selector.verify_tables(tables, comparisons, anchors)

    def test_symmetric_infinity_and_missing_pds_rejected(self):
        for metric, value in ((2, np.inf), (0, np.nan)):
            tables, comparisons, anchors = fixtures()
            for v in tables.values():
                for t in v.values():
                    t.iloc[0, metric] = value
            with self.assertRaisesRegex(ValueError, "Infinite member or missing PDS"):
                selector.verify_tables(tables, comparisons, anchors)

    def test_transfer_metric_mismatch_rejected(self):
        tables, comparisons, anchors = fixtures()
        tables["B"]["transfer"].iloc[0, 2] += .001
        with self.assertRaisesRegex(ValueError, "exactly identical"):
            selector.verify_tables(tables, comparisons, anchors)

    def test_mse_is_ratio_of_sums(self):
        tables, comparisons, anchors = fixtures()
        for v in ("A", "B"):
            for arm in ("transfer", "stack"):
                frame = tables[v][arm]
                frame["expr_mse_unbiased_capped"] = [1, 100] * 6
                frame["expr_distance_unbiased"] = [1, 10] * 6
                comparisons[v]["raw"][arm][selector.MSE] = 101 / 11
        selector.verify_tables(tables, comparisons, anchors)
        comparisons["B"]["raw"]["stack"][selector.MSE] = 5.5
        with self.assertRaisesRegex(ValueError, "ratio-of-sums"):
            selector.verify_tables(tables, comparisons, anchors)

    def test_h5ad_serialization_differences_preserve_exact_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            obj = ad.AnnData(sp.csr_matrix([[0, 2, 3], [7, 0, 1]], dtype=np.float32),
                obs=pd.DataFrame({"gene": ["T1", "T2"]}, index=["a", "b"]),
                var=pd.DataFrame(index=["G3", "G1", "G2"]))
            obj.write_h5ad(root / "a.h5ad")
            obj.write_h5ad(root / "b.h5ad", compression="gzip")
            self.assertNotEqual(selector.pilot.sha(root / "a.h5ad"), selector.pilot.sha(root / "b.h5ad"))
            self.assertEqual(selector.prediction_fingerprint(root / "a.h5ad"), selector.prediction_fingerprint(root / "b.h5ad"))
            obj.X.data[0] += 1
            obj.write_h5ad(root / "c.h5ad")
            self.assertNotEqual(selector.prediction_fingerprint(root / "a.h5ad"), selector.prediction_fingerprint(root / "c.h5ad"))

    def test_b_provenance_must_bind_a_preparation_and_ab_protocol(self):
        bundle = {"targets": [f"T{i}" for i in range(12)]}
        evaluation = {"status": "registered_before_truth_expression_read", "targets": bundle["targets"],
            "bundle_sha256": selector.BUNDLE_SHA, "anchors_sha256": selector.ANCHORS_SHA,
            "scoring_code_sha256": selector.SCORERS["B"]}
        infer = {"bundle_sha256": selector.BUNDLE_SHA, "adapter_sha256": selector.ADAPTERS["B"],
            "checkpoint_sha256": selector.pilot.CHECKPOINT_SHA, "genelist_sha256": selector.pilot.GENELIST_SHA,
            "preparation_adapter_sha256": selector.ADAPTERS["A"], "ab_protocol_sha256": selector.AB_SHA,
            "input_axis_policy": "own_measured_support"}
        finished = {"targets": bundle["targets"], "cells_per_target": 400}
        selector.provenance(evaluation, infer, finished, bundle, "B")
        for key in ("preparation_adapter_sha256", "ab_protocol_sha256"):
            with self.assertRaisesRegex(ValueError, "Inference provenance"):
                selector.provenance(evaluation, infer | {key: "wrong"}, finished, bundle, "B")

    def test_nullable_categorical_labels_and_gene_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nullable.h5ad"
            categories = pd.Index(pd.array(["T1", "T2"], dtype="string"))
            obj = ad.AnnData(sp.csr_matrix(np.ones((4, 2)), dtype=np.float32),
                obs=pd.DataFrame({"gene": pd.Categorical(["T1", "T1", "T2", "T2"], categories=categories)}, index=list("abcd")),
                var=pd.DataFrame(index=pd.Index(pd.array(["G1", "G2"], dtype="string"))))
            with ad.settings.override(allow_write_nullable_strings=True):
                obj.write_h5ad(path)
            self.assertEqual(selector.prediction_fingerprint(path)["shape"], [4, 2])


if __name__ == "__main__":
    unittest.main()
