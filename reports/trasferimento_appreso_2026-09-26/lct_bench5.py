"""r5: the learned magnitude channel on a bench isolated as the audit of 26 September asks.

The audit (codex, reports/audit_piani_dati_2026-09-26/RISULTATI.md section 4) found that r2-r4
built every task before the fold loop: source centres (each source's mean response) and label
centres included the held-out targets, and a training task could use the held-out family's source
as an input. What changes here:
1. Strict family exclusion. For a held-out family no source of that family enters training, as a
   label, an input or a centre. Training tasks are the other families' sources, each predicted
   from the sources of the remaining families (K562 held out: CD4 from HCT116 and HEK293T,
   HCT116 and HEK293T from CD4).
2. Built inside each target fold. Training features, input centres and label centres use only the
   training fold's targets. Test features use the other families' sources on every panel target,
   as stage 104 does for A/B/C: those are inputs, never labels.
3. Early stopping is validated on a tenth of the (task, target) groups held out whole
   (`transfer_model.fit_magnitude_model(groups=...)`), not on random rows.
4. Arms: `t20like` (shrunk pooled transfer x 1.576 + cis head); `rw_all0.25` (every gene
   reweighted, as stage 104 wrote effects_t21_2026-09-26); `rw_tx0.25` and `rw_tx0.5` (only the
   transferred part reweighted; the target's own gene and the cis head keep their values). Every
   arm is rescaled to t20like's median detectable genes, the cis head outside the scale.
5. Proxies: PDS, reach and sign precision@200 in effect space, as r3; PDS and an nMAE proxy
   (sum |pred - truth| / sum |truth| on the truth's significant genes, own gene out) after the
   trial-01 profile step and a 400-cell pseudobulk (r4's model, A/B/C basals, seeds 1-3).
Regime C: each target is measured in other contexts, and the held-out context's line never enters
training. The gene priors, cis prior and STRING partners come from K562 (panel targets excluded):
when K562 is held out its line is not new, and the output says so. The production code is the one
under test (`vcc2026.transfer_model`, `vcc2026.priors`, stage 104's loaders). Proxies against public
sources, not VCC scores.

    scripts/py.cmd reports/trasferimento_appreso_2026-09-26/lct_bench5.py --out reports/trasferimento_appreso_2026-09-26/r5 \
        --save C:/Users/ferra/vcc2026-data/processed/lct_r5_predictions_2026-09-26
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "modulo_cis_2026-09-26"))
sys.path.insert(0, str(REPO / "reports" / "banco_varianti_2026-09-25"))
sys.path.insert(0, str(HERE))

from cis_bench import DATA, SEED, boot, pds_proxy, reach_proxy  # noqa: E402
from lct_bench2 import precision_at  # noqa: E402
from noise_sim import rank_pds  # noqa: E402
from noise_sim2 import realise  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402
from vcc2026.priors import add_cis, cis_prior, partner_effects  # noqa: E402
from vcc2026.transfer_model import (  # noqa: E402
    detectable_threshold, fit_magnitude_model, gene_priors, match_detectable, pair_features, predict_magnitude,
    reweight, training_rows,
)

_spec = importlib.util.spec_from_file_location("stage104", REPO / "scripts" / "104_learned_reweighting.py")
stage104 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage104)

SOURCES = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]
FAMILIES = ["k562", "cd4", "orion"]
N_FOLDS = 3
GENES_PER_TARGET = 1500
AMPLITUDE = 1.576


def family(name: str) -> str:
    return name.split("_")[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--universe", type=Path, default=DATA / "processed/universe_k562_2026-09-26")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--recipe", type=Path, default=REPO / "configs/recipes/t20.json")
    ap.add_argument("--links", type=Path, default=DATA / "interim/encoder_inputs_2026-09-14/string_physical_links")
    ap.add_argument("--info", type=Path, default=DATA / "interim/encoder_inputs_2026-09-14/string_protein_info")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--save", type=Path, required=True)
    ap.add_argument("--max-targets", type=int, default=0, help="smoke run on the first N panel targets")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    args.save.mkdir(parents=True, exist_ok=False)
    t0 = time.time()
    log = lambda msg: print(f"[{time.time() - t0:6.0f}s] {msg}", flush=True)  # noqa: E731

    rng = np.random.default_rng(SEED)
    axis = np.asarray(official_axis().symbols)
    G = axis.size
    col = {g: i for i, g in enumerate(axis)}
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    panel_all = list(panel)
    if args.max_targets:
        panel = panel[:args.max_targets]
    panel_cols = np.array([col[g] for g in panel_all if g in col])
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    cpm_abc = basal[["A", "B", "C"]].mean(axis=1).to_numpy()
    xa = 0.05 * cpm_abc
    w_eval = (xa / (1.0 + xa)).astype(np.float32)
    gate = cpm_abc >= 5.0
    thr = detectable_threshold(cpm_abc)
    det = lambda E: float(np.median(((np.abs(E) > thr[None, :]) & gate[None, :]).sum(axis=1)))  # noqa: E731

    cis_spec = json.loads(args.recipe.read_text(encoding="utf-8"))["cis"]
    coords = load_coordinates(args.coords)
    cis_model = cis_prior(pd.read_csv(REPO / cis_spec["pairs"]), panel_all)

    def cis_matrix(targets):
        m = np.zeros((len(targets), G), dtype=np.float32)
        add_cis(m, np.zeros((len(targets), G), dtype=bool), targets, axis, cis_model, coords,
                int(cis_spec["max_distance_bp"]), float(cis_spec.get("scale", 1.0)))
        return m

    idx = pd.read_csv(args.universe / "index.csv")
    priors = gene_priors((np.load(args.universe / c, allow_pickle=False) for c in sorted(idx["chunk"].unique())),
                         set(panel_all), G)
    assoc, _ = partner_effects(panel, args.universe, args.links, args.info, 700, axis, exclude=frozenset(panel_all))
    tables = {n: stage104.load(args.cache, n) for n in SOURCES}
    log("priors, partners and sources ready")

    perm = rng.permutation(len(panel))
    fold = {panel[i]: int(k % N_FOLDS) for k, i in enumerate(perm)}

    def features(preds, targets, context_cpm, centre_on):
        raws = [tables[n][0] for n in preds]
        return pair_features(raws, [tables[n][1] for n in preds],
                             [stage104.source_se(args.cache, t, targets, G) for t in raws], targets, col, context_cpm,
                             [basal[n].to_numpy() for n in preds], priors, cis_matrix(targets),
                             np.stack([assoc.get(t, np.zeros(G, dtype=np.float32)) for t in targets]), panel_cols,
                             centre_on=centre_on)

    def covered(targets, preds):
        return [t for t in targets if any(t in tables[n][0].index() for n in preds)]

    models, train_info = {}, []
    for fi, fam in enumerate(FAMILIES):
        for k in range(N_FOLDS):
            train_t = [t for t in panel if fold[t] != k]
            Xs, ys, ws, gs = [], [], [], []
            for si, task in enumerate([s for s in SOURCES if family(s) != fam]):
                preds = [s for s in SOURCES if family(s) not in (fam, family(task))]
                truth = tables[task][0]
                tix = truth.index()
                targets = covered([t for t in train_t if t in tix], preds)
                F = features(preds, targets, basal[task].to_numpy(), centre_on=train_t)
                y = truth.raw[np.array([tix[t] for t in targets])].astype(np.float32)
                x = 0.05 * np.nan_to_num(basal[task].to_numpy())
                X, yy, ww, rows = training_rows(F, y, ((x / (1 + x)) ** 2).astype(np.float32), GENES_PER_TARGET,
                                                np.random.default_rng([SEED, fi, k, si]), with_rows=True)
                Xs.append(X)
                ys.append(yy)
                ws.append(ww)
                gs.append(si * 100000 + rows)
                train_info.append({"held_family": fam, "fold": k, "task": task, "inputs": preds, "targets": len(targets),
                                   "rows": int(yy.size)})
                del F
            model = fit_magnitude_model(np.vstack(Xs), np.concatenate(ys), np.concatenate(ws), SEED,
                                        groups=np.concatenate(gs))
            models[(fam, k)] = model
            train_info[-1]["n_iter_of_fold_model"] = int(model.n_iter_)
            log(f"{fam} fold {k}: model fitted on {sum(len(y) for y in ys)} rows, {model.n_iter_} iterations")
            del Xs, ys, ws, gs

    rows_out = []
    brng = np.random.default_rng(SEED)
    for held in SOURCES:
        fam = family(held)
        preds = [s for s in SOURCES if family(s) != fam]
        truth = tables[held][0]
        tix = truth.index()
        targets = covered([t for t in panel if t in tix], preds)
        T = len(targets)
        F = features(preds, targets, basal[held].to_numpy(), centre_on=None)
        P = np.zeros((T, G), dtype=np.float32)
        for k in range(N_FOLDS):
            ix = np.array([i for i, t in enumerate(targets) if fold[t] == k])
            sub = {name: np.asarray(v)[ix] for name, v in F.items()}
            P[ix] = predict_magnitude(models[(fam, k)], sub, ix.size, G)
            del sub
        y = truth.raw[np.array([tix[t] for t in targets])].astype(np.float32)
        Zt = y / stage104.source_se(args.cache, truth, targets, G)
        tx = (np.nan_to_num(F["m_shr"]) * AMPLITUDE).astype(np.float32)
        cis = F["cis"].astype(np.float32)
        own = F["own_gene"] > 0
        t20 = tx + cis
        arms = {"t20like": t20, "rw_all0.25": match_detectable(reweight(t20, P, 0.25), t20, thr, gate)[0]}
        for a in (0.25, 0.5):
            arms[f"rw_tx{a}"] = match_detectable(reweight(tx, P, a, keep=own), t20, thr, gate, offset=cis)[0]
        np.savez_compressed(args.save / f"{held}.npz", targets=np.array(targets), magnitude=P, t20like=t20, tx=tx, cis=cis,
                            truth=y, truth_z=Zt.astype(np.float32))
        del F

        tcols = np.array([col.get(t, -1) for t in targets])
        valid = np.isfinite(y) & ~np.isin(np.arange(G), panel_cols)[None, :]
        Tw = np.where(valid, y * w_eval, 0.0).astype(np.float64)
        null = float((Tw ** 2).sum())
        sig = np.isfinite(y) & (np.abs(np.nan_to_num(Zt)) >= 3) & gate[None, :] & ~own
        observed = np.abs(t20) > 0
        live = {}
        for c in ("A", "B", "C"):
            cpm = basal[c].to_numpy(dtype=float)
            x = 0.05 * cpm
            keep = np.ones(G, dtype=bool)
            keep[panel_cols] = False
            live[c] = (cpm, x, keep & (cpm > 0))
        prec = {name: precision_at(E, y, gate, tcols) for name, E in arms.items()}
        cohort = np.all([np.isfinite(v) for v in prec.values()], axis=0)
        per = {}
        for name, E in arms.items():
            pds_gen, nmae_gen = [], []
            for c in ("A", "B", "C"):
                cpm, x, lv = live[c]
                Tl = (np.log1p(x * np.exp(np.clip(np.nan_to_num(y), -20, 20))) - np.log1p(x))[:, lv]
                for seed in (1, 2, 3):
                    noisy, _, _ = realise(E, cpm, observed, np.random.default_rng([seed, ord(c)]))
                    D = (np.log1p(x * np.exp(np.clip(noisy, -20, 20))) - np.log1p(x))[:, lv]
                    pds_gen.append(rank_pds(D, Tl))
                    err = np.where(sig, np.abs(noisy - np.nan_to_num(y)), 0.0).sum(axis=1)
                    ref = np.where(sig, np.abs(np.nan_to_num(y)), 0.0).sum(axis=1)
                    nmae_gen.append(np.where(ref > 0, err / np.maximum(ref, 1e-12), np.nan))
            Pw = np.where(valid, E * w_eval, 0.0).astype(np.float64)
            per[name] = {"pds": pds_proxy(E, y, w_eval, panel_cols), "reach": reach_proxy(E, y, Zt, gate, tcols),
                         "prec": prec[name], "pds_gen": np.mean(pds_gen, axis=0), "nmae_gen": np.nanmean(nmae_gen, axis=0),
                         "mse_ratio": float(((Tw - Pw) ** 2).sum() / null),
                         "energy_ratio": float((np.asarray(E, np.float64) ** 2).sum() / (np.asarray(t20, np.float64) ** 2).sum()),
                         "detectable_median": det(E)}
        for name, v in per.items():
            row = {"held_out": held, "arm": name, "targets": T, "line_new": held != "k562",
                   "pds_proxy": float(np.mean(v["pds"])), "reach_proxy": float(np.nanmean(v["reach"])),
                   "prec_200_shared": float(np.nanmean(v["prec"][cohort])), "pds_gen": float(np.mean(v["pds_gen"])),
                   "nmae_gen": float(np.nanmean(v["nmae_gen"])), "mse_ratio": v["mse_ratio"],
                   "energy_ratio": v["energy_ratio"], "detectable_median": v["detectable_median"]}
            if name != "t20like":
                base = per["t20like"]
                for key in ("pds", "reach", "pds_gen", "nmae_gen"):
                    diff = np.asarray(v[key], dtype=np.float64) - np.asarray(base[key], dtype=np.float64)
                    diff = diff[np.isfinite(diff)]
                    row[f"{key}_minus_t20like"], row[f"{key}_ci95"] = boot(diff, brng)
                d, ci = boot((v["prec"] - base["prec"])[cohort], brng)
                row["prec_minus_t20like"], row["prec_ci95"] = d, ci
            rows_out.append(row)
        log(f"{held}: {T} targets evaluated")

    s = pd.DataFrame(rows_out)
    s.to_csv(args.out / "summary.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "trasferimento_appreso_2026-09-26/lct_bench5.py",
                   "claim_type": "effect-space and generator-model proxies against held-out public sources; regime C "
                                 "(targets measured in other contexts); strict family exclusion and fold-internal "
                                 "centres; not VCC scores",
                   "saved_predictions": str(args.save), "training": train_info, "rows": rows_out},
                  fh, indent=1, default=float)
    pd.set_option("display.width", 250)
    cols = ["held_out", "arm", "pds_proxy", "pds_minus_t20like", "reach_minus_t20like", "prec_minus_t20like",
            "pds_gen", "pds_gen_minus_t20like", "pds_gen_ci95", "nmae_gen", "nmae_gen_minus_t20like", "energy_ratio",
            "detectable_median"]
    print(s[[c for c in cols if c in s.columns]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
