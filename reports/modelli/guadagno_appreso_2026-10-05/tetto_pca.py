"""DIAGNOSI_TETTO_PCA.md: ceiling of projecting the all transfer on a basis of the source effects (cube r2).

    python tetto_pca.py --cube <layout> --code <cube code> --out <file.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guadagno as G  # noqa: E402

KS = (5, 10, 20, 50, 100, 200)
LAMS = (0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.576, 2.4)
PER_GROUP = 1500


def basis(C, ctx, held, torch, dev, kmax):
    """Top right singular vectors of the stacked source group means (all rule, L excluded), keys hashed per group."""
    cube = C.cube
    rows = []
    for g in C.groups("all", {held}):
        keys = sorted({k for t in C.tables(g, "all") for k in cube.keys_of(t)}, key=lambda k: G.hkey(k, "pca"))
        keys = keys[:PER_GROUP]
        m, _, _ = G.group_stats(C, g, "all", keys, ctx.commons)
        m = np.nan_to_num(m)
        rows.append(m[np.abs(m).sum(1) > 0])
    M = torch.tensor(np.vstack(rows), device=dev)
    _, s, V = torch.svd_lowrank(M, q=kmax + 20, niter=4)
    return V[:, :kmax].cpu().numpy(), s[:kmax].cpu().numpy(), int(M.shape[0])


def score(Dp, Dy, yy, noise, mask):
    mse = float(((Dp - Dy) ** 2).sum() - noise.sum()) / float(yy.sum())
    c = float((Dp * Dy).sum() / np.sqrt((Dp ** 2).sum() * yy.sum()))
    A = Dp / np.maximum(np.linalg.norm(Dp, axis=1), 1e-12)[:, None]
    Bn = Dy / np.maximum(np.linalg.norm(Dy, axis=1), 1e-12)[:, None]
    dist = 1 - A @ Bn.T
    d0 = np.diag(dist)[:, None]
    rank = (dist < d0).sum(1) + 0.5 * ((dist == d0).sum(1) - 1)
    return {"mse": round(mse, 4), "pds": round(float(np.mean(1 - rank / len(Dp))), 4), "c": round(c, 4)}


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
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    C = G.Cubes(arms, a.cube)
    cube = C.cube
    rec = {"lines": {}}
    for L in G.HELD:
        ctx = G.Context(C, L)
        keys = G.eval_keys(C, L)
        st = G.transfer(C, "all", keys, ctx.commons, {L})
        keys = [k for k, s in zip(keys, st["n"].max(1) > 0) if s][:G.MAX_EVAL]
        T = np.nan_to_num(G.transfer(C, "all", keys, ctx.commons, {L})["T"])
        V, sv, nrows = basis(C, ctx, L, torch, dev, max(KS))
        y, ysd, _ = G.truth(C, L, keys)
        bl = G.basal_of(cube, cube.tables_of(L))
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        mask = np.isfinite(bl)[None] & np.isfinite(y)
        own = G.own_gene_cols(cube, keys)
        panel = np.zeros(len(cube.genes), bool)
        panel[own[own >= 0]] = True
        mask &= ~panel[None]                               # official: every panel target gene out
        Yf = np.where(mask, np.nan_to_num(y), 0)
        Dy = np.where(mask, G.to_delta(Yf, x), 0)
        e = np.exp(np.clip(Yf, -10, 10))
        noise = np.where(mask, (x[None] * e / (1 + x[None] * e)) ** 2 * np.nan_to_num(ysd) ** 2, 0).sum(1)
        yy = (Dy ** 2).sum(1) - noise
        grid = {}
        for k in (None,) + KS:
            P0 = T if k is None else (T @ V[:, :k]) @ V[:, :k].T
            for lam in LAMS:
                Dp = np.where(mask, G.to_delta(lam * P0, x), 0)
                grid[f"k{k or 'none'}_l{lam}"] = score(Dp, Dy, yy, noise, mask)
        rec["lines"][L] = {"targets": len(keys), "basis_rows": nrows, "sv_top10": [float(v) for v in sv[:10]],
                           "grid": grid}
        best = min(grid.items(), key=lambda kv: kv[1]["mse"])
        print(L, len(keys), "none@1.576", grid["knone_l1.576"], "| best", best, flush=True)
        a.out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    # honest pick: (k, lambda) minimising the mean MSE on the other four lines
    names = list(next(iter(rec["lines"].values()))["grid"])
    honest = {}
    for L in rec["lines"]:
        others = [o for o in rec["lines"] if o != L]
        pick = min(names, key=lambda n: np.mean([rec["lines"][o]["grid"][n]["mse"] for o in others]))
        ref = rec["lines"][L]["grid"]["knone_l1.576"]
        got = rec["lines"][L]["grid"][pick]
        honest[L] = {"pick": pick, **got, "pds_vs_all_prod_amp": round(got["pds"] - ref["pds"], 4)}
    rec["honest"] = honest
    rec["reading"] = {
        "lines_mse_le_0.95": sum(v["mse"] <= 0.95 for v in honest.values()),
        "lines_pds_not_below_-0.01": sum(v["pds_vs_all_prod_amp"] >= -0.01 for v in honest.values())}
    a.out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print("honest", json.dumps(honest), "\nreading", rec["reading"], flush=True)


if __name__ == "__main__":
    main()
