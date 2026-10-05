import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, "kaggle_in/cube_r2_code"); sys.path.insert(0, "C:/Users/39346/virtual-cell-challenge-2026/reports/modelli/guadagno_appreso_2026-10-05")
import arms, guadagno as G
C = G.Cubes(arms, Path("kaggle_in/cube_r2_layout")); cube = C.cube
rng = np.random.default_rng(0); res = {}
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
    parts = {g: G.group_stats(C, g, "all", keys, ctx.commons)[0] for g in C.groups("all", {held}) if g != "Neuron"}
    gs = list(parts)
    ref = np.ones(len(keys))
    curve = {}
    for k in range(1, len(gs) + 1):
        vals = []
        for _ in range(12 if k < len(gs) else 1):
            sub = rng.choice(gs, k, replace=False)
            P = np.stack([parts[g] for g in sub]); ok = np.isfinite(P); n = ok.sum(0)
            T = np.divide(np.where(ok, P, 0).sum(0), n, out=np.zeros(P.shape[1:], np.float32), where=n > 0)
            ref = np.sqrt((np.where(mask, T, 0) ** 2).sum(1))
            m = G.measures(T, y, ysd ** 2, x, mask, ref)
            vals.append((float(np.nanmean(m["cos"])), float(np.mean(m["pds"]))))
        curve[k] = [float(np.mean([v[0] for v in vals])), float(np.mean([v[1] for v in vals]))]
    res[held] = curve
    print(held, {k: [round(v[0], 3), round(v[1], 3)] for k, v in curve.items()}, flush=True)
Path("processed/guadagno_appreso_2026-10-05/diag_curva_r1.json").write_text(json.dumps(res, indent=1))
