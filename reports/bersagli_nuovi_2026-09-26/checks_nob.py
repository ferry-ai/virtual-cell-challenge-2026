"""r3: the STRING + cis comparison of checks.py (r2) without the common response b in any arm.

r2 added b, the mean K562 response over training targets, to every arm; a vector shared by all
targets lowers the discrimination the PDS proxy measures (production removes it with gamma 1),
and r1 had compared cis WITHOUT b against string arms WITH b. Here no arm has b. The in-sample
check is repeated unchanged.

Original purpose of checks.py: is the linear model's null a bug, and can STRING help cis?

1. In-sample sanity of the Ahlmann-Eltze linear model: fitted on the non-panel K562 targets as
   in r1, it predicts 272 of its OWN training targets (seeded draw); PDS proxy against their
   K562 effects. A model that cannot rank the targets it was fitted on has a bug; one that can
   but fails on held-out targets simply does not generalise.
2. STRING scaled before adding the cis head: lambda x string700 + cis, lambda = 0.1, 0.25, 0.5,
   on the r1 held-out sources (the sum in r1 was lambda = 1 and lost to cis alone out of K562).

    scripts/py.cmd reports/bersagli_nuovi_2026-09-26/checks.py \
        --universe C:/Users/ferra/vcc2026-data/processed/universe_k562_2026-09-26 --out reports/bersagli_nuovi_2026-09-26/r3
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

from linear_new_targets import (DATA, REPO, SEED, boot, fit_linear, load_universe,  # noqa: E402
                                pds_proxy, stage100, top_basis)
from vcc2026.predictor_sc import load_coordinates  # noqa: E402

LAMBDAS = (0.1, 0.25, 0.5, 1.0, 2.0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", type=Path, required=True)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "interim/basal_cpm_by_context.csv")
    ap.add_argument("--genes", type=Path, default=DATA / "raw/controls/gene_names.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--pairs", type=Path, default=REPO / "reports/cis_2026-09-17/k562_neighbour_pairs.csv")
    ap.add_argument("--string-links", type=Path, default=DATA / "external/annotation/string_physical_links.gz")
    ap.add_argument("--string-info", type=Path, default=DATA / "external/annotation/string_protein_info.gz")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(SEED)
    axis = pd.read_csv(args.genes)["gene_name"].astype(str).to_numpy()
    panel_list = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    panel = set(panel_list)
    col = {g: i for i, g in enumerate(axis)}
    panel_cols = np.array([col[g] for g in panel_list if g in col])
    cpm = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)[["A", "B", "C"]].mean(axis=1).to_numpy()
    x = 0.05 * cpm
    w = (x / (1.0 + x)).astype(np.float32)

    X, train_t, genes_used, b, _ = load_universe(args.universe, panel)
    gpos = {int(g): i for i, g in enumerate(genes_used)}
    G = top_basis(X, 50, rng)
    W, _ = fit_linear(X, train_t, col, gpos, G, 10.0)
    # 1. in-sample: 272 training targets whose gene is on the modelled axis
    usable = [j for j, t in enumerate(train_t) if col.get(t, -1) in gpos]
    pick = sorted(rng.choice(usable, size=272, replace=False).tolist())
    truth = np.full((len(pick), axis.size), np.nan, dtype=np.float32)
    predm = np.zeros((len(pick), axis.size), dtype=np.float32)
    for i, j in enumerate(pick):
        truth[i, genes_used] = X[:, j] + b
        predm[i, genes_used] = G @ (W @ G[gpos[col[train_t[j]]]]) + b
    ins = pds_proxy(predm, truth, w, panel_cols)
    proj = np.zeros_like(predm)
    for i, j in enumerate(pick):
        proj[i, genes_used] = G @ (G.T @ X[:, j]) + b      # the best any rank-50 model could do
    ceil = pds_proxy(proj, truth, w, panel_cols)
    checks = {"in_sample_pds_linear_k50_r10": float(np.mean(ins)), "in_sample_pds_rank50_projection": float(np.mean(ceil))}
    print(checks, flush=True)

    # 2. lambda x string700 + cis on the held-out sources of r1
    info = pd.read_csv(args.string_info, sep="\t", usecols=[0, 1])
    sym = dict(zip(info.iloc[:, 0], info.iloc[:, 1]))
    links = pd.read_csv(args.string_links, sep=" ")
    links = links[links["combined_score"] >= 700]
    links["a"] = links["protein1"].map(sym)
    links["b"] = links["protein2"].map(sym)
    tcol = {t: j for j, t in enumerate(train_t)}
    sub = links[links["a"].isin(panel) & links["b"].isin(tcol)]
    groups = sub.groupby("a")["b"].apply(lambda v: sorted(set(v)))
    string = np.zeros((len(panel_list), axis.size), dtype=np.float32)   # centred: b is added below
    for i, t in enumerate(panel_list):
        if t in groups.index:
            string[i, genes_used] = X[:, [tcol[g] for g in groups[t]]].mean(axis=1)
    del X, links
    cis_model = stage100.cis_prior(pd.read_csv(args.pairs), panel_list)
    coords = load_coordinates(args.coords)
    prow = {t: i for i, t in enumerate(panel_list)}
    b_full = np.zeros(axis.size, dtype=np.float32)
    b_full[genes_used] = b
    rows = []
    brng = np.random.default_rng(SEED)
    for held in ("k562", "cd4_mix", "orion_hct116", "orion_hek293t"):
        tab = stage100.load_table(args.cache, held, "raw")
        tidx = tab.index()
        targets = [t for t in panel_list if t in tidx]
        T = tab.raw[np.array([tidx[t] for t in targets])].astype(np.float32)
        cis = np.zeros((len(targets), axis.size), dtype=np.float32)
        stage100.add_cis(cis, np.zeros_like(cis, dtype=bool), targets, axis, cis_model, coords, 5000, 2.0)
        S = string[np.array([prow[t] for t in targets])]
        ref = pds_proxy(cis, T, w, panel_cols)
        rows.append({"held_out": held, "arm": "cis", "targets": len(targets), "pds_proxy": float(np.mean(ref)),
                     "minus_cis": 0.0, "ci95": [0.0, 0.0]})
        for lam in LAMBDAS:
            v = pds_proxy(lam * S + cis, T, w, panel_cols)
            d, ci = boot(v - ref, brng)
            rows.append({"held_out": held, "arm": f"{lam}*string700+cis", "targets": len(targets),
                         "pds_proxy": float(np.mean(v)), "minus_cis": d, "ci95": ci})
        print(held, "done", flush=True)
    s = pd.DataFrame(rows)
    s.to_csv(args.out / "string_lambda.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "bersagli_nuovi_2026-09-26/checks_nob.py", "claim_type": "effect-space proxies; not VCC scores",
                   "checks": checks, "rows": rows}, f, indent=1)
    pd.set_option("display.width", 200)
    print(s.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
