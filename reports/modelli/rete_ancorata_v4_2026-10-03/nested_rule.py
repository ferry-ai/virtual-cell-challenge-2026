"""The sufficiency rule of the nested-samples study (CAMPIONI_ANNIDATI.md §4), applied to the groups table.

    python nested_rule.py --groups <nested/groups.csv.gz> --manifest <nested/manifest.json> --out <new dir> \
        [--caps 32 64 128] [--exploratory]

A decision that a training may use is written only for a table computed on the cells of class train of one fold
(nested_samples.py --classes train, the manifest says so): decision.json and decision.md, with the fold. A table
that read every class (held-out line and hidden targets included) is refused unless --exploratory is given, and then
the output is exploratory.json and exploratory.md, marked as not usable by any training (CAMPIONI_ANNIDATI.md §10:
choosing the data with the responses of the evaluation brings their information into the training).

The constants below were written before any number of the study was read (CAMPIONI_ANNIDATI.md, frozen with the commit
that holds it). Per unit (line group::study) and level c:
- whole: the groups with at most c cells, kept whole: no loss by construction;
- reading population: the groups with more than c cells, in a key with at least MIN_TARGETS targets (so that a generic
  response can be removed), whose specific shift is measurable in the full group: the two halves agree,
  r_spec_halves >= MEASURABLE. Where the full group itself shows no reproducible specific shift, no level can be judged;
- status of the level: "no_loss" when no group of the unit is truncated; "not_judgeable" when the reading population has
  fewer than MIN_GROUPS groups; "sufficient" when on the reading population the median of r_spec_c is at least R_MEDIAN,
  its 10th percentile at least R_P10 and the median of sign_top_spec_c at least SIGN_MEDIAN; else "insufficient";
- coverage guard, on every group of the unit: guides kept at c over guides present >= GUIDES_SHARE.
Recommended level of a unit: the smallest level that is "sufficient" or "no_loss" and passes the guard. With none: "above"
when the largest level is "insufficient" or fails the guard (an exception to the cap, to be sized for that unit),
otherwise the largest level, marked "not_judgeable" (the conservative default).

Reported without threshold: the total-shift metrics, the share of groups kept whole, the groups whose specific shift is
not measurable, and r_pred: what a random sample of c cells of a homogeneous group would give against the full group,
from the cells n and the halves' agreement rho alone (kappa = (1/rho - 1) n/2; r_pred = sqrt((1 + kappa/n) /
(1 + kappa/c))). measured - r_pred below zero means the stratified sample loses more than cell numbers explain.
This is an operational rule for choosing where a training starts and where the cap is widened first; it is not a proof
that a training on the sample equals a training on everything (that is the six-metric comparison between levels).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

MIN_TARGETS = 10
MEASURABLE = 0.5
R_MEDIAN = 0.90
R_P10 = 0.75
SIGN_MEDIAN = 0.90
MIN_GROUPS = 20
GUIDES_SHARE = 0.99
RULE = {"MIN_TARGETS": MIN_TARGETS, "MEASURABLE": MEASURABLE, "R_MEDIAN": R_MEDIAN, "R_P10": R_P10,
        "SIGN_MEDIAN": SIGN_MEDIAN, "MIN_GROUPS": MIN_GROUPS, "GUIDES_SHARE": GUIDES_SHARE}


def r_pred(n, rho, c):
    """Expected correlation of a random c-cell sample's mean shift with the full group's (n cells), homogeneous cells."""
    n, rho = np.asarray(n, float), np.clip(np.asarray(rho, float), 1e-6, 1 - 1e-9)
    kappa = (1 / rho - 1) * n / 2
    return np.sqrt((1 + kappa / n) / (1 + kappa / c))


def q(series, p):
    s = series.dropna()
    return float(s.quantile(p)) if len(s) else None


def level_of_unit(sub: pd.DataFrame, c: int) -> dict:
    truncated = sub[sub["cells"] > c]
    measurable = truncated[(truncated["targets_in_key"] >= MIN_TARGETS) & (truncated["r_spec_halves"] >= MEASURABLE)]
    read = measurable[measurable[f"r_spec_{c}"].notna()]
    guides = float(sub[f"guides_{c}"].sum() / max(1, sub["guides"].sum()))
    e = {"cells": int(sub[f"cells_{c}"].sum()), "share_of_cells": float(sub[f"cells_{c}"].sum() / max(1, sub["cells"].sum())),
         "groups_whole": int((sub["cells"] <= c).sum()), "groups_truncated": int(len(truncated)),
         "groups_read": int(len(read)), "groups_not_measurable": int(len(truncated) - len(measurable)),
         "guides_kept_share": guides, "guard_passed": bool(guides >= GUIDES_SHARE),
         "groups_losing_guides": int((sub[f"guides_{c}"] < sub["guides"]).sum()),
         "r_spec_median": q(read[f"r_spec_{c}"], 0.5), "r_spec_p10": q(read[f"r_spec_{c}"], 0.1),
         "sign_top_spec_median": q(read[f"sign_top_spec_{c}"], 0.5),
         "share_of_read_groups_at_r_median": float((read[f"r_spec_{c}"] >= R_MEDIAN).mean()) if len(read) else None,
         "reported": {"r_total_median_truncated": q(truncated[f"r_{c}"], 0.5),
                      "sign_top_total_median_truncated": q(truncated[f"sign_top_{c}"], 0.5),
                      "overlap_top_spec_median_read": q(read[f"overlap_top_spec_{c}"], 0.5),
                      "r_spec_halves_median_read": q(read["r_spec_halves"], 0.5),
                      "cells_median_read": q(read["cells"], 0.5)}}
    if len(read):
        diff = read[f"r_spec_{c}"] - r_pred(read["cells"], read["r_spec_halves"], c)
        e["reported"]["measured_minus_r_pred_median"] = float(diff.median())
    if f"var_r_{c}" in sub.columns:                    # --dispersion runs: variance and zeros, no threshold
        e["reported"]["var_r_median_truncated"] = q(truncated[f"var_r_{c}"], 0.5)
        e["reported"]["zero_mad_median_truncated"] = q(truncated[f"zero_mad_{c}"], 0.5)
    if not len(truncated):
        e["status"] = "no_loss"
    elif len(read) < MIN_GROUPS:
        e["status"] = "not_judgeable"
    elif e["r_spec_median"] >= R_MEDIAN and e["r_spec_p10"] >= R_P10 and e["sign_top_spec_median"] >= SIGN_MEDIAN:
        e["status"] = "sufficient"
    else:
        e["status"] = "insufficient"
    return e


def decide(df: pd.DataFrame, caps) -> dict:
    caps = sorted(caps)
    units = {}
    for u, sub in df.groupby("unit"):
        levels = {str(c): level_of_unit(sub, c) for c in caps}
        good = [c for c in caps if levels[str(c)]["status"] in ("sufficient", "no_loss") and levels[str(c)]["guard_passed"]]
        last = levels[str(caps[-1])]
        if good:
            rec = {"level": good[0], "why": levels[str(good[0])]["status"]}
        elif last["status"] == "insufficient" or not last["guard_passed"]:
            rec = {"level": None, "why": "above"}
        else:
            rec = {"level": caps[-1], "why": "not_judgeable"}
        units[str(u)] = {"groups": int(len(sub)), "cells": int(sub["cells"].sum()), "keys": int(sub["key"].nunique()),
                         "targets": int(sub["target"].nunique()), "levels": levels, "recommended": rec}
    totals = {"cells_full": int(df["cells"].sum()), **{str(c): int(df[f"cells_{c}"].sum()) for c in caps}}
    totals["at_recommended_levels"] = int(sum(
        (e["levels"][str(e["recommended"]["level"])]["cells"] if e["recommended"]["level"] else e["cells"])
        for e in units.values()))
    return {"rule": RULE, "caps": caps, "units": units, "totals": totals,
            "note": "units recommended 'above' count with all their cells in at_recommended_levels; controls are not in "
                    "these numbers (they enter a training through its reservoir)"}


def markdown(doc: dict) -> str:
    caps = doc["caps"]
    head = "| Unità | Gruppi | Cellule | " + " | ".join(f"{c}: stato, letti, r spec. mediana / p10, segno" for c in caps) \
        + " | Livello |\n|---|---:|---:|" + "---|" * len(caps) + "---|\n"
    lines = []
    f = lambda v: "n.d." if v is None else f"{v:.3f}"
    for u, e in doc["units"].items():
        cells = []
        for c in caps:
            lv = e["levels"][str(c)]
            cells.append(f"{lv['status']}, {lv['groups_read']}, {f(lv['r_spec_median'])} / {f(lv['r_spec_p10'])}, "
                         f"{f(lv['sign_top_spec_median'])}" + ("" if lv["guard_passed"] else ", guide perse"))
        rec = e["recommended"]
        lines.append(f"| `{u}` | {e['groups']} | {e['cells']} | " + " | ".join(cells)
                     + f" | {rec['level'] if rec['level'] else 'oltre ' + str(caps[-1])} ({rec['why']}) |")
    return head + "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--groups", type=Path, required=True)
    p.add_argument("--manifest", type=Path, help="manifest.json of the nested_samples.py run that wrote the table")
    p.add_argument("--exploratory", action="store_true",
                   help="describe a table that read every class; the output cannot be used by a training")
    p.add_argument("--caps", nargs="+", type=int, default=[32, 64, 128])
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    man = json.loads(a.manifest.read_text(encoding="utf-8")) if a.manifest else {}
    sha = hashlib.sha256(a.groups.read_bytes()).hexdigest()
    if man and man.get("outputs", {}).get("groups.csv.gz") not in (None, sha):
        raise SystemExit("refusing: the manifest is of another groups table")
    classes = man.get("classes", "all" if man else None)     # a manifest older than --classes read every class
    if not a.exploratory and classes != "train":
        raise SystemExit("refusing: a decision for a training needs the manifest of a --classes train run of one fold "
                         f"(classes here: {classes}); --exploratory describes the table without deciding")
    doc = decide(pd.read_csv(a.groups), a.caps)
    doc["inputs"] = {"groups": str(a.groups), "sha256": sha, "manifest": str(a.manifest) if a.manifest else None,
                     "prepass_sha256": man.get("prepass_sha256")}
    doc["classes"], doc["fold_holdout_group"] = classes, man.get("holdout_group")
    doc["exploratory"] = bool(a.exploratory)
    doc["use"] = ("exploratory description: no training decision may use it" if a.exploratory else
                  f"levels for the trainings of the fold that holds out {man.get('holdout_group')}, from its class-train "
                  "cells only")
    name = "exploratory" if a.exploratory else "decision"
    head = ("**Analisi esplorativa: letta su tutte le classi, non utilizzabile per decisioni di addestramento.**\n\n"
            if a.exploratory else f"Fold con linea esclusa {man.get('holdout_group')}: solo cellule di classe training.\n\n")
    a.out.mkdir(parents=True)
    (a.out / f"{name}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    (a.out / f"{name}.md").write_text(head + markdown(doc), encoding="utf-8")
    print(json.dumps({"use": doc["use"], "units": {u: e["recommended"] for u, e in doc["units"].items()},
                      "totals": doc["totals"]}))


if __name__ == "__main__":
    main()
