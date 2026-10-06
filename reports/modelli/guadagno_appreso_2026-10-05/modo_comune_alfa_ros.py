"""Post-hoc: as modo_comune_alfa.py but with the official aggregations: MSE as ratio of sums over targets
(sum of debiased errors / sum of debiased truth energies, Delta space) and PDS as 1 - rank/n (random = 0.5)."""
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
    own = G.own_gene_cols(cube, keys)
    panel = np.zeros(len(cube.genes), bool); panel[own[own >= 0]] = True
    mask &= ~panel[None]                                   # official: every panel target gene out
    Yf = np.where(mask, np.nan_to_num(y), 0)
    Dy = np.where(mask, G.to_delta(Yf, x), 0)
    e = np.exp(np.clip(Yf, -10, 10)); noise = np.where(mask, (x[None] * e / (1 + x[None] * e)) ** 2 * np.nan_to_num(ysd) ** 2, 0).sum(1)
    yy = (Dy ** 2).sum(1) - noise
    Bn = Dy / np.maximum(np.linalg.norm(Dy, axis=1), 1e-12)[:, None]
    row = {}
    for amp in (0.5, 1.0, 1.576, 2.4):
        for al in (0.0, 0.1, 0.2, 0.3, 0.5, 1.0):
            P = amp * Tall + al * cL[None]
            Dp = np.where(mask, G.to_delta(P, x), 0)
            mse = float(((Dp - Dy) ** 2).sum(1).sum() - noise.sum()) / float(yy.sum())
            A = Dp / np.maximum(np.linalg.norm(Dp, axis=1), 1e-12)[:, None]
            dist = 1 - A @ Bn.T
            rank = (dist < np.diag(dist)[:, None]).sum(1) + 0.5 * ((dist == np.diag(dist)[:, None]).sum(1) - 1)
            pds = float(np.mean(1 - rank / len(keys)))
            row[f"T{amp}+c{al}"] = [round(pds, 3), round(mse, 3)]
    rec[L] = row
    print(L, json.dumps(row), flush=True)
out.write_text(json.dumps(rec, indent=1))
