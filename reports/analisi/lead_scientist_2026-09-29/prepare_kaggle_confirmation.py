"""Stage dataset version 2 after Colab development has finished; never uploads.

Preserves the original dataset staging and source archive. Only completed benchmark
outputs are added; the four data files are hardlinks to the authorized version 1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tarfile


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, obj):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(obj, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-v1", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path,
                        help="New frozen code archive plus input_manifest.json, when repaired before scoring")
    parser.add_argument("--development-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    snapshot_root = args.snapshot_root or args.dataset_v1
    inputs = json.loads((snapshot_root / "input_manifest.json").read_text())
    source_archive = snapshot_root / inputs["code_archive"]["upload_name"]
    if digest(source_archive) != inputs["code_archive"]["sha256"]:
        raise ValueError("Frozen code archive changed")
    prepared = json.loads((args.development_root / "target_manifest.json").read_text())
    selection_path = args.development_root / "development/selection.json"
    selection = json.loads(selection_path.read_text())
    if prepared["design"] != "joint_14_arms_amendment_02" or prepared["truth"] != "full":
        raise ValueError("Wrong prospective design")
    if set(prepared["development"]) & set(prepared["confirmation"]):
        raise ValueError("Split overlap")
    expected = {"repo": {r["relative_path"]: r["sha256"] for r in inputs["code_files"]},
                "data": {r["relative_path"]: r["sha256"] for r in inputs["data_files"]}}
    for filename, info in prepared["fingerprints"].items():
        normal = filename.replace("\\", "/")
        matched = False
        for name, original in prepared["path_roots"].items():
            prefix = original.replace("\\", "/").rstrip("/") + "/"
            if normal.startswith(prefix):
                if expected[name].get(normal[len(prefix):]) != info["sha256"]:
                    raise ValueError(f"Development input differs from frozen dataset: {filename}")
                matched = True
                break
        if not matched:
            raise ValueError(f"Unmapped development fingerprint: {filename}")
    effects = args.development_root / "prepared_effects.npz"
    if digest(effects) != prepared["prepared_effects_sha256"]:
        raise ValueError("Prepared effects changed")
    files = [args.development_root / "target_manifest.json", effects]
    files += sorted((args.development_root / "development").rglob("*"))
    environment = args.development_root / "development_environment.json"
    if environment.exists():
        files.append(environment)
    files = [p for p in files if p.is_file()]
    allowed = [r["upload_name"] for r in inputs["data_files"]]
    args.out.mkdir(parents=True)
    for name in allowed:
        os.link(args.dataset_v1 / name, args.out / name)
    os.link(source_archive, args.out / source_archive.name)
    os.link(snapshot_root / "input_manifest.json", args.out / "input_manifest.json")
    archive = args.out / "development_bundle.tar.gz"
    entries = []
    with tarfile.open(archive, "w:gz") as stream:
        for path in files:
            relative = "generator_r1/" + path.relative_to(args.development_root).as_posix()
            entries.append({"relative_path": relative, "bytes": path.stat().st_size,
                            "sha256": digest(path)})
            stream.add(path, arcname=relative, recursive=False)
    write_json(args.out / "development_bundle_manifest.json", {
        "code_archive_sha256": inputs["code_archive"]["sha256"],
        "archive": {"upload_name": archive.name, "bytes": archive.stat().st_size,
                    "sha256": digest(archive)}, "files": entries,
        "shortlist": selection["shortlist"]})
    metadata = json.loads((args.dataset_v1 / "dataset-metadata.json").read_text())
    metadata["resources"] = [{"path": p.name} for p in sorted(args.out.iterdir()) if p.is_file()]
    write_json(args.out / "dataset-metadata.json", metadata)
    print(json.dumps({"staging": str(args.out), "files_added": len(entries),
                      "bundle_bytes": archive.stat().st_size, "shortlist": selection["shortlist"]}))


if __name__ == "__main__":
    main()
