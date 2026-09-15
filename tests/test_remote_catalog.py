"""Catalog contracts: measured bytes, no silent 61.3 GB, one-block disk gate."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(REPO / "src"))

from vcc2026.external import REGISTRY  # noqa: E402
from vcc2026.remote_catalog import (  # noqa: E402
    LARGE_FETCH_BYTES,
    load_catalog,
    persist_kind,
    plan_block,
    recommend_fetch_ids,
)
from vcc2026.resources import GiB  # noqa: E402


class CatalogLoadTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()

    def test_k562_gw_bytes_match_figshare_registry_not_the_profile_figure(self):
        block = self.catalog.by_id("k562_gwps_raw_singlecell")
        fig = REGISTRY["k562_gwps_raw_singlecell"]
        self.assertEqual(block.bytes, fig.size)
        self.assertEqual(block.md5, fig.md5)
        self.assertEqual(block.url, fig.url)
        self.assertEqual(block.bytes, 65_830_941_948)
        self.assertNotEqual(block.bytes, block.advertised_bytes)
        self.assertIn("61.3", block.advertised_note)

    def test_normalized_twin_is_forbidden(self):
        block = self.catalog.by_id("rpe1_normalized_singlecell")
        self.assertTrue(block.do_not_fetch)
        self.assertFalse(block.fetchable())

    def test_cd4_is_a_stub(self):
        block = self.catalog.by_id("cd4_marson")
        self.assertTrue(block.stub)
        self.assertFalse(block.fetchable())

    def test_jiang_blocks_are_separate_and_rds(self):
        ids = [b.id for b in self.catalog.blocks if b.id.startswith("jiang_")]
        self.assertIn("jiang_tgfb", ids)
        self.assertEqual(self.catalog.by_id("jiang_tgfb").format, "seurat_rds")
        self.assertEqual(self.catalog.by_id("jiang_tgfb").derive, "rds_blocked")

    def test_hepg2_md5_is_the_acquired_mirror(self):
        block = self.catalog.by_id("nadig_hepg2")
        self.assertEqual(block.md5, "af2be47f7477cf32fa6e4bec1c6a4868")
        self.assertEqual(block.bytes, 850_590_740)


class GateTests(unittest.TestCase):
    def test_sixty_five_gib_refused_on_the_laptop_floor(self):
        catalog = load_catalog()
        block = catalog.by_id("k562_gwps_raw_singlecell")
        plan = plan_block(
            block,
            free_bytes=int(11.3 * GiB),
            ram_available_bytes=int(0.7 * GiB),
            floor_bytes=int(10 * GiB),
            fetch=True,
            already_complete=False,
        )
        self.assertEqual(plan["decision"], "skip_disk")
        self.assertFalse(plan["input_leaves_floor"])

    def test_colab_87_gib_can_fetch_input_but_plan_only_without_fetch_flag(self):
        catalog = load_catalog()
        block = catalog.by_id("k562_gwps_raw_singlecell")
        planned = plan_block(
            block,
            free_bytes=int(87.25 * GiB),
            ram_available_bytes=int(11 * GiB),
            floor_bytes=int(2 * GiB),
            fetch=False,
            already_complete=False,
        )
        self.assertEqual(planned["decision"], "plan_only")
        self.assertTrue(planned["input_leaves_floor"])
        fetch = plan_block(
            block,
            free_bytes=int(87.25 * GiB),
            ram_available_bytes=int(11 * GiB),
            floor_bytes=int(2 * GiB),
            fetch=True,
            already_complete=False,
        )
        self.assertEqual(fetch["decision"], "fetch")

    def test_complete_hepg2_is_not_fetched_again(self):
        catalog = load_catalog()
        block = catalog.by_id("nadig_hepg2")
        plan = plan_block(
            block,
            free_bytes=int(87 * GiB),
            ram_available_bytes=int(11 * GiB),
            floor_bytes=int(2 * GiB),
            fetch=True,
            already_complete=True,
        )
        self.assertEqual(plan["decision"], "skip_complete")

    def test_two_large_files_do_not_both_fit_after_the_first(self):
        catalog = load_catalog()
        gw = catalog.by_id("k562_gwps_raw_singlecell")
        rpe1 = catalog.by_id("rpe1_raw_singlecell")
        # 68 GiB holds GW (65.8) plus the 2 GiB floor, not also RPE1 SC (8.1).
        free = int(68 * GiB)
        floor = int(2 * GiB)
        first = plan_block(
            gw, free_bytes=free, ram_available_bytes=int(11 * GiB),
            floor_bytes=floor, fetch=True, already_complete=False,
        )
        self.assertEqual(first["decision"], "fetch")
        remaining = free - gw.bytes
        second = plan_block(
            rpe1, free_bytes=remaining, ram_available_bytes=int(11 * GiB),
            floor_bytes=floor, fetch=True, already_complete=False,
        )
        self.assertEqual(second["decision"], "skip_disk")


class RecommendTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()

    def test_colab_drive_missing_hepg2_then_k562_gw(self):
        rec = recommend_fetch_ids(
            self.catalog,
            free_bytes=int(87.25 * GiB),
            ram_available_bytes=int(11 * GiB),
            floor_bytes=int(2 * GiB),
            persist_survives_session=True,
            complete_ids=set(),
        )
        self.assertEqual(
            rec["ids"],
            ["nadig_hepg2", "k562_gwps_raw_singlecell"],
        )
        self.assertNotIn("rpe1_raw_singlecell", rec["ids"])

    def test_colab_drive_complete_hepg2_recommends_only_k562_gw(self):
        rec = recommend_fetch_ids(
            self.catalog,
            free_bytes=int(87.25 * GiB),
            ram_available_bytes=int(11 * GiB),
            floor_bytes=int(2 * GiB),
            persist_survives_session=True,
            complete_ids={"nadig_hepg2"},
        )
        self.assertEqual(rec["ids"], ["k562_gwps_raw_singlecell"])
        self.assertNotIn("rpe1_raw_singlecell", rec["ids"])

    def test_ephemeral_colab_does_not_start_sixty_five_gib(self):
        rec = recommend_fetch_ids(
            self.catalog,
            free_bytes=int(87.25 * GiB),
            ram_available_bytes=int(11 * GiB),
            floor_bytes=int(2 * GiB),
            persist_survives_session=False,
            complete_ids=set(),
        )
        self.assertEqual(rec["ids"], ["nadig_hepg2"])
        self.assertNotIn("k562_gwps_raw_singlecell", rec["ids"])
        self.assertTrue(
            any("ephemeral" in s["reason"] for s in rec["skipped"]
                if s["id"] == "k562_gwps_raw_singlecell")
        )

    def test_ephemeral_with_hepg2_present_recommends_nothing(self):
        rec = recommend_fetch_ids(
            self.catalog,
            free_bytes=int(87.25 * GiB),
            ram_available_bytes=int(11 * GiB),
            floor_bytes=int(2 * GiB),
            persist_survives_session=False,
            complete_ids={"nadig_hepg2"},
        )
        self.assertEqual(rec["ids"], [])
        self.assertNotIn("nadig_jurkat_mirror", rec["ids"])

    def test_laptop_floor_never_recommends_k562_gw(self):
        rec = recommend_fetch_ids(
            self.catalog,
            free_bytes=int(11.3 * GiB),
            ram_available_bytes=int(0.7 * GiB),
            floor_bytes=int(10 * GiB),
            persist_survives_session=True,
            complete_ids=set(),
        )
        self.assertNotIn("k562_gwps_raw_singlecell", rec["ids"])
        self.assertLess(sum(
            self.catalog.by_id(i).bytes or 0 for i in rec["ids"]
        ), 2 * GiB)
        gw = self.catalog.by_id("k562_gwps_raw_singlecell")
        self.assertGreater(gw.bytes, LARGE_FETCH_BYTES)

    def test_rds_stays_out_of_auto_fetch(self):
        rec = recommend_fetch_ids(
            self.catalog,
            free_bytes=int(87.25 * GiB),
            ram_available_bytes=int(11 * GiB),
            floor_bytes=int(2 * GiB),
            persist_survives_session=True,
            complete_ids={"nadig_hepg2", "k562_gwps_raw_singlecell",
                          "rpe1_raw_singlecell", "nadig_jurkat_mirror"},
        )
        self.assertEqual(rec["ids"], [])
        self.assertTrue(any(s["id"] == "jiang_tgfb" for s in rec["skipped"]))


class PersistTests(unittest.TestCase):
    def test_content_vcc_persist_is_ephemeral(self):
        kind = persist_kind(Path("/content/vcc-persist/remote_ingest_x"))
        self.assertEqual(kind["kind"], "colab_vm")
        self.assertFalse(kind["survives_session"])

    def test_drive_is_labelled_durable(self):
        kind = persist_kind(Path("/content/drive/MyDrive/vcc2026/out"))
        self.assertEqual(kind["kind"], "colab_drive")
        self.assertTrue(kind["survives_session"])


class CheckpointTests(unittest.TestCase):
    def test_complete_checkpoint_is_not_overwritten(self):
        from vcc2026.remote_catalog import write_checkpoint

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = write_checkpoint(root, {
                "block_id": "nadig_hepg2", "status": "complete", "md5": "abc",
            })
            again = write_checkpoint(root, {
                "block_id": "nadig_hepg2", "status": "complete", "md5": "def",
            })
            self.assertEqual(first, again)
            payload = (root / "checkpoints" / "nadig_hepg2.json").read_text(encoding="utf-8")
            self.assertIn("abc", payload)
            self.assertNotIn("def", payload)


if __name__ == "__main__":
    unittest.main()
