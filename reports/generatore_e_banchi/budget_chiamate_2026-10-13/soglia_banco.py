"""Call budget on the cube bench (README.md in this folder): what keeping only the strongest predicted effects does.

For each held-out line of the stage-1 bench (guadagno.py), the `all` transfer T is scaled to site units
(E = T x 1.576 x 1.5, the t28 emission) and hard-thresholded at |E| >= tau; tau = 0 is the dense production vector.
Effect-space proxies of the DE members, per target, own gene excluded, genes with control CPM >= 5:
  n_pred = #{|E| >= tau and |E| >= 0.2}   (0.2 ~ what the site detects today: median 1474 genes/target, 23/09 calls)
  R      = truth-significant genes, |y / se| >= Z
  k      = predicted genes whose sign matches the truth's sign (truth defined and non-zero)
  fid    = k / max(n_pred, |R|)     prec = k / n_pred     jac = |P & R| / |P | R|
plus the bench's debiased cosine and PDS index (guadagno.measures) of the thresholded vector against the dense one.
Ranking alternatives: |T| (amplitude), |T| x agree (source sign agreement), |T| / se (source z).

    python soglia_banco.py --cube <layout> --code <cube code> --out <new dir>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "modelli" / "guadagno_appreso_2026-10-05"))
import guadagno as gd  # noqa: E402

SCALE = gd.AMP * 1.5
DETECT = 0.2
TAUS = (0.0, 0.3, 0.5, 0.75, 1.0, 1.5)
Z = 3.0


def proxies(E, y, se, own, expressed, tau, rank=None):
    K = E.shape[0]
    out = {m: np.full(K, np.nan) for m in ("n_pred", "n_conf", "k", "fid", "prec", "jac")}
    for i in range(K):
        e, t, s = E[i], y[i], se[i]
        ok = expressed & np.isfinite(t) & np.isfinite(e)
        if own[i] >= 0:
            ok[own[i]] = False
        z = np.divide(t, s, out=np.zeros_like(t), where=np.isfinite(s) & (s > 0))
        R = ok & (np.abs(z) >= Z)
        if rank is None:
            P = ok & (np.abs(e) >= max(tau, DETECT))
        else:                                   # keep the same number of genes as |E| >= tau, chosen by `rank`
            m = int((ok & (np.abs(e) >= max(tau, DETECT))).sum())
            r = np.where(ok & (np.abs(e) >= DETECT), rank[i], -np.inf)
            P = np.zeros_like(ok)
            if m > 0:
                P[np.argpartition(-r, m - 1)[:m]] = True
                P &= np.isfinite(r)
        k = int((P & (np.sign(e) == np.sign(t)) & (t != 0)).sum())
        npred, nconf = int(P.sum()), int(R.sum())
        out["n_pred"][i], out["n_conf"][i], out["k"][i] = npred, nconf, k
        den = max(npred, nconf)
        out["fid"][i] = k / den if den else np.nan
        out["prec"][i] = k / npred if npred else np.nan
        un = int((P | R).sum())
        out["jac"][i] = (P & R).sum() / un if un else 1.0
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
    rec = {"scale": SCALE, "detect": DETECT, "z": Z, "taus": TAUS, "lines": {}}
    for held in gd.HELD:
        t0 = time.time()
        ctx = gd.Context(C, held)
        keys = gd.eval_keys(C, held)
        st = gd.transfer(C, "all", keys, ctx.commons, {held})
        keys = [k for k, s in zip(keys, st["n"].max(1) > 0) if s][:gd.MAX_EVAL]
        st = gd.transfer(C, "all", keys, ctx.commons, {held})
        y, se, _ = gd.truth(C, held, keys)
        T = np.nan_to_num(st["T"])
        E = T * SCALE
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
        ranks = {"amp": None, "agree": np.abs(T) * np.nan_to_num(st["agree"]),
                 "z": np.abs(T) / (np.nan_to_num(st["se"], nan=np.inf) + 1e-3)}
        line = {"targets": len(keys), "arms": {}}
        for tau in TAUS:
            Pt = np.where(np.abs(E) >= tau, T, 0.0) if tau > 0 else T
            ms = gd.measures(Pt, y, se ** 2, x, mask, ref)
            for rn, rk in ranks.items():
                if tau == 0 and rn != "amp":
                    continue
                p = proxies(E, y, se, own, expressed, tau, rk)
                line["arms"][f"tau{tau}_{rn}"] = {
                    **{m: float(np.nanmean(v)) for m, v in p.items()},
                    "n_pred_median": float(np.nanmedian(p["n_pred"])), "n_conf_median": float(np.nanmedian(p["n_conf"])),
                    "cos": float(np.nanmean(ms["cos"])) if rn == "amp" else None,
                    "pds": float(np.nanmean(ms["pds"])) if rn == "amp" else None}
        rec["lines"][held] = line
        print(held, f"{time.time() - t0:.0f}s", json.dumps({k: {m: round(v, 3) for m, v in d.items() if v is not None}
                                                            for k, d in line["arms"].items()}), flush=True)
        (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    arms_ = list(next(iter(rec["lines"].values()))["arms"])
    rec["mean_over_lines"] = {k: {m: float(np.mean([rec["lines"][h]["arms"][k][m] for h in rec["lines"]]))
                                  for m in ("fid", "prec", "jac", "n_pred_median", "n_conf_median")}
                              for k in arms_}
    for k in arms_:
        if rec["lines"][gd.HELD[0]]["arms"][k]["cos"] is not None:
            rec["mean_over_lines"][k]["cos"] = float(np.mean([rec["lines"][h]["arms"][k]["cos"] for h in rec["lines"]]))
            rec["mean_over_lines"][k]["pds"] = float(np.mean([rec["lines"][h]["arms"][k]["pds"] for h in rec["lines"]]))
    (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec["mean_over_lines"], indent=1))


if __name__ == "__main__":
    main()
