"""Context-matched transfer on the cube bench (README.md in this folder): Davide's open hypothesis "one vote per lineage".

For each held-out line h the source groups are ranked by the correlation of their controls' basal profile (log1p CPM)
with h's controls -- controls only, so the same rule applies to A/B/C. Arms:
  all      equal-weight mean of every source group (today's base);
  top_k    equal-weight mean of the k most similar groups; a target none of them measures falls back to `all`;
  soft_t   similarity-weighted mean, weights softmax(corr / t) over the groups that measure the target.
Debiased cosine and PDS index (guadagno.measures), plus the DE proxies of ampiezza_banco.py at the t28 emission.

    python affini_banco.py --cube <layout> --code <cube code> --out <new dir>
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
from soglia_banco import SCALE, proxies  # noqa: E402

KS = (1, 2, 3, 5)
TEMPS = (0.02, 0.05)


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
    rec = {"ks": KS, "temps": TEMPS, "lines": {}}
    for held in gd.HELD:
        t0 = time.time()
        ctx = gd.Context(C, held)
        keys = gd.eval_keys(C, held)
        st = gd.transfer(C, "all", keys, ctx.commons, {held})
        keys = [k for k, s in zip(keys, st["n"].max(1) > 0) if s][:gd.MAX_EVAL]
        st = gd.transfer(C, "all", keys, ctx.commons, {held})
        Tall = np.nan_to_num(st["T"]).astype(np.float64)
        y, se_y, _ = gd.truth(C, held, keys)
        bl = gd.basal_of(cube, cube.tables_of(held))
        groups = C.groups("all", {held})
        sim = {}
        for g in groups:
            bg = gd.basal_of(cube, cube.tables_of(g))
            ok = np.isfinite(bl) & np.isfinite(bg)
            sim[g] = float(np.corrcoef(bl[ok], bg[ok])[0, 1])
        order = sorted(groups, key=lambda g: -sim[g])
        means = {}
        for g in groups:
            m, _, _ = gd.group_stats(C, g, "all", keys, ctx.commons)
            means[g] = m.astype(np.float64)
        cand = {"all": Tall}
        for k in KS:
            sel = order[:k]
            P = np.stack([means[g] for g in sel])
            ok = np.isfinite(P)
            n = ok.sum(0)
            Tk = np.divide(np.where(ok, P, 0).sum(0), n, out=np.full(Tall.shape, np.nan), where=n > 0)
            Tk = np.where(np.isfinite(Tk), Tk, Tall)
            cand[f"top{k}"] = Tk
        P = np.stack([means[g] for g in groups])
        ok = np.isfinite(P)
        s = np.array([sim[g] for g in groups])
        for t in TEMPS:
            w = np.exp((s - s.max()) / t)[:, None, None] * ok
            den = w.sum(0)
            Ts = np.divide((w * np.where(ok, P, 0)).sum(0), den, out=np.full(Tall.shape, np.nan), where=den > 0)
            cand[f"soft{t}"] = np.where(np.isfinite(Ts), Ts, Tall)
        cpm = np.expm1(np.nan_to_num(bl, nan=-1))
        expressed = np.isfinite(bl) & (cpm >= 5)
        own = gd.own_gene_cols(cube, keys)
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        mask = np.isfinite(bl)[None, :] & np.isfinite(y)
        for i, o in enumerate(own):
            if o >= 0:
                mask[i, o] = False
        ref = np.sqrt((np.where(mask, Tall, 0) ** 2).sum(1))
        line = {"targets": len(keys), "similarity": sim, "order": order, "arms": {}}
        for name, T in cand.items():
            nP = np.sqrt((T ** 2).sum(1))
            Tn = T * np.divide(np.sqrt((Tall ** 2).sum(1)), nP, out=np.zeros_like(nP), where=nP > 0)[:, None]
            E = Tn * SCALE
            p = proxies(E, y, se_y, own, expressed, 0.0)
            ms = gd.measures(Tn.astype(np.float32), y, se_y ** 2, x, mask, ref)
            line["arms"][name] = {"cos": float(np.nanmean(ms["cos"])), "pds": float(np.nanmean(ms["pds"])),
                                  "fid": float(np.nanmean(p["fid"])), "jac": float(np.nanmean(p["jac"])),
                                  "nmae": float(np.nanmean(nmae(E, y, se_y, own, expressed)))}
        rec["lines"][held] = line
        print(held, f"{time.time() - t0:.0f}s", "order", order[:3],
              json.dumps({k: {m: round(v, 3) for m, v in d.items()} for k, d in line["arms"].items()}), flush=True)
        (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    names = list(next(iter(rec["lines"].values()))["arms"])
    rec["mean_over_lines"] = {n: {m: float(np.mean([rec["lines"][h]["arms"][n][m] for h in rec["lines"]]))
                                  for m in ("cos", "pds", "fid", "jac", "nmae")} for n in names}
    (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec["mean_over_lines"], indent=1))


if __name__ == "__main__":
    main()
