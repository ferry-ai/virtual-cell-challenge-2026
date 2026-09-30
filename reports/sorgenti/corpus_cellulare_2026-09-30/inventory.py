"""P1 of R-LAB: check every path of sources.yaml and classify each source by what exists, at what level.

For each local path: does it exist, how many bytes and files, and a cheap look at its format that
never loads a matrix: h5ad shape, encoding and dtype of X and a sample of its values (are they
integer counts?); the header of a .csv.gz/.tsv.gz and the dimensions line of a .mtx.gz; the rows of
a parquet file from its metadata; cell counts recorded by a manifest.json beside derived data.
Drive paths are only stat-ed. Writes inventory.json (per path) and availability.csv (per source),
refusing existing outputs, and prints the classification the day plan asks for first.

    python inventory.py --data-root C:/Users/ferra/vcc2026-data --out-dir <new folder or this one>
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DRIVE = Path("G:/Il mio Drive/vcc2026/data")


def tree_size(p: Path) -> tuple[int, int]:
    total = files = 0
    for root, _dirs, names in os.walk(p):
        for n in names:
            try:
                total += os.path.getsize(os.path.join(root, n)); files += 1
            except OSError:
                pass
    return total, files


def probe_h5ad(p: Path) -> dict:
    import h5py
    import numpy as np
    out = {}
    with h5py.File(p, "r") as f:
        x = f.get("X")
        if isinstance(x, h5py.Group):
            out["x_encoding"] = x.attrs.get("encoding-type", "?")
            shape = x.attrs.get("shape")
            out["shape"] = [int(s) for s in shape] if shape is not None else None
            data = x["data"]
            out["x_dtype"] = str(data.dtype)
            sample = data[: min(20000, data.shape[0])]
        elif isinstance(x, h5py.Dataset):
            out["x_encoding"] = "dense"
            out["shape"] = list(x.shape)
            out["x_dtype"] = str(x.dtype)
            sample = x[: min(50, x.shape[0])].ravel()[:20000]
        else:
            sample = np.array([])
        if sample.size:
            out["x_sample_integer"] = bool(np.all(np.equal(np.mod(sample, 1), 0)))
            out["x_sample_min"] = float(sample.min()); out["x_sample_max"] = float(sample.max())
        if "obs" in f:
            out["obs_columns"] = sorted(k for k in f["obs"].keys() if not k.startswith("_"))[:40]
        if "layers" in f:
            out["layers"] = sorted(f["layers"].keys())
        if "raw" in f:
            out["has_raw"] = True
    return out


def probe_text(p: Path) -> dict:
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8", errors="replace") as fh:
        first = fh.readline().rstrip("\n")
        if p.name.endswith(".mtx.gz") or p.suffix == ".mtx":
            while first.startswith("%"):
                first = fh.readline().rstrip("\n")
            dims = [int(v) for v in first.split()]
            return {"mtx_rows": dims[0], "mtx_cols": dims[1], "mtx_nnz": dims[2]}
        sep = "\t" if ".tsv" in p.name else ","
        cols = first.split(sep)
        second = fh.readline().split(sep)
        return {"header_columns": len(cols), "header_first": cols[:4], "row_first": [c[:30] for c in second[:3]]}


def probe_parquet(p: Path) -> dict:
    import pyarrow.parquet as pq
    meta = pq.ParquetFile(p).metadata
    return {"parquet_rows": meta.num_rows, "parquet_columns": meta.num_columns}


def manifest_cells(d: Path) -> dict:
    found = {}
    for m in sorted(d.glob("**/manifest*.json"))[:20]:
        try:
            data = json.loads(m.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cells = data.get("cells") if isinstance(data, dict) else None
        if isinstance(cells, dict) and "read" in cells:
            found[str(m.relative_to(d))] = {k: cells.get(k) for k in ("read", "retained")}
    return found


def probe(p: Path) -> dict:
    info = {"exists": p.exists()}
    if not p.exists():
        return info
    if p.is_dir():
        info["bytes"], info["files"] = tree_size(p)
        cells = manifest_cells(p)
        if cells:
            info["manifest_cells"] = cells
        big = sorted((q for q in p.rglob("*") if q.is_file()), key=lambda q: -q.stat().st_size)[:3]
        info["largest"] = [q.relative_to(p).as_posix() for q in big]
        if any(q.name.endswith(".mtx.gz") for q in big):
            info["probe_largest"] = probe_text(big[0])
        return info
    info["bytes"] = p.stat().st_size
    name = p.name.lower()
    try:
        if name.endswith(".h5ad"):
            info.update(probe_h5ad(p))
        elif name.endswith((".csv.gz", ".tsv.gz", ".mtx.gz", ".csv", ".tsv")):
            info.update(probe_text(p))
        elif name.endswith(".parquet"):
            info.update(probe_parquet(p))
    except Exception as exc:  # a format we cannot read cheaply is recorded, not fatal
        info["probe_error"] = f"{type(exc).__name__}: {exc}"
    return info


def status(src: dict) -> str:
    """The first classification the day plan asks for (§10), from the declared levels."""
    local, drive, remote = src.get("livello_locale"), src.get("livello_drive"), src.get("cellule_remote")
    if local == "cellule":
        return "cellule in locale"
    if drive == "cellule":
        return "cellule su Drive"
    if local == "nessuno":
        return "non acquisita" + ("" if remote == "si" else ", cellule da verificare")
    if remote == "si":
        return f"da recuperare: in locale solo {local}, cellule remote"
    if remote == "da_verificare":
        return f"in locale solo {local}, cellule da verificare"
    return f"solo {local}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", default=os.environ.get("VCC2026_DATA_ROOT", "C:/Users/ferra/vcc2026-data"))
    ap.add_argument("--out-dir", default=str(HERE))
    ap.add_argument("--no-drive", action="store_true", help="do not stat Drive paths")
    args = ap.parse_args()
    out_dir, root = Path(args.out_dir), Path(args.data_root)
    for name in ("inventory.json", "availability.csv"):
        if (out_dir / name).exists():
            sys.exit(f"refusing: {out_dir / name} exists")
    sources = yaml.safe_load((HERE / "sources.yaml").read_text(encoding="utf-8"))["sorgenti"]
    inventory, rows = {}, []
    for src in sources:
        entry = {"locale": {}, "drive": {}}
        for rel in src.get("locale") or []:
            entry["locale"][rel] = probe(root / rel)
            print(f"  {src['id']}: {rel} {'ok' if entry['locale'][rel]['exists'] else 'MISSING'}", flush=True)
        for rel in [] if args.no_drive else (src.get("drive") or []):
            p = DRIVE / rel
            entry["drive"][rel] = {"exists": p.exists(), "bytes": p.stat().st_size if p.exists() else None}
        inventory[src["id"]] = entry
        present = [v for v in entry["locale"].values() if v.get("exists")]
        rows.append({
            "id": src["id"], "stato": status(src), "modalita": src.get("modalita"),
            "livello_locale": src.get("livello_locale"), "livello_drive": src.get("livello_drive", ""),
            "percorsi_locali": len(entry["locale"]), "percorsi_presenti": len(present),
            "byte_locali": sum(v.get("bytes", 0) for v in present),
            "byte_drive": sum((v.get("bytes") or 0) for v in entry["drive"].values()),
            "remoto": src.get("remoto", ""), "ostacolo": src.get("ostacolo", ""),
            "prossimo_passo": src.get("prossimo_passo", ""),
        })
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "inventory.json").write_text(json.dumps(inventory, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out_dir / "availability.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    groups = {}
    for r in rows:
        groups.setdefault(r["stato"], []).append(r["id"])
    for k in sorted(groups):
        print(f"{k}: {', '.join(groups[k])}")
    missing = [(s, p) for s, e in inventory.items() for p, v in e["locale"].items() if not v["exists"]]
    print(f"missing local paths: {missing or 'none'}")


if __name__ == "__main__":
    main()
