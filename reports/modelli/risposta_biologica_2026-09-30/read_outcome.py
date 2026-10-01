"""Read the outputs of a training kernel of kaggle_train.py (one process, several arms) by the rule of the protocols in
reports/modelli/cellnet_*: part A item by item, part B per class and arm. Prints JSON; decides nothing on its own.

    python read_outcome.py <downloaded kernel output folder>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def main() -> None:
    root = Path(sys.argv[1])
    run = root / "train"
    kd, rc = load(root / "kernel_done.json"), load(root / "resume_check.json")
    cov, plan, done = load(run / "coverage.json"), load(run / "plan.json"), load(run / "done.json")
    ver = load(run / "verify.json")
    arms = (cov or {}).get("arms") or [a[0] for a in (kd or {}).get("arms", [])]
    out = {"A": {
        "1_kernel_code": (kd or {}).get("return_code"),
        "2_resume_check": None if rc is None else {k: rc.get(k) for k in (
            "passed", "batch_chain_equal", "seen_equal", "model_max_abs_diff", "model_max_abs", "models_compared")},
        "3_verify": None if ver is None else {"shards": ver.get("shards"), "differ": ver.get("differ"),
                                              "seconds": ver.get("seconds")},
        "4_coverage": None if cov is None else {
            "epochs_done": cov.get("epochs_done"), "stop": cov.get("stop"), "steps": cov.get("steps"),
            "admitted_training_cells": cov.get("admitted_training_cells"),
            "distinct_cells_seen": cov.get("distinct_cells_seen"),
            "all_seen": cov.get("distinct_cells_seen") == cov.get("admitted_training_cells"),
            "leakage_passed": (cov.get("leakage_check") or {}).get("passed"), "throughput": cov.get("throughput"),
            "memory": cov.get("memory")},
        "5_eval": {}, "6_plan": None if plan is None else {k: plan.get(k) for k in (
            "measured_from_step", "measured_steps", "cells_per_second", "data_wait_fraction", "evaluation_reserve_seconds",
            "epochs_expected", "train_until_utc", "memory")},
        "done": done}, "B": {}}
    for arm in arms:
        ev = load(run / arm / "eval.json")
        if ev is None:
            out["A"]["5_eval"][arm] = None
            continue
        s = ev["summary"]
        out["A"]["5_eval"][arm] = s.get("evaluation")
        out["B"][arm] = {c: {k: s[c].get(k) for k in (
            "groups", "skipped", "ll_gain_vs_no_effect", "ll_gain_vs_unknown_target",
            "share_target_specific_gain_positive", "cos_model", "cos_transfer", "groups_with_transfer",
            "cos_model_where_transfer", "cos_generic")} for c in ("C", "T", "J") if c in s}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
