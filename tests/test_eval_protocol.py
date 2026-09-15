"""Contracts for the frozen evaluation protocol: leakage, anchors, promotion."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(REPO / "src"))

from vcc2026.eval_protocol import (  # noqa: E402
    audit_split_file,
    load_protocol,
    local_anchor_deltas,
    promotion_decision,
    split_cells_for_anchors,
    tag_split_role,
)


class ProtocolLoadTests(unittest.TestCase):
    def test_frozen_protocol_loads(self):
        proto = load_protocol(REPO / "configs" / "eval_protocol.yaml")
        self.assertIn("new_context_unseen_target", proto.protocols)
        self.assertEqual(proto.confirmation_seed, 4242)
        self.assertIn(2026, proto.development_seeds)

    def test_rejects_unfrozen_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.yaml"
            path.write_text("frozen: false\nprotocols: []\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen"):
                load_protocol(path)


class SplitAuditTests(unittest.TestCase):
    def _write(self, payload):
        directory = Path(tempfile.mkdtemp())
        path = directory / "split.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path

    def test_unseen_overlap_fails(self):
        path = self._write({
            "protocol": "new_context_unseen_target",
            "direction_id": "toy",
            "train_context": "X",
            "test_context": "Y",
            "train_targets": ["A", "B"],
            "test_targets": ["B", "C"],
            "inner_val_targets": [],
            "seed": 2026,
        })
        audit = audit_split_file(path)
        self.assertFalse(audit["ok"])
        self.assertTrue(any(f["id"] == "unseen_target_in_train" for f in audit["findings"]))

    def test_unseen_disjoint_passes(self):
        path = self._write({
            "protocol": "new_context_unseen_target",
            "direction_id": "toy",
            "train_context": "X",
            "test_context": "Y",
            "train_targets": ["A", "B"],
            "test_targets": ["C"],
            "inner_val_targets": ["A"],
            "seed": 2026,
        })
        self.assertTrue(audit_split_file(path)["ok"])

    def test_development_seed_is_tagged(self):
        proto = load_protocol(REPO / "configs" / "eval_protocol.yaml")
        tagged = tag_split_role({"seed": 2026, "protocol": "x"}, protocol=proto)
        self.assertEqual(tagged["role"], "development")
        tagged_c = tag_split_role({"seed": 4242, "protocol": "x"}, protocol=proto)
        self.assertEqual(tagged_c["role"], "confirmation")


class AnchorTests(unittest.TestCase):
    def test_groups_are_disjoint_and_cover(self):
        labels = np.array(
            ["t1"] * 20 + ["t2"] * 20 + ["ntc"] * 40, dtype=object
        )
        splits = split_cells_for_anchors(
            labels, ntc_label="ntc", min_cells=8, seed=2026
        )
        self.assertEqual({s.target for s in splits}, {"t1", "t2"})
        for split in splits:
            self.assertFalse(set(split.group_a) & set(split.group_b))
            self.assertFalse(set(split.ntc_a) & set(split.ntc_b))
            self.assertGreaterEqual(split.group_a.size, 8)
            self.assertGreaterEqual(split.group_b.size, 8)

    def test_replicate_beats_chance_on_identical_halves(self):
        rng = np.random.default_rng(0)
        n_cells, n_genes = 80, 12
        labels = np.array(
            ["t1"] * 20 + ["t2"] * 20 + ["t3"] * 20 + ["ntc"] * 20, dtype=object
        )
        counts = rng.poisson(5.0, size=(n_cells, n_genes)).astype(np.float64)
        # Shared effect per target, so the two halves agree.
        for i, lab in enumerate(labels):
            if lab != "ntc":
                counts[i] += 8.0
        splits = split_cells_for_anchors(
            labels, ntc_label="ntc", min_cells=6, seed=1
        )
        result = local_anchor_deltas(counts, splits, n_boot=50, seed=1)
        self.assertTrue(result["not_a_vcc_score"])
        self.assertTrue(result["anchor_uses_query_ground_truth"])
        self.assertLess(result["replicate"]["pooled_mse_vs_null"], 0.5)


class PromotionTests(unittest.TestCase):
    def test_exploratory_without_confirmation(self):
        decision = promotion_decision(
            paired_ci95=(0.1, 0.4),
            harms={},
            has_stable_anchors=True,
            independent_confirmation=False,
            direction="higher_is_better",
        )
        self.assertEqual(decision["status"], "exploratory")

    def test_promotes_only_when_interval_clears_zero(self):
        ok = promotion_decision(
            paired_ci95=(0.02, 0.08),
            harms={},
            has_stable_anchors=True,
            independent_confirmation=True,
            direction="higher_is_better",
        )
        self.assertEqual(ok["status"], "promoted")
        no = promotion_decision(
            paired_ci95=(-0.01, 0.08),
            harms={},
            has_stable_anchors=True,
            independent_confirmation=True,
            direction="higher_is_better",
        )
        self.assertEqual(no["status"], "not_promoted")

    def test_harm_blocks_promotion(self):
        decision = promotion_decision(
            paired_ci95=(0.1, 0.4),
            harms={"pds_cosine": True},
            has_stable_anchors=True,
            independent_confirmation=True,
            direction="higher_is_better",
        )
        self.assertEqual(decision["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
