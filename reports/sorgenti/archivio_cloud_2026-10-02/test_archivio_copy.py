"""Tests of archivio.py copy: hard links sent once, large files deferred and recorded when they never fit,
receipts in append-only order, nothing overwritten. Free space is replaced by a fixed value."""
import argparse
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import archivio


class TestCopy(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="arch_test_"))
        self.root, self.dest = self.tmp / "root", self.tmp / "dest"
        (self.root / "a").mkdir(parents=True)
        self.dest.mkdir()
        (self.root / "a" / "small1.bin").write_bytes(os.urandom(1000))
        (self.root / "a" / "big.bin").write_bytes(os.urandom(3 << 20))
        (self.root / "a" / "small2.bin").write_bytes(os.urandom(2000))
        os.link(self.root / "a" / "small1.bin", self.root / "a" / "small1_link.bin")
        archivio.cmd_inventory(argparse.Namespace(root=str(self.root), out=str(self.tmp / "inv.tsv")))
        (self.tmp / "drive.tsv").write_text("", encoding="utf-8")
        archivio.cmd_plan(argparse.Namespace(inventory=str(self.tmp / "inv.tsv"), drive_listing=str(self.tmp / "drive.tsv"),
                                             out=str(self.tmp / "plan.json")))
        self._free = archivio.free_bytes

    def tearDown(self):
        archivio.free_bytes = self._free
        shutil.rmtree(self.tmp, ignore_errors=True)

    def copy(self, free: int, **kw):
        archivio.free_bytes = lambda _path: free
        args = dict(root=str(self.root), dest=str(self.dest), plan=str(self.tmp / "plan.json"), hashes=None,
                    receipts=str(self.tmp / "rec.jsonl"), only=None, exclude=None, stop_file=None, cache_disk=str(self.tmp),
                    min_free_gb=0.0, max_wait_s=0, defer_over_gb=0.001, final_wait_s=60)
        args.update(kw)
        with mock.patch.object(archivio.time, "sleep", lambda _s: None):  # no real waiting in tests
            archivio.cmd_copy(argparse.Namespace(**args))
        return [json.loads(l) for l in (self.tmp / "rec.jsonl").read_text(encoding="utf-8").splitlines()]

    def test_big_file_deferred_then_recorded_when_it_never_fits(self):
        recs = self.copy(free=1 << 20)  # 1 MiB free: the small files fit, the 3 MiB file never does
        st = {r["rel"]: r["status"] for r in recs}
        self.assertEqual(st["a/big.bin"], "deferred_no_space")
        self.assertEqual(st["a/small1.bin"], "copied")
        self.assertEqual(st["a/small2.bin"], "copied")
        self.assertEqual(st["a/small1_link.bin"], "skipped_hardlink")
        self.assertFalse((self.dest / "a" / "big.bin").exists())
        self.assertEqual([r["rel"] for r in recs][-1], "a/big.bin")  # recorded after the others

    def test_everything_sent_when_space_allows_and_resume_skips_done(self):
        recs = self.copy(free=1 << 30)
        self.assertEqual(sorted(r["status"] for r in recs), ["copied", "copied", "copied", "skipped_hardlink"])
        for name in ("small1.bin", "big.bin", "small2.bin"):
            self.assertEqual((self.dest / "a" / name).read_bytes(), (self.root / "a" / name).read_bytes())
        again = self.copy(free=1 << 30)
        self.assertEqual(len(again), len(recs))  # a second run adds nothing

    def test_existing_destination_is_never_overwritten(self):
        (self.dest / "a").mkdir()
        (self.dest / "a" / "small2.bin").write_bytes(b"other")
        recs = self.copy(free=1 << 30)
        st = {r["rel"]: r["status"] for r in recs}
        self.assertEqual(st["a/small2.bin"], "refused_exists_different_size")
        self.assertEqual((self.dest / "a" / "small2.bin").read_bytes(), b"other")


if __name__ == "__main__":
    unittest.main()
