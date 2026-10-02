"""Kaggle-side integrity check of the private corpus datasets (runs inside a Kaggle CPU kernel).

For every file under /kaggle/input it records bytes and sha256, read from the mounted dataset on Kaggle's own
machines: an environment independent of Colab, where the shards were written, and of the laptop. For the first
.h5ad of every unit it also opens the file with h5py and checks the structure the training reader relies on:
cell count from obs, the count matrix (dense or CSR) and its internal consistency. Nothing is trained or changed.

Output: /kaggle/working/verify_kaggle.json (one record per file, plus the opened samples and the run environment).
The comparison with the publish receipts is done afterwards, outside the kernel.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/kaggle/input")
OUT = Path("/kaggle/working/verify_kaggle.json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for blk in iter(lambda: fh.read(16 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def frame_rows(frame) -> int | None:
    """Rows of an AnnData dataframe group: its index column may be a dataset or an encoded group."""
    import h5py
    key = frame.attrs.get("_index", "_index")
    key = key.decode() if isinstance(key, bytes) else key
    if key not in frame:
        return None
    col = frame[key]
    if isinstance(col, h5py.Dataset):
        return int(col.shape[0])
    for sub in ("codes", "values", "data"):
        if sub in col:
            return int(col[sub].shape[0])
    return None


def open_h5ad(path: Path) -> dict:
    import h5py
    import numpy as np
    rec: dict = {"file": str(path)}
    with h5py.File(path, "r") as f:
        obs = f["obs"]
        rec["n_obs"] = frame_rows(obs)
        rec["n_var"] = frame_rows(f["var"])
        X = f["X"]
        if isinstance(X, h5py.Group):
            enc = X.attrs.get("encoding-type", b"")
            rec["X_encoding"] = enc.decode() if isinstance(enc, bytes) else str(enc)
            indptr = X["indptr"][:]
            rec["X_nnz"] = int(X["data"].shape[0])
            rec["indptr_consistent"] = bool(indptr[0] == 0 and indptr[-1] == X["data"].shape[0]
                                            and np.all(np.diff(indptr) >= 0))
            head = X["data"][: min(100000, X["data"].shape[0])]
        else:
            rec["X_encoding"] = "dense"
            rec["X_shape"] = list(X.shape)
            head = X[: min(50, X.shape[0])].ravel()
        rec["X_dtype"] = str(head.dtype)
        rec["X_head_sum"] = float(head.sum())
        rec["X_head_integer_valued"] = bool(np.all(np.mod(head, 1) == 0))
        rec["obs_columns"] = sorted(k for k in obs.keys() if not k.startswith("__"))[:60]
        rec["layers"] = sorted(f["layers"].keys()) if "layers" in f else []
    try:  # the reader the training uses, when the image has it
        import anndata
        ad = anndata.read_h5ad(path, backed="r")
        rec["anndata_shape"] = list(ad.shape)
        rec["anndata_matches_h5py"] = rec["anndata_shape"] == [rec["n_obs"], rec["n_var"]]
        ad.file.close()
    except ImportError:
        rec["anndata"] = "not installed"
    except Exception as e:  # noqa: BLE001
        rec["anndata_error"] = repr(e)
    return rec


def main() -> None:
    t0 = time.time()
    files, samples, errors = [], [], []
    opened_units: set[tuple[str, str]] = set()
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        try:
            files.append({"path": rel, "bytes": p.stat().st_size, "sha256": sha256(p)})
        except OSError as e:
            errors.append({"path": rel, "error": str(e)})
            continue
        if p.suffix == ".h5ad":
            parts = rel.split("/")
            dataset = "/".join(parts[1:3]) if parts[0] == "datasets" else parts[0]
            unit = p.name.split("__", 1)[0]
            if (dataset, unit) not in opened_units:
                opened_units.add((dataset, unit))
                try:
                    samples.append(open_h5ad(p))
                except Exception as e:  # noqa: BLE001 - record any failure to open, do not stop
                    samples.append({"file": rel, "error": repr(e)})
        if len(files) % 200 == 0:
            print(f"{len(files)} files, {sum(f['bytes'] for f in files) / 2**30:.1f} GiB, "
                  f"{time.time() - t0:.0f}s", flush=True)
    try:
        import h5py
        h5py_version = h5py.__version__
    except Exception:  # noqa: BLE001
        h5py_version = None
    OUT.write_text(json.dumps({
        "written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seconds": round(time.time() - t0, 1),
        "environment": {"python": sys.version, "platform": platform.platform(), "h5py": h5py_version,
                        "hostname": os.uname().nodename if hasattr(os, "uname") else None},
        "datasets": sorted({"/".join(f["path"].split("/")[1:3]) if f["path"].startswith("datasets/")
                            else f["path"].split("/", 1)[0] for f in files}),
        "files": files, "samples": samples, "errors": errors}, indent=0), encoding="utf-8")
    print(f"done: {len(files)} files, {len(samples)} samples, {len(errors)} errors, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
