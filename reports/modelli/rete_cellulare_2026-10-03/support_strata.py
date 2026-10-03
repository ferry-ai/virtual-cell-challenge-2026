"""Lane A errors by the number of training line groups that teach each target (descriptive, the question of Codex).

Joins the lane A rows of one held-out line (per_target_<line>.csv.gz, class C) with the matrix of target_matrix.py
(eval_support.csv, target_by_group.csv.gz) on the symbol, and reports the mean PDS of `cells`, of the transfer with the
same information and of `mean` per stratum, with two counts of support: any modality and any admitted cell (the reading
of matrix_r1/LETTURA.md), and CRISPRi only with at least --min-cells cells per target and group (Codex's sensitivity).
Strata compare different targets: this is not the effect of adding contexts (matrix_r1/NOTA_CODEX.md).

    py.cmd support_strata.py --line H1 <laneA dir> <matrix dir> [--line ...] --out <new dir>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ARMS = ("cells", "transfer_cells", "mean")


def stratum(n: int) -> str:
    return str(n) if n <= 4 else "5+"


def strata(lane: Path, matrix: Path, line: str, min_cells: int) -> pd.DataFrame:
    rows = pd.read_csv(lane / f"per_target_{line}.csv.gz", keep_default_na=False, na_values=["", "nan", "NaN"])
    rows = rows[(rows.cls == "C") & rows.arm.isin(ARMS)]
    sup = pd.read_csv(matrix / "eval_support.csv").query("`class` == 'C'")
    any_n = sup.groupby("symbol").training_groups_any.max()
    tbg = pd.read_csv(matrix / "target_by_group.csv.gz")
    strict = (tbg[(tbg.modality == "CRISPRi") & (tbg.training_cells >= min_cells)]
              .groupby("symbol").group.nunique())
    wide = rows.pivot_table(index=["table", "target_key", "symbol"], columns="arm", values="pds").reset_index()
    wide["groups_any"] = wide.symbol.map(any_n)
    wide["groups_crispri"] = wide.symbol.map(strict).fillna(0).astype(int)
    out = []
    for count in ("groups_any", "groups_crispri"):
        known = wide.dropna(subset=[count])
        for s, g in known.groupby(known[count].astype(int).map(stratum)):
            out.append({"line": line, "count": count, "stratum": s, "targets": len(g),
                        **{f"pds_{a}": g[a].mean() for a in ARMS},
                        "cells_minus_transfer": (g["cells"] - g["transfer_cells"]).mean(),
                        "cells_minus_mean": (g["cells"] - g["mean"]).mean()})
        out.append({"line": line, "count": count, "stratum": "missing", "targets": int(wide[count].isna().sum())})
    return pd.DataFrame(out)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--line", nargs=3, action="append", required=True, metavar=("GROUP", "LANE_A", "MATRIX"))
    p.add_argument("--min-cells", type=int, default=20)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    table = pd.concat([strata(Path(lane), Path(matrix), g, a.min_cells) for g, lane, matrix in a.line])
    a.out.mkdir(parents=True)
    table.to_csv(a.out / "strata.csv", index=False)
    (a.out / "run.json").write_text(json.dumps({"lines": a.line, "min_cells": a.min_cells}, indent=1), encoding="utf-8")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(table.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
