"""Confidence at the head of the ranking on the cube bench (README.md in this folder): a reach proxy.

The scorer's reach ranks the truth-significant genes of a target by the PREDICTION's p-value and keeps the deepest
prefix whose sign purity is >= 0.9 (REACH_PURITY_FLOOR), as a fraction of the truth budget. Proxy here: rank by
|E| x sqrt(control CPM) (the Wilcoxon detectability of a mean shift), purity of sign(E) == sign(y).
Arms (E = T x 1.576 x 1.5, then each target back to its own norm, so only the direction moves):
  dense         today's emission;
  boost_b_z0    genes whose source z = |T| / se >= z0 multiplied by (1 + b);
  zpow_g        E x (z / median z) ** g (smooth confidence weighting).
Also the fidelity, Jaccard and nMAE proxies (ampiezza_banco.py) and the debiased cosine and PDS index.

    python testa_banco.py --cube <layout> --code <cube code> --out <new dir>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "modelli" / "guadagno_appreso_2026-10-05"))
import guadagno as gd  # noqa: E402
from ampiezza_banco import nmae  # noqa: E402
from soglia_banco import SCALE, Z, proxies  # noqa: E402

FLOOR = 0.9


def reach(E, y, se, own, expressed, cpm):
    out = np.full(E.shape[0], np.nan)
    det = np.sqrt(np.maximum(cpm, 0))
    for i in range(E.shape[0]):
        t, s = y[i], se[i]
        ok = expressed & np.isfinite(t) & (t != 0)
        if own[i] >= 0:
            ok[own[i]] = False
        z = np.divide(t, s, out=np.zeros_like(t), where=np.isfinite(s) & (s > 0))
        R = np.flatnonzero(ok & (np.abs(z) >= Z))
        if len(R) == 0:
            continue
        order = R[np.argsort(-(np.abs(E[i][R]) * det[R]), kind="stable")]
        hit = (np.sign(E[i][order]) == np.sign(t[order])).astype(float)
        pur = np.cumsum(hit) / np.arange(1, len(order) + 1)
        good = np.flatnonzero(pur >= FLOOR)
        out[i] = (good[-1] + 1) / len(R) if len(good) else 0.0
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cube", type=Path, required=True)
    ap.add_argument("--code", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: never overwrite")
    a.out.mkdir(parents=True)
    sys.path.insert(0, str(a.code))
    import arms
    C = gd.Cubes(arms, a.cube)
    cube = C.cube
    rec = {"floor": FLOOR, "lines": {}}
    for held in gd.HELD:
        t0 = time.time()
        ctx = gd.Context(C, held)
        keys = gd.eval_keys(C, held)
        st = gd.transfer(C, "all", keys, ctx.commons, {held})
        keys = [k for k, s in zip(keys, st["n"].max(1) > 0) if s][:gd.MAX_EVAL]
        st = gd.transfer(C, "all", keys, ctx.commons, {held})
        y, se_y, _ = gd.truth(C, held, keys)
        T = np.nan_to_num(st["T"]).astype(np.float64)
        se = np.nan_to_num(st["se"], nan=np.inf).astype(np.float64)
        zT = np.abs(T) / (se + 1e-3)
        zmed = np.median(zT[np.abs(T) > 0])
        bl = gd.basal_of(cube, cube.tables_of(held))
        cpm = np.expm1(np.nan_to_num(bl, nan=-1))
        expressed = np.isfinite(bl) & (cpm >= 5)
        own = gd.own_gene_cols(cube, keys)
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        mask = np.isfinite(bl)[None, :] & np.isfinite(y)
        for i, o in enumerate(own):
            if o >= 0:
                mask[i, o] = False
        ref = np.sqrt((np.where(mask, T, 0) ** 2).sum(1))
        cand = {"dense": T}
        for b in (0.5, 1.0):
            for z0 in (2.0, 3.0):
                cand[f"boost{b}_z{z0}"] = T * (1 + b * (zT >= z0))
        for g in (0.25, 0.5):
            cand[f"zpow{g}"] = T * (zT / zmed) ** g
        line = {"targets": len(keys), "arms": {}}
        for name, P in cand.items():
            nP = np.sqrt((P ** 2).sum(1))
            P = P * np.divide(np.sqrt((T ** 2).sum(1)), nP, out=np.zeros_like(nP), where=nP > 0)[:, None]
            E = P * SCALE
            p = proxies(E, y, se_y, own, expressed, 0.0)
            ms = gd.measures(P.astype(np.float32), y, se_y ** 2, x, mask, ref)
            line["arms"][name] = {"reach": float(np.nanmean(reach(E, y, se_y, own, expressed, cpm))),
                                  "fid": float(np.nanmean(p["fid"])), "jac": float(np.nanmean(p["jac"])),
                                  "nmae": float(np.nanmean(nmae(E, y, se_y, own, expressed))),
                                  "cos": float(np.nanmean(ms["cos"])), "pds": float(np.nanmean(ms["pds"]))}
        rec["lines"][held] = line
        print(held, f"{time.time() - t0:.0f}s", flush=True)
        (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    names = list(next(iter(rec["lines"].values()))["arms"])
    rec["mean_over_lines"] = {n: {m: float(np.mean([rec["lines"][h]["arms"][n][m] for h in rec["lines"]]))
                                  for m in ("reach", "fid", "jac", "nmae", "cos", "pds")} for n in names}
    (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec["mean_over_lines"], indent=1))


if __name__ == "__main__":
    main()
