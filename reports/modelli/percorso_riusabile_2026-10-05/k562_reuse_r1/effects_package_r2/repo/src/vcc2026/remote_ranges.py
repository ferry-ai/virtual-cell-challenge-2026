"""Budgeted HTTP random access for metadata/sample inspection of public files."""
import io
from collections import OrderedDict
import re
import httpx


class HTTPRangeReader(io.RawIOBase):
    def __init__(self, url, max_bytes=64 * 1024**2, block_size=128 * 1024):
        self.url, self.max_bytes, self.block_size = url, max_bytes, block_size
        self.client = httpx.Client(timeout=60, follow_redirects=True, headers={'Accept-Encoding':'identity'})
        self.pos = 0
        self.transferred = 0
        self.cache = OrderedDict()
        self.size = None
        try:
            self._block(0)
        except Exception:
            self.client.close()
            raise

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, offset, whence=0):
        new = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset if whence == 2 else -1
        if new < 0: raise ValueError('Invalid seek')
        self.pos = new
        return new

    def _block(self, block):
        if block in self.cache:
            self.cache.move_to_end(block)
            return self.cache[block]
        start = block * self.block_size
        end = start + self.block_size - 1
        if self.size is not None: end = min(end, self.size - 1)
        if self.transferred + end - start + 1 > self.max_bytes:
            raise RuntimeError('Remote inspection byte budget exceeded')
        with self.client.stream('GET', self.url, headers={'Range': f'bytes={start}-{end}'}) as r:
            if r.status_code != 206:
                raise RuntimeError(f'Server did not honor Range: HTTP {r.status_code}; refusing full download')
            m = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', r.headers.get('Content-Range',''))
            if not m or int(m[1]) != start or int(m[2]) != min(end,int(m[3])-1):
                raise RuntimeError('Invalid Content-Range')
            size = int(m[3])
            end = int(m[2])
            if self.size is not None and self.size != size: raise RuntimeError('Remote size changed')
            self.size = size
            data = bytearray()
            for chunk in r.iter_bytes():
                data.extend(chunk)
                if len(data) > end - start + 1: raise RuntimeError('Oversized range response')
            if len(data) != end - start + 1: raise RuntimeError('Incomplete range response')
        self.transferred += len(data)
        self.cache[block] = bytes(data)
        while len(self.cache) > 32: self.cache.popitem(last=False)
        return self.cache[block]

    def read(self, size=-1):
        if size is None or size < 0: size = self.size - self.pos
        size = min(size, self.size - self.pos)
        if size <= 0: return b''
        if size > self.max_bytes: raise RuntimeError('Read exceeds inspection budget')
        chunks = []
        while size:
            block, offset = divmod(self.pos, self.block_size)
            data = self._block(block)
            piece = data[offset:offset + size]
            if not piece: break
            chunks.append(piece)
            self.pos += len(piece)
            size -= len(piece)
        return b''.join(chunks)

    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)

    def close(self):
        if not self.closed:
            self.client.close()
            super().close()
