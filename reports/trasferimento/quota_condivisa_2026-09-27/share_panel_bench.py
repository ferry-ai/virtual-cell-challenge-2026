"""The atlas's closest arm, on the panel: t22's transferred part weighted per gene by the share of the response the lines have in common.

Atlas r1 (reports/trasferimento/atlante_2026-09-26/RISULTATI.md) found no arm passing its rule; the closest was
`share_atlas`: t22's transferred part times sigma2 / (sigma2 + tau2) per gene, sigma2 the variance the
lines share and tau2 the line's own, both estimated by moments over thousands of targets outside the
panel, then scaled to t22's median count of detectable genes. It was +0.008 and +0.009 with CD4 and
HCT116 held out, -0.0002 with K562 held out. This tests the same arm on the 300 panel targets, which the
atlas never used: for each held-out public source H (its family out of everything),
* the variances come from the genome-wide universes of the other families only (at most 6,000 targets
  outside the panel measured in at least two of them, seeded), with the atlas bench's own code path
  (`atlas_bench.Universe` and `blend`; CD4's SE variance x 2), and nothing of H;
* `t22like`: the t22 recipe's shape on the stage-98 panel cache (equal-weight `mix` of shrunk effects of
  the t22 sources minus H's family, gamma 1, reliability n/(n+100), x 1.576, plus the cis head);
* `share`: t22like's transferred part times the share, scaled with `match_detectable` to t22like's
  median count of detectable genes, plus the same cis head;
* proxies as reports/trasferimento/quattro_sorgenti_2026-09-26: PDS, reach and sign precision at 200 in effect space;
  PDS and nMAE after the trial-01 profile step and a 400-cell pseudobulk (A/B/C basal, 3 seeds); the
  combined difference 0.36 dPDS_gen - 0.27 dnMAE_gen, paired bootstrap over the panel targets.
Not VCC scores.

    scripts/py.cmd reports/trasferimento/quota_condivisa_2026-09-27/share_panel_bench.py --out reports/trasferimento/quota_condivisa_2026-09-27/r1 \
        --universe k562=<dir> --universe cd4_mix=<dir> --universe orion_hct116=<dir>
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
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "trasferimento" / "modulo_cis_2026-09-26"))
sys.path.insert(0, str(REPO / "reports" / "trasferimento" / "banco_varianti_2026-09-25"))
sys.path.insert(0, str(REPO / "reports" / "trasferimento" / "trasferimento_appreso_2026-09-26"))
sys.path.insert(0, str(REPO / "reports" / "trasferimento" / "atlante_2026-09-26"))

from atlas_bench import BLOCK, Universe, blend, family  # noqa: E402
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

AMPLITUDE = 1.576
W_PDS, W_NMAE = 0.36, 0.27
T22_SOURCES = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]


from vcc2026.config import repo_file  # noqa: E402


def shared_share(unis: dict, inputs: list[str], panel: set, basal: pd.DataFrame, G: int, cd4_k: float,
                 max_targets: int, rng) -> tuple[np.ndarray, dict]:
    """sigma2 / (sigma2 + tau2) per gene from the universes in ``inputs``, over targets outside the panel
    measured in at least two of them: the moments and the blend of atlas_bench, centred per source."""
    ks = [cd4_k if family(n) == "cd4" else 1.0 for n in inputs]
    count = {}
    for n in inputs:
        for t in unis[n].targets:
            count[t] = count.get(t, 0) + 1
    est = sorted(t for t, c in count.items() if c >= 2 and t not in panel)
    if len(est) > max_targets:
        est = sorted(rng.choice(est, size=max_targets, replace=False).tolist())
    expr = np.log1p(np.nanmean(np.vstack([basal[n].to_numpy(dtype=float) for n in inputs]), axis=0))

    def block(part):
        ys, ses = [], []
        for n in inputs:
            have = [t for t in part if t in unis[n].targets]
            y = np.full((len(part), G), np.nan, dtype=np.float32)
            se = np.full((len(part), G), np.nan, dtype=np.float32)
            if have:
                tab = unis[n].table(have)
                ix = tab.index()
                for i, t in enumerate(part):
                    if t in ix:
                        y[i], se[i] = tab.raw[ix[t]], tab.se[ix[t]]
            ys.append(y)
            ses.append(se)
        return ys, ses

    tot = {n: np.zeros(G) for n in inputs}
    cnt = {n: np.zeros(G) for n in inputs}
    for b0 in range(0, len(est), BLOCK):
        ys, _ = block(est[b0:b0 + BLOCK])
        for n, y in zip(inputs, ys):
            tot[n] += np.nansum(y, axis=0, dtype=np.float64)
            cnt[n] += np.isfinite(y).sum(axis=0)
    centre = {n: np.divide(tot[n], cnt[n], out=np.zeros(G), where=cnt[n] > 0) for n in inputs}
    s_num, s_den, ex, n_ex, pair_t, obs_t = (np.zeros(G) for _ in range(6))
    for b0 in range(0, len(est), BLOCK):
        part = est[b0:b0 + BLOCK]
        ys, ses = block(part)
        ys = [y - centre[n][None, :] for n, y in zip(inputs, ys)]
        ses = [se.astype(np.float64) for se in ses]
        pair_any = np.zeros((len(part), G), dtype=bool)
        for i in range(len(ys)):
            for j in range(i + 1, len(ys)):
                ok = np.isfinite(ys[i]) & np.isfinite(ys[j])
                s_num += np.where(ok, ys[i] * ys[j], 0.0).sum(axis=0)
                s_den += ok.sum(axis=0)
                pair_any |= ok
        obs_any = np.zeros((len(part), G), dtype=bool)
        for y, se, k in zip(ys, ses, ks):
            ok = np.isfinite(y) & np.isfinite(se)
            ex += np.where(ok, y * y - k * se * se, 0.0).sum(axis=0)
            n_ex += ok.sum(axis=0)
            obs_any |= ok
        pair_t += pair_any.sum(axis=0)
        obs_t += obs_any.sum(axis=0)
    sigma2_raw = np.divide(s_num, s_den, out=np.zeros(G), where=s_den > 0)
    tau2_raw = np.divide(ex, n_ex, out=np.zeros(G), where=n_ex > 0) - sigma2_raw
    has = (s_den > 0) & (n_ex > 0) & np.isfinite(expr)
    sigma2 = blend(np.maximum(sigma2_raw, 0.0), pair_t, expr, has)
    tau2 = blend(np.maximum(tau2_raw, 0.0), obs_t, expr, has)
    share = np.divide(sigma2, sigma2 + tau2, out=np.zeros(G), where=(sigma2 + tau2) > 0).astype(np.float32)
    info = {"inputs": inputs, "estimation_targets": len(est), "share_median": float(np.median(share[has])),
            "share_below_0.5": float(np.mean(share[has] < 0.5)), "genes_with_moments": int(has.sum())}
    return share, info


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", action="append", required=True, metavar="NAME=DIR")
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--recipe", type=Path, default=REPO / "configs/recipes/t22.json")
    ap.add_argument("--max-estimation-targets", type=int, default=6000)
    ap.add_argument("--cd4-se-factor", type=float, default=2.0)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:7.0f}s] {m}", flush=True)  # noqa: E731
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
    cis_model = cis_prior(pd.read_csv(repo_file(cis_spec["pairs"])), panel)
    coords = load_coordinates(args.coords)
    unis = {}
    for spec in args.universe:
        name, _, folder = spec.partition("=")
        unis[name] = Universe(name, Path(folder))
        log(f"universe {name}: {len(unis[name].targets)} targets")
    tables = {n: stage104.load(args.cache, n) for n in T22_SOURCES}
    keep = np.ones(G, dtype=bool)
    keep[panel_cols] = False
    rng = np.random.default_rng(SEED)
    rows_out, runs = [], []
    for held in T22_SOURCES:
        uni_inputs = [n for n in unis if family(n) != family(held)]
        if len(uni_inputs) < 2:
            log(f"{held}: fewer than two universes outside its family, skipped")
            continue
        share, info = shared_share(unis, uni_inputs, set(panel), basal, G, args.cd4_se_factor,
                                   args.max_estimation_targets, rng)
        log(f"{held}: share from {info}")
        inputs = [n for n in T22_SOURCES if family(n) != family(held)]
        truth = tables[held][0]
        tix = truth.index()
        targets = [t for t in panel if t in tix and any(t in tables[n][0].index() for n in inputs)]
        T = len(targets)
        cis = np.zeros((T, G), dtype=np.float32)
        add_cis(cis, np.zeros((T, G), dtype=bool), targets, axis, cis_model, coords,
                int(cis_spec["max_distance_bp"]), float(cis_spec.get("scale", 1.0)))
        m, d = mix([tables[n][1] for n in inputs], targets, weights={n: 1.0 for n in inputs}, gamma=1.0,
                   reliability_scale=100.0)
        tx = (np.where(d > 0, m, 0.0) * AMPLITUDE).astype(np.float32)
        base = (tx + cis).astype(np.float32)
        arm, scale = match_detectable(tx * share[None, :], base, thr, gate, offset=cis)
        arms = {"t22like": base, "share": arm}
        y = truth.raw[np.array([tix[t] for t in targets])].astype(np.float32)
        Zt = y / stage104.source_se(args.cache, truth, targets, G)
        tcols = np.array([col.get(t, -1) for t in targets])
        own = np.zeros((T, G), dtype=bool)
        own[np.arange(T)[tcols >= 0], tcols[tcols >= 0]] = True
        sig = np.isfinite(y) & (np.abs(np.nan_to_num(Zt)) >= 3) & gate[None, :] & ~own
        observed = np.abs(base) > 0
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
                    noisy, _, _ = realise(E, cpm, observed | (np.abs(E) > 0), np.random.default_rng([seed, ord(c)]))
                    D = (np.log1p(x * np.exp(np.clip(noisy, -20, 20))) - np.log1p(x))[:, lv]
                    pds_gen.append(rank_pds(D, Tl))
                    err = np.where(sig, np.abs(noisy - np.nan_to_num(y)), 0.0).sum(axis=1)
                    ref = np.where(sig, np.abs(np.nan_to_num(y)), 0.0).sum(axis=1)
                    nmae_gen.append(np.where(ref > 0, err / np.maximum(ref, 1e-12), np.nan))
            per[name] = {"pds": pds_proxy(E, y, w_eval, panel_cols), "reach": reach_proxy(E, y, Zt, gate, tcols),
                         "prec": prec[name], "pds_gen": np.mean(pds_gen, axis=0), "nmae_gen": np.nanmean(nmae_gen, axis=0),
                         "energy_ratio": float((np.asarray(E, np.float64) ** 2).sum() / (np.asarray(base, np.float64) ** 2).sum()),
                         "detectable_median": det(E)}
        brng = np.random.default_rng([SEED, len(rows_out)])
        for name, v in per.items():
            row = {"held_out": held, "arm": name, "targets": T, "pds_proxy": float(np.mean(v["pds"])),
                   "reach_proxy": float(np.nanmean(v["reach"])), "prec_200_shared": float(np.nanmean(v["prec"][cohort])),
                   "pds_gen": float(np.mean(v["pds_gen"])), "nmae_gen": float(np.nanmean(v["nmae_gen"])),
                   "energy_ratio": v["energy_ratio"], "detectable_median": v["detectable_median"]}
            if name != "t22like":
                b = per["t22like"]
                for key in ("pds", "reach", "pds_gen", "nmae_gen"):
                    diff = np.asarray(v[key], dtype=np.float64) - np.asarray(b[key], dtype=np.float64)
                    row[f"{key}_minus_base"], row[f"{key}_ci95"] = boot(diff[np.isfinite(diff)], brng)
                combo = W_PDS * (v["pds_gen"] - b["pds_gen"]) - W_NMAE * (v["nmae_gen"] - b["nmae_gen"])
                row["combined_minus_base"], row["combined_ci95"] = boot(combo[np.isfinite(combo)], brng)
                row["scale"] = scale
            rows_out.append(row)
        runs.append({"held_out": held, "inputs": inputs, "targets": T, **{f"share_{k}": v for k, v in info.items()}})
        np.save(args.out / f"share_{held}.npy", share)
        log(f"{held}: evaluated")
    s = pd.DataFrame(rows_out)
    s.to_csv(args.out / "summary.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "quota_condivisa_2026-09-27/share_panel_bench.py",
                   "claim_type": "effect-space and generator-model proxies against held-out public sources on the panel; "
                                 "not VCC scores", "runs": runs, "rows": rows_out}, fh, indent=1, default=float)
    pd.set_option("display.width", 250)
    cols = ["held_out", "arm", "targets", "pds_gen", "nmae_gen", "combined_minus_base", "combined_ci95", "pds_minus_base",
            "reach_minus_base", "energy_ratio", "detectable_median"]
    print(s[[c for c in cols if c in s.columns]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
