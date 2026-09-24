"""Third pass: can the targets whose transfer ranks BELOW chance be recognised in advance?

A target whose predicted effects look more like other targets' responses than its own
scores below 0.5 on the PDS proxy; a zero prediction ties every competitor and scores
exactly 0.5 (midrank). With the trial-01 generator a zeroed target still gets its
generator calls, so the DE members would move little (interpretation, to be checked).

Nested rule, no use of the held-out source: for held-out H and predictor sources S, each
source s in S is predicted from the others in S (other families only), and a target's
transferability estimate is the mean of its per-target PDS proxies over those inner tests.
Targets with estimate < tau are zeroed; the held-out proxy of the gated prediction is
compared with the ungated one on the same targets. Effects as in analyze.py's base
variant (the t15 recipe) and zk4 (stage-98 shrunk).

    scripts/py.cmd reports/banco_varianti_2026-09-25/gating.py --out reports/banco_varianti_2026-09-25/r3
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from analyze import DATA, FAMILY, SOURCES, load, pds_proxy, predict  # noqa: E402

TAUS = (0.3, 0.4, 0.5, 0.6)


def per_target_pds(variant, preds, truth_name, cache, panel, weight, panel_cols):
    truth = load(cache, truth_name, "raw")
    tidx = truth.index()
    targets = [t for t in panel if t in tidx]
    P = predict(variant, preds, cache, targets)
    has = np.abs(P).sum(axis=1) > 0
    targets = [t for t, h in zip(targets, has) if h]
    P = P[has]
    T = truth.raw[np.array([tidx[t] for t in targets])].astype(np.float64)
    return dict(zip(targets, pds_proxy(P, T, weight, panel_cols)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "interim/basal_cpm_by_context.csv")
    ap.add_argument("--genes", type=Path, default=DATA / "raw/controls/gene_names.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = pd.read_csv(args.genes)["gene_name"].astype(str).to_numpy()
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    col = {g: i for i, g in enumerate(axis)}
    panel_cols = np.array([col[g] for g in panel if g in col])
    cpm = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)[["A", "B", "C"]].mean(axis=1).to_numpy()
    x = 0.05 * cpm
    weight = x / (1.0 + x)

    rows, per_rows = [], []
    for variant in ("base_g1", "shrunk_g1"):
        for held in SOURCES:
            preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
            outer = per_target_pds(variant, preds, held, args.cache, panel, weight, panel_cols)
            inner: dict[str, list[float]] = {}
            for s in preds:
                inner_preds = [p for p in preds if FAMILY[p] != FAMILY[s]]
                if not inner_preds:
                    continue
                for t, v in per_target_pds(variant, inner_preds, s, args.cache, panel, weight,
                                           panel_cols).items():
                    inner.setdefault(t, []).append(float(v))
            targets = [t for t in outer if t in inner]
            est = np.array([np.mean(inner[t]) for t in targets])
            out = np.array([outer[t] for t in targets])
            rho = float(pd.Series(est).corr(pd.Series(out), method="spearman"))
            for t, e, o in zip(targets, est, out):
                per_rows.append({"variant": variant, "held_out": held, "target": t, "inner_estimate": e,
                                 "outer_pds": o})
            row = {"variant": variant, "held_out": held, "predictors": "+".join(preds), "targets": len(targets),
                   "spearman_inner_outer": rho, "outer_mean_ungated": float(out.mean())}
            for tau in TAUS:
                gated = est < tau
                row[f"gated_share_tau{tau}"] = float(gated.mean())
                row[f"outer_mean_tau{tau}"] = float(np.where(gated, 0.5, out).mean())
                row[f"gain_tau{tau}"] = row[f"outer_mean_tau{tau}"] - row["outer_mean_ungated"]
            rows.append(row)
            print(variant, held, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(args.out / "gating.csv", index=False)
    pd.DataFrame(per_rows).to_csv(args.out / "per_target.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "banco_varianti_2026-09-25/gating.py", "claim_type":
                   "effect-space proxy, nested (inner estimates never see the held-out source); not VCC scores",
                   "cache": str(args.cache), "taus": TAUS, "rows": rows}, f, indent=1)
    cols = ["variant", "held_out", "targets", "spearman_inner_outer", "outer_mean_ungated"] + \
           [c for t in TAUS for c in (f"gated_share_tau{t}", f"gain_tau{t}")]
    print(df[cols].round(4).to_string())


if __name__ == "__main__":
    main()
