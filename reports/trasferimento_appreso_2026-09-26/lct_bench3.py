"""r3: two channels. Direction from the transferred effects (t20), magnitude profile from the model.

r2 (lct_bench2.py) showed the learned model on centred labels (`lct_c`) loses the discrimination
between targets (PDS proxy -0.11..-0.14 against t20like) but ranks well which genes will move
(reach proxy +0.18 on HCT116, +0.11 on HEK293T; precision at 200 +0.07 on HCT116). This pass
keeps t20's target-specific direction and borrows only the model's magnitude profile:

  t20_rw<a>      t20like x (|lct_c| / its mean over the target's genes) ^ a, a = 0.25, 0.5, 1
  t20_sign_mag   sign(t20like) x |lct_c|, scaled to t20like's detectable genes
  gbpos_rw0.5    r2's gene_beta_pos reweighted the same way (a = 0.5)
Same nested design as r2 (3 target folds, family exclusion, panel excluded from STRING partners,
CD4 SE rebuilt); the fold models are refitted with the same seed. Predictions of every task are
saved (npz) so that further combinations need no refit. Proxies, not VCC scores.

    scripts/py.cmd reports/trasferimento_appreso_2026-09-26/lct_bench3.py --out reports/trasferimento_appreso_2026-09-26/r3 \
        --save C:/Users/ferra/vcc2026-data/processed/lct_r3_predictions_2026-09-26
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

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "reports" / "modulo_cis_2026-09-26"))
sys.path.insert(0, str(HERE))

from cis_bench import DATA, FAMILY, SEED, boot, pds_proxy, reach_proxy, stage100  # noqa: E402
from lct_bench import flat, gene_priors  # noqa: E402
from lct_bench2 import FAMILIES, GENES_PER_TARGET, N_FOLDS, SOURCES, build, precision_at  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402


def reweight(E, P, a):
    mag = np.abs(P)
    mean = mag.mean(axis=1, keepdims=True)
    return E * np.power(np.divide(mag, mean, out=np.zeros_like(mag), where=mean > 0), a)


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
    ap.add_argument("--save", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    args.save.mkdir(parents=True, exist_ok=False)
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
    mu = cpm_abc * 20000 / 1e6
    thr = np.where(mu > 0, 4.0 / np.sqrt(400 * np.maximum(mu, 1e-12)), np.inf)
    det = lambda E: float(np.median(((np.abs(E) > thr[None, :]) & gate[None, :]).sum(axis=1)))
    priors = gene_priors(args.universe, set(panel_list), axis.size)
    cis_model = stage100.cis_prior(pd.read_csv(args.pairs), panel_list)
    coords = load_coordinates(args.coords)
    assoc, _ = stage100.partner_effects(panel_list, args.universe, args.links, args.info, 700, axis,
                                        exclude=frozenset(panel_list))
    perm = rng.permutation(len(panel_list))
    fold = {panel_list[i]: int(k % N_FOLDS) for k, i in enumerate(perm)}
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
        with np.errstate(all="ignore"):
            yc = y - np.nanmean(y, axis=0, keepdims=True)
        train[held] = (flat(F, rt, cg), np.clip(yc[rt, cg], -4, 4), wh[cg], np.array([fold[targets[i]] for i in rt]))
        tfold = np.array([fold[t] for t in targets])
        sums = {}
        for f in range(N_FOLDS):
            m = F["m_shr"][tfold == f].astype(np.float64)
            yy = yc[tfold == f].astype(np.float64)
            okp = np.isfinite(m) & np.isfinite(yy)
            sums[f] = (np.where(okp, m * yy, 0).sum(axis=0), np.where(okp, m * m, 0).sum(axis=0))
        beta_sums[held] = sums
        print(held, "features", f"{time.time() - t0:.0f}s", flush=True)
        del F

    rows = []
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
        for held in [h for h in SOURCES if FAMILY[h] == fam]:
            targets, F, y, wh, Zt = build(held, args.cache, axis, col, panel_list, basal, priors, cis_model, coords, assoc)
            T, G = len(targets), axis.size
            P = np.zeros((T, G), dtype=np.float32)
            betas = np.zeros((T, G), dtype=np.float32)
            for k in range(N_FOLDS):
                idx = [i for i, t in enumerate(targets) if fold[t] == k]
                for a in range(0, len(idx), 40):
                    part = idx[a:a + 40]
                    P[part] = models[k].predict(flat(F, np.repeat(part, G), np.tile(np.arange(G), len(part)))).reshape(-1, G)
                num = sum(beta_sums[h][f][0] for h in SOURCES if FAMILY[h] != fam for f in range(N_FOLDS) if f != k)
                den = sum(beta_sums[h][f][1] for h in SOURCES if FAMILY[h] != fam for f in range(N_FOLDS) if f != k)
                bbar = num.sum() / max(den.sum(), 1e-12)
                lam = float(np.median(den[den > 0]))
                betas[idx] = ((num + lam * bbar) / (den + lam)).astype(np.float32)
            m_shr0 = np.nan_to_num(F["m_shr"])
            t20 = m_shr0 * 1.576 + F["cis"]
            gbpos = np.maximum(betas, 0) * m_shr0 * 1.576 + F["cis"]
            np.savez_compressed(args.save / f"{held}.npz", targets=np.array(targets), lct_c=P, t20like=t20.astype(np.float32),
                                gene_beta=betas, truth=y, truth_z=Zt.astype(np.float32))
            target_det = det(t20)

            def match(E):
                lo, hi = 1e-3, 1e4
                for _ in range(50):
                    mid = np.sqrt(lo * hi)
                    lo, hi = (mid, hi) if det(mid * E) < target_det else (lo, mid)
                return E * np.sqrt(lo * hi)

            arms = {"t20like": t20, "lct_c": P, "gene_beta_pos": gbpos}
            for a in (0.25, 0.5, 1.0):
                arms[f"t20_rw{a}"] = match(reweight(t20, P, a))
            arms["t20_sign_mag"] = match(np.sign(t20) * np.abs(P))
            arms["gbpos_rw0.5"] = match(reweight(gbpos, P, 0.5))
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
                                  "prec_200_shared": float(np.nanmean(prec[name][cohort])),
                                  "mse_ratio": float(((Tw - Pw) ** 2).sum() / null),
                                  "mse_ratio_best_scale": float(((Tw - a_star * Pw) ** 2).sum() / null),
                                  "detectable_median": det(E)})
            for row in task_rows:
                if row["arm"] != "t20like":
                    for key, j in (("pds", 0), ("reach", 1)):
                        d, ci = boot(res[row["arm"]][j] - res["t20like"][j], brng)
                        row[f"{key}_minus_t20like"], row[f"{key}_ci95"] = d, ci
                    d, ci = boot((res[row["arm"]][2] - res["t20like"][2])[cohort], brng)
                    row["prec_minus_t20like"], row["prec_ci95"] = d, ci
            rows += task_rows
            print(held, "done", f"{time.time() - t0:.0f}s", flush=True)
            del F, P, arms

    s = pd.DataFrame(rows)
    s.to_csv(args.out / "summary.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "trasferimento_appreso_2026-09-26/lct_bench3.py",
                   "claim_type": "effect-space proxies against held-out public sources; nested target folds and family "
                                 "exclusion; not VCC scores", "saved_predictions": str(args.save), "rows": rows},
                  fh, indent=1, default=float)
    pd.set_option("display.width", 250)
    cols = ["held_out", "arm", "pds_proxy", "pds_minus_t20like", "reach_proxy", "reach_minus_t20like",
            "prec_200_shared", "prec_minus_t20like", "mse_ratio", "mse_ratio_best_scale", "detectable_median"]
    print(s[cols].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
