"""Eighth pass, after t16's score: shrinkage against the t16 recipe at comparable detectability.

t16 (raw effects x 0.788) gained mostly on the DE members (CP-0037), so a variant that moves
fewer genes can lose there what it gains on PDS. This pass keeps the corrected set-up of
`sweep_v2.py` (stage 100's loader, one target set per held-out source) and the model of the
trial-01 profile step and pseudobulk noise, and adds, per arm:

* ``detectable``: genes at >= 5 CPM in the context whose realised |ln fc| exceeds
  4 / sqrt(400 * mu), mu = counts per cell (a z of about 4 for a Poisson mean over 400 cells);
  a crude stand-in for the prediction's own DE calls, not the scorer's Wilcoxon;
* ``det_precision``: share of detectable genes whose realised sign matches the held-out
  source's sign (held-out effect finite and non-zero, significance not required, as the
  scorer's k); ``det_yield``: k / max(detectable, n_conf), n_conf = held-out |raw/se| >= 3.

Arms: raw at 0.788 (t16) and 1.576 (the next step of t16's rule); zk4 and zk16 on a grid of
amplitudes, capped at |ln fc| 3. Two noise seeds.

    scripts/py.cmd reports/banco_varianti_2026-09-25/sweep_v3.py --out reports/banco_varianti_2026-09-25/r8
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
from noise_sim import N_CELLS, UMI, rank_pds  # noqa: E402
from noise_sim2 import realise  # noqa: E402
from sweep_v2 import pooled, stage100  # noqa: E402

SEEDS = (1, 2)
GRID = (0.788, 1.576, 3.152, 6.304, 12.608)


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
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)

    rows = []
    for held in SOURCES:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = stage100.load_table(args.cache, held, "raw")
        tidx = truth.index()
        base = [t for t in panel if t in tidx]
        arms = {"raw": pooled(args.cache, preds, base, "raw"),
                "zk4": pooled(args.cache, preds, base, "zshrink", 4.0),
                "zk16": pooled(args.cache, preds, base, "zshrink", 16.0)}
        ok = np.all([np.abs(e).sum(axis=1) > 0 for e, _ in arms.values()], axis=0)
        targets = [t for t, o in zip(base, ok) if o]
        rows_t = np.array([tidx[t] for t in targets])
        T = truth.raw[rows_t].astype(np.float64)
        Z = (truth.raw[rows_t] / truth.se[rows_t]).astype(np.float64)
        observed = arms["raw"][1][ok] > 0
        tcols = np.array([col.get(t, -1) for t in targets])
        sim = {"raw@0.788": arms["raw"][0][ok] * 0.788, "raw@1.576": arms["raw"][0][ok] * 1.576}
        for name in ("zk4", "zk16"):
            for a in GRID:
                sim[f"{name}@{a}"] = np.clip(arms[name][0][ok] * a, -3.0, 3.0)
        for c in ("A", "B", "C"):
            cpm = basal[c].to_numpy(dtype=float)
            x = 0.05 * cpm
            live = keep & (cpm > 0)
            gate = cpm >= 5.0
            mu = cpm * UMI / 1e6
            thr = np.where(mu > 0, 4.0 / np.sqrt(N_CELLS * np.maximum(mu, 1e-12)), np.inf)
            Tl = (np.log1p(x * np.exp(np.clip(np.nan_to_num(T), -20, 20))) - np.log1p(x))[:, live]
            tsign = np.sign(np.nan_to_num(T))
            conf = (np.abs(np.nan_to_num(Z)) >= 3) & gate[None, :]
            conf[np.arange(len(targets))[tcols >= 0], tcols[tcols >= 0]] = False
            n_conf = conf.sum(axis=1)
            for name, E in sim.items():
                pds, det, prec, yld = [], [], [], []
                for seed in SEEDS:
                    noisy, _, real_ln = realise(E, cpm, observed, np.random.default_rng(seed))
                    D = (np.log1p(x * np.exp(np.clip(noisy, -20, 20))) - np.log1p(x))[:, live]
                    pds.append(float(rank_pds(D, Tl).mean()))
                    called = (np.abs(noisy) > thr[None, :]) & gate[None, :]
                    called[np.arange(len(targets))[tcols >= 0], tcols[tcols >= 0]] = False
                    judged = called & (tsign != 0)
                    k = (judged & (np.sign(noisy) == tsign)).sum(axis=1)
                    n = judged.sum(axis=1)
                    det.append(float(np.median(called.sum(axis=1))))
                    prec.append(float(k.sum() / max(n.sum(), 1)))
                    yld.append(float(np.mean(k / np.maximum(np.maximum(n, n_conf), 1))))
                rows.append({"held_out": held, "context": c, "arm": name, "targets": len(targets),
                             "pds_proxy_generator": float(np.mean(pds)), "detectable_median": float(np.mean(det)),
                             "det_precision": float(np.mean(prec)), "det_yield": float(np.mean(yld)),
                             "n_conf_median": float(np.median(n_conf))})
            print(held, c, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(args.out / "sweep_v3.csv", index=False)
    summary = df.groupby(["held_out", "arm"])[["pds_proxy_generator", "detectable_median", "det_precision",
                                              "det_yield", "n_conf_median"]].mean().round(4).reset_index()
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "banco_varianti_2026-09-25/sweep_v3.py", "claim_type":
                   "model of the generator step and of detectability on an effect-space proxy; not VCC scores",
                   "seeds": SEEDS, "grid": GRID, "summary": summary.to_dict("records")}, f, indent=1)
    pd.set_option("display.width", 200)
    print(summary.to_string())


if __name__ == "__main__":
    main()
