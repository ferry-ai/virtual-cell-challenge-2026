"""Download the DLD-1 (GSE337988) Low1 effect matrices and the guide library, with a manifest.

Refuses to overwrite: an existing file is left as it is and only re-hashed.
"""
import datetime
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

BASE = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE337nnn/GSE337988/suppl/"
FILES = [
    "GSE337988_sublib2_samplesheet.csv.gz",
    "GSE337988_NGS6475_crispr_feature_barcode_MENGNTCUPDATE.csv.gz",
    "GSE337988_sublib2_de_matrices_lfc_matrix_Low1.csv.gz",
    "GSE337988_sublib2_de_matrices_se_matrix_Low1.csv.gz",
]
out = Path(sys.argv[1])
if len(sys.argv) > 2:
    FILES = sys.argv[2:]
out.mkdir(parents=True, exist_ok=True)
entries = []
for name in FILES:
    dest = out / name
    if not dest.exists():
        tmp = dest.with_suffix(dest.suffix + ".part")
        with urllib.request.urlopen(BASE + name, timeout=120) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        tmp.rename(dest)
    h = hashlib.sha256()
    with open(dest, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    entries.append({"file": name, "url": BASE + name, "bytes": dest.stat().st_size, "sha256": h.hexdigest()})
    print(f"{name}\t{dest.stat().st_size}", flush=True)
manifest = {
    "source": "GEO GSE337988 (Yeung ... Xie, bioRxiv 10.64898/2026.07.10.737863)",
    "downloaded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "files": entries,
}
mpath = out / "manifest.json"
if mpath.exists():
    mpath = out / f"manifest_{datetime.datetime.now():%Y%m%d_%H%M%S}.json"
mpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("manifest:", mpath)
