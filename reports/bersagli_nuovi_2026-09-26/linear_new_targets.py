"""New targets: how well can a target no source measured be predicted, and by what?

The final set brings 300 new targets. For a target that some source measured, the pipeline
transfers its measured effect; for one that none measured it has nothing but the cis head. This
measures, on the 300 panel targets treated as NEW (every one of their perturbation outcomes
removed from training), the linear baseline of Ahlmann-Eltze et al. (Nature Methods 2025):

    Y (genes x training targets, K562 genome-wide effects, centred per gene) ~ G W P^T
    G = top-k left singular vectors of Y (gene embeddings, k = 25, 50, 100)
    P_t = G[t], the embedding of the target's own gene as a readout (how gene t moves when
    OTHER genes are knocked down), so a never-perturbed target still has one
    W by ridge (penalty 1, 10); prediction for a new target: G W G[t]^T + b.

Training uses the K562 universe of reports/universo_2026-09-26 minus the 300 panel targets.
Evaluation (effect-space proxies of cis_bench.py; not VCC scores):
  regime T: truth = K562's own measurement of the panel targets (same context, new targets);
  regime J: truth = CD4, HCT116, HEK293T (new context and new targets).
Arms: common (b alone), cis (stage 100's prior, 2 x within 5 kb, panel targets excluded),
linear_k*, linear_k*+cis; string700 / string400, "guilt by association": the mean K562 effect of
the target's STRING physical partners (combined score >= 700 or 400) among the training targets,
b where it has none, and string700+cis; and, as the ceiling that new targets do not have,
transfer (the target's own K562 effect, shrunk, gamma 1).

    scripts/py.cmd reports/bersagli_nuovi_2026-09-26/linear_new_targets.py \
        --universe C:/Users/ferra/vcc2026-data/processed/universe_k562_2026-09-26 --out reports/bersagli_nuovi_2026-09-26/r1
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

from cis_bench import (DATA, SEED, boot, fidelity_proxy, pds_proxy, reach_proxy,  # noqa: E402
                       stage100, truth_z)
from vcc2026.multisource import AxisTable, mix  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402

HELD = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]
KS = (25, 50, 100)
RIDGES = (1.0, 10.0)


def load_universe(folder: Path, panel: set):
    """X (K562-measured genes x non-panel targets, float32, centred per gene), their names, the
    gene columns, the per-gene mean, and the panel targets' K562 table."""
    idx = pd.read_csv(folder / "index.csv")
    chunks = sorted(idx["chunk"].unique())
    first = np.load(folder / chunks[0], allow_pickle=False)
    genes_used = np.flatnonzero(np.isfinite(first["raw"]).mean(axis=0) > 0.5)
    del first
    n_train = int((~idx["target"].astype(str).isin(panel)).sum())
    X = np.zeros((genes_used.size, n_train), dtype=np.float32)
    train_t, panel_parts, j = [], [], 0
    for chunk in chunks:
        z = np.load(folder / chunk, allow_pickle=False)
        t = z["targets"].astype(str)
        is_panel = np.isin(t, list(panel))
        block = np.nan_to_num(z["shrunk"][~is_panel][:, genes_used]).T
        X[:, j:j + block.shape[1]] = block
        j += block.shape[1]
        train_t += t[~is_panel].tolist()
        if is_panel.any():
            panel_parts.append((t[is_panel].tolist(), z["shrunk"][is_panel], z["raw"][is_panel], z["se"][is_panel],
                                z["n_cells"][is_panel]))
        del z, block
    X = X[:, :j]
    b = X.mean(axis=1)
    X -= b[:, None]
    pt = [x for part in panel_parts for x in part[0]]
    tab = AxisTable("k562", pt, np.vstack([q[1] for q in panel_parts]), np.vstack([q[2] for q in panel_parts]),
                    np.vstack([q[3] for q in panel_parts]), np.concatenate([q[4] for q in panel_parts]), {})
    return X, train_t, genes_used, b, tab


def top_basis(X: np.ndarray, k: int, rng) -> np.ndarray:
    """Top-k left singular vectors of X (genes x targets), randomized, 3 power iterations."""
    omega = rng.standard_normal((X.shape[1], k + 20)).astype(np.float32)
    Q, _ = np.linalg.qr(X @ omega)
    for _ in range(3):
        Q, _ = np.linalg.qr(X @ (X.T @ Q))
    U, _, _ = np.linalg.svd(Q.T @ X, full_matrices=False)
    return (Q @ U[:, :k]).astype(np.float32)


def fit_linear(X: np.ndarray, train_t: list[str], col: dict, gpos: dict, G: np.ndarray, ridge: float):
    """W (k x k) of the Ahlmann-Eltze model on the nested basis G; targets off the axis are skipped."""
    usable = [j for j, t in enumerate(train_t) if col.get(t, -1) in gpos]
    P = G[[gpos[col[train_t[j]]] for j in usable]]
    GtX = (G.T @ X)[:, usable]          # k x targets, without copying X
    k = G.shape[1]
    W = GtX @ P @ np.linalg.inv(P.T @ P + ridge * np.eye(k, dtype=np.float32))
    return W, len(usable)


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
    keep = np.ones(axis.size, dtype=bool)
    keep[panel_cols] = False
    cpm = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)[["A", "B", "C"]].mean(axis=1).to_numpy()
    x = 0.05 * cpm
    w = (x / (1.0 + x)).astype(np.float32)
    gate = cpm >= 5.0

    X, train_t, genes_used, b, k562_panel = load_universe(args.universe, panel)
    print(f"training targets {len(train_t)}, genes modelled {genes_used.size}", flush=True)
    gpos = {int(g): i for i, g in enumerate(genes_used)}
    G_max = top_basis(X, max(KS), rng)
    # the models, fitted once on K562 non-panel targets (no panel outcome anywhere)
    models = {}
    for k in KS:
        G = G_max[:, :k]
        for r in RIDGES:
            W, n_fit = fit_linear(X, train_t, col, gpos, G, r)
            models[f"linear_k{k}_r{int(r)}"] = (G, W, n_fit)
    b_full = np.zeros(axis.size, dtype=np.float32)
    b_full[genes_used] = b
    # predictions for every panel target, computed once (they do not depend on the held-out source)
    pred = {}
    for name, (G, W, n_fit) in models.items():
        P = np.broadcast_to(b_full, (len(panel_list), axis.size)).copy()
        for i, t in enumerate(panel_list):
            c = col.get(t, -1)
            if c in gpos:
                P[i, genes_used] = G @ (W @ G[gpos[c]]) + b
        pred[name] = P
    info = pd.read_csv(args.string_info, sep="\t", usecols=[0, 1])
    sym = dict(zip(info.iloc[:, 0], info.iloc[:, 1]))
    links = pd.read_csv(args.string_links, sep=" ")
    links = links[links["combined_score"] >= 400]
    links["a"] = links["protein1"].map(sym)
    links["b"] = links["protein2"].map(sym)
    tcol = {t: j for j, t in enumerate(train_t)}
    partners_n = {}
    for thr in (700, 400):
        sub = links[(links["combined_score"] >= thr) & links["a"].isin(panel) & links["b"].isin(tcol)]
        groups = sub.groupby("a")["b"].apply(lambda v: sorted(set(v)))
        P = np.broadcast_to(b_full, (len(panel_list), axis.size)).copy()
        n_with = 0
        for i, t in enumerate(panel_list):
            if t in groups.index:
                cols = [tcol[g] for g in groups[t]]
                P[i, genes_used] = X[:, cols].mean(axis=1) + b
                n_with += 1
        pred[f"string{thr}"] = P
        partners_n[thr] = n_with
    print("panel targets with a STRING partner among training targets:", partners_n, flush=True)
    del X, links
    prow = {t: i for i, t in enumerate(panel_list)}
    cis_model = stage100.cis_prior(pd.read_csv(args.pairs), panel_list)
    coords = load_coordinates(args.coords)

    rows, per = [], []
    brng = np.random.default_rng(SEED)
    for held in HELD:
        truth = stage100.load_table(args.cache, held, "raw")
        tidx = truth.index()
        targets = [t for t in panel_list if t in tidx and t in set(k562_panel.targets)]
        T = truth.raw[np.array([tidx[t] for t in targets])].astype(np.float32)
        Z = truth_z(args.cache, held, truth, targets)
        tcols = np.array([col.get(t, -1) for t in targets])
        valid = np.isfinite(T) & keep[None, :]
        Tw = np.where(valid, T * w, 0.0).astype(np.float32)
        null_t = (Tw.astype(np.float64) ** 2).sum(axis=1)

        def score(P):
            pds = pds_proxy(P, T, w, panel_cols)
            reach = reach_proxy(P, T, Z, gate, tcols)
            fid = fidelity_proxy(P, T, Z, gate, tcols)
            Pw = np.where(valid, P * w, 0.0)
            err = ((Tw - Pw).astype(np.float64) ** 2).sum(axis=1)
            return pds, reach, fid, err

        cis = np.zeros((len(targets), axis.size), dtype=np.float32)
        obs = np.zeros_like(cis, dtype=bool)
        stage100.add_cis(cis, obs, targets, axis, cis_model, coords, 5000, 2.0)
        arms = {"common": np.broadcast_to(b_full, cis.shape).copy(), "cis": cis.copy()}
        rows_t = np.array([prow[t] for t in targets])
        for name, P_all in pred.items():
            P = P_all[rows_t]
            arms[name] = P
            if name.startswith("linear") or name == "string700":
                arms[name + "+cis"] = P + cis
        if held != "k562":   # in K562 the target's own K562 effect is the truth itself
            eff, den = mix([k562_panel], targets, weights={"k562": 1.0}, gamma=1.0, reliability_scale=100.0)
            eff[den == 0] = 0.0
            arms["transfer_ceiling"] = eff.astype(np.float32)
        res = {name: score(P) for name, P in arms.items()}
        ref = res["common"]
        regime = "T" if held == "k562" else "J"
        for name, (pds, reach, fid, err) in res.items():
            d, ci = boot(pds - ref[0], brng) if name != "common" else (0.0, [0.0, 0.0])
            rows.append({"regime": regime, "held_out": held, "arm": name, "targets": len(targets),
                         "pds_proxy": float(np.mean(pds)), "pds_minus_common": d, "ci95": ci,
                         "reach_proxy": float(np.nanmean(reach)), "prec_200": float(np.nanmean(fid["prec_200"])),
                         "mse_ratio": float(err.sum() / null_t.sum())})
            for t, a in zip(targets, pds):
                per.append({"held_out": held, "arm": name, "target": t, "pds": float(a)})
        print(held, "done", flush=True)
        del arms, res

    s = pd.DataFrame(rows)
    s.to_csv(args.out / "summary.csv", index=False)
    pd.DataFrame(per).to_csv(args.out / "per_target.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "bersagli_nuovi_2026-09-26/linear_new_targets.py",
                   "claim_type": "effect-space proxies; panel targets absent from every fit; not VCC scores",
                   "universe": str(args.universe), "training_targets": len(train_t),
                   "genes_modelled": int(genes_used.size), "fitted_targets": {n: m[2] for n, m in models.items()},
                   "panel_targets_with_string_partner": partners_n,
                   "rows": rows}, f, indent=1)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_rows", 200)
    print(s.drop(columns=["ci95"]).round(4).to_string())


if __name__ == "__main__":
    main()
