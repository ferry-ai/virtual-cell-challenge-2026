"""Small CPU interface and counterexample tests; no biological evaluation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from pie_adapter import adapt, check_exposure, export, read_pie, sha256
from embedding_ridge import MaskedRidge
from run_embedding_probe import run
from export_stage100 import export_stage100


def fixture():
    requests = [dict(dataset="toy", context="held", perturbation="T1", context_group="held",
                     target_components=["T1"]),
                dict(dataset="toy", context="held", perturbation="T2", context_group="held",
                     target_components=["T2"])]
    row = dict(dataset="toy", context="held", perturbation="T1", p_de=[0.0, 0.9],
               lfc_pred=[0.0, 2.0], delta_p_pred=[9.0, -3.0])
    contract = dict(schema_version=1, regime="J", code_revision="a"*40,
        assets=[dict(revision="a"*40, sha256="b"*64, role="fixture")], license_review="fixture only",
        baseline_stage="final_effect_before_emitter",
        postprocess=dict(gain=1.0, center=False, cis=False),
        normalization_bridge=dict(status="verified", evidence_sha256="b"*64,
            source_quantity="log2_fold_change", destination_quantity="ln_fold_change",
            source_normalization="toy", destination_normalization="toy", pseudocount_policy="toy",
            denominator_gene_axis_sha256="c"*64, review_id="synthetic-test"),
        exposure=dict(status="reviewed", review_id="synthetic-test", complete_label_inventory=True,
                      label_context_groups=["training"], label_target_components=["T0"], knowledge_sources=[]))
    for name in ("release", "protocol", "checkpoint", "predictions", "baseline"):
        contract[name+"_sha256"] = "a"*64
    base = np.array([[5., 6., 7.], [8., 9., 10.]])
    return {"toy": ["g2", "g1"]}, [row], requests, ["g1", "g2", "missing"], base, np.ones_like(base, dtype=bool), contract


class AdapterTests(unittest.TestCase):
    def test_reorder_zero_and_fallback(self):
        args = fixture()
        result = adapt(*args)
        np.testing.assert_allclose(result["effects"][0], [2*np.log(2), 0, 7])
        self.assertEqual(result["effects"][1].tobytes(), args[4][1].tobytes())
        self.assertEqual(result["external_mask"].sum(), 2)
        self.assertEqual(result["p_de"][0, 0], 0.9)
        self.assertEqual(result["delta_p_pred"][0, 0], -3)

    def test_empty_branch_identity(self):
        args = list(fixture()); args[1] = []
        self.assertEqual(adapt(*args)["effects"].tobytes(), args[4].tobytes())

    def test_normalization_and_double_correction_rejected(self):
        for change in ("normalization", "gain", "center", "cis"):
            args = list(fixture())
            if change == "normalization":
                args[-1]["normalization_bridge"]["status"] = "unknown"
            else:
                args[-1]["postprocess"][change] = 2 if change == "gain" else True
            with self.assertRaises(ValueError): adapt(*args)

    def test_exposure_and_protected_rows(self):
        for case in ("context", "target", "unknown", "protected"):
            args = list(fixture())
            if case == "context": args[-1]["exposure"]["label_context_groups"].append("held")
            if case == "target": args[-1]["exposure"]["label_target_components"].append("T1")
            if case == "unknown": args[-1]["exposure"]["complete_label_inventory"] = False
            if case == "protected": args[2][0]["protected"] = True
            with self.assertRaises(ValueError): adapt(*args)

    def test_missing_baseline_remains_masked(self):
        args = list(fixture()); args[5][0, 2] = False; args[4][0, 2] = np.nan
        output = adapt(*args)
        self.assertFalse(output["mask"][0, 2])
        self.assertTrue(np.isnan(output["effects"][0, 2]))

    def test_duplicate_axes_rows_nonfinite_probabilities(self):
        for case in ("axis", "row", "request", "lfc", "prob"):
            args = list(fixture())
            if case == "axis": args[0]["toy"] = ["g1", "g1"]
            if case == "row": args[1].append(args[1][0])
            if case == "request": args[2][1] = args[2][0]
            if case == "lfc": args[1][0]["lfc_pred"][0] = np.nan
            if case == "prob": args[1][0]["p_de"][0] = 1.1
            with self.assertRaises(ValueError): adapt(*args)

    def test_parquet_cli_export_and_hash_tampering(self):
        axes, rows, requests, genes, base, mask, contract = fixture()
        mask[1, 2] = False
        base[1, 2] = np.nan
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            table = pa.Table.from_pylist(rows).replace_schema_metadata(
                {b"pie": json.dumps(dict(format_version=1, genes=axes)).encode()})
            pred = root/"pred.parquet"; pq.write_table(table, pred)
            parsed_axes, parsed = read_pie(pred)
            self.assertEqual(parsed_axes, axes)
            np.testing.assert_array_equal(parsed[0]["lfc_pred"], rows[0]["lfc_pred"])
            baseline = root/"base.npz"
            np.savez(baseline, effects=base, mask=mask, genes=genes,
                     **{n: [r[n] for r in requests] for n in ("dataset", "context", "perturbation")})
            contract.update(genes=genes, requests=requests, predictions_sha256=sha256(pred),
                            baseline_sha256=sha256(baseline))
            conf = root/"contract.json"; conf.write_text(json.dumps(contract))
            manifest = export(pred, baseline, conf, root/"out")
            self.assertEqual(manifest["external_cells"], 2)
            final = export_stage100(root/"out", root/"stage100")
            with np.load(root/"stage100"/final["files"][0]["file"], allow_pickle=False) as saved:
                self.assertEqual(set(saved.files), {"targets", "genes", "lfc", "observed"})
                self.assertEqual(saved["lfc"].dtype, np.float32)
                np.testing.assert_allclose(saved["lfc"][0], [2*np.log(2), 0, 7])
                np.testing.assert_array_equal(saved["targets"], ["T1", "T2"])
                self.assertEqual(saved["lfc"][1, 2], 0)
                self.assertFalse(saved["observed"][1, 2])
            with self.assertRaises(FileExistsError): export_stage100(root/"out", root/"stage100")
            with (root/"out"/"effects.npz").open("ab") as stream: stream.write(b"tamper")
            with self.assertRaisesRegex(ValueError, "checksum"): export_stage100(root/"out", root/"stage100_bad")
            with self.assertRaises(FileExistsError): export(pred, baseline, conf, root/"out")
            with pred.open("ab") as stream: stream.write(b"changed")
            with self.assertRaisesRegex(ValueError, "actual input"): export(pred, baseline, conf, root/"out2")

    def test_parquet_missing_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"p.parquet"; pq.write_table(pa.Table.from_pylist(fixture()[1]), path)
            with self.assertRaises(ValueError): read_pie(path)


class RidgeTests(unittest.TestCase):
    def inputs(self):
        x = np.array([[0., 1.], [1., 0.], [2., 1.], [3., 0.]])
        y = np.column_stack((2*x[:, 0], -x[:, 0], np.zeros(4)))
        mask = np.ones(y.shape, bool); mask[1, 1] = False; mask[:, 2] = False
        policy = dict(row_contexts=["train"]*4, row_targets=["a", "b", "c", "d"],
                      excluded_contexts=["test"], excluded_targets=["z"])
        return x, y, mask, policy

    def test_hidden_values_do_not_affect_fit(self):
        x, y, mask, policy = self.inputs()
        a = MaskedRidge().fit(x, y, mask, **policy)
        y[~mask] = 1e100
        b = MaskedRidge().fit(x, y, mask, **policy)
        np.testing.assert_array_equal(a.coef, b.coef)
        prediction, support = b.predict(x)
        self.assertFalse(support[:, 2].any())
        self.assertTrue(np.isnan(prediction[:, 2]).all())
        y[0, 0] += 1
        c = MaskedRidge().fit(x, y, mask, **policy)
        self.assertFalse(np.array_equal(a.coef, c.coef))

    def test_forbidden_rows_rejected(self):
        x, y, mask, policy = self.inputs(); policy["excluded_targets"] = ["a"]
        with self.assertRaises(ValueError): MaskedRidge().fit(x, y, mask, **policy)

    def test_missing_features_and_generic(self):
        x, y, mask, policy = self.inputs()
        model = MaskedRidge().fit(x, y, mask, **policy)
        x[0] = np.nan
        result, support = model.predict(x, np.array([False, True, True, True]))
        self.assertTrue(np.isnan(result[0]).all()); self.assertFalse(support[0].any())
        self.assertEqual(model.generic[0], 3.)
        self.assertEqual(model.receipt["contexts_read"], ["train"])

    def test_ridge_matches_independent_augmented_least_squares(self):
        x, y, mask, policy = self.inputs()
        model = MaskedRidge(alpha=0.2).fit(x, y, mask, **policy)
        z = (x-model.feature_mean)/model.feature_scale
        for j in (0, 1):
            selected = mask[:, j]; n = selected.sum()
            design = np.column_stack((z[selected], np.ones(n))) / np.sqrt(n)
            penalty = np.column_stack((np.sqrt(0.2)*np.eye(2), np.zeros(2)))
            coef = np.linalg.lstsq(np.vstack((design, penalty)),
                                  np.r_[y[selected, j]/np.sqrt(n), 0., 0.], rcond=None)[0]
            np.testing.assert_allclose(model.coef[:, j], coef[:2], atol=1e-12)
            self.assertAlmostEqual(model.intercept[j], coef[-1])

    def test_frozen_runner_roundtrip_and_coverage_guard(self):
        x, y, mask, policy = self.inputs()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); features = root/"esm2"; features.mkdir()
            meta = dict(name="esm2", layout="dense", index="pert", keys=["a", "b", "c", "d", "z"],
                        dim=2, dtype="float32", provenance={"synthetic": True})
            (features/"meta.json").write_text(json.dumps(meta))
            np.save(features/"embeddings.npy", np.vstack([x, [[4., 1.]]]).astype("float32"))
            train = root/"train.npz"
            np.savez(train, targets=policy["row_targets"], context_groups=policy["row_contexts"],
                     context_ids=["study1"]*4,
                     genes=["g1", "g2", "g3"], effects=y, observed=mask, weights=np.ones(4))
            manifest = dict(schema_version=1, protocol_status="agreed", validation_review="synthetic-test",
                mode="development", regime="J", modality="CRISPRi", quantity="toy", normalization="toy",
                train=dict(path=str(train), sha256=sha256(train)), expected_rows_by_context={"study1":4},
                esm2=dict(path=str(features), sha256={n:sha256(features/n) for n in ("meta.json", "embeddings.npy")}),
                queries=[dict(context_id="held-study", context_group="test", target="z")], alpha=0.2,
                excluded_contexts=["test"], excluded_targets=["z"])
            path=root/"manifest.json"; path.write_text(json.dumps(manifest))
            receipt=run(path, root/"out")
            self.assertEqual(receipt["scientific_benefit"], "not_scored")
            with np.load(root/"out"/"native_predictions.npz", allow_pickle=False) as saved:
                self.assertEqual(saved["effects"].shape, (1,3))
                self.assertFalse(saved["observed"][0,2])
            # Same lineage/target in independent studies must remain separate rows.
            np.savez(train, targets=["a", "a", "c", "d"], context_groups=["train"]*4,
                     context_ids=["study1", "study2", "study1", "study1"],
                     genes=["g1", "g2", "g3"], effects=y, observed=mask, weights=np.ones(4))
            manifest["train"]["sha256"] = sha256(train)
            manifest["expected_rows_by_context"] = {"study1":3, "study2":1}
            path.write_text(json.dumps(manifest))
            receipt = run(path, root/"two-studies")
            self.assertEqual(receipt["consumed_rows_by_lineage"], {"train":4})
            self.assertEqual(receipt["consumed_rows_by_context"], {"study1":3, "study2":1})
            manifest["expected_rows_by_context"]["study1"] = 5
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "D-053"): run(path, root/"out2")


if __name__ == "__main__":
    unittest.main()
