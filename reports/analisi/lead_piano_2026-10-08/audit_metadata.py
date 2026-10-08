"""Recount existing metadata only; never open cellular matrices or access the network."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BANK = ROOT / "reports/modelli/banca_canonica_2026-10-07"


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    paths = {
        "registry": BANK / "registro_fonti_r1.json",
        "consumption": BANK / "fit/r1/completion/consumo.json",
        "release": BANK / "fit/release_r1.json",
        "t36": ROOT / "reports/invii/prediction_t36_2026-10-06/comparison.json",
        "stage100": ROOT / "scripts/100_build_context_effects.py",
        "registry_code": BANK / "registro.py",
    }
    inputs = {k: {"path": str(p.relative_to(ROOT)).replace("\\", "/"),
                  "bytes": p.stat().st_size,
                  "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
              for k, p in paths.items()}
    registry = json.loads(paths["registry"].read_text(encoding="utf-8"))
    consumption = json.loads(paths["consumption"].read_text(encoding="utf-8"))
    score = json.loads(paths["t36"].read_text(encoding="utf-8"))
    units, sources = registry["units"], registry["sources"]
    voted = {n for n, s in sources.items() if s["role"] == "voto"}
    voted_units = {u for n in voted for u in sources[n]["units"]}
    excluded = set(units) - voted_units
    bank_rows = sum(u["cells"]["all"] for u in units.values())
    shared_h1 = min(units[u]["cells"]["control"] for u in ("h1_train", "h1_val"))
    represented = sum(units[u]["cells"].get("control", 0) +
                      units[u]["cells"].get("panel_target", 0) for u in voted_units) - shared_h1
    checks = {
        "bank_total_reconciled": bank_rows == registry["summary"]["bank_cells"],
        "represented_reconciled": represented == registry["summary"]["cells_in_bank_rows_read_by_voted_sources"],
        "expected_verified_read_equal": set(consumption["sources_expected"]) ==
            set(consumption["sources_verified"]) == set(consumption["sources_read_by_stage100"]) == voted,
        "release_hash_matches": inputs["release"]["sha256"] == consumption["release_sha256"],
        "no_unexplained_target_changes": not consumption["targets_changed_outside_added_votes"],
        "not_claimed_complete": registry["claims_complete_corpus"] is False,
    }
    categories = Counter(r["destination"] for r in registry["catalogue"])
    out = {
        "utc": datetime.now(timezone.utc).isoformat(), "inputs": inputs,
        "claim_type": "Recount of stored metadata; no raw-data, live-cloud, training or predictive verification",
        "checks": checks,
        "bank": {"units": len(units), "rows_in_cell_counts": bank_rows,
                 "known_shared_h1_controls": shared_h1,
                 "after_known_h1_dedup_only": bank_rows - shared_h1,
                 "voted_units": len(voted_units), "not_voted_units": len(excluded),
                 "cells_in_not_voted_units": sum(units[u]["cells"]["all"] for u in excluded),
                 "not_voted_pct_including_duplicate_k562": 100 * sum(units[u]["cells"]["all"] for u in excluded) / bank_rows,
                 "represented_controls_plus_panel": represented,
                 "represented_pct_of_recorded_bank": 100 * represented / bank_rows,
                 "off_panel_cells_in_voted_units": sum(units[u]["cells"].get("other_target", 0) for u in voted_units),
                 "representation_note": "Estimated from bank row metadata, not individual cells read by stage 100; excludes historical K562 BULK and includes controls of zero-panel tables.",
                 "sample_gb_recorded": registry["summary"]["derived_samples_gb"],
                 "sample_levels_recorded_subset": {level: sum(u["samples_levels"].get(level, 0) for u in units.values() if isinstance(u.get("samples_levels"), dict)) for level in ("32", "64", "128")},
                 "sample_levels_missing_units": sorted(n for n, u in units.items() if not isinstance(u.get("samples_levels"), dict)),
                 "sample_note": "Recorded subset only. Nested levels overlap; totals are not unique cells, and are not evidence of training exposure."},
        "sources": {"loaded": len(voted), "with_panel_votes": sum(sources[n].get("panel_targets_voted", 0) > 0 for n in voted),
                    "without_panel_votes": sorted(n for n in voted if not sources[n].get("panel_targets_voted")),
                    "changed_targets": consumption["targets_with_added_votes"]},
        "excluded_units": {u: {"cells": units[u]["cells"], "destination": units[u]["destination"]} for u in sorted(excluded)},
        "catalogue": {"records": len(registry["catalogue"]), "destinations": dict(categories),
                      "outside_catalogue": registry["summary"]["units_outside_catalogue"]},
        "official": {k: score[k] for k in ("score_avg", "reference_t28", "t36_minus_t28", "scaled_published", "rule_branch")},
    }
    if not all(checks.values()):
        raise SystemExit(f"Metadata consistency checks failed: {checks}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(out, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({k: out[k] for k in ("checks", "bank", "sources", "catalogue")}, indent=2))


if __name__ == "__main__":
    main()
