"""Run the first modular-vs-monolithic pilot on local pseudobulk signatures.

Proxy metrics in log2FC, not VCC scores. Does not submit, does not download,
does not pick a winner on the test split.

    scripts/py.cmd scripts/51_run_modular_pilot.py --run-id m001
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.benchmark.protocol import load_yaml_config
from vcc2026.benchmark.run import run_pilot
from vcc2026.manifest import RunManifest
from vcc2026.resources import peak_rss_bytes, snapshot


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", default="m001")
    p.add_argument("--config", type=Path, default=None,
                   help="defaults to configs/benchmark.yaml")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--signatures", type=Path, nargs="*", default=None,
                   help="one or more directories of .npz signatures, searched in "
                        "order; sources may live in different run directories")
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    cfg_path = args.config or (
        Path(__file__).resolve().parents[1] / "configs" / "benchmark.yaml"
    )
    cfg = load_yaml_config(cfg_path)
    out_dir = args.out or config.run_dir(args.run_id)
    print(f"config: {cfg_path}")
    print(f"out: {out_dir}")
    print(f"primary metric: {cfg['primary_metric']} ({cfg['primary_metric_space']})")
    print("non-inferiority margin:", cfg["non_inferiority_margin"])

    snap0 = snapshot(out_dir)
    result = run_pilot(
        cfg_path=cfg_path,
        out_dir=out_dir,
        signatures_dir=args.signatures,
        allow_overwrite=args.allow_overwrite,
    )
    man = RunManifest(
        run_id=args.run_id, stage="51_run_modular_pilot",
        config=vars(args) | {"benchmark_yaml": str(cfg_path)},
        seed=cfg["pilot"]["seeds"][0],
    )
    man.add_input("config", cfg_path)
    for name in ("inventory", "results", "table", "summary"):
        path = Path(result[name])
        if path.exists():
            man.add_output(name, path)
    man.metrics = {
        "n_rows": result["n_rows"],
        "n_targets_used": result["subsample"]["n_used"],
        "n_shared_available": result["subsample"]["n_shared_available"],
        "peak_rss_bytes": peak_rss_bytes(),
        "ram_available_gib_at_start": snap0.ram_available_gib,
        "not_a_vcc_score": True,
        "winner_declared": False,
    }
    man.note(
        "Primary metric is pooled_mse_vs_null in pseudobulk log2FC. "
        "Not a VCC score. No architecture was selected on the external test."
    )
    man.note(
        "With two perturbed contexts, holding one out leaves a single training "
        "context: transfer feasibility, not general context-dependence learning."
    )
    man.write(out_dir / "manifest_51_run_modular_pilot.json",
              allow_overwrite=args.allow_overwrite)
    print(json.dumps({k: result[k] for k in ("n_rows", "subsample")}, indent=2))
    print(f"table: {result['table']}")


if __name__ == "__main__":
    main()
