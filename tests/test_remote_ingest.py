"""Remote-ingest contract: path rules, disk gate, no silent Windows paths."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(REPO / "src"))

from vcc2026.remote_ingest import (  # noqa: E402
    JIANG_TGFB,
    colab_default_roots,
    detect_runtime,
    jiang_tgfb_gate,
    refuse_windows_paths,
)
from vcc2026.resources import GiB  # noqa: E402


class RuntimeTests(unittest.TestCase):
    def test_this_process_is_local(self):
        self.assertEqual(detect_runtime(), "local")

    def test_remote_refuses_windows_drive(self):
        with self.assertRaisesRegex(ValueError, "Windows path"):
            refuse_windows_paths(Path("C:/Users/ferra/vcc2026-data"))

    def test_colab_without_drive_is_ephemeral_vm_disk(self):
        roots = colab_default_roots(drive_mydrive_exists=False)
        self.assertEqual(roots["data"], "/content/vcc-data")
        self.assertEqual(roots["persist"], "/content/vcc-persist")

    def test_colab_with_drive_keeps_matrices_on_drive(self):
        roots = colab_default_roots(drive_mydrive_exists=True)
        self.assertEqual(roots["data"], "/content/drive/MyDrive/vcc2026/data")
        self.assertEqual(roots["persist"], "/content/drive/MyDrive/vcc2026/runs")
        self.assertTrue(roots["data"].startswith("/content/drive/"))


class JiangGateTests(unittest.TestCase):
    def test_skips_when_floor_would_break(self):
        free = int(11.3 * GiB)
        floor = int(10 * GiB)
        gate = jiang_tgfb_gate(free_bytes=free, floor_bytes=floor, fetch=True)
        self.assertFalse(gate["input_leaves_floor"])
        self.assertEqual(gate["decision"], "skip")
        self.assertEqual(gate["block"]["bytes"], JIANG_TGFB["bytes"])

    def test_fetch_only_when_asked_and_floor_holds(self):
        free = int(40 * GiB)
        floor = int(10 * GiB)
        skipped = jiang_tgfb_gate(free_bytes=free, floor_bytes=floor, fetch=False)
        self.assertEqual(skipped["decision"], "skip")
        fetched = jiang_tgfb_gate(free_bytes=free, floor_bytes=floor, fetch=True)
        self.assertTrue(fetched["input_leaves_floor"])
        self.assertEqual(fetched["decision"], "fetch")


if __name__ == "__main__":
    unittest.main()
