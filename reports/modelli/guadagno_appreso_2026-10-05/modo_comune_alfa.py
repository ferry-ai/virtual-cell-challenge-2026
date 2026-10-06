"""Post-hoc reading of DIAGNOSI_MODO_COMUNE.md: T_all + alpha * c_L (oracle common) for a grid of alpha; cosine, PDS
index and median normalised MSE at the arm's own scale. Declared after the registered reading."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guadagno as G
from modo_comune import raw_common
cube_dir, code_dir, out = map(Path, sys.argv[1:4])
sys.path.insert(0, str(code_dir))
import arms
C = G.Cubes(arms, cube_dir); cube = C.cube; rec = {}
for L in G.HELD:
    ctx = G.Context(C, L)
    keys = G.eval_keys(C, L)
    st = G.transfer(C, "all", keys, ctx.commons, {L})
    keys = [k for k, s in zip(keys, st["n"].max(1) > 0) if s][:G.MAX_EVAL]
    Tall = np.nan_to_num(G.transfer(C, "all", keys, ctx.commons, {L})["T"])
    cL = np.nan_to_num(raw_common(cube, cube.tables_of(L)))
    y, ysd, _ = G.truth(C, L, keys)
    bl = G.basal_of(cube, cube.tables_of(L)); x = 0.05 * np.expm1(np.nan_to_num(bl))
    mask = np.isfinite(bl)[None] & np.isfinite(y)
    for i, o in enumerate(G.own_gene_cols(cube, keys)):
        if o >= 0: mask[i, o] = False
    row = {}
    for amp in (1.0, 1.576, 2.4):
        for al in (0.0, 0.1, 0.2, 0.3, 0.5, 1.0):
            P = amp * Tall + al * cL[None]
            ref = np.sqrt((np.where(mask, P, 0) ** 2).sum(1)) / G.AMP
            m = G.measures(P, y, ysd ** 2, x, mask, ref)
            row[f"T{amp}+c{al}"] = [round(float(np.nanmean(m["cos"])), 3), round(float(np.mean(m["pds"])), 3),
                                    round(float(np.nanmedian(m["mse"])), 3)]
    rec[L] = row
    print(L, json.dumps(row), flush=True)
out.write_text(json.dumps(rec, indent=1))
