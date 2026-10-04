"""Rete L1 (PROTOCOLLO.md): an MLP trained with the nMAE-weighted L1 loss on the DE genes of the arrival line, so it
estimates the conditional median log2FC of a gene given that it is DE. Bench (leave-one-group-out), final fit, and
the export of the per-gene targets for A, B, C.

Usage:
  python rete_l1.py bench  --keys <chiavi> --extra <extra chiavi> --out <dir> --controls <raw/controls>
  python rete_l1.py export --keys <chiavi> --extra <extra chiavi> --out <dir> --steps N --controls <raw/controls>
                           --targets-out <data root>/processed/l1_obiettivi_<date>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

LN2 = np.log(2.0)
SOURCE = "replogle_k562_gwps|K562"
EXCLUDED = {"replogle_k562_essential|K562"}
ORDER = ["h1", "kolf", "rpe1", "hepg2", "jurkat", "hipsci", "tian"]
DEPTH, N_CTRL, Z_GATE, MIN_GATE, MIN_CPM = 1.5e4, 5000, 3.0, 10, 5.0
UNCOVERED_PER_LINE = 60
N_FEAT = 10


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def group_of(g: str) -> str:
    return "tian" if g.startswith("tian") else g


def cpm_of(basal: np.ndarray) -> np.ndarray:
    return np.expm1(basal.astype(np.float64)) * 100.0  # basal = log1p(1e4-normalized mean)


class Source:
    """K562 gwps: log2FC, per-gene priors and per-target strength."""

    def __init__(self, path: Path):
        z = np.load(path, allow_pickle=False)
        self.targets = list(map(str, z["targets"]))
        self.row = {t: i for i, t in enumerate(self.targets)}
        self.meas = np.asarray(z["measured"])
        self.k = np.where(self.meas[None, :], np.nan_to_num(z["eff"].astype(np.float32)), 0.0) / np.float32(LN2)
        self.n = z["n_cells"].astype(np.float64)
        self.cpm = cpm_of(z["basal"])
        k = self.k
        self.prior_mean = k.mean(0)
        big = np.abs(k) > 0.3
        up = ((k > 0.3).sum(0) + 1.0) / (big.sum(0) + 2.0)
        self.prior_up = (up - 0.5).astype(np.float32)
        self.strength = np.log1p((np.abs(k) > 0.5).sum(1)).astype(np.float32)


def features(src: Source, target: str | None, line_cpm: np.ndarray, genes: np.ndarray) -> np.ndarray:
    """N_FEAT features for one target over the given gene indices."""
    f = np.zeros((len(genes), N_FEAT), np.float32)
    lc = np.log10(line_cpm[genes] + 1.0)
    kc = np.log10(src.cpm[genes] + 1.0)
    f[:, 3] = src.prior_mean[genes] * 4.0
    f[:, 4] = src.prior_up[genes] * 2.0
    f[:, 6] = lc
    f[:, 7] = kc
    f[:, 9] = src.meas[genes]
    if target is not None and target in src.row:
        i = src.row[target]
        k = src.k[i, genes]
        snr = np.abs(k) * LN2 * np.sqrt(src.n[i] * src.cpm[genes] * DEPTH / 1e6)
        f[:, 0] = k
        f[:, 1] = np.abs(k)
        f[:, 2] = np.sign(k) * np.log1p(snr)
        f[:, 5] = src.strength[i]
        f[:, 8] = 1.0
    return f


def load_lines(keys: Path, extra: Path):
    lines = []
    for d in (keys, extra):
        for p in sorted(d.glob("*.npz")):
            z = np.load(p, allow_pickle=False)
            key = str(z["key"])
            if key == SOURCE or key in EXCLUDED:
                continue
            lines.append({"key": key, "group": group_of(str(z["group"])), "path": p})
    return lines


def line_rows(src: Source, ln: dict, rng: np.random.Generator, gpos: dict):
    """Training rows of one arrival line: (X, y, target id, n targets) on the DE-gate proxy."""
    z = np.load(ln["path"], allow_pickle=False)
    meas = np.asarray(z["measured"])
    cpm = cpm_of(z["basal"])
    ok_gene = meas & (cpm >= MIN_CPM)
    targets = list(map(str, z["targets"]))
    covered = [i for i, t in enumerate(targets) if t in src.row]
    unc = [i for i, t in enumerate(targets) if t not in src.row]
    unc = list(rng.permutation(unc)[:UNCOVERED_PER_LINE]) if unc else []
    X, Y, T = [], [], []
    for i in covered + unc:
        y = z["eff"][i].astype(np.float64)
        n = float(z["n_cells"][i])
        se = np.sqrt((1.0 / max(n, 1.0) + 1.0 / N_CTRL) / np.maximum(cpm * DEPTH / 1e6, 1e-12))
        gate = ok_gene & np.isfinite(y) & (np.abs(y) >= Z_GATE * se) & (y != 0)
        if targets[i] in gpos:  # the knocked-down gene's own row leaves the gate, as in the scorer
            gate[gpos[targets[i]]] = False
        if gate.sum() < MIN_GATE:
            continue
        g = np.where(gate)[0]
        X.append(features(src, targets[i], cpm, g))
        Y.append((y[g] / LN2).astype(np.float32))
        T.append(np.full(len(g), len(T), np.int32))
    if not X:
        return None
    return np.concatenate(X), np.concatenate(Y), np.concatenate(T), len(X)


class Net(nn.Module):
    def __init__(self, h: int = 64):
        super().__init__()
        self.f = nn.Sequential(nn.Linear(N_FEAT, h), nn.GELU(), nn.Linear(h, h), nn.GELU(), nn.Linear(h, 1))

    def forward(self, x):
        return self.f(x).squeeze(-1)


def weights(y: np.ndarray, t: np.ndarray, n_t: int) -> np.ndarray:
    """nMAE weight per row: each target counts once, scaled by its own mean |y|."""
    cnt = np.bincount(t, minlength=n_t).astype(np.float64)
    den = np.bincount(t, weights=np.abs(y), minlength=n_t) / np.maximum(cnt, 1)
    return (1.0 / (cnt[t] * den[t] * n_t)).astype(np.float32)


def nmae_per_target(pred: np.ndarray, y: np.ndarray, t: np.ndarray, n_t: int) -> np.ndarray:
    num = np.bincount(t, weights=np.abs(pred - y), minlength=n_t)
    den = np.bincount(t, weights=np.abs(y), minlength=n_t)
    return num / den


def to_dev(data, dev):
    X, y, t, n_t = data
    return (torch.as_tensor(X, device=dev), torch.as_tensor(y, device=dev),
            torch.as_tensor(weights(y, t, n_t), device=dev))


def eval_net(net, data, dev) -> float:
    X, y, t, n_t = data
    with torch.no_grad():
        p = torch.cat([net(torch.as_tensor(X[s:s + 262144], device=dev)) for s in range(0, len(X), 262144)]).cpu().numpy()
    return float(nmae_per_target(p, y, t, n_t).mean()), p


def train(groups_data: dict, inner: dict | None, dev, seed: int, max_steps: int = 4000, every: int = 250,
          patience: int = 6, fixed_steps: int | None = None):
    torch.manual_seed(seed)
    net = Net().to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4)
    tens = {g: to_dev(d, dev) for g, d in groups_data.items()}
    gk = sorted(tens)
    rng = np.random.default_rng(seed)
    best, best_step, best_state, bad = np.inf, 0, None, 0
    steps = fixed_steps or max_steps
    for step in range(1, steps + 1):
        loss = 0.0
        for g in gk:  # every group weighs the same in each step
            X, y, w = tens[g]
            idx = torch.as_tensor(rng.integers(0, len(y), 16384), device=dev)
            loss = loss + (w[idx] * (net(X[idx]) - y[idx]).abs()).sum() / w[idx].sum()
        opt.zero_grad()
        (loss / len(gk)).backward()
        opt.step()
        if inner is not None and step % every == 0:
            v, _ = eval_net(net, inner, dev)
            if v < best - 1e-5:
                best, best_step, bad = v, step, 0
                best_state = {k: x.detach().clone() for k, x in net.state_dict().items()}
            else:
                bad += 1
                if bad >= patience:
                    break
    if best_state is not None:
        net.load_state_dict(best_state)
    return net, best_step if inner is not None else steps, best


def boot(a: np.ndarray, b: np.ndarray, n: int = 10000, seed: int = 0) -> dict:
    d = a - b
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), (n, len(d)))].mean(1)
    return {"mean": float(d.mean()), "lo": float(np.quantile(m, 0.025)), "hi": float(np.quantile(m, 0.975)),
            "n_targets": int(len(d))}


def axis_genes(controls: Path) -> np.ndarray:
    import pandas as pd
    return pd.read_csv(controls / "gene_names.csv").iloc[:, 0].astype(str).to_numpy()


def build(a):
    rng = np.random.default_rng(0)
    gpos = {g: i for i, g in enumerate(axis_genes(a.controls))}
    src = Source(a.keys / "replogle_k562_gwps__K562.npz")
    log(f"source: {len(src.targets)} targets, {int(src.meas.sum())} measured genes")
    by_group: dict[str, list] = {}
    for ln in load_lines(a.keys, a.extra):
        r = line_rows(src, ln, rng, gpos)
        if r is None:
            continue
        by_group.setdefault(ln["group"], []).append(r)
        log(f"{ln['key'][:40]:40s} group {ln['group']:7s} targets {r[3]:5d} rows {len(r[1]):9d}")
    data = {}
    for g, parts in by_group.items():
        X = np.concatenate([p[0] for p in parts]); y = np.concatenate([p[1] for p in parts])
        offs = np.cumsum([0] + [p[3] for p in parts])
        t = np.concatenate([p[2] + offs[i] for i, p in enumerate(parts)])
        data[g] = (X, y, t, int(offs[-1]))
    return src, data


def bench(a) -> None:
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src, data = build(a)
    order = [g for g in ORDER if g in data]
    res = {"groups": {g: {"targets": data[g][3], "rows": int(len(data[g][1]))} for g in order}, "folds": {}}
    per_arm = {k: [] for k in ("zero", "copia1", "copia2", "rete")}
    for g in order:
        inner_g = order[(order.index(g) + 1) % len(order)]
        tr = {h: data[h] for h in order if h not in (g, inner_g)}
        net, step, vbest = train(tr, data[inner_g], dev, seed=0)
        X, y, t, n_t = data[g]
        _, p = eval_net(net, data[g], dev)
        arms = {"zero": np.zeros_like(y), "copia1": X[:, 0], "copia2": 2 * X[:, 0], "rete": p}
        pt = {k: nmae_per_target(v, y, t, n_t) for k, v in arms.items()}
        cov = np.bincount(t, weights=X[:, 8], minlength=n_t) > 0
        sign = {k: float(np.mean(np.sign(v[v != 0]) == np.sign(y[v != 0]))) if (v != 0).any() else None
                for k, v in arms.items()}
        res["folds"][g] = {
            "inner": inner_g, "best_step": step, "inner_nmae": vbest,
            "nmae": {k: float(v.mean()) for k, v in pt.items()},
            "nmae_covered": {k: float(v[cov].mean()) for k, v in pt.items()},
            "rete-zero": boot(pt["rete"], pt["zero"]), "rete-copia2": boot(pt["rete"], pt["copia2"]),
            "sign_agreement_nonzero": sign,
            "pred_abs_median": float(np.median(np.abs(p))), "y_abs_median": float(np.median(np.abs(y)))}
        for k in per_arm:
            per_arm[k].append(pt[k])
        log(f"{g}: step {step} " + json.dumps({k: round(v, 4) for k, v in res['folds'][g]['nmae'].items()}))
    macro = {k: float(np.mean([v.mean() for v in vs])) for k, vs in per_arm.items()}
    rng = np.random.default_rng(1)
    draws = np.mean([v[rng.integers(0, len(v), (10000, len(v)))].mean(1) for v in per_arm["rete"]], 0)
    macro["rete_ci"] = [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))]
    wins = sum(res["folds"][g]["nmae"]["rete"] < res["folds"][g]["nmae"]["copia2"] for g in order)
    macro["folds_rete_beats_copia2"] = int(wins)
    macro["passes"] = bool(macro["rete"] <= 0.99 and macro["rete_ci"][1] < 1.0 and wins >= 5)
    macro["median_best_step"] = int(np.median([res["folds"][g]["best_step"] for g in order]))
    res["macro"] = macro
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "result.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    log("macro " + json.dumps(macro))


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ctx_cpm_and_ref(h5ad: Path, n_genes: int):
    """Per-gene mean of per-cell CPM over the controls (the scorer's reference mean) and the pooled basal CPM."""
    import h5py
    with h5py.File(h5ad, "r") as f:
        indptr = f["X/indptr"][:].astype(np.int64)
        n_cells = len(indptr) - 1
        ref = np.zeros(n_genes, np.float64)
        pooled = np.zeros(n_genes, np.float64)
        for s in range(0, n_cells, 4000):
            e = min(n_cells, s + 4000)
            lo, hi = indptr[s], indptr[e]
            data = f["X/data"][lo:hi].astype(np.float64)
            idx = f["X/indices"][lo:hi]
            rows = np.repeat(np.arange(e - s), np.diff(indptr[s:e + 1]))
            L = np.bincount(rows, weights=data, minlength=e - s)
            ref += np.bincount(idx, weights=data * (1e6 / L[rows]), minlength=n_genes)
            pooled += np.bincount(idx, weights=data, minlength=n_genes)
    return ref / n_cells, pooled / pooled.sum() * 1e6


def export(a) -> None:
    import pandas as pd
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src, data = build(a)
    net, steps, _ = train(data, None, dev, seed=0, fixed_steps=a.steps)
    a.out.mkdir(parents=True, exist_ok=True)
    torch.save(net.state_dict(), a.out / "rete_l1_final.pt")
    if a.targets_out.exists():
        raise SystemExit(f"{a.targets_out} exists: never overwrite")
    a.targets_out.mkdir(parents=True)
    genes = axis_genes(a.controls)
    panel = pd.read_csv(a.controls / "pert_counts.csv")["target_gene"].astype(str).drop_duplicates().tolist()
    gpos = {g: i for i, g in enumerate(genes)}
    meta = {"model_sha256": sha256(a.out / "rete_l1_final.pt"), "steps": steps, "contexts": {}}
    for ctx in "ABC":
        ref, pooled = ctx_cpm_and_ref(a.controls / f"context_{ctx}.h5ad", len(genes))
        gidx = np.where(ref >= MIN_CPM)[0]
        m = np.zeros((len(panel), len(gidx)), np.float32)
        with torch.no_grad():
            for i, t in enumerate(panel):
                f = features(src, t, pooled, gidx)
                m[i] = net(torch.as_tensor(f, device=dev)).cpu().numpy()
        own = np.array([gpos.get(t, -1) for t in panel])
        path = a.targets_out / f"obiettivi_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(panel, dtype=str), gene_idx=gidx.astype(np.int32), m=m,
                            ref_mean_cpm=ref.astype(np.float64), own_idx=own.astype(np.int32))
        cov = np.array([t in src.row for t in panel])
        meta["contexts"][ctx] = {"file": path.name, "sha256": sha256(path), "genes": int(len(gidx)),
                                 "covered_targets": int(cov.sum()),
                                 "m_abs_median": float(np.median(np.abs(m))),
                                 "m_abs_q90": float(np.quantile(np.abs(m), 0.9)),
                                 "m_pos_share": float((m > 0).mean())}
        log(f"{ctx}: {len(gidx)} genes; |m| median {meta['contexts'][ctx]['m_abs_median']:.3f}")
    (a.targets_out / "export.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["bench", "export"])
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--extra", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--controls", type=Path, required=True)
    ap.add_argument("--targets-out", type=Path, default=None)
    a = ap.parse_args()
    bench(a) if a.mode == "bench" else export(a)


if __name__ == "__main__":
    main()
