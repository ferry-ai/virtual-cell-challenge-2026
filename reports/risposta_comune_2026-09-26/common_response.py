"""How much of the squared error is the response every knockdown shares, and does it transfer?

The submission recipe removes from each source its common response (the mean over targets,
gamma 1), so every prediction lacks the part of the response that all knockdowns share. The
official `expr_mse_unbiased_capped_norm` compares with the whole response. On each held-out public
source (the other families as inputs, as in the r5 bench of reports/trasferimento_appreso_2026-09-26/)
this measures, in effect space with the log1p weights of the benches (w = x / (1 + x),
x = 0.05 x mean CPM of A/B/C, panel genes excluded):

* ``common_share``: the share of the truth's weighted energy explained by the truth's OWN mean
  over targets (an oracle: how large the common part is);
* ``common_transfer_r``: per-gene correlation between the inputs' common response and the truth's;
* squared-error ratios (1 = predicting no change) of: t20like (the recipe's transfer, centred) at
  its submission scale and at a fitted scale; the inputs' common response alone at a fitted scale;
  t20like plus the common response, two fitted scales. "fitted" = least squares on the OTHER three
  held-out sources (cross-fitted); the oracle fit on the source itself is reported beside it;
* the PDS proxy of t20like and of t20like plus the common response at the cross-fitted scales:
  what the shared shift costs the discrimination between targets.
Proxies against public sources, not VCC scores; the official member works on generated cells.

    scripts/py.cmd reports/risposta_comune_2026-09-26/common_response.py --out reports/risposta_comune_2026-09-26/r1
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "banco_varianti_2026-09-25"))

from analyze import pds_proxy  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402

_spec = importlib.util.spec_from_file_location("stage104", REPO / "scripts" / "104_learned_reweighting.py")
stage104 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage104)

DATA = Path("C:/Users/ferra/vcc2026-data")
SOURCES = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]


def family(name: str) -> str:
    return name.split("_")[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--pred", type=Path, default=DATA / "processed/lct_r5_predictions_2026-09-26")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = np.asarray(official_axis().symbols)
    G = axis.size
    col = {g: i for i, g in enumerate(axis)}
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    panel_cols = np.array([col[g] for g in panel if g in col])
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    x = 0.05 * basal[["A", "B", "C"]].mean(axis=1).to_numpy()
    w = (x / (1 + x)).astype(np.float64)
    w[panel_cols] = 0.0
    tables = {n: stage104.load(args.cache, n)[0] for n in SOURCES}

    stats, per_task = {}, {}
    for held in SOURCES:
        z = np.load(args.pred / f"{held}.npz")
        targets = z["targets"].astype(str).tolist()
        y = z["truth"].astype(np.float64)
        t20 = z["t20like"].astype(np.float64)
        preds = [s for s in SOURCES if family(s) != family(held)]
        commons = np.vstack([tables[s].common([t for t in panel if t in tables[s].index()]) for s in preds])
        c_in = commons.mean(axis=0)
        ok = np.isfinite(y)
        Y = np.where(ok, y, 0.0) * w
        A = np.where(ok, t20, 0.0) * w
        C = np.where(ok, np.broadcast_to(c_in, y.shape), 0.0) * w
        ybar = np.divide(np.where(ok, y, 0.0).sum(axis=0), ok.sum(axis=0), out=np.zeros(G), where=ok.sum(axis=0) > 0)
        Yc = np.where(ok, y - ybar, 0.0) * w
        null = float((Y ** 2).sum())
        stats[held] = {"YY": null, "AA": float((A * A).sum()), "CC": float((C * C).sum()), "AC": float((A * C).sum()),
                       "YA": float((Y * A).sum()), "YC": float((Y * C).sum())}
        g = w > 0
        r = float(np.corrcoef(c_in[g], ybar[g])[0, 1])
        per_task[held] = {"targets": len(targets), "inputs": preds, "common_share": 1.0 - float((Yc ** 2).sum()) / null,
                          "common_transfer_r": r, "t20_at_submission_scale": float(((Y - A) ** 2).sum()) / null,
                          "arrays": (Y, A, C, y, t20, c_in)}

    def solve(keys, s):
        """Least-squares scales for the columns ``keys`` of A (t20like) and C (common) from sums ``s``."""
        if keys == ("A",):
            return np.array([s["YA"] / s["AA"]])
        if keys == ("C",):
            return np.array([s["YC"] / s["CC"]])
        M = np.array([[s["AA"], s["AC"]], [s["AC"], s["CC"]]])
        return np.linalg.solve(M, np.array([s["YA"], s["YC"]]))

    def ratio(Y, parts, coef, null):
        P = sum(c * p for c, p in zip(coef, parts))
        return float(((Y - P) ** 2).sum()) / null

    rows = []
    for held in SOURCES:
        Y, A, C, y, t20, c_in = per_task[held].pop("arrays")
        null = stats[held]["YY"]
        others = [h for h in SOURCES if h != held]
        pooled = {k: sum(stats[h][k] for h in others) for k in stats[held]}
        row = {"held_out": held, **{k: v for k, v in per_task[held].items() if k != "inputs"},
               "inputs": "+".join(per_task[held]["inputs"])}
        for name, keys, parts in (("t20like", ("A",), (A,)), ("common", ("C",), (C,)), ("t20like+common", ("A", "C"), (A, C))):
            cf, orc = solve(keys, pooled), solve(keys, stats[held])
            row[f"{name}_scales_crossfit"] = [float(v) for v in cf]
            row[f"{name}_ratio_crossfit"] = ratio(Y, parts, cf, null)
            row[f"{name}_ratio_oracle"] = ratio(Y, parts, orc, null)
        cf = solve(("A", "C"), pooled)
        wv = w.astype(np.float32)
        base = pds_proxy(t20.astype(np.float32), y.astype(np.float32), wv, panel_cols)
        shifted = pds_proxy((cf[0] * t20 + cf[1] * np.broadcast_to(c_in, t20.shape)).astype(np.float32),
                            y.astype(np.float32), wv, panel_cols)
        row["pds_t20like"] = float(base.mean())
        row["pds_t20like_plus_common_crossfit"] = float(shifted.mean())
        rows.append(row)
        print(held, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
    pd.DataFrame(rows).to_csv(args.out / "summary.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "risposta_comune_2026-09-26/common_response.py",
                   "claim_type": "effect-space squared-error and PDS proxies against held-out public sources; "
                                 "cross-fitted scales from the other three sources, oracle fits beside them; not VCC scores",
                   "inputs": {"pred": str(args.pred), "cache": str(args.cache)}, "rows": rows}, fh, indent=1)


if __name__ == "__main__":
    main()
