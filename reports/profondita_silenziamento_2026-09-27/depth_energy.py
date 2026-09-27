"""Does a target's downstream response grow with how deeply its own gene is silenced, across cell lines?

Exploratory, no decision rule. For every universe (stage-98 chunks + index.csv, read with the atlas's `Universe`),
per target whose own gene is on the axis:
* depth d = -raw at the target's own column (natural-log fold change; positive when the gene falls), and its z;
* downstream energy E = mean of shrunk^2 over a fixed gene set G* (genes with basal CPM >= --min-cpm in every
  context of the run, from the basal table), the target's own gene and genes within 5 kb of its TSS left out,
  over the entries that are finite (`n_genes` counts them).
Then for every pair of universes, on the targets both measured with a clear knockdown in both (z <= -3, d > 0), the
least-squares slope and the correlation of log(E_a / E_b) on log(d_a / d_b), with a bootstrap over targets. If the
downstream response scaled linearly with depth, energy would scale with depth squared: slope near 2. Noise in d
biases the slope toward 0, so the slope is a lower bound on the coupling, not an estimate of it.

    scripts/py.cmd reports/profondita_silenziamento_2026-09-27/depth_energy.py --out <new dir> \
        --universe k562=<dir> --universe orion_hct116=<dir> ...
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "atlante_2026-09-26"))

from atlas_bench import Universe  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402

DATA = Path("C:/Users/ferra/vcc2026-data")
NEAR_BP = 5000
N_BOOT = 1000


def load_coords(path: Path) -> pd.DataFrame:
    c = pd.read_csv(path, sep="\t")
    return c.drop_duplicates("symbol").set_index("symbol")


def per_target(uni: Universe, axis: np.ndarray, gstar: np.ndarray, coords: pd.DataFrame, batch: int) -> pd.DataFrame:
    col = {g: i for i, g in enumerate(axis)}
    chrom = coords.reindex(axis)["chrom"].astype(str).to_numpy()
    tss = coords.reindex(axis)["tss"].to_numpy(dtype=float)
    targets = sorted(t for t in uni.targets if t in col)
    rows = []
    for start in range(0, len(targets), batch):
        part = targets[start:start + batch]
        tab = uni.table(part)
        ix = tab.index()
        for t in part:
            if t not in ix:
                continue
            i, own = ix[t], col[t]
            raw, se = float(tab.raw[i, own]), float(tab.se[i, own])
            keep = gstar.copy()
            keep[own] = False
            if t in coords.index:
                c, p = str(coords.at[t, "chrom"]), float(coords.at[t, "tss"])
                keep &= ~((chrom == c) & (np.abs(tss - p) <= NEAR_BP))
            v = tab.shrunk[i, keep].astype(np.float64)
            v = v[np.isfinite(v)]
            rows.append({"target": t, "d": -raw, "z_own": raw / se if np.isfinite(se) and se > 0 else np.nan,
                         "energy": float(np.mean(v ** 2)) if v.size else np.nan, "n_genes": int(v.size)})
    return pd.DataFrame(rows).set_index("target")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", action="append", required=True, metavar="NAME=DIR[:BASALCOL]")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-27.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--min-cpm", type=float, default=10.0)
    ap.add_argument("--batch", type=int, default=400)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = np.asarray(official_axis().symbols)
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    coords = load_coords(args.coords)
    specs = []
    for spec in args.universe:
        name, _, rest = spec.partition("=")
        folder, basal_col = (rest.rsplit(":", 1) if rest.count(":") > 1 else (rest, name))
        specs.append((name, Path(folder), basal_col))
    cpm = np.vstack([basal[b].to_numpy(dtype=float) for _, _, b in specs])
    gstar = np.all(np.nan_to_num(cpm, nan=0.0) >= args.min_cpm, axis=0)
    print(f"G*: {int(gstar.sum())} genes with CPM >= {args.min_cpm} in every context", flush=True)
    tables = {}
    for name, folder, _ in specs:
        tab = per_target(Universe(name, folder), axis, gstar, coords, args.batch)
        tab.to_csv(args.out / f"per_target_{name}.csv")
        tables[name] = tab
        ok = tab["d"].notna() & tab["energy"].notna()
        print(f"{name}: {int(ok.sum())} targets; median depth {tab.loc[ok, 'd'].median():.3f}, "
              f"median energy {tab.loc[ok, 'energy'].median():.5f}", flush=True)
    rng = np.random.default_rng(20260927)
    pairs = []
    for a, b in itertools.combinations([s[0] for s in specs], 2):
        ta, tb = tables[a], tables[b]
        common = ta.index.intersection(tb.index)
        x = ta.loc[common]
        y = tb.loc[common]
        sel = (x["z_own"] <= -3) & (y["z_own"] <= -3) & (x["d"] > 0) & (y["d"] > 0) & \
              (x["energy"] > 0) & (y["energy"] > 0)
        lx = np.log(x.loc[sel, "d"].to_numpy() / y.loc[sel, "d"].to_numpy())
        le = np.log(x.loc[sel, "energy"].to_numpy() / y.loc[sel, "energy"].to_numpy())
        n = lx.size
        if n < 30:
            pairs.append({"a": a, "b": b, "targets": int(n)})
            continue
        slope = float(np.polyfit(lx, le, 1)[0])
        corr = float(np.corrcoef(lx, le)[0, 1])
        idx = rng.integers(0, n, size=(N_BOOT, n))
        bs = np.array([np.polyfit(lx[k], le[k], 1)[0] for k in idx])
        bc = np.array([np.corrcoef(lx[k], le[k])[0, 1] for k in idx])
        pairs.append({"a": a, "b": b, "targets": int(n), "slope": slope,
                      "slope_ci95": [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))],
                      "corr": corr, "corr_ci95": [float(np.quantile(bc, 0.025)), float(np.quantile(bc, 0.975))],
                      "median_log_depth_ratio": float(np.median(lx)), "median_log_energy_ratio": float(np.median(le))})
        print(f"{a} vs {b}: n={n}, slope {slope:.2f} ({pairs[-1]['slope_ci95'][0]:.2f}..{pairs[-1]['slope_ci95'][1]:.2f}), "
              f"corr {corr:.3f}", flush=True)
    pd.DataFrame(pairs).to_csv(args.out / "pairs.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "profondita_silenziamento_2026-09-27/depth_energy.py", "args": vars(args),
                   "gstar_genes": int(gstar.sum()), "pairs": pairs,
                   "claim_type": "exploratory association across public sources; not a VCC score"}, fh,
                  indent=1, default=str)


if __name__ == "__main__":
    main()
