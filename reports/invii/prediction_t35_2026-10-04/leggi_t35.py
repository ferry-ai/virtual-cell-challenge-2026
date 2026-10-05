"""Reader of the t35 official result by the rule registered in prediction.json (written before the score is known).

    python leggi_t35.py <t35 vcc json (submit raw or status)>   -> writes comparison.json next to this file
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
T34 = HERE.parent / "trial_rlead_2026-10-04" / "status_SjJp6tuHoMRL7VlQEvFY.json"
SCALED = ["score_pds", "score_mse", "score_nmae", "score_fid", "score_reach", "score_jac"]
RAW = ["pds_cosine", "expr_mse_unbiased_capped_norm", "de_wilcoxon_lfc_nmae", "de_wilcoxon_direction_fidelity_yield_raw",
       "de_wilcoxon_direction_reach_raw", "de_wilcoxon_sig_jaccard"]


def entry(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    d = json.loads(text[text.index("{"):])
    while "score_avg" not in d:
        d = next(v for v in d.values() if isinstance(v, dict))
    return d


def main() -> None:
    out = HERE / "comparison.json"
    if out.exists():
        raise SystemExit("comparison.json exists: never overwrite")
    t35, t34 = entry(Path(sys.argv[1])), entry(T34)
    if t35.get("status") != "published" or t35.get("score_avg") is None:
        raise SystemExit(f"t35 not scored yet: {t35.get('status')}")
    d = t35["score_avg"] - t34["score_avg"]
    branch = "a_gain_at_least_0.005" if d >= 0.005 else ("c_loss_at_least_0.005" if d <= -0.005 else "b_within_0.005")
    rec = {"written_utc": datetime.now(timezone.utc).isoformat(), "entry_id": t35.get("entry_id"),
           "score_avg": t35["score_avg"], "rank": t35.get("rank"), "t34": t34["score_avg"], "t35_minus_t34": d,
           "rule_branch": branch, "inside_band": 0.005 <= d <= 0.03,
           "scaled": {k: [t35.get(k), t34.get(k), (t35.get(k) or 0) - (t34.get(k) or 0)] for k in SCALED},
           "raw": {k: [t35.get(k), t34.get(k)] for k in RAW}}
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
