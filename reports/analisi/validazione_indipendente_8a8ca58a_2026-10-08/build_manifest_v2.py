"""Write manifest v2 as v1 plus three declared changes; the folds, the arms and the hidden-target rule are v1's.

1. the primary discrimination measure of level A is `disc95` (v1: `disc`, unusable on C-K562);
2. the alias pattern `dld` leaves the HCT116 lineage (DLD-1 is another cell line; no table was affected);
3. level B is recorded: the two folds with extracted real cells, their kernels and the hashes of the cells.

    py build_manifest_v2.py <manifest_fold_v1.json> <out v2.json>
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> None:
    v1_path, out = Path(sys.argv[1]), Path(sys.argv[2])
    doc = json.loads(v1_path.read_text(encoding="utf-8"))
    assert doc["version"] == "v1"
    folds_before = json.dumps([{k: f[k] for k in ("id", "lineage", "exclude_tables", "exclude_units", "arm_sources",
                                                    "truth")} for f in doc["folds_C"]], sort_keys=True)
    doc["version"] = "v2"
    doc["schema"] = "vcc2026.validazione.folds/2"
    doc["frozen_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    doc["supersedes"] = {"version": "v1", "path": v1_path.name, "sha256": sha(v1_path),
                         "unchanged": ["folds_C: lineages, excluded tables and units, arm sources, truth tables",
                                       "arms", "hidden_target_rule", "panel_hidden_groups", "protected", "axis",
                                       "panel", "interface", "emission", "scorer"]}
    patterns = doc["lineages"]["HCT116"]["name_patterns"]
    assert patterns == ["hct116", "dld"]
    doc["lineages"]["HCT116"]["name_patterns"] = ["hct116"]
    for f in doc["folds_C"]:
        if f["lineage"] == "HCT116":
            f["exclude_name_patterns"] = ["hct116"]
    doc["measures_level_A"] = {
        "primary": ["disc95", "r_spec"],
        "disc95": "1 - normalised rank of a target's own truth among all truths, by cosine, on the genes valid for "
                  "at least 95% of the compared targets in the arms of the manifest; an invalid pair counts 0 on "
                  "both sides",
        "disc": "v1's strict variant (genes valid for every target): secondary, read only where its shuffle control "
                "passes",
        "usable_when": "T0 minus T0 with shuffled targets is resolved positive on the fold, for the same measure",
        "why_changed": "on C-K562 one gene is valid for all 272 targets: v1's disc is 0.49 for T0 and 0.50 for the "
                       "shuffle, the control registered in v1 fails, and the measure cannot see specificity there"}
    extraction = {}
    for line, fold in (("k562", "C-K562"), ("ipsc", "C-iPSC")):
        here = HERE / "banco" / ("celle_%s_r1" % line)
        done = json.loads((here / "completion/extract_done.json").read_text(encoding="utf-8"))
        launch = json.loads((here / "launch.json").read_text(encoding="utf-8"))
        cells = sorted(done["sidecar"]["targets"].values())
        extraction[fold] = {"kernel": launch["slug"], "key": done["sidecar"]["key"],
                            "real_cells_sha256": done["sidecar"]["sha256"], "targets": len(cells),
                            "cells_per_target": {"min": cells[0], "median": cells[len(cells) // 2], "max": cells[-1]},
                            "controls": done["sidecar"]["controls"], "genes": done["sidecar"]["genes"],
                            "cap": done["sidecar"]["cap"], "seed": done["sidecar"]["seed"]}
    doc["level_B"] = {"bench": "reports/generatore_e_banchi/banco_v2_2026-10-04/bench_v2.py, unchanged",
                      "bench_sha256": sha(HERE.parents[2] / "reports/generatore_e_banchi/banco_v2_2026-10-04/bench_v2.py"),
                      "folds": extraction, "runs": ["full: T0, T1, P4, five seeds", "changed: T0, T1, R1 on the "
                                                    "targets with added votes, five seeds",
                                                    "control: T0 against T0 with exchanged rows, one seed"],
                      "lineages_without_real_cells": ["CD4T", "HCT116", "HEK293", "H1 (15 targets, 64 cells)"]}
    folds_after = json.dumps([{k: f[k] for k in ("id", "lineage", "exclude_tables", "exclude_units", "arm_sources",
                                                   "truth")} for f in doc["folds_C"]], sort_keys=True)
    assert folds_before == folds_after, "v2 must not move a fold"
    with out.open("x", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    print(json.dumps({"version": doc["version"], "sha256": sha(out), "level_B_folds": extraction}, indent=1))


if __name__ == "__main__":
    main()
