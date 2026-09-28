"""The same K562 knockdowns read with 10x Flex (VIPerturb-seq) and with 3' (Replogle 2022): how much survives.

The VCC contexts are 10x Flex; every perturbation source of the project is 3', except VIPerturb-seq (Bradu et al.
2026), a genome-wide CRISPRi screen in K562 read with Flex. For pairs of universes on their shared targets, per
target the cosine of the shrunk effects on the genes both measure (the target's own gene and genes within 5 kb of
its TSS left out), on all shared targets and on the strong ones (at least --min-sig genes with |z| >= 3 in both).
Pairs: Flex K562 against 3' K562 (the bridge), two 3' K562 experiments of the same lab (genome-wide against the
essential screen: the same-line, same-chemistry reference), and 3' K562 against 3' HCT116 (another line, another
lab). Also per gene, over the strong shared targets, the least-squares slope of Flex on 3' (how a gene's response
scales between the chemistries), summarised. Exploratory, no decision rule.

    scripts/py.cmd reports/sorgenti/ponte_flex_2026-09-28/bridge.py --out reports/sorgenti/ponte_flex_2026-09-28/r1
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

from atlas_bench import Universe  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402

DATA = Path("C:/Users/ferra/vcc2026-data")
NEAR_BP = 5000
UNIVERSES = {
    "viperturb_flex": DATA / "processed/universe_viperturb_2026-09-27_p1",
    "k562_3p": DATA / "processed/universe_k562_2026-09-26",
    "k562ess_3p": DATA / "processed/universe_k562ess_2026-09-26",
    "hct116_3p": DATA / "processed/universe_orion_hct116_2026-09-27_me1",
}
NAMES = {"viperturb_flex": "viperturb", "k562_3p": "k562", "k562ess_3p": "k562ess", "hct116_3p": "orion_hct116"}
PAIRS = [("viperturb_flex", "k562_3p"), ("viperturb_flex", "k562ess_3p"), ("k562ess_3p", "k562_3p"),
         ("hct116_3p", "k562_3p")]


def rows(uni: Universe, targets: list[str]):
    tab = uni.table(targets)
    ix = tab.index()
    return {t: (tab.shrunk[ix[t]].astype(np.float64), tab.raw[ix[t]].astype(np.float64),
                tab.se[ix[t]].astype(np.float64)) for t in targets if t in ix}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--min-sig", type=int, default=30)
    ap.add_argument("--batch", type=int, default=400)
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = np.asarray(official_axis().symbols)
    col = {g: i for i, g in enumerate(axis)}
    coords = pd.read_csv(args.coords, sep="\t").drop_duplicates("symbol").set_index("symbol")
    chrom = coords.reindex(axis)["chrom"].astype(str).to_numpy()
    tss = coords.reindex(axis)["tss"].to_numpy(dtype=float)
    unis = {k: Universe(NAMES[k], v) for k, v in UNIVERSES.items()}
    summary, gene_slopes = [], {}
    for a, b in PAIRS:
        shared = sorted(set(unis[a].targets) & set(unis[b].targets))
        recs, xs, ys = [], [], []
        for start in range(0, len(shared), args.batch):
            part = shared[start:start + args.batch]
            ra, rb = rows(unis[a], part), rows(unis[b], part)
            for t in part:
                if t not in ra or t not in rb:
                    continue
                sa, xa, ea = ra[t]
                sb, xb, eb = rb[t]
                keep = np.isfinite(sa) & np.isfinite(sb)
                if t in col:
                    keep[col[t]] = False
                if t in coords.index:
                    keep &= ~((chrom == str(coords.at[t, "chrom"])) & (np.abs(tss - float(coords.at[t, "tss"])) <= NEAR_BP))
                if keep.sum() < 100:
                    continue
                with np.errstate(divide="ignore", invalid="ignore"):
                    sig_a = int((np.abs(xa[keep] / ea[keep]) >= 3).sum())
                    sig_b = int((np.abs(xb[keep] / eb[keep]) >= 3).sum())
                va, vb = sa[keep], sb[keep]
                na, nb = np.linalg.norm(va), np.linalg.norm(vb)
                cos = float(va @ vb / (na * nb)) if na > 0 and nb > 0 else np.nan
                recs.append({"target": t, "cosine": cos, "sig_a": sig_a, "sig_b": sig_b, "genes": int(keep.sum()),
                             "energy_ratio_a_over_b": float(na ** 2 / nb ** 2) if nb > 0 else np.nan})
                if (a, b) == ("viperturb_flex", "k562_3p") and min(sig_a, sig_b) >= args.min_sig:
                    xs.append(np.where(keep, sb, np.nan))
                    ys.append(np.where(keep, sa, np.nan))
        df = pd.DataFrame(recs)
        df.to_csv(args.out / f"pair_{a}__{b}.csv", index=False)
        strong = df[(df.sig_a >= args.min_sig) & (df.sig_b >= args.min_sig)]
        row = {"a": a, "b": b, "shared_targets": len(df),
               "cosine_median": float(df.cosine.median()), "cosine_q25": float(df.cosine.quantile(.25)),
               "cosine_q75": float(df.cosine.quantile(.75)), "strong_targets": len(strong),
               "strong_cosine_median": float(strong.cosine.median()) if len(strong) else None,
               "strong_cosine_q25": float(strong.cosine.quantile(.25)) if len(strong) else None,
               "strong_cosine_q75": float(strong.cosine.quantile(.75)) if len(strong) else None,
               "energy_ratio_median": float(df.energy_ratio_a_over_b.median())}
        summary.append(row)
        print(json.dumps(row), flush=True)
        if xs:
            X, Y = np.vstack(xs), np.vstack(ys)
            ok = np.isfinite(X) & np.isfinite(Y)
            num = np.nansum(np.where(ok, X * Y, 0.0), axis=0)
            den = np.nansum(np.where(ok, X * X, 0.0), axis=0)
            n = ok.sum(axis=0)
            with np.errstate(divide="ignore", invalid="ignore"):
                slope = np.where((n >= 20) & (den > 0), num / den, np.nan)
            gene_slopes = pd.DataFrame({"gene": axis, "slope_flex_on_3p": slope, "targets": n})
            gene_slopes.to_csv(args.out / "gene_slopes_flex_on_3p.csv", index=False)
            s = gene_slopes.slope_flex_on_3p.dropna()
            print(f"per-gene slope Flex on 3' over {X.shape[0]} strong targets: {s.size} genes, median {s.median():.3f}, "
                  f"q10 {s.quantile(.1):.3f}, q90 {s.quantile(.9):.3f}", flush=True)
    with (args.out / "summary.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "ponte_flex_2026-09-28/bridge.py", "min_sig": args.min_sig, "pairs": summary,
                   "claim_type": "exploratory comparison of public screens; not a VCC score"}, fh, indent=1)


if __name__ == "__main__":
    main()
