"""Publish downloaded raw files to their frozen home, hash the copies, and write the manifest last.

Reads the receipt of fetch.py (every file with url, bytes, sha256 and, for a bucket, crc32c), copies
each file under --out keeping the path relative to --from, re-hashes the copy, and only then writes
`manifest.json` with a role per file taken from --roles. Raw files are never opened as data here: a
reserve stays unread. Refuses an existing --out.

    python publish.py --receipt fetched.json --from /content/work/dl --out <Drive dir> \
        --roles '{"test/": "RISERVA"}' --note "..."
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import sha256  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--receipt", required=True, type=Path)
    p.add_argument("--from", dest="src", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--roles", default="{}", help="JSON: relative path prefix -> role")
    p.add_argument("--note", default="")
    p.add_argument("--min-free-bytes", type=int, default=0)
    a = p.parse_args()
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    fetched = json.loads(a.receipt.read_text(encoding="utf-8"))["files"]
    need = sum(f["bytes"] for f in fetched) + a.min_free_bytes
    probe = a.out.parent
    while not probe.exists():
        probe = probe.parent
    free = shutil.disk_usage(probe).free
    if free < need:
        sys.exit(f"refusing: {free} bytes free where the files go, {need} needed")
    roles = json.loads(a.roles)
    a.out.mkdir(parents=True)
    files = []
    for f in fetched:
        rel = Path(f["dest"]).relative_to(a.src)
        dest, tmp = a.out / rel, a.out / (str(rel) + ".partial")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f["dest"], tmp)
        os.replace(tmp, dest)
        copy = sha256(dest)
        if copy != f["sha256"]:
            sys.exit(f"{rel}: the copy hashes {copy}, the download {f['sha256']}")
        role = next((r for prefix, r in roles.items() if rel.as_posix().startswith(prefix)), "raw")
        files.append({"path": rel.as_posix(), "bytes": f["bytes"], "sha256": copy, "crc32c": f.get("crc32c"),
                      "url": f["url"], "generation": f.get("generation"), "role": role})
        print(f"published {rel} ({f['bytes']} bytes), role {role}", flush=True)
    with open(a.out / "manifest.json", "x", encoding="utf-8") as fh:
        json.dump({"published_utc": datetime.now(timezone.utc).isoformat(), "note": a.note,
                   "fetch_receipt_sha256": sha256(a.receipt), "files": files}, fh, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
