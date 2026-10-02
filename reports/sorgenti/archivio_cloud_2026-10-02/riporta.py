"""Bring files back from the Drive mirror into the local data root, checking each against the archive manifest.

For research code in reports/ that reads a group no longer on the laptop: either run it on Colab with
VCC2026_DATA_ROOT=/content/drive/MyDrive/vcc2026/data (the mirror keeps relative paths, nothing to change), or
bring back the files it needs with this tool. A file is restored only if its sha256 after the copy equals the
one in the manifest (manifest A of the mirror or B of the data already on Drive); an existing local file is
never overwritten. Reading from the Drive mount downloads the file through Drive for desktop: check free
space first (the tool refuses when the file plus --min-free-gb does not fit).

    py -3 riporta.py --prefix interim/kolf_sums/ --manifest <run>/manifests/a_specchio_r1.json
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prefix", required=True, help="relative path or prefix under the data root")
    p.add_argument("--manifest", required=True, nargs="+", type=Path)
    p.add_argument("--drive-data", default=r"G:\Il mio Drive\vcc2026\data", type=Path)
    p.add_argument("--data-root", default=r"C:\Users\ferra\vcc2026-data", type=Path)
    p.add_argument("--min-free-gb", type=float, default=8.0)
    a = p.parse_args()
    entries = {}
    for m in a.manifest:
        for e in json.loads(m.read_text(encoding="utf-8"))["files"]:
            entries[e["rel"]] = e
    todo = [e for rel, e in sorted(entries.items()) if rel.startswith(a.prefix)]
    if not todo:
        sys.exit(f"no manifest entry under {a.prefix}")
    for e in todo:
        dst = a.data_root / e["rel"]
        if dst.exists():
            print(f"skip, exists locally: {e['rel']}")
            continue
        if shutil.disk_usage(a.data_root).free < e["bytes"] + a.min_free_gb * 2**30:
            sys.exit(f"stop: not enough free space for {e['rel']} ({e['bytes'] / 2**30:.2f} GiB)")
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + ".partial")
        h = hashlib.sha256()
        with (a.drive_data / e["rel"]).open("rb") as fi, tmp.open("wb") as fo:
            for blk in iter(lambda: fi.read(8 << 20), b""):
                h.update(blk)
                fo.write(blk)
        if h.hexdigest() != e["sha256"]:
            tmp.unlink()
            sys.exit(f"sha256 differs for {e['rel']}: nothing restored for it")
        tmp.replace(dst)
        print(f"restored {e['rel']} ({e['bytes'] / 2**20:.1f} MiB), sha256 ok")


if __name__ == "__main__":
    main()
