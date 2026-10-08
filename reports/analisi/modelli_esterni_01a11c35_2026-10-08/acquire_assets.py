"""Acquire only the reviewed immutable plan after explicit human authorization.

Run outside the repository data tree. Completed files are checked, never replaced.
Failed partials are retained; retry uses HTTP Range only after a validated 206.
This script never installs packages, launches compute, or accesses private APIs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from urllib.request import Request, urlopen


def digest(path, git_blob=False):
    h = hashlib.sha1() if git_blob else hashlib.sha256()
    if git_blob:
        h.update(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def verify(path, item):
    if path.stat().st_size != item["bytes"]:
        raise ValueError(f"size differs: {path}")
    expected = item["sha256"] or item["git_blob"]
    if digest(path, git_blob=not item["sha256"]) != expected:
        raise ValueError(f"checksum differs: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--selection", choices=["esm2", "pie"], required=True)
    parser.add_argument("--authorization", required=True, help="Human authorization reference")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    files = [f for f in plan["acquisition_plan"]
             if args.selection == "pie" or f["path"].startswith("esm2/")]
    root = args.root.resolve()
    repo = Path(__file__).resolve().parents[3]
    if root == repo or root.is_relative_to(repo):
        raise ValueError("assets must stay outside repository")
    root.mkdir(parents=True, exist_ok=True)
    lock = root/".acquisition.lock"
    with lock.open("x", encoding="utf-8") as stream:
        json.dump(dict(pid=os.getpid(), selection=args.selection, authorization=args.authorization), stream)
    log = root/f"acquisition_{time.time_ns()}.jsonl"
    try:
        pending_bytes = sum(f["bytes"] for f in files
                            if not (root/f["repo"].split("/")[-1]/f["revision"]/f["path"]).exists())
        if shutil.disk_usage(root).free < pending_bytes + 1024**3:
            raise ValueError("insufficient local/runtime free space including 1 GiB reserve")
        with log.open("x", encoding="utf-8") as receipt:
            for item in files:
                path = root/item["repo"].split("/")[-1]/item["revision"]/item["path"]
                if not path.resolve().is_relative_to(root):
                    raise ValueError("asset path escapes destination")
                started = time.monotonic()
                if path.exists():
                    verify(path, item)
                    state = "reused_verified"
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    partial = path.with_name(path.name+".partial")
                    offset = partial.stat().st_size if partial.exists() else 0
                    if offset > item["bytes"]:
                        raise ValueError("partial larger than expected; preserve and inspect")
                    if offset < item["bytes"]:
                        headers = {"User-Agent": "VCC2026-authorized-assets"}
                        if offset: headers["Range"] = f"bytes={offset}-"
                        with urlopen(Request(item["url"], headers=headers), timeout=60) as response:
                            if offset and (response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")):
                                raise ValueError("server did not honor resume range; partial preserved")
                            with partial.open("ab" if offset else "xb") as stream:
                                shutil.copyfileobj(response, stream, 4*1024*1024)
                    verify(partial, item)
                    partial.rename(path)
                    state = "downloaded_verified"
                row = dict(path=str(path), bytes=item["bytes"], sha256=digest(path),
                           state=state, seconds=time.monotonic()-started)
                receipt.write(json.dumps(row)+"\n"); receipt.flush()
                print(json.dumps(row), flush=True)
    finally:
        lock.unlink()


if __name__ == "__main__":
    main()
