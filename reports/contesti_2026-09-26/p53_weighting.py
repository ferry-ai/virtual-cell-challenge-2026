"""p53 status instead of whole-transcriptome similarity: do sources with the same p53 state transfer better?

H6 as whole-profile similarity failed on Mixscale (r1 of this folder). Nadig et al. (Nat Genet
2025, via the grok report in reports/trasferimento_appreso_2026-09-26/agenti/) found cross-line
transfer of essential-gene knockdowns high between lines that share p53 status and growth mode
(K562-Jurkat 0.74, HepG2-RPE1 0.75) and low across (K562-RPE1 0.40): an interpretation of the
authors, not a controlled test. Here: the p53 group of each context is read from its controls,
the mean expression percentile of 25 canonical p53 targets (basal_profiles.py output):
low = K562 (0.45), HEK293T (0.61); high = CD4 (0.75), HCT116 (0.71). For each held-out source,
predictor sources in its p53 group get weight m (1 = equal weights, 2, 4, and 'only' = the
other group dropped); t20 shape (shrunk x 1.576 + cis). PDS and reach proxies, paired bootstrap
over targets against equal weights. Effect-space proxies, not VCC scores.

    scripts/py.cmd reports/contesti_2026-09-26/p53_weighting.py --out reports/contesti_2026-09-26/r2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "reports" / "modulo_cis_2026-09-26"))
sys.path.insert(0, str(REPO / "reports" / "trasferimento_appreso_2026-09-26"))

from cis_bench import DATA, FAMILY, SEED, boot, pds_proxy, reach_proxy, stage100  # noqa: E402
from lct_bench2 import cd4_mix_se  # noqa: E402
from vcc2026.multisource import mix  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402

SOURCES = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]
P53_TARGETS = ["CDKN1A", "MDM2", "ZMAT3", "RPS27L", "TP53I3", "SESN1", "SESN2", "FDXR", "BAX", "TNFRSF10B", "GDF15",
               "PHLDA3", "AEN", "TRIAP1", "RRM2B", "DDB2", "XPC", "TIGAR", "BBC3", "FAS", "CCNG1", "POLH", "SPATA18",
               "EDA2R", "APOBEC3C", "TP53INP1"]
MULTS = (2.0, 4.0, "only")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--genes", type=Path, default=DATA / "raw/controls/gene_names.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--pairs", type=Path, default=REPO / "reports/cis_2026-09-17/k562_neighbour_pairs.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = pd.read_csv(args.genes)["gene_name"].astype(str).to_numpy()
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    col = {g: i for i, g in enumerate(axis)}
    panel_cols = np.array([col[g] for g in panel if g in col])
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    cpm = basal[["A", "B", "C"]].mean(axis=1).to_numpy()
    x = 0.05 * cpm
    w = (x / (1.0 + x)).astype(np.float32)
    gate = cpm >= 5.0
    score = {}
    for c in SOURCES + ["A", "B", "C"]:
        pct = np.log1p(basal[c]).rank(pct=True)
        score[c] = float(pct[[g for g in P53_TARGETS if np.isfinite(basal[c].get(g, np.nan))]].mean())
    cut = float(np.median([score[s] for s in SOURCES]))
    group = {c: ("high" if v > cut else "low") for c, v in score.items()}
    print(score, group, flush=True)
    cis_model = stage100.cis_prior(pd.read_csv(args.pairs), panel)
    coords = load_coordinates(args.coords)
    rng = np.random.default_rng(SEED)
    rows = []
    for held in SOURCES:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = stage100.load_table(args.cache, held, "raw")
        tidx = truth.index()
        tabs = [stage100.load_table(args.cache, s, "shrunk") for s in preds]
        base_t = [t for t in panel if t in tidx]
        eq, den = mix(tabs, base_t, weights={s: 1.0 for s in preds}, gamma=1.0, reliability_scale=100.0)
        ok = np.abs(eq).sum(axis=1) > 0
        targets = [t for t, o in zip(base_t, ok) if o]
        T = truth.raw[np.array([tidx[t] for t in targets])].astype(np.float32)
        if held == "cd4_mix":
            se = cd4_mix_se(args.cache, targets, axis.size)
        else:
            se = truth.se[np.array([tidx[t] for t in targets])]
        Z = T / se
        tcols = np.array([col.get(t, -1) for t in targets])
        cis = np.zeros((len(targets), axis.size), dtype=np.float32)
        stage100.add_cis(cis, np.zeros_like(cis, dtype=bool), targets, axis, cis_model, coords, 5000, 2.0)
        same = [s for s in preds if group[s] == group[held]]
        arms = {"equal": eq[ok] * 1.576 + cis}
        if same and len(same) < len(preds):
            for m in MULTS:
                if m == "only":
                    wts = {s: (1.0 if s in same else 0.0) for s in preds}
                else:
                    wts = {s: (m if s in same else 1.0) for s in preds}
                e, _ = mix(tabs, targets, weights=wts, gamma=1.0, reliability_scale=100.0)
                arms[f"p53match_{m}"] = e * 1.576 + cis
        res = {}
        for name, E in arms.items():
            res[name] = (pds_proxy(E, T, w, panel_cols), reach_proxy(E, T, Z, gate, tcols))
            row = {"held_out": held, "group": group[held], "same_group_sources": "+".join(same), "arm": name,
                   "targets": len(targets), "pds_proxy": float(res[name][0].mean()), "reach_proxy": float(np.nanmean(res[name][1]))}
            if name != "equal":
                for key, j in (("pds", 0), ("reach", 1)):
                    d, ci = boot(res[name][j] - res["equal"][j], rng)
                    row[f"{key}_minus_equal"], row[f"{key}_ci95"] = d, ci
            rows.append(row)
        print(held, "done", flush=True)
    s = pd.DataFrame(rows)
    s.to_csv(args.out / "summary.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "contesti_2026-09-26/p53_weighting.py", "p53_score": score, "group": group, "cut": cut,
                   "claim_type": "effect-space proxies; not VCC scores", "rows": rows}, fh, indent=1, default=float)
    pd.set_option("display.width", 220)
    print(s.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
