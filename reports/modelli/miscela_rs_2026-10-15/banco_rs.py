"""Third ingredient for the ta 42 mixture: Davide's RSB on the lineage-excluded folds (README.md in this folder).

Same folds, targets, network refits (seeds 2-6) and measures as rete_su_t3_2026-10-15/banco_t3.py, plus Davide's
public `davidmaisterx/vcc-rsb-effects-70dc-r1` (RSB__C-K562, C-iPSC, C-HCT116, C-HEK293: one model per fold, T3's
per-target norm, cosine 0.16-0.23 with T3f). Arms (each ingredient at unit norm, mixed, then at T3's norm):
  t3, rete_c, rsb       the single predictors;
  ens_0.7               0.7 t3 + 0.3 rete_c (ta 42's recipe, the reference);
  mix3_w                t3 : rete_c : rsb = 0.7 (1 - w) : 0.3 (1 - w) : w, w in (0.1, 0.2, 0.3).
Registered before the numbers (README.md): a mix3 arm becomes a proposal for the site if, averaged over the four folds,
its PDS index >= ens_0.7's + 0.005 and its cosine >= ens_0.7's; among those that pass, the highest mean PDS index.

    python banco_rs.py --cube <layout> --code <cube code> --cache <rete cache> --t3 <T3 folder> --rsb <RSB folder> --out <new>
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
SEEDS = (2, 3, 4, 5, 6)
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
    ap.add_argument("--rsb", type=Path, required=True)
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
    rec = {"seeds": SEEDS, "w3": W3, "folds": {}}
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
        zr = np.load(a.rsb / f"RSB__{fname}.npz", allow_pickle=False)
        if [str(t) for t in zr["targets"]] != targets or list(np.asarray(zr["genes"], str)) != list(genes):
            raise SystemExit(f"{fname}: RSB axes differ from T3f")
        rsb = np.where(zr["observed"], zr["lfc"], 0).astype(np.float64)[rows][:, gpos] / gd.AMP
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
        cand = {"t3": t3, "rete_c": rete_c, "rsb": rsb, "ens_0.7": 0.7 * unit(t3) + 0.3 * unit(rete_c)}
        for w in W3:
            cand[f"mix3_{w}"] = 0.7 * (1 - w) * unit(t3) + 0.3 * (1 - w) * unit(rete_c) + w * unit(rsb)
        y, se_y, _ = gd.truth(C, held, keys)
        bl = gd.basal_of(cube, cube.tables_of(held))
        cpm = np.expm1(np.nan_to_num(bl, nan=-1))
        expressed = np.isfinite(bl) & (cpm >= 5)
        own = gd.own_gene_cols(cube, keys)
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        mask = np.isfinite(bl)[None, :] & np.isfinite(y)
        for i, o in enumerate(own):
            if o >= 0:
                mask[i, o] = False
        nT3 = np.sqrt((np.where(mask, t3, 0) ** 2).sum(1))
        line = {"targets": len(keys), "arms": {}}
        for name, Q in cand.items():
            Q = np.nan_to_num(Q)
            nQ = np.sqrt((np.where(mask, Q, 0) ** 2).sum(1))
            Qn = Q * np.divide(nT3, nQ, out=np.zeros_like(nQ), where=nQ > 0)[:, None]
            ms = gd.measures(Qn.astype(np.float32), y, se_y ** 2, x, mask, nT3)
            E = Qn * gd.AMP * 1.5
            p = proxies(E, y, se_y, own, expressed, 0.0)
            line["arms"][name] = {"cos": float(np.nanmean(ms["cos"])), "pds": float(np.nanmean(ms["pds"])),
                                  "fid": float(np.nanmean(p["fid"])), "jac": float(np.nanmean(p["jac"])),
                                  "nmae": float(np.nanmean(nmae(E, y, se_y, own, expressed)))}
        cosmat = lambda A, B: float(np.median((A * B).sum(1) / np.maximum(
            np.linalg.norm(A, axis=1) * np.linalg.norm(B, axis=1), 1e-12)))
        line["cos_t3_rete_c_median"] = cosmat(t3, rete_c)
        line["cos_t3_rsb_median"] = cosmat(t3, rsb)
        line["cos_rete_c_rsb_median"] = cosmat(rete_c, rsb)
        rec["folds"][held] = line
        log(f"{held} {len(keys)} targets, {time.time() - t0:.0f}s, cos(t3, rete_c) {line['cos_t3_rete_c_median']:.3f} "
            + json.dumps({k: {m: round(v, 3) for m, v in d.items()} for k, d in line["arms"].items()}))
        (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        del fold
        torch.cuda.empty_cache()
    names = list(next(iter(rec["folds"].values()))["arms"])
    mean = {n: {m: float(np.mean([rec["folds"][h]["arms"][n][m] for h in rec["folds"]]))
                for m in ("cos", "pds", "fid", "jac", "nmae")} for n in names}
    rec["mean_over_folds"] = mean
    passing = [n for n in (f"mix3_{w}" for w in W3)
               if mean[n]["pds"] >= mean["ens_0.7"]["pds"] + 0.005 and mean[n]["cos"] >= mean["ens_0.7"]["cos"]]
    rec["rule"] = {"passing": passing,
                   "candidate": max(passing, key=lambda n: mean[n]["pds"]) if passing else None}
    (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    log("mean " + json.dumps({k: {m: round(v, 4) for m, v in d.items()} for k, d in mean.items()}))
    log("rule " + json.dumps(rec["rule"]))


if __name__ == "__main__":
    main()
