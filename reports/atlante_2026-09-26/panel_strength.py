"""Are the 300 panel targets stronger knockdowns than the average one? A check of the atlas bench's design.

The atlas bench tests on a random sample of targets outside the panel. If the panel's targets were much
stronger than the typical knockdown, that sample would not stand for them. Per target of each universe:
the energy of its shrunk effects on genes expressed in A/B/C (log1p weights of the scorer, own gene out),
and for K562 the count of those genes with |raw/se| >= 3; then the panel's targets' percentiles among the
others. Public sources only; descriptive.

    scripts/py.cmd reports/atlante_2026-09-26/panel_strength.py --out reports/atlante_2026-09-26/forza_pannello \
        --universe k562=<dir> --universe cd4_mix=<dir>
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

from atlas_bench import DATA, Universe  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", action="append", required=True, metavar="NAME=DIR")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = np.asarray(official_axis().symbols)
    col = {g: i for i, g in enumerate(axis)}
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    cpm = basal[["A", "B", "C"]].mean(axis=1).to_numpy()
    x = 0.05 * cpm
    w = x / (1.0 + x)
    gate = cpm >= 5.0
    panel = set(pd.read_csv(args.panel).iloc[:, 0].astype(str))
    summary = {"stage": "atlante_2026-09-26/panel_strength.py", "claim_type": "descriptive, public sources", "sources": []}
    for spec in args.universe:
        name, _, folder = spec.partition("=")
        u = Universe(name, Path(folder))
        ts = sorted(u.targets)
        rows = []
        for b0 in range(0, len(ts), 400):
            tab = u.table(ts[b0:b0 + 400])
            E = np.where(gate[None, :], np.nan_to_num(tab.shrunk) * w[None, :], 0.0)
            with np.errstate(divide="ignore", invalid="ignore"):
                Z = np.where(gate[None, :], np.nan_to_num(tab.raw / tab.se), 0.0)
            for i, t in enumerate(tab.targets):
                j = col.get(t)
                if j is not None:
                    E[i, j] = 0.0
                    Z[i, j] = 0.0
                sig = int((np.abs(Z[i]) >= 3).sum()) if np.isfinite(tab.se[i]).any() else None
                rows.append({"target": t, "panel": t in panel, "energy": float((E[i] ** 2).sum()),
                             "genes_z3": sig, "cells": float(tab.n_cells[i])})
        df = pd.DataFrame(rows)
        df.to_csv(args.out / f"strength_{name}.csv", index=False, float_format="%.6g")
        other = df.loc[~df.panel, "energy"].to_numpy()
        pct = np.array([(other < v).mean() for v in df.loc[df.panel, "energy"]])
        entry = {"source": name, "targets": int(len(df)), "panel_targets": int(df.panel.sum())}
        for label, g in (("panel", df[df.panel]), ("other", df[~df.panel])):
            entry[f"energy_quantiles_{label}"] = [float(q) for q in np.quantile(g.energy, [0.1, 0.25, 0.5, 0.75, 0.9])]
            entry[f"cells_median_{label}"] = float(g.cells.median())
            if g.genes_z3.notna().any():
                entry[f"genes_z3_median_{label}"] = float(g.genes_z3.dropna().median())
        entry["panel_percentile_among_other"] = [float(q) for q in np.quantile(pct, [0.25, 0.5, 0.75])]
        summary["sources"].append(entry)
        print(json.dumps(entry), flush=True)
    with (args.out / "summary.json").open("x", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)


if __name__ == "__main__":
    main()
