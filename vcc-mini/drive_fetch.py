"""Fetch catalog files into Google Drive from a Colab VM, one file at a time, verified.

For each file of the selected tiers:
  1. skip it if <dest>/raw/<tier>/<file>.verified.json exists and the Drive copy has the right size;
  2. download it to the VM's local disk (resumable, retried), never straight into Drive;
  3. check size and checksum (md5 or sha256 from the host; size only for S3, where the
     sha256 is computed and recorded instead);
  4. copy it into Drive under a temporary name, rename, re-check the size on Drive;
  5. write the .verified.json sidecar, append a line to <dest>/logs/, delete the VM copy.

A failed checksum stops that file (kept on the VM as .bad) and the run continues with the next.
Nothing is ever overwritten on Drive: an existing file with a wrong size is renamed .stale.

    python drive_fetch.py --catalog catalog.json --dest /content/drive/MyDrive/vcc-data --tiers mini
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

DAILY_UPLOAD_GUARD = 700e9   # Google Drive accepts ~750 GB of uploads per user per day


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def digest(path: Path, algo: str) -> str:
    h = hashlib.md5() if algo == "md5" else hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 24), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, part: Path, size: int, tries: int = 5) -> None:
    for attempt in range(1, tries + 1):
        start = part.stat().st_size if part.exists() else 0
        if start == size:
            return
        req = urllib.request.Request(url, headers={"User-Agent": "vcc-drive-fetch/0.1"})
        if start:
            req.add_header("Range", f"bytes={start}-")
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                if start and r.status != 206:
                    start = 0
                done, t0, last = start, time.time(), 0.0
                with part.open("ab" if start else "wb") as f:
                    while True:
                        block = r.read(1 << 23)
                        if not block:
                            break
                        f.write(block)
                        done += len(block)
                        if time.time() - last > 10:
                            rate = (done - start) / max(time.time() - t0, 1e-6) / 1e6
                            print(f"    {done / 1e9:7.2f} / {size / 1e9:.2f} GB  {rate:6.1f} MB/s", flush=True)
                            last = time.time()
            if part.stat().st_size == size:
                return
        except Exception as exc:  # network errors: retry from where the file stopped
            print(f"    attempt {attempt} failed: {exc!r}", flush=True)
        time.sleep(min(60, 5 * attempt))
    raise RuntimeError(f"download incomplete after {tries} attempts: {part.stat().st_size if part.exists() else 0} of {size}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--dest", required=True, help="Drive folder, e.g. /content/drive/MyDrive/vcc-data")
    ap.add_argument("--stage", default="/content/stage", help="local VM disk")
    ap.add_argument("--tiers", nargs="+", required=True)
    ap.add_argument("--limit", type=int, default=0, help="at most this many files (0 = all)")
    args = ap.parse_args()
    cat = json.loads(Path(args.catalog).read_text())
    unknown = set(args.tiers) - set(cat["tiers"])
    if unknown:
        print("unknown tiers:", unknown, "available:", list(cat["tiers"]))
        return 2
    todo = [e for e in cat["files"] if e["tier"] in args.tiers]
    if args.limit:
        todo = todo[: args.limit]
    dest, stage = Path(args.dest), Path(args.stage)
    stage.mkdir(parents=True, exist_ok=True)
    (dest / "logs").mkdir(parents=True, exist_ok=True)
    log = dest / "logs" / f"fetch_{now().replace(':', '')}.jsonl"
    total = sum(e["bytes"] for e in todo)
    print(f"{len(todo)} files, {total / 1e9:.2f} GB, tiers {args.tiers}")
    uploaded, failures = 0, 0
    for i, e in enumerate(todo, 1):
        folder = dest / "raw" / e["tier"]
        folder.mkdir(parents=True, exist_ok=True)
        target, sidecar = folder / e["file"], folder / (e["file"] + ".verified.json")
        print(f"[{i}/{len(todo)}] {e['tier']}/{e['file']}  {e['bytes'] / 1e9:.2f} GB", flush=True)
        if sidecar.exists() and target.exists() and target.stat().st_size == e["bytes"]:
            print("    already on Drive, verified: skip")
            continue
        if target.exists():
            target.rename(target.with_name(target.name + f".stale_{now().replace(':', '')}"))
        if uploaded + e["bytes"] > DAILY_UPLOAD_GUARD:
            print("    stop: this file would pass the daily Drive upload guard; rerun tomorrow")
            break
        free = shutil.disk_usage(stage).free
        if free < e["bytes"] + 2e9:
            print(f"    stop: {free / 1e9:.1f} GB free on the VM, file needs {e['bytes'] / 1e9:.1f} GB")
            break
        part = stage / (e["file"] + ".part")
        rec = dict(utc=now(), tier=e["tier"], file=e["file"], url=e["url"], bytes=e["bytes"], algo=e["algo"])
        try:
            download(e["url"], part, e["bytes"])
            if e["algo"] in ("md5", "sha256"):
                got = digest(part, e["algo"])
                rec["checksum"] = got
                if got != e["checksum"]:
                    part.rename(part.with_name(f"{e['file']}.bad_{now().replace(':', '')}"))
                    raise RuntimeError(f"{e['algo']} mismatch: got {got}, catalog {e['checksum']}")
            else:
                rec["sha256_computed"] = digest(part, "sha256")
            tmp = target.with_name(target.name + ".copying")
            shutil.copyfile(part, tmp)
            os.replace(tmp, target)
            if target.stat().st_size != e["bytes"]:
                raise RuntimeError(f"size on Drive {target.stat().st_size} != {e['bytes']}")
            rec.update(status="verified", source=e["source"], license=e["license"])
            sidecar.write_text(json.dumps(rec, indent=1))
            part.unlink()
            uploaded += e["bytes"]
        except Exception as exc:
            rec.update(status="failed", error=repr(exc))
            failures += 1
            print("    FAILED:", exc, flush=True)
        with log.open("a") as f:
            f.write(json.dumps(rec) + "\n")
    print(f"done: {uploaded / 1e9:.2f} GB uploaded this run, {failures} failures, log {log}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
