"""Does adding HEK293T (all four genome-scale sources) to the t20 recipe help on held-out public sources?

The t20 recipe pools K562, CD4 and HCT116. HEK293T (X-Atlas/Orion, same study as HCT116) covers 281
panel targets and is not in it. On the held-out sources that leave both Orion lines as inputs (K562
and CD4), this compares the t20 shape with three inputs against four:

  t20like_3     the recipe's inputs minus the held-out one (K562 out: CD4 + HCT116; CD4 out: K562 + HCT116)
  hek_equal     the same plus HEK293T at weight 1
  hek_half      the same plus HEK293T, the two Orion lines at weight 0.5 each (one weight per study)

all as the recipe: stage-98 shrunk effects, `mix` with gamma 1 and reliability n / (n + 100), times
1.576, plus the cis head of configs/recipes/t20.json. Proxies as reports/trasferimento_appreso_2026-09-26/
r5: PDS, reach, precision in effect space; PDS and nMAE after the trial-01 profile step and a 400-cell
pseudobulk; the combined difference 0.36 dPDS_gen - 0.27 dnMAE_gen. Not VCC scores.

    scripts/py.cmd reports/quattro_sorgenti_2026-09-26/four_sources_bench.py --out reports/quattro_sorgenti_2026-09-26/r1
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
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
from vcc2026.transfer_model import detectable_threshold  # noqa: E402

_spec = importlib.util.spec_from_file_location("stage104", REPO / "scripts" / "104_learned_reweighting.py")
stage104 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage104)

AMPLITUDE = 1.576
W_PDS, W_NMAE = 0.36, 0.27
TASKS = {"k562": ["cd4_mix", "orion_hct116"], "cd4_mix": ["k562", "orion_hct116"]}
ARMS = {"t20like_3": {}, "hek_equal": {"orion_hek293t": 1.0},
        "hek_half": {"orion_hek293t": 0.5, "orion_hct116": 0.5}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--recipe", type=Path, default=REPO / "configs/recipes/t20.json")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
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
    names = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]
    tables = {n: stage104.load(args.cache, n) for n in names}
    keep = np.ones(G, dtype=bool)
    keep[panel_cols] = False
    rows_out = []
    brng = np.random.default_rng(SEED)
    for held, base_inputs in TASKS.items():
        truth = tables[held][0]
        tix = truth.index()
        inputs_all = base_inputs + ["orion_hek293t"]
        # the same targets for every arm: covered by the three-input recipe
        targets = [t for t in panel if t in tix and any(t in tables[n][0].index() for n in base_inputs)]
        T = len(targets)
        cis = np.zeros((T, G), dtype=np.float32)
        add_cis(cis, np.zeros((T, G), dtype=bool), targets, axis, cis_model, coords,
                int(cis_spec["max_distance_bp"]), float(cis_spec.get("scale", 1.0)))
        arms = {}
        for arm, extra in ARMS.items():
            weights = {n: 1.0 for n in base_inputs}
            weights.update(extra)
            used = [n for n in inputs_all if weights.get(n, 0) > 0]
            m, d = mix([tables[n][1] for n in used], targets, weights=weights, gamma=1.0, reliability_scale=100.0)
            arms[arm] = (np.where(d > 0, m, 0.0) * AMPLITUDE + cis).astype(np.float32)
        y = truth.raw[np.array([tix[t] for t in targets])].astype(np.float32)
        Zt = y / stage104.source_se(args.cache, truth, targets, G)
        tcols = np.array([col.get(t, -1) for t in targets])
        own = np.zeros((T, G), dtype=bool)
        own[np.arange(T)[tcols >= 0], tcols[tcols >= 0]] = True
        sig = np.isfinite(y) & (np.abs(np.nan_to_num(Zt)) >= 3) & gate[None, :] & ~own
        observed = np.abs(arms["t20like_3"]) > 0
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
                         "detectable_median": det(E)}
        for name, v in per.items():
            row = {"held_out": held, "arm": name, "targets": T, "pds_proxy": float(np.mean(v["pds"])),
                   "reach_proxy": float(np.nanmean(v["reach"])), "prec_200_shared": float(np.nanmean(v["prec"][cohort])),
                   "pds_gen": float(np.mean(v["pds_gen"])), "nmae_gen": float(np.nanmean(v["nmae_gen"])),
                   "detectable_median": v["detectable_median"]}
            if name != "t20like_3":
                base = per["t20like_3"]
                for key in ("pds", "reach", "pds_gen", "nmae_gen"):
                    diff = np.asarray(v[key], dtype=np.float64) - np.asarray(base[key], dtype=np.float64)
                    row[f"{key}_minus_base"], row[f"{key}_ci95"] = boot(diff[np.isfinite(diff)], brng)
                combo = W_PDS * (v["pds_gen"] - base["pds_gen"]) - W_NMAE * (v["nmae_gen"] - base["nmae_gen"])
                row["combined_minus_base"], row["combined_ci95"] = boot(combo[np.isfinite(combo)], brng)
            rows_out.append(row)
        print(held, "done", flush=True)
    s = pd.DataFrame(rows_out)
    s.to_csv(args.out / "summary.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "quattro_sorgenti_2026-09-26/four_sources_bench.py",
                   "claim_type": "effect-space and generator-model proxies against held-out public sources; not VCC scores",
                   "rows": rows_out}, fh, indent=1, default=float)
    pd.set_option("display.width", 250)
    cols = ["held_out", "arm", "pds_minus_base", "pds_gen_minus_base", "pds_gen_ci95", "nmae_gen_minus_base",
            "combined_minus_base", "combined_ci95", "reach_minus_base", "detectable_median"]
    print(s[[c for c in cols if c in s.columns]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
