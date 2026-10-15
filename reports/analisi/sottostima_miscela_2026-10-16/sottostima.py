"""Why the fold bench under-predicted ta 42's site gain (README.md in this folder): the mixture's gain by truth strength.

Same folds, targets, network refits (seeds 2-6), T3f and measures as reports/modelli/rete_su_t3_2026-10-15/banco_t3.py,
arms t3, rete_c, ens_0.5, ens_0.7, kept PER TARGET. Each target's truth strength is its signal-to-noise in the scorer's
geometry, snr = sqrt(mean over scored genes of (y / se)^2). Targets are split in terciles of snr within each fold, and
the PDS index and cosine of each arm, and the gains ens - t3, are reported per tercile and pooled over folds.
Note on units: the bench's PDS index is 1 - 2 x (share of other targets closer), chance 0; the site's raw pds_cosine is
the share of others farther, chance 0.5, so a bench gain is twice the corresponding raw site gain.

    python sottostima.py --cube <layout> --code <cube code> --cache <rete cache> --t3 <T3 folder> --out <new dir>
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
sys.path.insert(0, str(HERE.parents[1] / "modelli" / "rete_ponte_jepa_2026-10-09"))
sys.path.insert(0, str(HERE.parents[1] / "generatore_e_banchi" / "budget_chiamate_2026-10-13"))
sys.path.insert(0, str(HERE.parents[1] / "modelli" / "guadagno_appreso_2026-10-05"))
import rete_ponte as rp  # noqa: E402
from rete_ponte import gd  # noqa: E402
from ampiezza_banco import nmae  # noqa: E402
from soglia_banco import proxies  # noqa: E402

FOLDS = {"K562": "C-K562", "iPSC": "C-iPSC", "HCT116": "C-HCT116", "HEK293T": "C-HEK293"}
SEEDS = (2, 3, 4, 5, 6)
WEIGHTS = (0.5, 0.7)
ARMS = ("t3", "rete_c", "ens_0.5", "ens_0.7")


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
        cand = {"rete_c": rete_c, "t3": t3}
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
        z2 = np.where(mask, np.divide(np.nan_to_num(y), np.nan_to_num(se_y, nan=np.inf),
                                      out=np.zeros_like(np.nan_to_num(y)), where=np.isfinite(se_y) & (se_y > 0)), 0)
        snr = np.sqrt((z2 ** 2).sum(1) / np.maximum(mask.sum(1), 1))
        line = {"targets": len(keys), "snr": snr.tolist(), "per_target": {}}
        for name in ARMS:
            Q = np.nan_to_num(cand[name])
            nQ = np.sqrt((np.where(mask, Q, 0) ** 2).sum(1))
            Qn = Q * np.divide(nT3, nQ, out=np.zeros_like(nQ), where=nQ > 0)[:, None]
            ms = gd.measures(Qn.astype(np.float32), y, se_y ** 2, x, mask, nT3)
            line["per_target"][name] = {"pds": [float(v) for v in ms["pds"]],
                                        "cos": [None if not np.isfinite(v) else float(v) for v in ms["cos"]]}
        q = np.quantile(snr, [1 / 3, 2 / 3])
        terc = np.digitize(snr, q)
        line["terciles"] = {}
        for k in range(3):
            sel = terc == k
            row = {"n": int(sel.sum()), "snr_median": float(np.median(snr[sel]))}
            for name in ARMS:
                row[f"pds_{name}"] = float(np.mean(np.array(line["per_target"][name]["pds"])[sel]))
                cs = np.array([np.nan if v is None else v for v in line["per_target"][name]["cos"]])[sel]
                row[f"cos_{name}"] = float(np.nanmean(cs))
            line["terciles"][f"t{k}"] = row
        rec["folds"][held] = line
        log(f"{held} {len(keys)} targets, {time.time() - t0:.0f}s " + json.dumps(line["terciles"]))
        (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        del fold
        torch.cuda.empty_cache()
    pooled = {}
    for k in range(3):
        rows = [rec["folds"][h]["terciles"][f"t{k}"] for h in rec["folds"]]
        n = sum(r["n"] for r in rows)
        out = {"n": n}
        for name in ARMS:
            for m in ("pds", "cos"):
                out[f"{m}_{name}"] = float(sum(r[f"{m}_{name}"] * r["n"] for r in rows) / n)
        out["gain_pds_ens_0.7"] = out["pds_ens_0.7"] - out["pds_t3"]
        out["gain_pds_ens_0.5"] = out["pds_ens_0.5"] - out["pds_t3"]
        out["gain_cos_ens_0.7"] = out["cos_ens_0.7"] - out["cos_t3"]
        pooled[f"t{k}"] = out
    rec["pooled_terciles"] = pooled
    (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    log("pooled " + json.dumps({k: {m: round(v, 4) for m, v in d.items()} for k, d in pooled.items()}))


if __name__ == "__main__":
    main()
