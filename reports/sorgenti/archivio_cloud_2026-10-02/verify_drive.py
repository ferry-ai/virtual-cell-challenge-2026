"""Verify the Drive mirror of the data root from a Colab runtime (an environment independent of the laptop).

Every manifest in --manifest-dir (JSON with a sidecar <name>.sha256 holding its sha256) lists files as
{"rel", "bytes", "sha256"}; each file is read from <data root>/<rel> through the runtime's own Drive mount, so the
bytes come from Google's servers, not from the laptop's Drive cache. Missing or mismatching files are retried
for --rounds rounds, --wait-s seconds apart, because uploads from the laptop can still be in flight. A sample
of files of every kind is also opened with the reader the project uses (h5py/anndata, numpy, pandas, json,
zipfile, pyarrow), to show that the copy is usable and not only byte-identical.

Writes only into --out, which must not exist: verify_receipts.jsonl (one line per file and round),
opened_samples.json, summary.json (written last).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for blk in iter(lambda: fh.read(16 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def load_manifests(d: Path) -> list[dict]:
    entries = []
    for m in sorted(d.glob("*.json")):
        side = m.with_suffix(".sha256")
        if not side.exists():
            print(f"skip {m.name}: no sidecar", flush=True)
            continue
        want = side.read_text(encoding="utf-8").split()[0]
        if sha256(m) != want:
            sys.exit(f"refusing: {m.name} does not match its sidecar")
        doc = json.loads(m.read_text(encoding="utf-8"))
        for e in doc["files"]:
            entries.append({**e, "manifest": m.name})
    return entries


def open_sample(path: Path) -> dict:
    name = path.name.lower()
    rec: dict = {"file": str(path)}
    if name.endswith(".h5ad"):
        import h5py
        with h5py.File(path, "r") as f:
            rec["keys"] = sorted(f.keys())
            X = f["X"]
            rec["X"] = ({"encoding": str(X.attrs.get("encoding-type", "")), "nnz": int(X["data"].shape[0])}
                        if isinstance(X, h5py.Group) else {"shape": list(X.shape), "dtype": str(X.dtype)})
        try:
            import anndata
            ad = anndata.read_h5ad(path, backed="r")
            rec["anndata_shape"] = list(ad.shape)
            ad.file.close()
        except Exception as e:  # noqa: BLE001
            rec["anndata_error"] = repr(e)
    elif name.endswith(".npz"):
        import numpy as np
        with np.load(path, allow_pickle=False) as z:
            rec["arrays"] = {k: [list(z[k].shape), str(z[k].dtype)] for k in list(z.files)[:20]}
    elif name.endswith(".npy"):
        import numpy as np
        a = np.load(path, mmap_mode="r", allow_pickle=False)
        rec["shape"], rec["dtype"] = list(a.shape), str(a.dtype)
        rec["first_row_finite"] = bool(np.isfinite(np.asarray(a[0], dtype="float64")).all()) if a.size else None
    elif name.endswith((".csv", ".tsv", ".csv.gz", ".tsv.gz", ".txt.gz")):
        import pandas as pd
        sep = "\t" if ".tsv" in name else ","
        df = pd.read_csv(path, sep=sep, nrows=5)
        rec["columns"] = list(map(str, df.columns))[:30]
        rec["rows_read"] = len(df)
    elif name.endswith(".json"):
        rec["top_keys"] = list(json.loads(path.read_text(encoding="utf-8")))[:20] if path.stat().st_size < 64 << 20 else "large"
    elif name.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            rec["members"] = z.namelist()[:30]
    elif name.endswith(".parquet"):
        import pyarrow.parquet as pq
        md = pq.ParquetFile(path).metadata
        rec["rows"], rec["row_groups"] = md.num_rows, md.num_row_groups
    elif name.endswith(".gz"):
        with gzip.open(path, "rb") as fh:
            rec["first_bytes"] = len(fh.read(1 << 16))
    else:
        rec["note"] = "no reader for this type; bytes and sha256 only"
    return rec


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--manifest-dir", required=True, type=Path)
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--rounds", type=int, default=12)
    p.add_argument("--wait-s", type=int, default=1200)
    p.add_argument("--samples-per-kind", type=int, default=3)
    p.add_argument("--seed", type=int, default=20261002)
    a = p.parse_args()
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    a.out.mkdir(parents=True)
    entries = load_manifests(a.manifest_dir)
    print(f"{now()} {len(entries)} files, {sum(e['bytes'] for e in entries) / 2**30:.2f} GiB", flush=True)
    status: dict[str, str] = {}
    t0 = time.time()
    with (a.out / "verify_receipts.jsonl").open("a", encoding="utf-8") as rf:
        pending = entries
        for rnd in range(1, a.rounds + 1):
            failed = []
            for e in pending:
                path = a.data_root / e["rel"]
                rec = {"rel": e["rel"], "manifest": e["manifest"], "round": rnd, "expected_bytes": e["bytes"],
                       "expected_sha256": e["sha256"], "utc": now()}
                if not path.is_file():
                    rec["status"] = "absent"
                else:
                    size = path.stat().st_size
                    rec["bytes"] = size
                    if size != e["bytes"]:
                        rec["status"] = "size_differs"
                    else:
                        try:
                            got = sha256(path)
                            rec["sha256"] = got
                            rec["status"] = "verified" if got == e["sha256"] else "sha256_differs"
                        except OSError as err:
                            rec["status"] = f"read_error:{err}"
                rf.write(json.dumps(rec) + "\n")
                rf.flush()
                status[e["rel"]] = rec["status"]
                if rec["status"] != "verified":
                    failed.append(e)
            done_bytes = sum(e["bytes"] for e in entries if status.get(e["rel"]) == "verified")
            print(f"{now()} round {rnd}: verified {len(entries) - len(failed)}/{len(entries)} "
                  f"({done_bytes / 2**30:.2f} GiB), {time.time() - t0:.0f}s", flush=True)
            if not failed or rnd == a.rounds:
                pending = failed
                break
            pending = failed
            time.sleep(a.wait_s)
    # Representative opening: a few verified files of every extension, chosen with a fixed seed.
    rng = random.Random(a.seed)
    by_kind: dict[str, list[dict]] = {}
    for e in entries:
        if status.get(e["rel"]) == "verified":
            kind = "".join(Path(e["rel"]).suffixes[-2:]).lower() or "(none)"
            by_kind.setdefault(kind, []).append(e)
    samples = []
    for kind, lst in sorted(by_kind.items()):
        for e in rng.sample(lst, min(a.samples_per_kind, len(lst))):
            try:
                samples.append({"kind": kind, "rel": e["rel"], **open_sample(a.data_root / e["rel"])})
            except Exception as err:  # noqa: BLE001
                samples.append({"kind": kind, "rel": e["rel"], "error": repr(err)})
    (a.out / "opened_samples.json").write_text(json.dumps(samples, indent=1), encoding="utf-8")
    counts: dict[str, int] = {}
    for s in status.values():
        counts[s] = counts.get(s, 0) + 1
    (a.out / "summary.json").write_text(json.dumps({
        "written_utc": now(), "seconds": round(time.time() - t0, 1), "files": len(entries),
        "bytes": sum(e["bytes"] for e in entries), "status_counts": counts,
        "not_verified": sorted(r for r, s in status.items() if s != "verified"),
        "samples_opened": len(samples), "samples_failed": sum(1 for s in samples if "error" in s)}, indent=1),
        encoding="utf-8")
    print(f"{now()} done {counts}", flush=True)


if __name__ == "__main__":
    main()
