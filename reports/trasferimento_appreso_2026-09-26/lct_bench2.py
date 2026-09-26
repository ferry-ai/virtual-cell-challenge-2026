"""r2 of the learned transfer (LCT) bench, after an independent review (codex, hub run
20260926-131907-v2-lct-review): nested target folds, no test outcome anywhere in training.

What r1 got wrong, and what changes here:
1. r1 trained, for a test task, on tasks whose LABEL was in another family, but those tasks used
   the test family's measurements of the SAME targets as input features. Here the panel targets
   are split into 3 seeded folds; the model predicting fold k of a test task is trained only on
   other-family tasks AND only on targets outside fold k, so no test target appears in training
   as a label or as an input row.
2. r1's STRING association used every K562 target as partner and centre, including panel
   targets, whose K562 effects are test labels. Here `partner_effects` excludes the whole panel.
3. `cd4_mix` has no SE in the cache: r1 turned its z into zeros. Here its SE is rebuilt from the
   three conditions with the pooling's own reliability weights, sqrt(sum r^2 se^2) / sum r
   (independence assumed), for its source-side z and for its truth z (reach proxy).
4. Precision at 200 is computed on one target cohort shared by every arm.
5. r1's model learned mostly WHICH GENES move on average in a context (its top features were
   expression percentiles), which helps squared error and hurts discrimination. Here the label
   is centred per gene over the task's targets, so the model learns the target-specific part
   (`lct_c`), and a simpler architecture is added: per-gene transfer coefficients
   beta_g = sum m y / sum m^2 over (target, task) pairs of other families and other folds,
   shrunk to their mean (`gene_beta`: beta_g x shrunk pooled effect x 1.576 + cis; `gene_beta_pos`
   with negative betas set to 0): how much each gene's response carries across contexts.
Added: `lct_matched`, the LCT prediction scaled so that its median number of detectable genes
per target (4 / sqrt(400 mu), >= 5 CPM, as sweep_v3) equals t20like's, and the squared-error
ratio of each arm at its own best single scale (the model's quality with the amplitude removed).

Features, label and model as r1 (lct_bench.py). Effect-space proxies against public sources,
not VCC scores.

    scripts/py.cmd reports/trasferimento_appreso_2026-09-26/lct_bench2.py --out reports/trasferimento_appreso_2026-09-26/r2
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
sys.path.insert(0, str(HERE))

from cis_bench import DATA, FAMILY, SEED, boot, pds_proxy, reach_proxy, stage100  # noqa: E402
from lct_bench import FEATURES, flat, gene_priors, pct  # noqa: E402
from vcc2026.multisource import mix  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402

SOURCES = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]
FAMILIES = ["k562", "cd4", "orion"]
GENES_PER_TARGET = 1500
N_FOLDS = 3
CD4_PARTS = ("cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr")


def cd4_mix_se(cache: Path, targets: list[str], n_genes: int) -> np.ndarray:
    """SE of the reliability-weighted mean of the CD4 conditions: sqrt(sum r^2 se^2) / sum r."""
    parts = [stage100.load_table(cache, p, "raw") for p in CD4_PARTS]
    num = np.zeros((len(targets), n_genes))
    den = np.zeros((len(targets), n_genes))
    for tab in parts:
        ix = tab.index()
        for i, t in enumerate(targets):
            if t in ix:
                j = ix[t]
                r = tab.n_cells[j] / (tab.n_cells[j] + 100.0)
                ok = np.isfinite(tab.raw[j]) & np.isfinite(tab.se[j])
                num[i, ok] += (r * tab.se[j][ok].astype(np.float64)) ** 2
                den[i, ok] += r
    return np.where(den > 0, np.sqrt(num) / np.maximum(den, 1e-12), np.nan).astype(np.float32)


def se_rows(cache, tab, targets, n_genes):
    if tab.name == "cd4_mix":
        return cd4_mix_se(cache, targets, n_genes)
    ix = tab.index()
    se = np.full((len(targets), n_genes), np.nan, dtype=np.float32)
    for i, t in enumerate(targets):
        if t in ix:
            se[i] = tab.se[ix[t]]
    return se


def build(held, cache, axis, col, panel_list, basal, priors, cis_model, coords, assoc):
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
    vals, zs, st = [], [], []
    for tab in tabs_raw:
        rows = tab.rows(targets).astype(np.float32)
        se = se_rows(cache, tab, targets, G)
        vals.append(rows - tab.common().astype(np.float32))
        z = rows / se
        zs.append(z)
        has = np.isfinite(z).any(axis=1)
        st.append(np.where(has, (np.abs(np.nan_to_num(z)) >= 3).sum(axis=1), np.nan))
    V, Z = np.stack(vals), np.stack(zs)
    fin = np.isfinite(V)
    F["n_src"] = fin.sum(axis=0).astype(np.float32)
    sgn = np.where(fin, np.sign(V), 0).sum(axis=0)
    F["sign_agree"] = np.divide(np.abs(sgn), F["n_src"], out=np.full((T, G), np.nan, dtype=np.float32), where=F["n_src"] > 0)
    with np.errstate(all="ignore"):
        F["spread"] = np.nanstd(np.where(fin, V, np.nan), axis=0).astype(np.float32)
        F["max_absz"] = np.nanmax(np.abs(Z), axis=0).astype(np.float32)
        F["mean_z"] = np.nanmean(Z, axis=0).astype(np.float32)
        strength = np.nanmedian(np.vstack(st), axis=0).astype(np.float32)
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
    with np.errstate(all="ignore"):
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
    F["target_strength"] = np.broadcast_to(strength[:, None], (T, G))
    y = truth.raw[np.array([tidx[t] for t in targets])].astype(np.float32)
    se_truth = se_rows(cache, truth, targets, G)
    x = 0.05 * np.nan_to_num(basal[held].to_numpy())
    wh = ((x / (1 + x)) ** 2).astype(np.float32)
    return targets, F, y, wh, y / se_truth


def precision_at(E, T, gate, tcols, n=200):
    out = np.full(E.shape[0], np.nan)
    for i in range(E.shape[0]):
        ok = gate & np.isfinite(T[i]) & (T[i] != 0) & (E[i] != 0)
        if tcols[i] >= 0:
            ok[tcols[i]] = False
        idx = np.flatnonzero(ok)
        if idx.size >= n:
            top = idx[np.argsort(-np.abs(E[i, idx]), kind="stable")[:n]]
            out[i] = float(np.mean(np.sign(E[i, top]) == np.sign(T[i, top])))
    return out


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
    if not np.isfinite(cpm_abc).all():
        raise SystemExit("A/B/C basal CPM not finite on the whole axis")
    xa = 0.05 * cpm_abc
    w_eval = (xa / (1.0 + xa)).astype(np.float32)
    gate = cpm_abc >= 5.0
    mu = cpm_abc * 20000 / 1e6
    thr = np.where(mu > 0, 4.0 / np.sqrt(400 * np.maximum(mu, 1e-12)), np.inf)
    priors = gene_priors(args.universe, set(panel_list), axis.size)
    cis_model = stage100.cis_prior(pd.read_csv(args.pairs), panel_list)
    coords = load_coordinates(args.coords)
    assoc, _ = stage100.partner_effects(panel_list, args.universe, args.links, args.info, 700, axis,
                                        exclude=frozenset(panel_list))
    perm = rng.permutation(len(panel_list))
    fold = {panel_list[i]: int(k % N_FOLDS) for k, i in enumerate(perm)}
    print(f"priors ready {time.time() - t0:.0f}s", flush=True)

    train, beta_sums = {}, {}
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
        tf = np.array([fold[targets[i]] for i in rt])
        with np.errstate(all="ignore"):
            yc = y - np.nanmean(y, axis=0, keepdims=True)      # the target-specific part, gene by gene
        train[held] = (flat(F, rt, cg), np.clip(yc[rt, cg], -4, 4), wh[cg], tf)
        # per-gene transfer sums by fold: beta_g = sum m y / sum m^2 over (target, task) pairs
        tfold = np.array([fold[t] for t in targets])
        sums = {}
        for f in range(N_FOLDS):
            rows_f = tfold == f
            m = F["m_shr"][rows_f].astype(np.float64)
            yy = yc[rows_f].astype(np.float64)
            okp = np.isfinite(m) & np.isfinite(yy)
            sums[f] = (np.where(okp, m * yy, 0).sum(axis=0), np.where(okp, m * m, 0).sum(axis=0))
        beta_sums[held] = sums
        print(held, "features", train[held][0].shape, f"{time.time() - t0:.0f}s", flush=True)
        del F

    rows, imps = [], []
    brng = np.random.default_rng(SEED)
    for fam in FAMILIES:
        models = {}
        for k in range(N_FOLDS):
            tr = [h for h in SOURCES if FAMILY[h] != fam]
            sel = [(train[h][0][train[h][3] != k], train[h][1][train[h][3] != k], train[h][2][train[h][3] != k]) for h in tr]
            m = HistGradientBoostingRegressor(max_iter=600, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=500,
                                              l2_regularization=1.0, early_stopping=True, validation_fraction=0.1,
                                              n_iter_no_change=30, random_state=SEED)
            m.fit(np.vstack([s[0] for s in sel]), np.concatenate([s[1] for s in sel]), sample_weight=np.concatenate([s[2] for s in sel]))
            models[k] = m
            print(fam, "fold", k, "iters", m.n_iter_, f"{time.time() - t0:.0f}s", flush=True)
        for held in [h for h in SOURCES if FAMILY[h] == fam]:
            targets, F, y, wh, Zt = build(held, args.cache, axis, col, panel_list, basal, priors, cis_model, coords, assoc)
            T, G = len(targets), axis.size
            P = np.zeros((T, G), dtype=np.float32)
            for k in range(N_FOLDS):
                idx = [i for i, t in enumerate(targets) if fold[t] == k]
                for a in range(0, len(idx), 40):
                    part = idx[a:a + 40]
                    rt = np.repeat(part, G)
                    cg = np.tile(np.arange(G), len(part))
                    P[part] = models[k].predict(flat(F, rt, cg)).reshape(-1, G)
            t20 = np.nan_to_num(F["m_shr"]) * 1.576 + F["cis"]
            # per-gene transfer coefficients from other families' tasks, other folds' targets
            betas = np.zeros((T, G), dtype=np.float32)
            beta_info = {}
            for k in range(N_FOLDS):
                num = sum(beta_sums[h][f][0] for h in SOURCES if FAMILY[h] != fam for f in range(N_FOLDS) if f != k)
                den = sum(beta_sums[h][f][1] for h in SOURCES if FAMILY[h] != fam for f in range(N_FOLDS) if f != k)
                bbar = num.sum() / max(den.sum(), 1e-12)
                lam = float(np.median(den[den > 0]))
                b = (num + lam * bbar) / (den + lam)
                idx = [i for i, t in enumerate(targets) if fold[t] == k]
                betas[idx] = b.astype(np.float32)
                beta_info[k] = {"beta_bar": float(bbar), "lambda": lam,
                                "beta_quantiles": np.quantile(b[den > 0], [0.05, 0.25, 0.5, 0.75, 0.95]).tolist()}
            m_shr0 = np.nan_to_num(F["m_shr"])
            gene_beta = betas * m_shr0 * 1.576 + F["cis"]
            gene_beta_pos = np.maximum(betas, 0) * m_shr0 * 1.576 + F["cis"]
            det = lambda E: float(np.median(((np.abs(E) > thr[None, :]) & gate[None, :]).sum(axis=1)))
            target_det = det(t20)
            lo, hi = 0.1, 1000.0
            for _ in range(40):
                mid = np.sqrt(lo * hi)
                lo, hi = (mid, hi) if det(mid * P) < target_det else (lo, mid)
            s_match = float(np.sqrt(lo * hi))
            arms = {"t16like": np.nan_to_num(F["m_raw"]) * 0.788, "t20like": t20, "gene_beta": gene_beta,
                    "gene_beta_pos": gene_beta_pos, "lct_c": P, "lct_c_matched": P * s_match,
                    "lct_c+t20like": t20 + P * s_match}
            tcols = np.array([col.get(t, -1) for t in targets])
            valid = np.isfinite(y) & ~np.isin(np.arange(G), panel_cols)[None, :]
            Tw = np.where(valid, y * w_eval, 0.0).astype(np.float64)
            null = float((Tw ** 2).sum())
            prec = {name: precision_at(E, y, gate, tcols) for name, E in arms.items()}
            cohort = np.all([np.isfinite(v) for v in prec.values()], axis=0)
            res, task_rows = {}, []
            for name, E in arms.items():
                pds = pds_proxy(E, y, w_eval, panel_cols)
                reach = reach_proxy(E, y, Zt, gate, tcols)
                Pw = np.where(valid, E * w_eval, 0.0).astype(np.float64)
                a_star = float((Pw * Tw).sum() / max((Pw * Pw).sum(), 1e-12))
                res[name] = (pds, reach, prec[name])
                task_rows.append({"held_out": held, "arm": name, "targets": T, "pds_proxy": float(pds.mean()),
                                  "reach_proxy": float(np.nanmean(reach)),
                                  "prec_200_shared": float(np.nanmean(prec[name][cohort])), "prec_cohort": int(cohort.sum()),
                                  "mse_ratio": float(((Tw - Pw) ** 2).sum() / null),
                                  "mse_ratio_best_scale": float(((Tw - a_star * Pw) ** 2).sum() / null),
                                  "best_scale": a_star, "detectable_median": det(E),
                                  "scale_vs_model": s_match if name.startswith("lct_c") else None,
                                  "beta_info": beta_info if name == "gene_beta" else None})
            for row in task_rows:
                if row["arm"] != "t20like":
                    for key, j in (("pds", 0), ("reach", 1)):
                        d, ci = boot(res[row["arm"]][j] - res["t20like"][j], brng)
                        row[f"{key}_minus_t20like"], row[f"{key}_ci95"] = d, ci
                    d, ci = boot((res[row["arm"]][2] - res["t20like"][2])[cohort], brng)
                    row["prec_minus_t20like"], row["prec_ci95"] = d, ci
            rows += task_rows
            with np.errstate(all="ignore"):
                yc = y - np.nanmean(y, axis=0, keepdims=True)
            k0 = [i for i, t in enumerate(targets) if fold[t] == 0]
            sel_t = rng.choice(k0, size=min(50, len(k0)), replace=False)
            rt = np.repeat(sel_t, 300)
            cg = np.concatenate([rng.choice(np.flatnonzero(np.isfinite(y[i]) & (wh > 0)), size=300, replace=True) for i in sel_t])
            pi = permutation_importance(models[0], flat(F, rt, cg), np.clip(np.nan_to_num(yc[rt, cg]), -4, 4), sample_weight=wh[cg],
                                        n_repeats=3, random_state=SEED)
            imps += [{"held_out": held, "feature": f, "importance": float(v)} for f, v in zip(FEATURES, pi.importances_mean)]
            print(held, "done", f"{time.time() - t0:.0f}s", flush=True)
            del F, P, arms

    s = pd.DataFrame(rows)
    s.to_csv(args.out / "summary.csv", index=False)
    pd.DataFrame(imps).to_csv(args.out / "importance.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "trasferimento_appreso_2026-09-26/lct_bench2.py",
                   "claim_type": "effect-space proxies against held-out public sources; nested target folds and "
                                 "family exclusion; not VCC scores", "features": FEATURES, "n_folds": N_FOLDS,
                   "rows": rows, "importance": imps}, fh, indent=1, default=float)
    pd.set_option("display.width", 250)
    cols = ["held_out", "arm", "pds_proxy", "pds_minus_t20like", "pds_ci95", "reach_proxy", "reach_minus_t20like",
            "prec_200_shared", "prec_minus_t20like", "mse_ratio", "mse_ratio_best_scale", "detectable_median"]
    print(s[[c for c in cols if c in s]].round(4).to_string(index=False))
    print(pd.DataFrame(imps).pivot(index="feature", columns="held_out", values="importance").round(5).to_string())


if __name__ == "__main__":
    main()
