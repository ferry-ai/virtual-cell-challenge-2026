"""Download the declared source files of one R-LAB job onto the runtime, and verify every byte.

The list is a JSON file of {"url", "bytes", "sha256", "dest"}: the locators and hashes come from
the download manifests written when the same files were fetched to the laptop (HIPSCI on 27/09,
Jurkat on 24/09), so a file that arrives different is refused, not used. A destination that already
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


def fetch_one(item: dict, attempts: int) -> dict:
    dest = Path(item["dest"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size == item["bytes"]:
        if sha256(dest) == item["sha256"]:
            return {**item, "status": "already present, hash verified"}
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
    got = sha256(part)
    if got != item["sha256"]:
        sys.exit(f"refusing: {dest.name} arrived with sha256 {got}, declared {item['sha256']}")
    part.rename(dest)
    return {**item, "status": "downloaded, hash verified"}


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
