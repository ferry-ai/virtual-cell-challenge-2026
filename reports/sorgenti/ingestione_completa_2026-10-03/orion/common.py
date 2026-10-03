"""Shared pieces of the expanded ingestion: the reused R-LAB code, a shard sink with receipts, byte-range fetching.

The shard contract, the adapters and the job runner of `reports/sorgenti/corpus_cellulare_2026-09-30` are imported
from their own files, never copied or changed (reports/CLAUDE.md). A shard written through `ShardSink` is judged by
the same `contracts.validate_shard` and laid out as `rlab_job.py` lays it out:

    <out>/<unit>/<shard>.h5ad
    <out>/<unit>/receipts/<shard>.json
    <out>/<unit>/manifest.json             (written when the unit ends, with its parity)
    <out>/complete.json                    (written last, only if every unit passed)
    <out>/verify_manifest.json (+ .sha256) (the list an independent runtime re-hashes: archivio_cloud verify_drive.py)

so `publish_kaggle.py` and the readers of the cell network work on it unchanged. Nothing is written over: every
output directory must be new; an earlier attempt is passed as `reuse` and its verified shards are referenced in
place, exactly as `rlab_job.py --reuse` does.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import shutil
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CORPUS = REPO / "reports/sorgenti/corpus_cellulare_2026-09-30"
MISSING = "MISSING"
USER_AGENT = "vcc2026-ingestione-espansione/1"
REDIRECTS = (301, 302, 303, 307, 308)


def corpus():
    """(adapters, rlab_job, contracts, inspect_remote): the R-LAB modules, imported from their own folder."""
    if str(CORPUS) not in sys.path:
        sys.path.insert(0, str(CORPUS))
    import adapters  # noqa: PLC0415
    import contracts  # noqa: PLC0415
    import inspect_remote  # noqa: PLC0415
    import rlab_job  # noqa: PLC0415
    return adapters, rlab_job, contracts, inspect_remote


def remote_csr():
    """`vcc2026.remote_csr` (selected rows of a remote CSR as exact byte ranges), from the live library."""
    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from vcc2026 import remote_csr as module  # noqa: PLC0415
    return module


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _plain(v):
    if hasattr(v, "item"):
        return v.item()
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, (set, frozenset)):
        return sorted(v)
    return str(v)


def dump_new(path: Path, obj) -> None:
    """Write JSON to a file that must not exist yet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, default=_plain)


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def new_dir(path: Path) -> Path:
    """A directory that must not exist: no output is ever written over."""
    if path.exists():
        sys.exit(f"refusing: {path} exists")
    path.mkdir(parents=True)
    return path


def sidecar_of(path: Path) -> Path:
    return path.with_name(path.name + ".sha256")


def write_sidecar(path: Path) -> str:
    """`<file>.sha256` next to a state file (obs table, chunk map, sample), written once."""
    digest = sha256_file(path)
    with open(sidecar_of(path), "x", encoding="utf-8") as fh:
        fh.write(f"{digest}  {path.name}\n")
    return digest


def check_sidecar(path: Path) -> str:
    """The sha256 of `path`, which must equal the one in its sidecar."""
    want = sidecar_of(path).read_text(encoding="utf-8").split()[0]
    got = sha256_file(path)
    if got != want:
        sys.exit(f"refusing: {path} hashes {got}, its sidecar says {want}")
    return got


def find_state(name: str, out: Path, reuse: list[Path] | None) -> Path | None:
    """A state file of this attempt or of an earlier one (searched in the order given), when its sidecar matches."""
    for root in [out] + list(reuse or []):
        path = root / name
        if path.is_file() and sidecar_of(path).is_file():
            check_sidecar(path)
            return path
    return None


# ------------------------------------------------------------------------------------------ byte ranges

def head(url: str, attempts: int = 5) -> dict:
    """Size, ETag and Last-Modified of a public URL, from a one-byte ranged GET (hosts that redirect to signed
    storage sign the URL for the method used: a HEAD-resolved URL can refuse ranged GETs, inspect_remote.py)."""
    req = urllib.request.Request(url, headers={"Range": "bytes=0-0", "User-Agent": USER_AGENT})
    last = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                total = r.headers.get("Content-Range", "").rsplit("/", 1)[-1]
                size = int(total) if total.isdigit() else int(r.headers["Content-Length"])
                return {"url": url, "final_host": urllib.parse.urlsplit(r.geturl()).netloc, "bytes": size,
                        "etag": r.headers.get("ETag") or MISSING,
                        "last_modified": r.headers.get("Last-Modified") or MISSING, "status": r.status}
        except OSError as err:
            last = err
            time.sleep(5 * attempt)
    raise OSError(f"{url}: no answer after {attempts} attempts ({last})")


def range_fetcher(url: str, expected_size: int, etag: str | None = None, retries: int = 6, timeout: float = 120.0):
    """`fetch(a, b)` -> bytes [a, b) of the URL, thread-safe, with the standard library only.

    Every answer must be a 206 of exactly the span asked, of a file of `expected_size` bytes and, when the host sends
    ETags, of the same ETag as the first answer (or as `etag` when given): bytes of two versions of a file are never
    mixed. Each thread keeps one connection open (thousands of small ranges would otherwise pay a TLS handshake
    each); a host that answers with a redirect (signed storage URLs) is asked through urllib, which follows it."""
    parts = urllib.parse.urlsplit(url)
    target = parts.path + (f"?{parts.query}" if parts.query else "")
    local = threading.local()
    lock = threading.Lock()
    state = {"etag": etag if etag and etag != MISSING else None, "redirects": False, "requests": 0, "bytes": 0}

    def headers(a: int, b: int) -> dict:
        return {"Range": f"bytes={a}-{b - 1}", "User-Agent": USER_AGENT, "Accept-Encoding": "identity"}

    def bounded(r, status: int, span: str, a: int, b: int) -> bytes:
        """The body of an answer, read only when it is the 206 asked for and never beyond the span: a server that
        ignores Range (a 200 with the whole file) is refused before one byte of the file is materialised."""
        if status in REDIRECTS:
            return b""
        if status != 206:
            raise OSError(f"HTTP {status}: the server did not honour Range")
        if not span.startswith(f"bytes {a}-{b - 1}/"):
            raise OSError(f"unexpected Content-Range {span!r}")
        if int(span.rsplit("/", 1)[-1]) != expected_size:
            raise ValueError(f"the remote size changed: {span}, expected {expected_size}")
        body = r.read(b - a + 1)
        if len(body) != b - a:
            raise OSError(f"body of {len(body)} bytes for a span of {b - a}")
        return body

    def keepalive(a: int, b: int):
        conn = getattr(local, "conn", None)
        if conn is None:
            cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
            conn = local.conn = cls(parts.netloc, timeout=timeout)
        try:
            conn.request("GET", target, headers=headers(a, b))
            r = conn.getresponse()
            span = r.getheader("Content-Range", "") or ""
            body = bounded(r, r.status, span, a, b)
            if r.status in REDIRECTS:
                r.read()
        except Exception:
            conn.close()                      # an unread or refused body must not poison the next request
            local.conn = None
            raise
        return r.status, r.getheader("ETag"), body

    def oneshot(a: int, b: int):
        req = urllib.request.Request(url, headers=headers(a, b))
        with urllib.request.urlopen(req, timeout=timeout) as r:
            span = r.headers.get("Content-Range", "") or ""
            return r.status, r.headers.get("ETag"), bounded(r, r.status, span, a, b)

    def fetch(a: int, b: int) -> bytes:
        last = None
        for attempt in range(retries):
            try:
                status, tag, body = oneshot(a, b) if state["redirects"] else keepalive(a, b)
                if status in REDIRECTS:
                    state["redirects"] = True
                    status, tag, body = oneshot(a, b)
                if status != 206 or len(body) != b - a:
                    raise OSError(f"HTTP {status} with {len(body)} bytes for a span of {b - a}")
                with lock:
                    if tag and state["etag"] is None:
                        state["etag"] = tag
                    elif tag and tag != state["etag"]:
                        raise ValueError(f"the file changed while it was read: ETag {tag} after {state['etag']}")
                    state["requests"] += 1
                    state["bytes"] += len(body)
                return body
            except ValueError:
                raise
            except (OSError, http.client.HTTPException) as err:
                last = err
                time.sleep(min(60.0, 2.0 ** attempt))
        raise OSError(f"range {a}-{b} of {url} failed after {retries} attempts: {last}")

    fetch.state = state
    return fetch


def local_fetcher(path: Path):
    """Byte ranges of a local file: the test double of `range_fetcher`."""
    state = {"etag": None, "redirects": False, "requests": 0, "bytes": 0}

    def fetch(a: int, b: int) -> bytes:
        with open(path, "rb") as fh:
            fh.seek(a)
            body = fh.read(b - a)
        state["requests"] += 1
        state["bytes"] += len(body)
        return body

    fetch.state = state
    return fetch


def download(url: str, size: int, dest: Path, sha256: str | None = None, md5: str | None = None, threads: int = 8,
             chunk: int = 32 << 20) -> dict:
    """A whole file by parallel ranges, accepted only with the published size and checksum.

    Nothing is written over: `dest` must not exist, the bytes go to a fresh `<dest>.<pid>.<ns>.partial` opened
    exclusively, and the partial becomes `dest` only after every check passed. A failed attempt removes its own
    partial and leaves `dest` absent."""
    from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415
    dest = Path(dest)
    if dest.exists():
        raise FileExistsError(f"refusing: {dest} exists")
    partial = dest.with_name(f"{dest.name}.{os.getpid()}.{time.time_ns()}.partial")
    fetch = range_fetcher(url, size)
    spans = [(a, min(a + chunk, size)) for a in range(0, size, chunk)]

    def run(span):
        buf = fetch(*span)
        with open(partial, "r+b") as fh:
            fh.seek(span[0])
            fh.write(buf)

    t0 = time.time()
    try:
        with open(partial, "xb") as fh:
            fh.truncate(size)
        with ThreadPoolExecutor(threads) as ex:
            list(ex.map(run, spans))
        got = {"bytes": partial.stat().st_size, "seconds": round(time.time() - t0, 1),
               "etag": fetch.state["etag"] or MISSING}
        if got["bytes"] != size:
            raise OSError(f"{dest.name}: {got['bytes']} bytes on disk, {size} published")
        if sha256:
            got["sha256"] = sha256_file(partial)
            if got["sha256"] != sha256:
                raise OSError(f"{dest.name}: sha256 {got['sha256']} is not the published {sha256}")
        if md5:
            got["md5"] = md5_file(partial)
            if got["md5"] != md5:
                raise OSError(f"{dest.name}: md5 {got['md5']} is not the published {md5}")
        if dest.exists():
            raise FileExistsError(f"refusing: {dest} appeared during the download")
        os.rename(partial, dest)
    finally:
        if partial.exists():
            partial.unlink()
    return got


# ------------------------------------------------------------------------------------------ shards

def writer_record(script: Path, runtime_manifest: Path | None = None) -> dict:
    """Who wrote a shard: script, reused modules and snapshot, as `rlab_job.py` records them."""
    return {"script": script.name, "script_sha256": sha256_file(script),
            "adapters_sha256": sha256_file(CORPUS / "adapters.py"),
            "contracts_sha256": sha256_file(CORPUS / "contracts.py"),
            "rlab_job_sha256": sha256_file(CORPUS / "rlab_job.py"),
            "common_sha256": sha256_file(HERE / "common.py"),
            "snapshot_sha256": os.environ.get("RLAB_SNAPSHOT_SHA256", MISSING),
            "commit": os.environ.get("RLAB_COMMIT", MISSING),
            "runtime_manifest": str(runtime_manifest) if runtime_manifest else MISSING,
            "runtime_manifest_sha256": sha256_file(runtime_manifest) if runtime_manifest else MISSING}


def source_record(source_id: str, release: str, license_: str, files: list[dict]) -> dict:
    """The `uns/source` of a shard: id, release, locator and checksum of the bytes read (the first file in the open,
    all of them as JSON). Never a None: anndata cannot write it."""
    first = files[0]
    return {"id": source_id, "release": release, "locator": first["locator"], "bytes": int(first["bytes"]),
            "sha256": first.get("sha256") or "not recomputed: read by ranges, see etag, md5 or crc32c",
            "md5": first.get("md5") or MISSING, "etag": first.get("etag") or MISSING,
            "files_json": json.dumps(files), "license": license_ or MISSING}


class ShardSink:
    """One unit of a job: shards written, validated, copied to the out disk, re-hashed there and receipted one by one."""

    def __init__(self, out: Path, stage: Path, unit: str, source: dict, writer: dict, reuse: list[Path] | None = None,
                 min_free_stage_bytes: int = 4 << 30, require: dict | None = None):
        self.unit, self.source, self.writer = unit, source, writer
        self.out, self.stage = out / unit, stage / unit
        self.reuse = list(reuse or [])
        self.min_free = min_free_stage_bytes
        self.require = require or {}          # receipt fields an earlier shard must share to be reused
        self.out.mkdir(parents=True)
        self.stage.mkdir(parents=True)
        self.shards: list[dict] = []
        self.t0 = time.time()

    def have(self, name: str) -> dict | None:
        """A shard of an earlier attempt with a matching receipt, size and sha256 (re-read now): referenced, not
        copied. A shard made under other parameters (`require`, e.g. another sample manifest) is never reused."""
        for earlier in self.reuse:
            receipt = earlier / self.unit / "receipts" / f"{name}.json"
            if not receipt.is_file():
                continue
            old = load_json(receipt)
            if any(old.get(k) != v for k, v in self.require.items()):
                continue
            candidate = earlier / self.unit / f"{name}.h5ad"
            if not candidate.is_file() and old.get("path"):
                candidate = Path(old["path"])
            if (candidate.is_file() and candidate.stat().st_size == old.get("bytes")
                    and sha256_file(candidate) == old.get("sha256")):
                hit = {**old, "path": str(candidate), "reused_from": str(candidate)}
                # Persist the reference so another restart can follow this attempt alone.
                dump_new(self.out / "receipts" / f"{name}.json", hit)
                self.shards.append(hit)
                print(f"{self.unit}/{name}: reused from {hit['reused_from']}", flush=True)
                return hit
        return None

    def put(self, name: str, x, obs, var, uns: dict, obsm: dict | None = None, extra: dict | None = None) -> dict:
        _, rlab_job, _, _ = corpus()
        free = shutil.disk_usage(self.stage).free
        if free < self.min_free:
            sys.exit(f"stopping: {free} bytes free on the stage disk")
        uns = {**uns, "source": self.source, "qc_version": "none", "writer": self.writer}
        local = self.stage / f"{name}.h5ad"
        problems, info = rlab_job.write_local(x, obs, var, uns, local, obsm)
        if problems:
            dump_new(self.out / "receipts" / f"{name}.FAILED.json", {"problems": problems, "utc": now()})
            sys.exit(f"{self.unit}/{name}: contract problems {problems}")
        digest = sha256_file(local)
        dest, tmp = self.out / f"{name}.h5ad", self.out / f"{name}.h5ad.partial"
        shutil.copyfile(local, tmp)
        os.replace(tmp, dest)
        copy_digest = sha256_file(dest)
        if copy_digest != digest:
            sys.exit(f"{self.unit}/{name}: the copy on the out disk hashes {copy_digest}, the local file {digest}")
        receipt = {**info, "shard": name, "path": str(dest), "bytes": dest.stat().st_size, "sha256": digest,
                   "copy_sha256_reread": copy_digest, "rows": uns.get("rows"), "utc": now(),
                   **self.require, **(extra or {})}
        dump_new(self.out / "receipts" / f"{name}.json", receipt)
        local.unlink()
        self.shards.append(receipt)
        print(f"{self.unit}/{name}: {info['cells']} cells, {info['nnz']} nnz, {receipt['bytes']} bytes, "
              f"{time.time() - self.t0:.0f}s", flush=True)
        return receipt

    def finish(self, parity: dict, extra: dict | None = None) -> dict:
        """The unit manifest. `parity` holds the unit's checks; `ok` is the conjunction of its boolean entries and of
        the per-shard re-read. A unit without shards never passes."""
        parity = {"per_shard_reread": all(s["sum_after"] == s["sum_before"] for s in self.shards),
                  "has_shards": bool(self.shards), **parity}
        parity["ok"] = all(v for v in parity.values() if isinstance(v, bool))
        keys = ("shard", "path", "bytes", "sha256", "cells", "nnz", "sum_after", "targets", "control_kind",
                "reused_from")
        manifest = {"unit": self.unit, "source": self.source,
                    "shards": [{k: s.get(k) for k in keys} for s in self.shards],
                    "totals": {"shards": len(self.shards), "cells": sum(s["cells"] for s in self.shards),
                               "nnz": sum(s["nnz"] for s in self.shards),
                               "counts": sum(s["sum_after"] for s in self.shards),
                               "bytes": sum(s["bytes"] for s in self.shards),
                               "control_kind": dict(sum((Counter(s["control_kind"]) for s in self.shards),
                                                        Counter()))},
                    "parity": parity, "seconds": round(time.time() - self.t0, 1), "utc": now(), **(extra or {})}
        dump_new(self.out / "manifest.json", manifest)
        if self.stage.is_dir() and not any(self.stage.iterdir()):
            self.stage.rmdir()
        return manifest


def complete(out: Path, job_id: str, units: list[dict], data_root: Path | None = None,
             extra: dict | None = None) -> bool:
    """`complete.json` (or `parity_failed.json`) written last, and the list an independent runtime re-hashes."""
    ok = bool(units) and all(u["parity"]["ok"] for u in units)
    if ok and data_root is not None:
        files = []
        for u in units:
            for s in u["shards"]:
                p = Path(s["path"])
                try:
                    rel = p.resolve().relative_to(Path(data_root).resolve()).as_posix()
                except ValueError:
                    rel = str(p)
                files.append({"rel": rel, "bytes": s["bytes"], "sha256": s["sha256"], "unit": u["unit"],
                              "cells": s["cells"]})
        listing = out / "verify_manifest.json"
        dump_new(listing, {"job_id": job_id, "data_root": str(data_root), "files": files, "utc": now()})
        with open(listing.with_suffix(".sha256"), "x", encoding="utf-8") as fh:   # the name verify_drive.py reads
            fh.write(f"{sha256_file(listing)}  {listing.name}\n")
    dump_new(out / ("complete.json" if ok else "parity_failed.json"),
             {"job_id": job_id, "status": "complete" if ok else "parity_failed",
              "units": {u["unit"]: {"cells": u["totals"]["cells"], "shards": u["totals"]["shards"],
                                    "bytes": u["totals"]["bytes"], "parity_ok": u["parity"]["ok"],
                                    "manifest_sha256": sha256_file(out / u["unit"] / "manifest.json")}
                        for u in units},
              "utc": now(), **(extra or {})})
    return ok
