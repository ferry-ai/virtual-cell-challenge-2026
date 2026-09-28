"""Line, lab and cell state: how much two sources' knockdown profiles agree, on the same targets.

Reads the per-target tables of shared_response.py runs (condivisione_r*/per_target_<a>_<b>.csv) and puts
every pair on a common target set, so that differences between pairs are not differences between target
populations: the targets of Replogle's K562 essential screen that every listed pair measured, and
separately the non-essential targets shared by the pairs that cover them. Per pair: the cosine's quantiles
(profiles on genes expressed in A/B/C, log1p weights, own gene out, noise NOT removed: the SE-based noise
correction fails on Replogle's sources, whose summed SE^2 exceeds the observed energy), the share above
0.1, and the median cells of each side, because fewer cells mean a noisier profile and a lower cosine.
Descriptive, public sources.

    scripts/py.cmd reports/trasferimento/atlante_2026-09-26/pair_table.py --out reports/trasferimento/atlante_2026-09-26/confronto_r1 \
        --runs reports/trasferimento/atlante_2026-09-26/condivisione_r1 reports/trasferimento/atlante_2026-09-26/condivisione_r2 ...
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

DATA = Path("C:/Users/ferra/vcc2026-data")
KIND = {  # what differs between the two sides of a pair
    ("k562ess", "k562"): "same line, another experiment (same lab)",
    ("rpe1", "k562ess"): "another line, same lab and screen design",
    ("rpe1", "k562"): "another line, same lab",
    ("k562ess", "cd4_mix"): "another line and lab",
    ("rpe1", "cd4_mix"): "another line and lab",
    ("k562", "cd4_mix"): "another line and lab",
    ("k562", "cd4_Rest"): "another line and lab",
    ("k562", "cd4_Stim48hr"): "another line and lab",
    ("cd4_Rest", "cd4_Stim8hr"): "same cells and donors, another state",
    ("cd4_Rest", "cd4_Stim48hr"): "same cells and donors, another state",
    ("cd4_Stim8hr", "cd4_Stim48hr"): "same cells and donors, another state",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", type=Path, required=True)
    ap.add_argument("--essential", type=Path, default=DATA / "external/K562_essential_raw_bulk_01.h5ad")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    with h5py.File(args.essential, "r") as fh:
        essential = {s.decode().split("_")[1] for s in fh["obs/gene_transcript"][:] if b"non-targeting" not in s}
    tables = {}
    for run in args.runs:
        for f in sorted(run.glob("per_target_*.csv")):
            df = pd.read_csv(f)
            cells = [c for c in df.columns if c.startswith("cells_")]
            a, b = (c[len("cells_"):] for c in cells)
            if (a, b) not in tables:
                tables[(a, b)] = df.assign(source=f"{run.name}/{f.name}")
    rows = []
    for label, keep in (("essential", lambda t: t in essential), ("non-essential", lambda t: t not in essential)):
        pairs = {k: v[v.target.map(keep)] for k, v in tables.items()}
        pairs = {k: v for k, v in pairs.items() if len(v) >= 200}
        if not pairs:
            continue
        common = set.intersection(*(set(v.target) for v in pairs.values()))
        for (a, b), v in pairs.items():
            v = v[v.target.isin(common)]
            q = np.quantile(v.cosine, [0.25, 0.5, 0.75, 0.9])
            rows.append({"targets": label, "pair": f"{a} x {b}", "differs_by": KIND.get((a, b), ""), "n_targets": len(v),
                         "cosine_q25": q[0], "cosine_median": q[1], "cosine_q75": q[2], "cosine_q90": q[3],
                         "share_above_0.1": float((v.cosine > 0.1).mean()),
                         f"cells_median_a": float(v[f"cells_{a}"].median()), f"cells_median_b": float(v[f"cells_{b}"].median()),
                         "from": v.source.iloc[0]})
    out = pd.DataFrame(rows)
    out.to_csv(args.out / "pairs.csv", index=False, float_format="%.4f")
    with (args.out / "summary.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "atlante_2026-09-26/pair_table.py", "claim_type": "descriptive, public sources; cosine "
                   "with noise, compare only with the cell counts beside it", "rows": rows}, fh, indent=1, default=float)
    pd.set_option("display.width", 250)
    print(out.drop(columns=["from"]).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
