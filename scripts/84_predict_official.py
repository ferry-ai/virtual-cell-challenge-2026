"""Stage 84: predict a submission's official score from a bench arm, and register it first.

Three ingredients, all measured:

1. a bench arm's six RAW members (`reports/bench_2026-09-17/*_bench.json`, field `raw`);
2. a CALIBRATION pair -- one bench arm whose configuration was also submitted and scored,
   giving a per-member ratio `official_raw / bench_raw`;
3. the official anchors solved by stage 82, which turn a raw value into the scaled score.

The output is a prediction, not a measurement, and its weakest link is (2): a single
scored submission gives one ratio per member with no error bar, and the ratios measured on
2026-09-17 range from 0.10 (jaccard) to 1.33 (mse). Written BEFORE the submission it
describes, so that comparing it afterwards means something.

    python scripts/84_predict_official.py --bench reports/bench_2026-09-17/hepg2_h002_bench.json \
        --arm "transfer_a2.0+cismeas_a1.0+cis_a1.0" \
        --calib-arm "transfer_a1.0+cismeas_a1.0+cis_a1.0" \
        --calib-status reports/trial_2026-09-17/status_49Gvtu504clN1mIu8T2V.json \
        --anchors reports/anchors_2026-09-17/anchors.json --out reports/prediction_t03_2026-09-17
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

MEMBERS = ["pds_cosine", "expr_mse_unbiased_capped_norm", "de_wilcoxon_lfc_nmae",
           "de_wilcoxon_direction_fidelity_yield_raw", "de_wilcoxon_direction_reach_raw",
           "de_wilcoxon_sig_jaccard"]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bench", type=Path, required=True)
    p.add_argument("--arm", required=True, help="the arm whose official score we predict")
    p.add_argument("--calib-arm", required=True, help="the arm matching an already scored submission")
    p.add_argument("--calib-status", type=Path, required=True, help="that submission's `vcc status --json`")
    p.add_argument("--anchors", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--label", default=None, help="what the prediction is about, e.g. the file name")
    args = p.parse_args()
    if (args.out / "prediction.json").exists():
        raise SystemExit(f"{args.out} already holds a prediction; a registered prediction is never overwritten")
    args.out.mkdir(parents=True, exist_ok=True)

    bench = json.loads(args.bench.read_text(encoding="utf-8"))["results"]
    arm = bench[args.arm]["raw"]
    calib_bench = bench[args.calib_arm]["raw"]
    scored = json.loads(args.calib_status.read_text(encoding="utf-8-sig"))
    anchors = json.loads(args.anchors.read_text(encoding="utf-8"))["anchors"]

    rows, total, n = {}, 0.0, 0
    for m in MEMBERS:
        ratio = scored[m] / calib_bench[m] if calib_bench[m] else None
        pred_raw = arm[m] * ratio if ratio is not None else None
        a = anchors.get(m)
        if a is None or pred_raw is None:
            rows[m] = {"bench_raw": arm[m], "calib_bench_raw": calib_bench[m], "calib_official_raw": scored[m],
                       "ratio": ratio, "predicted_raw": pred_raw, "predicted_scaled": None,
                       "note": "anchors unsolved for this member; the challenge clipped it to 0 in both "
                               "scored entries, so 0 is the value assumed in the average"}
            total += 0.0
            n += 1
            continue
        s = (pred_raw - a["baseline"]) / (a["replicate"] - a["baseline"])
        rows[m] = {"bench_raw": arm[m], "calib_bench_raw": calib_bench[m], "calib_official_raw": scored[m],
                   "ratio": ratio, "predicted_raw": pred_raw, "predicted_scaled": s,
                   "baseline": a["baseline"], "replicate": a["replicate"]}
        total += s
        n += 1

    payload = {
        "stage": "84_predict_official", "written_utc": datetime.now(timezone.utc).isoformat(),
        "label": args.label or args.arm, "arm": args.arm,
        "calibration": {"arm": args.calib_arm, "entry_id": scored["entry_id"],
                        "official_score_avg": scored["score_avg"]},
        "inputs": {"bench": str(args.bench), "status": str(args.calib_status), "anchors": str(args.anchors)},
        "members": rows, "predicted_score_avg": total / n,
        "claim_type": ("PREDICTION, registered before the submission it describes. Rests on a one-point "
                       "per-member calibration from bench raw to official raw, with no error bar."),
    }
    (args.out / "prediction.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"{'membro':46s} {'banco':>9} {'ratio':>7} {'raw atteso':>11} {'scalato atteso':>15}")
    for m, r in rows.items():
        s = r["predicted_scaled"]
        print(f"{m:46s} {r['bench_raw']:9.4f} {r['ratio'] or float('nan'):7.3f} "
              f"{r['predicted_raw'] or float('nan'):11.4f} "
              + (f"{s:+15.4f}" if s is not None else f"{'0 (tosato)':>15}"))
    print(f"\nmedia attesa: {payload['predicted_score_avg']:+.4f}   "
          f"(calibrazione: {args.calib_arm} -> {scored['entry_id']}, {scored['score_avg']:+.4f})")


if __name__ == "__main__":
    main()
