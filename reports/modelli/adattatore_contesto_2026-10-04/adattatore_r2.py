"""Context adapter r2 (PROTOCOLLO_R2.md): K562 copy on the genes K562 measures (M), a learned model on the rest (U).

Arms: k562, hyb_adapter, hyb_adapterU (adapter trained with the loss on U only), hyb_ridge. beta per arm on the
validation pairs from {0, 0.25, 0.5, 1, 2, 4}. Target split with seed 1 (r1 used seed 0).
Usage: python adattatore_r2.py --keys <chiavi dir> --fold R|T|H --out <dir> [--split-seed 1] [--seed 0]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adattatore as r1  # noqa: E402

BETAS = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)


def train_masked(src, tr, va, m_idx, n_genes, dev, seed, gene_mask, max_steps=3000, patience=10, log_every=100):
    """r1.train_adapter with the loss and the early-stopping cosine restricted to `gene_mask`."""
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = r1.Adapter(m_idx, n_genes, src.basal).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    gm = torch.as_tensor(gene_mask, device=dev)
    by_line: dict[str, list] = {}
    for p in tr:
        by_line.setdefault(p[0].key, []).append(p)
    keys = list(by_line)
    w = np.array([len(by_line[k]) for k in keys], float)
    w /= w.sum()
    best, best_state, bad, hist = -1e9, None, 0, []
    for step in range(max_steps + 1):
        if step % log_every == 0:
            vc = float(np.mean(r1.score(r1.predict_adapter(model, src, va, m_idx, dev), va, gene_mask)))
            hist.append({"step": step, "val_cos": vc})
            if vc > best + 1e-5:
                best, bad = vc, 0
                best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            else:
                bad += 1
                if bad >= patience:
                    break
            model.train()
        cand = by_line[keys[rng.choice(len(keys), p=w)]]
        prs = [cand[i] for i in rng.choice(len(cand), size=min(64, len(cand)), replace=False)]
        x, y = r1.batch(src, prs, m_idx, dev)
        yh = model(x, torch.as_tensor(prs[0][0].basal, device=dev))
        y = torch.where(gm[None, :], y, torch.full_like(y, float("nan")))
        ok = ~torch.isnan(y)
        y0, yh0 = torch.where(ok, y, torch.zeros_like(y)), torch.where(ok, yh, torch.zeros_like(yh))
        rel = ((yh0 - y0) ** 2).sum(1) / ((y0 ** 2).sum(1) + 1e-8)
        loss = (1 - r1.cos_masked(yh, y)).mean() + 0.1 * rel.mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    model.load_state_dict(best_state)
    return model, hist, best


def hybrid(copy: np.ndarray, model_out: np.ndarray, U: np.ndarray, beta: float) -> np.ndarray:
    out = copy.copy()
    out[:, U] = beta * model_out[:, U]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--fold", choices=["R", "T", "H"], required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--split-seed", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    out = a.out / f"r2_fold_{a.fold}_split{a.split_seed}_seed{a.seed}"
    out.mkdir(parents=True, exist_ok=False)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src, lines = r1.load(a.keys)
    n_genes = src.d.shape[1]
    m_idx = np.where(~np.isnan(src.d).all(0))[0]
    U = np.ones(n_genes, bool)
    U[m_idx] = False
    split = r1.split_targets(src, lines, seed=a.split_seed)
    train_lines, test_lines = r1.fold_lines(lines, a.fold)
    tr, va = r1.pairs(src, train_lines, split["train"]), r1.pairs(src, train_lines, split["val"])
    te = r1.pairs(src, test_lines, split["test"])
    r1.log(f"r2 fold {a.fold} split {a.split_seed}: pairs train {len(tr)} val {len(va)} test {len(te)}; "
           f"test targets {len({t for _, t in te})}")
    copy_va, copy_te = r1.k562_predict(src, va, m_idx, n_genes), r1.k562_predict(src, te, m_idx, n_genes)
    models_va, models_te, res = {}, {}, {"fold": a.fold, "split_seed": a.split_seed, "seed": a.seed,
                                         "test_lines": [l.key for l in test_lines],
                                         "test_targets": len({t for _, t in te}), "n_pairs": [len(tr), len(va), len(te)]}

    lams = [10.0 ** e for e in np.linspace(-3, 3, 13)]
    rg = r1.Ridge(src, tr, m_idx)
    rv = {lam: float(np.mean(r1.score(rg.predict(va, lam), va, U))) for lam in lams}
    lam = max(rv, key=rv.get)
    models_va["hyb_ridge"], models_te["hyb_ridge"] = rg.predict(va, lam), rg.predict(te, lam)
    res["ridge_lambda"] = lam
    del rg

    m_all, h_all, _ = r1.train_adapter(src, tr, va, m_idx, n_genes, dev, a.seed)
    models_va["hyb_adapter"] = r1.predict_adapter(m_all, src, va, m_idx, dev)
    models_te["hyb_adapter"] = r1.predict_adapter(m_all, src, te, m_idx, dev)
    m_u, h_u, _ = train_masked(src, tr, va, m_idx, n_genes, dev, a.seed, U)
    models_va["hyb_adapterU"] = r1.predict_adapter(m_u, src, va, m_idx, dev)
    models_te["hyb_adapterU"] = r1.predict_adapter(m_u, src, te, m_idx, dev)
    torch.save(m_all.state_dict(), out / "adapter.pt")
    torch.save(m_u.state_dict(), out / "adapterU.pt")
    res["adapter_steps"], res["adapterU_steps"] = h_all[-1]["step"], h_u[-1]["step"]

    preds_te = {"k562": copy_te}
    res["beta"], res["beta_val_grid"] = {}, {}
    for arm in ("hyb_ridge", "hyb_adapter", "hyb_adapterU"):
        grid = {b: float(np.mean(r1.score(hybrid(copy_va, models_va[arm], U, b), va))) for b in BETAS}
        b = max(grid, key=grid.get)
        res["beta"][arm], res["beta_val_grid"][arm] = b, {str(k): v for k, v in grid.items()}
        preds_te[arm] = hybrid(copy_te, models_te[arm], U, b)
    res["val_cos_k562"] = float(np.mean(r1.score(copy_va, va)))
    res["test_cos"] = {k: float(np.mean(r1.score(v, te))) for k, v in preds_te.items()}
    res["test_cos_U_model"] = {k: float(np.mean(r1.score(models_te[k], te, U))) for k in models_te}
    pt = {k: r1.per_target(r1.score(v, te), te) for k, v in preds_te.items()}
    res["diff"] = {f"{k}-k562": r1.boot(pt[k], pt["k562"]) for k in preds_te if k != "k562"}
    res["nan_in_predictions"] = {k: bool(np.isnan(v).any()) for k, v in preds_te.items()}
    (out / "result.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    r1.log(json.dumps({"beta": res["beta"], "test_cos": res["test_cos"], "diff": res["diff"]}, indent=1))


if __name__ == "__main__":
    main()
