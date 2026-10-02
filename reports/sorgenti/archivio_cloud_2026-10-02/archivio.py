"""Inventory, hash and copy the data root to the Drive mirror, with receipts (cloud archive of 2 October 2026).

Subcommands, each writing new files and refusing to overwrite an output:

  inventory  walk the data root (software environments and caches excluded) and write one row per file:
             relative path, bytes, mtime, NTFS file id and link count, so hard links are counted once.
  hash       sha256 and md5 of every inventoried file, appended to a TSV; resumable (a row whose
             bytes and mtime are unchanged is not hashed again). Runs at low priority.
  plan       compare the inventory with a metadata listing of the Drive mirror: per file, absent,
             same size, or different size on Drive (a conflict is never overwritten).
  copy       copy the planned files to the Drive mirror one at a time, hashing the bytes while they
             are copied; refuses to overwrite; waits while free space on the cache disk is below the
             file size plus a margin, because Drive for desktop keeps a file in its local cache until
             it is uploaded. A receipt line per file. A copy on the mount is NOT proof of upload:
             the remote check reads the files from an independent runtime (Colab), see verify_drive.py.

The mirror keeps relative paths: <data root>/<rel> -> <Drive>/vcc2026/data/<rel>, so a manifest written
against the data root resolves on Colab with VCC2026_DATA_ROOT=/content/drive/MyDrive/vcc2026/data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Not data: software environments, caches and retired agent infrastructure (listed apart, never uploaded).
EXCLUDE_TOP = {".venv", "orch-venv", "orchestrator", "ciclo", "archivio_repo"}
EXCLUDE_ANY = {"__pycache__", ".ipynb_checkpoints", ".cache", ".pytest_cache"}
CHUNK = 8 << 20


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def refuse_existing(path: Path) -> None:
    if path.exists():
        sys.exit(f"refusing: {path} exists")


def cmd_inventory(a: argparse.Namespace) -> None:
    out = Path(a.out)
    refuse_existing(out)
    root = Path(a.root)
    t0 = time.time()
    n = 0
    skipped: dict[str, int] = {}
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["rel", "bytes", "mtime_ns", "file_id", "nlink"])
        stack = [root]
        while stack:
            d = stack.pop()
            try:
                entries = list(os.scandir(d))
            except OSError as e:
                w.writerow([f"ERROR:{d}", -1, 0, str(e), 0])
                continue
            for e in entries:
                rel = os.path.relpath(e.path, root).replace("\\", "/")
                top = rel.split("/", 1)[0]
                if top in EXCLUDE_TOP or e.name in EXCLUDE_ANY:
                    skipped[top if top in EXCLUDE_TOP else e.name] = skipped.get(top if top in EXCLUDE_TOP else e.name, 0) + 1
                    continue
                if e.is_dir(follow_symlinks=False):
                    stack.append(Path(e.path))
                elif e.is_file(follow_symlinks=False):
                    st = os.stat(e.path, follow_symlinks=False)
                    w.writerow([rel, st.st_size, st.st_mtime_ns, f"{st.st_dev}:{st.st_ino}", st.st_nlink])
                    n += 1
                    if n % 5000 == 0:
                        print(f"{now()} {n} files", flush=True)
                else:
                    w.writerow([f"SPECIAL:{rel}", -1, 0, "", 0])
    print(json.dumps({"files": n, "seconds": round(time.time() - t0, 1), "excluded_entries": skipped, "out": str(out)}))


def read_tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def lower_priority() -> None:
    if os.name == "nt":
        try:
            import ctypes
            BELOW_NORMAL = 0x00004000
            PROCESS_MODE_BACKGROUND_BEGIN = 0x00100000  # also lowers I/O priority
            h = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.kernel32.SetPriorityClass(h, BELOW_NORMAL)
            ctypes.windll.kernel32.SetPriorityClass(h, PROCESS_MODE_BACKGROUND_BEGIN)
        except Exception as e:  # noqa: BLE001 - priority is a courtesy, not a requirement
            print(f"priority not lowered: {e}", flush=True)


def keep_awake() -> None:
    """Ask Windows not to sleep while this process runs (released automatically when it exits)."""
    if os.name == "nt":
        try:
            import ctypes
            ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        except Exception as e:  # noqa: BLE001
            print(f"keep-awake not set: {e}", flush=True)


def hash_file(path: Path) -> tuple[str, str, int]:
    s, m, n = hashlib.sha256(), hashlib.md5(), 0
    with path.open("rb") as fh:
        while True:
            b = fh.read(CHUNK)
            if not b:
                break
            s.update(b)
            m.update(b)
            n += len(b)
    return s.hexdigest(), m.hexdigest(), n


def cmd_hash(a: argparse.Namespace) -> None:
    lower_priority()
    root = Path(a.root)
    inv = [r for r in read_tsv(Path(a.inventory)) if not r["rel"].startswith(("ERROR:", "SPECIAL:"))]
    out = Path(a.out)
    done: dict[tuple[str, str, str], dict] = {}
    if out.exists():
        for r in read_tsv(out):
            done[(r["rel"], r["bytes"], r["mtime_ns"])] = r
    new = not out.exists()
    seen_ids: dict[str, str] = {}
    total = sum(int(r["bytes"]) for r in inv)
    t0, read = time.time(), 0
    with out.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        if new:
            w.writerow(["rel", "bytes", "mtime_ns", "file_id", "sha256", "md5", "hashed_utc", "note"])
        for r in sorted(inv, key=lambda r: r["rel"]):
            key = (r["rel"], r["bytes"], r["mtime_ns"])
            if key in done:
                continue
            p = root / r["rel"]
            fid = r["file_id"]
            if fid in seen_ids and int(r["nlink"]) > 1:
                prev = seen_ids[fid]
                w.writerow([r["rel"], r["bytes"], r["mtime_ns"], fid, prev[0], prev[1], now(), "hardlink"])
                fh.flush()
                continue
            try:
                st = p.stat()
                if str(st.st_size) != r["bytes"] or str(st.st_mtime_ns) != r["mtime_ns"]:
                    w.writerow([r["rel"], st.st_size, st.st_mtime_ns, fid, "", "", now(), "changed_since_inventory"])
                    fh.flush()
                    continue
                sha, md5, n = hash_file(p)
            except OSError as e:
                w.writerow([r["rel"], r["bytes"], r["mtime_ns"], fid, "", "", now(), f"error:{e}"])
                fh.flush()
                continue
            seen_ids[fid] = (sha, md5)
            w.writerow([r["rel"], n, r["mtime_ns"], fid, sha, md5, now(), ""])
            fh.flush()
            read += n
            if read // (5 << 30) != (read - n) // (5 << 30):
                print(f"{now()} hashed {read / 2**30:.1f} of {total / 2**30:.1f} GiB", flush=True)
        print(json.dumps({"bytes_hashed": read, "of_total": total, "seconds": round(time.time() - t0, 1)}), flush=True)


def load_drive_listing(path: Path) -> dict[str, int]:
    """Listing written by list_drive.ps1: <rel under vcc2026>\\t<bytes>\\t<mtime>."""
    out = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3 or parts[0] == "ERROR":
                continue
            out[parts[0].replace("\\", "/")] = int(parts[1])
    return out


def cmd_plan(a: argparse.Namespace) -> None:
    out = Path(a.out)
    refuse_existing(out)
    inv = [r for r in read_tsv(Path(a.inventory)) if not r["rel"].startswith(("ERROR:", "SPECIAL:"))]
    drive = load_drive_listing(Path(a.drive_listing))
    by_size_name: dict[tuple[int, str], list[str]] = {}
    for rel, b in drive.items():
        by_size_name.setdefault((b, rel.rsplit("/", 1)[-1]), []).append(rel)
    rows = []
    for r in inv:
        dest = f"data/{r['rel']}"
        b = int(r["bytes"])
        if dest in drive:
            status = "same_size_on_drive" if drive[dest] == b else "conflict_size_differs"
        else:
            status = "absent"
        elsewhere = [x for x in by_size_name.get((b, r["rel"].rsplit("/", 1)[-1]), []) if x != dest]
        rows.append({"rel": r["rel"], "bytes": b, "file_id": r["file_id"], "nlink": int(r["nlink"]),
                     "dest": dest, "status": status, "same_name_size_elsewhere": elsewhere})
    out.write_text(json.dumps({"written_utc": now(), "rows": rows}, indent=0), encoding="utf-8")
    summ: dict[str, list[int]] = {}
    for x in rows:
        s = summ.setdefault(x["status"], [0, 0])
        s[0] += 1
        s[1] += x["bytes"]
    print(json.dumps({k: {"files": v[0], "GiB": round(v[1] / 2**30, 3)} for k, v in summ.items()}))


def free_bytes(path: str) -> int:
    return shutil.disk_usage(path).free


def cmd_copy(a: argparse.Namespace) -> None:
    lower_priority()
    keep_awake()
    root, dest_root = Path(a.root), Path(a.dest)
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))["rows"]
    prefixes = tuple(a.only) if a.only else None
    hashes = {}
    if a.hashes and Path(a.hashes).exists():
        hashes = {r["rel"]: r for r in read_tsv(Path(a.hashes)) if r["sha256"]}
    receipts = Path(a.receipts)
    done = set()
    if receipts.exists():
        for line in receipts.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("status") in ("copied", "skipped_exists_same_size", "skipped_hardlink"):
                done.add(rec["rel"])
    margin = int(a.min_free_gb * 2**30)
    # One upload per physical file: a hard link whose file is already on Drive, or already copied under
    # another path, is recorded and not uploaded again.
    on_drive_ids = {r["file_id"]: r["dest"] for r in plan if r["status"] == "same_size_on_drive"}
    copied_ids: dict[str, str] = {}
    by_rel = {r["rel"]: r for r in plan}
    if receipts.exists():
        for line in receipts.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("status") == "copied" and rec["rel"] in by_rel:
                copied_ids[by_rel[rec["rel"]]["file_id"]] = rec["rel"]
    excluded = tuple(a.exclude) if a.exclude else ()
    todo = [r for r in plan if r["status"] == "absent" and (prefixes is None or r["rel"].startswith(prefixes))
            and not (excluded and r["rel"].startswith(excluded)) and r["rel"] not in done]
    todo.sort(key=lambda r: r["rel"])
    print(f"{now()} {len(todo)} files, {sum(r['bytes'] for r in todo) / 2**30:.2f} GiB to consider", flush=True)
    stop_file = Path(a.stop_file) if a.stop_file else None
    with receipts.open("a", encoding="utf-8") as rf:
        for r in todo:
            if stop_file and stop_file.exists():
                print(f"{now()} stop file {stop_file} present: stopping before {r['rel']}", flush=True)
                return
            src, dst = root / r["rel"], dest_root / r["rel"]
            if r["nlink"] > 1 and (r["file_id"] in on_drive_ids or r["file_id"] in copied_ids):
                other = on_drive_ids.get(r["file_id"]) or f"data/{copied_ids[r['file_id']]}"
                rf.write(json.dumps({"rel": r["rel"], "bytes": r["bytes"], "status": "skipped_hardlink",
                                     "same_physical_file_as": other, "finished_utc": now()}) + "\n")
                rf.flush()
                continue
            need = r["bytes"] + margin
            waited = 0
            while free_bytes(a.cache_disk) < need:
                if waited == 0:
                    print(f"{now()} waiting: free {free_bytes(a.cache_disk) / 2**30:.2f} GiB < "
                          f"{need / 2**30:.2f} GiB for {r['rel']}", flush=True)
                time.sleep(30)
                waited += 30
                if a.max_wait_s and waited > a.max_wait_s:
                    print(f"{now()} stop: waited {waited}s for free space", flush=True)
                    return
            rec = {"rel": r["rel"], "bytes": r["bytes"], "dest": str(dst), "started_utc": now()}
            if dst.exists():
                same = dst.stat().st_size == r["bytes"]
                rec.update(status="skipped_exists_same_size" if same else "refused_exists_different_size",
                           dest_bytes=dst.stat().st_size, finished_utc=now())
                rf.write(json.dumps(rec) + "\n")
                rf.flush()
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_name(dst.name + ".partial")
            if tmp.exists():
                tmp.unlink()
            s, m, n = hashlib.sha256(), hashlib.md5(), 0
            t0 = time.time()
            try:
                with src.open("rb") as fi, tmp.open("wb") as fo:
                    while True:
                        b = fi.read(CHUNK)
                        if not b:
                            break
                        s.update(b)
                        m.update(b)
                        n += len(b)
                        fo.write(b)
                os.replace(tmp, dst)
            except OSError as e:
                rec.update(status="error", error=str(e), finished_utc=now())
                rf.write(json.dumps(rec) + "\n")
                rf.flush()
                print(f"{now()} error on {r['rel']}: {e}", flush=True)
                if tmp.exists():
                    try:
                        tmp.unlink()
                    except OSError:
                        pass
                continue
            copied_ids[r["file_id"]] = r["rel"]
            rec.update(status="copied", copied_bytes=n, sha256=s.hexdigest(), md5=m.hexdigest(),
                       seconds=round(time.time() - t0, 2), finished_utc=now(),
                       free_gib_after=round(free_bytes(a.cache_disk) / 2**30, 2))
            h = hashes.get(r["rel"])
            if h:
                rec["matches_local_hash"] = (h["sha256"] == rec["sha256"])
            rf.write(json.dumps(rec) + "\n")
            rf.flush()
            print(f"{now()} copied {r['rel']} {n / 2**20:.1f} MiB in {rec['seconds']}s", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("inventory")
    s.add_argument("--root", required=True)
    s.add_argument("--out", required=True)
    s = sub.add_parser("hash")
    s.add_argument("--root", required=True)
    s.add_argument("--inventory", required=True)
    s.add_argument("--out", required=True)
    s = sub.add_parser("plan")
    s.add_argument("--inventory", required=True)
    s.add_argument("--drive-listing", required=True)
    s.add_argument("--out", required=True)
    s = sub.add_parser("copy")
    s.add_argument("--root", required=True)
    s.add_argument("--dest", required=True, help="the Drive mirror of the data root, e.g. G:/Il mio Drive/vcc2026/data")
    s.add_argument("--plan", required=True)
    s.add_argument("--hashes", default=None)
    s.add_argument("--receipts", required=True)
    s.add_argument("--only", nargs="*", default=None, help="relative path prefixes to copy")
    s.add_argument("--exclude", nargs="*", default=None, help="relative path prefixes never copied in this run")
    s.add_argument("--stop-file", default=None, help="stop before the next file when this path exists")
    s.add_argument("--cache-disk", default="C:\\")
    s.add_argument("--min-free-gb", type=float, default=8.0)
    s.add_argument("--max-wait-s", type=int, default=0)
    a = p.parse_args()
    {"inventory": cmd_inventory, "hash": cmd_hash, "plan": cmd_plan, "copy": cmd_copy}[a.cmd](a)


if __name__ == "__main__":
    main()
