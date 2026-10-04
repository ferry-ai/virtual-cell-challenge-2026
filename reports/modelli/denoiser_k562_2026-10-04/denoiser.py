"""K562 effect denoiser (PROTOCOLLO.md): mean + top-k principal directions of the 9,510 K562 gwps effects.

Arms k562, pca (k on validation), mean_only; folds R, T, H of the context adapter, target split seed 2.
Usage: python denoiser.py --keys <chiavi dir> --fold R|T|H --out <dir> [--split-seed 2]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adattatore_contesto_2026-10-04"))
import adattatore as r1  # noqa: E402

KS = (8, 16, 32, 64, 128, 256, 512, 1024)


class Denoiser:
    def __init__(self, src, m_idx, dev):
        X = torch.as_tensor(np.nan_to_num(src.d[:, m_idx]), device=dev)
        self.mu = X.mean(0)
        _, _, Vh = torch.linalg.svd(X - self.mu, full_matrices=False)
        self.V = Vh[: max(KS)].T.contiguous()  # genes x maxK
        self.src, self.m_idx, self.dev = src, m_idx, dev

    def predict(self, prs, k, n_genes, mean_only=False):
        x = torch.as_tensor(np.stack([self.src.d[self.src.row[t]][self.m_idx] for _, t in prs]), device=self.dev)
        if mean_only:
            y = self.mu.expand_as(x)
        else:
            V = self.V[:, :k]
            y = self.mu + ((x - self.mu) @ V) @ V.T
        out = np.zeros((len(prs), n_genes), np.float32)
        out[:, self.m_idx] = y.cpu().numpy()
        return out


def discrimination(pred: np.ndarray, prs) -> float:
    """Mean over targets of the share of other targets s with cos(pred_t, true_t) > cos(pred_t, true_s), per line."""
    by_line: dict[str, list] = {}
    for i, (ln, _) in enumerate(prs):
        by_line.setdefault(ln.key, []).append(i)
    vals = []
    for key, idx in by_line.items():
        ln = prs[idx[0]][0]
        meas = ~np.isnan(ln.d).all(0)
        Y = np.nan_to_num(np.stack([ln.d[ln.row[prs[i][1]]] for i in idx])[:, meas]).astype(np.float64)
        P = pred[idx][:, meas].astype(np.float64)
        Yn = Y / np.maximum(np.linalg.norm(Y, axis=1, keepdims=True), 1e-12)
        Pn = P / np.maximum(np.linalg.norm(P, axis=1, keepdims=True), 1e-12)
        C = Pn @ Yn.T
        own = np.diag(C)
        n = len(idx)
        if n < 2:
            continue
        vals += list(((own[:, None] > C).sum(1)) / (n - 1))
    return float(np.mean(vals))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--fold", choices=["R", "T", "H"], required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--split-seed", type=int, default=2)
    a = ap.parse_args()
    out = a.out / f"denoiser_fold_{a.fold}_split{a.split_seed}"
    out.mkdir(parents=True, exist_ok=False)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src, lines = r1.load(a.keys)
    n_genes = src.d.shape[1]
    m_idx = np.where(~np.isnan(src.d).all(0))[0]
    split = r1.split_targets(src, lines, seed=a.split_seed)
    train_lines, test_lines = r1.fold_lines(lines, a.fold)
    va, te = r1.pairs(src, train_lines, split["val"]), r1.pairs(src, test_lines, split["test"])
    r1.log(f"denoiser fold {a.fold} split {a.split_seed}: val {len(va)} test {len(te)}; "
           f"test targets {len({t for _, t in te})}")
    dn = Denoiser(src, m_idx, dev)
    grid = {k: float(np.mean(r1.score(dn.predict(va, k, n_genes), va))) for k in KS}
    k = max(grid, key=grid.get)
    preds = {"k562": r1.k562_predict(src, te, m_idx, n_genes), "pca": dn.predict(te, k, n_genes),
             "mean_only": dn.predict(te, k, n_genes, mean_only=True)}
    res = {"fold": a.fold, "split_seed": a.split_seed, "k": k, "val_grid": {str(x): v for x, v in grid.items()},
           "val_cos_k562": float(np.mean(r1.score(r1.k562_predict(src, va, m_idx, n_genes), va))),
           "test_lines": [l.key for l in test_lines], "test_targets": len({t for _, t in te}),
           "test_cos": {n: float(np.mean(r1.score(p, te))) for n, p in preds.items()},
           "discrimination": {n: discrimination(p, te) for n, p in preds.items()}}
    pt = {n: r1.per_target(r1.score(p, te), te) for n, p in preds.items()}
    res["diff"] = {f"{n}-k562": r1.boot(pt[n], pt["k562"]) for n in ("pca", "mean_only")}
    res["nan_in_predictions"] = {n: bool(np.isnan(p).any()) for n, p in preds.items()}
    (out / "result.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    r1.log(json.dumps({"k": k, "test_cos": res["test_cos"], "discrimination": res["discrimination"],
                       "diff": res["diff"]}, indent=1))


if __name__ == "__main__":
    main()
