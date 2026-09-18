"""Read a dense, contiguous single-cell h5ad in one sequential pass.

The Replogle K562 genome-wide raw single-cell file is 65,830,941,948 bytes. The
Colab download of 2026-09-15 recorded an md5 equal to the catalog's
(`MyDrive/vcc2026/data/raw/replogle/K562_gwps_raw_singlecell_01.h5ad.fetch.json`),
but no run has read its contents: that run's QC step failed on a code error
before opening it. Its byte count is identical to its
normalized twin's, which is what a dense float32 matrix of fixed shape would
give, and the pseudobulk file from the same release stores X as a contiguous,
uncompressed dataset at byte offset 2048. If the single-cell file has the same
layout, a single front-to-back read of the file can do three jobs at once:

* recompute the file's md5 on the bytes actually read (CP-0018 forbids using
  the Drive copy unless it matches the catalog);
* accumulate per-perturbation sufficient statistics for every row;
* copy the cells of selected perturbations into a sparse file small enough to
  work with.

Everything here refuses to guess. `dense_layout` raises unless X is a
contiguous, uncompressed float32 dataset, in which case row ``i`` lives at
``offset + i * n_vars * 4`` and the raw bytes *are* the matrix.

Nothing in this module needs anndata to read: the object was written by an
anndata 0.7-era writer (``__categories`` subgroups), which `read_frame`
decodes directly with h5py, together with the newer categorical layout.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

__all__ = [
    "DenseLayout",
    "GroupAccumulator",
    "CsrAppendWriter",
    "dense_layout",
    "read_frame",
    "stream_dense_rows",
]

_H5D_CONTIGUOUS = 1


def _decode(values: np.ndarray) -> np.ndarray:
    if values.dtype.kind in ("S", "O"):
        return np.array(
            [v.decode("utf-8") if isinstance(v, (bytes, np.bytes_)) else str(v) for v in values],
            dtype=object,
        )
    return values


def read_frame(group: h5py.Group) -> pd.DataFrame:
    """Decode an anndata dataframe group (0.7 ``__categories`` or >=0.8 layout)."""
    attrs = group.attrs
    index_key = attrs.get("_index", "_index")
    if isinstance(index_key, bytes):
        index_key = index_key.decode()
    old_cats = group["__categories"] if "__categories" in group else None
    order = [c.decode() if isinstance(c, bytes) else str(c) for c in attrs.get("column-order", [])]
    names = order or [k for k in group.keys() if k not in (index_key, "__categories")]
    cols: dict[str, object] = {}
    for name in names:
        node = group[name]
        if isinstance(node, h5py.Group):  # >=0.8 categorical: codes + categories
            codes = node["codes"][:]
            cats = _decode(node["categories"][:])
            cols[name] = pd.Categorical.from_codes(codes, categories=pd.Index(cats))
            continue
        values = node[:]
        if old_cats is not None and name in old_cats:
            cats = _decode(old_cats[name][:])
            cols[name] = pd.Categorical.from_codes(values.astype(np.int64), categories=pd.Index(cats))
        else:
            cols[name] = _decode(values)
    index_node = group[index_key]
    if isinstance(index_node, h5py.Group):  # nullable-string layout
        index = _decode(index_node["values"][:])
    else:
        index = _decode(index_node[:])
    return pd.DataFrame(cols, index=pd.Index(index, name=None))


@dataclass(frozen=True)
class DenseLayout:
    path: str
    n_obs: int
    n_vars: int
    offset: int
    itemsize: int
    file_size: int

    @property
    def row_nbytes(self) -> int:
        return self.n_vars * self.itemsize

    @property
    def x_end(self) -> int:
        return self.offset + self.n_obs * self.row_nbytes

    def as_dict(self) -> dict:
        return asdict(self) | {"row_nbytes": self.row_nbytes, "x_end": self.x_end}


def dense_layout(path: str | Path) -> DenseLayout:
    """Byte layout of a dense X, or a ValueError naming what is different."""
    path = Path(path)
    with h5py.File(path, "r") as f:
        x = f["X"]
        if not isinstance(x, h5py.Dataset):
            raise ValueError(f"{path}: X is a {type(x).__name__}, not a dense dataset")
        if x.dtype != np.dtype("<f4"):
            raise ValueError(f"{path}: X dtype is {x.dtype}, expected little-endian float32")
        layout = x.id.get_create_plist().get_layout()
        if layout != _H5D_CONTIGUOUS or x.compression is not None or x.chunks is not None:
            raise ValueError(
                f"{path}: X is not contiguous and uncompressed "
                f"(layout={layout}, chunks={x.chunks}, compression={x.compression})"
            )
        offset = x.id.get_offset()
        if offset is None:
            raise ValueError(f"{path}: X has no storage offset (never written?)")
        n_obs, n_vars = (int(s) for s in x.shape)
        storage = int(x.id.get_storage_size())
        if storage != n_obs * n_vars * 4:
            raise ValueError(f"{path}: X storage {storage} != {n_obs}*{n_vars}*4")
    size = path.stat().st_size
    out = DenseLayout(str(path), n_obs, n_vars, int(offset), 4, int(size))
    if out.x_end > size:
        raise ValueError(f"{path}: X region ends at {out.x_end}, past the file size {size}")
    return out


def stream_dense_rows(
    layout: DenseLayout,
    *,
    block_bytes: int = 256 * 1024**2,
    md5: bool = True,
    start_row: int = 0,
    stop_row: int | None = None,
    progress_every_s: float = 60.0,
    log=print,
    result: dict | None = None,
):
    """Yield ``(first_row, rows_as_float32_array)`` in file order.

    With ``md5=True`` the whole file is read front to back (``start_row`` must be 0
    and ``stop_row`` unset) and the digest lands in ``result`` once the generator is
    exhausted, with ``bytes_read`` and timing. With ``md5=False`` reading covers
    ``[start_row, stop_row)``, which is how an interrupted pass resumes.

    The yielded array is a view on a reused buffer: copy what must outlive the step.
    """
    if md5 and stop_row is not None:
        raise ValueError("an md5 pass has to read the whole file")
    stop = layout.n_obs if stop_row is None else min(int(stop_row), layout.n_obs)
    if md5 and start_row:
        raise ValueError("an md5 pass has to start at row 0")
    row_nb = layout.row_nbytes
    per_block = max(1, block_bytes // row_nb)
    digest = hashlib.md5() if md5 else None
    t0 = last = time.time()
    done = 0
    with open(layout.path, "rb", buffering=0) as fh:
        if md5:
            head = fh.read(layout.offset)
            digest.update(head)
            done += len(head)
        else:
            fh.seek(layout.offset + start_row * row_nb)
        buf = bytearray(per_block * row_nb)
        row = start_row
        while row < stop:
            n = min(per_block, stop - row)
            view = memoryview(buf)[: n * row_nb]
            got = 0
            while got < view.nbytes:
                k = fh.readinto(view[got:])
                if not k:
                    raise IOError(f"short read at row {row}: {got} of {view.nbytes} bytes")
                got += k
            if digest is not None:
                digest.update(view)
            done += got
            rows = np.frombuffer(view, dtype="<f4").reshape(n, layout.n_vars)
            yield row, rows
            row += n
            now = time.time()
            if now - last >= progress_every_s:
                rate = done / max(now - t0, 1e-9) / 1024**2
                log(f"  row {row:,}/{layout.n_obs:,}  {done / 1024**3:.1f} GiB  {rate:.0f} MiB/s")
                last = now
        if digest is not None:
            while True:
                tail = fh.read(64 * 1024**2)
                if not tail:
                    break
                digest.update(tail)
                done += len(tail)
    elapsed = time.time() - t0
    if result is not None:
        result.update({
            "md5": digest.hexdigest() if digest is not None else None,
            "bytes_read": done,
            "rows": [start_row, stop],
            "seconds": elapsed,
            "mib_per_s": done / max(elapsed, 1e-9) / 1024**2,
        })


class GroupAccumulator:
    """Per-group sums of counts and of per-cell library-normalized counts.

    ``frac_sq_sums[g]`` gives the between-cell variance of those fractions, hence a
    standard error for every group without keeping its cells.
    ``sums[g]`` is the pseudobulk count sum, the quantity the scorer's
    ``bulk_lognorm`` comparator starts from. ``frac_sums[g]`` is the sum over
    cells of ``x / L``, whose mean is the per-cell-normalize-then-average
    functional the DE log2FC uses. The two differ exactly by the depth-composition
    covariance (cell_eval2 #286), so both are kept.
    """

    def __init__(self, n_groups: int, n_vars: int) -> None:
        self.sums = np.zeros((n_groups, n_vars), dtype=np.float64)
        self.frac_sums = np.zeros((n_groups, n_vars), dtype=np.float64)
        self.frac_sq_sums = np.zeros((n_groups, n_vars), dtype=np.float64)
        self.detect = np.zeros((n_groups, n_vars), dtype=np.int32)
        self.n_cells = np.zeros(n_groups, dtype=np.int64)
        self.lib_sum = np.zeros(n_groups, dtype=np.float64)
        self.lib_sq_sum = np.zeros(n_groups, dtype=np.float64)

    def add(self, codes: np.ndarray, rows: np.ndarray) -> None:
        kernel = _numba_kernel()
        if kernel is not None:
            kernel(np.ascontiguousarray(codes, dtype=np.int64), np.ascontiguousarray(rows, dtype=np.float32),
                   self.sums, self.frac_sums, self.frac_sq_sums, self.detect,
                   self.n_cells, self.lib_sum, self.lib_sq_sum)
            return
        self._add_numpy(codes, rows)

    def _add_numpy(self, codes: np.ndarray, rows: np.ndarray) -> None:
        """Reference path, ~20x slower than the numba kernel at a 256-MiB block."""
        order = np.argsort(codes, kind="stable")
        sc = codes[order]
        uniq, starts = np.unique(sc, return_index=True)
        block = rows[order]
        lib = block.sum(axis=1, dtype=np.float64)
        safe = np.where(lib > 0, lib, 1.0)
        self.sums[uniq] += np.add.reduceat(block, starts, axis=0, dtype=np.float64)
        frac = block / safe[:, None].astype(np.float32)
        self.frac_sums[uniq] += np.add.reduceat(frac, starts, axis=0, dtype=np.float64)
        np.multiply(frac, frac, out=frac)
        self.frac_sq_sums[uniq] += np.add.reduceat(frac, starts, axis=0, dtype=np.float64)
        self.detect[uniq] += np.add.reduceat((block > 0).astype(np.int32), starts, axis=0)
        self.n_cells[uniq] += np.diff(np.append(starts, sc.size))
        self.lib_sum[uniq] += np.add.reduceat(lib, starts)
        self.lib_sq_sum[uniq] += np.add.reduceat(lib * lib, starts)

    def save(self, out: Path, *, rows_done: int) -> None:
        out.mkdir(parents=True, exist_ok=True)
        tmp = out / "accumulator.tmp.npz"
        np.savez(
            tmp, sums=self.sums, frac_sums=self.frac_sums, frac_sq_sums=self.frac_sq_sums,
            detect=self.detect,
            n_cells=self.n_cells, lib_sum=self.lib_sum, lib_sq_sum=self.lib_sq_sum,
            rows_done=np.array([rows_done]),
        )
        tmp.replace(out / "accumulator.npz")

    @classmethod
    def load(cls, path: Path) -> tuple["GroupAccumulator", int]:
        z = np.load(path)
        acc = cls(*z["sums"].shape)
        for k in ("sums", "frac_sums", "frac_sq_sums", "detect", "n_cells", "lib_sum", "lib_sq_sum"):
            getattr(acc, k)[...] = z[k]
        return acc, int(z["rows_done"][0])


_KERNEL = None


def _numba_kernel():
    """A compiled row loop, or None when numba is unavailable (scanpy pulls it in)."""
    global _KERNEL
    if _KERNEL is not None:
        return _KERNEL or None
    try:
        from numba import njit
    except ImportError:
        _KERNEL = False
        return None

    @njit(cache=False, nogil=True)
    def kernel(codes, block, sums, frac_sums, frac_sq, detect, n_cells, lib_sum, lib_sq):
        n_rows, n_vars = block.shape
        for i in range(n_rows):
            c = codes[i]
            lib = 0.0
            for j in range(n_vars):
                lib += block[i, j]
            inv = 1.0 / lib if lib > 0.0 else 1.0
            for j in range(n_vars):
                v = block[i, j]
                if v != 0.0:
                    sums[c, j] += v
                    f = v * inv
                    frac_sums[c, j] += f
                    frac_sq[c, j] += f * f
                    detect[c, j] += 1
            n_cells[c] += 1
            lib_sum[c] += lib
            lib_sq[c] += lib * lib

    _KERNEL = kernel
    return kernel


class CsrAppendWriter:
    """Append sparse count rows to an .h5ad; obs is written from a frame at close."""

    def __init__(self, path: str | Path, var: pd.DataFrame, *, compression: str | None = "gzip") -> None:
        self.path = Path(path)
        self.var = var
        self._f = h5py.File(self.path, "w")
        self._f.attrs["encoding-type"] = "anndata"
        self._f.attrs["encoding-version"] = "0.1.0"
        x = self._f.create_group("X")
        x.attrs["encoding-type"] = "csr_matrix"
        x.attrs["encoding-version"] = "0.1.0"
        kw = {"chunks": (1 << 20,), "maxshape": (None,)}
        if compression:
            kw |= {"compression": compression, "compression_opts": 4}
        self._data = x.create_dataset("data", shape=(0,), dtype=np.float32, **kw)
        self._indices = x.create_dataset("indices", shape=(0,), dtype=np.int32, **kw)
        self._indptr = [np.zeros(1, dtype=np.int64)]
        self._nnz = 0
        self.n_obs = 0

    def add(self, rows: np.ndarray) -> None:
        if rows.shape[0] == 0:
            return
        m = sp.csr_matrix(rows)
        m.eliminate_zeros()
        m.sort_indices()
        n = m.data.size
        self._data.resize((self._nnz + n,))
        self._data[self._nnz:] = m.data.astype(np.float32, copy=False)
        self._indices.resize((self._nnz + n,))
        self._indices[self._nnz:] = m.indices.astype(np.int32, copy=False)
        self._indptr.append(m.indptr[1:].astype(np.int64) + self._nnz)
        self._nnz += n
        self.n_obs += rows.shape[0]

    def close(self, obs: pd.DataFrame) -> None:
        from anndata.io import write_elem

        if len(obs) != self.n_obs:
            raise ValueError(f"obs has {len(obs)} rows, writer holds {self.n_obs}")
        try:
            indptr = np.concatenate(self._indptr)
            dtype = np.int32 if self._nnz <= np.iinfo(np.int32).max else np.int64
            self._f["X"].attrs["shape"] = np.array([self.n_obs, len(self.var)], dtype=np.int64)
            self._f["X"].create_dataset("indptr", data=indptr.astype(dtype), chunks=True)
            write_elem(self._f, "obs", obs)
            write_elem(self._f, "var", self.var)
            for empty in ("layers", "obsm", "varm", "obsp", "varp", "uns"):
                write_elem(self._f, empty, {})
        finally:
            self._f.close()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
