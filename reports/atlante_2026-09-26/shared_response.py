"""What two lines share: per gene and per knockdown, over every target both universes measured.

For each pair of universes of different families (e.g. K562 and CD4), on the targets both measured
outside the 300 of the panel, effects centred per source over those targets (as gamma 1 does):
* per gene: the cross-line covariance of the response over targets (the shared variance, sigma2 of
  the hierarchical model), each line's signal variance (mean square minus mean SE^2, CD4's SE
  variance times --cd4-se-factor), and their disattenuated correlation
  rho = cov / sqrt(signal_i signal_j): how much of a gene's knockdown-to-knockdown variation the two
  lines have in common, sampling noise removed;
* per target: the cosine of the two lines' profiles on expressed genes (log1p weights of A/B/C, the
  target's own gene out), each profile's energy and cells;
* summaries by simple gene classes (symbol families and a few textbook response sets) and target
  classes (complexes by symbol prefix). The classes are symbol lists, not an enrichment test.
Descriptive, effect space, public sources only; not VCC scores.

    scripts/py.cmd reports/atlante_2026-09-26/shared_response.py --out reports/atlante_2026-09-26/condivisione_r1 \
        --universe k562=<dir> --universe cd4_mix=<dir>
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
sys.path.insert(0, str(HERE))

from atlas_bench import BLOCK, DATA, Universe, family  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402

GENE_SETS = {  # textbook response sets, by symbol; interpretation aids only
    "p53 targets": ["CDKN1A", "MDM2", "BAX", "GDF15", "TP53I3", "SESN1", "SESN2", "FAS", "RRM2B", "ZMAT3",
                    "TNFRSF10B", "BBC3", "PMAIP1", "TP53INP1", "DDB2", "XPC", "AEN", "PLK3", "BTG2", "TRIAP1"],
    "cholesterol synthesis": ["HMGCS1", "HMGCR", "LDLR", "INSIG1", "SQLE", "FDFT1", "IDI1", "MVD", "MVK", "LSS",
                              "CYP51A1", "DHCR7", "DHCR24", "SC5D", "MSMO1", "NSDHL", "HSD17B7", "FDPS", "STARD4", "SREBF2"],
    "unfolded protein response": ["HSPA5", "DDIT3", "ATF4", "XBP1", "HERPUD1", "SEL1L", "DNAJB9", "PDIA4", "HYOU1",
                                  "CALR", "SDF2L1", "MANF", "CRELD2", "ASNS", "TRIB3", "CHAC1", "SESN2", "VEGFA"],
    "heat shock": ["HSPA1A", "HSPA1B", "DNAJB1", "HSPH1", "HSPA8", "HSP90AA1", "HSPD1", "HSPE1", "BAG3", "HSPB1"],
    "cell cycle": ["MKI67", "TOP2A", "CCNB1", "CDK1", "CCNA2", "CDC20", "PLK1", "AURKA", "AURKB", "BUB1", "E2F1",
                   "MCM2", "MCM3", "MCM4", "MCM5", "MCM6", "MCM7", "PCNA", "TYMS", "RRM2", "CCNE1", "CCNE2"],
    "interferon": ["IFIT1", "IFIT2", "IFIT3", "IFI6", "IFI27", "ISG15", "MX1", "MX2", "OAS1", "OAS2", "OAS3",
                   "IFI44", "IFI44L", "RSAD2", "STAT1", "IRF7", "BST2", "XAF1"],
}
GENE_PREFIXES = {"ribosomal proteins": ("RPL", "RPS"), "mitochondrial ribosome": ("MRPL", "MRPS"),
                 "mitochondrial genome": ("MT-",), "histones": ("H1-", "H2AC", "H2BC", "H3C", "H4C", "H2AZ", "H3-3"),
                 "HLA": ("HLA-",)}
TARGET_PREFIXES = {"ribosome (RPL/RPS)": ("RPL", "RPS"), "mito ribosome": ("MRPL", "MRPS"),
                   "proteasome (PSM)": ("PSM",), "RNA pol II (POLR2)": ("POLR2",), "RNA pol I/III": ("POLR1", "POLR3"),
                   "mediator (MED)": ("MED",), "spliceosome (SF3/SNRP/PRPF)": ("SF3", "SNRP", "PRPF", "LSM"),
                   "translation initiation (EIF)": ("EIF",), "chaperonin (CCT)": ("CCT",), "nucleoporins (NUP)": ("NUP",),
                   "TFIID (TAF)": ("TAF",), "exosome (EXOSC)": ("EXOSC",), "cohesin/condensin (SMC)": ("SMC",),
                   "respiratory chain (NDUF/COX/UQCR/ATP5)": ("NDUF", "COX", "UQCR", "ATP5", "SDH")}


def gene_class(g: str) -> str:
    for name, genes in GENE_SETS.items():
        if g in genes:
            return name
    for name, pre in GENE_PREFIXES.items():
        if g.startswith(pre):
            return name
    return "other"


def target_class(t: str) -> str:
    for name, pre in TARGET_PREFIXES.items():
        if t.startswith(pre):
            return name
    return "other"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", action="append", required=True, metavar="NAME=DIR")
    ap.add_argument("--cd4-se-factor", type=float, default=2.0)
    ap.add_argument("--pairs", nargs="*", default=None, metavar="A:B",
                    help="explicit pairs of universe names (also of the same family, e.g. two CD4 conditions); "
                         "default: every pair of different families")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = np.asarray(official_axis().symbols)
    G = axis.size
    col = {g: i for i, g in enumerate(axis)}
    panel = set(pd.read_csv(args.panel).iloc[:, 0].astype(str))
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    cpm_abc = basal[["A", "B", "C"]].mean(axis=1).to_numpy()
    xa = 0.05 * cpm_abc
    w = (xa / (1.0 + xa))
    gate = cpm_abc >= 5.0
    unis = {}
    for spec in args.universe:
        name, _, folder = spec.partition("=")
        unis[name] = Universe(name, Path(folder))
    summary = {"stage": "atlante_2026-09-26/shared_response.py", "claim_type": "descriptive, effect space, public "
               "sources; classes are symbol lists, not enrichment tests", "pairs": []}
    gcls = np.array([gene_class(g) for g in axis])
    pairs = ([tuple(x.split(":")) for x in args.pairs] if args.pairs
             else [(a, b) for a, b in itertools.combinations(unis, 2) if family(a) != family(b)])
    for a, b in pairs:
        shared = sorted((unis[a].targets & unis[b].targets) - panel)
        ka = args.cd4_se_factor if family(a) == "cd4" else 1.0
        kb = args.cd4_se_factor if family(b) == "cd4" else 1.0
        print(f"{a} x {b}: {len(shared)} shared targets outside the panel", flush=True)

        def block(part):
            # a target listed in an index can lack a row in one table (a CD4 condition): keep the common ones
            ta, tb = unis[a].table(part), unis[b].table(part)
            common = [t for t in ta.targets if t in set(tb.targets)]
            if common != ta.targets:
                ta = unis[a].table(common)
            if common != tb.targets:
                tb = unis[b].table(common)
            return ta, tb

        tot = {k: np.zeros(G) for k in ("a", "b")}
        cnt = {k: np.zeros(G) for k in ("a", "b")}
        for b0 in range(0, len(shared), BLOCK):
            ta, tb = block(shared[b0:b0 + BLOCK])
            for k, tab in (("a", ta), ("b", tb)):
                tot[k] += np.nansum(tab.raw, axis=0, dtype=np.float64)
                cnt[k] += np.isfinite(tab.raw).sum(axis=0)
        ca = np.divide(tot["a"], cnt["a"], out=np.zeros(G), where=cnt["a"] > 0)
        cb = np.divide(tot["b"], cnt["b"], out=np.zeros(G), where=cnt["b"] > 0)
        acc = {k: np.zeros(G) for k in ("ab", "n_ab", "aa", "se_a", "n_a", "bb", "se_b", "n_b")}
        per_target = []
        for b0 in range(0, len(shared), BLOCK):
            ta, tb = block(shared[b0:b0 + BLOCK])
            part = ta.targets
            ya, yb = ta.raw.astype(np.float64) - ca[None, :], tb.raw.astype(np.float64) - cb[None, :]
            sa, sb = ta.se.astype(np.float64), tb.se.astype(np.float64)
            ok = np.isfinite(ya) & np.isfinite(yb)
            acc["ab"] += np.where(ok, ya * yb, 0.0).sum(axis=0)
            acc["n_ab"] += ok.sum(axis=0)
            for y, s, k, key in ((ya, sa, ka, "a"), (yb, sb, kb, "b")):
                o = np.isfinite(y) & np.isfinite(s)
                acc[key * 2] += np.where(o, y * y, 0.0).sum(axis=0)
                acc[f"se_{key}"] += np.where(o, k * s * s, 0.0).sum(axis=0)
                acc[f"n_{key}"] += o.sum(axis=0)
            for i, t in enumerate(part):
                m = ok[i] & gate
                j = col.get(t)
                if j is not None:
                    m[j] = False
                u, v = ya[i, m] * w[m], yb[i, m] * w[m]
                nu, nv = np.linalg.norm(u), np.linalg.norm(v)
                per_target.append({"target": t, "class": target_class(t), "cosine": float(u @ v / max(nu * nv, 1e-12)),
                                   f"energy_{a}": float(nu ** 2), f"energy_{b}": float(nv ** 2),
                                   f"cells_{a}": float(ta.n_cells[i]), f"cells_{b}": float(tb.n_cells[i])})
        cov = np.divide(acc["ab"], acc["n_ab"], out=np.full(G, np.nan), where=acc["n_ab"] > 0)
        sig_a = np.divide(acc["aa"] - acc["se_a"], acc["n_a"], out=np.full(G, np.nan), where=acc["n_a"] > 0)
        sig_b = np.divide(acc["bb"] - acc["se_b"], acc["n_b"], out=np.full(G, np.nan), where=acc["n_b"] > 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            rho = cov / np.sqrt(np.clip(sig_a, 0, None) * np.clip(sig_b, 0, None))
        genes = pd.DataFrame({"gene": axis, "class": gcls, "expressed_abc": gate, "cpm_abc": cpm_abc,
                              "targets": acc["n_ab"], "cov": cov, f"signal_{a}": sig_a, f"signal_{b}": sig_b,
                              "rho": rho})
        genes.to_csv(args.out / f"per_gene_{a}_{b}.csv", index=False, float_format="%.6g")
        tdf = pd.DataFrame(per_target)
        tdf.to_csv(args.out / f"per_target_{a}_{b}.csv", index=False, float_format="%.6g")
        ex = genes[genes["expressed_abc"] & np.isfinite(genes["rho"]) & (genes[f"signal_{a}"] > 0)
                   & (genes[f"signal_{b}"] > 0)]
        by_gene = ex.groupby("class").agg(genes=("gene", "size"), rho_median=("rho", "median"),
                                          cov_median=("cov", "median")).reset_index()
        by_target = tdf.groupby("class").agg(targets=("target", "size"), cosine_median=("cosine", "median"),
                                             cosine_q75=("cosine", lambda s: float(np.quantile(s, 0.75)))).reset_index()
        strong = ex[(ex[f"signal_{a}"] > ex[f"signal_{a}"].median()) & (ex[f"signal_{b}"] > ex[f"signal_{b}"].median())]
        pair = {"pair": [a, b], "shared_targets": len(shared), "targets_with_rows_in_both": int(len(tdf)),
                "cd4_se_factor": args.cd4_se_factor,
                "genes_expressed_with_signal": int(len(ex)),
                "rho_quantiles_expressed": [float(q) for q in np.quantile(ex["rho"].clip(-2, 2), [0.1, 0.25, 0.5, 0.75, 0.9])],
                "rho_by_gene_class": by_gene.to_dict(orient="records"),
                "top_shared_genes_strong_signal": strong.nlargest(40, "cov")[["gene", "class", "rho", "cov"]].to_dict(orient="records"),
                "cosine_quantiles": [float(q) for q in np.quantile(tdf["cosine"], [0.1, 0.25, 0.5, 0.75, 0.9])],
                "cosine_by_target_class": by_target.to_dict(orient="records"),
                "top_transferring_targets": tdf.nlargest(40, "cosine")[["target", "class", "cosine"]].to_dict(orient="records"),
                "cosine_vs_energy_spearman": float(pd.Series(tdf["cosine"]).corr(
                    np.sqrt(tdf[f"energy_{a}"] * tdf[f"energy_{b}"]), method="spearman"))}
        summary["pairs"].append(pair)
        print(json.dumps({k: v for k, v in pair.items() if k in ("pair", "shared_targets", "rho_quantiles_expressed",
                                                                  "cosine_quantiles", "cosine_vs_energy_spearman")}), flush=True)
        print(by_gene.round(3).to_string(index=False), flush=True)
        print(by_target.round(3).to_string(index=False), flush=True)
    with (args.out / "summary.json").open("x", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, default=float)


if __name__ == "__main__":
    main()
