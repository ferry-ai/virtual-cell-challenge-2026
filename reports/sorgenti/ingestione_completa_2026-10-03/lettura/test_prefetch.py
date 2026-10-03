"""PrefetchFile against a made-up host: the same bytes as the one-block-at-a-time reader, each block asked once, several
at a time, with the failures and the file-version check of the reader it extends. No network.

    python -m unittest test_prefetch -v           (from this folder, with the project venv)
"""
from __future__ import annotations

import io
import sys
import tempfile
import threading
import time
import types
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prefetch  # noqa: E402
from prefetch import PrefetchFile, RangeFile  # noqa: E402


class Host:
    """A file served by ranges: counts the requests, can be slow, can expire its signed URL, fail or change."""

    def __init__(self, body: bytes, delay: float = 0.0):
        self.body, self.delay, self.lock = body, delay, threading.Lock()
        self.calls, self.resolves, self.live, self.peak = [], 0, 0, 0
        self.etag, self.expire_after, self.served_since_resolve, self.fail_at = '"v1"', None, 0, None

    def resolve(self, reader):
        with self.lock:
            self.resolves += 1
            self.served_since_resolve = 0
        reader.final_url, reader.size = "signed", len(self.body)
        reader.etag = reader.etag or self.etag

    def fetch(self, reader, url, lo, hi):
        with self.lock:
            if self.expire_after is not None and self.served_since_resolve >= self.expire_after:
                raise urllib.error.HTTPError(url, 403, "expired", None, None)
            self.served_since_resolve += 1
            self.calls.append((lo, hi))
            self.live += 1
            self.peak = max(self.peak, self.live)
        time.sleep(self.delay)
        with self.lock:
            self.live -= 1
        if self.fail_at is not None and lo <= self.fail_at <= hi:
            raise OSError("host down")
        return self.body[lo:hi + 1], self.etag

    def patches(self):
        host = self
        return (mock.patch.object(RangeFile, "_resolve", lambda r: host.resolve(r)),
                mock.patch.object(RangeFile, "_fetch", lambda r, url, lo, hi: host.fetch(r, url, lo, hi)),
                mock.patch("time.sleep", side_effect=lambda s, real=time.sleep: real(min(s, 0.01))))


class Reads(unittest.TestCase):
    def setUp(self):
        self.body = np.random.default_rng(5).integers(0, 256, 1_000_003, dtype=np.uint8).tobytes()

    def open(self, host, **kw):
        for p in host.patches():
            p.start()
            self.addCleanup(p.stop)
        return PrefetchFile("https://host/file", **{"block": 4096, "max_bytes": 1 << 20, "ahead": 6, "threads": 6, **kw})

    def test_sequential_and_random_reads_return_the_file(self):
        host = Host(self.body)
        f = io.BufferedReader(self.open(host), buffer_size=4096)
        self.assertEqual(f.read(), self.body)
        self.assertEqual(len(host.calls), len(set(host.calls)))                 # no block asked twice in the scan
        self.assertEqual(len(host.calls), -(-len(self.body) // 4096))
        rng = np.random.default_rng(1)
        for a in rng.integers(0, len(self.body) - 9000, 60):
            f.seek(int(a))
            self.assertEqual(f.read(9000), self.body[int(a):int(a) + 9000])
        f.seek(len(self.body) - 10)
        self.assertEqual(f.read(100), self.body[-10:])

    def test_two_interleaved_scans_are_read_several_blocks_at_a_time(self):
        host = Host(self.body, delay=0.02)
        raw = self.open(host)
        half, got_a, got_b, t0 = len(self.body) // 2, bytearray(), bytearray(), time.time()
        for k in range(0, half, 8192):
            raw.seek(k)
            got_a += raw.read(8192)[:max(0, min(8192, half - k))]
            raw.seek(half + k)
            got_b += raw.read(8192)
        seconds = time.time() - t0
        self.assertEqual(bytes(got_a), self.body[:half])
        self.assertEqual(bytes(got_b)[:len(self.body) - half], self.body[half:half + len(got_b)])
        self.assertGreater(host.peak, 2)
        self.assertLess(seconds, len(host.calls) * 0.02 / 2)                    # at least twice the serial speed

    def test_an_expired_url_is_resolved_once_for_all_threads(self):
        host = Host(self.body[:200_000])
        host.expire_after = 10
        f = io.BufferedReader(self.open(host), buffer_size=4096)
        self.assertEqual(f.read(), self.body[:200_000])
        self.assertGreater(host.resolves, 2)
        self.assertLessEqual(host.resolves, 1 + -(-len(host.calls) // 10) + 6)   # not one renewal per thread and block

    def test_a_failed_block_and_a_changed_file_stop_the_read(self):
        host = Host(self.body)
        host.fail_at = 300_000
        f = io.BufferedReader(self.open(host), buffer_size=4096)
        with self.assertRaises(OSError):
            f.read()
        other = Host(self.body)
        raw = self.open(other)
        raw.read(4096)
        other.etag = '"v2"'
        with self.assertRaises(OSError):
            raw.seek(500_000)
            raw.read(4096)

    def test_h5py_reads_through_it_and_install_keeps_local_paths(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "m.h5"
            values = np.arange(300_000, dtype=np.int64)
            with h5py.File(path, "w") as f:
                f.create_dataset("indices", data=values, chunks=(4096,))
            host = Host(path.read_bytes())
            module = types.SimpleNamespace()
            for p in host.patches():
                p.start()
                self.addCleanup(p.stop)
            prefetch.install(module, block=8192, max_bytes=1 << 20, ahead=4, threads=4)
            with module._h5_open("https://host/m.h5") as f:
                self.assertTrue(np.array_equal(f["indices"][1000:250_000], values[1000:250_000]))
            with module._h5_open(path) as f:
                self.assertEqual(int(f["indices"][7]), 7)


if __name__ == "__main__":
    unittest.main()
