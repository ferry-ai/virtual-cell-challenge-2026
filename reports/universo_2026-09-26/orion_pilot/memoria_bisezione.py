"""Bisect the committed-memory growth of apply_file on one small local parquet file."""
import gc
import importlib.util
import sys
from pathlib import Path

import numpy as np

REPO = Path(r"C:\Users\ferra\OneDrive\Desktop\vcc2026")
spec = importlib.util.spec_from_file_location("ou", REPO / "reports/universo_2026-09-26/orion_universe.py")
ou = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ou)
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

work = Path(r"C:\Users\ferra\vcc2026-data\interim\orion_universe_leaktest")
parquet = work / "leak.parquet"
mode = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 15


def read(set_pool: bool, pre_buffer: bool = False, to_numpy: bool = True):
    if set_pool:
        pa.set_memory_pool(pa.system_memory_pool())
    pf = pq.ParquetFile(parquet, buffer_size=4 << 20, pre_buffer=pre_buffer)
    for batch in pf.iter_batches(batch_size=512, columns=ou.COLUMNS):
        if to_numpy:
            tgt = batch.column("gene_target").to_numpy(zero_copy_only=False).astype(str)
            tok = batch.column("gene_token_id").values.to_numpy(zero_copy_only=False)
            ex = batch.column("gene_expression").values.to_numpy(zero_copy_only=False)
            del tgt, tok, ex


def poolbuf():
    pb = ou.PoolBuffer(work / "leak_pool.f32", 18533, 3621)
    pb.add(np.arange(10, dtype=np.int64), np.ones((10, 18533)))
    pb.close()


steps = {"read_setpool": lambda: read(True), "read_default": lambda: read(False),
         "read_prebuffer": lambda: read(False, True), "open_only": lambda: read(False, False, False),
         "poolbuf": poolbuf}
print(mode, "start", ou.memory()["private_mib"], flush=True)
vals = []
for i in range(n):
    steps[mode]()
    gc.collect()
    vals.append(ou.memory()["private_mib"])
print(mode, vals, "growth per call", round((vals[-1] - vals[1]) / (n - 2), 2), "MiB", flush=True)
