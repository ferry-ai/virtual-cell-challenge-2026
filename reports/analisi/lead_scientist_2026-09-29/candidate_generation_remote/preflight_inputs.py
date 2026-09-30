"""Read-only inventory for the proposed remote generator; never uploads or generates."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


EFFECTS = "data/processed/effects_t25_2026-09-27"
CONTROLS = "data/raw/controls"
ARCHIVE = "runs/lead_generator_setup_2026-09-29_r3/code_snapshot.tar.gz"
ARCHIVE_SHA = "f7324778e5d7225552734e2c7303353f46dee6c01e9d455703adce3b9b105860"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--local-data", type=Path, required=True)
    p.add_argument("--drive-root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    import h5py
    import numpy as np
    files = []
    relatives = [f"{CONTROLS}/context_{c}.h5ad" for c in "ABC"]
    relatives += [f"{CONTROLS}/gene_names.csv", f"{CONTROLS}/pert_counts.csv"]
    relatives += [f"{EFFECTS}/effects_{c}.npz" for c in "ABC"]
    relatives += [f"{EFFECTS}/manifest.json"]
    for relative in relatives:
        local = args.local_data / relative.removeprefix("data/")
        remote = args.drive_root / relative
        print("inventory", relative, flush=True)
        item = {"drive_relative": relative, "local_source": str(local),
                "bytes": local.stat().st_size, "sha256": sha256(local), "sha256_mode": "full",
                "drive_exists_at_preflight": remote.is_file()}
        if remote.is_file():
            item["drive_bytes"] = remote.stat().st_size
            item["drive_sha256"] = sha256(remote)
            if item["drive_bytes"] != item["bytes"] or item["drive_sha256"] != item["sha256"]:
                raise ValueError(f"Local/Drive mismatch: {relative}")
        if local.suffix == ".npz":
            with np.load(local, allow_pickle=False) as z:
                item["arrays"] = {k: {"shape": list(z[k].shape), "dtype": str(z[k].dtype)} for k in z.files}
                assert z["lfc"].shape == z["observed"].shape == (300, 18533)
                assert np.isfinite(z["lfc"]).all()
        elif local.suffix == ".h5ad":
            with h5py.File(local, "r") as f:
                item["matrix_shape"] = [int(v) for v in f["X"].attrs["shape"]]
                item["stored_entries"] = int(f["X/data"].shape[0])
                assert item["matrix_shape"] == [18400, 18533]
        files.append(item)
    archive = args.drive_root / ARCHIVE
    actual_archive_sha = sha256(archive)
    if actual_archive_sha != ARCHIVE_SHA:
        raise ValueError("Wrong code archive")
    payload = {"claim_type": "measured read-only preflight; no generation or upload",
               "created_utc": datetime.now(timezone.utc).isoformat(),
               "drive_root_observed": str(args.drive_root),
               "colab_drive_root": "/content/drive/MyDrive/vcc2026",
               "code_archive": {"drive_relative": ARCHIVE, "sha256": ARCHIVE_SHA,
                                "bytes": archive.stat().st_size},
               "files": files,
               "missing_drive_inputs": [i["drive_relative"] for i in files if not i["drive_exists_at_preflight"]],
               "generation": {"effects_scale": 1.5, "phi_scale_allowed": [0.5, 1.0],
                              "seed": 20260912, "contexts": ["A", "B", "C"],
                              "cells_per_pert": 400, "required_vcc_cli": "0.2.0"}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"out": str(args.out), "missing_drive_inputs": payload["missing_drive_inputs"]}))


if __name__ == "__main__":
    main()
