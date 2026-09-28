"""Single-factor pairs of official submissions: the difference in the mean, member by member, against the seed noise.

Reads `invii.csv` (from raccolta.py). A pair is two submissions that differ in one declared change (the pairs and
their changes are the ones PROGETTO section 0 and the checkpoints state; t16 is absent because its status was not
saved, see CP-0037). For each pair: the difference in the mean and each scaled member's contribution to it (member
difference / 6), and whether the mean moved by more than the noise floor measured by t24 against t22 (one pair:
D = 0.0016; the rules read +/-0.005, about 3 x D). Also the composition of the best entry: which member carries it.

    scripts/py.cmd reports/invii/lezioni_invii_2026-09-28/coppie.py --invii reports/invii/lezioni_invii_2026-09-28/invii.csv \
        --out reports/invii/lezioni_invii_2026-09-28/coppie.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

SCALED = ["score_pds", "score_mse", "score_nmae", "score_fid", "score_reach", "score_jac"]
PAIRS = [  # (after, before, the one change)
    ("t10", "t08", "CD4 removed (K562 alone), trial-01 generator at amplitude 0.197"),
    ("t11", "t08", "HCT116 added to K562 + CD4, equal weights, amplitude 0.197"),
    ("t15", "t11", "amplitude doubled, 0.197 -> 0.394"),
    ("t17", "t15", "HEK293T added, amplitude matched on q99 (0.4285)"),
    ("t22", "t20", "HEK293T added to t20's three sources at equal weight"),
    ("t24", "t22", "generator seed only (replicate)"),
    ("t14", "t08", "ControlModel generator with effects x 2.5 instead of trial-01 x 0.197"),
]
NOISE = 0.0016
THRESHOLD = 0.005


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--invii", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    t = pd.read_csv(args.invii).set_index("trial")
    rows = []
    for a, b, change in PAIRS:
        if a not in t.index or b not in t.index:
            continue
        d = float(t.at[a, "score_avg"] - t.at[b, "score_avg"])
        row = {"after": a, "before": b, "change": change, "delta_mean": d,
               "beyond_threshold_0.005": abs(d) > THRESHOLD, "multiple_of_seed_noise": abs(d) / NOISE}
        for m in SCALED:
            row[f"{m}_contribution"] = float(t.at[a, m] - t.at[b, m]) / 6
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(args.out, index=False)
    pd.set_option("display.width", 250)
    show = ["after", "before", "delta_mean", "multiple_of_seed_noise"] + [f"{m}_contribution" for m in SCALED]
    print(out[show].round(4).to_string(index=False))
    best = t["score_avg"].idxmax()
    comp = {m: float(t.at[best, m]) / 6 for m in SCALED}
    print(f"\ncomposition of the best entry ({best}, mean {t.at[best, 'score_avg']:.4f}): " +
          ", ".join(f"{m} {v:+.4f}" for m, v in comp.items()))


if __name__ == "__main__":
    main()
