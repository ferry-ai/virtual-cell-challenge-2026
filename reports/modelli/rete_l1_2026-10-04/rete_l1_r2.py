"""Rete L1, variant `rete_anti` (ADDENDUM_1.md): the sign is the transfer's (K562 log2FC) and the network learns only
the L1-optimal magnitude, out = sign(k) * softplus(f(unsigned inputs)); out = 0 where k = 0.

Usage:
  python rete_l1_r2.py bench  --keys <chiavi> --extra <extra> --controls <raw/controls> --out <dir>
  python rete_l1_r2.py export --keys <chiavi> --extra <extra> --controls <raw/controls> --out <dir> --steps N
                              --t34 <effects_t34 dir> --targets-out <data root>/processed/l1_obiettivi_<date>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rete_l1 as r1  # noqa: E402


def unsigned(x: torch.Tensor):
    s = torch.sign(x[:, 0])
    g = torch.stack([x[:, 1], x[:, 2].abs(), x[:, 3] * s, x[:, 4] * s, x[:, 5], x[:, 6], x[:, 7], x[:, 9]], 1)
    return s, g


class NetAnti(nn.Module):
    def __init__(self, h: int = 64):
        super().__init__()
        self.f = nn.Sequential(nn.Linear(8, h), nn.GELU(), nn.Linear(h, h), nn.GELU(), nn.Linear(h, 1))
        with torch.no_grad():
            self.f[4].bias.fill_(-2.0)  # start near a small magnitude (softplus(-2) ~ 0.13)

    def forward(self, x):
        s, g = unsigned(x)
        return s * F.softplus(self.f(g).squeeze(-1))


def train(groups_data: dict, inner, dev, seed: int, max_steps: int = 4000, every: int = 250, patience: int = 6,
          fixed_steps: int | None = None):
    torch.manual_seed(seed)
    net = NetAnti().to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4)
    tens = {g: r1.to_dev(d, dev) for g, d in groups_data.items()}
    gk = sorted(tens)
    rng = np.random.default_rng(seed)
    best, best_step, best_state, bad = np.inf, 0, None, 0
    for step in range(1, (fixed_steps or max_steps) + 1):
        loss = 0.0
        for g in gk:
            X, y, w = tens[g]
            idx = torch.as_tensor(rng.integers(0, len(y), 16384), device=dev)
            loss = loss + (w[idx] * (net(X[idx]) - y[idx]).abs()).sum() / w[idx].sum()
        opt.zero_grad()
        (loss / len(gk)).backward()
        opt.step()
        if inner is not None and step % every == 0:
            v, _ = r1.eval_net(net, inner, dev)
            if v < best - 1e-5:
                best, best_step, bad = v, step, 0
                best_state = {k: x.detach().clone() for k, x in net.state_dict().items()}
            else:
                bad += 1
                if bad >= patience:
                    break
    if best_state is not None:
        net.load_state_dict(best_state)
    return net, (best_step if inner is not None else fixed_steps), best


def bench(a) -> None:
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src, data = r1.build(a)
    order = [g for g in r1.ORDER if g in data]
    res = {"folds": {}}
    per = {k: [] for k in ("zero", "copia1", "rete_anti")}
    for g in order:
        inner_g = order[(order.index(g) + 1) % len(order)]
        tr = {h: data[h] for h in order if h not in (g, inner_g)}
        net, step, vbest = train(tr, data[inner_g], dev, seed=0)
        X, y, t, n_t = data[g]
        _, p = r1.eval_net(net, data[g], dev)
        arms = {"zero": np.zeros_like(y), "copia1": X[:, 0], "rete_anti": p}
        pt = {k: r1.nmae_per_target(v, y, t, n_t) for k, v in arms.items()}
        nz = X[:, 0] != 0
        res["folds"][g] = {"inner": inner_g, "best_step": step, "inner_nmae": vbest,
                           "nmae": {k: float(v.mean()) for k, v in pt.items()},
                           "anti-zero": r1.boot(pt["rete_anti"], pt["zero"]),
                           "anti-copia1": r1.boot(pt["rete_anti"], pt["copia1"]),
                           "sign_agreement_k_nonzero": float(np.mean(np.sign(X[nz, 0]) == np.sign(y[nz]))),
                           "pred_abs_median_k_nonzero": float(np.median(np.abs(p[nz]))),
                           "y_abs_median": float(np.median(np.abs(y)))}
        for k in per:
            per[k].append(pt[k])
        r1.log(f"{g}: step {step} " + json.dumps({k: round(v, 4) for k, v in res['folds'][g]['nmae'].items()})
               + f" |m| {res['folds'][g]['pred_abs_median_k_nonzero']:.3f}")
    macro = {k: float(np.mean([v.mean() for v in vs])) for k, vs in per.items()}
    rng = np.random.default_rng(1)
    draws = np.mean([v[rng.integers(0, len(v), (10000, len(v)))].mean(1) for v in per["rete_anti"]], 0)
    macro["rete_anti_ci"] = [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))]
    macro["folds_anti_le_copia1"] = int(sum(res["folds"][g]["nmae"]["rete_anti"] <= res["folds"][g]["nmae"]["copia1"]
                                            for g in order))
    macro["h1_anti"] = res["folds"]["h1"]["nmae"]["rete_anti"]
    macro["passes"] = bool(macro["rete_anti"] <= 0.99 and macro["rete_anti_ci"][1] < 1.0 and macro["h1_anti"] < 1.0
                           and macro["folds_anti_le_copia1"] >= 5)
    macro["median_best_step"] = int(np.median([res["folds"][g]["best_step"] for g in order]))
    res["macro"] = macro
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "result.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    r1.log("macro " + json.dumps(macro))


def export(a) -> None:
    import pandas as pd
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src, data = r1.build(a)
    net, steps, _ = train(data, None, dev, seed=0, fixed_steps=a.steps)
    a.out.mkdir(parents=True, exist_ok=True)
    torch.save(net.state_dict(), a.out / "rete_anti_final.pt")
    if a.targets_out.exists():
        raise SystemExit(f"{a.targets_out} exists: never overwrite")
    a.targets_out.mkdir(parents=True)
    genes = r1.axis_genes(a.controls)
    panel = pd.read_csv(a.controls / "pert_counts.csv")["target_gene"].astype(str).drop_duplicates().tolist()
    gpos = {g: i for i, g in enumerate(genes)}
    meta = {"model_sha256": r1.sha256(a.out / "rete_anti_final.pt"), "steps": steps, "contexts": {}}
    for ctx in "ABC":
        ref, pooled = r1.ctx_cpm_and_ref(a.controls / f"context_{ctx}.h5ad", len(genes))
        gidx = np.where(ref >= r1.MIN_CPM)[0]
        z = np.load(a.t34 / f"effects_{ctx}.npz", allow_pickle=False)
        rows34 = {t: i for i, t in enumerate(map(str, z["targets"]))}
        lfc34, obs34 = z["lfc"], z["observed"]
        if list(map(str, z["genes"])) != list(genes):
            raise SystemExit("t34 effects gene order differs from the axis")
        m = np.full((len(panel), len(gidx)), np.nan, np.float32)
        with torch.no_grad():
            for i, t in enumerate(panel):
                f = r1.features(src, t, pooled, gidx)
                mag = net(torch.as_tensor(f, device=dev)).abs().cpu().numpy()
                e = lfc34[rows34[t], gidx].astype(np.float64)
                ok = obs34[rows34[t], gidx] & (e != 0) & (f[:, 0] != 0)
                m[i, ok] = (np.sign(e[ok]) * mag[ok]).astype(np.float32)
        own = np.array([gpos.get(t, -1) for t in panel])
        path = a.targets_out / f"obiettivi_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(panel, dtype=str), gene_idx=gidx.astype(np.int32), m=m,
                            ref_mean_cpm=ref.astype(np.float64), own_idx=own.astype(np.int32))
        act = np.isfinite(m)
        meta["contexts"][ctx] = {"file": path.name, "sha256": r1.sha256(path), "genes_cpm5": int(len(gidx)),
                                 "active_pairs": int(act.sum()), "targets_with_active": int(act.any(1).sum()),
                                 "m_abs_median": float(np.median(np.abs(m[act]))),
                                 "m_abs_q90": float(np.quantile(np.abs(m[act]), 0.9))}
        r1.log(f"{ctx}: {json.dumps(meta['contexts'][ctx])}")
    (a.targets_out / "export.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["bench", "export"])
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--extra", type=Path, required=True)
    ap.add_argument("--controls", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--t34", type=Path, default=None)
    ap.add_argument("--targets-out", type=Path, default=None)
    a = ap.parse_args()
    bench(a) if a.mode == "bench" else export(a)


if __name__ == "__main__":
    main()
