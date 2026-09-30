"""Build a reviewable private notebook with exactly five frozen runtime source files."""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ALLOWLIST = [HERE / name for name in (
    "neural_sources.py", "train_neural_sources.py", "read_neural_sources.py", "PROTOCOLLO_NEURALE.md")]
ALLOWLIST += [REPO / "reports/modelli/rete_contesti_2026-09-27/pool.py"]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def save(path, obj):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(obj, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    payload_io = io.BytesIO()
    entries = []
    with tarfile.open(fileobj=payload_io, mode="w") as archive:
        for path in ALLOWLIST:
            content = path.read_bytes()
            relative = path.relative_to(REPO).as_posix()
            entry = tarfile.TarInfo(relative)
            entry.size, entry.mode, entry.mtime = len(content), 0o644, 0
            archive.addfile(entry, io.BytesIO(content))
            entries.append({"path": relative, "bytes": len(content), "sha256": sha256(content)})
    payload = gzip.compress(payload_io.getvalue(), mtime=0)
    data_manifest = HERE / "kaggle_neural_r1/input_metadata/manifest.json"
    review = {"kernel": "davidmaisterx/vcc-lead-neural-sources-r1", "private": True,
              "dataset": "davidmaisterx/vcc-rete-contesti-r2", "dataset_id": 12242239,
              "dataset_manifest_sha256": sha256(data_manifest.read_bytes()),
              "payload_sha256": sha256(payload), "payload_bytes": len(payload), "code_allowlist": entries,
              "fold_order": ["k562", "cd4", "orion", "ipsc", "rpe1"], "regime": "C", "seed": 0,
              "accelerator_requested": "NvidiaTeslaT4", "cuda_visible_devices": "0",
              "quota_observed_hours_remaining": 8.92, "new_data_uploaded": False,
              "network_or_package_install_in_runtime": False, "no_production_fit": True,
              "cross_family_requires_all_five": True}
    runner = (HERE / "neural_kaggle_runner.py").read_text(encoding="utf-8")
    encoded = base64.b64encode(payload).decode("ascii")
    cell = runner + "\n\nmain(" + repr(encoded) + ", " + repr(review) + ")\n"
    compile(cell, "neural_kaggle_cell.py", "exec")
    notebook = {"nbformat": 4, "nbformat_minor": 5,
                "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                             "language_info": {"name": "python"}},
                "cells": [{"cell_type": "markdown", "id": "scope", "metadata": {},
                           "source": ["# VCC: attenzione sulle sorgenti biologiche\n",
                                      "Corsa privata preregistrata: cinque famiglie tenute fuori, regime C, seed 0. "
                                      "Ogni fallimento resta visibile; la lettura complessiva richiede tutti i cinque fold. "
                                      "Nessun risultato di questo proxy autorizza un invio VCC.\n"]},
                          {"cell_type": "code", "id": "all-five-folds", "metadata": {}, "execution_count": None,
                           "outputs": [], "source": cell.splitlines(keepends=True)}]}
    metadata = {"id": review["kernel"], "title": "VCC Lead Neural Sources R1",
                "code_file": "vcc-lead-neural-sources-r1.ipynb", "language": "python", "kernel_type": "notebook",
                "is_private": True, "enable_gpu": True, "enable_tpu": False, "enable_internet": False,
                "machine_shape": "NvidiaTeslaT4", "dataset_sources": [review["dataset"]],
                "competition_sources": [], "kernel_sources": [], "model_sources": []}
    save(args.out / metadata["code_file"], notebook)
    save(args.out / "kernel-metadata.json", metadata)
    save(args.out / "review_manifest.json", review)
    with (args.out / "runtime_payload.tar.gz").open("xb") as stream:
        stream.write(payload)
    for entry in entries:
        if sha256((REPO / entry["path"]).read_bytes()) != entry["sha256"]:
            raise RuntimeError(f"Source changed during freeze: {entry['path']}")
    save(args.out / "artifact_hashes.json", {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p.read_bytes())}
                                           for p in sorted(args.out.iterdir()) if p.is_file()})
    print(json.dumps({"folder": str(args.out), "payload_sha256": review["payload_sha256"],
                      "payload_bytes": len(payload), "runtime_files": len(entries), "private": True}))


if __name__ == "__main__":
    main()
