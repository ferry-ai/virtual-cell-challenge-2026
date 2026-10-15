"""Reader of the ta 43 official result by the rule registered in prediction.json, written before the score is known.

    python leggi_ta43.py <ta 43 vcc json>   -> writes comparison.json next to this file (never overwrites)
Registered rule against ta 42 (receipt on this branch); also against td 38 (0.148922, as a number) and ta 40.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
T42 = HERE.parent / "trial_rlead_2026-10-15" / "status_wAUBxckeaH0Ab8bMXYaM.json"
T40 = HERE.parent / "trial_rlead_2026-10-12" / "status_D4DVVnBo4I3xn2aU59eN.json"
T28 = "origin/main:reports/invii/trial_2026-09-29/status_ZvrYZ4UazadAyuq4AsDB_20260929T2305.json"
DAVIDE_T38 = 0.148922
SCALED = ["score_pds", "score_mse", "score_nmae", "score_fid", "score_reach", "score_jac"]
RAW = ["pds_cosine", "expr_mse_unbiased_capped_norm", "de_wilcoxon_lfc_nmae", "de_wilcoxon_direction_fidelity_yield_raw",
       "de_wilcoxon_direction_reach_raw", "de_wilcoxon_sig_jaccard"]


def entry_text(text: str) -> dict:
    d = json.loads(text[text.index("{"):])
    while "score_avg" not in d:
        d = next(v for v in d.values() if isinstance(v, dict))
    return d


def members(a: dict, b: dict) -> dict:
    """Per scaled member: [a, b, a - b, (a - b) / 6 = contribution to the mean]."""
    out = {}
    for k in SCALED:
        x, y = a.get(k) or 0.0, b.get(k) or 0.0
        out[k] = [a.get(k), b.get(k), x - y, (x - y) / 6]
    return out


def main() -> None:
    out = HERE / "comparison.json"
    if out.exists():
        raise SystemExit("comparison.json exists: never overwrite")
    t43 = entry_text(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    if t43.get("status") != "published" or t43.get("score_avg") is None:
        raise SystemExit(f"ta 43 not scored yet: {t43.get('status')}")
    t42 = entry_text(T42.read_text(encoding="utf-8-sig"))
    t40 = entry_text(T40.read_text(encoding="utf-8-sig"))
    d = t43["score_avg"] - t42["score_avg"]
    branch = "a" if d >= 0.005 else ("c" if d <= -0.005 else "b")
    rec = {"written_utc": datetime.now(timezone.utc).isoformat(), "entry_id": t43.get("entry_id"),
           "score_avg": t43["score_avg"], "rank": t43.get("rank"),
           "ta42": t42["score_avg"], "ta43_minus_ta42": d, "rule_branch": branch,
           "inside_band": -0.006 <= d <= 0.006, "registered_centre": 0.0015,
           "weak_vote": "site_curve" if d > 0 else "fold_bench",
           "td38": DAVIDE_T38, "ta43_minus_td38": t43["score_avg"] - DAVIDE_T38,
           "ta40": t40["score_avg"],
           "scaled_ta43_vs_ta42": members(t43, t42), "scaled_ta43_vs_ta40": members(t43, t40),
           "raw_ta43_ta42_ta40": {k: [t43.get(k), t42.get(k), t40.get(k)] for k in RAW}}
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
