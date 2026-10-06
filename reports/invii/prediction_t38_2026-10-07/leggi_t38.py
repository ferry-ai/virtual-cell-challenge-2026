"""Reader of the t38 official result by the rule registered in prediction.json, written before the score is known.

    python leggi_t38.py <t38 vcc json>   -> writes comparison.json next to this file (never overwrites)
t36's receipt is read from this branch (reports/invii/trial_rlead_2026-10-06/status_LgakrSXj3X2nAtN5P4Yk.json);
t28's from main (reports/invii/trial_2026-09-29/status_ZvrYZ4UazadAyuq4AsDB_20260929T2305.json).
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
T36 = HERE.parent / "trial_rlead_2026-10-06" / "status_LgakrSXj3X2nAtN5P4Yk.json"
T28 = "origin/main:reports/invii/trial_2026-09-29/status_ZvrYZ4UazadAyuq4AsDB_20260929T2305.json"
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
    t38 = entry_text(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    if t38.get("status") != "published" or t38.get("score_avg") is None:
        raise SystemExit(f"t38 not scored yet: {t38.get('status')}")
    t36 = entry_text(T36.read_text(encoding="utf-8-sig"))
    t28 = entry_text(subprocess.run(["git", "show", T28], capture_output=True, text=True, check=True,
                                    encoding="utf-8").stdout)
    d = t38["score_avg"] - t36["score_avg"]
    branch = "a" if d >= 0.005 else ("c" if d <= -0.005 else "b")
    rec = {"written_utc": datetime.now(timezone.utc).isoformat(), "entry_id": t38.get("entry_id"),
           "score_avg": t38["score_avg"], "rank": t38.get("rank"),
           "t36": t36["score_avg"], "t38_minus_t36": d, "rule_branch": branch,
           "inside_band": -0.012 <= d <= 0.015, "registered_centre": 0.002,
           "addendum_estimate_from_bench": -0.004,
           "t28": t28["score_avg"], "t38_minus_t28": t38["score_avg"] - t28["score_avg"],
           "scaled_t38_vs_t36": members(t38, t36), "scaled_t38_vs_t28": members(t38, t28),
           "raw": {k: [t38.get(k), t36.get(k), t28.get(k)] for k in RAW}}
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
