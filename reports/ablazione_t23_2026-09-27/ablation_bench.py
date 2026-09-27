"""t23 taken apart on the panel: gene exclusion, per-gene weighting and rescaling, each against the others.

t23 is t22 with its transferred part multiplied gene by gene by the shared share sigma2 / (sigma2 + tau2)
and rescaled to t22's median count of detectable genes. Of the 18,533 genes, 8,247 get share 0 (the
universes cannot estimate them), 8,395 get 1 and 1,891 fall in between: t23 mixes an exclusion, a
weighting and a rescaling, and the panel bench that produced it (reports/quota_condivisa_2026-09-27/,
share_panel_bench.py, r1) compared only the whole against t22. This bench keeps that bench's code path
(`shared_share`, `mix`, the cis head, the proxies, the seeds) and adds the arms that separate the parts:
* `t22like`: t22's shape without H's family;
* `excl`: the transferred part with the share-0 genes set to 0 and every other gene kept at 1, rescaled
  with `match_detectable` to t22like's detectable genes, plus the cis head;
* `excl_noscale`: the same exclusion, not rescaled;
* `share`: the t23 arm of share_panel_bench (weighting, rescaled);
* `share_noscale`: the weighting, not rescaled.
The shares are recomputed exactly as in share_panel_bench r1 (same universes, seed and order) and checked
against the ones r1 saved, when their folder is given. Besides each arm against t22like, the combined
proxy difference 0.36 dPDS_gen - 0.27 dnMAE_gen is bootstrapped for share - excl, share - share_noscale and
excl - excl_noscale, paired over the panel targets. Not VCC scores.

    scripts/py.cmd reports/ablazione_t23_2026-09-27/ablation_bench.py --out reports/ablazione_t23_2026-09-27/r1 \
        --universe k562=<dir> --universe cd4_mix=<dir> --universe orion_hct116=<dir> \
        --check-shares reports/quota_condivisa_2026-09-27/r1
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "reports" / "quota_condivisa_2026-09-27"))

from share_panel_bench import (  # noqa: E402
    AMPLITUDE, DATA, SEED, T22_SOURCES, W_NMAE, W_PDS, Universe, add_cis, boot, cis_prior, detectable_threshold,
    family, load_coordinates, match_detectable, mix, official_axis, pds_proxy, precision_at, rank_pds, reach_proxy,
    realise, shared_share, stage104,
)

PAIRS = [("share", "excl"), ("share", "share_noscale"), ("excl", "excl_noscale")]


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
    ap.add_argument("--check-shares", type=Path, default=None, help="a share_panel_bench output folder to compare with")
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
    cis_model = cis_prior(pd.read_csv(REPO / cis_spec["pairs"]), panel)
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
        same = None
        if args.check_shares is not None:
            ref = args.check_shares / f"share_{held}.npy"
            same = bool(ref.exists() and np.array_equal(np.load(ref), share))
        log(f"{held}: share from {info}; identical to the saved one: {same}")
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
        excl_w = (share > 0).astype(np.float32)
        arm_share, scale_share = match_detectable(tx * share[None, :], base, thr, gate, offset=cis)
        arm_excl, scale_excl = match_detectable(tx * excl_w[None, :], base, thr, gate, offset=cis)
        arms = {"t22like": base, "excl": arm_excl, "excl_noscale": (tx * excl_w[None, :] + cis).astype(np.float32),
                "share": arm_share, "share_noscale": (tx * share[None, :] + cis).astype(np.float32)}
        scales = {"excl": scale_excl, "share": scale_share}
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
                    ref_ = np.where(sig, np.abs(np.nan_to_num(y)), 0.0).sum(axis=1)
                    nmae_gen.append(np.where(ref_ > 0, err / np.maximum(ref_, 1e-12), np.nan))
            per[name] = {"pds": pds_proxy(E, y, w_eval, panel_cols), "reach": reach_proxy(E, y, Zt, gate, tcols),
                         "prec": prec[name], "pds_gen": np.mean(pds_gen, axis=0), "nmae_gen": np.nanmean(nmae_gen, axis=0),
                         "energy_ratio": float((np.asarray(E, np.float64) ** 2).sum() / (np.asarray(base, np.float64) ** 2).sum()),
                         "detectable_median": det(E)}
            log(f"{held}: {name} evaluated")
        combo = {k: W_PDS * v["pds_gen"] - W_NMAE * v["nmae_gen"] for k, v in per.items()}
        brng = np.random.default_rng([SEED, len(runs)])
        for name, v in per.items():
            row = {"held_out": held, "arm": name, "against": "t22like", "targets": T,
                   "pds_proxy": float(np.mean(v["pds"])), "reach_proxy": float(np.nanmean(v["reach"])),
                   "prec_200_shared": float(np.nanmean(v["prec"][cohort])), "pds_gen": float(np.mean(v["pds_gen"])),
                   "nmae_gen": float(np.nanmean(v["nmae_gen"])), "energy_ratio": v["energy_ratio"],
                   "detectable_median": v["detectable_median"], "scale": scales.get(name, 1.0)}
            if name != "t22like":
                b = per["t22like"]
                for key in ("pds", "reach", "pds_gen", "nmae_gen"):
                    diff = np.asarray(v[key], dtype=np.float64) - np.asarray(b[key], dtype=np.float64)
                    row[f"{key}_minus_base"], row[f"{key}_ci95"] = boot(diff[np.isfinite(diff)], brng)
                diff = combo[name] - combo["t22like"]
                row["combined_minus_base"], row["combined_ci95"] = boot(diff[np.isfinite(diff)], brng)
            rows_out.append(row)
        for a, b in PAIRS:
            diff = combo[a] - combo[b]
            est, ci = boot(diff[np.isfinite(diff)], brng)
            rows_out.append({"held_out": held, "arm": a, "against": b, "targets": T,
                             "combined_minus_base": est, "combined_ci95": ci})
        runs.append({"held_out": held, "inputs": inputs, "targets": T, "share_identical_to_saved": same,
                     "genes_share_zero": int((share == 0).sum()), "genes_share_one": int((share == 1).sum()),
                     **{f"share_{k}": v for k, v in info.items()}})
    s = pd.DataFrame(rows_out)
    s.to_csv(args.out / "summary.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "ablazione_t23_2026-09-27/ablation_bench.py", "cache": str(args.cache),
                   "claim_type": "effect-space and generator-model proxies against held-out public sources on the panel; "
                                 "not VCC scores", "runs": runs, "rows": rows_out}, fh, indent=1, default=float)
    pd.set_option("display.width", 250)
    cols = ["held_out", "arm", "against", "targets", "combined_minus_base", "combined_ci95", "pds_gen", "nmae_gen",
            "energy_ratio", "detectable_median", "scale"]
    print(s[[c for c in cols if c in s.columns]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
