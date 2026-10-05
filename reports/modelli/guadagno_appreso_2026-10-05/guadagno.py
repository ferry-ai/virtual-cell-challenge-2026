"""Learned gain on the `all` transfer (PROTOCOLLO.md in this folder): stage 1 on Davide's bench cube r2.

Arms per held-out line group L (regime C): prod, all, centrato (diagnostic), guadagno (g * T_all, g = softplus(MLP)).
Measures in the scorer's pseudobulk geometry (log1p of counts at 5e4): debiased cosine with L's truth, a PDS index,
the normalised MSE at the recipe's norm; paired bootstrap over targets; the registered rule.

    python guadagno.py --cube <cube folder: table/{raw,se,shrunk}.npy> --code <Davide's cube code> --out <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

HELD = ("H1", "HepG2", "RPE1", "Jurkat", "K562")
PRODUCTION_TABLES = ("k562_gwps", "cd4_rest", "cd4_stim8hr", "cd4_stim48hr", "hct116", "hek293t")
AMP = 1.576
MIN_TRUTH_CELLS, MAX_EVAL, MIN_TRAIN_KEYS, MAX_TRAIN_KEYS, GENES_PER_KEY = 30, 400, 50, 300, 4000
F32 = np.float32


def hkey(k: str, salt: str) -> str:
    return hashlib.sha256(f"{k}|{salt}".encode()).hexdigest()


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Cubes:
    """Davide's Cube plus the source rules of anchors.source_cube ('all' = every table, 'production')."""

    def __init__(self, arms, folder: Path):
        self.arms = arms
        self.cube = arms.Cube(folder, min_cells=10)
        c = self.cube
        self.prod_tables = [t for t in c.tables if t in PRODUCTION_TABLES]

    def tables(self, group: str, rule: str) -> list[str]:
        ts = self.cube.tables_of(group)
        return ts if rule == "all" else [t for t in ts if t in self.prod_tables]

    def groups(self, rule: str, exclude: set) -> list[str]:
        return [g for g in self.cube.groups if g not in exclude and self.tables(g, rule)]


def table_means(cube, exclude_groups: set, block: int = 1000) -> dict:
    """arms.table_means / anchors.j_table_means with no forbidden key: mean shrunk per source table."""
    out = {}
    G = len(cube.genes)
    for t in cube.tables:
        if cube.group[t] in exclude_groups:
            continue
        keys = cube.keys_of(t)
        s, n = np.zeros(G), np.zeros(G)
        for b0 in range(0, len(keys), block):
            x, _ = cube.get(t, "shrunk", keys[b0:b0 + block])
            ok = np.isfinite(x)
            s += np.where(ok, x, 0).sum(0)
            n += ok.sum(0)
        out[t] = np.divide(s, n, out=np.zeros(G), where=n > 0).astype(F32)
    return out


def group_stats(C: Cubes, group: str, rule: str, keys, commons: dict, kind: str = "shrunk", gamma: float = 1.0):
    """arms.group_mean (reliability n/(n+100) within the group) and the SE of that weighted mean, from the se arrays."""
    cube = C.cube
    G = len(cube.genes)
    num = np.zeros((len(keys), G), F32)
    den = np.zeros((len(keys), G), F32)
    var = np.zeros((len(keys), G), F32)
    cells = np.zeros(len(keys))
    for t in C.tables(group, rule):
        x, have = cube.get(t, kind, keys, purpose="fit" if kind == "shrunk" else "truth")
        if not have.any():
            continue
        se, _ = cube.get(t, "se", keys, purpose="fit" if kind == "shrunk" else "truth")
        x, se = x[have], se[have]
        if gamma:
            x = x - gamma * commons[t][None, :]
        n = cube.cells(t, keys)[have]
        cells[have] += n
        w = (n / (n + 100.0)).astype(F32)
        ok = np.isfinite(x)
        num[have] += np.where(ok, x * w[:, None], 0)
        den[have] += np.where(ok, w[:, None], 0)
        var[have] += np.where(ok & np.isfinite(se), (w[:, None] * se) ** 2, 0)
    mean = np.divide(num, den, out=np.full_like(num, np.nan), where=den > 0)
    sd = np.divide(np.sqrt(var), den, out=np.full_like(num, np.nan), where=den > 0)
    return mean, sd, cells


def transfer(C: Cubes, rule: str, keys, commons: dict, exclude: set) -> dict:
    """T = equal-weight mean over source groups of their group means (arms.combine_groups), with per-pair stats."""
    parts, ses, cells = [], [], np.zeros(len(keys))
    for g in C.groups(rule, exclude):
        m, s, c = group_stats(C, g, rule, keys, commons)
        parts.append(m)
        ses.append(s)
        cells += c
    P = np.stack(parts)                     # (groups, keys, genes)
    ok = np.isfinite(P)
    n = ok.sum(0)
    T = np.divide(np.where(ok, P, 0).sum(0), n, out=np.full(P.shape[1:], np.nan, F32), where=n > 0)
    absum = np.where(ok, np.abs(P), 0).sum(0)
    agree = np.divide(np.abs(np.where(ok, P, 0).sum(0)), absum, out=np.ones_like(T), where=absum > 0)
    dev = np.sqrt(np.divide(np.where(ok, (P - np.nan_to_num(T)[None]) ** 2, 0).sum(0), n,
                            out=np.zeros_like(T), where=n > 0))
    S = np.stack(ses)
    se_T = np.divide(np.sqrt(np.where(ok & np.isfinite(S), S ** 2, 0).sum(0)), n, out=np.full_like(T, np.nan), where=n > 0)
    return {"T": T, "n": n.astype(F32), "agree": agree.astype(F32), "dev": dev.astype(F32), "se": se_T.astype(F32),
            "cells": cells, "groups": C.groups(rule, exclude)}


def truth(C: Cubes, group: str, keys):
    """L's raw effect: within-group reliability-weighted mean of its tables' raw (no common term), and its SE."""
    m, s, cells = group_stats(C, group, "all", keys, {}, kind="raw", gamma=0.0)
    return m, s, cells


def basal_of(cube, tables) -> np.ndarray:
    return np.nanmean(np.vstack([cube.basal[t] for t in tables]), 0).astype(F32)


def to_delta(f: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Pseudobulk log1p change at 5e4 total counts for ln fold change f, x = 0.05 * CPM of the controls."""
    return (np.log1p(x[None, :] * np.exp(np.clip(f, -10, 10))) - np.log1p(x)[None, :]).astype(F32)


def features(st: dict, basal_line: np.ndarray, basal_src: np.ndarray, common_abs: np.ndarray) -> np.ndarray:
    T = np.nan_to_num(st["T"])
    a = np.abs(T)
    K, G = T.shape
    norm = np.log(np.sqrt((T ** 2).sum(1)) + 1e-3)
    f = [a, st["n"], st["agree"], np.log((st["dev"] + 1e-3) / (a + 0.01)),
         np.log((a + 1e-4) / (np.nan_to_num(st["se"], nan=1.0) + 1e-4)),
         np.broadcast_to(np.nan_to_num(basal_line)[None], (K, G)), np.broadcast_to(np.nan_to_num(basal_src)[None], (K, G)),
         np.broadcast_to(common_abs[None], (K, G)), np.broadcast_to(norm[:, None], (K, G)),
         np.broadcast_to(np.log1p(st["cells"])[:, None], (K, G))]
    return np.stack(f, -1).astype(F32)


class Context:
    """Everything one held-out line needs, computed only from the sources and L's controls."""

    def __init__(self, C: Cubes, held: str):
        cube = C.cube
        self.held = held
        self.commons = table_means(cube, {held})
        self.src_tables = [t for t in cube.tables if cube.group[t] != held]
        self.common_abs = np.mean([np.abs(self.commons[t]) for t in self.src_tables], 0).astype(F32)


def eval_keys(C: Cubes, held: str) -> list[str]:
    cube = C.cube
    keys = sorted({k for t in cube.tables_of(held) for k in cube.keys_of(t)})
    cells = np.zeros(len(keys))
    for t in cube.tables_of(held):
        cells += cube.cells(t, keys)
    keys = [k for k, c in zip(keys, cells) if c >= MIN_TRUTH_CELLS]
    return sorted(keys, key=lambda k: hkey(k, "guadagno"))


def own_gene_cols(cube, keys) -> np.ndarray:
    return np.array([cube.gpos.get(cube.symbol.get(k, ""), -1) for k in keys])


def training_set(C: Cubes, ctx: Context, rng, log):
    """Rows of every group h != L with >= 50 keys: T without L and h, y = raw of h, controls of h."""
    cube = C.cube
    X, Y, W, Tv = [], [], [], []
    for h in cube.groups:
        if h == ctx.held:
            continue
        keys = sorted({k for t in cube.tables_of(h) for k in cube.keys_of(t)}, key=lambda k: hkey(k, "fit"))
        if len(keys) < MIN_TRAIN_KEYS:
            log(f"  train group {h}: {len(keys)} keys, skipped")
            continue
        keys = keys[:MAX_TRAIN_KEYS]
        st = transfer(C, "all", keys, ctx.commons, {ctx.held, h})
        y, _, _ = truth(C, h, keys)
        bl = basal_of(cube, cube.tables_of(h))
        src = [t for t in cube.tables if cube.group[t] not in (ctx.held, h)]
        feats = features(st, bl, basal_of(cube, src), ctx.common_abs)
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        w = (x / (1 + x)) ** 2
        own = own_gene_cols(cube, keys)
        G = len(cube.genes)
        n0 = 0
        for i in range(len(keys)):
            cols = rng.choice(G, size=min(GENES_PER_KEY, G), replace=False)
            ok = np.isfinite(st["T"][i, cols]) & (st["T"][i, cols] != 0) & np.isfinite(y[i, cols]) & (cols != own[i]) \
                & np.isfinite(bl[cols])
            cols = cols[ok]
            X.append(feats[i, cols]); Y.append(y[i, cols]); W.append(w[cols]); Tv.append(st["T"][i, cols])
            n0 += len(cols)
        log(f"  train group {h}: {len(keys)} keys, {n0} pairs, sources {st['groups']}")
    return np.concatenate(X), np.concatenate(Y), np.concatenate(W), np.concatenate(Tv)


def fit_gain(X, Y, W, Tv, log, seed: int = 0):
    import torch
    torch.manual_seed(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    mu, sd = X.mean(0), X.std(0) + 1e-6
    net = torch.nn.Sequential(torch.nn.Linear(X.shape[1], 32), torch.nn.ReLU(), torch.nn.Linear(32, 32),
                              torch.nn.ReLU(), torch.nn.Linear(32, 1)).to(dev)
    with torch.no_grad():
        net[-1].weight.zero_()
        net[-1].bias.fill_(float(np.log(np.e - 1)))      # softplus(b) = 1
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    Xt = torch.tensor((X - mu) / sd, dtype=torch.float32)
    Yt, Wt, Tt = (torch.tensor(v, dtype=torch.float32) for v in (Y, W, Tv))
    g = torch.Generator().manual_seed(seed)
    B = 65536
    for ep in range(4):
        perm = torch.randperm(len(Xt), generator=g)
        tot = 0.0
        for b0 in range(0, len(perm), B):
            idx = perm[b0:b0 + B]
            gain = torch.nn.functional.softplus(net(Xt[idx].to(dev))).squeeze(1)
            loss = (Wt[idx].to(dev) * (gain * Tt[idx].to(dev) - Yt[idx].to(dev)) ** 2).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += float(loss) * len(idx)
        log(f"  epoch {ep}: weighted loss {tot / len(perm):.6g}")
    base = float((W * (Tv - Y) ** 2).mean())
    log(f"  reference loss at g = 1: {base:.6g}")
    net = net.cpu().eval()

    def apply(F: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            z = torch.tensor((F.reshape(-1, F.shape[-1]) - mu) / sd, dtype=torch.float32)
            out = torch.cat([torch.nn.functional.softplus(net(z[i:i + 262144])).squeeze(1)
                             for i in range(0, len(z), 262144)])
        return out.numpy().reshape(F.shape[:-1]).astype(F32)
    return apply, {"loss_final": tot / len(perm), "loss_g1": base}


def measures(P: np.ndarray, Y: np.ndarray, var: np.ndarray, x: np.ndarray, mask: np.ndarray, scale_ref: np.ndarray):
    """Per-target debiased cosine, PDS index, normalised MSE at the reference norm x 1.576; all in Delta space."""
    K = len(P)
    P0 = np.where(mask, np.nan_to_num(P), 0)
    nP = np.sqrt((P0 ** 2).sum(1))
    Pn = P0 * np.divide(scale_ref * AMP, nP, out=np.zeros_like(nP), where=nP > 0)[:, None]
    Dp = np.where(mask, to_delta(Pn, x), 0)
    Yf = np.where(mask, np.nan_to_num(Y), 0)
    Dy = np.where(mask, to_delta(Yf, x), 0)
    deriv = (x[None] * np.exp(np.clip(Yf, -10, 10)) / (1 + x[None] * np.exp(np.clip(Yf, -10, 10)))) ** 2
    noise = np.where(mask, deriv * np.nan_to_num(var), 0).sum(1)
    yy = (Dy ** 2).sum(1) - noise
    pp = (Dp ** 2).sum(1)
    cross = (Dp * Dy).sum(1)
    valid = (yy > 0) & (pp > 0)
    cos = np.where(valid, cross / np.sqrt(np.where(valid, pp * yy, 1)), np.nan)
    mse = np.where(valid, (pp - 2 * cross + (Dy ** 2).sum(1) - noise) / np.where(valid, yy, 1), np.nan)
    # PDS index: cosine distance of each prediction to every truth; quota of other targets closer than its own
    A = Dp / np.maximum(np.sqrt(pp), 1e-12)[:, None]
    Bm = Dy / np.maximum(np.sqrt((Dy ** 2).sum(1)), 1e-12)[:, None]
    d = 1 - A @ Bm.T
    own = np.diag(d)
    closer = (d < own[:, None]).sum(1)
    pds = 1 - 2 * closer / max(K - 1, 1)
    return {"cos": cos, "pds": pds.astype(float), "mse": mse}


def boot_diff(a: np.ndarray, b: np.ndarray, rng, n: int = 2000):
    ok = np.isfinite(a) & np.isfinite(b)
    d = (a - b)[ok]
    if not len(d):
        return {"mean": None, "lo90": None, "hi90": None, "n": 0}
    idx = rng.integers(0, len(d), (n, len(d)))
    m = d[idx].mean(1)
    return {"mean": float(d.mean()), "lo90": float(np.quantile(m, 0.05)), "hi90": float(np.quantile(m, 0.95)),
            "n": int(len(d))}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cube", type=Path, required=True)
    ap.add_argument("--code", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--held", default=",".join(HELD))
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    a.out.mkdir(parents=True)
    logf = open(a.out / "run.log", "w", encoding="utf-8")

    def log(s):
        line = f"{time.strftime('%H:%M:%S')} {s}"
        print(line, flush=True)
        logf.write(line + "\n"); logf.flush()

    sys.path.insert(0, str(a.code))
    import arms
    C = Cubes(arms, a.cube)
    cube = C.cube
    record = {"cube_manifest_sha256": sha(a.cube / "manifest.json"), "groups": cube.groups,
              "genes": len(cube.genes), "lines": {}}
    rng_boot = np.random.default_rng(0)
    import pandas as pd
    kc = pd.read_csv(a.cube / "keys.csv")
    strata = dict(zip(kc["target_key"].astype(str), kc["stratum"].astype(str)))
    for held in a.held.split(","):
        t0 = time.time()
        log(f"== {held}")
        ctx = Context(C, held)
        keys = eval_keys(C, held)
        st_all = transfer(C, "all", keys, ctx.commons, {held})
        sup = st_all["n"].max(1) > 0
        keys = [k for k, s in zip(keys, sup) if s][:MAX_EVAL]
        st_all = transfer(C, "all", keys, ctx.commons, {held})
        st_prod = transfer(C, "production", keys, ctx.commons, {held})
        # parity with Davide's transfer_for = combine_groups(group_mean(...)) on 20 keys
        pk = keys[:20]
        ref, _ = arms.combine_groups([arms.group_mean(cube, g, pk, ctx.commons) for g in C.groups("all", {held})])
        mine = st_all["T"][:20]
        if not np.allclose(np.nan_to_num(ref, nan=9), np.nan_to_num(mine, nan=9), atol=1e-5):
            raise SystemExit(f"{held}: transfer parity failed")
        y, ysd, ycells = truth(C, held, keys)
        bl = basal_of(cube, cube.tables_of(held))
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        own = own_gene_cols(cube, keys)
        mask = np.isfinite(bl)[None, :] & np.isfinite(y)
        for i, o in enumerate(own):
            if o >= 0:
                mask[i, o] = False
        Tall = np.nan_to_num(st_all["T"])
        ref_norm = np.sqrt((np.where(mask, Tall, 0) ** 2).sum(1))
        log(f"  {len(keys)} targets, sources all {st_all['groups']}, prod {st_prod['groups']}; parity ok")
        rng = np.random.default_rng(0)
        X, Y, W, Tv = training_set(C, ctx, rng, log)
        apply, fitinfo = fit_gain(X, Y, W, Tv, log)
        del X, Y, W, Tv
        src = [t for t in cube.tables if cube.group[t] != held]
        g = apply(features(st_all, bl, basal_of(cube, src), ctx.common_abs))
        arms_pred = {"prod": np.nan_to_num(st_prod["T"]), "all": Tall,
                     "centrato": Tall - Tall.mean(0, keepdims=True), "guadagno": g * Tall}
        var = ysd ** 2
        res = {name: measures(P, y, var, x, mask, ref_norm) for name, P in arms_pred.items()}
        stratum = np.array([strata.get(k, "") for k in keys])
        line = {"targets": len(keys), "truth_cells_median": float(np.median(ycells)),
                "sources_all": st_all["groups"], "sources_prod": st_prod["groups"], "fit": fitinfo,
                "gain_quantiles": np.quantile(g[mask & (Tall != 0)], [0.05, 0.25, 0.5, 0.75, 0.95]).tolist(),
                "arms": {n: {m: float(np.nanmean(v)) for m, v in r.items()} | {"cos_excluded": int(np.isnan(r["cos"]).sum())}
                         for n, r in res.items()},
                "diff": {}}
        for (p, q) in (("guadagno", "all"), ("all", "prod"), ("centrato", "all")):
            line["diff"][f"{p}-{q}"] = {m: boot_diff(res[p][m], res[q][m], rng_boot) for m in ("cos", "pds", "mse")}
            for s in ("panel", "essential"):
                sel = stratum == s
                line["diff"][f"{p}-{q}"][f"cos_{s}"] = boot_diff(res[p]["cos"][sel], res[q]["cos"][sel], rng_boot)
        line["per_target"] = {"keys": keys, **{f"{n}_{m}": [None if not np.isfinite(v) else float(v) for v in r[m]]
                                               for n, r in res.items() for m in ("cos", "pds")}}
        record["lines"][held] = line
        log(f"  arms: " + json.dumps({n: {m: round(v, 4) for m, v in d.items()} for n, d in line["arms"].items()}))
        log(f"  guadagno-all: " + json.dumps(line["diff"]["guadagno-all"]))
        log(f"  {time.time() - t0:.0f} s")
        (a.out / "result.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    record["rule"] = rule(record)
    (a.out / "result.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    log("rule: " + json.dumps(record["rule"]))


def rule(record: dict) -> dict:
    lines = record["lines"]
    above, diffs, pds_ok = [], [], []
    for L, d in lines.items():
        c = d["diff"]["guadagno-all"]["cos"]
        p = d["diff"]["guadagno-all"]["pds"]
        diffs.append(c["mean"])
        above.append(c["mean"] is not None and c["mean"] >= 0.02 and c["lo90"] > 0)
        pds_ok.append(p["mean"] is not None and p["mean"] >= -0.01)
    passed = sum(above) >= 4 and float(np.mean(diffs)) >= 0.03 and all(pds_ok) and len(lines) == 5
    return {"lines_above": int(sum(above)), "mean_cos_diff": float(np.mean(diffs)), "pds_ok_all": bool(all(pds_ok)),
            "n_lines": len(lines), "passed": bool(passed)}


if __name__ == "__main__":
    main()
