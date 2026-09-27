"""Probe the structure of the KOLF2.1J pan-genome h5ad over HTTP ranges (metadata only, byte budget)."""
import sys
from pathlib import Path

import h5py

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from vcc2026.remote_ranges import HTTPRangeReader  # noqa: E402

URL = "https://ndownloader.figshare.com/files/64650261"
r = HTTPRangeReader(URL, max_bytes=48 * 1024**2, block_size=256 * 1024)
f = h5py.File(r, "r")
print("file size", r.size, "top keys", list(f.keys()))
print("root attrs", dict(f.attrs))
X = f["X"]
if isinstance(X, h5py.Group):
    print("X attrs", dict(X.attrs))
    for k in X:
        ds = X[k]
        print(f"  X/{k}: shape {ds.shape} dtype {ds.dtype} chunks {ds.chunks} compression {ds.compression} opts {ds.compression_opts} filters {list(ds._filters.keys()) if hasattr(ds, '_filters') else '?'}")
else:
    print("X dataset", X.shape, X.dtype, X.chunks, X.compression)
obs = f["obs"]
print("obs attrs", {k: (v if len(str(v)) < 300 else str(v)[:300]) for k, v in obs.attrs.items()})
for k in list(obs.keys())[:40]:
    o = obs[k]
    if isinstance(o, h5py.Group):
        cats = o["categories"]
        print(f"  obs/{k}: categorical, {cats.shape[0]} categories, codes {o['codes'].dtype} {o['codes'].shape}")
    else:
        print(f"  obs/{k}: {o.dtype} {o.shape}")
var = f["var"]
print("var keys", list(var.keys())[:20], "attrs", {k: str(v)[:200] for k, v in var.attrs.items()})
for k in ("layers", "obsm", "uns", "raw"):
    if k in f:
        print(k, list(f[k].keys())[:20])
print("bytes transferred", r.transferred)
