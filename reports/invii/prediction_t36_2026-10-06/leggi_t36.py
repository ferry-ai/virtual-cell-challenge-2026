"""Reader of the t36 (and, if given, t37) official result by the rule registered in prediction.json, written before
the score is known.

    python leggi_t36.py <t36 vcc json> [<t37 vcc json>]   -> writes comparison.json next to this file
t28's receipt is read from main (reports/invii/trial_2026-09-29/status_ZvrYZ4UazadAyuq4AsDB_20260929T2305.json).
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
T28 = "origin/main:reports/invii/trial_2026-09-29/status_ZvrYZ4UazadAyuq4AsDB_20260929T2305.json"
SCALED = ["score_pds", "score_mse", "score_nmae", "score_fid", "score_reach", "score_jac"]
RAW = ["pds_cosine", "expr_mse_unbiased_capped_norm", "de_wilcoxon_lfc_nmae", "de_wilcoxon_direction_fidelity_yield_raw",
       "de_wilcoxon_direction_reach_raw", "de_wilcoxon_sig_jaccard"]


def entry_text(text: str) -> dict:
    d = json.loads(text[text.index("{"):])
    while "score_avg" not in d:
        d = next(v for v in d.values() if isinstance(v, dict))
    return d


def entry(path: Path) -> dict:
    return entry_text(path.read_text(encoding="utf-8-sig"))


def branch(d: float, step: float, names) -> str:
    return names[0] if d >= step else (names[2] if d <= -step else names[1])


def members(a: dict, b: dict) -> dict:
    return {k: [a.get(k), b.get(k), (a.get(k) or 0) - (b.get(k) or 0)] for k in SCALED}


def main() -> None:
    out = HERE / "comparison.json"
    if out.exists():
        raise SystemExit("comparison.json exists: never overwrite")
    t36 = entry(Path(sys.argv[1]))
    t28 = entry_text(subprocess.run(["git", "show", T28], capture_output=True, text=True, check=True,
                                    encoding="utf-8").stdout)
    if t36.get("status") != "published" or t36.get("score_avg") is None:
        raise SystemExit(f"t36 not scored yet: {t36.get('status')}")
    d = t36["score_avg"] - t28["score_avg"]
    rec = {"written_utc": datetime.now(timezone.utc).isoformat(), "entry_id": t36.get("entry_id"),
           "score_avg": t36["score_avg"], "rank": t36.get("rank"), "t28": t28["score_avg"], "t36_minus_t28": d,
           "rule_branch": branch(d, 0.01, ("a_gain_at_least_0.01", "b_within_0.01", "c_loss_at_least_0.01")),
           "inside_band": 0.0 <= d <= 0.06,
           "scaled_vs_t28": members(t36, t28), "raw": {k: [t36.get(k), t28.get(k)] for k in RAW}}
    if len(sys.argv) > 2:
        t37 = entry(Path(sys.argv[2]))
        if t37.get("status") == "published" and t37.get("score_avg") is not None:
            r = t36["score_avg"] - t37["score_avg"]
            rec.update({"t37_entry_id": t37.get("entry_id"), "t37": t37["score_avg"], "t36_minus_t37": r,
                        "t37_minus_t28": t37["score_avg"] - t28["score_avg"],
                        "r_branch": branch(r, 0.005, ("R_stays", "R_not_conclusive", "R_removed")),
                        "scaled_t36_vs_t37": members(t36, t37)})
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
