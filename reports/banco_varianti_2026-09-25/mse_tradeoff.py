"""Tenth pass: what the amplitude does to squared error, the member that is clipped to 0.

The owner asked (25 September) whether walking the amplitude upward (t16 -> t18) paints us
into a corner if the mse member is ever to leave 0. On each held-out public source, with
stage 100's loader, this measures in effect space:

* ``mse_ratio``: sum of w^2 (truth - a * pred)^2 over the sum of w^2 truth^2, i.e. the squared
  error of the prediction relative to predicting no change; below 1 means better than no
  change. w = x / (1 + x), x = 0.05 * mean CPM of A/B/C, the log1p weight of a small effect;
  panel genes excluded; truth NaN pairs skipped;
* ``a_star``: the amplitude that minimises it, sum w^2 truth pred / sum w^2 pred^2, and the
  ratio there (the best squared error a single amplitude can buy);
* ``detectable``: median genes per target with |a * pred| above 4 / sqrt(400 mu) at >= 5 CPM,
  the crude stand-in for DE calls of sweep_v3.py (no noise here).

Arms: raw (t15-t18) and the stage-98 shrunk effects (t19), at 0.197, 0.394, 0.788, 1.576.
The truth is a noisy public source, so every ratio is pulled toward 1; the ordering is the
point, not the level. Not VCC scores; the official mse is computed on generated cells.

    scripts/py.cmd reports/banco_varianti_2026-09-25/mse_tradeoff.py --out reports/banco_varianti_2026-09-25/r10
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "src"))

from analyze import DATA, FAMILY, SOURCES  # noqa: E402
from noise_sim import N_CELLS, UMI  # noqa: E402
from sweep_v2 import pooled, stage100  # noqa: E402

AMPS = (0.197, 0.394, 0.788, 1.576)


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
    keep = np.ones(axis.size, dtype=bool)
    keep[[col[g] for g in panel if g in col]] = False
    cpm = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)[["A", "B", "C"]].mean(axis=1).to_numpy()
    x = 0.05 * cpm
    w = x / (1.0 + x)
    mu = cpm * UMI / 1e6
    thr = np.where(mu > 0, 4.0 / np.sqrt(N_CELLS * np.maximum(mu, 1e-12)), np.inf)
    gate = cpm >= 5.0

    rows = []
    for held in SOURCES:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = stage100.load_table(args.cache, held, "raw")
        tidx = truth.index()
        base = [t for t in panel if t in tidx]
        arms = {"raw": pooled(args.cache, preds, base, "raw"), "shrunk": pooled(args.cache, preds, base, "shrunk")}
        ok = np.all([np.abs(e).sum(axis=1) > 0 for e, _ in arms.values()], axis=0)
        T = truth.raw[np.array([tidx[t] for t, o in zip(base, ok) if o])].astype(np.float64)
        valid = np.isfinite(T) & keep[None, :]
        Tw = np.where(valid, T * w, 0.0)
        null = float((Tw ** 2).sum())
        for name, (E, _) in arms.items():
            Pw = np.where(valid, E[ok] * w, 0.0)
            a_star = float((Pw * Tw).sum() / (Pw * Pw).sum())
            for a in AMPS + (a_star,):
                ratio = float(((Tw - a * Pw) ** 2).sum() / null)
                det = float(np.median(((np.abs(a * E[ok]) > thr[None, :]) & gate[None, :]).sum(axis=1)))
                rows.append({"held_out": held, "arm": name, "amplitude": round(a, 4),
                             "is_a_star": a == a_star, "mse_ratio": ratio, "detectable_median": det})
        print(held, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(args.out / "mse_tradeoff.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "banco_varianti_2026-09-25/mse_tradeoff.py", "claim_type":
                   "effect-space squared error against held-out public sources; not VCC scores",
                   "rows": rows}, f, indent=1)
    pd.set_option("display.width", 200)
    print(df.round(4).to_string())


if __name__ == "__main__":
    main()
