"""DIAGNOSI_TETTO_DE.md: DE-set members if only the top-N genes by a source-only confidence score are called (cube r2).

    python tetto_de.py --cube <layout> --code <cube code> --out <file.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guadagno as G  # noqa: E402
from tetto_pca import score as bulk_score  # noqa: E402

NS = (10, 20, 50, 100, 200, 500, 1000, 2000)
SCORES = ("mag", "z", "agree", "det")
LAMS = (0.5, 1.0, 1.576)


def reach_proxy(order, sgn_ok, inR, nR, floor=0.9):
    """Deepest k along `order` whose sign purity over the adjudicated genes (in R) is >= floor, over |R|."""
    if nR == 0:
        return np.nan
    adj = inR[order]
    ok = sgn_ok[order] & adj
    cum_adj = np.cumsum(adj)
    cum_ok = np.cumsum(ok)
    pur = np.divide(cum_ok, cum_adj, out=np.ones(len(order)), where=cum_adj > 0)
    good = np.where((pur >= floor) & (cum_adj > 0))[0]
    return float(cum_adj[good[-1]] / nR) if len(good) else 0.0


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
    rec = {"lines": {}}
    for L in G.HELD:
        ctx = G.Context(C, L)
        keys = G.eval_keys(C, L)
        st = G.transfer(C, "all", keys, ctx.commons, {L})
        keys = [k for k, s in zip(keys, st["n"].max(1) > 0) if s][:G.MAX_EVAL]
        st = G.transfer(C, "all", keys, ctx.commons, {L})
        T = np.nan_to_num(st["T"])
        seT = np.where(np.isfinite(st["se"]) & (st["se"] > 0), st["se"], np.inf)
        y, ysd, _ = G.truth(C, L, keys)
        bl = G.basal_of(cube, cube.tables_of(L))
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        mask = np.isfinite(bl)[None] & np.isfinite(y)
        own = G.own_gene_cols(cube, keys)
        panel = np.zeros(len(cube.genes), bool)
        panel[own[own >= 0]] = True
        mask &= ~panel[None]
        cpm_ok = (x / 0.05) >= 5
        R = mask & cpm_ok[None] & (np.abs(np.nan_to_num(y)) >= 3 * np.nan_to_num(ysd, nan=np.inf))
        sgn_ok = np.sign(T) == np.sign(np.nan_to_num(y))
        sc = {"mag": np.abs(T), "z": np.abs(T) / seT, "agree": np.abs(T) * st["agree"],
              "det": np.abs(T) * np.sqrt(x)[None]}
        avail = mask & (T != 0)
        K = len(keys)
        res = {}

        def sets_metrics(P):
            inter = (P & R).sum(1)
            union = (P | R).sum(1)
            nR = R.sum(1)
            jac = np.where(union > 0, inter / np.maximum(union, 1), 1.0)
            rec_ = np.where(nR > 0, inter / np.maximum(nR, 1), np.nan)
            sa = np.where(inter > 0, (P & R & sgn_ok).sum(1) / np.maximum(inter, 1), np.nan)
            return float(np.mean(jac)), float(np.nanmean(rec_)), float(np.nanmean(sa)), float(P.sum(1).mean())

        j, r, s, n = sets_metrics(avail)
        res["all_nonzero"] = {"jac": j, "recall": r, "sign_acc": s, "n_called": n}
        for name, S in sc.items():
            S = np.where(avail, S, -1.0)
            order = np.argsort(-S, axis=1)
            reach = float(np.nanmean([reach_proxy(order[i], sgn_ok[i], R[i], R[i].sum()) for i in range(K)]))
            res[f"{name}_order_reach"] = reach
            for N in NS:
                P = np.zeros_like(R)
                np.put_along_axis(P, order[:, :N], True, axis=1)
                P &= avail
                j, r, s, n = sets_metrics(P)
                res[f"{name}_N{N}"] = {"jac": j, "recall": r, "sign_acc": s, "n_called": n}
        # bulk cost of switching the other genes off (det score, N from the grid)
        Yf = np.where(mask, np.nan_to_num(y), 0)
        Dy = np.where(mask, G.to_delta(Yf, x), 0)
        e = np.exp(np.clip(Yf, -10, 10))
        noise = np.where(mask, (x[None] * e / (1 + x[None] * e)) ** 2 * np.nan_to_num(ysd) ** 2, 0).sum(1)
        yy = (Dy ** 2).sum(1) - noise
        bulk = {}
        order = np.argsort(-np.where(avail, sc["det"], -1.0), axis=1)
        for N in (None, 50, 200, 1000):
            keep = np.ones_like(R) if N is None else np.zeros_like(R)
            if N is not None:
                np.put_along_axis(keep, order[:, :N], True, axis=1)
            for lam in LAMS:
                Dp = np.where(mask, G.to_delta(lam * np.where(keep, T, 0), x), 0)
                bulk[f"det_N{N or 'all'}_l{lam}"] = bulk_score(Dp, Dy, yy, noise, mask)
        rec["lines"][L] = {"targets": K, "R_size_mean": float(R.sum(1).mean()), "R_size_median": float(np.median(R.sum(1))),
                           "sets": res, "bulk": bulk}
        best = max(((k, v) for k, v in res.items() if isinstance(v, dict)), key=lambda kv: kv[1]["jac"])
        print(L, K, "R mean", round(float(R.sum(1).mean()), 1), "| all_nonzero", {k: round(v, 3) for k, v in res["all_nonzero"].items()},
              "| best", best[0], {k: round(v, 3) for k, v in best[1].items()},
              "| reach", {s: round(res[f"{s}_order_reach"], 3) for s in SCORES}, flush=True)
        print("   bulk", {k: v for k, v in bulk.items() if k.endswith("l1.0")}, flush=True)
        a.out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    names = [k for k, v in next(iter(rec["lines"].values()))["sets"].items() if isinstance(v, dict) and k != "all_nonzero"]
    honest = {}
    for L in rec["lines"]:
        others = [o for o in rec["lines"] if o != L]
        pick = max(names, key=lambda n: np.mean([rec["lines"][o]["sets"][n]["jac"] for o in others]))
        got = rec["lines"][L]["sets"][pick]
        base = rec["lines"][L]["sets"]["all_nonzero"]["jac"]
        honest[L] = {"pick": pick, **{k: round(v, 4) for k, v in got.items()}, "ratio_vs_all": round(got["jac"] / max(base, 1e-9), 2)}
    rec["honest"] = honest
    rec["reading"] = {"lines_ratio_ge_3": sum(v["ratio_vs_all"] >= 3 for v in honest.values()),
                      "mean_jac": round(float(np.mean([v["jac"] for v in honest.values()])), 4)}
    a.out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print("honest", json.dumps(honest), "\nreading", rec["reading"], flush=True)


if __name__ == "__main__":
    main()
