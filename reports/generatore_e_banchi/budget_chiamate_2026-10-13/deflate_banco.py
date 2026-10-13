"""Deflation of the transfer on the cube bench (README.md in this folder): remove the top-r programmes shared by the
panel's predicted targets (the opposite of denoise_banco.py, whose projection ON them destroyed the PDS).

Arms: dense; centred (panel mean removed, as ta 40); deflate_r = centred minus its top-r SVD components.

Original notes of denoise_banco.py follow.

For each held-out line of the stage-1 bench, the `all` transfer T of its targets (predictions only, no truth) is
  lowrank_r : projected on the top-r right singular vectors of the K x G prediction matrix itself (programmes
              shared across the panel's targets; per-target noise is independent across targets);
  shrink    : T * T^2 / (T^2 + se^2), se = the transfer's standard error per (target, gene);
  both      : shrink, then lowrank_r.
Every arm is compared at the recipe's norm (guadagno.measures rescales to |T|), so only the DIRECTION changes:
debiased cosine with the truth, PDS index, and the DE proxies of soglia_banco.py at the dense arm's norm.

    python deflate_banco.py --cube <layout> --code <cube code> --out <new dir>
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
from soglia_banco import SCALE, proxies  # noqa: E402

RANKS = (1, 2, 3, 5, 8, 12, 20)


def svd(T: np.ndarray):
    return np.linalg.svd(np.nan_to_num(T.astype(np.float64), nan=0.0, posinf=0.0, neginf=0.0), full_matrices=False)


def lowrank(usv, r: int) -> np.ndarray:
    U, s, Vt = usv
    return (U[:, :r] * s[:r]) @ Vt[:r]


def at_norm(P: np.ndarray, T: np.ndarray) -> np.ndarray:
    nP = np.sqrt((P ** 2).sum(1))
    nT = np.sqrt((T ** 2).sum(1))
    return P * np.divide(nT, nP, out=np.zeros_like(nP), where=nP > 0)[:, None]


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
    rec = {"ranks": RANKS, "lines": {}}
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
        den = T ** 2 + se ** 2
        S = T * np.divide(T ** 2, den, out=np.zeros_like(T), where=np.isfinite(se) & (den > 0))
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
        Tc = T - T.mean(0, keepdims=True)
        cand = {"dense": T, "centred": Tc}
        uC = svd(Tc)
        for r in RANKS:
            cand[f"deflate{r}"] = Tc - lowrank(uC, r)
        line = {"targets": len(keys), "arms": {}}
        for name, P in cand.items():
            P = at_norm(P, T)
            ms = gd.measures(P.astype(np.float32), y, se_y ** 2, x, mask, ref)
            p = proxies(P * SCALE, y, se_y, own, expressed, 0.0)
            line["arms"][name] = {"cos": float(np.nanmean(ms["cos"])), "pds": float(np.nanmean(ms["pds"])),
                                  "fid": float(np.nanmean(p["fid"])), "prec": float(np.nanmean(p["prec"])),
                                  "jac": float(np.nanmean(p["jac"])), "n_pred_median": float(np.nanmedian(p["n_pred"]))}
        rec["lines"][held] = line
        print(held, f"{time.time() - t0:.0f}s", json.dumps({k: {m: round(v, 3) for m, v in d.items()}
                                                            for k, d in line["arms"].items()}), flush=True)
        (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    names = list(next(iter(rec["lines"].values()))["arms"])
    rec["mean_over_lines"] = {n: {m: float(np.mean([rec["lines"][h]["arms"][n][m] for h in rec["lines"]]))
                                  for m in ("cos", "pds", "fid", "prec", "jac", "n_pred_median")} for n in names}
    (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec["mean_over_lines"], indent=1))


if __name__ == "__main__":
    main()
