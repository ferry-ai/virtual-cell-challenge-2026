"""Read-ahead for the remote h5ad reader of the corpus: the same bytes, several ranges at a time.

`inspect_remote.RangeFile` (corpus_cellulare_2026-09-30) asks one block of 8 MB after another. On the KOLF pan-genome
file (Figshare) that gave 5.8 MB/s, measured on 3/10 on a Kaggle CPU kernel (kernel vcc-kolf-pan-p0of2-r1: 83 ranges
in 120 s): 4.5 hours for the 94.5 GB of the counts layer, and a CD4 file of 143 GB would not fit the 12 hours of a
kernel. `PrefetchFile` is that reader with a thread pool: when a block is asked, the blocks after it are requested
too, so a sequential scan (or two interleaved ones, the indices and the data of a sparse matrix) finds them ready.
Blocks, checks and cache are those of RangeFile: every answer must be the range asked, of one version of the file.

`install(adapters_module)` makes a module's `_h5_open` use it for URLs; local paths are opened as before.
"""
from __future__ import annotations

import io
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[2] / "corpus_cellulare_2026-09-30"
if str(CORPUS) not in sys.path:
    sys.path.insert(0, str(CORPUS))
from inspect_remote import RangeFile  # noqa: E402


class PrefetchFile(RangeFile):
    def __init__(self, url: str, block: int = 8 << 20, max_bytes: int = 1 << 30, ahead: int = 8, threads: int = 8):
        self.lock, self.resolve_lock, self.local, self.generation = threading.RLock(), threading.Lock(), threading.local(), 0
        self.pending: dict = {}
        self.ahead, self.pool = ahead, ThreadPoolExecutor(threads)
        super().__init__(url, block=block, max_bytes=max_bytes)

    def _resolve(self):
        """One renewal serves every thread. Figshare's signed URLs expire after 10 seconds, so all the threads find
        theirs expired together: the first renews it, the others see that the URL is newer than the one their
        request used and ask again with it."""
        with self.resolve_lock:
            used = getattr(self.local, "generation", None)
            if used is not None and used < self.generation:
                return
            super()._resolve()
            self.generation += 1

    def _fetch(self, url, lo, hi):
        self.local.generation = self.generation
        return super()._fetch(url, lo, hi)

    def _load(self, i: int) -> bytes:
        lo, hi = i * self.block, min(self.size, (i + 1) * self.block) - 1
        data, etag = self._get(lo, hi)
        if self.etag and etag and etag != self.etag:
            raise OSError(f"the file changed while it was read: ETag {etag} after {self.etag}")
        if len(data) != hi - lo + 1:
            raise OSError(f"range {lo}-{hi} returned {len(data)} bytes: the server ignores Range")
        with self.lock:
            self.cache[i] = data
            self.fetched += len(data)
            self.pending.pop(i, None)
            while len(self.cache) > self.max_blocks:
                self.cache.popitem(last=False)
        return data

    def _blk(self, i: int) -> bytes:
        blocks = -(-self.size // self.block)
        with self.lock:
            for j in range(i, min(blocks, i + 1 + self.ahead)):
                if j not in self.cache and j not in self.pending:
                    self.pending[j] = self.pool.submit(self._load, j)
            if i in self.cache:
                self.cache.move_to_end(i)
                return self.cache[i]
            wait = self.pending[i]
        return wait.result()

    def close(self):
        self.pool.shutdown(wait=False, cancel_futures=True)
        super().close()


def install(adapters_module, block: int = 8 << 20, max_bytes: int = 1 << 30, ahead: int = 8, threads: int = 8) -> None:
    """Replace `adapters_module._h5_open` so that URLs are read through PrefetchFile."""
    import h5py  # noqa: PLC0415

    def _h5_open(path):
        if str(path).startswith(("http://", "https://")):
            raw = PrefetchFile(str(path), block=block, max_bytes=max_bytes, ahead=ahead, threads=threads)
            return h5py.File(io.BufferedReader(raw, buffer_size=block), "r")
        return h5py.File(path, "r")

    adapters_module._h5_open = _h5_open
