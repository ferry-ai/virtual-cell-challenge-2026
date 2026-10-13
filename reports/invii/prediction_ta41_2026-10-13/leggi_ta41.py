"""Reader of the ta 41 official result by the rule registered in prediction.json, written before the score is known.

    python leggi_ta41.py <ta 41 vcc json>   -> writes comparison.json next to this file (never overwrites)
Registered rule against ta 40 (reports/invii/trial_rlead_2026-10-12/status_D4DVVnBo4I3xn2aU59eN.json); ta 39 is read
from this branch, td 28 from main, td 38 as a number (its receipt is not on GitHub yet).
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
T40 = HERE.parent / "trial_rlead_2026-10-12" / "status_D4DVVnBo4I3xn2aU59eN.json"
T39 = HERE.parent / "trial_rlead_2026-10-09" / "status_oeRXw89O1hefFsdCwifD.json"
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
    t41 = entry_text(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    if t41.get("status") != "published" or t41.get("score_avg") is None:
        raise SystemExit(f"ta 41 not scored yet: {t41.get('status')}")
    t40 = entry_text(T40.read_text(encoding="utf-8-sig"))
    t39 = entry_text(T39.read_text(encoding="utf-8-sig"))
    t28 = entry_text(subprocess.run(["git", "show", T28], capture_output=True, text=True, check=True,
                                    encoding="utf-8").stdout)
    d = t41["score_avg"] - t40["score_avg"]
    branch = "a" if d >= 0.005 else ("c" if d <= -0.005 else "b")
    rec = {"written_utc": datetime.now(timezone.utc).isoformat(), "entry_id": t41.get("entry_id"),
           "score_avg": t41["score_avg"], "rank": t41.get("rank"),
           "ta40": t40["score_avg"], "ta41_minus_ta40": d, "rule_branch": branch,
           "inside_band": -0.004 <= d <= 0.006, "registered_centre": 0.002,
           "nmae_up_vs_ta40": (t41.get("score_nmae") or 0) > (t40.get("score_nmae") or 0),
           "ta39": t39["score_avg"], "td28": t28["score_avg"], "td38": DAVIDE_T38, "ta41_minus_td38": t41["score_avg"] - DAVIDE_T38,
           "scaled_ta41_vs_ta40": members(t41, t40), "scaled_ta41_vs_td28": members(t41, t28),
           "bench_expected_scaled": {"score_nmae": 0.021, "score_pds": -0.012},
           "raw_ta41_ta40_ta39_td28": {k: [t41.get(k), t40.get(k), t39.get(k), t28.get(k)] for k in RAW}}
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
