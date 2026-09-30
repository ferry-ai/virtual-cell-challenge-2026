"""Download the declared source files of one R-LAB job onto the runtime, and verify every byte.

The list is a JSON file of {"url", "bytes", "sha256", "dest"}: the locators and hashes come from
the download manifests written when the same files were fetched to the laptop (HIPSCI on 27/09,
Jurkat on 24/09), so a file that arrives different is refused, not used. A file never fetched before
(H1 2025) is declared with the "crc32c" its bucket publishes instead of a sha256: it is checked
against that, and its sha256 is computed and recorded for every later use. A destination that already
holds the right bytes is kept; a partial one is resumed with an HTTP Range request; nothing is ever
written over a complete file with different bytes.

    python fetch.py --list files.json --receipt fetched.json [--attempts 5]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CHUNK = 8 << 20


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def sha256_crc32c(path: Path) -> tuple[str, str]:
    """One read: the sha256 (hex) and the crc32c in the base64 form Google Cloud Storage publishes."""
    import base64
    import google_crc32c
    h, c = hashlib.sha256(), google_crc32c.Checksum()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
            c.update(block)
    return h.hexdigest(), base64.b64encode(c.digest()).decode()


def matches(path: Path, item: dict) -> tuple[bool, str]:
    if item.get("sha256"):
        got = sha256(path)
        return got == item["sha256"], got
    got, crc = sha256_crc32c(path)
    return crc == item["crc32c"], got


def fetch_one(item: dict, attempts: int) -> dict:
    dest = Path(item["dest"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size == item["bytes"]:
        ok, got = matches(dest, item)
        if ok:
            return {**item, "sha256": got, "status": "already present, hash verified"}
        sys.exit(f"refusing: {dest} is complete but its hash differs from the declared one")
    part = dest.with_name(dest.name + ".part")
    for attempt in range(1, attempts + 1):
        have = part.stat().st_size if part.exists() else 0
        request = urllib.request.Request(item["url"], headers={"User-Agent": "vcc2026-rlab/1"})
        if have:
            request.add_header("Range", f"bytes={have}-")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                if have and response.status != 206:
                    have = 0  # the server ignored the range: start again
                with open(part, "ab" if have else "wb") as fh:
                    while True:
                        block = response.read(CHUNK)
                        if not block:
                            break
                        fh.write(block)
        except OSError as exc:
            print(f"{dest.name}: attempt {attempt}/{attempts} failed at {have} bytes: {exc}", flush=True)
            time.sleep(min(60, 10 * attempt))
            continue
        if part.stat().st_size == item["bytes"]:
            break
        print(f"{dest.name}: attempt {attempt} ended at {part.stat().st_size} of {item['bytes']} bytes", flush=True)
    else:
        sys.exit(f"refusing: {dest.name} not complete after {attempts} attempts")
    ok, got = matches(part, item)
    if not ok:
        sys.exit(f"refusing: {dest.name} arrived with a hash different from the declared one (sha256 {got})")
    part.rename(dest)
    return {**item, "sha256": got, "status": "downloaded, hash verified"}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--list", required=True, type=Path)
    p.add_argument("--receipt", required=True, type=Path)
    p.add_argument("--attempts", type=int, default=5)
    a = p.parse_args()
    if a.receipt.exists():
        sys.exit(f"refusing: {a.receipt} exists")
    items = json.loads(a.list.read_text(encoding="utf-8"))
    started = datetime.now(timezone.utc).isoformat()
    done = []
    for item in items:
        t0 = time.time()
        done.append({**fetch_one(item, a.attempts), "seconds": round(time.time() - t0, 1)})
        print(done[-1]["status"], Path(item["dest"]).name, item["bytes"], flush=True)
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    with open(a.receipt, "x", encoding="utf-8") as fh:
        json.dump({"started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
                   "list_sha256": sha256(a.list), "files": done}, fh, indent=1)


if __name__ == "__main__":
    main()
