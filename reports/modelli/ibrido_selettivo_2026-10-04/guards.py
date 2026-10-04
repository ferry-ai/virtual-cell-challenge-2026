"""Internal validation pairs and guards of the D-056 network (PROTOCOLLO.md §3 and §5), plain numpy.

A validation pair is a (training key, target) with an anchor; its cells pass through the batches with loss weight 0.
At every check the trainer hands over, per arm and per pair, the sums since the last check of the observed proportions,
of the predicted proportions with the network (softmax(beta + anchor + delta), no common head), with the anchor alone
(softmax(beta + anchor)) and with the baseline (softmax(beta)), and the number of cells. From them:

- shifts by the one estimator (cell_data.shift): observed against the key's control mean, N and A against the baseline;
- discrimination: in keys with at least `min_pairs` pairs, observed and predicted shifts centred on the key's mean over
  its pairs; for pair i the share of other pairs j of the key with mean|pred_i - obs_j| < mean|pred_i - obs_i| (0 is
  perfect); reported for N and A, and rank_N - rank_A;
- ratio: RMS(N - A) / RMS(A) over pairs and genes where both are defined;
- common share: per key, ||mean_i R_i||^2 / mean_i ||R_i||^2 with R = N - A, averaged over keys with equal weight;
- benefit: mean over pairs of cos(N_c, obs_c) - cos(A_c, obs_c) on the `top` genes with the largest |obs_c|, where _c
  is centred per key.

    choose_pairs(...)  -> the pairs, by hash
    check(...)         -> the metrics of one check and of one arm
    breaches(m, ...)   -> which conditions of PROTOCOLLO.md §5 a check breaks
"""
from __future__ import annotations

import hashlib
from collections import defaultdict

import numpy as np

SALT = "d056-val"


def pair_hash(key_name: str, symbol: str) -> float:
    h = hashlib.sha256(f"{SALT}|{key_name}|{symbol}".encode("utf-8")).hexdigest()
    return int(h[:15], 16) / 16 ** 15


def choose_pairs(candidates, frac: float, per_key: int, max_pairs: int) -> list[dict]:
    """candidates: (key_name, symbol, key_idx, tgt, admitted cells). The pairs with hash < frac, at most `per_key` per key
    (lowest hashes) and `max_pairs` in all (lowest hashes), in hash order."""
    scored = sorted((pair_hash(k, s), k, s, int(ki), int(t), int(n)) for k, s, ki, t, n in candidates)
    by_key = defaultdict(list)
    for c in scored:
        if c[0] < frac and len(by_key[c[1]]) < per_key:
            by_key[c[1]].append(c)
    kept = sorted(c for v in by_key.values() for c in v)[:max_pairs]
    return [{"key": k, "symbol": s, "key_idx": ki, "tgt": t, "admitted": n, "hash": round(u, 8)}
            for u, k, s, ki, t, n in kept]


def _shift(p, base, ok, eps=1e-9):
    good = ok & (p > 0) & (base > 0)
    out = np.zeros(p.shape)
    out[good] = np.log(p[good] + eps) - np.log(base[good] + eps)
    return out, good


def _cos(u, v):
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    return float(u @ v / (nu * nv)) if nu > 0 and nv > 0 else 0.0


def check(obs, pm, pa, pb, n, pair_keys, ctrl_mean, masks, min_cells=20, min_pairs=5, top=200) -> dict:
    """obs, pm, pa, pb [P, G] sums; n [P] cells; pair_keys [P] key of each pair; ctrl_mean [P, G] the control mean
    proportions of each pair's key; masks [P, G] the genes each pair's key measures. Returns the metrics."""
    obs, pm, pa, pb = (np.asarray(v, np.float64) for v in (obs, pm, pa, pb))
    n = np.asarray(n, np.float64)
    use = np.flatnonzero(n >= min_cells)
    out = {"pairs_used": int(use.size), "pairs": int(n.size), "cells_used": int(n[use].sum()) if use.size else 0}
    if not use.size:
        return {**out, "rank_N": None, "rank_A": None, "rank_diff": None, "ratio": None, "common_share": None,
                "benefit": None, "keys_used": 0}
    S_obs, S_N, S_A, OK = {}, {}, {}, {}
    for i in use:
        so, ok_o = _shift(obs[i] / n[i], ctrl_mean[i], masks[i])
        sn, ok_n = _shift(pm[i] / n[i], pb[i] / n[i], masks[i])
        sa, ok_a = _shift(pa[i] / n[i], pb[i] / n[i], masks[i])
        ok = ok_o & ok_n & ok_a
        S_obs[i], S_N[i], S_A[i], OK[i] = so, sn, sa, ok
    # ratio over every used pair
    num = sum(float(((S_N[i] - S_A[i])[OK[i]] ** 2).sum()) for i in use)
    den = sum(float((S_A[i][OK[i]] ** 2).sum()) for i in use)
    cnt = sum(int(OK[i].sum()) for i in use)
    out["ratio"] = float(np.sqrt(num / den)) if den > 0 else None
    out["rms_correction"] = float(np.sqrt(num / max(cnt, 1)))
    out["rms_anchor"] = float(np.sqrt(den / max(cnt, 1)))
    by_key = defaultdict(list)
    for i in use:
        by_key[pair_keys[i]].append(i)
    ranks_n, ranks_a, commons, benefits = [], [], [], []
    keys_used = 0
    for k, idx in by_key.items():
        if len(idx) < min_pairs:
            continue
        keys_used += 1
        ok = np.logical_and.reduce([OK[i] for i in idx])
        if ok.sum() < 2:
            continue
        O = np.stack([S_obs[i][ok] for i in idx])
        N = np.stack([S_N[i][ok] for i in idx])
        A = np.stack([S_A[i][ok] for i in idx])
        R = N - A
        e = (R ** 2).sum(1).mean()
        commons.append(float((R.mean(0) ** 2).sum() / e) if e > 0 else 0.0)
        Oc, Nc, Ac = O - O.mean(0), N - N.mean(0), A - A.mean(0)
        m = len(idx)
        for a, P in ((ranks_n, Nc), (ranks_a, Ac)):
            d = np.abs(P[:, None, :] - Oc[None, :, :]).mean(-1)          # d[i, j] = mean|pred_i - obs_j|
            own = np.diag(d)
            a.extend(((d < own[:, None]).sum(1) / (m - 1)).tolist())
        for j in range(m):
            t = np.argsort(-np.abs(Oc[j]))[:top]
            benefits.append(_cos(Nc[j, t], Oc[j, t]) - _cos(Ac[j, t], Oc[j, t]))
    out["keys_used"] = keys_used
    out["rank_N"] = float(np.mean(ranks_n)) if ranks_n else None
    out["rank_A"] = float(np.mean(ranks_a)) if ranks_a else None
    out["rank_diff"] = (out["rank_N"] - out["rank_A"]) if ranks_n else None
    out["common_share"] = float(np.mean(commons)) if commons else None
    out["benefit"] = float(np.mean(benefits)) if benefits else None
    return out


def breaches(m: dict, rank_margin=0.05, ratio_max=1.0, common_max=0.5) -> list[str]:
    """The conditions of PROTOCOLLO.md §5 that one check breaks (a metric that could not be computed breaks nothing)."""
    out = []
    if m.get("rank_diff") is not None and m["rank_diff"] > rank_margin:
        out.append("discrimination")
    if m.get("ratio") is not None and m["ratio"] > ratio_max:
        out.append("ratio")
    if m.get("common_share") is not None and m["common_share"] > common_max:
        out.append("common")
    return out
