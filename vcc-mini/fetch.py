"""Download the files listed in sources.json into raw/, resumable, with md5 check.

Standard library only. A file whose md5 does not match the published one is kept
as <name>.bad and the script exits non-zero: nothing downstream reads it.
"""
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def md5sum(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def fetch(entry: dict, raw: Path) -> dict:
    dest = raw / entry["file"]
    part = dest.with_suffix(dest.suffix + ".part")
    if dest.exists() and dest.stat().st_size == entry["bytes"]:
        got = md5sum(dest)
        return {"key": entry["key"], "status": "present", "md5_ok": got == entry["md5"], "md5": got}
    start = part.stat().st_size if part.exists() else 0
    req = urllib.request.Request(entry["url"], headers={"User-Agent": "vcc-mini/0.1"})
    if start:
        req.add_header("Range", f"bytes={start}-")
    with urllib.request.urlopen(req, timeout=120) as r:
        if start and r.status != 206:  # server ignored the range: restart cleanly
            start = 0
        mode = "ab" if start else "wb"
        done = start
        with part.open(mode) as f:
            while True:
                block = r.read(1 << 22)
                if not block:
                    break
                f.write(block)
                done += len(block)
                print(f"\r{entry['file']}: {done / 1e6:,.0f} / {entry['bytes'] / 1e6:,.0f} MB", end="", flush=True)
    print()
    if part.stat().st_size != entry["bytes"]:
        return {"key": entry["key"], "status": "short", "bytes": part.stat().st_size}
    got = md5sum(part)
    if got != entry["md5"]:
        part.rename(dest.with_suffix(dest.suffix + ".bad"))
        return {"key": entry["key"], "status": "md5_mismatch", "md5": got}
    part.rename(dest)
    return {"key": entry["key"], "status": "downloaded", "md5_ok": True, "md5": got}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="keys from sources.json (default: all)")
    args = ap.parse_args()
    raw = ROOT / "raw"
    raw.mkdir(exist_ok=True)
    entries = json.loads((ROOT / "sources.json").read_text())
    if args.only:
        entries = [e for e in entries if e["key"] in set(args.only)]
    results = [fetch(e, raw) for e in entries]
    (raw / "fetch_log.json").write_text(json.dumps(results, indent=1))
    for r in results:
        print(r)
    return 0 if all(r.get("md5_ok") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
