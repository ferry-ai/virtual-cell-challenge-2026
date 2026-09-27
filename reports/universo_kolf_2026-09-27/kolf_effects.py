"""F1 of R-V2, KOLF2.1J: effects of EVERY target of the KOLF2.1J CRISPRi screen, from kolf_sums.py's sums.

kolf_sums.py (this folder) streams the screen's raw counts (Figshare+ 27261219,
KOLF_Pan_Genome_QC_Filtered.h5ad; controls ``NTC``) into one ``sums.npz``: for every group (target,
pool), pool = channel code modulo 8, the counts of its cells summed on each gene of the official axis
(NaN on the axis genes the file lacks), its cells, and their total UMIs over ALL genes of the file. This
turns the sums into effects as orion_universe.py (reports/universo_2026-09-26/) turns Orion's: for each
block of 600 targets, in sorted order, one pseudobulk row per (target, pool) plus the NTC row of every
pool, with the counts on the axis genes the file has and ONE extra column holding the rest of the row's
library (total_counts minus its counts on the axis), so that every library size is the cells' own; then
`effects_from_pseudobulk`, each pool against its own controls (a pool with fewer than 10 cells of a
target is skipped; ``min_expected`` 1.0, the corrected estimator of 27 September), and
`AxisTable.from_source` onto the axis. Axis genes the file lacks are no column: they come out NaN,
unmeasured, never zero. A target without a pool of 10 cells has no effect row.

The matrix (groups x axis genes, float32, Fortran order) is never loaded whole. ``sums.npy`` is stored in the
archive uncompressed, so it is mapped with `np.memmap` at the byte where its data start (after the
member's local zip header and its NPY header), a window of genes at a time: in Fortran order each gene's
column is contiguous, and only the rows of a block's groups are read from it. A first pass reads the
whole archive in order: it checks the matrix (finite and >= 0 on the genes of the file, NaN on the
others), sums each group's counts on the axis for its off-axis column, and hashes the archive. Every
block read back must agree with those sums. A block's rows are held as dense float32 (at most 600
targets x 8 pools + 8 control rows, by 17,971 genes of the file: 346 MB) and handed on as float64 CSR.

Writes to a NEW --out: ``kolf_NN.npz`` for block NN, in stage 98's format (targets, shrunk, raw, se,
n_cells, meta; the block's targets with effects), ``index.csv`` (every target with cells: its chunk file,
empty without effects, its cells and pools) and, last, ``manifest.json`` (the archive's sha256 and its
groups_sha256, the estimator and its options, counts, the chunks' bytes and sha256): a folder without it
is an interrupted run. --report, if given, gets copies of index.csv and manifest.json. Nothing is
overwritten.

    scripts/py.cmd reports/universo_kolf_2026-09-27/kolf_effects.py --selftest
    scripts/py.cmd reports/universo_kolf_2026-09-27/kolf_effects.py --sums <dir>/sums.npz \
        --out <data_root>/processed/universe_kolf_2026-09-27_me1 --report reports/universo_kolf_2026-09-27/effetti_me1

--selftest writes a small synthetic sums.npz with kolf_sums.py's own functions (so the archive has the
real format), runs the pipeline on it in a temporary folder and prints one line per check; exit 1 if one
fails.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import inspect
import io
import json
import struct
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE))

import kolf_sums  # noqa: E402
from vcc2026 import config  # noqa: E402
from vcc2026.bench import log  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.multisource import AxisTable, effects_from_pseudobulk  # noqa: E402
from vcc2026.resources import peak_rss_bytes  # noqa: E402

DATA = config.paths().data_root
NAME = "kolf"                    # AxisTable name and chunk prefix
LINE = "KOLF2.1J"
NTC = "NTC"                      # the screen's controls: a target of their own in kolf_sums.py's groups
CONTROL = "non-targeting"        # what effects_from_pseudobulk calls them
OFF_AXIS = "__off_axis__"        # the extra column, as orion_universe.py; not on the axis, so dropped there
N_POOLS = 8
CHUNK = 600                      # targets per block and per chunk file, as the K562 universe
WINDOW = 256                     # axis genes per memory map: 95 MB for the 92,636 groups of the merge
MIN_CELLS = 10.0                 # target cells per pool, as stage 98
MIN_EXPECTED = 1.0               # the corrected estimator (reports/pseudoconteggio_2026-09-27/)
SOURCE = "KOLF2.1J CRISPRi screen, Figshare+ 27261219, KOLF_Pan_Genome_QC_Filtered.h5ad"   # file and licence
LICENCE = "CC-BY-4.0"            # as reports/ricerca_sorgenti_2026-09-27/RISULTATI.md records them
PANEL_CSV = DATA / "raw" / "controls" / "pert_counts.csv"
KEYS = ("target", "pool", "n_cells", "total_counts", "genes", "file_columns", "missing_genes", "groups_sha256",
        "url")                   # what kolf_sums.merge writes beside the matrix, the member sums.npy
LOCAL_HEADER = struct.Struct("<4s2B4HL2L2H")   # zip local file header; the name and the extra field follow
ESTIMATOR_DEFAULTS = {k: p.default for k, p in inspect.signature(effects_from_pseudobulk).parameters.items()
                      if p.default is not inspect.Parameter.empty}
RARE, PLANTED = "G07", ("G05", "G05", 0.25)    # selftest: a gene under 1 expected count; target, gene, fold


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path, block: int = 16 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(block):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------------- the sums, mapped

def npy_member(path: Path, name: str) -> tuple[int, tuple, bool, np.dtype]:
    """Byte where an uncompressed NPY member's array data start in its archive, and its shape, order and
    dtype: the directory gives the member's local header, whose name and extra field precede the NPY
    header, which precedes the data."""
    with zipfile.ZipFile(path) as z:
        info = z.getinfo(name)
    if info.compress_type != zipfile.ZIP_STORED:
        raise ValueError(f"{path}: {name} is compressed and cannot be mapped")
    with open(path, "rb") as fh:
        fh.seek(info.header_offset)
        head = LOCAL_HEADER.unpack(fh.read(LOCAL_HEADER.size))
        if head[0] != b"PK\x03\x04" or head[4] != zipfile.ZIP_STORED or fh.read(head[10]) != name.encode():
            raise ValueError(f"{path}: the local header of {name} is not where the directory says")
        start = info.header_offset + LOCAL_HEADER.size + head[10] + head[11]
        fh.seek(start)
        shape, fortran, dtype = kolf_sums._header(fh)
        data = fh.tell()
    nbytes = dtype.itemsize * int(np.prod(shape))
    if info.file_size != data - start + nbytes or Path(path).stat().st_size < data + nbytes:
        raise ValueError(f"{path}: {name} holds {info.file_size} bytes, its NPY header {data - start + nbytes}")
    return data, shape, fortran, dtype


class Sums:
    """kolf_sums.py's merged sums.npz: the group table in memory, the matrix mapped a window of genes at a time."""

    def __init__(self, path: Path):
        self.path = Path(path)
        with np.load(self.path, allow_pickle=False) as z:    # members are read one by one: never sums.npy
            lacking = [k for k in (*KEYS, "sums") if k not in z.files]
            if lacking:
                raise ValueError(f"{self.path}: not a kolf_sums.py merge, it lacks {lacking}")
            self.target = z["target"].astype(str)
            self.pool = z["pool"].astype(np.int64)
            self.n_cells = z["n_cells"].astype(np.int64)
            self.total = z["total_counts"].astype(np.float64)
            self.genes = z["genes"].astype(str)
            self.file_columns = z["file_columns"].astype(np.int64)
            missing = z["missing_genes"].astype(str)
            self.groups_sha256, self.url = str(z["groups_sha256"]), str(z["url"])
        self.ng, self.na = self.target.size, self.genes.size
        self.present = np.flatnonzero(self.file_columns >= 0)     # axis positions of the genes the file has
        if (not (self.pool.size == self.n_cells.size == self.total.size == self.ng)
                or self.file_columns.size != self.na):
            raise ValueError(f"{self.path}: group or gene arrays of different lengths")
        if len(set(self.genes.tolist())) != self.na:
            raise ValueError(f"{self.path}: the gene axis repeats a symbol")
        if sorted(missing.tolist()) != sorted(self.genes[self.file_columns < 0].tolist()):
            raise ValueError(f"{self.path}: missing_genes disagrees with file_columns")
        if not np.isin(self.pool, np.arange(N_POOLS)).all():
            raise ValueError(f"{self.path}: a pool outside 0..{N_POOLS - 1}")
        if (self.n_cells < 1).any() or not (np.isfinite(self.total) & (self.total > 0)).all():
            raise ValueError(f"{self.path}: a group without cells or without counts")
        if len(set(zip(self.target.tolist(), self.pool.tolist()))) != self.ng:
            raise ValueError(f"{self.path}: two groups share a target and a pool")
        self.data_offset, shape, fortran, dtype = npy_member(self.path, "sums.npy")
        if shape != (self.ng, self.na) or not fortran or dtype != np.dtype("<f4"):
            raise ValueError(f"{self.path}: sums.npy is {shape} {dtype} (Fortran order {fortran}), not "
                             f"({self.ng}, {self.na}) <f4 in Fortran order")

    def window(self, a: int, b: int) -> np.memmap:
        """Axis genes a..b-1 as a (b - a, groups) array: in Fortran order they are one contiguous stretch."""
        return np.memmap(self.path, dtype="<f4", mode="r", offset=self.data_offset + 4 * self.ng * a,
                         shape=(b - a, self.ng), order="C")

    def gather(self, rows: np.ndarray, cols: np.ndarray, window: int = WINDOW) -> np.ndarray:
        """The matrix at ``rows`` x ``cols`` (sorted axis positions), float32. Each window is unmapped once
        read, and in each gene's column only the rows asked for are touched."""
        out = np.empty((rows.size, cols.size), dtype=np.float32)
        for a in range(0, self.na, window):
            b = min(self.na, a + window)
            j0, j1 = np.searchsorted(cols, [a, b])
            if j1 > j0:
                blk = self.window(a, b)
                out[:, j0:j1] = blk[np.ix_(cols[j0:j1] - a, rows)].T
                del blk
        return out

    def scan(self, window: int = WINDOW) -> tuple[np.ndarray, bool, str]:
        """One pass over the whole archive, in order: each group's counts on the axis (float64), whether
        every sum is a whole number, and the archive's sha256. Refuses a sum that is negative or not
        finite on a gene of the file, and a value other than NaN on an axis gene the file lacks."""
        h = hashlib.sha256()
        with open(self.path, "rb") as fh:
            h.update(fh.read(self.data_offset))
        has = self.file_columns >= 0
        on_axis, whole = np.zeros(self.ng), True
        for a in range(0, self.na, window):
            b = min(self.na, a + window)
            blk = self.window(a, b)
            h.update(blk.reshape(-1))          # consecutive windows: together, the matrix's bytes (1-D for hashlib)
            here = has[a:b]
            if here.any():
                vals = blk[np.flatnonzero(here)]
                lo, hi = vals.min(), vals.max()
                if not (np.isfinite(lo) and np.isfinite(hi) and lo >= 0):
                    raise ValueError(f"axis genes {a}..{b - 1}: a sum is negative or not finite")
                on_axis += vals.sum(axis=0, dtype=np.float64)
                whole = whole and bool(np.array_equal(vals, np.floor(vals)))
                del vals
            if not here.all() and not np.isnan(blk[np.flatnonzero(~here)]).all():
                raise ValueError(f"axis genes {a}..{b - 1}: a gene the file lacks is not NaN")
            del blk
        with open(self.path, "rb") as fh:
            fh.seek(self.data_offset + 4 * self.ng * self.na)
            h.update(fh.read())
        return on_axis, whole, h.hexdigest()


def pseudobulk(s: Sums, rows: np.ndarray, on_axis: np.ndarray, off: np.ndarray, window: int) -> sp.csr_matrix:
    """The estimator's input for ``rows``: their counts on the axis genes of the file, then one column with
    the rest of each row's library, so that every row sums to its total_counts. Float64 CSR, built row by
    row: no index arrays the size of the dense block."""
    dense = s.gather(rows, s.present, window)
    if not np.allclose(dense.sum(axis=1, dtype=np.float64), on_axis[rows], rtol=1e-9, atol=1e-6):
        raise ValueError("rows read back disagree with the scan: the matrix was not read where it lies")
    G = s.present.size
    extra = off[rows]
    nnz = np.count_nonzero(dense, axis=1) + (extra > 0)
    indptr = np.zeros(rows.size + 1, dtype=np.int64)
    np.cumsum(nnz, out=indptr[1:])
    indices = np.empty(int(indptr[-1]), dtype=np.int32)
    data = np.empty(int(indptr[-1]), dtype=np.float64)
    for i in range(rows.size):
        nz = np.flatnonzero(dense[i])
        a = int(indptr[i])
        b = a + nz.size
        indices[a:b] = nz
        data[a:b] = dense[i, nz]
        if extra[i] > 0:
            indices[b] = G
            data[b] = extra[i]
    del dense
    return sp.csr_matrix((data, indices, indptr), shape=(rows.size, G + 1))


# ----------------------------------------------------------------------------- effects

def run(sums_path: Path, out: Path, *, report: Path | None = None, panel: Path | None = None,
        chunk: int = CHUNK, min_cells: float = MIN_CELLS, min_expected: float = MIN_EXPECTED,
        official: bool = True, window: int = WINDOW) -> dict:
    """Effects of every target of ``sums_path``: chunk files, index.csv and, last, manifest.json in the new
    folder ``out``. ``official`` checks the sums' genes against the official axis when it is available."""
    t0 = time.monotonic()
    sums_path, out = Path(sums_path), Path(out)
    for p in (out, report):
        if p is not None and Path(p).exists():
            raise FileExistsError(f"{p} exists; a new run goes to a new folder")
    if chunk < 1 or window < 1:
        raise ValueError("chunk and window must be positive")
    s = Sums(sums_path)
    axis = s.genes
    matches = None
    if official:
        try:
            matches = bool(np.array_equal(np.asarray(official_axis().symbols), axis))
        except FileNotFoundError as exc:
            log(f"official axis not found ({exc}); the axis of {sums_path.name} is not checked")
        if matches is False:
            raise ValueError(f"{sums_path}: its genes are not the official axis")
    target, pool, n_cells, total = s.target, s.pool, s.n_cells, s.total
    if (target == CONTROL).any():
        raise ValueError(f"a target is named {CONTROL!r}, the estimator's name for the controls")
    order = np.argsort(target, kind="stable")
    names, first = np.unique(target[order], return_index=True)
    edges = np.append(first, s.ng)
    rows_of = {str(t): order[edges[i]:edges[i + 1]] for i, t in enumerate(names)}
    ctrl = rows_of.pop(NTC, None)
    if ctrl is None or not rows_of:
        raise ValueError(f"{sums_path}: no {NTC} group, or no target")
    targets = sorted(rows_of)
    ntc_cells = np.bincount(pool[ctrl], weights=n_cells[ctrl], minlength=N_POOLS).astype(np.int64)
    log(f"{sums_path.name}: {s.ng} groups, {len(targets)} targets, {NTC} cells per pool {ntc_cells.tolist()}; "
        f"{s.present.size} of {s.na} axis genes in the file; matrix data at byte {s.data_offset}")
    if (ntc_cells == 0).any():
        log(f"  pools without {NTC} cells: {np.flatnonzero(ntc_cells == 0).tolist()}; the estimator skips "
            f"their rows")

    t1 = time.monotonic()
    on_axis, whole, digest = s.scan(window)
    off = total - on_axis
    short = off < -(1.0 + 1e-6 * total)      # float32 sums of the largest groups may round up a few counts
    if short.any():
        i = int(np.argmin(off / total))
        raise ValueError(f"{int(short.sum())} groups count more on the axis than their total_counts, e.g. "
                         f"{target[i]} pool {pool[i]}: {on_axis[i]:.0f} > {total[i]:.0f}")
    clipped = int((off < 0).sum())
    off = np.maximum(off, 0.0)
    share = on_axis / total
    scan_s = time.monotonic() - t1
    log(f"scan {scan_s:.0f}s: share of the library on the axis {share.min():.3f}..{share.max():.3f} "
        f"(median {np.median(share):.3f}); whole sums {whole}; sha256 {digest[:16]}")

    panel_set = set(pd.read_csv(panel).iloc[:, 0].astype(str)) if panel is not None else None
    axis_set = set(axis.tolist())
    out.mkdir(parents=True, exist_ok=False)
    genes = np.append(axis[s.present], OFF_AXIS)
    options = {**ESTIMATOR_DEFAULTS, "condition": None, "min_cells": min_cells, "min_expected": min_expected}
    chunks, where, n_eff = [], {}, {}
    for c, start in enumerate(range(0, len(targets), chunk)):
        part = targets[start:start + chunk]
        rows = np.sort(np.concatenate([rows_of[t] for t in part] + [ctrl]))
        X = pseudobulk(s, rows, on_axis, off, window)
        obs = pd.DataFrame({"target": np.where(target[rows] == NTC, CONTROL, target[rows]),
                            "donor": [f"pool{k}" for k in pool[rows].tolist()], "condition": LINE,
                            "n_cells": n_cells[rows].astype(np.float64)})
        src = effects_from_pseudobulk(X, obs, genes, targets=part, condition=None, min_cells=min_cells,
                                      min_expected=min_expected)
        del X
        tab = AxisTable.from_source(NAME, src, axis)
        del src
        path = out / f"{NAME}_{c:02d}.npz"
        chunk_meta = {**tab.meta, "source": SOURCE, "url": s.url, "groups_sha256": s.groups_sha256,
                      "min_cells": min_cells, "licence": LICENCE,
                      "estimator": "vcc2026.multisource.effects_from_pseudobulk, pools of channels as donors, "
                                   "one off-axis column per row"}
        np.savez_compressed(path, targets=np.asarray(tab.targets, dtype=str), shrunk=tab.shrunk, raw=tab.raw,
                            se=tab.se, n_cells=np.asarray(tab.n_cells), meta=json.dumps(chunk_meta, default=str))
        chunks.append({"file": path.name, "targets_in_block": len(part), "targets": len(tab.targets),
                       "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        where.update({t: path.name for t in tab.targets})
        n_eff.update({t: int(n) for t, n in zip(tab.targets, tab.n_cells)})
        log(f"  {path.name}: {len(tab.targets)} of {len(part)} targets with effects, {rows.size} rows, "
            f"{time.monotonic() - t0:.0f}s")
        del tab

    records = []
    for t in targets:
        r = rows_of[t]
        rec = {"target": t, "chunk": where.get(t, ""), "n_cells": n_eff.get(t, 0),
               "cells_total": int(n_cells[r].sum()), "pools_with_cells": int(r.size),
               "pools_min_cells": int((n_cells[r] >= min_cells).sum())}
        if panel_set is not None:
            rec["in_panel"] = t in panel_set
        rec["on_official_axis"] = t in axis_set
        records.append(rec)
    idx = pd.DataFrame(records)
    idx.to_csv(out / "index.csv", index=False)
    with_fx = idx[idx["chunk"] != ""]
    peak = peak_rss_bytes()
    summary = {"groups": s.ng, "targets_with_cells": int(len(idx)), "targets_with_effects": int(len(with_fx)),
               "targets_without_effects": int(len(idx) - len(with_fx)),
               "on_official_axis_with_effects": int(with_fx["on_official_axis"].sum()),
               **({"in_panel_with_cells": int(idx["in_panel"].sum()),
                   "in_panel_with_effects": int(with_fx["in_panel"].sum())} if panel_set is not None else {}),
               "median_cells_total": float(idx["cells_total"].median()),
               "median_n_cells_with_effects": float(with_fx["n_cells"].median()) if len(with_fx) else None,
               "cells": int(n_cells.sum()), "ntc_cells": int(ntc_cells.sum()),
               "ntc_cells_per_pool": ntc_cells.tolist(), "genes_on_axis": s.na,
               "genes_in_file": int(s.present.size), "genes_absent_nan": int(s.na - s.present.size),
               "all_sums_whole": bool(whole),
               "library_share_on_axis": {"min": float(share.min()), "median": float(np.median(share)),
                                         "max": float(share.max())},
               "groups_off_axis_clipped_to_0": clipped, "seconds_scan": round(scan_s, 1),
               "seconds": round(time.monotonic() - t0, 1),
               "peak_working_set_mib": round(peak / 2**20) if peak else None,
               "chunk_bytes": int(sum(ch["bytes"] for ch in chunks))}
    manifest = {"stage": "universo_kolf_2026-09-27/kolf_effects.py", "written_utc": now(), "name": NAME,
                "line": LINE, "source": {"what": SOURCE, "url": s.url, "licence": LICENCE},
                "input": {"sums": str(sums_path), "bytes": int(sums_path.stat().st_size), "sha256": digest,
                          "groups_sha256": s.groups_sha256,
                          "matrix": {"member": "sums.npy", "data_offset": int(s.data_offset), "shape": [s.ng, s.na],
                                     "dtype": "<f4", "order": "F"},
                          "axis_matches_official": matches},
                "out": str(out), "chunk_size": chunk, "window_genes": window,
                "estimator": {"function": "vcc2026.multisource.effects_from_pseudobulk", "options": options,
                              "donors": f"{N_POOLS} pools of channels (channel code mod {N_POOLS}, kolf_sums.py), "
                                        f"each against its own {NTC} cells",
                              "library": "each row's total_counts over all genes of the file: its counts on the "
                                         "axis genes of the file plus one column with the rest",
                              "axis": "AxisTable.from_source, control fraction >= 1e-6; axis genes the file "
                                      "lacks are NaN"},
                "chunks": chunks, "summary": summary,
                "claim_type": "effect tables (ln fold change, quasi-Poisson SE, z-shrinkage) with the corrected "
                              "estimator, for every KOLF2.1J target with a pool of >= min_cells cells; no claim "
                              "on their use as a source"}
    with (out / "manifest.json").open("x", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, default=str)
    if report is not None:
        report = Path(report)
        report.mkdir(parents=True, exist_ok=False)
        with (report / "manifest.json").open("x", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=1, default=str)
        idx.to_csv(report / "index.csv", index=False)
    log(f"{NAME}: {summary['targets_with_effects']} of {summary['targets_with_cells']} targets with effects in "
        f"{len(chunks)} chunks, {summary['chunk_bytes'] / 1e6:.0f} MB, {summary['seconds']:.0f}s, peak working "
        f"set {summary['peak_working_set_mib']} MiB")
    return manifest


# ----------------------------------------------------------------------------- selftest

def _synthetic() -> tuple[dict, np.ndarray]:
    """What a small sums.npz holds: 40 axis genes, three the file lacks (NaN) and a rare one, the controls
    and seven targets in 8 pools, groups in shuffled order. Counts are rounded expectations with 70% of
    every library on the axis; target G05 knocks its own gene down to a quarter."""
    rng = np.random.default_rng(2026)
    axis = np.array([f"G{j:02d}" for j in range(40)])
    columns = np.arange(axis.size, dtype=np.int64)
    columns[[3, 17, 31]] = -1
    rare = int(np.flatnonzero(axis == RARE)[0])
    frac = np.where(columns >= 0, rng.uniform(0.5, 1.5, axis.size), 0.0)
    frac[rare] = 0.0
    frac *= 0.7 / frac.sum()
    frac[rare] = 1e-5                  # 8 counts in each control row, 0.2-0.6 expected in a target's
    cells = {NTC: [400] * 8, "G05": [30] * 8, "T_A": [20] * 8, "T_B": [15] * 8,
             "T_C": [18, 0, 22, 0, 30, 0, 11, 0], "T_FEW": [4, 0, 9, 0, 0, 7, 0, 0],
             "T_MIX": [12] * 4 + [6] * 4, "T_NULL": [25] * 8}
    groups = [(t, k, n) for t, per in cells.items() for k, n in enumerate(per) if n]
    groups = [groups[i] for i in rng.permutation(len(groups))]
    target = np.array([t for t, _, _ in groups])
    n_cells = np.array([n for _, _, n in groups], dtype=np.int64)
    total = n_cells * 2000.0
    fold = np.ones((len(groups), axis.size))
    fold[target == PLANTED[0], int(np.flatnonzero(axis == PLANTED[1])[0])] = PLANTED[2]
    sums = np.rint(total[:, None] * frac[None, :] * fold).astype(np.float32)
    sums[:, columns < 0] = np.nan
    table = {"target": target, "pool": np.array([k for _, k, _ in groups], dtype=np.int8), "n_cells": n_cells,
             "total_counts": total, "genes": axis, "file_columns": columns, "missing_genes": axis[columns < 0],
             "groups_sha256": hashlib.sha256(b"kolf_effects.py selftest").hexdigest(),
             "url": "https://synthetic.invalid/kolf.h5ad"}
    return table, sums


def _publish_sums(path: Path, table: dict, sums: np.ndarray) -> Path:
    """Write ``table`` and the matrix as kolf_sums.merge does: its disk-backed NPY, then its `_publish`."""
    matrix = path.with_name(path.stem + ".matrix.npy")
    offset = kolf_sums._matrix_file(matrix, sums.shape)
    kolf_sums._write_columns(matrix, offset, 0, sums)
    kolf_sums._publish(path, table, matrix)
    matrix.unlink()
    return path


def _reference(table: dict, sums: np.ndarray, min_expected: float) -> AxisTable:
    """The estimator called once on the whole in-memory matrix, off-axis column included."""
    have = table["file_columns"] >= 0
    on = sums[:, have].astype(np.float64)
    X = sp.csr_matrix(np.hstack([on, (table["total_counts"] - on.sum(axis=1))[:, None]]))
    target = table["target"]
    obs = pd.DataFrame({"target": np.where(target == NTC, CONTROL, target),
                        "donor": [f"pool{k}" for k in table["pool"].tolist()], "condition": LINE,
                        "n_cells": table["n_cells"].astype(np.float64)})
    src = effects_from_pseudobulk(X, obs, np.append(table["genes"][have], OFF_AXIS),
                                  targets=sorted(set(target.tolist()) - {NTC}), condition=None,
                                  min_cells=MIN_CELLS, min_expected=min_expected)
    return AxisTable.from_source(NAME, src, table["genes"])


def _read_run(out: Path) -> dict:
    """{target: raw, se, shrunk, n_cells and file} over the chunk files of a run."""
    found = {}
    for path in sorted(out.glob(f"{NAME}_*.npz")):
        with np.load(path, allow_pickle=False) as z:
            names, raw, se, shrunk, cells = z["targets"].astype(str), z["raw"], z["se"], z["shrunk"], z["n_cells"]
        for i, t in enumerate(names.tolist()):
            found[t] = {"raw": raw[i], "se": se[i], "shrunk": shrunk[i], "n_cells": int(cells[i]), "file": path.name}
    return found


def _diff(a: dict, b: dict, keys=("raw", "se", "shrunk"), shift: float = 0.0) -> float:
    """Largest |a - b - shift| over entries finite in both; inf when they are finite in different places."""
    worst = 0.0
    for k in keys:
        fa, fb = np.isfinite(a[k]), np.isfinite(b[k])
        if not np.array_equal(fa, fb):
            return np.inf
        if fa.any():
            worst = max(worst, float(np.max(np.abs(a[k][fa].astype(np.float64) - b[k][fa] - shift))))
    return worst


def selftest() -> int:
    """The pipeline on a synthetic sums.npz written by kolf_sums.py's own functions; one line per check."""
    results: list[bool] = []

    def check(name: str, ok, detail: str) -> None:
        results.append(bool(ok))
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}", flush=True)

    def quiet(path: Path, out: Path) -> dict:
        with contextlib.redirect_stdout(io.StringIO()):
            return run(path, out, chunk=3, window=7, official=False)

    table, sums = _synthetic()
    axis = table["genes"]
    col = {g: i for i, g in enumerate(axis.tolist())}
    with tempfile.TemporaryDirectory(prefix="kolf-effects-selftest-", ignore_cleanup_errors=True) as where:
        tmp = Path(where)
        base = _publish_sums(tmp / "sums.npz", table, sums)
        with np.load(base, allow_pickle=False) as z:
            stored = z["sums"]
        s = Sums(base)
        same = [np.array_equal(s.gather(np.arange(s.ng), np.arange(s.na), w), stored, equal_nan=True)
                for w in (1, 7, WINDOW)]
        check("memmap", np.array_equal(stored, sums, equal_nan=True) and all(same),
              f"sums.npy mapped at byte {s.data_offset} of {base.stat().st_size}; windows of 1, 7 and {WINDOW} "
              f"genes read what np.load reads, {s.ng} groups x {s.na} genes")
        del s

        quiet(base, tmp / "base")
        got = _read_run(tmp / "base")
        t, g, fold = PLANTED
        j = col[g]
        row = got.get(t, {"raw": np.full(axis.size, np.nan, np.float32), "shrunk": np.full(axis.size, np.nan)})
        rest = np.abs(np.delete(row["raw"], j))
        rest = float(rest[np.isfinite(rest)].max()) if np.isfinite(rest).any() else np.inf
        check("planted knockdown", t in got and np.isfinite(row["raw"]).any()
              and abs(row["raw"][j] - np.log(fold)) < 0.02 and abs(row["shrunk"][j] - np.log(fold)) < 0.03
              and int(np.nanargmin(row["raw"])) == j and rest < 0.05,
              f"{t} on {g}: raw {row['raw'][j]:.4f}, shrunk {row['shrunk'][j]:.4f}, planted ln {fold} = "
              f"{np.log(fold):.4f}; its other genes |raw| <= {rest:.4f}")
        others = [float(r["raw"][j]) for u, r in got.items() if u != t]
        leak = float(np.max(np.abs(others))) if others else np.inf
        check("knockdown only in its target", leak < 0.05,
              f"{g} in the other {len(others)} targets: |raw| <= {leak:.4f}")

        absent = np.flatnonzero(table["file_columns"] < 0)
        measured = np.setdiff1d(np.flatnonzero(table["file_columns"] >= 0), [col[RARE]])
        keys = ("raw", "se", "shrunk")
        check("absent genes", all(np.isnan(r[k][absent]).all() and np.isfinite(r[k][measured]).all()
                                  for r in got.values() for k in keys),
              f"{axis[absent].tolist()}, absent from the file, are NaN in raw, se and shrunk for all {len(got)} "
              f"targets; the other {measured.size} genes of the file, {RARE} aside, are finite")

        ref0 = _reference(table, sums, 0.0)
        low = ref0.raw[:, col[RARE]]
        check("min_expected", all(np.isnan(r["raw"][col[RARE]]) for r in got.values())
              and len(ref0.targets) == len(got) and np.isfinite(low).all(),
              f"{RARE}, 0.2-0.6 expected counts per target group: NaN in every target with min_expected "
              f"{MIN_EXPECTED:g}; with 0 it reads {np.nanmin(low):.2f} to {np.nanmax(low):.2f}, the constant "
              f"pseudocount's induction")

        idx = pd.read_csv(tmp / "base" / "index.csv").set_index("target")
        few = idx.loc["T_FEW"] if "T_FEW" in idx.index else None
        check("no pool of 10 cells", few is not None and "T_FEW" not in got and pd.isna(few["chunk"])
              and few["n_cells"] == 0 and few["cells_total"] == 20 and few["pools_with_cells"] == 3
              and few["pools_min_cells"] == 0,
              "T_FEW (4, 9 and 7 cells in three pools) has no effect row; index.csv lists it with an empty "
              "chunk, 20 cells, 3 pools")
        n_mix, n_c = got.get("T_MIX", {}).get("n_cells"), got.get("T_C", {}).get("n_cells")
        check("pools under 10 cells skipped", n_mix == 48 and n_c == 81,
              f"T_MIX (12 cells in four pools, 6 in four) counts {n_mix} cells, 48 expected; T_C (18, 22, 30 and "
              f"11) {n_c}, 81 expected")

        ref = _reference(table, sums, MIN_EXPECTED)
        want = {u: {"raw": ref.raw[i], "se": ref.se[i], "shrunk": ref.shrunk[i], "n_cells": int(ref.n_cells[i])}
                for i, u in enumerate(ref.targets)}
        alike = set(want) == set(got) and all(got[u]["n_cells"] == want[u]["n_cells"] for u in want)
        worst = max(_diff(got[u], want[u]) for u in want) if alike else np.inf
        check("parity with one direct call", alike and worst <= 1e-6,
              f"{len(got)} targets read from the chunk files against the estimator called once on the whole "
              f"in-memory matrix: same targets and cells, max |diff| {worst:.1e}")

        prop = _publish_sums(tmp / "sums_prop.npz", dict(table, total_counts=table["total_counts"] * 1.5), sums)
        quiet(prop, tmp / "prop")
        got_p = _read_run(tmp / "prop")
        worst = max(_diff(got_p[u], got[u]) for u in got) if set(got_p) == set(got) else np.inf
        check("library: off-axis counts in proportion", worst <= 1e-5,
              f"every row's total_counts x 1.5, controls included (off-axis counts added in proportion to each "
              f"total): no effect moves by more than {worst:.1e}")

        one = _publish_sums(tmp / "sums_one.npz", dict(
            table, total_counts=np.where(table["target"] == "T_A", 1.5, 1.0) * table["total_counts"]), sums)
        quiet(one, tmp / "one")
        got_o = _read_run(tmp / "one")
        if set(got_o) == set(got):
            moved = _diff(got_o["T_A"], got["T_A"], ("raw",), shift=-np.log(1.5))
            kept = max([_diff(got_o["T_A"], got["T_A"], ("se",))]
                       + [_diff(got_o[u], got[u]) for u in got if u != "T_A"])
        else:
            moved = kept = np.inf
        check("library: off-axis counts on one target", max(moved, kept) <= 1e-5,
              f"T_A's total_counts x 1.5 alone: all its raw effects move by -ln 1.5 = {-np.log(1.5):.4f} (max "
              f"error {moved:.1e}); its SE and the other targets stay (max {kept:.1e}); so the column is read")

        folder = tmp / "base"
        files = sorted(p.name for p in folder.glob(f"{NAME}_*.npz"))
        shape_ok = True
        for file in files:
            with np.load(folder / file, allow_pickle=False) as z:
                meta, n = json.loads(str(z["meta"])), z["targets"].size
                shape_ok = shape_ok and (
                    set(z.files) == {"targets", "shrunk", "raw", "se", "n_cells", "meta"}
                    and all(z[k].shape == (n, axis.size) and z[k].dtype == np.float32 for k in keys)
                    and z["n_cells"].shape == (n,) and meta.get("min_expected") == MIN_EXPECTED
                    and meta.get("donors") == [f"pool{k}" for k in range(N_POOLS)])
        man = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        sums_ok = [c["file"] for c in man["chunks"]] == files and all(
            c["sha256"] == sha256_file(folder / c["file"]) and c["bytes"] == (folder / c["file"]).stat().st_size
            for c in man["chunks"]) and man["input"]["sha256"] == sha256_file(base)
        index_ok = all(idx.loc[u, "chunk"] == r["file"] for u, r in got.items())
        counts_ok = (man["summary"]["targets_with_cells"] == 7 and man["summary"]["targets_with_effects"] == 6
                     and [c["targets"] for c in man["chunks"]] == [3, 2, 1])
        check("outputs", shape_ok and sums_ok and index_ok and counts_ok,
              f"{files}: six keys, float32 targets x {axis.size}, meta with min_expected {MIN_EXPECTED:g} and "
              f"{N_POOLS} pools; index.csv names each target's file; the manifest's sha256 (chunks and input "
              f"archive) and bytes match; 6 of 7 targets with effects, 3, 2 and 1 per block")

        before = sha256_file(folder / "manifest.json")
        try:
            quiet(base, folder)
            refused = False
        except FileExistsError:
            refused = True
        check("never overwrite", refused and sha256_file(folder / "manifest.json") == before,
              "a second run into the same --out is refused and leaves it as it was")
    failed = results.count(False)
    print(f"selftest: {len(results) - failed} of {len(results)} checks passed", flush=True)
    return 1 if failed else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sums", type=Path, help="sums.npz written by kolf_sums.py merge")
    ap.add_argument("--out", type=Path, help="a NEW folder for the chunks, index.csv and manifest.json")
    ap.add_argument("--report", type=Path, default=None, help="a NEW folder for copies of index.csv and manifest.json")
    ap.add_argument("--panel", type=Path, default=None,
                    help="panel targets in the first column, for index.csv's in_panel (default: the control "
                         "bundle's pert_counts.csv, when it exists)")
    ap.add_argument("--chunk", type=int, default=CHUNK, help="targets per block and per chunk file")
    ap.add_argument("--min-cells", type=float, default=MIN_CELLS, help="estimator's target cells per pool")
    ap.add_argument("--min-expected", type=float, default=MIN_EXPECTED,
                    help="estimator's expected counts per pool (0: the constant pseudocount alone)")
    ap.add_argument("--selftest", action="store_true",
                    help="a synthetic sums.npz through the pipeline; exit 1 on a failed check")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if args.sums is None or args.out is None:
        ap.error("--sums and --out are required, or --selftest")
    if args.panel is not None and not args.panel.exists():
        ap.error(f"--panel {args.panel} does not exist")
    panel = args.panel or (PANEL_CSV if PANEL_CSV.exists() else None)
    run(args.sums, args.out, report=args.report, panel=panel, chunk=args.chunk, min_cells=args.min_cells,
        min_expected=args.min_expected)


if __name__ == "__main__":
    main()
