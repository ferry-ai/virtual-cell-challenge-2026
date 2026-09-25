"""Third pass: does the cis head's gain survive the generator's profile step and pseudobulk noise?

The production form chosen from r2 (`vcc2026.predictor_sc.CisModel.from_pairs`, median ln fold
change by TSS distance bin from K562 genome-wide pairs without panel targets, 2 x the prior added
within 5 kb, pairs marked observed) is passed, with and without the head, through the model of
the trial-01 profile step and of a 400-cell pseudobulk used by sweep_v2.py (r7) and sweep_v3.py:
clip at 6 log2, compositional shift over observed genes, Poisson-like noise at 20,000 UMI per
cell, in each of A, B and C's basal profiles, seeds 1-3. Measured on held-out public sources,
t16 shape (raw x 0.788) and t19 shape (shrunk x 1.576):

  pds_gen      PDS proxy on log1p pseudobulk deltas (noise_sim.rank_pds, panel genes excluded);
  detectable   median genes per target whose realised |ln fc| clears 4 / sqrt(400 mu) at >= 5 CPM;
  precision    share of detectable genes with the held-out source's sign (target gene excluded);
  head_right   share of targets whose largest realised |ln fc| among held-out genes with
               |raw/se| >= 3 has the held-out sign: the first step of the reach member.
Paired bootstrap over targets for the differences. Proxies, not VCC scores.

    scripts/py.cmd reports/modulo_cis_2026-09-26/cis_generator_check.py --out reports/modulo_cis_2026-09-26/r3
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
sys.path.insert(0, str(HERE))

from cis_bench import DATA, FAMILY, SOURCES, SEED, boot, pooled, stage100, truth_z  # noqa: E402
from noise_sim import N_CELLS, UMI, rank_pds  # noqa: E402
from noise_sim2 import realise  # noqa: E402
from vcc2026.predictor_sc import CisModel, load_coordinates  # noqa: E402

SHAPES = {"t16": ("raw", 0.788), "t19": ("shrunk", 1.576)}
SCALE, DMAX = 2.0, 5000
SEEDS = (1, 2, 3)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "interim/basal_cpm_by_context.csv")
    ap.add_argument("--genes", type=Path, default=DATA / "raw/controls/gene_names.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--pairs", type=Path, default=REPO / "reports/cis_2026-09-17/k562_neighbour_pairs.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)

    axis = pd.read_csv(args.genes)["gene_name"].astype(str).to_numpy()
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    col = {g: i for i, g in enumerate(axis)}
    keep = np.ones(axis.size, dtype=bool)
    keep[[col[g] for g in panel if g in col]] = False
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    pairs = pd.read_csv(args.pairs)
    model = CisModel.from_pairs(pairs[~pairs["target"].astype(str).isin(set(panel))], value="log2fc", log_base=2.0)
    coords = load_coordinates(args.coords)
    nb = {}
    for t in panel:
        pos, dist = model.neighbours(t, axis, coords)
        near = dist < DMAX
        if near.any():
            nb[t] = (pos[near], SCALE * model.prior(dist[near]))

    rows, per = [], []
    rng_b = np.random.default_rng(SEED)
    for held in SOURCES:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = stage100.load_table(args.cache, held, "raw")
        tidx = truth.index()
        base_t = [t for t in panel if t in tidx]
        trans = {shape: pooled(args.cache, preds, base_t, eff) for shape, (eff, _) in SHAPES.items()}
        ok = np.all([np.abs(e).sum(axis=1) > 0 for e, _ in trans.values()], axis=0)
        targets = [t for t, o in zip(base_t, ok) if o]
        T = truth.raw[np.array([tidx[t] for t in targets])].astype(np.float32)
        Z = truth_z(args.cache, held, truth, targets)
        tcols = np.array([col.get(t, -1) for t in targets])
        has_nb = np.array([t in nb for t in targets])
        sig = np.isfinite(Z) & (np.abs(Z) >= 3.0) & keep[None, :]
        for i, c in enumerate(tcols):
            if c >= 0:
                sig[i, c] = False
        for shape, (effect, amp) in SHAPES.items():
            eff, den = trans[shape]
            E0 = (eff[ok] * amp).astype(np.float32)
            obs0 = den[ok] > 0
            E1, obs1 = E0.copy(), obs0.copy()
            for i, t in enumerate(targets):
                if t in nb:
                    pos, val = nb[t]
                    E1[i, pos] += val
                    obs1[i, pos] = True
            res = {}
            for arm, (E, obs) in {"base": (E0, obs0), "cis": (E1, obs1)}.items():
                pds_runs, det, prec, head = [], [], [], []
                for c in ("A", "B", "C"):
                    cpm = basal[c].to_numpy(dtype=float)
                    x = 0.05 * cpm
                    live = keep & (cpm > 0)
                    Tl = (np.log1p(x * np.exp(np.clip(np.nan_to_num(T), -20, 20))) - np.log1p(x))[:, live]
                    mu = cpm * UMI / 1e6
                    thr = np.where(mu > 0, 4.0 / np.sqrt(N_CELLS * np.maximum(mu, 1e-12)), np.inf)
                    gate = cpm >= 5.0
                    for seed in SEEDS:
                        noisy, _, real_ln = realise(E, cpm, obs, np.random.default_rng([seed, ord(c)]))
                        D = (np.log1p(x * np.exp(np.clip(noisy, -20, 20))) - np.log1p(x))[:, live]
                        pds_runs.append(rank_pds(D, Tl))
                        if seed == SEEDS[0]:
                            d = (np.abs(real_ln) > thr[None, :]) & gate[None, :] & keep[None, :] & np.isfinite(T) & (T != 0)
                            det.append(d.sum(axis=1))
                            same = np.sign(real_ln) == np.sign(np.nan_to_num(T))
                            prec.append(np.divide((d & same).sum(axis=1), d.sum(axis=1),
                                                  out=np.full(len(targets), np.nan), where=d.sum(axis=1) > 0))
                            hr = np.full(len(targets), np.nan)
                            for i in range(len(targets)):
                                idx = np.flatnonzero(sig[i] & gate)
                                if idx.size:
                                    j = idx[np.argmax(np.abs(noisy[i, idx]))]
                                    hr[i] = float(np.sign(noisy[i, j]) == np.sign(T[i, j]))
                            head.append(hr)
                res[arm] = {"pds": np.mean(pds_runs, axis=0), "det": np.mean(det, axis=0),
                            "prec": np.nanmean(prec, axis=0), "head": np.nanmean(head, axis=0)}
            for key in ("pds", "prec", "head"):
                diff = res["cis"][key] - res["base"][key]
                mdiff, ci = boot(diff, rng_b)
                rows.append({"held_out": held, "shape": shape, "metric": key, "targets": len(targets),
                             "base": float(np.nanmean(res["base"][key])), "cis": float(np.nanmean(res["cis"][key])),
                             "cis_minus_base": mdiff, "ci95": ci,
                             "minus_base_nb_targets": float(np.nanmean(diff[has_nb])),
                             "targets_with_neighbour": int(has_nb.sum())})
            rows.append({"held_out": held, "shape": shape, "metric": "detectable_median", "targets": len(targets),
                         "base": float(np.median(res["base"]["det"])), "cis": float(np.median(res["cis"]["det"]))})
            for t, a, b in zip(targets, res["base"]["pds"], res["cis"]["pds"]):
                per.append({"held_out": held, "shape": shape, "target": t, "pds_gen_base": float(a),
                            "pds_gen_cis": float(b), "has_neighbour_5kb": t in nb})
            print(held, shape, "done", flush=True)

    s = pd.DataFrame(rows)
    s.to_csv(args.out / "generator_check.csv", index=False)
    pd.DataFrame(per).to_csv(args.out / "per_target.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "modulo_cis_2026-09-26/cis_generator_check.py",
                   "claim_type": "generator-model proxies against held-out public sources; not VCC scores",
                   "cache": str(args.cache), "cis": {"scale": SCALE, "max_distance_bp": DMAX,
                                                     "prior_ln_by_bin": model.by_bin.tolist(),
                                                     "edges_bp": list(model.edges)},
                   "seeds": list(SEEDS), "rows": rows}, f, indent=1)
    pd.set_option("display.width", 220)
    print(s.round(4).to_string())


if __name__ == "__main__":
    main()
