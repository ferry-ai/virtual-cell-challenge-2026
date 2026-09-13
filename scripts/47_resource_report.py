"""Stage 7: consolidate the measured cost of a set of runs into one table.

Every number here is copied out of a run's own `generation_diagnostics.json` or
`validation.json` -- never retyped. That is the point: the documented failure
mode of this repository is a measured number becoming a slightly different
number on its way into prose, and a script that reads the JSON cannot make that
mistake.

It also records what the installed CLI's own sizing model predicts for each
prediction's density, because that model -- fitted on the scoring service's
production instrumentation -- is what explains a packaging step that does not
finish on this machine.

    scripts/py.cmd scripts/47_resource_report.py --runs q00pilot q00full q01pilot q01full \
        --out reports/trial_2026-09-12/resources.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.manifest import environment_fingerprint
from vcc2026.resources import GiB, snapshot

REPO = Path(__file__).resolve().parents[1]


def sizing_model(nnz: int | None) -> dict:
    if nnz is None:
        return {"available": False, "reason": "no stored-entry count"}
    try:
        from vcc import sizing
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "available": True,
        "source": "vcc.sizing (installed vcc-cli)",
        "scipy_bytes_per_nnz": sizing.bytes_per_nnz(nnz),
        "crosses_int32_index_limit": nnz > sizing.INT32_INDEX_LIMIT,
        "prep_peak_gib_no_cast_in_order": sizing.prep_peak_gib(
            nnz, casts=False, reordered=False
        ),
        "prep_peak_gib_worst_case": sizing.prep_peak_gib(
            nnz, casts=True, reordered=True
        ),
        "scoring_container_peak_gib": sizing.estimated_peak_gib(nnz),
        "fraction_of_hard_cap": nnz / sizing.HARD_CAP_NNZ,
    }


def collect(run_id: str) -> dict:
    run = config.artifact_root() / run_id
    gen_path = run / "generation_diagnostics.json"
    val_path = run / "validation.json"
    entry: dict = {"run_id": run_id, "run_dir": str(run)}

    if gen_path.exists():
        gen = json.loads(gen_path.read_text(encoding="utf-8"))
        storage = gen["storage"]
        entry["generation"] = {
            "trial": gen["trial"]["id"],
            "kind": gen["trial"]["kind"],
            "is_pilot": gen["is_pilot"],
            "n_cells": gen["shape"]["n_cells"],
            "n_perturbations": gen["shape"]["n_perturbations"],
            "contexts": gen["shape"]["contexts"],
            "stored_entries": storage["stored_entries"],
            "stored_entries_per_cell": storage["stored_entries_per_cell"],
            "projected_entries_at_full_shape": storage[
                "projected_entries_at_full_shape"
            ],
            "fraction_of_global_cap_at_this_size": storage[
                "fraction_of_global_cap_at_this_size"
            ],
            "projected_fraction_of_cap": storage["projected_fraction_of_cap"],
            "file_gib": storage["file_bytes"] / GiB,
            "projected_file_gib_at_full_shape": (
                None if storage["projected_file_bytes_at_full_shape"] is None
                else storage["projected_file_bytes_at_full_shape"] / GiB
            ),
            "basal_seconds": gen["runtime"]["basal_profiles_seconds"],
            "generation_seconds": gen["runtime"]["generation_seconds"],
            "total_seconds": gen["runtime"]["total_seconds"],
            "seconds_per_block": gen["runtime"]["seconds_per_block"],
            "projected_generation_seconds_at_full_shape": gen["runtime"][
                "projected_generation_seconds_at_full_shape"
            ],
            "peak_rss_gib": gen["memory"]["peak_rss_gib"],
            "disk_free_gib_before": gen["memory"]["resources_before"][
                "disk_free_gib"
            ],
            "disk_free_gib_after": gen["memory"]["resources_after"]["disk_free_gib"],
            "ram_available_gib_before": gen["memory"]["resources_before"][
                "ram_available_gib"
            ],
            "context_provenance_ok": gen["context_provenance"][
                "all_labels_match_nearest_basal"
            ],
        }
        entry["sizing_model_for_this_file"] = sizing_model(storage["stored_entries"])
        if storage["projected_entries_at_full_shape"] and gen["is_pilot"]:
            entry["sizing_model_projected_full_shape"] = sizing_model(
                int(storage["projected_entries_at_full_shape"])
            )

    if val_path.exists():
        val = json.loads(val_path.read_text(encoding="utf-8"))
        dry = val.get("vcc_prep_dry_run") or {}
        pkg = val.get("vcc_prep_package") or {}
        entry["validation"] = {
            "contract_all_checks_pass": val["contract_recheck"]["all_checks_pass"],
            "failed_checks": [
                k for k, v in val["contract_recheck"]["checks"].items() if not v
            ],
            "contract_recheck_seconds": val["contract_recheck"].get("seconds"),
            "context_provenance_ok": val["context_provenance"][
                "all_labels_match_nearest_basal"
            ],
            "context_provenance_seconds": val["context_provenance"].get("seconds"),
            "prep_dry_run_exit": dry.get("exit_code"),
            "prep_dry_run_timed_out": dry.get("timed_out"),
            "prep_dry_run_seconds": dry.get("elapsed_seconds"),
            "prep_package_exit": pkg.get("exit_code") if pkg else None,
            "prep_package_timed_out": pkg.get("timed_out") if pkg else None,
            "prep_package_seconds": pkg.get("elapsed_seconds") if pkg else None,
            "vcc_bytes": (
                None if val.get("vcc_artifact") is None
                else val["vcc_artifact"]["bytes"]
            ),
            "vcc_sha256": (
                None if val.get("vcc_artifact") is None
                else val["vcc_artifact"]["sha256"]
            ),
            "prediction_sha256": val["prediction"].get("sha256"),
            "prediction_bytes": val["prediction"].get("bytes"),
        }
    return entry


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runs", nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    if args.out.exists() and not args.allow_overwrite:
        raise SystemExit(f"{args.out} exists; write to a new --out")

    ch = config.challenge()
    snap = snapshot(config.artifact_root())
    payload = {
        "generated_utc": None,
        "machine": snap.as_dict(),
        "environment": environment_fingerprint(),
        "official_full_shape": {
            "n_perturbations": ch.n_perturbations,
            "cells_per_pert": ch.cells_per_pert,
            "n_contexts": len(ch.contexts_validation),
            "n_cells": ch.n_cells_total,
            "n_genes": ch.n_genes,
            "max_stored_entries": ch.max_stored_entries,
            "per_cell_budget": ch.max_stored_per_cell,
            "max_counts_per_cell": ch.max_counts_per_cell,
        },
        "runs": [collect(r) for r in args.runs],
        "note": (
            "Every value is copied from a run's own diagnostics or validation "
            "JSON. Nothing here is a VCC score and nothing has been uploaded."
        ),
    }
    from datetime import datetime, timezone

    payload["generated_utc"] = datetime.now(timezone.utc).isoformat()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    print(f"machine: RAM total {snap.ram_total_bytes / GiB:.2f} GiB, "
          f"available {snap.ram_available_gib:.2f} GiB, "
          f"disk free {snap.disk_free_gib:.2f} GiB\n")
    header = (f"{'run':10s} {'trial':18s} {'cells':>9s} {'nnz':>14s} "
              f"{'/cell':>7s} {'cap%':>6s} {'GiB':>7s} {'gen s':>7s} {'peak GiB':>9s}")
    print(header)
    print("-" * len(header))
    for entry in payload["runs"]:
        g = entry.get("generation")
        if not g:
            print(f"{entry['run_id']:10s} (no generation diagnostics)")
            continue
        print(f"{entry['run_id']:10s} {g['trial']:18s} {g['n_cells']:9,d} "
              f"{g['stored_entries']:14,d} {g['stored_entries_per_cell']:7,.0f} "
              f"{g['fraction_of_global_cap_at_this_size'] * 100:5.1f}% "
              f"{g['file_gib']:7.2f} {g['generation_seconds']:7.0f} "
              f"{(g['peak_rss_gib'] or 0):9.2f}")
    print()
    for entry in payload["runs"]:
        s = entry.get("sizing_model_for_this_file", {})
        if s.get("available"):
            print(f"{entry['run_id']:10s} vcc prep peak (CLI model): "
                  f"{s['prep_peak_gib_no_cast_in_order']:.1f} GiB "
                  f"[{s['scipy_bytes_per_nnz']} B/nnz"
                  f"{', crosses int32 index limit' if s['crosses_int32_index_limit'] else ''}]")
    print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
