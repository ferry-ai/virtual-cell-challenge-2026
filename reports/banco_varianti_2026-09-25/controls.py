"""Fifth pass: negative controls for the shrinkage gain, and where the gain comes from.

* Shuffled targets: the rows of each prediction are permuted among targets (five seeds);
  a proxy that rewards sparsity itself would stay above 0.5 for the shrunk effects.
* Per-target gain of zk64 over raw (no noise), against the target's source support: the
  number of predictor sources that measured it, their cells, and the largest |z| any of
  them reports; a gain confined to targets with one weak source would be a warning.

    scripts/py.cmd reports/banco_varianti_2026-09-25/controls.py --out reports/banco_varianti_2026-09-25/r5
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

from analyze import DATA, FAMILY, SOURCES, pds_proxy  # noqa: E402
from shrink_sweep import table  # noqa: E402
from vcc2026.multisource import mix  # noqa: E402


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

    shuffled, per_target = [], []
    for held in SOURCES:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = table(args.cache, held, None)
        tidx = truth.index()
        base_targets = [t for t in panel if t in tidx]
        P = {}
        for name, k in (("raw", None), ("zk16", 16.0), ("zk64", 64.0)):
            tabs = [table(args.cache, s, k) for s in preds]
            E, den = mix(tabs, base_targets, weights={s: 1.0 for s in preds}, gamma=1.0, reliability_scale=100.0)
            E[den == 0] = 0.0
            P[name] = E
        has = np.abs(P["raw"]).sum(axis=1) > 0
        targets = [t for t, h in zip(base_targets, has) if h]
        T = truth.raw[np.array([tidx[t] for t in targets])].astype(np.float64)
        pds = {name: pds_proxy(E[has], T, weight, panel_cols) for name, E in P.items()}
        for name, E in P.items():
            vals = [float(pds_proxy(E[has][np.random.default_rng(s).permutation(len(targets))], T, weight,
                                    panel_cols).mean()) for s in range(5)]
            shuffled.append({"held_out": held, "variant": name, "true_order": float(pds[name].mean()),
                             "shuffled_mean": float(np.mean(vals)), "shuffled_min": float(np.min(vals)),
                             "shuffled_max": float(np.max(vals))})
        raw_tabs = [table(args.cache, s, None) for s in preds]
        for i, t in enumerate(targets):
            n_src, cells, zmax = 0, 0.0, 0.0
            for tab in raw_tabs:
                j = tab.index().get(t)
                if j is None:
                    continue
                n_src += 1
                cells += float(tab.n_cells[j])
                z = np.abs(tab.raw[j] / tab.se[j])
                zmax = max(zmax, float(np.nanmax(np.where(np.isfinite(z), z, 0.0))))
            per_target.append({"held_out": held, "target": t, "pds_raw": float(pds["raw"][i]),
                               "pds_zk64": float(pds["zk64"][i]), "gain_zk64": float(pds["zk64"][i] - pds["raw"][i]),
                               "predictor_sources": n_src, "predictor_cells": cells, "predictor_max_abs_z": zmax})
        print(held, "done", flush=True)

    sh = pd.DataFrame(shuffled)
    pt = pd.DataFrame(per_target)
    sh.to_csv(args.out / "shuffled.csv", index=False)
    pt.to_csv(args.out / "per_target_gain.csv", index=False)
    pt["support"] = pd.cut(pt.predictor_max_abs_z, [0, 5, 10, 20, np.inf], labels=["<5", "5-10", "10-20", ">=20"])
    by_support = (pt.groupby(["held_out", "support"], observed=True)
                    .agg(targets=("gain_zk64", "size"), mean_gain=("gain_zk64", "mean"),
                         share_gaining=("gain_zk64", lambda g: float((g > 0).mean())))
                    .round(4).reset_index())
    by_sources = (pt.groupby(["held_out", "predictor_sources"])
                    .agg(targets=("gain_zk64", "size"), mean_gain=("gain_zk64", "mean")).round(4).reset_index())
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "banco_varianti_2026-09-25/controls.py", "claim_type":
                   "negative control and decomposition of an effect-space proxy; not VCC scores",
                   "shuffled": sh.round(4).to_dict("records"), "gain_by_support": by_support.to_dict("records"),
                   "gain_by_predictor_sources": by_sources.to_dict("records")}, f, indent=1, default=str)
    print(sh.round(4).to_string())
    print(by_support.to_string())
    print(by_sources.to_string())


if __name__ == "__main__":
    main()
