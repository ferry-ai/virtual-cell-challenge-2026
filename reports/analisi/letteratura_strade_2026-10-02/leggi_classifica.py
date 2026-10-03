"""Read the public VCC 2026 validation leaderboard: raw and scaled members at a few ranks, and the self-declared
descriptions of the entries (the only public trace of what other teams do).

    python leggi_classifica.py --json lb.json            # a saved copy of the API answer
    curl -s "https://virtualcellchallenge.org/api/leaderboard?get_final=false&is_generalist=false" -o lb.json

The descriptions are declarations of their authors, not verified; names of people are not written anywhere.
"""
from __future__ import annotations

import argparse
import json

RAW = ["pds_cosine", "expr_mse_unbiased_capped_norm", "de_wilcoxon_lfc_nmae",
       "de_wilcoxon_direction_fidelity_yield_raw", "de_wilcoxon_direction_reach_raw", "de_wilcoxon_sig_jaccard"]
SCALED = ["score_pds", "score_mse", "score_nmae", "score_fid", "score_reach", "score_jac"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", required=True)
    ap.add_argument("--ranks", default="1,2,3,10,20,50,100,200,300")
    ap.add_argument("--descriptions", type=int, default=300, help="print descriptions down to this rank")
    a = ap.parse_args()
    d = json.load(open(a.json, encoding="utf-8"))
    e = sorted([x for x in d["entries"] if x.get("score_avg") is not None], key=lambda x: -x["score_avg"])
    print(f"{d['num_entries']} entries, {len(e)} scored")
    print("rank avg | " + " | ".join(f"{r}/{s}" for r, s in zip(RAW, SCALED)))
    for r in (int(v) for v in a.ranks.split(",")):
        x = e[r - 1]
        print(r, f"{x['score_avg']:.3f} |", " | ".join(f"{x[c]:.3f}/{x[s]:.3f}" for c, s in zip(RAW, SCALED)))
    for i, x in enumerate(e[:a.descriptions]):
        text = (x.get("description") or "").strip().replace("\n", " ")
        if len(text) > 25:
            print(f"\n{i + 1} {x['score_avg']:.3f} [{x.get('model_name')}] {text}")


if __name__ == "__main__":
    main()
