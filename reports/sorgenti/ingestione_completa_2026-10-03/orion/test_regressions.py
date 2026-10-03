"""Small local regressions for the 3 October independent ingestion review; no network or cloud."""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common
import coverage_audit as ca
import campionamento_v2 as cv
import orion_job as oj
from test_coverage_audit import key, run


class TestTargetIdentity(unittest.TestCase):
    def test_partial_ids_share_one_fold(self):
        a, b = key("a", "K562", MYC=20), key("b", "HepG2", MYC=20)
        for row in a:
            if row["target"] == "MYC":
                row["target_id"] = "ENSG00000136997.7"
        res, _ = run(a + b)
        self.assertEqual(dict(res["support"]["all_modalities"]), {"ENSG00000136997": 2})
        self.assertNotEqual(ca.target_fold("ENSG00000136997", 5), ca.target_fold("SYM:MYC", 5))
        res, _ = run(a + b, hidden_fold=ca.target_fold("ENSG00000136997", 5))
        self.assertEqual(dict(res["support"]["all_modalities"]), {})

    def test_conflicting_explicit_identity_fails(self):
        a = key("a", "K562", TP53=20)
        for row in a:
            if row["target"] == "TP53":
                row["target_id"] = "ENSG00000141510"
        with self.assertRaisesRegex(ValueError, "conflicting target"):
            run(a, target_keys={"TP53": "ENSG00000000001"})


class TestPhaseGates(unittest.TestCase):
    def make_meta(self, root, ok=True, wrong_digest=False):
        root.mkdir()
        p = root / "HCT116.parquet"
        pd.DataFrame({"gem_file": ["g"], "row": [0], "gene_target": ["TP53"],
                      "pass_guide_filter": [1]}).to_parquet(p, index=False)
        digest = common.write_sidecar(p)
        common.dump_new(root / "HCT116.json", {"line": "HCT116", "table_sha256": "wrong" if wrong_digest else digest,
                                               "ok": ok, "parity": {"rows": ok}})

    def test_failed_meta_cannot_create_sample(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_meta(root / "meta", ok=False)
            with self.assertRaisesRegex(ValueError, "parity"):
                oj.phase_sample({"design": {"k": 1, "name": "srs_line_target", "salt": "test"}},
                                "HCT116", root / "meta", root / "sample")
            self.assertFalse((root / "sample").exists())

    def test_receipt_must_bind_exact_table(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "meta"
            self.make_meta(root, wrong_digest=True)
            with self.assertRaisesRegex(ValueError, "receipt"):
                oj.checked_table(root, "HCT116", "table_sha256", require_parity=True)

    def test_passed_meta_creates_bound_sample(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_meta(root / "meta")
            spec = {"design": {"k": 1, "name": "srs_line_target", "salt": "test"}}
            oj.phase_sample(spec, "HCT116", root / "meta", root / "sample")
            _, receipt = oj.checked_table(root / "sample", "HCT116", "sample_sha256")
            self.assertEqual(receipt["design"], spec["design"])

    def test_reuse_fingerprint_changes_with_axis_and_spec(self):
        spec = common.load_json(HERE / "specs/orion_v2.json")
        with tempfile.TemporaryDirectory() as td:
            axis = Path(td) / "axis.csv"
            axis.write_text("gene\nA\nB\n", encoding="utf-8")
            a = oj.reuse_fingerprint(spec, "HCT116", axis, "sample")
            axis.write_text("gene\nB\nA\n", encoding="utf-8")
            b = oj.reuse_fingerprint(spec, "HCT116", axis, "sample")
            self.assertNotEqual(a, b)
            spec["design"]["k"] += 1
            self.assertNotEqual(b, oj.reuse_fingerprint(spec, "HCT116", axis, "sample"))


class TestShardReceipts(unittest.TestCase):
    def test_real_writer_schema_and_two_restart_chain(self):
        adapters, _, _, _ = common.corpus()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = common.source_record("fixture", "fixture", "fixture",
                                          [{"locator": "fixture", "bytes": 1, "sha256": "fixture"}])
            sink = common.ShardSink(root / "one", root / "stage1", "unit", source, {"script": "fixture"},
                                    min_free_stage_bytes=0, require={"ingestion_fingerprint": "fp"})
            obs = adapters._obs(2, cell_key=["s|l|a", "s|l|b"], study="s", library="l", barcode=["a", "b"],
                                target=["NTC", "TP53"], control_kind=["NTC", "none"], context="HCT116",
                                modality="CRISPRi", chemistry="MISSING", guides="MISSING",
                                depth_native=[3, 4], depth_published=[3, 4],
                                depth_on_file_axis=[3, 4], n_genes_detected=[1, 1])
            var = oj.token_axis(pd.DataFrame({"gene_token_id": [0], "gene_name": ["TP53"]}), None)
            receipt = sink.put("g", sp.csr_matrix([[3], [4]]), obs, var, {"read": {"how": "fixture"}, "rows": {"n": 2}})
            self.assertEqual((receipt["sum_before"], receipt["sum_after"]), (7, 7))
            self.assertTrue(sink.finish({"fixture": True})["parity"]["ok"])
            second = common.ShardSink(root / "two", root / "stage2", "unit", source, {},
                                      [root / "one"], require={"ingestion_fingerprint": "fp"})
            self.assertIsNotNone(second.have("g"))
            third = common.ShardSink(root / "three", root / "stage3", "unit", source, {},
                                     [root / "two"], require={"ingestion_fingerprint": "fp"})
            self.assertIsNotNone(third.have("g"))
            self.assertEqual(len(third.shards), 1)
            bad = common.ShardSink(root / "bad", root / "stage_bad", "unit", source, {},
                                   [root / "two"], require={"ingestion_fingerprint": "changed"})
            self.assertIsNone(bad.have("g"))

    def test_checksum_mismatch_is_not_reused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            file = root / "one/unit/g.h5ad"
            file.parent.mkdir(parents=True)
            file.write_bytes(b"original")
            common.dump_new(file.parent / "receipts/g.json",
                            {"bytes": 8, "sha256": common.sha256_file(file), "path": str(file)})
            file.write_bytes(b"modified")
            sink = common.ShardSink(root / "two", root / "stage", "unit", {}, {}, [root / "one"])
            self.assertIsNone(sink.have("g"))


class TestSampling(unittest.TestCase):
    def test_tranche_union_equals_larger_sample_for_both_designs(self):
        obs = pd.DataFrame({"gem_file": ["a"] * 13 + ["b"] * 17 + ["c"],
                            "target": ["TP53"] * 30 + ["NTC"], "pass_guide_filter": 1,
                            "is_control": [False] * 30 + [True]}, index=[f"cell{i}" for i in range(31)])
        for design in cv.DESIGNS:
            with self.subTest(design=design):
                small = cv.select_orion(obs, "HCT116", "test", 5, design)
                nxt = cv.select_orion(obs, "HCT116", "test", 10, design, window=(5, 10))
                large = cv.select_orion(obs, "HCT116", "test", 10, design)
                chosen = lambda s: set(s.loc[s.selected, "cell"])
                self.assertFalse(chosen(small) & chosen(nxt))
                self.assertEqual(chosen(small) | chosen(nxt), chosen(large))
                self.assertTrue(np.allclose(small.pi + nxt.pi, large.pi))


if __name__ == "__main__":
    unittest.main()
