"""verify_resume.py on made-up files with known answers: a file the earlier receipts verified with the same expected
sha256 is not read again; one they verified under another expected sha256, one they found different, one they never
reached and a cut last line are all read now; the summary counts both.

    python -m unittest test_verify_resume -v      (from this folder, with the project venv)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Resume(unittest.TestCase):
    def test_skips_only_what_was_verified(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            data, man = d / "data", d / "man"
            data.mkdir()
            man.mkdir()
            files = {f"f{i}.bin": bytes([i]) * (100 + i) for i in range(5)}
            for name, b in files.items():
                (data / name).write_bytes(b)
            entries = [{"rel": n, "bytes": len(b), "sha256": sha(b)} for n, b in files.items()]
            (man / "m.json").write_text(json.dumps({"files": entries}), encoding="utf-8")
            (man / "m.sha256").write_text(sha((man / "m.json").read_bytes()) + "  m.json\n", encoding="utf-8")
            e = {x["rel"]: x for x in entries}

            def line(rel, status, got=None, expected=None):
                x = e[rel]
                return json.dumps({"rel": rel, "round": 1, "expected_bytes": x["bytes"],
                                   "expected_sha256": expected or x["sha256"], "sha256": got or x["sha256"],
                                   "status": status})
            old = d / "old.jsonl"
            old.write_text("\n".join([line("f0.bin", "verified"), line("f1.bin", "verified"),
                                      line("f2.bin", "verified", got="0" * 64, expected="0" * 64),
                                      line("f3.bin", "sha256_differs", got="1" * 64)]) + '\n{"rel": "f4.b',
                           encoding="utf-8")
            proc = subprocess.run([sys.executable, str(HERE / "verify_resume.py"), "--manifest-dir", str(man),
                                   "--data-root", str(data), "--out", str(d / "out"), "--rounds", "1", "--wait-s", "0",
                                   "--already", str(old)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
            read = [json.loads(x)["rel"] for x in (d / "out" / "verify_receipts.jsonl").read_text().splitlines()]
            self.assertEqual(sorted(read), ["f2.bin", "f3.bin", "f4.bin"])
            s = json.loads((d / "out" / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(s["status_counts"], {"verified": 5})
            self.assertEqual(s["verified_earlier"], 2)
            self.assertEqual(s["earlier_receipts"][0]["sha256"], sha(old.read_bytes()))


if __name__ == "__main__":
    unittest.main()
