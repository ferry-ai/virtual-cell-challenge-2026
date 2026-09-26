"""Hierarchical empirical-Bayes transfer (candidate t22) against the t20 shape, on the isolated bench.

Model, per (target t, gene g), for each input source s (its common response over the panel removed,
gamma 1, as in the recipe):

    y_s = theta + delta_s + e_s,   theta ~ N(0, sigma2_g),  delta_s ~ N(0, tau2_g),  e_s ~ N(0, k_s SE_s^2)

theta is the response the lines share, delta_s the line's own deviation, e_s the source's sampling
noise. sigma2_g and tau2_g are method-of-moments estimates over the panel targets from the INPUT
sources only (E[y_s y_s'] = sigma2 for s != s'; E[y_s^2] = sigma2 + tau2 + k_s E[SE_s^2]), each blended
with the median of the genes of similar expression (weight n / (n + 100), n targets with data).
k_s inflates CD4's SE for the variance between donors that its pooled SE does not see (arm k2: k = 2,
inside the 1.65-2.17 measured by session 76a3a45e, CP-0040 section 5; arm k1: none). The prediction
for a new line is the posterior mean of theta,

    theta_hat = sum_s y_s / (tau2 + k_s SE_s^2)  /  (1 / sigma2 + sum_s 1 / (tau2 + k_s SE_s^2)),

times one scale plus the cis head of the t20 recipe (outside the scale). Genes whose response does
not repeat across lines (sigma2 small against tau2) shrink toward zero. No held-out measurement
enters: the variance components use the input sources, which production also has.

Arms: `t20like` (shrunk pooled transfer x 1.576 + cis); `eb_k1_det`, `eb_k2_det` (scale matched to
t20like's median detectable genes, as the recipe's amplitude was chosen); `eb_k2_energy` (scale
matched to t20like's energy). Proxies as r5 of reports/trasferimento_appreso_2026-09-26/: PDS, reach,
precision in effect space; PDS and nMAE after the trial-01 profile step and a 400-cell pseudobulk.
Regime C; K562 held out is not a new line (the cis prior comes from K562). Not VCC scores.

    scripts/py.cmd reports/trasferimento_gerarchico_2026-09-26/eb_bench.py --out reports/trasferimento_gerarchico_2026-09-26/r1 \
        --save C:/Users/ferra/vcc2026-data/processed/eb_r1_predictions_2026-09-26
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
sys.path.insert(0, str(REPO / "reports" / "trasferimento_appreso_2026-09-26"))

from cis_bench import DATA, SEED, boot, pds_proxy, reach_proxy  # noqa: E402
from lct_bench2 import precision_at  # noqa: E402
from noise_sim import rank_pds  # noqa: E402
from noise_sim2 import realise  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.multisource import mix  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402
from vcc2026.priors import add_cis, cis_prior  # noqa: E402
from vcc2026.transfer_model import detectable_threshold, match_detectable  # noqa: E402

_spec = importlib.util.spec_from_file_location("stage104", REPO / "scripts" / "104_learned_reweighting.py")
stage104 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage104)

SOURCES = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]
AMPLITUDE = 1.576
BIN_WEIGHT = 100.0
N_BINS = 50
# pendenze ufficiali sulla media dei sei membri, per unita' di grezzo: pds 2.165 / 6, nmae 1 / 0.608 / 6
W_PDS, W_NMAE = 0.36, 0.27


def family(name: str) -> str:
    return name.split("_")[0]


def variance_components(ys, ses, ks, expr):
    """Per-gene sigma2 (shared) and tau2 (line deviation) by moments, blended with expression bins."""
    G = ys[0].shape[1]
    s_num, s_den = np.zeros(G), np.zeros(G)
    for i in range(len(ys)):
        for j in range(i + 1, len(ys)):
            ok = np.isfinite(ys[i]) & np.isfinite(ys[j])
            s_num += np.where(ok, ys[i] * ys[j], 0.0).sum(axis=0)
            s_den += ok.sum(axis=0)
    sigma2 = np.divide(s_num, s_den, out=np.zeros(G), where=s_den > 0)
    excess, n_ex = np.zeros(G), np.zeros(G)
    for y, se, k in zip(ys, ses, ks):
        ok = np.isfinite(y) & np.isfinite(se)
        excess += np.where(ok, y * y - k * se * se, 0.0).sum(axis=0)
        n_ex += ok.sum(axis=0)
    total = np.divide(excess, n_ex, out=np.zeros(G), where=n_ex > 0)
    tau2 = total - sigma2
    sigma2, tau2 = np.maximum(sigma2, 0.0), np.maximum(tau2, 0.0)
    has = (s_den > 0) & (n_ex > 0) & np.isfinite(expr)
    edges = np.quantile(expr[has], np.linspace(0, 1, N_BINS + 1)[1:-1]) if has.any() else np.array([])
    b = np.digitize(np.nan_to_num(expr, nan=-1.0), edges)
    out = {}
    for name, v, n in (("sigma2", sigma2, s_den / max(len(ys) - 1, 1)), ("tau2", tau2, n_ex / len(ys))):
        med = np.array([np.median(v[has & (b == k)]) if (has & (b == k)).any() else 0.0 for k in range(N_BINS)])
        out[name] = np.where(has, (n * v + BIN_WEIGHT * med[b]) / (n + BIN_WEIGHT), 0.0)
    return out["sigma2"], out["tau2"]


def posterior_mean(ys, ses, ks, sigma2, tau2):
    num = np.zeros_like(ys[0], dtype=np.float64)
    den = np.zeros_like(ys[0], dtype=np.float64)
    for y, se, k in zip(ys, ses, ks):
        ok = np.isfinite(y) & np.isfinite(se)
        prec = np.where(ok, 1.0 / np.maximum(tau2[None, :] + k * np.where(ok, se, 0.0) ** 2, 1e-12), 0.0)
        num += prec * np.where(ok, y, 0.0)
        den += prec
    prior = np.divide(1.0, sigma2, out=np.full_like(sigma2, np.inf), where=sigma2 > 0)
    return np.where(np.isfinite(prior)[None, :] & (den > 0), num / (prior[None, :] + den), 0.0).astype(np.float32)


def match_energy(effect, reference, offset):
    target = float((np.asarray(reference, np.float64) ** 2).sum())
    lo, hi = 1e-3, 1e4
    for _ in range(60):
        mid = np.sqrt(lo * hi)
        e = float(((mid * effect.astype(np.float64) + offset) ** 2).sum())
        lo, hi = (mid, hi) if e < target else (lo, mid)
    s = float(np.sqrt(lo * hi))
    return (effect * s + offset).astype(np.float32), s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--recipe", type=Path, default=REPO / "configs/recipes/t20.json")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--save", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    args.save.mkdir(parents=True, exist_ok=False)
    t0 = time.time()
    log = lambda msg: print(f"[{time.time() - t0:6.0f}s] {msg}", flush=True)  # noqa: E731

    axis = np.asarray(official_axis().symbols)
    G = axis.size
    col = {g: i for i, g in enumerate(axis)}
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    panel_cols = np.array([col[g] for g in panel if g in col])
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    cpm_abc = basal[["A", "B", "C"]].mean(axis=1).to_numpy()
    xa = 0.05 * cpm_abc
    w_eval = (xa / (1.0 + xa)).astype(np.float32)
    gate = cpm_abc >= 5.0
    thr = detectable_threshold(cpm_abc)
    det = lambda E: float(np.median(((np.abs(E) > thr[None, :]) & gate[None, :]).sum(axis=1)))  # noqa: E731
    cis_spec = json.loads(args.recipe.read_text(encoding="utf-8"))["cis"]
    coords = load_coordinates(args.coords)
    cis_model = cis_prior(pd.read_csv(REPO / cis_spec["pairs"]), panel)
    tables = {n: stage104.load(args.cache, n) for n in SOURCES}
    log("sources ready")

    rows_out, comp_out = [], []
    brng = np.random.default_rng(SEED)
    for held in SOURCES:
        preds = [s for s in SOURCES if family(s) != family(held)]
        truth = tables[held][0]
        tix = truth.index()
        targets = [t for t in panel if t in tix and any(t in tables[n][0].index() for n in preds)]
        T = len(targets)
        cis = np.zeros((T, G), dtype=np.float32)
        add_cis(cis, np.zeros((T, G), dtype=bool), targets, axis, cis_model, coords,
                int(cis_spec["max_distance_bp"]), float(cis_spec.get("scale", 1.0)))
        m_shr, d = mix([tables[n][1] for n in preds], targets, weights={n: 1.0 for n in preds}, gamma=1.0,
                       reliability_scale=100.0)
        t20 = (np.where(d > 0, m_shr, 0.0) * AMPLITUDE + cis).astype(np.float32)
        ys, ses = [], []
        for n in preds:
            tab = tables[n][0]
            ys.append(tab.rows(targets).astype(np.float64) - tab.common([t for t in panel if t in tab.index()])[None, :])
            ses.append(stage104.source_se(args.cache, tab, targets, G).astype(np.float64))
        expr = np.log1p(np.nanmean(np.vstack([basal[n].to_numpy() for n in preds]), axis=0))
        arms = {"t20like": t20}
        comps = {}
        for label, kcd4 in (("k1", 1.0), ("k2", 2.0)):
            ks = [kcd4 if family(n) == "cd4" else 1.0 for n in preds]
            sigma2, tau2 = variance_components(ys, ses, ks, expr)
            theta = posterior_mean(ys, ses, ks, sigma2, tau2)
            comps[label] = {"sigma2_median": float(np.median(sigma2[gate])), "tau2_median": float(np.median(tau2[gate])),
                            "share_sigma2_gt_tau2": float(np.mean(sigma2[gate] > tau2[gate]))}
            arms[f"eb_{label}_det"], s_det = match_detectable(theta, t20, thr, gate, offset=cis)
            comps[label]["scale_det"] = s_det
            if label == "k2":
                arms["eb_k2_energy"], s_en = match_energy(theta, t20, cis)
                comps[label]["scale_energy"] = s_en
        comp_out.append({"held_out": held, "inputs": preds, **{f"{k}_{kk}": vv for k, v in comps.items() for kk, vv in v.items()}})
        y = truth.raw[np.array([tix[t] for t in targets])].astype(np.float32)
        Zt = y / stage104.source_se(args.cache, truth, targets, G)
        np.savez_compressed(args.save / f"{held}.npz", targets=np.array(targets), truth=y,
                            **{k: v for k, v in arms.items()})
        del ys, ses

        tcols = np.array([col.get(t, -1) for t in targets])
        own = np.zeros((T, G), dtype=bool)
        own[np.arange(T)[tcols >= 0], tcols[tcols >= 0]] = True
        sig = np.isfinite(y) & (np.abs(np.nan_to_num(Zt)) >= 3) & gate[None, :] & ~own
        observed = np.abs(t20) > 0
        keep = np.ones(G, dtype=bool)
        keep[panel_cols] = False
        prec = {name: precision_at(E, y, gate, tcols) for name, E in arms.items()}
        cohort = np.all([np.isfinite(v) for v in prec.values()], axis=0)
        per = {}
        for name, E in arms.items():
            pds_gen, nmae_gen = [], []
            for c in ("A", "B", "C"):
                cpm = basal[c].to_numpy(dtype=float)
                x = 0.05 * cpm
                lv = keep & (cpm > 0)
                Tl = (np.log1p(x * np.exp(np.clip(np.nan_to_num(y), -20, 20))) - np.log1p(x))[:, lv]
                for seed in (1, 2, 3):
                    noisy, _, _ = realise(E, cpm, observed, np.random.default_rng([seed, ord(c)]))
                    D = (np.log1p(x * np.exp(np.clip(noisy, -20, 20))) - np.log1p(x))[:, lv]
                    pds_gen.append(rank_pds(D, Tl))
                    err = np.where(sig, np.abs(noisy - np.nan_to_num(y)), 0.0).sum(axis=1)
                    ref = np.where(sig, np.abs(np.nan_to_num(y)), 0.0).sum(axis=1)
                    nmae_gen.append(np.where(ref > 0, err / np.maximum(ref, 1e-12), np.nan))
            per[name] = {"pds": pds_proxy(E, y, w_eval, panel_cols), "reach": reach_proxy(E, y, Zt, gate, tcols),
                         "prec": prec[name], "pds_gen": np.mean(pds_gen, axis=0), "nmae_gen": np.nanmean(nmae_gen, axis=0),
                         "energy_ratio": float((np.asarray(E, np.float64) ** 2).sum() / (np.asarray(t20, np.float64) ** 2).sum()),
                         "detectable_median": det(E)}
        for name, v in per.items():
            row = {"held_out": held, "arm": name, "targets": T, "line_new": held != "k562",
                   "pds_proxy": float(np.mean(v["pds"])), "reach_proxy": float(np.nanmean(v["reach"])),
                   "prec_200_shared": float(np.nanmean(v["prec"][cohort])), "pds_gen": float(np.mean(v["pds_gen"])),
                   "nmae_gen": float(np.nanmean(v["nmae_gen"])), "energy_ratio": v["energy_ratio"],
                   "detectable_median": v["detectable_median"]}
            if name != "t20like":
                base = per["t20like"]
                for key in ("pds", "reach", "pds_gen", "nmae_gen"):
                    diff = np.asarray(v[key], dtype=np.float64) - np.asarray(base[key], dtype=np.float64)
                    row[f"{key}_minus_t20like"], row[f"{key}_ci95"] = boot(diff[np.isfinite(diff)], brng)
                d, ci = boot((v["prec"] - base["prec"])[cohort], brng)
                row["prec_minus_t20like"], row["prec_ci95"] = d, ci
                combo = W_PDS * (v["pds_gen"] - base["pds_gen"]) - W_NMAE * (v["nmae_gen"] - base["nmae_gen"])
                row["combined_minus_t20like"], row["combined_ci95"] = boot(combo[np.isfinite(combo)], brng)
            rows_out.append(row)
        log(f"{held}: {T} targets evaluated")

    s = pd.DataFrame(rows_out)
    s.to_csv(args.out / "summary.csv", index=False)
    pd.DataFrame(comp_out).to_csv(args.out / "components.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "trasferimento_gerarchico_2026-09-26/eb_bench.py",
                   "claim_type": "effect-space and generator-model proxies against held-out public sources; regime C; "
                                 "variance components from the input sources only; not VCC scores",
                   "saved_predictions": str(args.save), "components": comp_out, "rows": rows_out},
                  fh, indent=1, default=float)
    pd.set_option("display.width", 250)
    cols = ["held_out", "arm", "pds_minus_t20like", "pds_gen_minus_t20like", "pds_gen_ci95", "nmae_gen_minus_t20like",
            "combined_minus_t20like", "combined_ci95", "energy_ratio", "detectable_median"]
    print(s[[c for c in cols if c in s.columns]].round(4).to_string(index=False))
    print(pd.DataFrame(comp_out).round(5).to_string(index=False))


if __name__ == "__main__":
    main()
