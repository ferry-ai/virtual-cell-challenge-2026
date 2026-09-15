"""Build a machine-readable inventory of data that is actually on disk.

Opens local files for cheap metadata (obs, var, sizes). Does not download.
Does not treat unmeasured genes as unchanged.

    scripts/py.cmd scripts/50_inventory_data.py --out reports/benchmark_2026-09-14
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.benchmark.inventory import build_inventory, write_inventory
from vcc2026.benchmark.generator_spec import missing_bundle_spec
from vcc2026.manifest import RunManifest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True,
                   help="directory for inventory.json; refused if the file exists")
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / "inventory.json"
    inventory = build_inventory(include_target_lists=True)
    write_inventory(dest, inventory)
    spec = missing_bundle_spec(inventory)
    spec_path = args.out / "missing_generator_bundle.json"
    if spec_path.exists() and not args.allow_overwrite:
        raise FileExistsError(spec_path)
    spec_path.write_text(
        __import__("json").dumps(spec, indent=2, default=str), encoding="utf-8"
    )

    man = RunManifest(
        run_id=args.out.name, stage="50_inventory_data",
        config={"out": str(args.out)},
    )
    man.add_output("inventory", dest)
    man.add_output("missing_generator_bundle", spec_path)
    n_exec = sum(
        1 for e in inventory["executable_experiments"] if e.get("status") == "executable"
    )
    n_block = sum(
        1 for e in inventory["executable_experiments"] if e.get("status") == "blocked"
    )
    man.metrics = {
        "n_sources": len(inventory["sources"]),
        "n_executable_experiments": n_exec,
        "n_blocked_experiments": n_block,
        "perturbed_contexts_local": inventory["perturbed_contexts_local"],
    }
    man.note("Unmeasured genes are not unchanged (D-009).")
    man.note("No download was performed.")
    man.write(args.out / "manifest_50_inventory_data.json",
              allow_overwrite=args.allow_overwrite)
    print(f"wrote {dest}")
    print(f"perturbed contexts local: {inventory['perturbed_contexts_local']}")
    print(f"executable: {n_exec}; blocked: {n_block}")


if __name__ == "__main__":
    main()
