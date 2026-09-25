"""Program layer: do response programs shared across sources transfer better than single genes?

Hypothesis H1 (reports/ipotesi_trasferimento_2026-09-24/IPOTESI.md), in the same-target setting
we can measure: a knockdown moves a few co-regulated programs (translation, mitochondria,
cholesterol, stress, cell cycle...), and the part of a transferred effect that lies on programs
recurring across contexts should carry over better than gene-level detail, which is mostly
source noise (per-target cosine between two sources 0.01-0.05, reports of 25 September).

Leave-one-source-family-out, stage 100's loader and pooling (sweep_v2.pooled), both production
shapes: t16 (raw x 0.788) and t19 (shrunk x 1.576). Programs are learned only from the
predictor sources, never from the held-out one:

  stack_r<r>   right singular vectors of the stacked predictor matrices (each source's panel
               effects minus its mean over targets, as gamma 1 does; unmeasured pairs 0), in the
               scorer's log1p geometry: columns multiplied by w = x/(1+x), x = 0.05 CPM of A/B/C,
               on genes at >= 1 CPM; the prediction is projected on the top r and mapped back by
               1/w; genes under 1 CPM keep their transferred value;
  self_r<r>    the same with the basis of the pooled prediction matrix itself (truncated SVD
               across targets);
  half_stack_r<r> projection plus half of the residual (partial denoising);
  random_r<r>  control: a random orthonormal basis of the same rank on the same genes.
r = 10, 20, 40, 80, 160. Metrics as reports/modulo_cis_2026-09-26/cis_bench.py: PDS proxy,
reach proxy, fidelity proxy at the top 200, weighted squared-error ratio, and the energy the
projection keeps. Paired bootstrap over targets. Effect-space proxies, not VCC scores.

    scripts/py.cmd reports/programmi_2026-09-26/programs_bench.py --out reports/programmi_2026-09-26/r1
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
sys.path.insert(0, str(REPO / "reports" / "modulo_cis_2026-09-26"))

from cis_bench import (DATA, FAMILY, SOURCES, SEED, boot, fidelity_proxy, pds_proxy, pooled,  # noqa: E402
                       reach_proxy, stage100, truth_z)

SHAPES = {"t16": ("raw", 0.788), "t19": ("shrunk", 1.576)}
RANKS = (10, 20, 40, 80, 160)


def centred(tab, targets) -> np.ndarray:
    rows = tab.rows(targets).astype(np.float32)
    rows = rows - tab.common().astype(np.float32)
    return np.nan_to_num(rows, nan=0.0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "interim/basal_cpm_by_context.csv")
    ap.add_argument("--genes", type=Path, default=DATA / "raw/controls/gene_names.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
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
    expr = np.flatnonzero(cpm >= 1.0)
    we = w[expr]
    rng_rand = np.random.default_rng(SEED)

    summary = []
    for held in SOURCES:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = stage100.load_table(args.cache, held, "raw")
        tidx = truth.index()
        base_t = [t for t in panel if t in tidx]
        trans = {}
        for shape, (effect, amp) in SHAPES.items():
            eff, den = pooled(args.cache, preds, base_t, effect)
            trans[shape] = (eff * amp).astype(np.float32)
        ok = np.all([np.abs(e).sum(axis=1) > 0 for e in trans.values()], axis=0)
        targets = [t for t, o in zip(base_t, ok) if o]
        T = truth.raw[np.array([tidx[t] for t in targets])].astype(np.float32)
        Z = truth_z(args.cache, held, truth, targets)
        tcols = np.array([col.get(t, -1) for t in targets])
        valid = np.isfinite(T) & keep[None, :]
        Tw = np.where(valid, T * w, 0.0).astype(np.float32)
        null_t = (Tw.astype(np.float64) ** 2).sum(axis=1)

        def metrics(P):
            pds = pds_proxy(P, T, w, panel_cols)
            reach = reach_proxy(P, T, Z, gate, tcols)
            fid = fidelity_proxy(P, T, Z, gate, tcols)
            Pw = np.where(valid, P * w, 0.0)
            err_t = ((Tw - Pw).astype(np.float64) ** 2).sum(axis=1)
            return pds, reach, fid, err_t

        rng = np.random.default_rng(SEED)
        for shape, (effect, amp) in SHAPES.items():
            E = trans[shape][ok]
            # program bases from the predictor sources only, in the log1p geometry
            stack = []
            for s in preds:
                tab = stage100.load_table(args.cache, s, effect)
                stack.append(centred(tab, [t for t in panel if t in tab.index()])[:, expr] * we)
                del tab
            X = np.vstack(stack)
            del stack
            _, sv_stack, Vt_stack = np.linalg.svd(X, full_matrices=False)
            del X
            Ew = E[:, expr] * we
            _, sv_self, Vt_self = np.linalg.svd(Ew, full_matrices=False)
            ref = metrics(E)
            e_norm = float(np.linalg.norm(Ew))
            arms = {"base": None}
            for r in RANKS:
                arms[f"stack_r{r}"] = ("stack", r)
                arms[f"half_stack_r{r}"] = ("half", r)
                arms[f"self_r{r}"] = ("self", r)
                arms[f"random_r{r}"] = ("random", r)
            for name, spec in arms.items():
                kept = 1.0
                if spec is None:
                    res = ref
                else:
                    kind, r = spec
                    if kind in ("stack", "half"):
                        V = Vt_stack[:r].T
                    elif kind == "self":
                        V = Vt_self[:r].T
                    else:
                        V, _ = np.linalg.qr(rng_rand.standard_normal((expr.size, r)).astype(np.float32))
                    proj = (Ew @ V) @ V.T
                    if kind == "half":
                        proj = proj + 0.5 * (Ew - proj)
                    kept = float(np.linalg.norm(proj) / e_norm)
                    P = E.copy()
                    P[:, expr] = proj / we
                    res = metrics(P)
                    del P, proj
                pds, reach, fid, err_t = res
                row = {"held_out": held, "shape": shape, "arm": name, "targets": len(targets),
                       "pds_proxy": float(np.mean(pds)), "reach_proxy": float(np.nanmean(reach)),
                       "prec_200": float(np.nanmean(fid["prec_200"])), "yield_200": float(np.nanmean(fid["yield_200"])),
                       "mse_ratio": float(err_t.sum() / null_t.sum()), "energy_kept": kept}
                for key, val, rr in (("pds", pds, ref[0]), ("reach", reach, ref[1])):
                    mdiff, ci95 = boot(val - rr, rng) if spec is not None else (0.0, [0.0, 0.0])
                    row[f"{key}_minus_base"] = mdiff
                    row[f"{key}_minus_base_ci95"] = ci95
                summary.append(row)
            print(held, shape, "done", flush=True)

    s = pd.DataFrame(summary)
    s.to_csv(args.out / "summary.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "programmi_2026-09-26/programs_bench.py",
                   "claim_type": "effect-space proxies against held-out public sources, one target set per held-out "
                                 "source, bases learned on predictor sources only, paired bootstrap over targets; "
                                 "not VCC scores",
                   "cache": str(args.cache), "seed": SEED, "ranks": list(RANKS), "genes_projected": int(expr.size),
                   "summary": s.to_dict("records")}, f, indent=1)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    cols = ["held_out", "shape", "arm", "pds_proxy", "pds_minus_base", "pds_minus_base_ci95", "reach_proxy",
            "reach_minus_base", "prec_200", "mse_ratio", "energy_kept"]
    print(s[cols].round(4).to_string())


if __name__ == "__main__":
    main()
