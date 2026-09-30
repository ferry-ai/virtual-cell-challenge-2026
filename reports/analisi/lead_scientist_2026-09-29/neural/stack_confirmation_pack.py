"""Separate prospective confirmation inputs; reuse exact pilot source/dest NTC.

No model, weights, destination perturbed cells, scoring or upload. Targets are
selected only from metadata and must match the pre-score expansion registration.
The resulting bundle is structurally compatible with the frozen pilot adapter;
using it for inference still requires a separately reviewed confirmation job.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

import stack_pilot as pilot

HERE = Path(__file__).resolve().parent
EXPECTED = ["PCBP1", "CDC20", "RNF31", "KIF11", "C7orf26", "RPS24", "GINS2", "YRDC", "DESI1", "MRPL38", "RSL1D1", "MYBBP1A"]
REUSED = ("source_00.h5ad", "destination_controls.h5ad")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def select(eligible, development, confirmation, pilot_targets, counts):
    reserve = set(eligible) - set(development) - set(confirmation) - set(pilot_targets)
    targets = sorted((t for t in reserve if counts.get(t, 0) >= 64),
                     key=lambda t: hashlib.sha256(f"StackConfirm:20260929:{t}".encode()).hexdigest())[:12]
    if len(targets) != 12:
        raise ValueError("Fewer than twelve eligible reserve targets; no substitution")
    return targets


def verify_reused(bundle, expected=None):
    manifest = load_json(bundle / "bundle.json")
    actual = {}
    for name in REUSED:
        actual[name] = pilot.sha(bundle / name)
        if actual[name] != manifest["files"][name]:
            raise ValueError(f"Pilot control file differs from its manifest: {name}")
    if expected is not None and actual != expected:
        raise ValueError("Pilot controls differ from confirmation plan")
    return manifest, actual


def plan(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    generator = load_json(args.generator_manifest)
    registration = load_json(args.registration)
    pilot_manifest, reused = verify_reused(args.pilot_bundle)
    counts = Counter()
    with args.source_groups.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["is_ntc"] != "True":
                counts[row["gene"]] += int(row["n_cells_obs"])
    targets = select(generator["eligible"], generator["development"], generator["confirmation"],
                     pilot_manifest["targets"], counts)
    if targets != EXPECTED or targets != registration["confirmation_targets_original"]:
        raise ValueError("Metadata selection differs from pre-score registration; do not substitute")
    # Verify small source manifests against the earlier metadata-only registration.
    known_hashes = set(registration["hashes"].values())
    if pilot.sha(args.source_groups) not in known_hashes or pilot.sha(args.generator_manifest) not in known_hashes:
        raise ValueError("Source groups or generator target split differ from registration")
    result = {"status": "planned_no_expression_read_no_scores", "role": "prospective_confirmation",
        "targets": targets, "source_counts": {t: counts[t] for t in targets},
        "source_min_cells": 64, "source_max_cells": 128, "seed": pilot.SEED, "n_output": pilot.N_OUTPUT,
        "selection_rule": "First12 SHA256 StackConfirm:20260929:<target> in eligible minus development, confirmation and pilot; source>=64",
        "source_cell_sampling": "Frozen pilot rng_for('source:<target>'), max128 without replacement",
        "source_size": args.source.stat().st_size,
        "source_groups_sha256": pilot.sha(args.source_groups),
        "generator_manifest_sha256": pilot.sha(args.generator_manifest),
        "registration_sha256": pilot.sha(args.registration),
        "pilot_bundle_manifest_sha256": pilot.sha(args.pilot_bundle / "bundle.json"),
        "reused_files": reused, "effects_sha256": pilot.sha(args.effects),
        "packer_sha256": pilot.sha(__file__), "adapter_sha256": pilot.sha(pilot.__file__),
        "proposal_sha256": pilot.sha(HERE / "PROPOSTA_STACK_ESTENSIONE.md"),
        "protocol_sha256": pilot.sha(HERE / "PROTOCOLLO_STACK_CONFERMA.md"),
        "inference_adapter_sha256": pilot.sha(HERE / "stack_confirmation_infer.py"),
        "scoring_code_sha256": pilot.sha(HERE / "stack_confirmation_score.py"),
        "stack_commit": pilot.STACK_COMMIT, "checkpoint_revision": pilot.STACK_REVISION,
        "inference_authorized": False,
        "decision_rule_status": "Frozen protocol; execution still requires parent authorization"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    pilot.write_json(args.out, result)
    print(json.dumps({"targets": targets, "new_source_rows": sum(min(counts[t], 128) for t in targets),
                      "controls_reused_without_resampling": True, "plan": str(args.out)}))


def prepare(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    planned = load_json(args.plan)
    if planned["targets"] != EXPECTED or planned["seed"] != pilot.SEED:
        raise ValueError("Confirmation target registration changed")
    for actual, expected, label in [
        (pilot.sha(__file__), planned["packer_sha256"], "packer"),
        (pilot.sha(pilot.__file__), planned["adapter_sha256"], "adapter"),
        (pilot.sha(HERE / "PROPOSTA_STACK_ESTENSIONE.md"), planned["proposal_sha256"], "proposal"),
        (pilot.sha(HERE / "PROTOCOLLO_STACK_CONFERMA.md"), planned["protocol_sha256"], "protocol"),
        (pilot.sha(HERE / "stack_confirmation_infer.py"), planned["inference_adapter_sha256"], "inference adapter"),
        (pilot.sha(HERE / "stack_confirmation_score.py"), planned["scoring_code_sha256"], "confirmation scorer"),
        (pilot.sha(args.effects), planned["effects_sha256"], "effects"),
        (pilot.sha(args.pilot_bundle / "bundle.json"), planned["pilot_bundle_manifest_sha256"], "pilot bundle"),
    ]:
        if actual != expected:
            raise ValueError(f"Frozen {label} changed")
    old, reused = verify_reused(args.pilot_bundle, planned["reused_files"])
    if args.source.stat().st_size != planned["source_size"]:
        raise ValueError("Original source size changed")
    source_genes, source_columns = pilot.unique_first(pilot.genes_of(args.source))
    if list(source_genes) != list(pilot.genes_of(args.pilot_bundle / "source_00.h5ad")):
        raise ValueError("Original source axis differs from reused controls")
    dest_genes = pilot.genes_of(args.pilot_bundle / "destination_controls.h5ad")
    rows = pilot.rows_for_labels(args.source, planned["targets"])
    if any(len(rows[t]) != planned["source_counts"][t] for t in planned["targets"]):
        raise ValueError("Original source target counts differ from frozen metadata")
    selected = {t: pilot.pick(rows[t], 128, f"source:{t}") for t in planned["targets"]}
    with np.load(args.effects, allow_pickle=False) as z:
        if "observed" not in z or z["observed"].dtype.kind != "b":
            raise ValueError("Frozen transfer requires explicit boolean observed mask")
        ti = pd.Index(z["targets"].astype(str)).get_indexer(planned["targets"])
        gi = pd.Index(z["genes"].astype(str)).get_indexer(dest_genes)
        if np.any(ti < 0):
            raise ValueError("Frozen transfer lacks a confirmation target")
        effect = np.zeros((12, len(dest_genes)), dtype=np.float32)
        observed = np.zeros(effect.shape, dtype=bool)
        have = gi >= 0
        effect[:, have] = z["lfc"][ti][:, gi[have]]
        observed[:, have] = z["observed"][ti][:, gi[have]]
    if not np.isfinite(effect).all():
        raise ValueError("Non-finite frozen transfer")
    args.out.mkdir(parents=True)
    for name in REUSED:
        shutil.copyfile(args.pilot_bundle / name, args.out / name)
        if pilot.sha(args.out / name) != reused[name]:
            raise ValueError("Reused control copy differs")
    for i, target in enumerate(planned["targets"], 1):
        pilot.write_counts(args.out / f"source_{i:02d}.h5ad",
                           pilot.read_rows(args.source, selected[target])[:, source_columns], source_genes, target)
    np.savez_compressed(args.out / "transfer.npz", targets=planned["targets"], genes=dest_genes,
                        lfc=effect, observed=observed)
    manifest = planned | {"status": "prepared_no_model_no_scores", "plan_sha256": pilot.sha(args.plan),
        "source": str(args.source), "destination": "Exact controls reused from pilot bundle064",
        "destination_size": old["destination_size"],
        "duplicate_gene_policy": "first column per symbol, identical to frozen pilot",
        "source_selected_rows": {t: r.tolist() for t, r in selected.items()} |
                                {pilot.CONTROL: old["source_selected_rows"][pilot.CONTROL]},
        "destination_control_rows": old["destination_control_rows"],
        "destination_truth_rows_read": 0, "files": {p.name: pilot.sha(p) for p in sorted(args.out.iterdir())}}
    pilot.write_json(args.out / "bundle.json", manifest)
    print(json.dumps({"bundle": str(args.out), "target_count": 12, "reused_controls_byte_identical": True}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="phase", required=True)
    for phase in ("plan", "prepare"):
        q = commands.add_parser(phase)
        for name in ("source", "pilot-bundle", "effects", "out"):
            q.add_argument("--" + name, type=Path, required=True)
        for name in (("source-groups", "generator-manifest", "registration") if phase == "plan" else ("plan",)):
            q.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    {"plan": plan, "prepare": prepare}[args.phase](args)


if __name__ == "__main__":
    main()
