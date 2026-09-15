"""Measure this machine and write the remote-job contract inputs.

Does not start Kaggle or Colab. Those runtimes have to measure themselves
with the same `collect_inventory` call. This script is the local baseline
and the disk-peak arithmetic for the jobs the plan wants first: HepG2
parity (already on disk) and Jiang TGFB / Jurkat mirror (not on disk).

    scripts/py.cmd scripts/63_runtime_preflight.py --out reports/runtime_2026-09-15
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.manifest import RunManifest
from vcc2026.resources import GiB
from vcc2026.runtime import collect_inventory, disk_peak_estimate

REPO = Path(__file__).resolve().parents[1]
TGFB_BYTES = 2_642_041_433
JURKAT_MIRROR_BYTES = 1_293_665_804
HEPG2_BYTES = 850_590_740


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / "runtime_inventory.json"
    if dest.exists():
        raise FileExistsError(f"{dest} exists; give a new --out")

    paths = config.paths()
    inventory = collect_inventory(repo=REPO, data_root=paths.data_root)
    free = inventory.resources["disk_free_bytes"]

    jobs = {
        "hepg2_parity": {
            "input_on_disk": True,
            "input_bytes": HEPG2_BYTES,
            "path": str(paths.data_root / "raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad"),
            "peak": disk_peak_estimate(
                input_bytes=HEPG2_BYTES,
                decompressed_bytes=5_600_128_608,
                derived_bytes=50_000_000,
                export_bytes=5_000_000,
            ),
            "note": "Parity job reads the local mirror; it should not re-download.",
        },
        "jiang_tgfb_block": {
            "input_on_disk": False,
            "input_bytes": TGFB_BYTES,
            "peak": disk_peak_estimate(
                input_bytes=TGFB_BYTES,
                decompressed_bytes=None,
                derived_bytes=None,
                export_bytes=None,
            ),
            "note": "Decompressed Seurat size is unknown. Do not invent RAM.",
        },
        "jurkat_mirror": {
            "input_on_disk": False,
            "input_bytes": JURKAT_MIRROR_BYTES,
            "peak": disk_peak_estimate(
                input_bytes=JURKAT_MIRROR_BYTES,
                decompressed_bytes=9_366_490_264,
                derived_bytes=80_000_000,
                export_bytes=10_000_000,
            ),
            "note": "Decompressed size is the GEO dense object, a ceiling not a measurement of the mirror.",
        },
    }
    for job in jobs.values():
        peak = job["peak"]["peak_bytes"]
        job["leaves_10gib_floor_if_peak_known"] = (
            None if peak is None else (free - peak) >= 10 * GiB
        )
        job["input_alone_leaves_10gib"] = (
            (free - job["input_bytes"]) >= 10 * GiB
        )

    assignment = {
        "this_machine": {
            "do": ["orchestration", "metadata", "tests", "HepG2 chunked reads", "packaging"],
            "do_not": [
                "readRDS of a 2.6 GB Seurat object",
                "materialise Jurkat GEO dense ~9.4 GB",
                "two matrix jobs at once",
            ],
            "ram_total_gib": inventory.resources.get("ram_total_gib"),
            "disk_free_gib": inventory.resources.get("disk_free_gib"),
        },
        "kaggle_or_colab": {
            "do": [
                "Jiang TGFB download + conversion, after that runtime measures itself",
                "Jurkat mirror download + audit, after disk is measured there",
            ],
            "not_measured_here": [
                "GPU quota", "RAM quota", "persistent disk", "network",
            ],
            "notebook": "notebooks/remote_ingest_hepg2.ipynb",
        },
        "companion_gpu": {
            "available_from": "2026-09-16 (declared by the user, not verified here)",
            "accelerates": "cell-eval2 DE backend only, on current code",
        },
    }

    report = {
        "inventory": inventory.as_dict(),
        "jobs": jobs,
        "assignment": assignment,
        "windows_paths_in_remote_jobs": False,
        "claim": "measured",
    }
    dest.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    manifest = RunManifest(
        run_id=args.out.name, stage="63_runtime_preflight", config={},
    )
    manifest.add_output("inventory", dest)
    manifest.write(args.out / "manifest_63_runtime_preflight.json")
    print(f"wrote {dest}")
    print(f"RAM {inventory.resources.get('ram_total_gib'):.2f} GiB  "
          f"disk free {inventory.resources.get('disk_free_gib'):.1f} GiB")
    print(f"HepG2 input leaves 10 GiB floor: "
          f"{jobs['hepg2_parity']['input_alone_leaves_10gib']}")
    print(f"Jiang TGFB input leaves 10 GiB floor: "
          f"{jobs['jiang_tgfb_block']['input_alone_leaves_10gib']}")


if __name__ == "__main__":
    main()
