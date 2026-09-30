"""rlab_job.reusable searches several earlier attempts in order and reuses a shard only when its receipt matches (1/10,
job 109 after 106: the shards of one unit are spread over two attempts).

    python -m unittest test_reuse -v          (from this folder)
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rlab_job  # noqa: E402


def attempt(root: Path, unit: str, name: str, payload: bytes, receipt_sha=None):
    (root / unit / "receipts").mkdir(parents=True, exist_ok=True)
    shard = root / unit / f"{name}.h5ad"
    shard.write_bytes(payload)
    digest = receipt_sha or rlab_job.sha256(shard)
    (root / unit / "receipts" / f"{name}.json").write_text(json.dumps({"bytes": len(payload), "sha256": digest}))


class Reuse(unittest.TestCase):
    def test_first_matching_attempt_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            r4, r5 = Path(tmp) / "r4", Path(tmp) / "r5"
            attempt(r4, "u", "shard_00000", b"from r4")
            attempt(r5, "u", "shard_00004", b"from r5")
            attempt(r4, "u", "shard_00004", b"old r4")
            self.assertTrue(rlab_job.reusable([r5, r4], "u", "shard_00000")["reused_from"].startswith(str(r4)))
            self.assertTrue(rlab_job.reusable([r5, r4], "u", "shard_00004")["reused_from"].startswith(str(r5)))
            self.assertIsNone(rlab_job.reusable([r5, r4], "u", "shard_00009"))
            self.assertIsNone(rlab_job.reusable(None, "u", "shard_00000"))

    def test_a_receipt_that_does_not_match_is_not_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp) / "r"
            attempt(r, "u", "shard_00000", b"bytes", receipt_sha="0" * 64)
            self.assertIsNone(rlab_job.reusable([r], "u", "shard_00000"))


if __name__ == "__main__":
    unittest.main()
