import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, "kaggle_in/cube_r2_code"); sys.path.insert(0, "C:/Users/39346/virtual-cell-challenge-2026/reports/modelli/guadagno_appreso_2026-10-05")
import arms, guadagno as G
C = G.Cubes(arms, Path("kaggle_in/cube_r2_layout")); cube = C.cube
out = {}
for a_, b_ in [("k562_gwps","k562_essential"), ("k562_gwps","k562_viperturb"), ("cd4_rest","cd4_stim8hr"), ("h1_train","h1_val")]:
    keys = sorted(set(cube.keys_of(a_)) & set(cube.keys_of(b_)))
    keys = [k for k in keys if min(cube.cells(a_,[k])[0], cube.cells(b_,[k])[0]) >= 30][:400]
    if not keys: out[f"{a_}~{b_}"]={"keys":0}; continue
    A,_ = cube.get(a_,"raw",keys); B,_ = cube.get(b_,"raw",keys); Sa,_=cube.get(a_,"se",keys); Sb,_=cube.get(b_,"se",keys)
    bl = np.nanmean(np.vstack([cube.basal[a_], cube.basal[b_]]),0); x = 0.05*np.expm1(np.nan_to_num(bl))
    own = G.own_gene_cols(cube, keys)
    m = np.isfinite(A)&np.isfinite(B)&np.isfinite(bl)[None]
    for i,o in enumerate(own):
        if o>=0: m[i,o]=False
    Da = np.where(m, G.to_delta(np.nan_to_num(A),x),0); Db = np.where(m, G.to_delta(np.nan_to_num(B),x),0)
    def corr(D, Y, S):
        e = np.exp(np.clip(np.nan_to_num(Y),-10,10)); der = (x[None]*e/(1+x[None]*e))**2
        return (D**2).sum(1) - np.where(m, der*np.nan_to_num(S)**2, 0).sum(1)
    na, nb = corr(Da,A,Sa), corr(Db,B,Sb); cr=(Da*Db).sum(1); ok=(na>0)&(nb>0)
    c = cr[ok]/np.sqrt(na[ok]*nb[ok])
    out[f"{a_}~{b_}"] = {"keys": int(ok.sum()), "cos_debiased_both_mean": float(np.mean(c)), "median": float(np.median(c))}
print(json.dumps(out, indent=1))
