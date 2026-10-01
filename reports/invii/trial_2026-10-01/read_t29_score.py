"""Read the official t29 status by its rule, registered before the export and the generation.

Offline: it never fetches a status and never submits. It reads a status saved by `vcc --json status`, checks that the
registration is the committed one, applies the registered rule unchanged and writes comparison.json beside the
registration (refusing an existing file). A missing or non-finite member stops it: nothing is estimated.

    python read_t29_score.py --status status_K6Q36uGCaEwQ1wRLmBLp.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REGISTRATION = REPO / "reports/invii/prediction_t29_2026-10-01/prediction.json"
REGISTRATION_SHA = "d92411da68dd99c9dceef6dbe576a1f5dcb33b25a86d21087bd1c6bd0b789721"
T22_STATUS = REPO / "reports/invii/trial_2026-09-26/status_hOy1AirAxJsFvpQAHH15.json"
ENTRY = "K6Q36uGCaEwQ1wRLmBLp"
MODEL = "trial-29 single-cell network (descriptors arm) with the trial-22 generator"
MEMBERS = {"pds_cosine": "score_pds", "expr_mse_unbiased_capped_norm": "score_mse", "de_wilcoxon_lfc_nmae": "score_nmae",
           "de_wilcoxon_direction_fidelity_yield_raw": "score_fid", "de_wilcoxon_direction_reach_raw": "score_reach",
           "de_wilcoxon_sig_jaccard": "score_jac"}


def number(value, field):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise SystemExit(f"missing or non-finite member: {field}")
    return float(value)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--status", required=True, type=Path)
    a = p.parse_args()
    out = REGISTRATION.parent / "comparison.json"
    if out.exists():
        raise SystemExit(f"refusing: {out} exists")
    if hashlib.sha256(REGISTRATION.read_bytes()).hexdigest() != REGISTRATION_SHA:
        raise SystemExit("the registration differs from the committed one")
    reg = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    st = json.loads((a.status if a.status.is_absolute() else HERE / a.status).read_text(encoding="utf-8"))
    if st.get("entry_id") != ENTRY or st.get("model_name") != MODEL:
        raise SystemExit("the status is not the t29 entry")
    if st.get("status") != "published" or not st.get("is_terminal"):
        raise SystemExit(f"not published yet: {st.get('status')}")
    t22 = json.loads(T22_STATUS.read_text(encoding="utf-8"))
    score = number(st.get("score_avg"), "score_avg")
    scaled = {v: number(st.get(v), v) for v in MEMBERS.values()}
    mean6 = sum(scaled.values()) / len(scaled)
    raw = {k: number(st.get(k), k) for k in MEMBERS}
    refs = reg["references"]
    if score >= 0.137:
        branch, text = "a", reg["rule"]["a_at_least_0.137"]
    elif score >= 0.06:
        branch, text = "b", reg["rule"]["b_0.06_to_0.137"]
    else:
        branch, text = "c", reg["rule"]["c_below_0.06"]
    band = reg["expected"]["score_avg_band"]
    comparison = {
        "written_utc": datetime.now(timezone.utc).isoformat(), "entry_id": ENTRY,
        "submission_date": st.get("submission_date"), "score_avg": score, "rank_at_scoring": st.get("rank"),
        "official_status": st.get("status"), "panel_id": st.get("panel_id"), "anchor_version": st.get("anchor_version"),
        "mean_of_six_scaled": mean6, "mean_matches_score_avg": abs(mean6 - score) < 1e-9,
        "t29_minus_t22": score - refs["t22"], "t29_minus_t22_t24_mean": score - refs["t22_t24_mean"],
        "t29_minus_t28_best_observed": score - refs["t28_best_observed"],
        "registered_band": band, "inside_avg_band": band[0] <= score <= band[1],
        "rule_branch": branch, "rule_text": text,
        "scaled_published": {"t29": scaled, "t22": {v: t22.get(v) for v in MEMBERS.values()},
                             "t29_minus_t22": {v: scaled[v] - t22[v] for v in MEMBERS.values()}},
        "raw": {k: {"t29": raw[k], "t22": t22.get(k), "t29_minus_t22": raw[k] - t22[k]} for k in MEMBERS},
        "registration_sha256": REGISTRATION_SHA, "status_file": a.status.name,
        "note": ("one submission, one seed of the network: the rule is read as registered; nothing is attributed beyond "
                 "the source of the effects, the only factor changed against t22")}
    out.write_text(json.dumps(comparison, indent=1), encoding="utf-8")
    print(json.dumps({k: comparison[k] for k in ("score_avg", "rank_at_scoring", "t29_minus_t22", "inside_avg_band",
                                                 "rule_branch", "mean_matches_score_avg")}, indent=1))


if __name__ == "__main__":
    main()
