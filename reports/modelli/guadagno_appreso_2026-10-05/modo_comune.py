"""DIAGNOSI_MODO_COMUNE.md: ceiling of adding the held-out line's common response to the all transfer (cube r2).

    python modo_comune.py --cube <layout> --code <cube code> --out <file.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guadagno as G  # noqa: E402


def raw_common(cube, tables) -> np.ndarray:
    """Reliability-weighted mean over the tables of the per-table mean raw effect over all usable keys."""
    num, den = 0, 0
    for t in tables:
        keys = cube.keys_of(t)
        s, n = np.zeros(len(cube.genes)), np.zeros(len(cube.genes))
        for b0 in range(0, len(keys), 1000):
            x, _ = cube.get(t, "raw", keys[b0:b0 + 1000], purpose="truth")
            ok = np.isfinite(x)
            s += np.where(ok, x, 0).sum(0)
            n += ok.sum(0)
        m = np.divide(s, n, out=np.full(len(cube.genes), np.nan), where=n > 0)
        w = len(keys) / (len(keys) + 100.0)
        num = num + np.where(np.isfinite(m), m * w, 0)
        den = den + np.where(np.isfinite(m), w, 0)
    return np.divide(num, den, out=np.full(len(cube.genes), np.nan), where=np.asarray(den) > 0).astype(np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cube", type=Path, required=True)
    ap.add_argument("--code", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    sys.path.insert(0, str(a.code))
    import arms
    C = G.Cubes(arms, a.cube)
    cube = C.cube
    rng = np.random.default_rng(0)
    rec = {"lines": {}}
    for L in G.HELD:
        ctx = G.Context(C, L)
        keys = G.eval_keys(C, L)
        st = G.transfer(C, "all", keys, ctx.commons, {L})
        keys = [k for k, s in zip(keys, st["n"].max(1) > 0) if s][:G.MAX_EVAL]
        Tall = np.nan_to_num(G.transfer(C, "all", keys, ctx.commons, {L})["T"])
        cL = np.nan_to_num(raw_common(cube, cube.tables_of(L)))
        src = [t for t in cube.tables if cube.group[t] != L]
        csrc = np.nanmean(np.vstack([ctx.commons[t] for t in src]), 0)
        y, ysd, _ = G.truth(C, L, keys)
        bl = G.basal_of(cube, cube.tables_of(L))
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        mask = np.isfinite(bl)[None] & np.isfinite(y)
        for i, o in enumerate(G.own_gene_cols(cube, keys)):
            if o >= 0:
                mask[i, o] = False
        d = x / (1 + x)
        Y = np.where(mask, np.nan_to_num(y), 0) * d[None]
        share = float(len(keys) * ((np.where(mask, cL[None], 0) * d[None])[0] ** 2).sum() / (Y ** 2).sum())
        K = len(keys)
        armsP = {"all": Tall, "comune_vero": np.broadcast_to(cL, Tall.shape).copy(), "all+comune_vero": Tall + cL[None],
                 "all+comune_sorgenti": Tall + csrc[None]}
        res = {}
        for n, P in armsP.items():
            ref = np.sqrt((np.where(mask, P, 0) ** 2).sum(1)) / G.AMP          # keep each arm's own norm
            res[n] = G.measures(P, y, ysd ** 2, x, mask, ref)
        line = {"targets": K, "energy_share_common": share,
                "arms": {n: {"cos": float(np.nanmean(r["cos"])), "pds": float(np.mean(r["pds"])),
                             "mse_med": float(np.nanmedian(r["mse"]))} for n, r in res.items()},
                "diff_vs_all": {n: {"cos": G.boot_diff(res[n]["cos"], res["all"]["cos"], rng),
                                    "pds": G.boot_diff(res[n]["pds"], res["all"]["pds"], rng)}
                                for n in ("all+comune_vero", "all+comune_sorgenti")}}
        rec["lines"][L] = line
        print(L, "share", round(share, 3), {n: {k: round(v, 3) for k, v in r.items()} for n, r in line["arms"].items()},
              flush=True)
    a.out.write_text(json.dumps(rec, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
