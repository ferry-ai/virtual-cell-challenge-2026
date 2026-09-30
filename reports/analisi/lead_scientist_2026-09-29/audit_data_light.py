"""Read-only, lightweight audit of basal profiles, universe indices and saved bridge results.

No raw matrices, identities, network access or new model fit. Existing bridge results
are stratified retrospectively, so these are exploratory summaries, not validation.
Run through scripts/py.cmd; --out must be a new directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def describe(x: pd.Series) -> dict:
    x = pd.to_numeric(x, errors="coerce").dropna()
    return {"n": len(x), "median": float(x.median()) if len(x) else None,
            "q25": float(x.quantile(.25)) if len(x) else None,
            "q75": float(x.quantile(.75)) if len(x) else None,
            "mean": float(x.mean()) if len(x) else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("C:/Users/ferra/vcc2026-data"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[3]
    panel = set(pd.read_csv(args.data / "raw/controls/pert_counts.csv").target_gene)
    basal = pd.read_csv(args.data / "processed/basal_sources_2026-09-28.csv", index_col=0)
    basal_rows = []
    for name, values in basal.items():
        scale = 1e6 / values.sum()
        basal_rows.append({"source": name, "measured": int(values.notna().sum()),
                           "cpm_sum_on_axis": float(values.sum()), "renormalization_factor": float(scale),
                           "above5_before": int((values >= 5).sum()),
                           "above5_after": int((values * scale >= 5).sum()),
                           "new_above5": int(((values < 5) & (values * scale >= 5)).sum())})
    pd.DataFrame(basal_rows).to_csv(args.out / "basal_scale.csv", index=False)

    universe_rows = []
    for index in sorted((args.data / "processed").glob("universe*/index.csv")):
        x = pd.read_csv(index)
        x = x.loc[x.chunk.notna() & x.chunk.astype(str).str.strip().ne("")]
        p = x[x.target.isin(panel)]
        universe_rows.append({"source": index.parent.name, "targets": len(x), "panel": len(p),
                              "cells_median": float(x.n_cells.median()),
                              "panel_cells_median": float(p.n_cells.median()) if len(p) else None,
                              "panel_lt50": int((p.n_cells < 50).sum()),
                              "panel_lt100": int((p.n_cells < 100).sum())})
    pd.DataFrame(universe_rows).to_csv(args.out / "universe_coverage.csv", index=False)

    bridge = repo / "reports/sorgenti/ponte_flex_2026-09-28"
    one = pd.read_csv(bridge / "r1/pair_viperturb_flex__k562_3p.csv")
    two = pd.read_csv(bridge / "r2/per_target.csv")
    panel_one, panel_two = one[one.target.isin(panel)], two[two.target.isin(panel)]
    panel_one.to_csv(args.out / "flex_bridge_panel.csv", index=False)
    panel_two.to_csv(args.out / "flex_split_half_selected_panel.csv", index=False)
    summary = {"claim_type": "retrospective descriptive stratification, not VCC scores",
               "bridge_r1_panel": {c: describe(panel_one[c]) for c in one.columns if c != "target"},
               "bridge_r1_nonpanel": {"cosine": describe(one.loc[~one.target.isin(panel), "cosine"])},
               "bridge_r2_selected_panel": {c: describe(panel_two[c]) for c in two.columns if c != "target"},
               "selection_caveat": "r2 includes only targets selected for >=30 significant genes in both full screens; neither independent nor representative of the panel"}
    paired = panel_two.dropna(subset=["viperturb_halfa__viperturb_halfb", "viperturb_halfa__k562_3p", "viperturb_halfb__k562_3p"])
    summary["bridge_r2_paired_selected_panel"] = {c: describe(paired[c]) for c in paired.columns if c != "target"}
    vi = pd.read_csv(args.data / "processed/universe_viperturb_2026-09-27_p1/index.csv")
    vi = vi.loc[vi.chunk.notna() & vi.target.isin(panel)].copy()
    vi = vi.merge(panel_one, how="left", on="target")
    vi = vi.merge(panel_two[["target", "viperturb_halfa__viperturb_halfb"]], how="left", on="target")
    vi.to_csv(args.out / "flex_panel_coverage.csv", index=False)
    summary["viperturb_panel"] = {"covered": len(vi), "with_existing_bridge": int(vi.cosine.notna().sum()),
                                  "with_existing_split_half": int(vi.viperturb_halfa__viperturb_halfb.notna().sum()),
                                  "n_cells": describe(vi.n_cells)}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
