"""Registered cross-family readout, with equal families and contexts; no cherry-picking."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


EXPECTED = {"k562", "cd4", "orion", "ipsc", "rpe1"}


def readout(runs, seed=20260929):
    tables, manifests = [], []
    for run in runs:
        tables.append(pd.read_csv(run / "per_target.csv"))
        manifests.append(json.loads((run / "manifest.json").read_text()))
    families = [m["options"]["holdout"] for m in manifests]
    if len(set(families)) != len(families) or set(families) != EXPECTED:
        raise ValueError(f"Need one frozen run for each {sorted(EXPECTED)}; found {families}")
    for field in ("regime", "seed", "selection_seed", "test_targets"):
        if len({str(m["options"][field]) for m in manifests}) != 1:
            raise ValueError(f"Incompatible runs: {field}")
    all_rows = pd.concat(tables, ignore_index=True)
    if set(all_rows.family) != EXPECTED:
        raise ValueError("Output families differ from frozen manifests")
    pivot = all_rows.pivot(index=["family", "context", "target"], columns="arm", values="rank")
    if pivot[["net", "transfer", "blind", "swap"]].isna().any().any():
        raise ValueError("Missing paired targets")
    rng = np.random.default_rng(seed)
    result = {"not_vcc_score": True, "families": {}, "contrasts": {}, "regime": manifests[0]["options"]["regime"],
              "training_seed": manifests[0]["options"]["seed"], "bootstrap_scope": "targets within each observed context; equal families then contexts, conditional on these five families"}
    for reference in ("transfer", "blind", "swap", "prior_permuted", "null"):
        delta = pivot["net"] - pivot[reference]
        family_points, global_boot = {}, np.zeros(2000)
        for family, df in delta.groupby(level="family"):
            groups = [x.to_numpy() for _, x in df.groupby(level="context")]
            family_points[family] = float(np.mean([x.mean() for x in groups]))
            family_boot = np.zeros(2000)
            for x in groups:
                family_boot += x[rng.integers(0, len(x), (2000, len(x)))].mean(1) / len(groups)
            global_boot += family_boot / len(EXPECTED)
        result["contrasts"][reference] = {"macro_family_delta": float(np.mean(list(family_points.values()))),
                                           "ci95": np.quantile(global_boot, [.025, .975]).tolist(),
                                           "per_family": family_points}
    primary = result["contrasts"]["transfer"]
    result["eligible_for_cell_scorer"] = bool(primary["macro_family_delta"] >= .01 and primary["ci95"][0] > 0 and
                                               min(primary["per_family"].values()) >= -.01)
    result["evidence_for_context_use"] = bool(result["contrasts"]["blind"]["macro_family_delta"] > 0)
    result["robust_across_seeds"] = False
    result["next_requirement"] = "A separate seed and an independent cell-level benchmark; this readout never authorizes submission."
    return result, all_rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    result, rows = readout(args.runs)
    args.out.mkdir(parents=True)
    (args.out / "verdict.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    rows.to_csv(args.out / "per_target.csv", index=False)
    print(json.dumps(result, indent=2))
