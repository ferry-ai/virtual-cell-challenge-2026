"""Small launcher and readout contract tests; no model, real data or network."""
import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

import score_stack_pilot as score
import stack_remote_runner as remote


def archive_bytes(entries):
    b = io.BytesIO()
    with tarfile.open(fileobj=b, mode="w:gz") as t:
        for name, contents in entries:
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            t.addfile(info, io.BytesIO(contents))
    return b.getvalue()


class RemoteTest(unittest.TestCase):
    def test_extract_exact_rejects_extra_duplicate_and_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "safe"
            remote.extract_exact(archive_bytes([("./a.txt", b"ok")]), dest,
                                 {"a.txt": hashlib.sha256(b"ok").hexdigest()})
            self.assertEqual((dest / "a.txt").read_bytes(), b"ok")
            for entries, expected in [([("extra", b"x")], {"a.txt": None}),
                ([("same", b"x"), ("same", b"x")], {"same": None}),
                ([("../escape", b"x")], {"../escape": None})]:
                with self.assertRaises(ValueError):
                    remote.extract_exact(archive_bytes(entries), Path(tmp) / "other", expected)

    def test_projection_sign_and_exact_null(self):
        targets = [f"T{i}" for i in range(12)]
        base = pd.DataFrame(.2, index=targets, columns=score.FIVE)
        anchor = {m: {"baseline": 0., "replicate": 1.} for m in score.FIVE}
        anchor["de_wilcoxon_lfc_nmae"] = {"baseline": 1., "replicate": 0.}
        null = score.contrast(base, base, anchor)
        self.assertEqual(null["delta_projection"], 0)
        self.assertFalse(null["proceed_to_distinct_confirmation"])
        candidate = base.copy()
        candidate["pds_cosine"] += .06
        candidate["de_wilcoxon_lfc_nmae"] -= .12
        changed = score.contrast(candidate, base, anchor)
        self.assertAlmostEqual(changed["delta_projection"], .03)
        self.assertTrue(changed["proceed_to_distinct_confirmation"])
        candidate["pds_cosine"] = .1
        self.assertFalse(score.contrast(candidate, base, anchor)["proceed_to_distinct_confirmation"])

    def test_eligibility_change_is_not_ignored(self):
        base = pd.DataFrame(.2, index=range(12), columns=score.FIVE)
        candidate = base.copy()
        candidate.iloc[0, 0] = np.nan
        anchors = {m: {"baseline": 0., "replicate": 1.} for m in score.FIVE}
        with self.assertRaises(ValueError):
            score.contrast(candidate, base, anchors)

    def test_mse_uses_ratio_of_sums_not_mean_of_ratios(self):
        table = pd.DataFrame(.2, index=["A", "B"], columns=score.FIVE)
        table["expr_mse_unbiased_capped"] = [1., 0.]
        table["expr_distance_unbiased"] = [1., 9.]
        raw = dict.fromkeys(score.FIVE, .2)
        raw["expr_mse_unbiased_capped_norm"] = .1
        result = score.verify_aggregation(table, raw)
        self.assertEqual(result["ratio"], .1)
        self.assertEqual(float((table.expr_mse_unbiased_capped / table.expr_distance_unbiased).mean()), .5)
        raw["expr_mse_unbiased_capped_norm"] = .5
        with self.assertRaises(ValueError):
            score.verify_aggregation(table, raw)

    def test_prediction_contract_requires_all_400_cells(self):
        genes = ["a", "b"]
        obj = ad.AnnData(sp.csr_matrix(np.ones((800, 2), dtype=np.float32)),
            obs=pd.DataFrame({"gene": ["T1"] * 400 + ["T2"] * 400}, index=[str(i) for i in range(800)]),
            var=pd.DataFrame(index=genes))
        x, labels = score.validate_prediction(obj, ["T1", "T2"], genes)
        self.assertEqual(x.shape, (800, 2))
        with self.assertRaises(ValueError):
            score.validate_prediction(obj[:-1].copy(), ["T1", "T2"], genes)
        with self.assertRaises(ValueError):
            score.validate_prediction(obj, ["T1", "T2"], genes[::-1])

    def test_readout_rejects_missing_targets_and_nonfinite_pds(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "metrics.csv"
            pd.DataFrame({"perturbation": ["A", "C"], "metric": ["pds_cosine"] * 2,
                          "value": [.1, .2]}).to_csv(p, index=False)
            with self.assertRaises(ValueError):
                score.per_target(p, ["A", "B"])
            pd.DataFrame({"perturbation": ["A", "B"], "metric": ["pds_cosine"] * 2,
                          "value": [.1, np.nan]}).to_csv(p, index=False)
            with self.assertRaises(ValueError):
                score.per_target(p, ["A", "B"])

    def test_provenance_binds_adapter_weights_and_genelist(self):
        infer = {"bundle_sha256": "bundle", "adapter_sha256": "adapter",
                 "checkpoint_sha256": score.pilot.CHECKPOINT_SHA, "genelist_sha256": score.pilot.GENELIST_SHA}
        score.verify_inference_provenance(infer, {"adapter_sha256": "adapter"}, "bundle")
        for field in infer:
            changed = infer | {field: "changed"}
            with self.assertRaises(ValueError):
                score.verify_inference_provenance(changed, {"adapter_sha256": "adapter"}, "bundle")

    def test_paired_null_retains_baseline_shared_mass_not_full_basal(self):
        basal, baseline = np.array([10., 20., 7.]), np.array([15., 17., 5.])
        generated = sp.csr_matrix([[4., 2., 1.]])
        result, info = score.pilot.corrected_profile(basal, baseline, ["A", "B", "C"],
            ["A", "B", "C"], {"A", "B"}, generated, generated)
        np.testing.assert_allclose(result, [10 * 32 / 30, 20 * 32 / 30, 5])
        self.assertEqual(info["shared_lfc_rms"], 0)
        self.assertEqual(float(result[:2].sum()), float(baseline[:2].sum()))
        self.assertFalse(np.allclose(result, basal))


if __name__ == "__main__":
    unittest.main()
