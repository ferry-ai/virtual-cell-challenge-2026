"""Stream CSC raw counts into target/pool sums; no whole matrix downloads.

Put the project's src/ on PYTHONPATH. Block numbers are zero-based. Run obs once,
then block for every I in range(K), then merge in the directory holding groups.npz
and the blocks. --axis accepts the official one-column gene_names.csv (header).
Without it, obs uses vcc2026.genes.official_axis().symbols.

NPZ files use ordinary, uncompressed NPY members. sums is float32, Fortran order
(groups x genes); total_counts is the float64 sum over ALL source response genes.
Chunk maps and source identity are cached in groups.npz, so block only fetches
count bytes. Reuse these maps only for the exact, unchanged source file.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

import h5py
import numpy as np

from vcc2026.remote_csr import ChunkMap, chunk_map, http_fetcher, read_rows
from vcc2026.remote_ranges import HTTPRangeReader


MAX_NNZ = 8_000_000
MAX_GENES = 32
GROUP_KEYS = ("target", "pool", "n_cells", "total_counts")


def _strings(ds):
    return np.asarray(ds.asstr()[:], dtype=str)


@contextmanager
def _source(url, local_path=None):
    # Local metadata plus injected local_fetcher is the network-free test seam.
    if local_path is not None:
        with h5py.File(local_path, "r") as f:
            yield f, Path(local_path).stat().st_size
    else:
        with HTTPRangeReader(url, max_bytes=512 * 2**20) as reader:
            with h5py.File(reader, "r") as f:
                yield f, reader.size


def _publish(path, arrays, matrix=None):
    """Write small arrays and optionally stream a disk-backed NPY into an NPZ."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    with tempfile.TemporaryDirectory(prefix=".kolf-", dir=path.parent) as tmp:
        partial = Path(tmp) / "partial.npz"
        with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_STORED,
                             allowZip64=True) as z:
            for name, value in arrays.items():
                with z.open(name + ".npy", "w", force_zip64=True) as dst:
                    np.lib.format.write_array(dst, np.asarray(value), allow_pickle=False)
            if matrix is not None:
                with open(matrix, "rb") as src, z.open("sums.npy", "w", force_zip64=True) as dst:
                    shutil.copyfileobj(src, dst, length=8 * 2**20)
        # No final name exists before the archive's central directory is closed.
        os.rename(partial, path)


def prepare_obs(url, out, symbols=None, *, local_path=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "groups.npz").exists():
        raise FileExistsError(out / "groups.npz")
    if symbols is None:
        from vcc2026.genes import official_axis
        symbols = official_axis().symbols
    axis = np.asarray(symbols, dtype=str)
    if axis.ndim != 1 or len(set(axis)) != len(axis):
        raise ValueError("official axis must contain unique symbols")
    result = {"axis_genes": axis, "url": url, "schema": 1}
    with _source(url, local_path) as (f, size):
        categories, codes = {}, {}
        for name in ("gene_target", "channel", "batch", "perturbed"):
            ds = f[f"obs/{name}/categories"]
            categories[name] = _strings(ds) if ds.dtype.kind in "OSU" else ds[:]
            codes[name] = f[f"obs/{name}/codes"][:].astype(np.int64)
            if np.any(codes[name] < 0) or np.any(codes[name] >= len(categories[name])):
                raise ValueError(f"missing/invalid categorical code: {name}")
        totals = f["obs/total_counts"][:].astype(np.float64)
        n = len(totals)
        if any(len(c) != n for c in codes.values()) or not np.isfinite(totals).all():
            raise ValueError("obs lengths or total_counts invalid")
        keys, inverse, counts = np.unique(codes["gene_target"] * 8 + codes["channel"] % 8,
                                          return_inverse=True, return_counts=True)
        result.update(group_of_cell=inverse.astype(np.int32),
                      target=np.asarray(categories["gene_target"][keys // 8], dtype=str),
                      pool=(keys % 8).astype(np.int8), n_cells=counts,
                      total_counts=np.bincount(inverse, weights=totals, minlength=len(keys)),
                      source_size=size)
        for name in categories:
            result[name + "_categories"] = categories[name]
        genes = _strings(f["var/_index"])
        if len(set(genes)) != len(genes):
            raise ValueError("duplicate source gene symbols: mapping is ambiguous")
        lookup = {g: i for i, g in enumerate(genes)}
        columns = np.array([lookup.get(g, -1) for g in axis], dtype=np.int64)
        result.update(file_columns=columns, missing_genes=axis[columns < 0])
        g = f["layers/counts"]
        if g.attrs.get("encoding-type") != "csc_matrix":
            raise ValueError("layers/counts must be CSC")
        if tuple(g.attrs["shape"]) != (n, len(genes)):
            raise ValueError("counts shape disagrees with obs/var")
        ptr = g["indptr"][:].astype(np.int64)
        if len(ptr) != len(genes) + 1 or ptr[0] != 0 or np.any(np.diff(ptr) < 0):
            raise ValueError("invalid CSC indptr")
        result["indptr"] = ptr
        for name, expected in (("data", np.dtype("float32")), ("indices", np.dtype("int64"))):
            cmap = chunk_map(g[name])
            if cmap.dtype != expected or cmap.n != ptr[-1]:
                raise ValueError(f"unexpected counts/{name} dtype or length")
            result[name + "_offsets"] = cmap.offsets
            result[name + "_layout"] = np.array([cmap.chunk_len, cmap.n], dtype=np.int64)
    _publish(out / "groups.npz", result)
    print(f"groups: {len(keys)}; mapped genes: {(columns >= 0).sum()}; absent: {(columns < 0).sum()}")
    return out / "groups.npz"


def _load(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def _digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for buf in iter(lambda: f.read(2**20), b""):
            h.update(buf)
    return h.hexdigest()


def _positions(groups, block, blocks):
    if blocks < 1 or not 0 <= block < blocks:
        raise ValueError("require blocks > 0 and 0 <= block < blocks")
    mapped = np.flatnonzero(groups["file_columns"] >= 0)
    width, remainder = divmod(len(mapped), blocks)
    start = block * width + min(block, remainder)
    return mapped[start:start + width + (block < remainder)]


def _matrix_file(path, shape):
    # Fortran order makes each gene contiguous. Only small windows are ever mapped.
    with open(path, "wb") as f:
        np.lib.format.write_array_header_2_0(f, dict(descr="<f4", fortran_order=True, shape=shape))
        offset = f.tell()
        f.truncate(offset + 4 * shape[0] * shape[1])
    return offset


def _write_columns(path, offset, start, values):
    if values.size:
        window = np.memmap(path, dtype="<f4", mode="r+", offset=offset + 4 * values.shape[0] * start,
                           shape=values.shape, order="F")
        window[:] = values
        window.flush()
        del window


def _header(stream):
    version = np.lib.format.read_magic(stream)
    if version == (1, 0):
        return np.lib.format.read_array_header_1_0(stream)
    if version == (2, 0):
        return np.lib.format.read_array_header_2_0(stream)
    raise ValueError(f"unsupported NPY version: {version}")


def _check_block(path, groups, digest, block, blocks, positions):
    with np.load(path, allow_pickle=False) as z:
        if (str(z["groups_sha256"]) != digest or int(z["block"]) != block
                or int(z["blocks"]) != blocks
                or not np.array_equal(z["axis_positions"], positions)
                or not np.array_equal(z["genes"], groups["axis_genes"][positions])):
            raise ValueError(f"block metadata mismatch: {path}")
    with zipfile.ZipFile(path) as z, z.open("sums.npy") as src:
        shape, order, dtype = _header(src)
        if shape != (len(groups["target"]), len(positions)) or not order or dtype != np.dtype("<f4"):
            raise ValueError(f"block matrix mismatch: {path}")
        if z.getinfo("sums.npy").file_size != src.tell() + 4 * shape[0] * shape[1]:
            raise ValueError(f"truncated block: {path}")


def run_block(url, groups_path, block, blocks, out, *, fetch=None, max_nnz=MAX_NNZ):
    """Return False on a matching completed block; otherwise compute and return True."""
    if not 1 <= max_nnz <= MAX_NNZ:
        raise ValueError(f"max_nnz must be between 1 and {MAX_NNZ}")
    groups = _load(groups_path)
    if str(groups["url"]) != url:
        raise ValueError("URL differs from groups source")
    positions = _positions(groups, block, blocks)
    digest = _digest(groups_path)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"block_{block}_of_{blocks}.npz"
    if dest.exists():
        _check_block(dest, groups, digest, block, blocks, positions)
        print(f"skip {dest.name}")
        return False
    maps = []
    for name, dtype in (("data", np.dtype("float32")), ("indices", np.dtype("int64"))):
        length, n = groups[name + "_layout"]
        maps.append(ChunkMap(groups[name + "_offsets"], int(length), dtype.itemsize, int(n), dtype))
    fetch = fetch if fetch is not None else http_fetcher(url, expected_size=int(groups["source_size"]))
    columns = groups["file_columns"][positions]
    ptr = groups["indptr"]
    group_ids = groups["group_of_cell"]
    ng = len(groups["target"])
    fetched = 0
    logical = int(np.sum(ptr[columns + 1] - ptr[columns])) * 12
    with tempfile.TemporaryDirectory(prefix=".kolf-block-", dir=out) as tmp:
        matrix = Path(tmp) / "sums.npy"
        offset = _matrix_file(matrix, (ng, len(columns)))
        start = 0
        while start < len(columns):
            end, nnz = start, 0
            while end < min(len(columns), start + MAX_GENES):
                c = columns[end]
                length = int(ptr[c + 1] - ptr[c])
                if nnz + length > max_nnz:
                    break
                nnz += length
                end += 1
            if end == start:
                # An unusually dense column can itself be split into bounded pieces.
                c = columns[start]
                sums = np.zeros((ng, 1), dtype=np.float64)
                for lo in range(int(ptr[c]), int(ptr[c + 1]), max_nnz):
                    hi = min(lo + max_nnz, int(ptr[c + 1]))
                    data, idx, _, used = read_rows([lo, hi], [0], *maps, fetch, threads=4)
                    if np.any(idx < 0) or np.any(idx >= len(group_ids)):
                        raise ValueError("cell index outside obs")
                    sums[:, 0] += np.bincount(group_ids[idx], weights=data, minlength=ng)
                    fetched += used
                    del data, idx
                end = start + 1
            else:
                data, idx, batch_ptr, used = read_rows(ptr, columns[start:end], *maps, fetch, threads=4)
                if np.any(idx < 0) or np.any(idx >= len(group_ids)):
                    raise ValueError("cell index outside obs")
                sums = np.empty((ng, end - start), dtype=np.float32, order="F")
                for j in range(end - start):
                    a, b = batch_ptr[j:j + 2]
                    sums[:, j] = np.bincount(group_ids[idx[a:b]], weights=data[a:b], minlength=ng)
                fetched += used
                del data, idx
            _write_columns(matrix, offset, start, sums)
            del sums
            start = end
        _publish(dest, dict(block=block, blocks=blocks, groups_sha256=digest,
                            axis_positions=positions, genes=groups["axis_genes"][positions],
                            logical_count_bytes=logical, fetched_count_bytes=fetched), matrix)
    print(f"wrote {dest.name}: logical_count_bytes={logical}; fetched_count_bytes={fetched}")
    return True


def merge(directory, out):
    directory, out = Path(directory), Path(out)
    if out.exists():
        raise FileExistsError(out)
    groups_path = directory / "groups.npz"
    groups, digest = _load(groups_path), _digest(groups_path)
    files = list(directory.glob("block_*_of_*.npz"))
    if not files:
        raise ValueError("no completed blocks")
    with np.load(files[0], allow_pickle=False) as z:
        blocks = int(z["blocks"])
    if blocks < 1 or len(files) != blocks:
        raise ValueError("missing or extra blocks")
    expected = [directory / f"block_{i}_of_{blocks}.npz" for i in range(blocks)]
    if set(files) != set(expected):
        raise ValueError("missing blocks or mixed block splits")
    for i, path in enumerate(expected):
        _check_block(path, groups, digest, i, blocks, _positions(groups, i, blocks))
    out.parent.mkdir(parents=True, exist_ok=True)
    ng, na = len(groups["target"]), len(groups["axis_genes"])
    with tempfile.TemporaryDirectory(prefix=".kolf-merge-", dir=out.parent) as tmp:
        matrix = Path(tmp) / "sums.npy"
        offset = _matrix_file(matrix, (ng, na))
        for start in range(0, na, MAX_GENES):
            _write_columns(matrix, offset, start,
                           np.full((ng, min(MAX_GENES, na - start)), np.nan, dtype=np.float32))
        for i, path in enumerate(expected):
            positions = _positions(groups, i, blocks)
            with zipfile.ZipFile(path) as z, z.open("sums.npy") as src:
                _header(src)
                for position in positions:
                    buf = src.read(ng * 4)
                    if len(buf) != ng * 4:
                        raise ValueError(f"short matrix read: {path}")
                    _write_columns(matrix, offset, int(position), np.frombuffer(buf, dtype="<f4")[:, None])
                if src.read(1):
                    raise ValueError(f"trailing matrix data: {path}")
        table = {k: groups[k] for k in GROUP_KEYS}
        table.update(genes=groups["axis_genes"], file_columns=groups["file_columns"],
                     missing_genes=groups["missing_genes"], groups_sha256=digest, url=groups["url"])
        _publish(out, table, matrix)
    print(f"merged {blocks} blocks: {ng} groups x {na} genes -> {out}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    obs = sub.add_parser("obs")
    obs.add_argument("--url", required=True)
    obs.add_argument("--out", required=True, type=Path)
    obs.add_argument("--axis", type=Path, help="official single-column CSV, with header")
    block = sub.add_parser("block")
    block.add_argument("--url", required=True)
    block.add_argument("--groups", required=True, type=Path)
    block.add_argument("--block", required=True, type=int)
    block.add_argument("--blocks", required=True, type=int)
    block.add_argument("--out", required=True, type=Path)
    join = sub.add_parser("merge")
    join.add_argument("--dir", required=True, type=Path)
    join.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "obs":
        symbols = None
        if args.axis is not None:
            with args.axis.open(newline="", encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))
            if not rows or any(len(row) != 1 for row in rows) or len(rows) != 18_534:
                raise ValueError("axis CSV must have a header and 18,533 symbols")
            symbols = [row[0] for row in rows[1:]]
        prepare_obs(args.url, args.out, symbols)
    elif args.command == "block":
        run_block(args.url, args.groups, args.block, args.blocks, args.out)
    else:
        merge(args.dir, args.out)


if __name__ == "__main__":
    main()
