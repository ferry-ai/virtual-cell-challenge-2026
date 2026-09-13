"""Stream a prediction to .h5ad without ever holding the full matrix in RAM.

A complete submission is 360,000 cells x 18,533 genes. At realistic sparsity
that is ~2.2 billion stored values -- roughly 17 GB as an in-memory CSR, on a
machine with 7.8 GB of RAM. So the matrix is never assembled: each perturbation
is sampled, appended straight to the HDF5 file, and dropped.

The CSR layout written here mirrors what anndata produces (`csr_matrix` encoding
0.1.0, float32 data, int32 indices). obs and var are handed to anndata's own
writer at close, so their encodings never drift from the library's.
"""

from __future__ import annotations

from pathlib import Path
from types import TracebackType

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp
from anndata.io import write_elem

__all__ = ["SubmissionWriter", "indptr_dtype"]

_CHUNK = 1 << 20  # ~1M values per HDF5 chunk: few enough to resize cheaply

_INT32_MAX = int(np.iinfo(np.int32).max)


def indptr_dtype(nnz: int):
    """Integer width that can hold CSR row offsets for `nnz` stored values.

    CSR offsets run up to `nnz` itself, and a full 2026 submission lands close
    to int32's ceiling: at the realistic ~5,800 stored values per cell,
    360,000 cells give about 2.09e9 offsets against a limit of 2,147,483,647 --
    inside it by under 3%. A slightly denser prediction crosses it, and
    `astype(np.int32)` past the limit **wraps silently to negative offsets**.
    The result is a file that still opens as a valid h5ad and whose matrix is
    garbage, which is the single worst failure this writer could produce. So the
    width is chosen from the count rather than assumed.
    """
    return np.int32 if int(nnz) <= _INT32_MAX else np.int64


class SubmissionWriter:
    """Append perturbation blocks to an .h5ad one at a time.

    Example:
        with SubmissionWriter(path, genes) as w:
            for ctx, gene, block in blocks:
                w.add(block, target_gene=gene, context=ctx)

    The file is only valid once `close` has run, which `with` handles.
    """

    def __init__(
        self,
        path: str | Path,
        genes: np.ndarray | list[str],
        *,
        pert_col: str = "target_gene",
        context_col: str = "context",
        compression: str | None = "gzip",
        compression_opts: int | None = 4,
    ) -> None:
        self.path = Path(path)
        self.genes = np.asarray(genes, dtype=object)
        self.n_genes = len(self.genes)
        self.pert_col = pert_col
        self.context_col = context_col

        self._file = h5py.File(self.path, "w")
        self._file.attrs["encoding-type"] = "anndata"
        self._file.attrs["encoding-version"] = "0.1.0"

        x = self._file.create_group("X")
        x.attrs["encoding-type"] = "csr_matrix"
        x.attrs["encoding-version"] = "0.1.0"

        kw = {"chunks": (_CHUNK,), "maxshape": (None,)}
        if compression:
            kw |= {"compression": compression, "compression_opts": compression_opts}
        self._data = x.create_dataset("data", shape=(0,), dtype=np.float32, **kw)
        self._indices = x.create_dataset("indices", shape=(0,), dtype=np.int32, **kw)

        self._indptr: list[np.ndarray] = [np.zeros(1, dtype=np.int64)]
        self._nnz = 0
        self._n_obs = 0
        self._perts: list[np.ndarray] = []
        self._contexts: list[np.ndarray] = []
        self._closed = False

    def add(self, block: sp.csr_matrix, *, target_gene: str, context: str) -> None:
        """Append one perturbation's cells in one context."""
        if self._closed:
            raise RuntimeError("writer is closed")
        if block.shape[1] != self.n_genes:
            raise ValueError(
                f"block has {block.shape[1]} genes, expected {self.n_genes}"
            )

        block = block.tocsr()
        block.eliminate_zeros()  # stored zeros count against the density cap
        block.sort_indices()

        data = block.data.astype(np.float32, copy=False)
        if np.any(data < 0) or np.any(data != np.floor(data)):
            raise ValueError(
                f"{context}/{target_gene}: counts must be non-negative whole numbers"
            )

        n = data.size
        self._data.resize((self._nnz + n,))
        self._data[self._nnz:] = data
        self._indices.resize((self._nnz + n,))
        self._indices[self._nnz:] = block.indices.astype(np.int32, copy=False)

        self._indptr.append(block.indptr[1:].astype(np.int64) + self._nnz)
        self._nnz += n

        rows = block.shape[0]
        self._perts.append(np.full(rows, target_gene, dtype=object))
        self._contexts.append(np.full(rows, context, dtype=object))
        self._n_obs += rows

    def close(self) -> None:
        """Write indptr, obs and var, then close the file."""
        if self._closed:
            return
        try:
            indptr = np.concatenate(self._indptr)
            self._file["X"].attrs["shape"] = np.array(
                [self._n_obs, self.n_genes], dtype=np.int64
            )
            self._file["X"].create_dataset(
                "indptr", data=indptr.astype(indptr_dtype(self._nnz)), chunks=True
            )

            perts = np.concatenate(self._perts) if self._perts else np.array([], dtype=object)
            ctxs = np.concatenate(self._contexts) if self._contexts else np.array([], dtype=object)

            obs = pd.DataFrame(
                {
                    self.pert_col: pd.Categorical(perts),
                    self.context_col: pd.Categorical(ctxs),
                },
                index=pd.Index(
                    [f"{c}_{g}_{i:04d}" for i, (c, g) in enumerate(zip(ctxs, perts))],
                    name=None,
                ),
            )
            var = pd.DataFrame(index=pd.Index(self.genes.astype(str), name=None))

            write_elem(self._file, "obs", obs)
            write_elem(self._file, "var", var)
            for empty in ("layers", "obsm", "varm", "obsp", "varp", "uns"):
                write_elem(self._file, empty, {})
        finally:
            self._file.close()
            self._closed = True

    @property
    def n_obs(self) -> int:
        return self._n_obs

    @property
    def nnz(self) -> int:
        return self._nnz

    def __enter__(self) -> SubmissionWriter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
