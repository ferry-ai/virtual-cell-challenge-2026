"""Context adapter: a learned map from a K562 knockdown effect to the effect in an unseen line (PROTOCOLLO.md).

Arms: `k562` (copy, the t31 shape), `ridge` (dual ridge, line-agnostic), `adapter` (gene-feature-modulated identity
plus rank-64 map, conditioned on the line's basal), `adapter_swap` (adapter with the test line's basal replaced by
the mean training basal). All effects live in the bulk-lognorm space at 50,000: d = log1p(5e4 p e^lfc) - log1p(5e4 p).

Usage: python adattatore.py --keys <chiavi dir> --fold R|T|H --out <dir> [--seed 0]
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

SOURCE = "replogle_k562_gwps|K562"
EXCLUDED = {"replogle_k562_essential|K562"}
SPLIT = (0.60, 0.15, 0.25)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def to_d(lfc: np.ndarray, basal: np.ndarray) -> np.ndarray:
    """ln fold change -> bulk-lognorm difference at 50,000, with p from the line's basal; NaN stays NaN."""
    p = np.expm1(basal.astype(np.float64)) / 1e4
    base = np.log1p(5e4 * p)
    out = np.empty(lfc.shape, np.float32)
    for s in range(0, lfc.shape[0], 512):
        part = np.clip(lfc[s:s + 512].astype(np.float64), -10, 10)
        out[s:s + 512] = np.log1p(5e4 * p * np.exp(part)) - base
    return out


@dataclass
class Line:
    key: str
    targets: list
    d: np.ndarray        # T x G float32, NaN = not usable
    basal: np.ndarray    # G float32

    def __post_init__(self):
        self.row = {t: i for i, t in enumerate(self.targets)}


def load(keys_dir: Path):
    lines, src = [], None
    for f in sorted(keys_dir.glob("*.npz")):
        z = np.load(f, allow_pickle=False)
        key = str(z["key"])
        if key in EXCLUDED:
            continue
        eff = z["eff"].astype(np.float32)
        eff[:, ~np.asarray(z["measured"])] = np.nan
        ln = Line(key, list(map(str, z["targets"])), to_d(eff, z["basal"]), z["basal"].astype(np.float32))
        if key == SOURCE:
            src = ln
        else:
            lines.append(ln)
    return src, lines


def split_targets(src: Line, lines: list[Line], seed: int = 0) -> dict:
    pool = sorted({t for ln in lines for t in ln.targets if t in src.row})
    rng = np.random.default_rng(seed)
    perm = [pool[i] for i in rng.permutation(len(pool))]
    a, b = int(SPLIT[0] * len(perm)), int((SPLIT[0] + SPLIT[1]) * len(perm))
    return {"train": set(perm[:a]), "val": set(perm[a:b]), "test": set(perm[b:])}


def fold_lines(lines: list[Line], fold: str):
    keys = [ln.key for ln in lines]
    if fold == "R":
        test = {k for k in keys if k.startswith("replogle_rpe1")}
        drop = set()
    elif fold == "T":
        test = {k for k in keys if k.startswith("tian2021_crispri")}
        drop = {k for k in keys if k.startswith("tian2019_neuron")}
    elif fold == "H":
        donors = sorted({k.split("|")[1].split("_")[0] for k in keys if k.startswith("hipsci")})[:2]
        test = {k for k in keys if k.startswith("hipsci") and k.split("|")[1].split("_")[0] in donors}
        drop = set()
    else:
        raise ValueError(fold)
    train = [ln for ln in lines if ln.key not in test and ln.key not in drop]
    return train, [ln for ln in lines if ln.key in test]


def pairs(src: Line, lines: list[Line], targets: set) -> list[tuple[Line, str]]:
    return [(ln, t) for ln in lines for t in ln.targets if t in targets and t in src.row]


class Adapter(nn.Module):
    def __init__(self, m_idx: np.ndarray, n_genes: int, basal_k: np.ndarray, rank: int = 64, emb: int = 16):
        super().__init__()
        self.register_buffer("m_idx", torch.as_tensor(m_idx, dtype=torch.long))
        self.register_buffer("basal_k", torch.as_tensor(basal_k, dtype=torch.float32))
        meas = np.zeros(n_genes, np.float32)
        meas[m_idx] = 1
        self.register_buffer("meas_k", torch.as_tensor(meas))
        self.n_genes = n_genes
        self.emb = nn.Parameter(0.01 * torch.randn(n_genes, emb))
        self.V = nn.Parameter(0.01 * torch.randn(len(m_idx), rank))
        self.U = nn.Parameter(0.01 * torch.randn(n_genes, rank))
        self.mlp = nn.Sequential(nn.Linear(emb + 3, 32), nn.GELU(), nn.Linear(32, 2))
        with torch.no_grad():  # start at the copy: identity gain 1, low-rank gain ~0
            self.mlp[2].weight.zero_()
            self.mlp[2].bias.copy_(torch.tensor([1.0, 0.0]))

    def gains(self, basal_l: torch.Tensor) -> torch.Tensor:
        f = torch.cat([self.emb, basal_l[:, None], self.basal_k[:, None], self.meas_k[:, None]], 1)
        return self.mlp(f)  # G x 2

    def forward(self, x: torch.Tensor, basal_l: torch.Tensor) -> torch.Tensor:
        g = self.gains(basal_l)
        ident = torch.zeros(x.shape[0], self.n_genes, device=x.device)
        ident[:, self.m_idx] = x
        low = (x @ self.V) @ self.U.T
        return g[:, 0] * ident + g[:, 1] * low


def cos_masked(y: torch.Tensor, d: torch.Tensor) -> torch.Tensor:
    ok = ~torch.isnan(d)
    d0, y0 = torch.where(ok, d, torch.zeros_like(d)), torch.where(ok, y, torch.zeros_like(y))
    return (y0 * d0).sum(1) / (y0.norm(dim=1) * d0.norm(dim=1) + 1e-8)


def batch(src: Line, prs, m_idx, dev):
    x = np.stack([src.d[src.row[t]][m_idx] for _, t in prs])
    y = np.stack([ln.d[ln.row[t]] for ln, t in prs])
    return torch.as_tensor(x, device=dev), torch.as_tensor(y, device=dev)


def predict_adapter(model, src, prs, m_idx, dev, basal_override=None):
    out = []
    model.eval()
    with torch.no_grad():
        by_line: dict[str, list] = {}
        for i, (ln, t) in enumerate(prs):
            by_line.setdefault(ln.key, []).append(i)
        res = [None] * len(prs)
        for key, idx in by_line.items():
            ln = prs[idx[0]][0]
            b = torch.as_tensor(basal_override if basal_override is not None else ln.basal, device=dev)
            for s in range(0, len(idx), 256):
                part = idx[s:s + 256]
                x, _ = batch(src, [prs[i] for i in part], m_idx, dev)
                y = model(x, b).cpu().numpy()
                for j, i in enumerate(part):
                    res[i] = y[j]
        out = np.stack(res)
    return out


def train_adapter(src, tr, va, m_idx, n_genes, dev, seed, max_steps=3000, patience=10, log_every=100):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = Adapter(m_idx, n_genes, src.basal).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    by_line: dict[str, list] = {}
    for p in tr:
        by_line.setdefault(p[0].key, []).append(p)
    line_keys = list(by_line)
    weights = np.array([len(by_line[k]) for k in line_keys], float)
    weights /= weights.sum()
    best, best_state, bad, history = -1e9, None, 0, []
    for step in range(max_steps + 1):
        if step % log_every == 0:
            vc = float(np.mean(score(predict_adapter(model, src, va, m_idx, dev), va)))
            history.append({"step": step, "val_cos": vc})
            if vc > best + 1e-5:
                best, bad = vc, 0
                best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            else:
                bad += 1
                if bad >= patience:
                    break
            model.train()
        k = line_keys[rng.choice(len(line_keys), p=weights)]
        cand = by_line[k]
        prs = [cand[i] for i in rng.choice(len(cand), size=min(64, len(cand)), replace=False)]
        x, y = batch(src, prs, m_idx, dev)
        yh = model(x, torch.as_tensor(prs[0][0].basal, device=dev))
        ok = ~torch.isnan(y)
        y0 = torch.where(ok, y, torch.zeros_like(y))
        yh0 = torch.where(ok, yh, torch.zeros_like(yh))
        rel = ((yh0 - y0) ** 2).sum(1) / ((y0 ** 2).sum(1) + 1e-8)
        loss = (1 - cos_masked(yh, y)).mean() + 0.1 * rel.mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    model.load_state_dict(best_state)
    return model, history, best


class Ridge:
    """Dual ridge, one eigendecomposition for every lambda; Y's NaN count as 0 (documented in ESITO)."""

    def __init__(self, src, tr, m_idx):
        self.src, self.m_idx = src, m_idx
        self.X = np.stack([src.d[src.row[t]][m_idx] for _, t in tr]).astype(np.float64)
        Y = np.nan_to_num(np.stack([ln.d[ln.row[t]] for ln, t in tr])).astype(np.float64)
        K = self.X @ self.X.T
        self.scale = np.trace(K) / len(K)
        self.w, self.Q = np.linalg.eigh(K)
        self.QtY = self.Q.T @ Y

    def predict(self, prs, lam):
        Xq = np.stack([self.src.d[self.src.row[t]][self.m_idx] for _, t in prs]).astype(np.float64)
        KQ = (Xq @ self.X.T) @ self.Q
        return ((KQ / (self.w + lam * self.scale)[None, :]) @ self.QtY).astype(np.float32)


def k562_predict(src, prs, m_idx, n_genes):
    out = np.zeros((len(prs), n_genes), np.float32)
    for i, (_, t) in enumerate(prs):
        out[i, m_idx] = src.d[src.row[t]][m_idx]
    return out


def score(pred: np.ndarray, prs, genes: np.ndarray | None = None) -> np.ndarray:
    y = np.stack([ln.d[ln.row[t]] for ln, t in prs]).astype(np.float64)
    p = pred.astype(np.float64)
    ok = ~np.isnan(y)
    if genes is not None:
        ok &= genes[None, :]
    y, p = np.where(ok, y, 0), np.where(ok, p, 0)
    den = np.linalg.norm(p, axis=1) * np.linalg.norm(y, axis=1)
    return np.where(den > 0, (p * y).sum(1) / np.where(den > 0, den, 1), 0.0)


def per_target(vals: np.ndarray, prs) -> dict:
    acc: dict[str, list] = {}
    for v, (_, t) in zip(vals, prs):
        acc.setdefault(t, []).append(v)
    return {t: float(np.mean(v)) for t, v in acc.items()}


def boot(a: dict, b: dict, n: int = 10000, seed: int = 0) -> dict:
    ts = sorted(set(a) & set(b))
    d = np.array([a[t] - b[t] for t in ts])
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), (n, len(d)))].mean(1)
    return {"mean": float(d.mean()), "lo": float(np.quantile(m, 0.025)), "hi": float(np.quantile(m, 0.975)),
            "n_targets": len(ts)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--fold", choices=["R", "T", "H"], required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    out = a.out / f"fold_{a.fold}_seed{a.seed}"
    out.mkdir(parents=True, exist_ok=False)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src, lines = load(a.keys)
    n_genes = src.d.shape[1]
    m_idx = np.where(~np.isnan(src.d).all(0))[0]
    split = split_targets(src, lines, seed=0)
    train_lines, test_lines = fold_lines(lines, a.fold)
    tr, va = pairs(src, train_lines, split["train"]), pairs(src, train_lines, split["val"])
    te = pairs(src, test_lines, split["test"])
    log(f"fold {a.fold}: train lines {len(train_lines)}, test lines {[l.key for l in test_lines]}; "
        f"pairs train {len(tr)} val {len(va)} test {len(te)}; test targets {len({t for _, t in te})}; M {len(m_idx)}")
    U = np.ones(n_genes, bool)
    U[m_idx] = False
    M = ~U

    res = {"fold": a.fold, "seed": a.seed, "device": dev, "n_pairs": {"train": len(tr), "val": len(va), "test": len(te)},
           "test_lines": [l.key for l in test_lines], "train_lines": [l.key for l in train_lines],
           "test_targets": len({t for _, t in te}), "genes_M": int(M.sum())}
    preds_te, preds_va = {}, {}
    preds_te["k562"], preds_va["k562"] = k562_predict(src, te, m_idx, n_genes), k562_predict(src, va, m_idx, n_genes)

    lams = [10.0 ** e for e in np.linspace(-3, 3, 13)]
    rg = Ridge(src, tr, m_idx)
    ridge_val = {lam: float(np.mean(score(rg.predict(va, lam), va))) for lam in lams}
    lam_best = max(ridge_val, key=ridge_val.get)
    preds_te["ridge"], preds_va["ridge"] = rg.predict(te, lam_best), rg.predict(va, lam_best)
    del rg
    res["ridge_lambda"], res["ridge_val_grid"] = lam_best, {str(k): v for k, v in ridge_val.items()}
    log(f"ridge lambda {lam_best:g}, val cos {ridge_val[lam_best]:.4f}")

    model, hist, best = train_adapter(src, tr, va, m_idx, n_genes, dev, a.seed)
    res["adapter_history"], res["adapter_best_val"] = hist, best
    preds_te["adapter"] = predict_adapter(model, src, te, m_idx, dev)
    preds_va["adapter"] = predict_adapter(model, src, va, m_idx, dev)
    mean_basal = np.mean([ln.basal for ln in train_lines], 0).astype(np.float32)
    preds_te["adapter_swap"] = predict_adapter(model, src, te, m_idx, dev, basal_override=mean_basal)
    torch.save(model.state_dict(), out / "adapter.pt")
    log(f"adapter: {len(hist)} evaluations, best val cos {best:.4f}")

    res["val_cos"] = {k: float(np.mean(score(v, va))) for k, v in preds_va.items()}
    res["test_cos"] = {k: float(np.mean(score(v, te))) for k, v in preds_te.items()}
    res["test_cos_U"] = {k: float(np.mean(score(v, te, U))) for k, v in preds_te.items()}
    res["test_cos_M"] = {k: float(np.mean(score(v, te, M))) for k, v in preds_te.items()}
    pt = {k: per_target(score(v, te), te) for k, v in preds_te.items()}
    res["diff"] = {f"{x}-k562": boot(pt[x], pt["k562"]) for x in ("ridge", "adapter", "adapter_swap")}
    res["diff"]["adapter-ridge"] = boot(pt["adapter"], pt["ridge"])
    res["diff"]["adapter-adapter_swap"] = boot(pt["adapter"], pt["adapter_swap"])
    res["nan_in_predictions"] = {k: bool(np.isnan(v).any()) for k, v in preds_te.items()}
    (out / "result.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    log(json.dumps({"val_cos": res["val_cos"], "test_cos": res["test_cos"], "diff": res["diff"]}, indent=1))


if __name__ == "__main__":
    main()
