"""Read the official t30 status by its rule, registered before the hybrid effects were read and before generation.

Offline: it never fetches a status and never submits. It reads a status saved by `vcc --json status`, checks that the
registration is the committed one (sha256 with CRLF folded to LF), applies the registered rule unchanged (t30 - t25
against +-0.005) and writes comparison.json beside the registration (refusing an existing file). A missing or
non-finite member stops it: nothing is estimated. Written on 4/10 before the upload, a copy of read_t29_score.py.

    python read_t30_score.py --status status_<entry>.json --entry <entry>
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
REGISTRATION = REPO / "reports/invii/prediction_t30_2026-10-04/prediction.json"
REGISTRATION_SHA_LF = "4b8f5dc07ca54d542f52d4cad3756fbf2f02781ef4fc3238083cbce5cf0ffa42"
T25_STATUS = REPO / "reports/invii/trial_2026-09-27/status_ekxW6wo83Csum25pkddl.json"
MODEL = "trial-30 selective hybrid: trial-25 transfer plus a weighted single-cell network correction"
MEMBERS = {"pds_cosine": "score_pds", "expr_mse_unbiased_capped_norm": "score_mse", "de_wilcoxon_lfc_nmae": "score_nmae",
           "de_wilcoxon_direction_fidelity_yield_raw": "score_fid", "de_wilcoxon_direction_reach_raw": "score_reach",
           "de_wilcoxon_sig_jaccard": "score_jac"}
THRESHOLD = 0.005


def number(value, field):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise SystemExit(f"missing or non-finite member: {field}")
    return float(value)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--status", required=True, type=Path)
    p.add_argument("--entry", required=True)
    a = p.parse_args()
    out = REGISTRATION.parent / "comparison.json"
    if out.exists():
        raise SystemExit(f"refusing: {out} exists")
    if hashlib.sha256(REGISTRATION.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != REGISTRATION_SHA_LF:
        raise SystemExit("the registration differs from the committed one")
    reg = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    st = json.loads((a.status if a.status.is_absolute() else HERE / a.status).read_text(encoding="utf-8"))
    if st.get("entry_id") != a.entry or st.get("model_name") != MODEL:
        raise SystemExit("the status is not the t30 entry")
    if st.get("status") != "published" or not st.get("is_terminal"):
        raise SystemExit(f"not published yet: {st.get('status')}")
    t25 = json.loads(T25_STATUS.read_text(encoding="utf-8"))
    score = number(st.get("score_avg"), "score_avg")
    scaled = {v: number(st.get(v), v) for v in MEMBERS.values()}
    mean6 = sum(scaled.values()) / len(scaled)
    raw = {k: number(st.get(k), k) for k in MEMBERS}
    refs = reg["references"]
    delta = score - refs["t25"]
    if delta >= THRESHOLD:
        branch, text = "a", reg["rule"]["a_gain_at_least_0.005"]
    elif delta <= -THRESHOLD:
        branch, text = "c", reg["rule"]["c_loss_at_least_0.005"]
    else:
        branch, text = "b", reg["rule"]["b_within_0.005"]
    band = reg["expected"]["score_avg_band"]
    comparison = {
        "written_utc": datetime.now(timezone.utc).isoformat(), "entry_id": a.entry,
        "submission_date": st.get("submission_date"), "score_avg": score, "rank_at_scoring": st.get("rank"),
        "official_status": st.get("status"), "panel_id": st.get("panel_id"), "anchor_version": st.get("anchor_version"),
        "mean_of_six_scaled": mean6, "mean_matches_score_avg": abs(mean6 - score) < 1e-9,
        "t30_minus_t25": delta, "t30_minus_t28_best_observed": score - refs["t28_best_observed"],
        "registered_band": band, "inside_avg_band": band[0] <= score <= band[1],
        "rule_branch": branch, "rule_text": text,
        "scaled_published": {"t30": scaled, "t25": {v: t25.get(v) for v in MEMBERS.values()},
                             "t30_minus_t25": {v: scaled[v] - t25[v] for v in MEMBERS.values()}},
        "raw": {k: {"t30": raw[k], "t25": t25.get(k), "t30_minus_t25": raw[k] - t25[k]} for k in MEMBERS},
        "registration_sha256_lf": REGISTRATION_SHA_LF, "status_file": a.status.name,
        "note": ("one submission, one network (the HepG2 fold) and one seed: the rule is read as registered; the only "
                 "factor changed against t25 is the weighted neural correction of the effects")}
    out.write_text(json.dumps(comparison, indent=1), encoding="utf-8")
    print(json.dumps({k: comparison[k] for k in ("score_avg", "rank_at_scoring", "t30_minus_t25", "inside_avg_band",
                                                 "rule_branch", "mean_matches_score_avg")}, indent=1))


if __name__ == "__main__":
    main()
