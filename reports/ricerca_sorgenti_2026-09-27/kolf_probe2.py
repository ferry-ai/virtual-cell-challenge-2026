"""Second probe of the KOLF2.1J h5ad: the raw-count layer and the category names (metadata only, byte budget)."""
import sys
from pathlib import Path

import h5py

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from vcc2026.remote_ranges import HTTPRangeReader
r = HTTPRangeReader("https://ndownloader.figshare.com/files/64650261", max_bytes=64 * 1024**2, block_size=256 * 1024)
f = h5py.File(r, "r")
L = f["layers/counts"]
print("counts attrs", dict(L.attrs))
for k in L:
    ds = L[k]; print(f"  counts/{k}: {ds.shape} {ds.dtype} chunks {ds.chunks} compression {ds.compression}")
X = f["X"]
print("X/data first offset", X["data"].id.get_offset() if X["data"].chunks is None else "chunked")
for k in ("perturbed", "batch", "perturbation_type", "celltype"):
    print(k, [c.decode() if isinstance(c, bytes) else c for c in f[f"obs/{k}/categories"][:]])
gt = f["obs/gene_target/categories"]
cats = [c.decode() if isinstance(c, bytes) else c for c in gt[:]]
print("gene_target categories", len(cats), "sample", cats[:5], "ntc-like:", [c for c in cats if "non" in c.lower() or "ntc" in c.lower() or "control" in c.lower()][:10])
ch = [c.decode() if isinstance(c, bytes) else c for c in f["obs/channel/categories"][:]]
print("channels sample", ch[:6])
var_ids = f["var/_index"]
print("var index sample", [v.decode() if isinstance(v, bytes) else v for v in var_ids[:5]])
ip = f["layers/counts/indptr"][:50]
print("counts indptr first", ip[:6], "last known", f["layers/counts/indptr"].shape)
print("bytes transferred", r.transferred)
