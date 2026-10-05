import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, "kaggle_in/cube_r2_code"); sys.path.insert(0, "C:/Users/39346/virtual-cell-challenge-2026/reports/modelli/guadagno_appreso_2026-10-05")
import arms, guadagno as G
C = G.Cubes(arms, Path("kaggle_in/cube_r2_layout")); cube = C.cube
res = {}
for held in G.HELD:
    ctx = G.Context(C, held)
    keys = G.eval_keys(C, held)
    st = G.transfer(C, "all", keys, ctx.commons, {held})
    keys = [k for k, s in zip(keys, st["n"].max(1) > 0) if s][:G.MAX_EVAL]
    y, ysd, _ = G.truth(C, held, keys)
    bl = G.basal_of(cube, cube.tables_of(held)); x = 0.05*np.expm1(np.nan_to_num(bl))
    mask = np.isfinite(bl)[None] & np.isfinite(y)
    for i, o in enumerate(G.own_gene_cols(cube, keys)):
        if o >= 0: mask[i, o] = False
    parts = {g: G.group_stats(C, g, "all", keys, ctx.commons)[0] for g in C.groups("all", {held})}
    Tall = G.transfer(C, "all", keys, ctx.commons, {held})["T"]
    ref = np.sqrt((np.where(mask, np.nan_to_num(Tall), 0)**2).sum(1))
    def cosof(P): return G.measures(np.nan_to_num(P), y, ysd**2, x, mask, ref)
    r = {"all": float(np.nanmean(cosof(Tall)["cos"]))}
    per = {}
    for g, P in parts.items():
        cov = np.isfinite(P).any(1)
        m = cosof(P)["cos"]
        per[g] = {"cos_on_covered": float(np.nanmean(m[cov])) if cov.any() else None, "covered": int(cov.sum())}
    r["single_groups"] = per
    # oracle: per-line nonnegative group weights chosen ON THE TRUTH (upper bound, not a model), greedy over a grid
    gs = list(parts); w = {g: 1.0 for g in gs}
    def comb(w):
        num = sum(np.where(np.isfinite(parts[g]), parts[g], 0)*w[g] for g in gs)
        den = sum(np.where(np.isfinite(parts[g]), w[g], 0) for g in gs)
        return np.divide(num, den, out=np.zeros_like(num), where=den > 0)
    best = float(np.nanmean(cosof(comb(w))["cos"]))
    for _ in range(3):
        for g in gs:
            for v in (0.0, 0.25, 0.5, 1, 2, 4):
                w2 = dict(w); w2[g] = v
                if sum(w2.values()) == 0: continue
                c = np.nanmean(cosof(comb(w2))["cos"])
                if c > best + 1e-4: best, w = float(c), w2
    r["oracle_weights"] = w; r["oracle_cos"] = float(best)
    res[held] = r
    print(held, json.dumps({"all": round(r["all"],3), "oracle": round(best,3), "w": w}), flush=True)
    print("   ", {g: (round(v["cos_on_covered"],3) if v["cos_on_covered"] is not None else None, v["covered"]) for g, v in per.items()}, flush=True)
Path("processed/guadagno_appreso_2026-10-05/diag_gruppi_r1.json").write_text(json.dumps(res, indent=1))
