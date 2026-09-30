"""Reconstruct historical scores and contrasts without querying the competition.

This is a retrospective audit, not a prospective test of a new model.
Uses the saved official-score collection and comparison JSONs; t16 raw members
remain labelled as derived and its clipped MSE is never back-calculated.
Run via scripts/py.cmd. Outputs must go to a new directory.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path


SCORES = ["score_pds", "score_mse", "score_nmae", "score_fid", "score_reach", "score_jac"]
RAW = ["pds_cosine", "expr_mse_unbiased_capped_norm", "de_wilcoxon_lfc_nmae",
       "de_wilcoxon_direction_fidelity_yield_raw", "de_wilcoxon_direction_reach_raw",
       "de_wilcoxon_sig_jaccard"]
REPO = Path(__file__).resolve().parents[4]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"Refusing existing output directory: {args.out}")
    inputs = set()
    rows: dict[str, dict] = {}
    provenance: dict[str, dict] = {}

    def put(trial, key, value, source, kind="published"):
        if value is None or not isinstance(value, (int, float)):
            return
        old = rows.setdefault(trial, {}).get(key)
        if old is not None and not math.isclose(old, value, rel_tol=0, abs_tol=1e-9):
            raise ValueError(f"Conflicting evidence for {trial}/{key}: {old} vs {value}")
        rows[trial][key] = float(value)
        provenance.setdefault(trial, {})[key] = {"source": source, "kind": kind}

    collection = REPO / "reports/invii/lezioni_invii_2026-09-28/invii.csv"
    inputs.add(collection)
    with collection.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            for key in ["score_avg", *SCORES, *RAW]:
                if row.get(key):
                    put(row["trial"], key, float(row[key]), str(collection.relative_to(REPO)))
    for path in sorted((REPO / "reports/invii").glob("prediction_t*/comparison.json")):
        match = re.match(r"prediction_(t\d+)_", path.parent.name)
        if not match:
            continue
        trial = match.group(1)
        inputs.add(path)
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        source = str(path.relative_to(REPO))
        put(trial, "score_avg", doc.get("score_avg"), source)
        for name, values in doc.get("scaled_published", {}).items():
            if re.fullmatch(r"t\d+", name) and isinstance(values, dict):
                for key in SCORES:
                    put(name, key, values.get(key), source)
        for key, values in doc.get("raw", {}).items():
            if key not in RAW or not isinstance(values, dict):
                continue
            for name, value in values.items():
                match = re.fullmatch(r"(t\d+)(?:_(published|derived))?", name)
                if match:
                    put(match.group(1), key, value, source, match.group(2) or "published")
    contrasts = []
    pairs = [("t15", "t11"), ("t16", "t15"), ("t20", "t16"), ("t22", "t20"),
             ("t24", "t22"), ("t25", "t22"), ("t23", "t22"), ("t26", "t25")]
    for after, before in pairs:
        a, b = rows[after], rows[before]
        parts = {key: (a[key] - b[key]) / 6 for key in SCORES}
        delta = a["score_avg"] - b["score_avg"]
        assert abs(sum(parts.values()) - delta) < 1e-9
        l1 = sum(abs(v) for v in parts.values())
        contrasts.append({"after": after, "before": before, "delta_avg": delta,
                          "sum_abs_member_contributions": l1,
                          "net_over_gross_change": abs(delta) / l1 if l1 else None,
                          **{f"contribution_{key}": value for key, value in parts.items()},
                          **{f"delta_raw_{key}": a[key] - b[key] for key in RAW
                             if key in a and key in b}})
    recipes = {}
    for trial in ["t11", "t15", "t16", "t20", "t22", "t25", "t27"]:
        path = REPO / f"configs/recipes/{trial}.json"
        inputs.add(path)
        recipe = json.loads(path.read_text(encoding="utf-8-sig"))
        recipes[trial] = {k: v for k, v in recipe.items() if k not in {"name", "why"}}
    # Two amplitudes cannot identify quadratic curvature, cross term AND the null
    # intercept. Vary the assumed null using the identical t11/t15 shape only.
    a1, a2 = 0.197, 0.394
    u1, u2 = (rows[t]["expr_mse_unbiased_capped_norm"] for t in ["t11", "t15"])
    sensitivity = []
    for null in [0.95, 0.969, 0.9864, 1.0, 1.012, 1.05, 1.15]:
        det = a1 * a1 * (-2 * a2) - a2 * a2 * (-2 * a1)
        curvature = ((u1 - null) * (-2 * a2) - (u2 - null) * (-2 * a1)) / det
        cross = (a1 * a1 * (u2 - null) - a2 * a2 * (u1 - null)) / det
        sensitivity.append({"assumed_null_raw": null, "quadratic_coefficient": curvature,
                            "cross_coefficient": cross,
                            "cosine_under_idealized_unit_truth_norm": cross / math.sqrt(curvature)
                            if curvature > 0 else None,
                            "nonnegative_optimal_amplitude": max(0, cross / curvature)
                            if curvature > 0 else None})
    assert "expr_mse_unbiased_capped_norm" not in rows["t16"]
    args.out.mkdir(parents=True)
    with (args.out / "scores.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["trial", "score_avg", *SCORES, *RAW])
        writer.writeheader()
        writer.writerows({"trial": t, **rows[t]} for t in sorted(rows, key=lambda v: int(v[1:])))
    fields = list(dict.fromkeys(key for row in contrasts for key in row))
    with (args.out / "contrasts.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(contrasts)
    (args.out / "evidence.json").write_text(json.dumps({
        "claim_type": "retrospective arithmetic on saved official scores; not new model validation",
        "provenance": provenance, "recipes": recipes, "mse_null_sensitivity": sensitivity,
        "sensitivity_caveat": "u=null+a^2*P-2*a*C is an approximation. A third unknown null cannot be identified with two amplitudes. Cosine assumes a common denominator, negligible corrections and linear response geometry; the generated log1p profiles are not exactly linear in amplitude.",
        "input_sha256": {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(inputs)},
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"trials": len(rows), "contrasts": contrasts,
                      "mse_null_sensitivity": sensitivity}, indent=2))


if __name__ == "__main__":
    main()
