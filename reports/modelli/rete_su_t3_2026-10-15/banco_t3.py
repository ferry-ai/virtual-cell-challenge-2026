"""Our centred bridge network together with Davide's T3 (the base of td 38), on the lineage-excluded folds (README.md).

Davide's public dataset `davideferrante11/vcc-rsb-inputs-70dc-r1` holds T3's production effects (sha256 b8c61f6d...,
the td 38 file) and T3 refitted with one lineage excluded: T3f__C-K562, C-iPSC, C-HCT116, C-HEK293 (300 panel
targets x 18,533 genes, ln fold change with amplitude 1.576 and cis applied). The cube r2 has those lineages' truth
(groups K562, iPSC, HCT116, HEK293T). For each fold h, on the panel targets that h measures (>= 30 cells):
  all      the cube `all` transfer without h (guadagno.transfer);
  rete_c   the bridge network refitted without h (seeds 2-6), residual centred over these targets (ta 40's arm);
  t3       T3f of the fold on the cube genes, / 1.576;
  t3_res   t3 + the centred residual of rete_c;
  ens_w    unit-norm t3 and unit-norm rete_c mixed w : (1 - w), w in (0.5, 0.7).
Measures: debiased cosine and PDS index (guadagno.measures), and the DE proxies of budget_chiamate_2026-10-13 at T3's
per-target norm x 1.5 (fidelity, Jaccard, nMAE).

Registered before the numbers (README.md, rule): an arm becomes the candidate for the site if, averaged over the four
folds, its cosine is >= t3's + 0.010 and its PDS index >= t3's. Between ens_0.5, ens_0.7 and t3_res the one with the
higher mean PDS index among those that pass is sent; if none passes, nothing is sent from this bench.

    python banco_t3.py --cube <layout> --code <cube code> --cache <rete cache> --t3 <dataset folder> --out <new dir>
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
WEIGHTS = (0.5, 0.7)


def unit(X):
    n = np.sqrt((X ** 2).sum(1))
    return X * np.divide(1.0, n, out=np.zeros_like(n), where=n > 0)[:, None]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cube", type=Path, required=True)
    ap.add_argument("--code", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--t3", type=Path, required=True)
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
    rec = {"seeds": SEEDS, "weights": WEIGHTS, "folds": {}}
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
        cand = {"all": Tall, "rete_c": rete_c, "t3": t3, "t3_res": t3 + res_c}
        for w in WEIGHTS:
            cand[f"ens_{w}"] = w * unit(t3) + (1 - w) * unit(rete_c)
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
        line["cos_t3_all_median"] = cosmat(t3, Tall)
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
    passing = [n for n in ("ens_0.5", "ens_0.7", "t3_res")
               if mean[n]["cos"] >= mean["t3"]["cos"] + 0.010 and mean[n]["pds"] >= mean["t3"]["pds"]]
    rec["rule"] = {"passing": passing,
                   "candidate": max(passing, key=lambda n: mean[n]["pds"]) if passing else None}
    (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    log("mean " + json.dumps({k: {m: round(v, 4) for m, v in d.items()} for k, d in mean.items()}))
    log("rule " + json.dumps(rec["rule"]))


if __name__ == "__main__":
    main()
