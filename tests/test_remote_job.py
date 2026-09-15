"""Resumable fetch and export: interrupt must not duplicate or restart."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from urllib.request import Request

REPO = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(REPO / "src"))

from vcc2026.remote_job import (  # noqa: E402
    ResumableFetcher,
    export_and_verify,
    simulate_interrupt,
)
from vcc2026.runtime import disk_peak_estimate  # noqa: E402
from vcc2026.source_card import Field, empty_card, validate_card  # noqa: E402


class FakeResponse:
    def __init__(self, data: bytes, status: int):
        self._data = data
        self._pos = 0
        self.status = status

    def getcode(self):
        return self.status

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            n = len(self._data) - self._pos
        chunk = self._data[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.calls: list[str | None] = []

    def __call__(self, request: Request):
        header = request.get_header("Range")
        self.calls.append(header)
        if header:
            start = int(header.split("=")[1].split("-")[0])
            return FakeResponse(self.payload[start:], 206)
        return FakeResponse(self.payload, 200)


class FetchTests(unittest.TestCase):
    def test_interrupt_then_resume_matches_full_file(self):
        payload = bytes(range(256)) * 8  # 2048 bytes
        opener = FakeOpener(payload)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "block.bin"
            fetcher = ResumableFetcher(
                "http://example.test/block.bin", dest,
                expected_bytes=len(payload),
                expected_md5=hashlib.md5(payload).hexdigest(),
                chunk_bytes=64,
                opener=opener,
            )
            first, second = simulate_interrupt(fetcher, first_bytes=200)
            self.assertFalse(first.done)
            self.assertEqual(first.received, 200)
            self.assertTrue(second.done)
            self.assertEqual(dest.read_bytes(), payload)
            self.assertGreaterEqual(len(opener.calls), 2)
            self.assertIsNone(opener.calls[0])
            self.assertTrue(str(opener.calls[1]).startswith("bytes=200-"))

    def test_byte_cap_is_enforced(self):
        payload = b"abcdefghij" * 50
        opener = FakeOpener(payload)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "cap.bin"
            fetcher = ResumableFetcher(
                "http://example.test/cap.bin", dest,
                max_bytes=40, chunk_bytes=16, opener=opener,
            )
            with self.assertRaisesRegex(RuntimeError, "byte cap"):
                fetcher.fetch()

    def test_export_refuses_overwrite_and_rehashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src.bin"
            dest = Path(tmp) / "persist" / "out.bin"
            src.write_bytes(b"abc123")
            record = export_and_verify(src, dest)
            self.assertTrue(record["reread_ok"])
            self.assertEqual(dest.read_bytes(), b"abc123")
            with self.assertRaises(FileExistsError):
                export_and_verify(src, dest)


class DiskPeakTests(unittest.TestCase):
    def test_margin_applied_when_complete(self):
        est = disk_peak_estimate(
            input_bytes=1000, decompressed_bytes=2000, derived_bytes=500,
            checkpoint_bytes=100, export_bytes=400, margin=0.25,
        )
        self.assertTrue(est["peak_complete"])
        self.assertEqual(est["peak_bytes"], int(round(4000 * 1.25)))

    def test_incomplete_when_a_component_is_unknown(self):
        est = disk_peak_estimate(
            input_bytes=1000, decompressed_bytes=None, derived_bytes=1,
        )
        self.assertFalse(est["peak_complete"])
        self.assertIsNone(est["peak_bytes"])
        self.assertIn("decompressed_bytes", est["unknown_components"])


class SourceCardTests(unittest.TestCase):
    def test_missing_stays_missing(self):
        card = empty_card("jiang_mixscale", "Jiang 2025")
        self.assertEqual(card.panel_overlap.claim, "missing")
        self.assertIsNone(card.panel_overlap.value)
        self.assertEqual(validate_card(card), [])

    def test_panel_overlap_requires_list_source(self):
        card = empty_card("x", "x")
        card.panel_overlap = Field(
            value={"n": 3}, claim="measured", source="file"
        )
        errors = validate_card(card)
        self.assertTrue(any("list_source" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
