"""Cap on effect magnitudes on the cube bench (README.md in this folder): E = clip(T x 1.576 x a, -c, c).

A called gene stays called above the detection level, so fidelity and Jaccard proxies should not move; the cap
removes the large wrong-sign values that cost the most nMAE. The cap changes the direction, so the debiased cosine and
PDS index (guadagno.measures) are reported. Original notes of ampiezza_banco.py follow.


Direction fixed (the dense `all` transfer T); only magnitudes change, so the PDS and cosine do not move. Arms:
  E = T x 1.576 x a x (|T_p| / median_p |T_p|)^alpha,   a in AMPS, alpha in ALPHAS (alpha = 0: today's emission)
DE proxies of soglia_banco.py (detection |E| >= 0.2 on expressed genes; truth-significant |y/se| >= 3) plus an nMAE
proxy on the truth-significant genes: per target sum|E - y| / sum|y|, averaged.
Calibration check, registered here before the numbers: on the site a = 1.0 -> 1.5 raised the fidelity (raw +0.025)
and worsened the nMAE (raw +0.027, ta 38 vs ta 36); the bench is usable for this question only if it shows the same
two signs.

    python tetto_banco.py --cube <layout> --code <cube code> --out <new dir>
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
from soglia_banco import Z, proxies  # noqa: E402

AMPS = (1.5, 2.0, 3.0)
CAPS = (None, 1.5, 1.0, 0.7, 0.5)


def nmae(E, y, se, own, expressed):
    out = np.full(E.shape[0], np.nan)
    for i in range(E.shape[0]):
        t, s = y[i], se[i]
        ok = expressed & np.isfinite(t)
        if own[i] >= 0:
            ok[own[i]] = False
        z = np.divide(t, s, out=np.zeros_like(t), where=np.isfinite(s) & (s > 0))
        R = ok & (np.abs(z) >= Z)
        den = np.abs(t[R]).sum()
        if den > 0:
            out[i] = np.abs(E[i][R] - t[R]).sum() / den
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
    rec = {"amps": AMPS, "caps": CAPS, "lines": {}}
    for held in gd.HELD:
        t0 = time.time()
        ctx = gd.Context(C, held)
        keys = gd.eval_keys(C, held)
        st = gd.transfer(C, "all", keys, ctx.commons, {held})
        keys = [k for k, s in zip(keys, st["n"].max(1) > 0) if s][:gd.MAX_EVAL]
        st = gd.transfer(C, "all", keys, ctx.commons, {held})
        y, se_y, _ = gd.truth(C, held, keys)
        T = np.nan_to_num(st["T"]).astype(np.float64)
        bl = gd.basal_of(cube, cube.tables_of(held))
        cpm = np.expm1(np.nan_to_num(bl, nan=-1))
        expressed = np.isfinite(bl) & (cpm >= 5)
        own = gd.own_gene_cols(cube, keys)
        nT = np.sqrt((T ** 2).sum(1))
        rel = nT / np.median(nT[nT > 0])
        line = {"targets": len(keys), "arms": {}}
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        mask = np.isfinite(bl)[None, :] & np.isfinite(y)
        for i, o in enumerate(own):
            if o >= 0:
                mask[i, o] = False
        ref = np.sqrt((np.where(mask, T, 0) ** 2).sum(1))
        for amp in AMPS:
            for cap in CAPS:
                E = T * gd.AMP * amp
                if cap is not None:
                    E = np.clip(E, -cap, cap)
                p = proxies(E, y, se_y, own, expressed, 0.0)
                ms = gd.measures((E / (gd.AMP * amp)).astype(np.float32), y, se_y ** 2, x, mask, ref)
                line["arms"][f"a{amp}_cap{cap}"] = {
                    "fid": float(np.nanmean(p["fid"])), "prec": float(np.nanmean(p["prec"])),
                    "jac": float(np.nanmean(p["jac"])), "nmae": float(np.nanmean(nmae(E, y, se_y, own, expressed))),
                    "cos": float(np.nanmean(ms["cos"])), "pds": float(np.nanmean(ms["pds"])),
                    "n_pred_median": float(np.nanmedian(p["n_pred"]))}
        rec["lines"][held] = line
        print(held, f"{time.time() - t0:.0f}s", flush=True)
        (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    names = list(next(iter(rec["lines"].values()))["arms"])
    rec["mean_over_lines"] = {n: {m: float(np.mean([rec["lines"][h]["arms"][n][m] for h in rec["lines"]]))
                                  for m in ("fid", "prec", "jac", "nmae", "cos", "pds", "n_pred_median")} for n in names}
    (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec["mean_over_lines"], indent=1))


if __name__ == "__main__":
    main()
