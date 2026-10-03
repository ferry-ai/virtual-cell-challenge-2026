"""Recount biological groups and technical coverage from small, recorded metadata."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit("Refusing to replace an existing audit")
    root = Path(__file__).resolve().parents[3]
    inputs = []

    def read(rel):
        raw = (root / rel).read_bytes()
        inputs.append({"path": rel, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        return raw

    pilot = {}
    for fold in ("h1", "hepg2", "rpe1"):
        c = json.loads(read(f"reports/modelli/rete_cellulare_2026-10-03/esito/train_{fold}_r3/coverage.json"))
        pilot[fold] = {"groups": sorted(c["loss_shares"]["by_group"]), "admitted_training_cells": c["admitted_training_cells"]}
    groups = sorted(set().union(*(v["groups"] for v in pilot.values())))
    mapping = json.loads(read("reports/sorgenti/ingestione_completa_2026-10-03/orion/line_groups_expanded_v1.json"))
    proposed = sorted(set(mapping["contexts"].values()) | set(mapping["study_prefixes"].values()))
    kolf = json.loads(read("reports/sorgenti/ingestione_completa_2026-10-03/kolf/esito_verifica_r1/source_complete.json"))
    receipts = json.loads(read("reports/analisi/candidato_ibrido_2026-10-03/training_receipts.json"))
    technical = {}
    for run, data in receipts["runs"].items():
        r = {key: val["content"] for key, val in data["receipts"].items()}
        c = r["train/coverage.json"]
        shares = c["loss_shares"]["by_group"]
        expected = 1 / len(shares)
        violations = {g: v for g, v in shares.items() if abs(v - expected) > 0.02}
        technical[run] = {
            "exit_code": r["kernel_done.json"]["return_code"],
            "health_passed": r["train/health.json"]["passed"],
            "shard_hash_differences": r["train/verify.json"]["differ"],
            "cell_class_leakage_passed": c["leakage_check"]["passed"],
            "anchor_derived_leakage_note": "Not tested by the cell-class check; J/T excluded from scientific conclusions by protocol amendment 9",
            "epochs_done": c["epochs_done"], "stop": c["stop"],
            "distinct_cells_seen": c["distinct_cells_seen"],
            "admitted_training_cells": c["admitted_training_cells"],
            "fraction_admitted_cells_seen": c["distinct_cells_seen"] / c["admitted_training_cells"],
            "data_wait_fraction": c["throughput"]["data_wait_fraction"],
            "expected_group_share": expected, "allowed_absolute_deviation": 0.02,
            "actual_group_shares": shares, "share_violations": violations,
            "group_balance_passed": not violations,
            "admitted_but_unseen_keys": [v for v in c["by_key"] if v["admitted_offered"] > 0 and v["distinct_drawn"] == 0],
            "scientific_metrics_opened": False,
            "full_technical_acceptance": "Not assessed here: evaluation completeness and other gates still required",
        }
    code = ast.parse(read("reports/modelli/rete_ancorata_2026-10-03/anchors.py"))
    anchor_groups = next(ast.literal_eval(node.value) for node in code.body if isinstance(node, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == "CELL_GROUPS" for t in node.targets))
    out = {
        "utc": datetime.now(timezone.utc).isoformat(), "kind": "measured_from_recorded_metadata",
        "pilot_groups": groups, "pilot_group_count": len(groups), "pilot_by_fold": pilot,
        "proposed_groups": proposed, "proposed_group_count": len(proposed),
        "proposed_but_not_in_pilot": sorted(set(proposed) - set(groups)),
        "proposal_warning": mapping["about"], "related_groups": mapping["related"],
        "anchor_source_allowlist": anchor_groups,
        "kolf": {"ok": kolf["ok"], "utc": kolf["utc"], "totals": kolf["totals"], "inventory": kolf["inventory"],
                 "sample_count_warning": "Coarse context-target caps only; no stratification by donor, guide, library or phenotype; controls separate"},
        "technical_training_audit": technical,
        "hypothetical_iid_sampling": {"rare_population_fraction": 0.01, "n": 64, "probability_of_missing_it": 0.99 ** 64},
        "inputs": inputs,
    }
    a.out.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pilot_groups": groups, "catalogue_groups": len(proposed), "technical_training_audit": technical}, indent=2))


if __name__ == "__main__":
    main()
