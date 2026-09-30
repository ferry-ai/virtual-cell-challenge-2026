"""P0 of R-LAB: can this runtime ingest cell-level data and score it, and with what resources?

Writes a new environment manifest (it refuses an existing path): interpreter, package versions,
whether the real scorer imports, a sparse round trip that keeps raw integer counts, the
distinction between an observed zero and an unmeasured gene, and cell identity, plus RAM, disk
and CPUs of the machine. The same script runs locally, on Colab and on Kaggle, so their
manifests can be compared before a job is planned on them.

    python validate_runtime.py --out environment_manifest_<where>.json [--data-root <dir>]

Standard library plus numpy, scipy and anndata for the round trip; a missing package is recorded,
not fatal.
"""
from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import importlib
import importlib.metadata as md
import json
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path

PACKAGES = ["numpy", "scipy", "pandas", "h5py", "anndata", "pyarrow", "PyYAML", "torch", "scanpy",
            "scikit-learn", "cell-eval2", "numba", "zarr", "polars", "fsspec", "requests",
            "pertpy", "scvi-tools", "harmonypy", "decoupler"]


def memory() -> dict:
    if sys.platform == "win32":
        class Status(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        s = Status(); s.dwLength = ctypes.sizeof(Status)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
        return {"total_bytes": s.ullTotalPhys, "available_bytes": s.ullAvailPhys}
    info = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            info[key] = int(value.split()[0]) * 1024
        return {"total_bytes": info.get("MemTotal"), "available_bytes": info.get("MemAvailable")}
    except OSError:
        return {}


def disks(paths: list[str]) -> dict:
    out = {}
    for p in paths:
        try:
            u = shutil.disk_usage(p)
            out[p] = {"total_bytes": u.total, "free_bytes": u.free}
        except OSError as exc:
            out[p] = {"error": str(exc)}
    return out


def gpu() -> dict:
    try:
        import torch
        if torch.cuda.is_available():
            return {"cuda": True, "name": torch.cuda.get_device_name(0),
                    "memory_bytes": torch.cuda.get_device_properties(0).total_memory}
        return {"cuda": False}
    except Exception as exc:  # torch missing or broken: recorded, not fatal
        return {"error": f"{type(exc).__name__}: {exc}"}


def scorer() -> dict:
    try:
        import cell_eval2
        from cell_eval2.metrics.direction import _components  # private API the live bench uses
        return {"import": True, "version": md.version("cell-eval2"), "private_api_components": callable(_components),
                "aggregate_metrics": hasattr(cell_eval2, "aggregate_metrics")}
    except Exception as exc:
        return {"import": False, "error": f"{type(exc).__name__}: {exc}"}


def roundtrip() -> dict:
    """Write and read back a tiny sparse AnnData: counts, identity, measured mask, raw layer."""
    try:
        import anndata as ad
        import numpy as np
        import scipy.sparse as sp
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    rng = np.random.default_rng(2026)
    dense = rng.poisson(0.3, size=(40, 25)).astype(np.int32)
    dense[:, 20:] = 0                                   # five genes the assay never measured
    x = sp.csr_matrix(dense)
    obs = {"cell_key": [f"study|lib{i % 3}|BC{i:04d}" for i in range(40)],
           "target": ["NTC" if i % 5 == 0 else f"G{i % 7}" for i in range(40)],
           "guide_confidence": rng.uniform(size=40)}
    var = {"gene_id": [f"ENSG{i:011d}" for i in range(25)], "measured": [i < 20 for i in range(25)]}
    import pandas as pd
    a = ad.AnnData(X=x, obs=pd.DataFrame(obs, index=[f"c{i}" for i in range(40)]),
                   var=pd.DataFrame(var, index=[f"g{i}" for i in range(25)]))
    a.layers["counts_raw"] = x.copy()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "roundtrip.h5ad"
        a.write_h5ad(path)
        b = ad.read_h5ad(path)
        backed = ad.read_h5ad(path, backed="r")
        checks = {
            "csr_kept": sp.issparse(b.X) and b.X.format == "csr",
            "integer_counts_kept": np.issubdtype(b.layers["counts_raw"].dtype, np.integer),
            "counts_equal": (b.X != x).nnz == 0,
            "sum_equal": int(b.X.sum()) == int(dense.sum()),
            "cell_identity_kept": list(b.obs["cell_key"]) == obs["cell_key"],
            "measured_mask_kept": list(b.var["measured"]) == var["measured"],
            "zero_vs_unmeasured_distinct": bool(b.var["measured"].sum() == 20 and dense[:, 20:].sum() == 0),
            "backed_read_rows": int(backed.X[5:10].sum()) == int(dense[5:10].sum()),
        }
        backed.file.close()
    return {"ok": all(checks.values()), **checks}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True)
    p.add_argument("--data-root", default=os.environ.get("VCC2026_DATA_ROOT"))
    args = p.parse_args()
    out = Path(args.out)
    if out.exists():
        sys.exit(f"refusing: {out} exists")
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = md.version(name)
        except md.PackageNotFoundError:
            versions[name] = None
    places = [str(Path.cwd()), tempfile.gettempdir()] + ([args.data_root] if args.data_root else [])
    manifest = {
        "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "host": platform.node(), "platform": platform.platform(), "python": sys.version.split()[0],
        "executable": sys.executable, "cpus": os.cpu_count(), "memory": memory(), "disks": disks(places),
        "gpu": gpu(), "packages": versions, "scorer": scorer(), "sparse_roundtrip": roundtrip(),
        "missing_packages": sorted(k for k, v in versions.items() if v is None),
    }
    out.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    ok = manifest["scorer"].get("import") and manifest["sparse_roundtrip"].get("ok")
    print(f"{out}: scorer {'ok' if manifest['scorer'].get('import') else 'MISSING'}, "
          f"roundtrip {'ok' if manifest['sparse_roundtrip'].get('ok') else 'FAILED'}, "
          f"free RAM {manifest['memory'].get('available_bytes', 0) / 1e9:.2f} GB")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
