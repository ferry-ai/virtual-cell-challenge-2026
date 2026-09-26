"""Learned context-conditioned transfer (LCT): a model that learns how to transfer, gene by gene.

The production recipe averages the sources' effects with fixed rules (reliability by cells,
local shrinkage, gamma 1, one amplitude). LCT replaces the fixed rule with a regression learned
across contexts: for each (target, gene) pair it predicts the effect in a context from features
of the sources' measurements and of the biology around the pair:

  transfer   m_raw, m_shr (the recipe's pooled raw and shrunk effects), n_src, sign agreement,
             spread, max |z|, mean z of the sources;
  mechanism  cis prior (stage 100's head, 2 x median within 5 kb), own-gene flag;
  network    STRING association (stage 100's partner_effects over the K562 universe);
  context    percentile of the gene's basal expression in the context predicted and in the
             sources, their difference, percentile of the target's own expression;
  gene       responsiveness (share of K562 universe targets outside the panel moving it at
             |z| >= 3), its common response and spread over those targets, panel flag;
  target     strength (median over sources of genes at |z| >= 3).

Label: the held-out source's raw effect (clipped at +/-4), weight w^2, w = x/(1+x),
x = 0.05 CPM of the gene in that context. Tasks: each source held out in turn, predicted from
the other families (as sweep_v2). For a test task the model is trained ONLY on tasks whose
held-out source belongs to another family (sklearn HistGradientBoostingRegressor). Evaluated
against t16like (raw x 0.788) and t20like (shrunk x 1.576 + cis) on the same targets: PDS
proxy, reach proxy, precision at 200, weighted squared-error ratio; paired bootstrap; permutation
importance on the test task. Effect-space proxies against public sources, not VCC scores.

Known limits: K562 gene priors and the cis and STRING priors come from K562, so the K562 test
task shares context (not target outcomes) with its features, as in the earlier benches.

    scripts/py.cmd reports/trasferimento_appreso_2026-09-26/lct_bench.py --out reports/trasferimento_appreso_2026-09-26/r1
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "reports" / "modulo_cis_2026-09-26"))

from cis_bench import (DATA, FAMILY, SEED, boot, fidelity_proxy, pds_proxy, reach_proxy,  # noqa: E402
                       stage100, truth_z)
from vcc2026.multisource import mix  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402

SOURCES = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]
FEATURES = ["m_raw", "m_shr", "n_src", "sign_agree", "spread", "max_absz", "mean_z", "cis", "own_gene",
            "assoc", "expr_ctx", "expr_src", "expr_diff", "target_expr", "gene_resp", "gene_common",
            "gene_spread", "panel_gene", "target_strength"]
GENES_PER_TARGET = 1500


def pct(v: np.ndarray) -> np.ndarray:
    """Percentile of log1p CPM among the genes a context measured; NaN where it did not."""
    out = np.full(v.shape, np.nan)
    ok = np.isfinite(v)
    out[ok] = pd.Series(np.log1p(v[ok])).rank(pct=True).to_numpy()
    return out


def gene_priors(universe: Path, panel: set, n_genes: int) -> dict:
    idx = pd.read_csv(universe / "index.csv")
    s1 = np.zeros(n_genes)
    s2 = np.zeros(n_genes)
    hits = np.zeros(n_genes)
    n = np.zeros(n_genes)
    for chunk in sorted(idx["chunk"].unique()):
        z = np.load(universe / chunk, allow_pickle=False)
        keep = ~np.isin(z["targets"].astype(str), list(panel))
        eff = z["shrunk"][keep].astype(np.float64)
        zz = (z["raw"][keep] / z["se"][keep]).astype(np.float64)
        ok = np.isfinite(eff)
        s1 += np.where(ok, eff, 0).sum(axis=0)
        s2 += np.where(ok, eff ** 2, 0).sum(axis=0)
        hits += (np.abs(np.nan_to_num(zz)) >= 3).sum(axis=0)
        n += ok.sum(axis=0)
    mean = np.divide(s1, n, out=np.full(n_genes, np.nan), where=n > 0)
    var = np.divide(s2, n, out=np.full(n_genes, np.nan), where=n > 0) - mean ** 2
    return {"gene_resp": np.divide(hits, n, out=np.full(n_genes, np.nan), where=n > 0),
            "gene_common": mean, "gene_spread": np.sqrt(np.maximum(var, 0))}


def build(held, cache, axis, col, panel_list, basal, priors, cis_model, coords, assoc):
    """Feature matrices (targets x genes) for one task, the truth and its weights."""
    preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
    truth = stage100.load_table(cache, held, "raw")
    tidx = truth.index()
    tabs_raw = [stage100.load_table(cache, s, "raw") for s in preds]
    tabs_shr = [stage100.load_table(cache, s, "shrunk") for s in preds]
    base_t = [t for t in panel_list if t in tidx]
    m_raw, d_raw = mix(tabs_raw, base_t, weights={s: 1.0 for s in preds}, gamma=1.0, reliability_scale=100.0)
    m_shr, _ = mix(tabs_shr, base_t, weights={s: 1.0 for s in preds}, gamma=1.0, reliability_scale=100.0)
    ok = np.abs(np.nan_to_num(m_raw)).sum(axis=1) > 0
    targets = [t for t, o in zip(base_t, ok) if o]
    T, G = len(targets), axis.size
    F = {"m_raw": np.where(d_raw[ok] > 0, m_raw[ok], np.nan).astype(np.float32),
         "m_shr": np.where(d_raw[ok] > 0, m_shr[ok], np.nan).astype(np.float32)}
    vals, zs = [], []
    for tab in tabs_raw:
        rows = tab.rows(targets).astype(np.float32) - tab.common().astype(np.float32)
        ix = tab.index()
        se = np.full((T, G), np.nan, dtype=np.float32)
        for i, t in enumerate(targets):
            if t in ix:
                se[i] = tab.se[ix[t]]
        vals.append(rows)
        zs.append(tab.rows(targets).astype(np.float32) / se)
    V = np.stack(vals)
    Z = np.stack(zs)
    fin = np.isfinite(V)
    F["n_src"] = fin.sum(axis=0).astype(np.float32)
    sgn = np.where(fin, np.sign(V), 0).sum(axis=0)
    F["sign_agree"] = np.divide(np.abs(sgn), F["n_src"], out=np.full((T, G), np.nan, dtype=np.float32), where=F["n_src"] > 0)
    F["spread"] = np.nanstd(np.where(fin, V, np.nan), axis=0).astype(np.float32)
    with np.errstate(all="ignore"):
        F["max_absz"] = np.nanmax(np.abs(Z), axis=0).astype(np.float32)
        F["mean_z"] = np.nanmean(Z, axis=0).astype(np.float32)
    del V, Z, vals, zs, fin
    cis = np.zeros((T, G), dtype=np.float32)
    stage100.add_cis(cis, np.zeros((T, G), dtype=bool), targets, axis, cis_model, coords, 5000, 2.0)
    F["cis"] = cis
    own = np.zeros((T, G), dtype=np.float32)
    for i, t in enumerate(targets):
        if t in col:
            own[i, col[t]] = 1
    F["own_gene"] = own
    F["assoc"] = np.stack([assoc.get(t, np.zeros(G, dtype=np.float32)) for t in targets]).astype(np.float32)
    ctx = pct(basal[held].to_numpy())
    src = np.nanmean(np.vstack([pct(basal[s].to_numpy()) for s in preds]), axis=0)
    F["expr_ctx"] = np.broadcast_to(ctx.astype(np.float32), (T, G))
    F["expr_src"] = np.broadcast_to(src.astype(np.float32), (T, G))
    F["expr_diff"] = F["expr_ctx"] - F["expr_src"]
    texpr = np.array([ctx[col[t]] if t in col else np.nan for t in targets], dtype=np.float32)
    F["target_expr"] = np.broadcast_to(texpr[:, None], (T, G))
    for k in ("gene_resp", "gene_common", "gene_spread"):
        F[k] = np.broadcast_to(priors[k].astype(np.float32), (T, G))
    pg = np.zeros(G, dtype=np.float32)
    pg[[col[g] for g in panel_list if g in col]] = 1
    F["panel_gene"] = np.broadcast_to(pg, (T, G))
    st = []
    for tab in tabs_raw:
        ix = tab.index()
        cnt = np.full(T, np.nan)
        for i, t in enumerate(targets):
            if t in ix:
                z = tab.raw[ix[t]] / tab.se[ix[t]]
                cnt[i] = np.sum(np.abs(np.nan_to_num(z)) >= 3)
        st.append(cnt)
    strength = np.nanmedian(np.vstack(st), axis=0).astype(np.float32)
    F["target_strength"] = np.broadcast_to(strength[:, None], (T, G))
    y = truth.raw[np.array([tidx[t] for t in targets])].astype(np.float32)
    cpm_h = basal[held].to_numpy()
    x = 0.05 * np.nan_to_num(cpm_h)
    wh = (x / (1 + x)) ** 2
    return targets, F, y, wh.astype(np.float32), truth


def flat(F, rows_t, cols_g):
    return np.column_stack([F[k][rows_t, cols_g] for k in FEATURES]).astype(np.float32)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--genes", type=Path, default=DATA / "raw/controls/gene_names.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--universe", type=Path, default=DATA / "processed/universe_k562_2026-09-26")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--pairs", type=Path, default=REPO / "reports/cis_2026-09-17/k562_neighbour_pairs.csv")
    ap.add_argument("--links", type=Path, default=DATA / "interim/encoder_inputs_2026-09-14/string_physical_links")
    ap.add_argument("--info", type=Path, default=DATA / "interim/encoder_inputs_2026-09-14/string_protein_info")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    axis = pd.read_csv(args.genes)["gene_name"].astype(str).to_numpy()
    panel_list = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    col = {g: i for i, g in enumerate(axis)}
    panel_cols = np.array([col[g] for g in panel_list if g in col])
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    cpm_abc = basal[["A", "B", "C"]].mean(axis=1).to_numpy()
    xa = 0.05 * cpm_abc
    w_eval = (xa / (1.0 + xa)).astype(np.float32)
    gate = cpm_abc >= 5.0
    priors = gene_priors(args.universe, set(panel_list), axis.size)
    cis_model = stage100.cis_prior(pd.read_csv(args.pairs), panel_list)
    coords = load_coordinates(args.coords)
    assoc, _ = stage100.partner_effects(panel_list, args.universe, args.links, args.info, 700, axis)
    print(f"priors ready {time.time() - t0:.0f}s", flush=True)

    # pass 1: training rows of every task
    train = {}
    for held in SOURCES:
        targets, F, y, wh, _ = build(held, args.cache, axis, col, panel_list, basal, priors, cis_model, coords, assoc)
        rt, cg = [], []
        for i in range(len(targets)):
            g = np.flatnonzero(np.isfinite(y[i]) & (wh > 0))
            if g.size > GENES_PER_TARGET:
                g = rng.choice(g, size=GENES_PER_TARGET, replace=False)
            rt.append(np.full(g.size, i))
            cg.append(g)
        rt, cg = np.concatenate(rt), np.concatenate(cg)
        train[held] = (flat(F, rt, cg), np.clip(y[rt, cg], -4, 4), wh[cg])
        print(held, "features", train[held][0].shape, f"{time.time() - t0:.0f}s", flush=True)
        del F

    rows, imps = [], []
    brng = np.random.default_rng(SEED)
    for held in SOURCES:
        tr = [h for h in SOURCES if FAMILY[h] != FAMILY[held]]
        Xtr = np.vstack([train[h][0] for h in tr])
        ytr = np.concatenate([train[h][1] for h in tr])
        wtr = np.concatenate([train[h][2] for h in tr])
        model = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, max_leaf_nodes=63,
                                              min_samples_leaf=500, l2_regularization=1.0, early_stopping=True,
                                              validation_fraction=0.1, n_iter_no_change=25, random_state=SEED)
        model.fit(Xtr, ytr, sample_weight=wtr)
        del Xtr, ytr, wtr
        targets, F, y, wh, truth = build(held, args.cache, axis, col, panel_list, basal, priors, cis_model, coords, assoc)
        T, G = len(targets), axis.size
        P = np.zeros((T, G), dtype=np.float32)
        for a in range(0, T, 40):
            rt = np.repeat(np.arange(a, min(a + 40, T)), G)
            cg = np.tile(np.arange(G), min(a + 40, T) - a)
            P[a:min(a + 40, T)] = model.predict(flat(F, rt, cg)).reshape(-1, G)
        arms = {"t16like": np.nan_to_num(F["m_raw"]) * 0.788,
                "t20like": np.nan_to_num(F["m_shr"]) * 1.576 + F["cis"],
                "lct": P}
        Tt = y
        Z = truth_z(args.cache, held, truth, targets)
        tcols = np.array([col.get(t, -1) for t in targets])
        valid = np.isfinite(Tt) & ~np.isin(np.arange(G), panel_cols)[None, :]
        Tw = np.where(valid, Tt * w_eval, 0.0)
        null_t = (Tw.astype(np.float64) ** 2).sum()
        res, task_rows = {}, []
        for name, E in arms.items():
            pds = pds_proxy(E, Tt, w_eval, panel_cols)
            reach = reach_proxy(E, Tt, Z, gate, tcols)
            fid = fidelity_proxy(E, Tt, Z, gate, tcols)
            Pw = np.where(valid, E * w_eval, 0.0)
            err = float(((Tw - Pw).astype(np.float64) ** 2).sum() / null_t)
            res[name] = (pds, reach)
            task_rows.append({"held_out": held, "trained_on": "+".join(tr), "arm": name, "targets": T,
                              "pds_proxy": float(pds.mean()), "reach_proxy": float(np.nanmean(reach)),
                              "prec_200": float(np.nanmean(fid["prec_200"])), "mse_ratio": err})
        for row in task_rows:
            if row["arm"] != "t20like":
                d, ci = boot(res[row["arm"]][0] - res["t20like"][0], brng)
                row["pds_minus_t20like"], row["pds_ci95"] = d, ci
                d, ci = boot(res[row["arm"]][1] - res["t20like"][1], brng)
                row["reach_minus_t20like"], row["reach_ci95"] = d, ci
        rows += task_rows
        # permutation importance on a sample of the test task's rows
        sel_t = rng.choice(T, size=min(60, T), replace=False)
        rt = np.repeat(sel_t, 400)
        cg = np.concatenate([rng.choice(np.flatnonzero(np.isfinite(y[i]) & (wh > 0)), size=400, replace=True) for i in sel_t])
        pi = permutation_importance(model, flat(F, rt, cg), np.clip(y[rt, cg], -4, 4), sample_weight=wh[cg],
                                    n_repeats=3, random_state=SEED)
        for f_name, m in zip(FEATURES, pi.importances_mean):
            imps.append({"held_out": held, "feature": f_name, "importance": float(m)})
        print(held, "done", model.n_iter_, f"{time.time() - t0:.0f}s", flush=True)
        del F, P, arms

    s = pd.DataFrame(rows)
    s.to_csv(args.out / "summary.csv", index=False)
    pd.DataFrame(imps).to_csv(args.out / "importance.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "trasferimento_appreso_2026-09-26/lct_bench.py",
                   "claim_type": "effect-space proxies against held-out public sources, model trained on other families' "
                                 "tasks only; not VCC scores", "features": FEATURES, "genes_per_target": GENES_PER_TARGET,
                   "rows": rows, "importance": imps}, fh, indent=1, default=float)
    pd.set_option("display.width", 220)
    print(s.round(4).to_string(index=False))
    print(pd.DataFrame(imps).pivot(index="feature", columns="held_out", values="importance").round(5).to_string())


if __name__ == "__main__":
    main()
