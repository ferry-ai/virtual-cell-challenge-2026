"""How much does VIPerturb-seq (Flex, K562) agree with itself? The noise ceiling for the Flex-vs-3' cosines of r1.

Two halves of the same screen (pools 0-3 and 4-7, each merged into one pool by half_pools.py and estimated by
kolf_effects.py exactly as the full screen) are compared per target, with bridge.py's cosine (shrunk effects, the
target's own gene and its 5 kb cis window left out), on ONE fixed set of targets: the strong targets of r1's pair
VIPerturb (full) vs Replogle 3' K562 (at least 30 genes with |z| >= 3 in both, r1/pair_viperturb_flex__k562_3p.csv).
Each half is also compared with Replogle 3' K562 on the same targets, so the half-vs-half and half-vs-3' cosines are
at the same depth. The split-half cosine is the self-agreement at half depth; the Spearman-Brown step 2r/(1+r) is
reported as an approximation of the full-depth self-agreement (it assumes two parallel halves, and a cosine is not
exactly a correlation). Exploratory, no decision rule.

    scripts/py.cmd reports/sorgenti/ponte_flex_2026-09-28/split_half.py --out reports/sorgenti/ponte_flex_2026-09-28/r2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "trasferimento" / "atlante_2026-09-26"))
sys.path.insert(0, str(HERE))

from atlas_bench import Universe  # noqa: E402
from bridge import NEAR_BP, rows  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402

DATA = Path("C:/Users/ferra/vcc2026-data")
UNIVERSES = {
    "viperturb_halfa": ("viperturb", DATA / "processed/universe_viperturb_2026-09-28_halfa"),
    "viperturb_halfb": ("viperturb", DATA / "processed/universe_viperturb_2026-09-28_halfb"),
    "viperturb_full": ("viperturb", DATA / "processed/universe_viperturb_2026-09-27_p1"),
    "k562_3p": ("k562", DATA / "processed/universe_k562_2026-09-26"),
    "k562ess_3p": ("k562ess", DATA / "processed/universe_k562ess_2026-09-26"),
}
PAIRS = [("viperturb_halfa", "viperturb_halfb"), ("viperturb_halfa", "k562_3p"), ("viperturb_halfb", "k562_3p"),
         ("viperturb_full", "k562_3p"), ("k562ess_3p", "k562_3p")]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--r1", type=Path, default=HERE / "r1" / "pair_viperturb_flex__k562_3p.csv")
    ap.add_argument("--min-sig", type=int, default=30)
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    r1 = pd.read_csv(args.r1)
    fixed = sorted(r1.loc[(r1.sig_a >= args.min_sig) & (r1.sig_b >= args.min_sig), "target"].astype(str))
    axis = np.asarray(official_axis().symbols)
    col = {g: i for i, g in enumerate(axis)}
    coords = pd.read_csv(args.coords, sep="\t").drop_duplicates("symbol").set_index("symbol")
    chrom = coords.reindex(axis)["chrom"].astype(str).to_numpy()
    tss = coords.reindex(axis)["tss"].to_numpy(dtype=float)
    unis = {k: Universe(n, p) for k, (n, p) in UNIVERSES.items()}
    tables = {k: rows(u, [t for t in fixed if t in set(u.targets)]) for k, u in unis.items()}
    per = {"target": fixed}
    summary = []
    for a, b in PAIRS:
        cos = []
        for t in fixed:
            if t not in tables[a] or t not in tables[b]:
                cos.append(np.nan)
                continue
            sa, sb = tables[a][t][0], tables[b][t][0]
            keep = np.isfinite(sa) & np.isfinite(sb)
            if t in col:
                keep[col[t]] = False
            if t in coords.index:
                keep &= ~((chrom == str(coords.at[t, "chrom"])) & (np.abs(tss - float(coords.at[t, "tss"])) <= NEAR_BP))
            if keep.sum() < 100:
                cos.append(np.nan)
                continue
            va, vb = sa[keep], sb[keep]
            na, nb = np.linalg.norm(va), np.linalg.norm(vb)
            cos.append(float(va @ vb / (na * nb)) if na > 0 and nb > 0 else np.nan)
        c = np.asarray(cos, dtype=float)
        per[f"{a}__{b}"] = c
        ok = np.isfinite(c)
        row = {"a": a, "b": b, "targets": int(ok.sum()), "median": float(np.median(c[ok])) if ok.any() else None,
               "q25": float(np.quantile(c[ok], .25)) if ok.any() else None,
               "q75": float(np.quantile(c[ok], .75)) if ok.any() else None, "mean": float(c[ok].mean()) if ok.any() else None}
        summary.append(row)
        print(json.dumps(row), flush=True)
    pd.DataFrame(per).to_csv(args.out / "per_target.csv", index=False)
    half = next(r for r in summary if (r["a"], r["b"]) == ("viperturb_halfa", "viperturb_halfb"))
    sb = None
    if half["median"] is not None and half["median"] > -1:
        r = half["median"]
        sb = 2 * r / (1 + r)
    with (args.out / "summary.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "ponte_flex_2026-09-28/split_half.py", "fixed_targets": len(fixed), "min_sig": args.min_sig,
                   "pairs": summary, "spearman_brown_full_depth_from_median_split_half": sb,
                   "claim_type": "exploratory comparison of public screens; not a VCC score"}, fh, indent=1)
    print(f"{len(fixed)} fixed strong targets; split-half median {half['median']}; Spearman-Brown {sb}", flush=True)


if __name__ == "__main__":
    main()
