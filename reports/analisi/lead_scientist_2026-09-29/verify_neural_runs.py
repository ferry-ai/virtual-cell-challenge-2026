"""Read-only provenance and coverage guard for the five frozen C/J fold outputs.

Does not read effect arrays or choose a model. Run before read_neural_sources.py.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

CONTEXTS = {"k562": {"k562", "k562ess", "viperturb"},
            "cd4": {"cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr"},
            "orion": {"orion_hct116", "orion_hek293t"},
            "ipsc": {"kolf", "hipsci_fit", "hipsci_nonfit"}, "rpe1": {"rpe1"}}
ARMS = {"net", "blind", "swap", "prior_permuted", "transfer", "null"}


def canonical_code(hashes):
    out = {}
    for filename, digest in hashes.items():
        name = filename.replace("\\", "/").rsplit("/", 1)[-1]
        if name in out:
            raise ValueError("Ambiguous duplicate code basename in manifest")
        out[name] = digest
    required = {"PROTOCOLLO_NEURALE.md", "neural_sources.py", "train_neural_sources.py", "pool.py"}
    if set(out) != required:
        raise ValueError(f"Frozen code identity differs: {set(out)}")
    return out


def verify(runs):
    seen, master, details = set(), None, {}
    for run in runs:
        manifest = json.loads((run / "manifest.json").read_text())
        options, design = manifest["options"], manifest["design"]
        family = options["holdout"]
        if family not in CONTEXTS or family in seen:
            raise ValueError(f"Unexpected or duplicate outer family {family}")
        seen.add(family)
        comparable = {k: v for k, v in options.items() if k not in ("data", "out", "holdout", "device")}
        identity = {"options": comparable, "data": manifest["data_files"],
                    "code": canonical_code(manifest["code_hashes"]), "contexts": manifest["context_names"],
                    "families": manifest["family_names"], "priors": manifest["prior_columns"]}
        if master is not None and identity != master:
            raise ValueError(f"{family}: code, protocol, data, priors or options differ across folds")
        master = identity
        if options["plan_only"] or options.get("predict_contexts") or options.get("predict_targets"):
            raise ValueError("Fold contains a preparation-only or production prediction configuration")
        context_names = manifest["context_names"]
        actual_hidden = {context_names[c] for c in design["hidden_contexts"]}
        if actual_hidden != CONTEXTS[family]:
            raise ValueError(f"{family}: whole-family exclusion is not the frozen r2 version map")
        test_rows = np.concatenate([np.asarray(rows, int) for rows in design["test"].values()])
        val_rows = np.concatenate([np.asarray(rows, int) for rows in design["validation"].values()])
        for name in ("train", "refit"):
            if np.intersect1d(design[name], test_rows).size:
                raise ValueError(f"{family}: test row entered {name}")
        if np.intersect1d(design["train"], val_rows).size:
            raise ValueError(f"{family}: validation row entered inner training")
        table = pd.read_csv(run / "per_target.csv", keep_default_na=False)
        if set(table.context) != CONTEXTS[family] or set(table.family) != {family} or set(table.arm) != ARMS:
            raise ValueError(f"{family}: output context/family/arm coverage is incomplete")
        if table.duplicated(["context", "target", "arm"]).any():
            raise ValueError(f"{family}: duplicate target-arm output")
        expected = {context_names[int(c)]: len(rows) for c, rows in design["test"].items()}
        for context, rows in table.groupby("context"):
            counts = rows.groupby("arm").target.nunique()
            if not (counts == expected[context]).all():
                raise ValueError(f"{family}/{context}: an arm lost frozen test targets")
            pivot = rows.pivot(index="target", columns="arm", values="rank")
            if pivot.isna().any().any() or not np.isfinite(pivot.to_numpy()).all():
                raise ValueError(f"{family}/{context}: missing paired rank or nonfinite result")
        details[family] = {"targets_per_context": expected, "test_rows": len(test_rows),
                           "validation_family": design["validation_family"]}
    if seen != set(CONTEXTS):
        raise ValueError(f"Incomplete family set: {seen}")
    return {"verified": True, "families": details, "large_arrays_rehashed": False,
            "limitation": "Compares recorded input identities and row disjointness. Large effect arrays remain identified by size and their dataset manifest, not independently rehashed here.",
            "outcomes_read_for_model_selection": False, "scientific_verdict": "Use the frozen readout next; provenance alone proves no improvement."}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    result = verify(args.runs)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
