"""Write the frozen C/T/J fold manifest of the independent validation (contract v1).

The manifest is the single machine-readable source of: lineage groups with every known
source/table/unit alias, the leave-one-lineage-out C folds on the panel, the hash rule that
assigns any target symbol to a hidden group (T and J regimes), the protected reserves, the
axis and panel identities, the emission and the seeds. It reads only small committed
metadata (the canonical registry and the frozen releases); no response matrix is opened.

    py build_manifest.py <out.json>      (exclusive create: a revision needs a new name)
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REGISTRY = REPO / "reports/modelli/banca_canonica_2026-10-07/registro_fonti_r1.json"
RELEASE_R1 = REPO / "reports/modelli/banca_canonica_2026-10-07/fit/release_r1.json"
RELEASE_T1 = REPO / "reports/modelli/dati_transfer_2026-10-08_01a11c34/release_t1_r1.json"
T36_RECIPE = REPO / "reports/invii/trial_2026-10-06/t36_recipe_extbank.json"
CONSUMO_R1 = REPO / "reports/modelli/banca_canonica_2026-10-07/fit/r1/completion/consumo.json"
HIDDEN_GROUPS = 5          # sha256(symbol) mod 5; group 0 is the J/T test, 1-4 are inner validation
J_TEST_GROUP = 0

# Lineage = the unit a C fold holds out. It is wider than the registry's `line_group` where two
# registry groups are one cell line and its derivative: HEK293T is HEK293 with the SV40 large T
# antigen, so a fold that calls HEK293T "new" must not train on HEK293 responses (Xu 2023).
LINEAGES = {
    "K562": {"registry_groups": ["K562"],
             "tables": ["k562", "k562_essential", "k562_gwps_sc", "dixit2016", "norman2019"],
             "units": ["k562_essential", "k562_gwps_a", "k562_gwps_b", "dixit2016_d7", "dixit2016_d13",
                       "dixit2016_high_moi", "norman2019"],
             "name_patterns": ["k562", "dixit", "norman", "adamson", "replogle_k562", "gwps"]},
    "CD4T": {"registry_groups": ["CD4T"],
             "tables": ["cd4_mix", "cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr", "shifrut2018"],
             "units": [f"D{d}_{c}" for d in (1, 2, 3, 4) for c in ("Rest", "Stim8hr", "Stim48hr")] + ["shifrut2018"],
             "name_patterns": ["cd4", "shifrut", "marson"]},
    "HCT116": {"registry_groups": ["HCT116"], "tables": ["orion_hct116"], "units": ["orion_hct116"],
               "name_patterns": ["hct116", "dld"]},
    "HEK293": {"registry_groups": ["HEK293", "HEK293T"], "tables": ["orion_hek293t", "xu2023"],
               "units": ["orion_hek293t", "xu2023"], "name_patterns": ["hek293", "xu2023"]},
    "iPSC": {"registry_groups": ["iPSC"],
             "tables": ["kolf_pan_genome", "kolf_strong", "kolf_chromatin", "kolf_metabolic", "hipsci_targeted_19",
                        "tian2019_ipsc"],
             "units": ["kolf_pan_genome", "kolf_strong", "kolf_chromatin", "kolf_metabolic", "hipsci_targeted_19",
                       "hipsci_gw_fitness", "hipsci_gw_nonfitness", "tian2019_ipsc"],
             "name_patterns": ["kolf", "hipsci", "ipsc"]},
    "H1": {"registry_groups": ["H1"], "tables": ["h1"], "units": ["h1_train", "h1_val"],
           "name_patterns": ["h1"]},
    "neuron": {"registry_groups": ["neuron"], "tables": ["tian2019_neuron", "tian2021_crispri", "tian2021_crispra"],
               "units": ["tian2019_neuron", "tian2021_crispri", "tian2021_crispra"], "name_patterns": ["neuron", "tian2021"]},
    "HepG2": {"registry_groups": ["HepG2"], "tables": ["hepg2_nadig"], "units": ["hepg2_nadig"],
              "name_patterns": ["hepg2"]},
    "Jurkat": {"registry_groups": ["Jurkat"], "tables": ["jurkat_nadig"],
               "units": ["jurkat_nadig", "datlinger2017", "datlinger2021"], "name_patterns": ["jurkat", "datlinger"]},
    "RPE1": {"registry_groups": ["RPE1"], "tables": ["rpe1"], "units": ["rpe1"], "name_patterns": ["rpe1"]},
    "A549": {"registry_groups": ["A549"], "tables": ["a549_ko"], "units": ["a549_ko"], "name_patterns": ["a549"]},
    "Calu3": {"registry_groups": ["Calu3"], "tables": ["sunshine2023"], "units": ["sunshine2023"],
              "name_patterns": ["calu3", "sunshine"]},
    "melanoma": {"registry_groups": ["melanoma"], "tables": ["frangieh2021"], "units": ["frangieh2021"],
                 "name_patterns": ["melanoma", "frangieh"]},
    "THP1": {"registry_groups": ["THP1"], "tables": [], "units": ["papalexi2021_arrayed"],
             "name_patterns": ["thp1", "papalexi"]},
}

# C folds on the panel: a lineage whose own table carries panel targets with a finite SE (or parts with one).
C_FOLDS = [
    {"id": "C-K562", "lineage": "K562", "truth": [{"table": "k562", "role": "primary"}]},
    {"id": "C-CD4T", "lineage": "CD4T", "truth": [{"table": "cd4_Rest", "role": "primary"},
                                                  {"table": "cd4_Stim8hr", "role": "stimulus"},
                                                  {"table": "cd4_Stim48hr", "role": "stimulus"}]},
    {"id": "C-HCT116", "lineage": "HCT116", "truth": [{"table": "orion_hct116", "role": "primary"}]},
    {"id": "C-HEK293", "lineage": "HEK293", "truth": [{"table": "orion_hek293t", "role": "primary"}]},
    {"id": "C-iPSC", "lineage": "iPSC", "truth": [{"table": "kolf_pan_genome", "role": "primary"},
                                                  {"table": "kolf_strong", "role": "second_library"}]},
    {"id": "C-H1", "lineage": "H1", "truth": [{"table": "h1", "role": "primary"}]},
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hidden_group(symbol: str) -> int:
    """Group of a target symbol, fixed by the symbol alone: it never moves when the corpus grows."""
    return int(hashlib.sha256(symbol.encode("utf-8")).hexdigest(), 16) % HIDDEN_GROUPS


def main() -> None:
    out = Path(sys.argv[1])
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    r1 = json.loads(RELEASE_R1.read_text(encoding="utf-8"))
    t1 = json.loads(RELEASE_T1.read_text(encoding="utf-8"))
    t36 = json.loads(T36_RECIPE.read_text(encoding="utf-8"))
    # every bank unit must belong to exactly one lineage, with the registry's own group
    unit_lineage = {}
    for name, lin in LINEAGES.items():
        for u in lin["units"]:
            assert u not in unit_lineage, u
            unit_lineage[u] = name
    problems = []
    for unit, record in registry["units"].items():
        lin = unit_lineage.get(unit)
        if lin is None:
            problems.append(f"unit without lineage: {unit}")
        elif not set(record["line_group"]) <= set(LINEAGES[lin]["registry_groups"]):
            problems.append(f"{unit}: registry group {record['line_group']} outside lineage {lin}")
    for unit in unit_lineage:
        if unit not in registry["units"]:
            problems.append(f"lineage unit not in the registry: {unit}")
    known_tables = (set(r1["voted"]) | set(r1["derived_not_voted"]) | set(r1["derived_not_admitted"])
                    | set(r1["mix"]["cd4_parts"]))
    table_lineage = {}
    for name, lin in LINEAGES.items():
        for t in lin["tables"]:
            assert t not in table_lineage, t
            table_lineage[t] = name
    for t in sorted(known_tables):
        if t not in table_lineage:
            problems.append(f"release table without lineage: {t}")
    if problems:
        raise SystemExit("\n".join(problems))
    consumo = json.loads(CONSUMO_R1.read_text(encoding="utf-8"))
    panel = sorted(consumo["votes_per_target"])          # the 300 panel symbols, as the r1 fit read them
    assert len(panel) == 300 and len(set(panel)) == 300
    votes = {t: sorted(v) for t, v in consumo["votes_per_target"].items()}
    arms = {
        "T0": {"what": "t36 reference: the 13 sources of the scored submission", "sources": sorted(r1["reference"]["sources"]),
               "recipe_sha256_production": r1["reference"]["recipe_sha256"]},
        "R1": {"what": "canonical release r1 of 7 October, 17 sources, as frozen", "sources": sorted(r1["voted"]),
               "release_sha256": sha(RELEASE_R1)},
        "T1": {"what": "DATI-TRANSFER T1: release r1 without the Tian 2019 neuron vote on RFK, 16 sources",
               "sources": sorted(t1["voted"]), "release_sha256": sha(RELEASE_T1)},
        "P4": {"what": "the four lineages of the t22/t25/t28 recipe, on the t36 tables: K562, CD4T, HCT116, HEK293T",
               "sources": ["cd4_mix", "k562", "orion_hct116", "orion_hek293t"]},
    }
    assert sorted(t36["contexts"]["A"]["weights"]) == arms["T0"]["sources"]
    folds = []
    for f in C_FOLDS:
        lin = LINEAGES[f["lineage"]]
        left = {a: sorted(set(v["sources"]) - set(lin["tables"])) for a, v in arms.items()}
        folds.append({**f, "regime": "C", "exclude_tables": sorted(lin["tables"]), "exclude_units": sorted(lin["units"]),
                      "exclude_name_patterns": lin["name_patterns"], "arm_sources": left,
                      # from the r1 consumption receipt: panel targets that keep at least one vote in the fold
                      "panel_targets_still_voted": {a: sum(1 for t in panel if set(votes[t]) & set(src))
                                                    for a, src in left.items()},
                      "targets": "panel targets with a finite prediction and a finite primary truth",
                      "inference_inputs": "unperturbed controls of the held lineage only"})
    doc = {
        "schema": "vcc2026.validazione.folds/1", "version": "v1",
        "frozen_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "author": "VALIDAZIONE, Claude Code session 8a8ca58a",
        "inputs": {str(p.relative_to(REPO).as_posix()): {"bytes": p.stat().st_size, "sha256": sha(p)}
                   for p in (REGISTRY, RELEASE_R1, RELEASE_T1, T36_RECIPE, CONSUMO_R1)},
        "axis": {"genes": 18533, "sha256": r1["axis_sha256"], "file": "raw/controls/gene_names.csv",
                 "order": "official axis order, no duplicates"},
        "panel": {"targets": 300, "panel_sha256": r1["panel_sha256"],
                  "file_sha256": "f57edd7b912ebd718efc7ee9d0f334772513e7cc418d133ce525470e373b3276",
                  "file": "raw/controls/pert_counts.csv"},
        "interface": {"format": "stage-100 npz: targets, genes, lfc, observed",
                      "lfc": "float32 natural-log fold change, amplitude and cis head applied, emission scale NOT applied",
                      "observed": "bool, same shape; an unmeasured or unpredicted pair is False and exactly 0",
                      "log2_inputs": "multiply by ln 2 and declare it; p_de and delta_p are diagnostics, never effects"},
        "emission": {"name": "t28", "trial": "trial-ext-profile", "effects_scale": 1.5, "gene_dispersion": True,
                     "gene_dispersion_scale": 1.0, "cells_per_target": 400, "generator_seed": 20260912,
                     "generator_seed_indices": [0, 1, 2, 3, 4], "bench_seed": 2026,
                     "streams": "one random stream per (seed, target), shared by every arm"},
        "scorer": {"package": "cell-eval2", "version": "0.16.0", "config": "vcc2026",
                   "wheel_sha256": "c78428ba705a94536e4a55464a34d1905aa5730d4f7e52ea8dbef4e7171d4fbe"},
        "protected": {"h1_test": "never read by any fold, arm, statistic, calibration or checkpoint under evaluation",
                      "final_set": "D, E, F are not available and are never a validation",
                      "development_lines": ["H1", "HepG2", "RPE1", "Jurkat", "K562"],
                      "development_note": "read repeatedly by six-member benches: never an independent confirmation"},
        "lineages": LINEAGES,
        "arms": arms,
        "folds_C": folds,
        "hidden_target_rule": {"function": "int(sha256(symbol utf-8).hexdigest(), 16) % 5", "groups": HIDDEN_GROUPS,
                               "test_group": J_TEST_GROUP, "inner_groups": [1, 2, 3, 4],
                               "components": "a perturbation label is hidden if ANY of its component genes, after "
                                             "alias reconciliation to the official symbol, is in the hidden group; "
                                             "guides, replicates and combinations follow their genes",
                               "scope": "every source, table, derived statistic, embedding fitted on responses, "
                                        "common vector, pooling and calibration, before it is computed"},
        "regimes": {
            "C": "target seen elsewhere, lineage held out: folds_C",
            "T": "target hidden (test_group) in every source, lineage seen: per lineage, no table removed",
            "J": "folds_C x hidden test_group: lineage held out AND target hidden in every source"},
        "panel_hidden_groups": {str(g): sorted(t for t in panel if hidden_group(t) == g) for g in range(HIDDEN_GROUPS)},
        "note": "panel_hidden_groups lists the 300 panel symbols; the rule applies to any symbol of any source. "
                "A same-target transfer has no T/J prediction beyond its cis head: that is declared, not a leak.",
    }
    with out.open("x", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    print(json.dumps({"folds_C": [f["id"] for f in folds], "lineages": len(LINEAGES), "units": len(unit_lineage),
                      "tables": len(table_lineage), "panel_symbols": len(panel),
                      "hidden_group_sizes": {g: len(v) for g, v in doc["panel_hidden_groups"].items()},
                      "sha256": sha(out)}))


if __name__ == "__main__":
    main()
