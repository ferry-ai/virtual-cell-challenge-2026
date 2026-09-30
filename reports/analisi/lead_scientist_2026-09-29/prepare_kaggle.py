"""Stage an explicit private Kaggle dataset; never uploads or launches compute.

The four large inputs are hardlinked, not copied. Archives contain only the
allowlisted source files. Existing output directories are never reused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA_FILES = (
    "raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad",
    "external/K562_gwps_raw_bulk_01.h5ad",
    "processed/banco_hepg2_v2_2026-09-26/t19like.npz",
    "processed/banco_hepg2_v2_2026-09-26/targets.txt",
)
REPORT_FILES = (
    "generator_bench.py", "PROTOCOLLO_GENERATORE.md",
    "EMENDAMENTO_GENERATORE_01.md", "EMENDAMENTO_GENERATORE_02.md",
    "generatore/depth_bins.py", "generatore/depth_candidate.py",
    "generatore/PROTOCOLLO_BANCO_BINS.md",
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    allowed_suffixes = {".py", ".cmd", ".ps1", ".sh", ".yaml", ".yml", ".json", ".md"}
    sources = []
    for directory in (REPO / "src/vcc2026", REPO / "scripts", REPO / "configs"):
        sources += [p for p in directory.rglob("*") if p.is_file() and p.suffix in allowed_suffixes
                    and "__pycache__" not in p.parts]
    # Only code and protocols from our report; no result matrices or hidden files.
    sources += [p for p in HERE.rglob("*") if p.is_file() and p.suffix in {".py", ".md"}
                and "__pycache__" not in p.parts]
    sources += [REPO / "reports/gara/anchors_2026-09-17/anchors.json"]
    sources = sorted(set(sources))
    for path in sources + [args.data_root / p for p in DATA_FILES]:
        if not path.is_file():
            raise FileNotFoundError(path)
    args.out.mkdir(parents=True)
    data = []
    for relative in DATA_FILES:
        source = args.data_root / relative
        staged = args.out / source.name
        os.link(source, staged)
        data.append({"relative_path": relative, "upload_name": staged.name,
                     "bytes": source.stat().st_size, "sha256": digest(source),
                     "staging": "hardlink"})
    archive = args.out / "code_snapshot.tar.gz"
    code = []
    with tarfile.open(archive, "w:gz") as stream:
        for source in sources:
            relative = source.relative_to(REPO).as_posix()
            code.append({"relative_path": relative, "bytes": source.stat().st_size,
                         "sha256": digest(source)})
            stream.add(source, arcname=relative, recursive=False)
    # Check that no writer changed the frozen snapshot while it was archived.
    for row in code:
        if digest(REPO / row["relative_path"]) != row["sha256"]:
            raise RuntimeError(f"Snapshot changed during staging: {row['relative_path']}")
    manifest = {"dataset": "davideferante/vcc-lead-generator-inputs-r1",
                "private": True, "data_files": data, "code_files": code,
                "code_archive": {"upload_name": archive.name, "bytes": archive.stat().st_size,
                                 "sha256": digest(archive)},
                "intended_compute": "confirmation only, after frozen development results are added"}
    write_json(args.out / "input_manifest.json", manifest)
    metadata = {"title": "VCC Lead Generator Inputs R1", "id": manifest["dataset"],
                "licenses": [{"name": "other"}], "isPrivate": True,
                "description": "Private workspace inputs for the preregistered generator benchmark. "
                               "Original data licenses remain applicable. No challenge private data or credentials.",
                "resources": [{"path": p.name} for p in sorted(args.out.iterdir()) if p.is_file()]}
    write_json(args.out / "dataset-metadata.json", metadata)
    print(json.dumps({"staging": str(args.out), "data_bytes": sum(x["bytes"] for x in data),
                      "data_files": len(data), "code_files": len(code),
                      "archive": manifest["code_archive"], "private": True}))


if __name__ == "__main__":
    main()
