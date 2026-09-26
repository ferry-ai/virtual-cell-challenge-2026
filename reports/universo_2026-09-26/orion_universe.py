"""F1 of R-V2, Orion: effects of EVERY X-Atlas/Orion target, not only the 300 of the panel.

Stage 102 streams X-Atlas/Orion (Xaira; HCT116 109 parquet files, HEK293T 223, one per GEM
batch; CC-BY-NC-SA-4.0) but keeps the panel targets only. This streams every file of a line once
more, one at a time (each download is deleted once applied), and keeps every target. The counts
of each pass-filter cell (``pass_guide_filter == 1``) are added to its pool of GEM batches -- file
index modulo 8 in the sorted file list, the pools of stage 102's ``--finalize`` -- in an on-disk
float32 array per pool: one row per target in order of first sight, one column per gene of the
official 18,533-gene axis (Orion gene tokens matched by name, as stages 102 and 98 match them).
Per (pool, target) it also keeps cells, UMIs and the counts over all named gene tokens, the
library size stage 98 divides by. Non-targeting cells are summed per pool in float64.

Crash safety: ``journal.json`` lists the files applied to each pool. A pool is marked dirty before
a file touches it and clean once its array is synced to disk; a pool found dirty on restart is
zeroed and rebuilt from its files, so no file is ever counted twice. A lock keeps a second
process off the same line.

``--finalize`` writes chunks of 600 targets in stage 98's npz format (targets, shrunk, raw, se,
n_cells, meta) with stage 98's own estimator: `effects_from_pseudobulk` on the (pool, target)
rows, each pool against its own controls, then `AxisTable.from_source` -- as the panel cache
``multisource_2026-09-23_r5/orion_<line>.npz`` was made. One extra column holds each row's counts
off the axis, so every library size is the one stage 98 used. The estimator skips a pool with
fewer than 10 cells of a target, so a target without such a pool has no effect row;
``index.csv`` still lists it, with an empty chunk. The manifest holds the file list, the bytes
and sha256 of the chunks, and the parity with the r5 panel cache.

    scripts/py.cmd reports/universo_2026-09-26/orion_universe.py --line HCT116                  # stream
    scripts/py.cmd reports/universo_2026-09-26/orion_universe.py --line HCT116 --finalize
    scripts/py.cmd reports/universo_2026-09-26/orion_universe.py --line HCT116 HEK293T --chain   # both, in turn
    scripts/py.cmd reports/universo_2026-09-26/orion_universe.py --line HCT116 --status

Defaults: work ``<data_root>/interim/orion_universe_<line>``, chunks
``<data_root>/processed/universe_orion_<line>_2026-09-26``, report copy
``reports/universo_2026-09-26/orion_<line>/``. Nothing is overwritten.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.bench import log  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402

_spec = importlib.util.spec_from_file_location("stage102", REPO / "scripts" / "102_extract_orion_panel.py")
stage102 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage102)

DATA = config.paths().data_root
NTC = stage102.NTC
N_POOLS = 8
CHUNK = 600          # targets per output npz, as the K562 universe
SUB = 150            # targets per call of the estimator: bounds the memory of its input rows
DATE = "2026-09-26"
COLUMNS = ["gene_token_id", "gene_expression", "gene_target", "pass_guide_filter", "total_counts", "sample"]
PANEL_CSV = DATA / "raw" / "controls" / "pert_counts.csv"
PANEL_CACHE = DATA / "processed" / "multisource_2026-09-23_r5"
COUNT_KEYS = ("cells", "umis", "named")


# ----------------------------------------------------------------------------- small utilities

def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _retry(fn, tries: int = 20, wait: float = 0.5):
    """Windows: a scanner holding a file for a moment must not kill an hours-long run."""
    for i in range(tries):
        try:
            return fn()
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(wait)


def write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    _retry(lambda: os.replace(tmp, path))


def save_json(path: Path, obj) -> None:
    write_atomic(path, json.dumps(obj, indent=1, default=str).encode("utf-8"))


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: Path, block: int = 16 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(block):
            h.update(chunk)
    return h.hexdigest()


def memory() -> dict:
    """This process's working set and private bytes, now and at their peak, in MiB (Windows)."""
    if sys.platform != "win32":
        return {}
    import ctypes.wintypes as wt

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    c = PMC()
    c.cb = ctypes.sizeof(PMC)
    get = ctypes.windll.psapi.GetProcessMemoryInfo
    get.argtypes = [wt.HANDLE, ctypes.POINTER(PMC), wt.DWORD]   # as vcc2026.resources: -1 must be a HANDLE
    get.restype = wt.BOOL
    if not get(wt.HANDLE(ctypes.windll.kernel32.GetCurrentProcess()), ctypes.byref(c), c.cb):
        return {}
    mib = float(2**20)
    return {"ws_mib": round(c.WorkingSetSize / mib), "peak_ws_mib": round(c.PeakWorkingSetSize / mib),
            "private_mib": round(c.PagefileUsage / mib), "peak_private_mib": round(c.PeakPagefileUsage / mib)}


def _alive(pid: int) -> bool:
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes.wintypes as wt
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k32.OpenProcess.restype = wt.HANDLE
    k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    k32.GetExitCodeProcess.restype = wt.BOOL
    k32.CloseHandle.argtypes = [wt.HANDLE]
    h = k32.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    try:
        code = wt.DWORD()
        return bool(k32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
    finally:
        k32.CloseHandle(h)


def lock_holder(work: Path) -> int | None:
    """PID of a live process holding the line's lock, else None."""
    path = work / "stream.lock"
    if not path.exists():
        return None
    try:
        pid = int(path.read_text(encoding="utf-8").split()[0])
    except (ValueError, IndexError, OSError):
        return None
    return pid if pid != os.getpid() and _alive(pid) else None


class Lock:
    """One process per line: a lock file with the PID; a lock left by a dead process is taken over."""

    def __init__(self, work: Path):
        self.path = work / "stream.lock"

    def __enter__(self):
        holder = lock_holder(self.path.parent)
        if holder is not None:
            raise SystemExit(f"{self.path}: process {holder} is working on this line")
        if self.path.exists():
            log(f"stale lock removed: {self.path.read_text(encoding='utf-8').strip()}")
            self.path.unlink()
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"{os.getpid()} {now()}\n".encode())
        os.close(fd)
        return self

    def __exit__(self, *exc):
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


# ----------------------------------------------------------------------------- the line's inputs

def defaults(line: str) -> SimpleNamespace:
    low = line.lower()
    return SimpleNamespace(work=DATA / "interim" / f"orion_universe_{low}",
                           out=DATA / "processed" / f"universe_orion_{low}_{DATE}",
                           report=HERE / f"orion_{low}")


def file_list(line: str, work: Path) -> list[dict]:
    """The line's files, frozen at the first run: path, bytes, LFS sha256 and pool.

    Paths and sizes come from stage 102's own `list_files`, so the pools are its pools; the
    sha256 is the Git LFS object id Hugging Face publishes for each file.
    """
    path = work / "files.json"
    if path.exists():
        return load_json(path)["files"]
    import httpx
    ref = stage102.list_files(line)
    r = httpx.get(f"https://huggingface.co/api/datasets/{stage102.REPO}/tree/main/data", timeout=60)
    r.raise_for_status()
    sha = {i["path"]: (i.get("lfs") or {}).get("oid") for i in r.json() if i.get("type") == "file"}
    files = [{"name": Path(p).stem, "path": p, "bytes": int(s), "sha256": sha.get(p), "pool": i % N_POOLS}
             for i, (p, s) in enumerate(ref)]
    save_json(path, {"line": line, "listed_utc": now(), "repo": stage102.REPO, "files": files})
    return files


def token_columns(tokens: pd.DataFrame, axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Official-axis column of every Orion gene token (-1 off the axis), and which tokens are named.

    Names are made unique as stage 102's h5ad makes them (``var_names_make_unique``, first
    occurrence keeps the name) and matched to the axis by name, as `AxisTable.from_source`
    matches that h5ad's genes in stage 98.
    """
    import warnings

    import anndata as ad
    n_tokens = int(tokens["gene_token_id"].max()) + 1
    names = tokens.set_index("gene_token_id").reindex(range(n_tokens))["gene_name"].fillna("").astype(str)
    named = (names != "").to_numpy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        var = ad.AnnData(var=pd.DataFrame(index=names.to_numpy()[named].astype(str)))
        var.var_names_make_unique()
    pos = pd.Index(axis).get_indexer(np.asarray(var.var_names).astype(str))
    col = np.full(n_tokens, -1, dtype=np.int64)
    col[np.flatnonzero(named)] = pos
    hit = col[col >= 0]
    if np.unique(hit).size != hit.size:
        raise ValueError("two gene tokens map to one axis gene")
    return col, named


class Registry:
    """Targets in order of first sight: the row of each target in every pool array."""

    def __init__(self, work: Path):
        self.path = work / "targets.json"
        self.names: list[str] = load_json(self.path) if self.path.exists() else []
        self.index = {t: i for i, t in enumerate(self.names)}

    def ids(self, names) -> np.ndarray:
        out = np.empty(len(names), dtype=np.int64)
        for j, t in enumerate(names):
            i = self.index.get(t)
            if i is None:
                i = self.index[t] = len(self.names)
                self.names.append(t)
            out[j] = i
        return out

    def save(self) -> None:
        save_json(self.path, self.names)


def pool_paths(work: Path, k: int) -> tuple[Path, Path]:
    return work / f"pool{k}.f32", work / f"pool{k}_counts.npz"


def load_counts(work: Path, k: int, n_targets: int, G: int) -> dict:
    c = {"cells": np.zeros(n_targets, np.int64), "umis": np.zeros(n_targets), "named": np.zeros(n_targets),
         "ntc_sums": np.zeros(G), "ntc_named": np.zeros(1), "ntc_cells": np.zeros(1, np.int64),
         "ntc_umis": np.zeros(1)}
    path = pool_paths(work, k)[1]
    if path.exists():
        with np.load(path) as z:
            for key in c:
                if key in COUNT_KEYS:
                    c[key][: z[key].size] = z[key]
                else:
                    c[key][...] = z[key]
    return c


def grow(c: dict, n: int) -> None:
    for key in COUNT_KEYS:
        if c[key].size < n:
            c[key] = np.concatenate([c[key], np.zeros(n - c[key].size, c[key].dtype)])


def save_counts(work: Path, k: int, c: dict) -> None:
    path = pool_paths(work, k)[1]
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        np.savez(fh, **c)
        fh.flush()
        os.fsync(fh.fileno())
    _retry(lambda: os.replace(tmp, path))


# ----------------------------------------------------------------------------- pool arrays on disk

def _runs(ridx: np.ndarray, most: int = 256):
    """(start, stop) positions in sorted ``ridx`` of runs of consecutive rows, at most ``most`` long."""
    cut = np.flatnonzero(np.diff(ridx) != 1) + 1
    for a, b in zip(np.r_[0, cut].tolist(), np.r_[cut, ridx.size].tolist()):
        for s in range(a, b, most):
            yield s, min(b, s + most)


def _read_into(fh, off: int, out: np.ndarray, size: int) -> None:
    """Fill ``out`` (zeros) from byte ``off``; bytes past the end of the file stay zero."""
    view = memoryview(out).cast("B")
    n = max(0, min(view.nbytes, size - off))
    fh.seek(off)
    got = 0
    while got < n:
        r = fh.readinto(view[got:n])
        if not r:
            raise OSError(f"short read at byte {off + got}")
        got += r


def _write_all(fh, off: int, arr: np.ndarray) -> None:
    view = memoryview(arr).cast("B")
    fh.seek(off)
    done = 0
    while done < view.nbytes:
        done += fh.write(view[done:])


def read_rows(path: Path, ridx: np.ndarray, G: int) -> np.ndarray:
    """Rows ``ridx`` (distinct, any order) of a pool array; rows past its end are zero."""
    out = np.zeros((ridx.size, G), np.float32)
    if not path.exists() or ridx.size == 0:
        return out
    order = np.argsort(ridx, kind="stable")
    srt = ridx[order]
    size = path.stat().st_size
    with open(path, "rb", buffering=0) as fh:
        for a, b in _runs(srt):
            block = np.zeros((b - a, G), np.float32)
            _read_into(fh, int(srt[a]) * G * 4, block, size)
            out[order[a:b]] = block
    return out


class PoolBuffer:
    """Adds count rows to one pool's on-disk float32 array through a bounded in-memory buffer.

    Counts are integers, exact in float32 up to 2**24 per (pool, target, gene); the targets'
    sums stay far below that. The array grows as rows past its end are written.
    """

    def __init__(self, path: Path, G: int, slots: int):
        self.path, self.G = path, G
        self.buf = np.zeros((slots, G), np.float32)
        self.slot: dict[int, int] = {}
        if not path.exists():
            path.touch()
        self.fh = open(path, "r+b", buffering=0)
        self.flushes = 0
        self.seconds = 0.0

    def add(self, ridx: np.ndarray, block: np.ndarray) -> None:
        fresh = [r for r in ridx.tolist() if r not in self.slot]
        if len(self.slot) + len(fresh) > self.buf.shape[0]:
            self.flush()
            fresh = ridx.tolist()
        for r in fresh:
            self.slot[r] = len(self.slot)
        s = np.fromiter((self.slot[r] for r in ridx.tolist()), dtype=np.int64, count=ridx.size)
        self.buf[s] += block.astype(np.float32)

    def flush(self) -> None:
        if not self.slot:
            return
        t0 = time.monotonic()
        ridx = np.fromiter(self.slot.keys(), np.int64, len(self.slot))
        slots = np.fromiter(self.slot.values(), np.int64, len(self.slot))
        order = np.argsort(ridx)
        ridx, slots = ridx[order], slots[order]
        size = os.fstat(self.fh.fileno()).st_size
        for a, b in _runs(ridx):
            cur = np.zeros((b - a, self.G), np.float32)
            off = int(ridx[a]) * self.G * 4
            _read_into(self.fh, off, cur, size)
            cur += self.buf[slots[a:b]]
            _write_all(self.fh, off, cur)
        self.buf[: len(self.slot)] = 0
        self.slot.clear()
        self.flushes += 1
        self.seconds += time.monotonic() - t0

    def close(self) -> None:
        self.flush()
        t0 = time.monotonic()
        os.fsync(self.fh.fileno())
        self.fh.close()
        self.seconds += time.monotonic() - t0


# ----------------------------------------------------------------------------- streaming

def fetch(f: dict, dest: Path, threads: int, attempts: int = 8) -> str:
    """Download with stage 102's parallel ranges; accept only the published size and sha256."""
    for attempt in range(1, attempts + 1):
        try:
            if not (dest.exists() and dest.stat().st_size == f["bytes"]):
                stage102.download(f["path"], f["bytes"], dest, threads=threads)
            digest = sha256_file(dest)
            if f["sha256"] is None or digest == f["sha256"]:
                return digest
            log(f"  {f['name']}: sha256 {digest[:12]} is not the published {f['sha256'][:12]}; again")
            _retry(dest.unlink)
        except Exception as exc:      # network: wait and try again, the journal is untouched
            log(f"  {f['name']}: download attempt {attempt} failed: {exc!r}")
        time.sleep(min(600, 30 * attempt))
    raise RuntimeError(f"{f['name']}: no verified download after {attempts} attempts")


def apply_file(parquet: Path, k: int, work: Path, reg: Registry, col: np.ndarray, named: np.ndarray,
               G: int, batch_rows: int, slots: int) -> dict:
    """Add one batch file's pass-filter cells to pool ``k``: counts on the axis, cells, UMIs, library."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    # pyarrow 25 pre-reads whole column chunks by default, and mimalloc keeps what it frees:
    # pages are streamed instead and memory goes back to the system after every file.
    pa.set_memory_pool(pa.system_memory_pool())
    counts = load_counts(work, k, len(reg.names), G)
    pool = PoolBuffer(pool_paths(work, k)[0], G, slots)
    pf = pq.ParquetFile(parquet, buffer_size=4 << 20, pre_buffer=False)
    n_tokens = col.size
    all_named = bool(named.all())
    rows_seen = cells_pass = cells_ntc = 0
    samples, in_file = set(), set()
    integer_counts = True
    decode_s = 0.0
    batches = pf.iter_batches(batch_size=batch_rows, columns=COLUMNS)
    while True:
        t_dec = time.monotonic()
        batch = next(batches, None)
        decode_s += time.monotonic() - t_dec
        if batch is None:
            break
        n = batch.num_rows
        rows_seen += n
        tgt = batch.column("gene_target").to_numpy(zero_copy_only=False).astype(str)
        ok = batch.column("pass_guide_filter").to_numpy(zero_copy_only=False) == 1
        samples.update(pd.unique(batch.column("sample").to_numpy(zero_copy_only=False).astype(str)).tolist())
        if not ok.any():
            continue
        umi = batch.column("total_counts").to_numpy(zero_copy_only=False).astype(np.float64)
        tok_col, ex_col = batch.column("gene_token_id"), batch.column("gene_expression")
        off = tok_col.offsets.to_numpy(zero_copy_only=False)
        if not np.array_equal(off, ex_col.offsets.to_numpy(zero_copy_only=False)):
            raise ValueError(f"{parquet.name}: token and expression lists differ")
        tok = tok_col.values.to_numpy(zero_copy_only=False)[off[0]:off[-1]]
        ex = ex_col.values.to_numpy(zero_copy_only=False)[off[0]:off[-1]]
        del tok_col, ex_col, batch
        if tok.size and (tok.min() < 0 or tok.max() >= n_tokens):
            raise ValueError(f"{parquet.name}: gene token outside gene_metadata")
        if integer_counts and ex.size and not np.array_equal(ex, np.round(ex)):
            integer_counts = False
        lens = np.diff(off)
        c_all = col[tok]                      # axis column of every stored count, -1 off the axis
        is_ntc = ok & (tgt == NTC)
        is_tgt = ok & (tgt != NTC)
        cells_pass += int(ok.sum())
        cells_ntc += int(is_ntc.sum())
        if is_ntc.any():
            el = np.repeat(is_ntc, lens)
            m = el & (c_all >= 0)
            counts["ntc_sums"] += np.bincount(c_all[m], weights=ex[m], minlength=G)
            counts["ntc_named"] += ex[el if all_named else el & named[tok]].sum(dtype=np.float64)
            counts["ntc_cells"] += int(is_ntc.sum())
            counts["ntc_umis"] += umi[is_ntc].sum()
            del el, m
        if is_tgt.any():
            rows = np.flatnonzero(is_tgt)
            names_u, inv = np.unique(tgt[rows], return_inverse=True)
            inv = inv.ravel()
            ridx = reg.ids(names_u.tolist())
            grow(counts, len(reg.names))
            nu = names_u.size
            counts["cells"][ridx] += np.bincount(inv, minlength=nu)
            counts["umis"][ridx] += np.bincount(inv, weights=umi[rows], minlength=nu)
            local = np.full(n, -1, dtype=np.int64)
            local[rows] = inv
            le = np.repeat(local, lens)
            m = le >= 0
            if not all_named:
                m &= named[tok]
            counts["named"][ridx] += np.bincount(le[m], weights=ex[m], minlength=nu)
            m &= c_all >= 0
            block = np.bincount(le[m] * G + c_all[m], weights=ex[m], minlength=nu * G).reshape(nu, G)
            del le, m
            pool.add(ridx, block)
            del block
            in_file.update(names_u.tolist())
    pool.close()
    save_counts(work, k, counts)
    return {"rows": rows_seen, "pass_cells": cells_pass, "ntc_cells": cells_ntc, "targets": len(in_file),
            "integer_counts": integer_counts, "flushes": pool.flushes, "decode_s": round(decode_s, 1),
            "disk_s": round(pool.seconds, 1), "samples": sorted(samples)}


def recover(work: Path, journal: dict) -> None:
    """Zero every pool a crash left dirty; its files are then applied again from the start."""
    changed = False
    for k, p in journal["pools"].items():
        if p["dirty"] is None:
            continue
        log(f"pool {k} was left dirty by {p['dirty']}: zeroed, its {len(p['applied'])} committed files "
            f"will be applied again")
        arr, cnt = pool_paths(work, int(k))
        if arr.exists():
            with open(arr, "r+b") as fh:
                fh.truncate(0)
        if cnt.exists():
            _retry(cnt.unlink)
        journal["rebuilds"].append({"pool": int(k), "utc": now(), "dirty_file": p["dirty"],
                                    "reapplied": list(p["applied"])})
        p["applied"], p["dirty"] = [], None
        changed = True
    if changed:
        save_json(work / "journal.json", journal)


def parity_102(parquet: Path, name: str, k: int, work: Path, reg: Registry, col: np.ndarray,
               named: np.ndarray, G: int, line: str) -> dict:
    """Pilot: this file's panel sums, cells and UMIs against stage 102's own `process_file`.

    Valid only while pool ``k`` holds this one file. Also compares stage 102's stored part of
    the same file, written on 22-23 September.
    """
    panel = pd.read_csv(PANEL_CSV).iloc[:, 0].astype(str).tolist()
    groups = panel + [NTC]
    index = {t: i for i, t in enumerate(groups)}
    t0 = time.monotonic()
    sums, cells, umis, _ = stage102.process_file(parquet, index, col.size)
    seconds = time.monotonic() - t0
    counts = load_counts(work, k, len(reg.names), G)
    tok_of = np.full(G, -1, dtype=np.int64)
    tok_of[col[col >= 0]] = np.flatnonzero(col >= 0)
    on = tok_of >= 0
    found = [t for t in panel if t in reg.index]
    absent = [index[t] for t in panel if t not in reg.index]
    ridx = np.array([reg.index[t] for t in found], dtype=np.int64)
    gi = np.array([index[t] for t in found], dtype=np.int64)
    mine = read_rows(pool_paths(work, k)[0], ridx, G).astype(np.float64)

    def compare(ref_sums, ref_cells, ref_umis) -> dict:
        return {"cells_equal": bool(np.array_equal(counts["cells"][ridx], ref_cells[gi])
                                    and not np.asarray(ref_cells)[absent].any()),
                "max_abs_umis": float(np.abs(counts["umis"][ridx] - ref_umis[gi]).max()),
                "max_abs_counts_on_axis": float(np.abs(mine[:, on] - ref_sums[gi][:, tok_of[on]]).max()),
                "max_abs_library": float(np.abs(counts["named"][ridx] - ref_sums[gi][:, named].sum(1)).max()),
                "ntc_cells_equal": int(counts["ntc_cells"][0]) == int(ref_cells[-1]),
                "max_abs_ntc_on_axis": float(np.abs(counts["ntc_sums"][on] - ref_sums[-1, tok_of[on]]).max()),
                "abs_ntc_library": float(abs(counts["ntc_named"][0] - ref_sums[-1, named].sum()))}

    out = {"panel_targets_in_file": int((cells[:-1] > 0).sum()), "panel_targets_registered": len(found),
           "stage102_process_file_seconds": round(seconds, 1),
           "vs_process_file": compare(sums, cells, umis)}
    del sums
    part = DATA / "interim" / f"orion_{line.lower()}" / f"part_{name}.npz"
    if part.exists():
        with np.load(part) as z:
            out["vs_stage102_part"] = {"path": str(part), **compare(z["sums"].astype(np.float64), z["cells"],
                                                                     z["umis"])}
    return out


def stream(line: str, work: Path, *, max_files: int | None = None, max_new: int | None = None, threads: int = 8,
           batch_rows: int = 512, buffer_mib: int = 256, parity: bool = False) -> bool:
    """Apply the line's files not yet applied (at most ``max_new`` of them). True when all are in.

    ``max_new`` exists because reading parquet leaves a few MB of committed memory behind per
    call (measured on 26 September: about 3 MB per call of a 6 MB file, about 50 MB per file of
    the stream), so `chain` runs the stream in segments, each in a fresh process.
    """
    work.mkdir(parents=True, exist_ok=True)
    with Lock(work):
        files = file_list(line, work)
        tokens = stage102.gene_tokens(work)
        axis = np.asarray(official_axis().symbols)
        G = axis.size
        col, named = token_columns(tokens, axis)
        slots = max(batch_rows, int(buffer_mib * 2**20 // (G * 4)))
        jpath = work / "journal.json"
        journal = load_json(jpath) if jpath.exists() else {
            "line": line, "created_utc": now(), "axis_genes": G, "pools": {
                str(k): {"applied": [], "dirty": None} for k in range(N_POOLS)}, "files": {}, "rebuilds": []}
        recover(work, journal)
        reg = Registry(work)
        applied = {n for p in journal["pools"].values() for n in p["applied"]}
        todo = files[:max_files] if max_files else files
        log(f"{line}: {len(files)} files, {sum(f['bytes'] for f in files) / 1e9:.1f} GB; {len(applied)} applied; "
            f"{len(reg.names)} targets registered; {int(np.sum(col >= 0))} gene tokens on the axis; "
            f"buffer {slots} rows")
        t0 = time.monotonic()
        done = 0
        for f in todo:
            if f["name"] in applied:
                continue
            if max_new is not None and done >= max_new:
                break
            k = f["pool"]
            dl = work / f"{f['name']}.parquet.download"
            t1 = time.monotonic()
            digest = fetch(f, dl, threads)
            t2 = time.monotonic()
            journal["pools"][str(k)]["dirty"] = f["name"]
            save_json(jpath, journal)
            stats = apply_file(dl, k, work, reg, col, named, G, batch_rows, slots)
            reg.save()
            t3 = time.monotonic()
            journal["pools"][str(k)]["applied"].append(f["name"])
            journal["pools"][str(k)]["dirty"] = None
            entry = {"pool": k, "bytes": f["bytes"], "sha256": digest, "applied_utc": now(),
                     "download_s": round(t2 - t1, 1), "apply_s": round(t3 - t2, 1), **stats,
                     "registry": len(reg.names), **memory()}
            journal["files"][f["name"]] = entry
            save_json(jpath, journal)
            applied.add(f["name"])
            if parity:
                if journal["pools"][str(k)]["applied"] == [f["name"]]:
                    entry["parity_102"] = parity_102(dl, f["name"], k, work, reg, col, named, G, line)
                    save_json(jpath, journal)
                    log(f"  parity with stage 102: {json.dumps(entry['parity_102'])}")
                else:
                    log("  parity with stage 102 skipped: the pool holds other files too")
            _retry(dl.unlink)
            done += 1
            log(f"  {f['name']} -> pool {k}: {f['bytes'] / 2**20:.0f} MiB, download {entry['download_s']:.0f}s, "
                f"apply {entry['apply_s']:.0f}s (decode {stats['decode_s']:.0f}s, disk {stats['disk_s']:.0f}s); "
                f"{stats['pass_cells']} pass cells ({stats['ntc_cells']} NTC), "
                f"{stats['targets']} targets, registry {len(reg.names)}; peak ws {entry.get('peak_ws_mib')} MiB, "
                f"peak private {entry.get('peak_private_mib')} MiB; {len(applied)}/{len(files)} files, "
                f"{time.monotonic() - t0:.0f}s this run")
        complete = all(f["name"] in applied for f in files)
        log(f"{line}: {len(applied)}/{len(files)} files applied ({done} this run); complete: {complete}")
        return complete


# ----------------------------------------------------------------------------- finalize

def estimate(sub: list[str], rid: dict, work: Path, counts: list[dict], cells: np.ndarray, genes: np.ndarray,
             axis: np.ndarray, line: str, name: str, min_cells: float):
    """Stage 98's estimate for ``sub``: `effects_from_pseudobulk` on (pool, target) rows, then the axis."""
    import scipy.sparse as sp

    from vcc2026.multisource import AxisTable, effects_from_pseudobulk
    G = axis.size
    ridx = np.array([rid[t] for t in sub], dtype=np.int64)
    blocks, obs = [], []
    for k in range(N_POOLS):
        have = cells[k, ridx] > 0
        if have.any():
            rows = read_rows(pool_paths(work, k)[0], ridx[have], G).astype(np.float64)
            off_axis = counts[k]["named"][ridx[have]] - rows.sum(axis=1)
            if (off_axis < -0.5).any():
                raise ValueError(f"pool {k}: library smaller than the counts on the axis")
            blocks.append(sp.csr_matrix(np.hstack([rows, off_axis[:, None]])))
            obs += [{"target": t, "donor": f"pool{k}", "condition": line, "n_cells": float(c)}
                    for t, c in zip(np.asarray(sub, dtype=object)[have], cells[k, ridx[have]])]
        if counts[k]["ntc_cells"][0] > 0:
            ntc = np.append(counts[k]["ntc_sums"], counts[k]["ntc_named"][0] - counts[k]["ntc_sums"].sum())
            blocks.append(sp.csr_matrix(ntc[None, :]))
            obs.append({"target": "non-targeting", "donor": f"pool{k}", "condition": line,
                        "n_cells": float(counts[k]["ntc_cells"][0])})
    X = sp.vstack(blocks, format="csr")
    src = effects_from_pseudobulk(X, pd.DataFrame(obs), genes, targets=list(sub), condition=None,
                                  min_cells=min_cells)
    return AxisTable.from_source(name, src, axis)


def compare_tables(ref: dict, mine: dict) -> dict:
    """Parity of two {target: {raw, se, shrunk, n_cells}} tables on their shared targets."""
    shared = [t for t in ref if t in mine]
    out = {"targets_ref": len(ref), "targets_mine": len(mine), "shared": len(shared),
           "only_ref": sorted(set(ref) - set(mine)), "only_mine": sorted(set(mine) - set(ref))}
    if not shared:
        return out
    out["n_cells_equal"] = int(sum(int(ref[t]["n_cells"]) == int(mine[t]["n_cells"]) for t in shared))
    for key in ("raw", "se", "shrunk"):
        a = np.vstack([ref[t][key] for t in shared]).astype(np.float64)
        b = np.vstack([mine[t][key] for t in shared]).astype(np.float64)
        fa, fb = np.isfinite(a), np.isfinite(b)
        both = fa & fb
        d = np.abs(a[both] - b[both])
        out[key] = {"finite_ref": int(fa.sum()), "finite_mine": int(fb.sum()),
                    "finite_mask_mismatches": int((fa != fb).sum()),
                    "max_abs_diff": float(d.max()) if d.size else None,
                    "entries_differing": int((d > 0).sum())}
    return out


def table_rows(path: Path, targets=None) -> dict:
    with np.load(path, allow_pickle=False) as z:
        names = [str(t) for t in z["targets"]]
        keep = [i for i, t in enumerate(names) if targets is None or t in targets]
        raw, se, shr, nc = z["raw"], z["se"], z["shrunk"], z["n_cells"]
        return {names[i]: {"raw": raw[i], "se": se[i], "shrunk": shr[i], "n_cells": int(nc[i])} for i in keep}


def check_parts(line: str, work: Path, names: list[str], tokens: pd.DataFrame, axis: np.ndarray,
                min_cells: float, mine: dict, name: str) -> dict:
    """Pilot: stage 102's own --finalize on its stored parts of the same files, then stage 98's estimate."""
    import anndata as ad

    from vcc2026.multisource import AxisTable, effects_from_pseudobulk
    src_dir = DATA / "interim" / f"orion_{line.lower()}"
    tmp = work / f"check_stage102_min{min_cells:g}"
    tmp.mkdir(exist_ok=False)
    for n in names:
        shutil.copy2(src_dir / f"part_{n}.npz", tmp / f"part_{n}.npz")
    panel = pd.read_csv(PANEL_CSV).iloc[:, 0].astype(str).tolist()
    ns = SimpleNamespace(work=tmp, pools=N_POOLS, out=tmp / "rows.h5ad", report_dir=tmp, line=line)
    stage102.finalize(ns, panel + [NTC], tokens)
    rows = ad.read_h5ad(ns.out)
    obs = rows.obs[["target", "donor", "condition", "n_cells"]].copy()
    src = effects_from_pseudobulk(rows.X, obs, rows.var_names, targets=panel, condition=None, min_cells=min_cells)
    tab = AxisTable.from_source(name, src, axis)
    ref = {t: {"raw": tab.raw[i], "se": tab.se[i], "shrunk": tab.shrunk[i], "n_cells": int(tab.n_cells[i])}
           for i, t in enumerate(tab.targets)}
    return {"what": "stage 102 --finalize on its 22-23 Sep parts of the same files, then stage 98's estimator",
            "parts": names, "min_cells": min_cells, **compare_tables(ref, mine)}


def finalize(line: str, work: Path, out: Path, report: Path, *, allow_partial: bool = False,
             min_cells: float = 10.0, panel_cache: Path | None = PANEL_CACHE, pilot_check: bool = False) -> dict:
    """Chunks of stage-98 effects for every target of the line, index, manifest and parity."""
    t0 = time.monotonic()
    holder = lock_holder(work)
    if holder is not None:
        raise SystemExit(f"process {holder} is still streaming {line}")
    files = load_json(work / "files.json")["files"]
    journal = load_json(work / "journal.json")
    dirty = {k: p["dirty"] for k, p in journal["pools"].items() if p["dirty"]}
    applied = {n: int(k) for k, p in journal["pools"].items() for n in p["applied"]}
    missing = [f["name"] for f in files if f["name"] not in applied]
    wrong = [f["name"] for f in files if f["name"] in applied and applied[f["name"]] != f["pool"]]
    if dirty or wrong or (missing and not allow_partial):
        raise SystemExit(f"{line}: not ready: dirty {dirty}, wrong pool {wrong}, missing {len(missing)} files")
    reg = Registry(work).names
    axis = np.asarray(official_axis().symbols)
    G = axis.size
    genes = np.append(axis, "__off_axis__")
    counts = [load_counts(work, k, len(reg), G) for k in range(N_POOLS)]
    cells = np.stack([c["cells"] for c in counts])
    name = f"orion_{line.lower()}"
    panel = set(pd.read_csv(PANEL_CSV).iloc[:, 0].astype(str))
    on_axis = set(axis)
    rid = {t: i for i, t in enumerate(reg)}
    targets = sorted(reg)
    if report.exists():
        raise FileExistsError(f"{report} exists; a new finalize goes to a new --report")
    out.mkdir(parents=True, exist_ok=False)
    chunks, meta, where, n_cells = [], None, {}, {}
    mine_panel = {}
    pend = {"targets": [], "shrunk": [], "raw": [], "se": [], "n_cells": []}

    def emit(final: bool) -> None:
        """Write chunks of exactly CHUNK targets with effects (the last one shorter)."""
        T = pend["targets"]
        if not T or (len(T) < CHUNK and not final):
            return
        arrs = {key: np.vstack(pend[key]) for key in ("shrunk", "raw", "se")}
        arrs["n_cells"] = np.concatenate(pend["n_cells"])
        while len(T) >= CHUNK or (final and T):
            m = min(CHUNK, len(T))
            path = out / f"{name}_{len(chunks):02d}.npz"
            chunk_meta = {**meta, "source": f"X-Atlas/Orion {line}", "min_cells": min_cells,
                          "estimator": "vcc2026.multisource.effects_from_pseudobulk, pools of GEM batches as donors",
                          "licence": "CC-BY-NC-SA-4.0"}
            np.savez_compressed(path, targets=np.array(T[:m]), shrunk=arrs["shrunk"][:m], raw=arrs["raw"][:m],
                                se=arrs["se"][:m], n_cells=arrs["n_cells"][:m],
                                meta=json.dumps(chunk_meta, default=str))
            chunks.append({"file": path.name, "targets": m, "bytes": path.stat().st_size,
                           "sha256": sha256_file(path)})
            where.update({t: path.name for t in T[:m]})
            log(f"  {path.name}: {m} targets, {len(where)} so far, {time.monotonic() - t0:.0f}s")
            T = T[m:]
            arrs = {key: v[m:] for key, v in arrs.items()}
        pend.update({"targets": list(T), "n_cells": [arrs["n_cells"]],
                     **{key: [arrs[key]] for key in ("shrunk", "raw", "se")}})

    for s in range(0, len(targets), SUB):
        tab = estimate(targets[s:s + SUB], rid, work, counts, cells, genes, axis, line, name, min_cells)
        meta = tab.meta
        pend["targets"] += list(tab.targets)
        for key in ("shrunk", "raw", "se"):
            pend[key].append(getattr(tab, key))
        pend["n_cells"].append(np.asarray(tab.n_cells))
        for i, t in enumerate(tab.targets):
            n_cells[t] = int(tab.n_cells[i])
            if t in panel:
                mine_panel[t] = {"raw": tab.raw[i].copy(), "se": tab.se[i].copy(),
                                 "shrunk": tab.shrunk[i].copy(), "n_cells": int(tab.n_cells[i])}
        del tab
        emit(final=False)
    emit(final=True)
    idx = pd.DataFrame([{"target": t, "chunk": where.get(t, ""), "n_cells": n_cells.get(t, 0),
                         "cells_total": int(cells[:, rid[t]].sum()),
                         "pools_with_cells": int((cells[:, rid[t]] > 0).sum()),
                         "pools_min_cells": int((cells[:, rid[t]] >= min_cells).sum()),
                         "in_panel": t in panel, "on_official_axis": t in on_axis} for t in targets])
    idx.to_csv(out / "index.csv", index=False)
    with_fx = idx[idx["chunk"] != ""]
    parity = {}
    if panel_cache is not None and not missing and (panel_cache / f"{name}.npz").exists():
        parity["r5_panel_cache"] = {"path": str(panel_cache / f"{name}.npz"),
                                    **compare_tables(table_rows(panel_cache / f"{name}.npz"), mine_panel)}
    if pilot_check:
        parity["stage102_parts"] = check_parts(line, work, sorted(applied), stage102.gene_tokens(work), axis,
                                               min_cells, mine_panel, name)
    ref102 = REPO / "reports" / "orion_2026-09-23" / f"manifest_{line}.json"
    pools = {f"pool{k}": sorted(n for n, kk in applied.items() if kk == k) for k in range(N_POOLS)}
    pools_match = None
    if ref102.exists() and not missing:
        theirs = load_json(ref102)["pools"]
        pools_match = all(sorted(theirs.get(p, [])) == m for p, m in pools.items() if m)
    fl = journal["files"]
    stream_s = sum(fl[n]["download_s"] + fl[n]["apply_s"] for n in applied if n in fl)
    summary = {"files_applied": len(applied), "files_listed": len(files),
               "bytes_streamed": int(sum(f["bytes"] for f in files if f["name"] in applied)),
               "targets_with_cells": int(len(idx)), "targets_with_effects": int(len(with_fx)),
               "targets_without_effects": int(len(idx) - len(with_fx)),
               "in_panel_with_cells": int(idx["in_panel"].sum()), "in_panel_with_effects": int(with_fx["in_panel"].sum()),
               "on_official_axis_with_effects": int(with_fx["on_official_axis"].sum()),
               "median_cells_total": float(idx["cells_total"].median()),
               "median_n_cells_with_effects": float(with_fx["n_cells"].median()) if len(with_fx) else None,
               "cells_pass_filter": int(sum(fl[n]["pass_cells"] for n in applied if n in fl)),
               "rows_read": int(sum(fl[n]["rows"] for n in applied if n in fl)),
               "ntc_cells_per_pool": [int(c["ntc_cells"][0]) for c in counts],
               "ntc_cells": int(sum(int(c["ntc_cells"][0]) for c in counts)),
               "all_counts_integer": all(fl[n].get("integer_counts", False) for n in applied if n in fl),
               "stream_seconds": round(stream_s, 1),
               "peak_ws_mib_stream": max((fl[n].get("peak_ws_mib", 0) for n in applied if n in fl), default=None),
               "peak_private_mib_stream": max((fl[n].get("peak_private_mib", 0) for n in applied if n in fl),
                                              default=None),
               "pool_rebuilds": len(journal["rebuilds"]),
               "finalize_seconds": round(time.monotonic() - t0, 1), "finalize_memory": memory(),
               "chunk_bytes": int(sum(ch["bytes"] for ch in chunks))}
    manifest = {"stage": "universo_2026-09-26/orion_universe.py", "written_utc": now(), "line": line,
                "source": {"repo": stage102.REPO, "licence": "CC-BY-NC-SA-4.0",
                           "filter": "pass_guide_filter == 1", "gene_metadata_sha256":
                               sha256_file(work / "gene_metadata.parquet")},
                "work": str(work), "out": str(out), "chunk_size": CHUNK,
                "estimator": {"function": "vcc2026.multisource.effects_from_pseudobulk", "phi": 0.2, "pseudo": 0.5,
                              "min_cells_per_pool": min_cells, "donors": "8 pools of GEM batches (file index mod 8)",
                              "axis": "AxisTable.from_source, control fraction >= 1e-6"},
                "partial": bool(missing), "files": [{**f, "applied": f["name"] in applied} for f in files],
                "pools": pools, "pools_match_stage102_manifest": pools_match,
                "chunks": chunks, "summary": summary, "parity": parity,
                "claim_type": "effect tables (ln fold change, quasi-Poisson SE, z-shrinkage) as stage 98's Orion "
                              "sources, for every target with a pool of >= min_cells cells"}
    report.mkdir(parents=True, exist_ok=False)
    for dest in (out / "manifest.json", report / "manifest.json"):
        with dest.open("x", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=1, default=str)
    idx.to_csv(report / "index.csv", index=False)
    log(f"finalized {line}: {summary['targets_with_effects']}/{summary['targets_with_cells']} targets with effects, "
        f"{len(chunks)} chunks, {summary['chunk_bytes'] / 1e6:.0f} MB, {summary['finalize_seconds']:.0f}s")
    log(f"parity: {json.dumps(parity, default=str)[:2000]}")
    return manifest


# ----------------------------------------------------------------------------- status and CLI

def status(line: str, work: Path) -> None:
    if not (work / "journal.json").exists():
        print(f"{line}: nothing streamed in {work}")
        return
    files = load_json(work / "files.json")["files"]
    j = load_json(work / "journal.json")
    applied = [n for p in j["pools"].values() for n in p["applied"]]
    fl = [j["files"][n] for n in applied if n in j["files"]]
    last = max(fl, key=lambda e: e["applied_utc"]) if fl else None
    print(json.dumps({"line": line, "work": str(work), "files_applied": len(applied), "files_listed": len(files),
                      "gb_applied": round(sum(e["bytes"] for e in fl) / 1e9, 2),
                      "gb_listed": round(sum(f["bytes"] for f in files) / 1e9, 2),
                      "dirty": {k: p["dirty"] for k, p in j["pools"].items() if p["dirty"]},
                      "rebuilds": len(j["rebuilds"]), "lock_holder_alive": lock_holder(work),
                      "targets_registered": len(load_json(work / "targets.json")) if (work / "targets.json").exists()
                      else 0, "last_applied_utc": last and last["applied_utc"],
                      "seconds_so_far": round(sum(e["download_s"] + e["apply_s"] for e in fl)),
                      "max_peak_ws_mib": max((e.get("peak_ws_mib", 0) for e in fl), default=None),
                      "max_peak_private_mib": max((e.get("peak_private_mib", 0) for e in fl), default=None)},
                     indent=1))


def segmented(line: str, work: Path | None, segment: int = 10) -> int:
    """The stream of one line in fresh processes of ``segment`` files each; 0 once complete.

    What a plain ``--line X`` stream runs: the chain launched on 26 September at 18:43 calls it
    that way, and a single process would keep what pyarrow leaves behind for a whole line.
    """
    import subprocess
    cmd = [sys.executable, "-u", str(Path(__file__).resolve()), "--line", line, "--max-new-files", str(segment)]
    if work is not None:
        cmd += ["--work", str(work)]
    while True:
        rc = subprocess.call(cmd)
        if rc != 3:
            return rc


def chain(lines: list[str], min_cells: float, segment: int = 10, tries: int = 3) -> None:
    """Stream then finalize each line in turn. Every step is a fresh process, so it runs this
    script as it is when the step starts. The stream goes in segments of ``segment`` files (exit
    code 3: more to do), which keeps the memory pyarrow leaves behind bounded; a stream that fails
    is resumed from its journal after ten minutes, up to ``tries`` failures per line."""
    import subprocess
    me = [sys.executable, "-u", str(Path(__file__).resolve())]
    for line in lines:
        failures = 0
        while True:
            log(f"chain: stream {line}, next {segment} files")
            rc = subprocess.call(me + ["--line", line, "--max-new-files", str(segment)])
            if rc == 0:
                break
            if rc == 3:
                continue
            failures += 1
            log(f"chain: stream {line} exited with {rc} (failure {failures} of {tries})")
            if failures >= tries:
                log(f"chain: {line} is not complete; the chain stops")
                return
            time.sleep(600)
        if (defaults(line).out / "manifest.json").exists():
            log(f"chain: {line} is already finalized in {defaults(line).out}")
            continue
        rc = subprocess.call(me + ["--line", line, "--finalize", "--min-cells", f"{min_cells:g}"])
        log(f"chain: finalize {line} exited with {rc}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--line", nargs="+", choices=["HCT116", "HEK293T"], required=True)
    ap.add_argument("--work", type=Path, default=None, help="one line only; default <data_root>/interim/...")
    ap.add_argument("--out", type=Path, default=None, help="--finalize, one line only")
    ap.add_argument("--report", type=Path, default=None, help="--finalize, one line only")
    ap.add_argument("--finalize", action="store_true")
    ap.add_argument("--chain", action="store_true", help="stream then finalize each --line, in turn")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--max-files", type=int, default=None, help="pilot: the first N files of the list")
    ap.add_argument("--max-new-files", type=int, default=None, help="stop after applying N files (exit 3)")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--batch-rows", type=int, default=512)
    ap.add_argument("--buffer-mib", type=int, default=256)
    ap.add_argument("--parity-102", action="store_true", help="pilot: compare each file with stage 102")
    ap.add_argument("--allow-partial", action="store_true", help="pilot: finalize before every file is in")
    ap.add_argument("--min-cells", type=float, default=10.0, help="estimator's cells per pool (10 = stage 98)")
    ap.add_argument("--pilot-check", action="store_true", help="--finalize: compare with stage 102 on its parts")
    args = ap.parse_args()
    if len(args.line) > 1 and (args.work or args.out or args.report):
        raise SystemExit("--work, --out and --report take one --line")
    if args.chain:
        chain(args.line, args.min_cells)
        return
    complete = True
    for line in args.line:
        d = defaults(line)
        work, out, report = args.work or d.work, args.out or d.out, args.report or d.report
        if args.status:
            status(line, work)
        elif args.finalize:
            finalize(line, work, out, report, allow_partial=args.allow_partial, min_cells=args.min_cells,
                     pilot_check=args.pilot_check)
        elif args.max_new_files is None and args.max_files is None and not args.parity_102:
            rc = segmented(line, args.work)
            if rc != 0:
                sys.exit(rc)
        else:
            complete &= stream(line, work, max_files=args.max_files, max_new=args.max_new_files,
                               threads=args.threads, batch_rows=args.batch_rows, buffer_mib=args.buffer_mib,
                               parity=args.parity_102)
    sys.exit(0 if complete else 3)   # 3: the stream stopped before the line's last file (e.g. --max-files)


if __name__ == "__main__":
    main()
