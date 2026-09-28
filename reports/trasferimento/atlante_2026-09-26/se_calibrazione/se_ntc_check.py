"""Calibrate effects_from_bulk's SE on non-targeting guides (pure noise) in Replogle bulk files."""
import sys
import h5py, numpy as np, pandas as pd
path = sys.argv[1]
phi = 0.2
with h5py.File(path, "r") as f:
    labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
    is_ntc = np.array(["non-targeting" in l for l in labels])
    rows = np.flatnonzero(is_ntc)
    X = f["X"][rows].astype(np.float64)
    n = f["obs/num_cells_filtered"][:][rows].astype(np.float64)
    good = np.isfinite(n) & (n >= 20)
    X, n, rows = X[good], n[good], rows[good]
print(path.split("/")[-1], "NTC rows:", len(rows), "cells per NTC row: median", np.median(n), "min", n.min(), "max", n.max())
print("X row sums (mean count per cell summed over genes): median", round(float(np.median(X.sum(axis=1))), 1),
      "; values integer-like?", bool(np.allclose(X[:5] * n[:5, None], np.round(X[:5] * n[:5, None]), atol=1e-3)))
rng = np.random.default_rng(0)
# split NTC rows: one row as the "target", the rest as control, for many rows; compare observed LFC^2 with predicted se^2
obs_sq, pred_sq, mu_all = [], [], []
for i in rng.choice(len(rows), size=min(200, len(rows)), replace=False):
    m = np.ones(len(rows), bool); m[i] = False
    ctrl_mu = (X[m] * n[m, None]).sum(axis=0) / n[m].sum()
    ctrl_frac = ctrl_mu / ctrl_mu.sum()
    n_ctrl = max(n[m].sum(), 1000.0)
    tot = n[i]
    mu = X[i]
    frac = mu / mu.sum()
    ok = (ctrl_frac >= 1e-6) & (mu > 0)
    eff = np.log(np.maximum(frac, 1e-7)) - np.log(np.maximum(ctrl_frac, 1e-7))
    se2 = 1.0 / (tot * np.maximum(mu, 1e-3)) + phi / tot + 1.0 / (n_ctrl * np.maximum(ctrl_mu, 1e-3)) + phi / n_ctrl
    obs_sq.append(np.where(ok, eff ** 2, np.nan)); pred_sq.append(np.where(ok, se2, np.nan)); mu_all.append(ctrl_mu)
O, P, M = np.array(obs_sq), np.array(pred_sq), np.array(mu_all).mean(axis=0)
bins = [0, 0.01, 0.03, 0.1, 0.3, 1, 3, 10, 1e9]
b = np.digitize(M, bins) - 1
print("control mean count/cell bin | genes | observed mean LFC^2 | predicted mean se^2 | ratio obs/pred")
for k in range(len(bins) - 1):
    g = b == k
    if g.sum() < 20: continue
    o, p = np.nanmean(O[:, g]), np.nanmean(P[:, g])
    print(f"  [{bins[k]}, {bins[k+1]}) {int(g.sum()):6d} {o:10.4f} {p:10.4f} {o/p:6.2f}")
