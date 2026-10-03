"""Reproduce verdict guards at pinned revisions and audit the archived support matrix.

Small local fixtures and CSV tables only; no training, cloud calls or source edits.
Run through scripts/py.cmd, with --out naming a new JSON file.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PILOT = Path("reports/modelli/rete_cellulare_2026-10-03")
LINES = ("H1", "HepG2", "RPE1")
ARMS = ("cells", "mean", "generic", "transfer_cells", "transfer_all", "generic_pseudobulk")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def fixture(root: Path, line: str):
    kernel, lane = root / line, root / (line + "_lane")
    train = kernel / "train"
    train.mkdir(parents=True)
    lane.mkdir()
    # Both locations keep receipt lookup independent of the guards under review.
    write_json(kernel / "kernel_done.json", {"return_code": 0})
    write_json(train / "kernel_done.json", {"return_code": 0})
    write_json(train / "verify.json", {"differ": []})
    write_json(train / "coverage.json", {"leakage_check": {"passed": True}, "epochs_done": 2,
               "loss_shares": {"by_group": {"source1": 0.5, "source2": 0.5}}})
    write_json(train / "config.json", {"args": {"pi_floor": 0.01, "health_check_step": 5000}})
    write_json(train / "health.json", {"step": 5000, "passed": True})
    for arm in ARMS[:3]:
        (train / arm).mkdir()
        write_json(train / arm / "eval.json", {"summary": {"evaluation": {"complete": True}}})
    (train / "train_log.jsonl").write_text(json.dumps({"msg": "step", "arms": {
        arm: {"pi_q50": 0.5, "responsibility_mean": 0.5} for arm in ARMS[:3]}}) + "\n", encoding="utf-8")
    with gzip.open(lane / f"per_target_{line}.csv.gz", "wt", encoding="utf-8", newline="") as handle:
        fields = ("table", "target_key", "cls", "arm", "pds", "cos_spec", "cos", "mse_ratio", "sign_sig")
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for target in range(4):
            for arm in ARMS:
                writer.writerow(dict(table="synthetic", target_key=f"T{target}", cls="C", arm=arm,
                                     pds=0.8 if arm == "cells" else 0.6, cos_spec=0.1,
                                     cos=0.2, mse_ratio=1.0, sign_sig=0.5))
    return [line, str(train), str(lane)]


def guard_cases(revision: str):
    commit = subprocess.check_output(["git", "rev-parse", revision], cwd=ROOT, text=True).strip()
    source = subprocess.check_output(["git", "show", f"{commit}:{PILOT.as_posix()}/decide_pilot.py"], cwd=ROOT)
    cases = {}
    for case in ("complete_positive_control", "missing_required_health", "failed_H1_health", "H1_not_supplied"):
        with tempfile.TemporaryDirectory(prefix="vcc_guard_review_") as temp:
            root = Path(temp)
            script = root / "decide_pilot.py"
            script.write_bytes(source)
            lines = [fixture(root, line) for line in LINES]
            h1 = Path(lines[0][1])
            if case == "missing_required_health":
                (h1 / "health.json").unlink()
            elif case == "failed_H1_health":
                write_json(h1 / "health.json", {"step": 5000, "passed": False})
            elif case == "H1_not_supplied":
                lines = lines[1:]
            command = [sys.executable, "-B", str(script), "--out", str(root / "decision")]
            for line in lines:
                command.extend(["--line", *line])
            run = subprocess.run(command, capture_output=True, text=True, check=True)
            result = json.loads((root / "decision" / "decision.json").read_text(encoding="utf-8"))
            cases[case] = {"usable": result["usable"], "outcome": result["outcome"],
                           "Q1_pds": result["comparisons"]["Q1_state"]["C"]["pds"],
                           "expected_expand_under_three_line_protocol": case == "complete_positive_control"}
    return {"commit": commit, "source_sha256": sha(source), "cases": cases}


def histogram(values):
    return {str(int(k)): int(v) for k, v in sorted(Counter(values).items())}


def support_counts():
    output = {}
    for name in ("h1", "hepg2", "rpe1"):
        folder = ROOT / PILOT / "esito" / "matrix_r1" / name
        matrix_path, eval_path = folder / "target_by_group.csv.gz", folder / "eval_support.csv"
        table, support = pd.read_csv(matrix_path), pd.read_csv(eval_path)
        selected = support[support["class"] == "C"].copy()
        cri = table[table.modality == "CRISPRi"].groupby(["symbol", "group"]).training_cells.sum()
        all_hist = table.groupby("symbol").group.nunique()
        cri20 = cri[cri >= 20].reset_index().groupby("symbol").group.nunique()
        selected["CRISPRi_groups_ge20cells"] = selected.symbol.map(cri20).fillna(0).astype(int)
        output[name] = {
            "inputs_sha256": {matrix_path.name: sha(matrix_path.read_bytes()), eval_path.name: sha(eval_path.read_bytes())},
            "training_targets": len(all_hist), "training_targets_by_any_groups": histogram(all_hist),
            "fraction_training_targets_single_group": float((all_hist == 1).mean()),
            "C_rows": len(selected), "C_unique_symbols": int(selected.symbol.nunique()),
            "C_any_groups": histogram(selected.training_groups_any),
            "C_CRISPRi_groups": histogram(selected.training_groups_CRISPRi),
            "C_CRISPRi_groups_ge20cells": histogram(selected.CRISPRi_groups_ge20cells),
            "note": "The >=20-cell view is a descriptive sensitivity check, not a new inclusion or verdict rule.",
        }
    return output


def finite_json(value):
    if isinstance(value, dict):
        return {k: finite_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [finite_json(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    result = {"written_utc": datetime.now(timezone.utc).isoformat(),
              "script_sha256": sha(Path(__file__).read_bytes()),
              "guards": {rev: guard_cases(rev) for rev in ("1357466", "05504a1")},
              "support": support_counts()}
    write_json(args.out, finite_json(result))
    print(json.dumps({"out": str(args.out), "guards": {rev: {case: data["outcome"]["expand_on_lane_A"]
        for case, data in report["cases"].items()} for rev, report in result["guards"].items()},
        "support": result["support"]}, indent=2))


if __name__ == "__main__":
    main()
