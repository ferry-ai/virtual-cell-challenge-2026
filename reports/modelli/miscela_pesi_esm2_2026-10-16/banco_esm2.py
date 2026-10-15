"""Weight of the ta 42 mixture and ESM2 as third ingredient, on the lineage-excluded folds (README.md in this folder).

Same folds, targets, network refits (seeds 2-6) and measures as rete_su_t3_2026-10-15/banco_t3.py.
Part A (weight), four folds, all panel targets each fold measures:
  ens_w = w t3 + (1 - w) rete_c at unit norm, w in (0.4, 0.5, 0.6, 0.7, 0.8); reference ens_0.7 (ta 42).
Part B (ESM2), folds K562 and iPSC only, on the 66 targets Davide's ESM2 + ridge predicts in regime J (target hidden from
training; public datasets davideferrante11/vcc-p3-esm2b-j-{k562,ipsc}-c2-r1, file J-<fold>_E2b.npz, the E2b variant
td 40 used as fallback):
  e2b alone; mix3e_w = 0.7 (1 - w) t3 + 0.3 (1 - w) rete_c + w e2b, w in (0.1, 0.2, 0.3); reference ens_0.7 on the
  same targets. The residual of rete_c is centred over all the fold's targets, as in production, then subset.
Rules (README.md, before the numbers): in each part an arm becomes a proposal for the site if, averaged over its folds,
its PDS index >= ens_0.7's + 0.005 and its cosine >= ens_0.7's; among those that pass, the highest mean PDS index.

    python banco_esm2.py --cube <layout> --code <cube code> --cache <rete cache> --t3 <T3 folder> --e2 <dir with J-*_E2b.npz> --out <new>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rete_ponte_jepa_2026-10-09"))
sys.path.insert(0, str(HERE.parents[1] / "generatore_e_banchi" / "budget_chiamate_2026-10-13"))
import rete_ponte as rp  # noqa: E402
from rete_ponte import gd  # noqa: E402
from ampiezza_banco import nmae  # noqa: E402
from soglia_banco import proxies  # noqa: E402

FOLDS = {"K562": "C-K562", "iPSC": "C-iPSC", "HCT116": "C-HCT116", "HEK293T": "C-HEK293"}
E2_FILES = {"K562": "J-K562_E2b.npz", "iPSC": "J-iPSC_E2b.npz"}
SEEDS = (2, 3, 4, 5, 6)
WA = (0.4, 0.5, 0.6, 0.7, 0.8)
W3 = (0.1, 0.2, 0.3)


def unit(X):
    n = np.sqrt((X ** 2).sum(1))
    return X * np.divide(1.0, n, out=np.zeros_like(n), where=n > 0)[:, None]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cube", type=Path, required=True)
    ap.add_argument("--code", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--t3", type=Path, required=True)
    ap.add_argument("--e2", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: never overwrite")
    a.out.mkdir(parents=True)
    logf = open(a.out / "run.log", "w", encoding="utf-8")

    def log(s):
        line = f"{time.strftime('%H:%M:%S')} {s}"
        print(line, flush=True)
        logf.write(line + "\n"); logf.flush()

    sys.path.insert(0, str(a.code))
    import arms
    C = gd.Cubes(arms, a.cube)
    cube = C.cube
    meta = rp.build_cache(C, a.cache, log)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    by_symbol = {}
    for k, s in cube.symbol.items():
        by_symbol.setdefault(s, set()).add(k)
    rec = {"seeds": SEEDS, "wa": WA, "w3": W3, "folds": {}, "folds_e2": {}}
    for held, fname in FOLDS.items():
        t0 = time.time()
        z = np.load(a.t3 / f"T3f__{fname}.npz", allow_pickle=False)
        targets, genes = [str(t) for t in z["targets"]], np.asarray(z["genes"], str)
        lfc = np.where(z["observed"], z["lfc"], 0).astype(np.float64)
        evalk = set(gd.eval_keys(C, held))
        rows, keys = [], []
        for i, t in enumerate(targets):
            ks = by_symbol.get(t, set())
            if len(ks) == 1 and next(iter(ks)) in evalk and next(iter(ks)) in meta["keys"]:
                rows.append(i)
                keys.append(next(iter(ks)))
        gpos = pd.Index(genes).get_indexer(cube.genes)
        if (gpos < 0).any():
            raise SystemExit("cube genes missing from the official axis")
        t3 = lfc[rows][:, gpos] / gd.AMP
        e2 = e2_rows = None
        if held in E2_FILES:
            ze = np.load(a.e2 / E2_FILES[held], allow_pickle=False)
            if [str(t) for t in ze["targets"]] != targets or list(np.asarray(ze["genes"], str)) != list(genes):
                raise SystemExit(f"{fname}: E2 axes differ from T3f")
            have = ze["observed"].any(1)[rows]
            e2_rows = np.flatnonzero(have)
            e2 = np.where(ze["observed"], ze["lfc"], 0).astype(np.float64)[rows][:, gpos][e2_rows]
        ctx = gd.Context(C, held)
        st = gd.transfer(C, "all", keys, ctx.commons, {held})
        Tall = np.nan_to_num(st["T"]).astype(np.float64)
        fold = rp.Fold(C, a.cache, meta, held, dev, log)
        P = Pw = 0.0
        for s in SEEDS:
            model, _ = fold.fit(seed=s)
            P = P + fold.predict(model, keys) / len(SEEDS)
            Pw = Pw + fold.predict(model, keys, residual=False) / len(SEEDS)
        res = (P - Pw).astype(np.float64)
        res_c = res - res.mean(0, keepdims=True)
        rete_c = Pw.astype(np.float64) + res_c
        y, se_y, _ = gd.truth(C, held, keys)
        bl = gd.basal_of(cube, cube.tables_of(held))
        cpm = np.expm1(np.nan_to_num(bl, nan=-1))
        expressed = np.isfinite(bl) & (cpm >= 5)
        own = gd.own_gene_cols(cube, keys)
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        mask_all = np.isfinite(bl)[None, :] & np.isfinite(y)
        for i, o in enumerate(own):
            if o >= 0:
                mask_all[i, o] = False

        def measure(cand, sub):
            mask = mask_all[sub]
            ref = np.sqrt((np.where(mask, cand["t3"], 0) ** 2).sum(1))
            out = {}
            for name, Q in cand.items():
                Q = np.nan_to_num(Q)
                nQ = np.sqrt((np.where(mask, Q, 0) ** 2).sum(1))
                Qn = Q * np.divide(ref, nQ, out=np.zeros_like(nQ), where=nQ > 0)[:, None]
                ms = gd.measures(Qn.astype(np.float32), y[sub], se_y[sub] ** 2, x, mask, ref)
                E = Qn * gd.AMP * 1.5
                p = proxies(E, y[sub], se_y[sub], own[sub], expressed, 0.0)
                out[name] = {"cos": float(np.nanmean(ms["cos"])), "pds": float(np.nanmean(ms["pds"])),
                             "fid": float(np.nanmean(p["fid"])), "jac": float(np.nanmean(p["jac"])),
                             "nmae": float(np.nanmean(nmae(E, y[sub], se_y[sub], own[sub], expressed)))}
            return out

        cosmat = lambda A, B: float(np.median((A * B).sum(1) / np.maximum(
            np.linalg.norm(A, axis=1) * np.linalg.norm(B, axis=1), 1e-12)))
        cand = {"t3": t3, "rete_c": rete_c}
        for w in WA:
            cand[f"ens_{w}"] = w * unit(t3) + (1 - w) * unit(rete_c)
        line = {"targets": len(keys), "arms": measure(cand, np.arange(len(keys))),
                "cos_t3_rete_c_median": cosmat(t3, rete_c)}
        if e2 is not None:
            sub = e2_rows
            t3s, rcs = t3[sub], rete_c[sub]
            cb = {"t3": t3s, "rete_c": rcs, "e2b": e2, "ens_0.7": 0.7 * unit(t3s) + 0.3 * unit(rcs)}
            for w in W3:
                cb[f"mix3e_{w}"] = 0.7 * (1 - w) * unit(t3s) + 0.3 * (1 - w) * unit(rcs) + w * unit(e2)
            rec["folds_e2"][held] = {"targets": int(len(sub)), "arms": measure(cb, sub),
                                     "cos_t3_e2b_median": cosmat(t3s, e2), "cos_rete_c_e2b_median": cosmat(rcs, e2)}
        rec["folds"][held] = line
        log(f"{held} {len(keys)} targets, {time.time() - t0:.0f}s, cos(t3, rete_c) {line['cos_t3_rete_c_median']:.3f} "
            + json.dumps({k: {m: round(v, 3) for m, v in d.items()} for k, d in line["arms"].items()}))
        (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        del fold
        torch.cuda.empty_cache()
    def mean_of(folds):
        names = list(next(iter(folds.values()))["arms"])
        return {n: {m: float(np.mean([folds[h]["arms"][n][m] for h in folds]))
                    for m in ("cos", "pds", "fid", "jac", "nmae")} for n in names}

    def rule(mean, arms):
        passing = [n for n in arms
                   if mean[n]["pds"] >= mean["ens_0.7"]["pds"] + 0.005 and mean[n]["cos"] >= mean["ens_0.7"]["cos"]]
        return {"passing": passing, "candidate": max(passing, key=lambda n: mean[n]["pds"]) if passing else None}

    mean = mean_of(rec["folds"])
    mean_e2 = mean_of(rec["folds_e2"])
    rec["mean_over_folds"], rec["mean_over_folds_e2"] = mean, mean_e2
    rec["rule"] = {"A_weight": rule(mean, [f"ens_{w}" for w in WA if w != 0.7]),
                   "B_esm2": rule(mean_e2, [f"mix3e_{w}" for w in W3])}
    (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    log("mean A " + json.dumps({k: {m: round(v, 4) for m, v in d.items()} for k, d in mean.items()}))
    log("mean B " + json.dumps({k: {m: round(v, 4) for m, v in d.items()} for k, d in mean_e2.items()}))
    log("rule " + json.dumps(rec["rule"]))


if __name__ == "__main__":
    main()
