"""Phase 2 of PROTOCOLLO.md: fit the chosen model on every line and on train+val targets, export effects for A, B, C.

Only run when a learned arm passed the registered rule. The direction comes from the model; the amplitude, per target,
is the t31 one: the L2 norm of the t31 lfc row of that target (A0 x K562 lfc, read from the t31 effects file), so that
against t31 only the direction changes. Targets K562 does not cover stay at lfc 0, observed False, as in t31.

Writes effects_<CTX>.npz in the stage-45 layout (targets, genes as str, lfc in ln, observed) and export_t32.json.
Usage: python esporta_t32.py --keys <chiavi> --controls <raw/controls> --t31 <effects_t31 dir> --arm adapter|ridge
       --steps N --lam L --out <data root>/processed/effects_t32_<date>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adattatore as ad_  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def context_basal(h5ad: Path, axis: np.ndarray) -> np.ndarray:
    import anndata as ad
    import scipy.sparse as sp

    a = ad.read_h5ad(h5ad)
    pos = pd.Index(a.var_names.astype(str)).get_indexer(axis)
    if (pos < 0).any():
        raise SystemExit(f"{h5ad}: {(pos < 0).sum()} axis genes missing")
    col = np.asarray(a.X.sum(axis=0)).ravel() if sp.issparse(a.X) else a.X.sum(axis=0)
    counts = np.asarray(col, np.float64)[pos]
    return np.log1p(1e4 * counts / counts.sum()).astype(np.float32)


def d_to_lfc(d: np.ndarray, basal: np.ndarray) -> np.ndarray:
    """Inverse of adattatore.to_d for one context; genes with p = 0 get lfc 0."""
    p = np.expm1(basal.astype(np.float64)) / 1e4
    base = 5e4 * p
    with np.errstate(all="ignore"):
        lfc = np.log(np.expm1(d.astype(np.float64) + np.log1p(base)) / base)
    lfc = np.where(base > 0, lfc, 0.0)
    return np.clip(np.nan_to_num(lfc, nan=0.0, posinf=10.0, neginf=-10.0), -10, 10).astype(np.float32)


def train_fixed(src, prs, m_idx, n_genes, dev, steps, seed=0):
    """adattatore.train_adapter's loop for a fixed number of steps, no validation."""
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = ad_.Adapter(m_idx, n_genes, src.basal).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    by_line: dict[str, list] = {}
    for p in prs:
        by_line.setdefault(p[0].key, []).append(p)
    keys = list(by_line)
    w = np.array([len(by_line[k]) for k in keys], float)
    w /= w.sum()
    model.train()
    for _ in range(steps):
        cand = by_line[keys[rng.choice(len(keys), p=w)]]
        part = [cand[i] for i in rng.choice(len(cand), size=min(64, len(cand)), replace=False)]
        x, y = ad_.batch(src, part, m_idx, dev)
        yh = model(x, torch.as_tensor(part[0][0].basal, device=dev))
        ok = ~torch.isnan(y)
        y0, yh0 = torch.where(ok, y, torch.zeros_like(y)), torch.where(ok, yh, torch.zeros_like(yh))
        rel = ((yh0 - y0) ** 2).sum(1) / ((y0 ** 2).sum(1) + 1e-8)
        loss = (1 - ad_.cos_masked(yh, y)).mean() + 0.1 * rel.mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    model.eval()
    return model


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--controls", type=Path, required=True)
    ap.add_argument("--t31", type=Path, required=True)
    ap.add_argument("--arm", choices=["adapter", "ridge"], required=True)
    ap.add_argument("--steps", type=int, default=0)
    ap.add_argument("--lam", type=float, default=1.0)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: never overwrite")
    a.out.mkdir(parents=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src, lines = ad_.load(a.keys)
    n_genes = src.d.shape[1]
    m_idx = np.where(~np.isnan(src.d).all(0))[0]
    split = ad_.split_targets(src, lines, seed=0)
    prs = ad_.pairs(src, lines, split["train"] | split["val"])
    ad_.log(f"fit {a.arm} on {len(lines)} lines, {len(prs)} pairs")
    if a.arm == "adapter":
        model = train_fixed(src, prs, m_idx, n_genes, dev, a.steps)
        torch.save(model.state_dict(), a.out / "adapter_final.pt")
    else:
        rg = ad_.Ridge(src, prs, m_idx)
    meta = {"arm": a.arm, "steps": a.steps, "lam": a.lam, "pairs": len(prs), "lines": [l.key for l in lines],
            "contexts": {}}
    for ctx in "ABC":
        t31 = np.load(a.t31 / f"effects_{ctx}.npz", allow_pickle=False)
        targets, genes = list(map(str, t31["targets"])), np.asarray(t31["genes"], str)
        basal = context_basal(a.controls / f"context_{ctx}.h5ad", genes)
        covered = [i for i, t in enumerate(targets) if t in src.row]
        x = torch.as_tensor(np.stack([src.d[src.row[targets[i]]][m_idx] for i in covered]), device=dev)
        if a.arm == "adapter":
            with torch.no_grad():
                d = np.concatenate([model(x[s:s + 128], torch.as_tensor(basal, device=dev)).cpu().numpy()
                                    for s in range(0, len(covered), 128)])
        else:
            fake = [(None, targets[i]) for i in covered]
            d = rg.predict(fake, a.lam)
        lfc = np.zeros((len(targets), n_genes), np.float32)
        observed = np.zeros((len(targets), n_genes), bool)
        raw = np.stack([d_to_lfc(row, basal) for row in d])
        ref = np.linalg.norm(t31["lfc"][covered].astype(np.float64), axis=1)
        cur = np.linalg.norm(raw.astype(np.float64), axis=1)
        lfc[covered] = raw * (ref / np.where(cur > 0, cur, 1))[:, None]
        observed[covered] = True
        path = a.out / f"effects_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(targets, dtype=str), genes=genes, lfc=lfc, observed=observed)
        cos31 = [float(np.dot(lfc[i], t31["lfc"][i]) / (np.linalg.norm(lfc[i]) * np.linalg.norm(t31["lfc"][i]) + 1e-12))
                 for i in covered]
        meta["contexts"][ctx] = {"file": path.name, "sha256": sha256(path), "covered": len(covered),
                                 "controls_sha256": sha256(a.controls / f"context_{ctx}.h5ad"),
                                 "median_cos_with_t31": float(np.median(cos31)),
                                 "lfc_abs_mean_covered": float(np.abs(lfc[covered]).mean())}
        ad_.log(f"{ctx}: {len(covered)} covered; median cos with t31 {np.median(cos31):.3f}")
    (a.out / "export_t32.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
