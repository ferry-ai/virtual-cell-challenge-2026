"""Second pass of the cis head: the forms production can use, and the sources' own cis values.

`cis_bench.py` (r1) tried a mean-by-bin prior with orientation. Production would go through the
live `vcc2026.predictor_sc.CisModel.from_pairs` (median by bin, bins 0/1/2/5/10/20 kb, no
orientation), the prior stages 75 and 76 already use, fitted on the same K562 pairs with the
panel targets removed. This pass measures, on the same held-out benches and target sets:

  base            transferred effects (t16 shape raw x 0.788, t19 shape shrunk x 1.576);
  cis_med_add<k>  neighbours within D get k x the CisModel median prior on top (k = 1, 2, 4);
  cis_mean_add<k> the same with the r1 mean prior without orientation (k = 1, 2);
  cis_meas        neighbours within D that a source measured get the pooled RAW value with no
                  amplitude (a direct effect is not the trans part's calibration target); the
                  others get the median prior;
  cis_shuffled    control for cis_med_add2: the same values on another target's neighbour set.
r1 found that replacing the transferred value with the prior loses and adding it gains, so this
pass doses the added prior. D = 2 and 5 kb. Same metrics as r1. Effect-space proxies, not VCC
scores.

    scripts/py.cmd reports/modulo_cis_2026-09-26/cis_bench2.py --out reports/modulo_cis_2026-09-26/r2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cis_bench import (DATA, FAMILY, REPO, SOURCES, SEED, boot, fidelity_proxy, pds_proxy,  # noqa: E402
                       pooled, reach_proxy, stage100, truth_z)
from vcc2026.predictor_sc import CisModel, load_coordinates  # noqa: E402

DMAX = (2000, 5000)
SHAPES = {"t16": ("raw", 0.788), "t19": ("shrunk", 1.576)}


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
    panel_cols = np.array([col[g] for g in panel if g in col])
    keep = np.ones(axis.size, dtype=bool)
    keep[panel_cols] = False
    cpm = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)[["A", "B", "C"]].mean(axis=1).to_numpy()
    x = 0.05 * cpm
    w = (x / (1.0 + x)).astype(np.float32)
    gate = cpm >= 5.0

    coords = load_coordinates(args.coords)
    pairs = pd.read_csv(args.pairs)
    pairs = pairs[~pairs["target"].astype(str).isin(set(panel))]
    med = CisModel.from_pairs(pairs, value="log2fc", log_base=2.0)
    b = np.searchsorted(med.edges, pairs["dist"].to_numpy(), side="right") - 1
    v = pairs["log2fc"].to_numpy() * np.log(2.0)
    mean_bins = np.array([v[b == k].mean() if np.any(b == k) else 0.0 for k in range(len(med.edges) - 1)])
    prior_info = {"edges": list(med.edges), "median_ln": med.by_bin.tolist(), "mean_ln": mean_bins.tolist(),
                  "n": med.n_by_bin.tolist(), "pairs_non_panel": int(len(pairs))}
    print(prior_info, flush=True)

    # neighbours of every panel target on the axis, with distance
    nb_rows = []
    for t in panel:
        pos, dist = med.neighbours(t, axis, coords)
        for p, d in zip(pos, dist):
            nb_rows.append((t, int(p), int(d)))
    nb_all = pd.DataFrame(nb_rows, columns=["target", "col", "dist"])
    kb = np.searchsorted(med.edges, nb_all["dist"].to_numpy(), side="right") - 1
    nb_all["med_ln"] = med.by_bin[kb]
    nb_all["mean_ln"] = mean_bins[kb]

    rng_shuf = np.random.default_rng(SEED)
    summary = []
    for held in SOURCES:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = stage100.load_table(args.cache, held, "raw")
        tidx = truth.index()
        base_t = [t for t in panel if t in tidx]
        trans, rawpool = {}, None
        for shape, (effect, amp) in SHAPES.items():
            eff, den = pooled(args.cache, preds, base_t, effect)
            trans[shape] = ((eff * amp).astype(np.float32), den)
            if effect == "raw":
                rawpool = (eff.astype(np.float32), den)
        ok = np.all([np.abs(e).sum(axis=1) > 0 for e, _ in trans.values()], axis=0)
        targets = [t for t, o in zip(base_t, ok) if o]
        T = truth.raw[np.array([tidx[t] for t in targets])].astype(np.float32)
        Z = truth_z(args.cache, held, truth, targets)
        tcols = np.array([col.get(t, -1) for t in targets])
        trow = {t: i for i, t in enumerate(targets)}
        valid = np.isfinite(T) & keep[None, :]
        Tw = np.where(valid, T * w, 0.0).astype(np.float32)
        null_t = (Tw.astype(np.float64) ** 2).sum(axis=1)
        R, Rden = rawpool[0][ok], rawpool[1][ok]

        def metrics(P):
            pds = pds_proxy(P, T, w, panel_cols)
            reach = reach_proxy(P, T, Z, gate, tcols)
            fid = fidelity_proxy(P, T, Z, gate, tcols)
            Pw = np.where(valid, P * w, 0.0)
            err_t = ((Tw - Pw).astype(np.float64) ** 2).sum(axis=1)
            return pds, reach, fid, err_t

        per_d = {}
        for d in DMAX:
            nb = nb_all[(nb_all["dist"] < d) & nb_all["target"].isin(trow)]
            ri = np.array([trow[t] for t in nb["target"]], dtype=int)
            ci = nb["col"].to_numpy(dtype=int)
            owners = sorted(set(ri.tolist()))
            perm = list(owners)
            for _ in range(50):
                rng_shuf.shuffle(perm)
                if all(a != c for a, c in zip(owners, perm)):
                    break
            remap = dict(zip(owners, perm))
            meas = Rden[ri, ci] > 0
            cis_meas = np.where(meas, R[ri, ci], nb["med_ln"].to_numpy())
            per_d[d] = {"ri": ri, "ci": ci, "ri_shuf": np.array([remap[r] for r in ri], dtype=int),
                        "med": nb["med_ln"].to_numpy(), "mean": nb["mean_ln"].to_numpy(), "meas": cis_meas,
                        "n_measured": int(meas.sum()), "n_pairs": int(ri.size), "n_targets": len(owners)}

        rng = np.random.default_rng(SEED)
        for shape in SHAPES:
            E = trans[shape][0][ok]
            ref = metrics(E)
            arms = {"base": None}
            for d in DMAX:
                for kind in ("med_add1", "med_add2", "med_add4", "mean_add1", "mean_add2", "meas", "shuffled"):
                    arms[f"cis_{kind}_{d // 1000}kb"] = (kind, d)
            has_nb = np.zeros(len(targets), dtype=bool)
            has_nb[per_d[5000]["ri"]] = True
            for name, spec in arms.items():
                if spec is None:
                    res = ref
                else:
                    kind, d = spec
                    q = per_d[d]
                    P = E.copy()
                    if kind.startswith("med_add"):
                        np.add.at(P, (q["ri"], q["ci"]), float(kind[-1]) * q["med"])
                    elif kind.startswith("mean_add"):
                        np.add.at(P, (q["ri"], q["ci"]), float(kind[-1]) * q["mean"])
                    elif kind == "meas":
                        P[q["ri"], q["ci"]] = q["meas"]
                    elif kind == "shuffled":
                        np.add.at(P, (q["ri_shuf"], q["ci"]), 2.0 * q["med"])
                    res = metrics(P)
                    del P
                pds, reach, fid, err_t = res
                row = {"held_out": held, "shape": shape, "arm": name, "targets": len(targets),
                       "pds_proxy": float(np.mean(pds)), "reach_proxy": float(np.nanmean(reach)),
                       "prec_200": float(np.nanmean(fid["prec_200"])), "yield_200": float(np.nanmean(fid["yield_200"])),
                       "mse_ratio": float(err_t.sum() / null_t.sum())}
                for key, val, r in (("pds", pds, ref[0]), ("reach", reach, ref[1])):
                    mdiff, ci95 = boot(val - r, rng) if spec is not None else (0.0, [0.0, 0.0])
                    row[f"{key}_minus_base"] = mdiff
                    row[f"{key}_minus_base_ci95"] = ci95
                    row[f"{key}_minus_base_nb_targets"] = float(np.nanmean((val - r)[has_nb])) if spec is not None else 0.0
                if spec is not None:
                    q = per_d[spec[1]]
                    row.update({"pairs": q["n_pairs"], "pairs_measured": q["n_measured"], "targets_with_pair": q["n_targets"]})
                summary.append(row)
        print(held, "done", flush=True)

    s = pd.DataFrame(summary)
    s.to_csv(args.out / "summary.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "modulo_cis_2026-09-26/cis_bench2.py",
                   "claim_type": "effect-space proxies against held-out public sources, one target set per held-out "
                                 "source, paired bootstrap over targets; not VCC scores",
                   "cache": str(args.cache), "seed": SEED, "prior": prior_info, "summary": s.to_dict("records")},
                  f, indent=1)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    cols = ["held_out", "shape", "arm", "pds_proxy", "pds_minus_base", "pds_minus_base_ci95", "reach_proxy",
            "reach_minus_base", "reach_minus_base_ci95", "prec_200", "mse_ratio"]
    print(s[cols].round(4).to_string())


if __name__ == "__main__":
    main()
