"""Phase 2 of PROTOCOLLO.md: fit the contrastive network on every group for the median of the folds' best steps,
export effects for A, B, C and measure the common share of the correction before centring.

Amplitude: per target, the L2 norm of the t31 lfc row (A0 x K562 lfc), so that against t31 only the direction changes.
Targets K562 does not cover stay at lfc 0, observed False, as in t31. Writes effects_<CTX>.npz (stage-45 layout) and
export.json. Usage: python esporta.py --keys <chiavi> --extra <extra> --controls <raw/controls> --t31 <effects_t31>
       --steps N --out <data root>/processed/effects_contr_<date>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "adattatore_contesto_2026-10-04"))
import adattatore as r1  # noqa: E402
import adattatore_r3 as r3  # noqa: E402
import contrastiva as c  # noqa: E402
from esporta_t32 import context_basal, d_to_lfc  # noqa: E402


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fit(src, groups, prs, m_idx, n_genes, dev, steps, seed=0):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = r1.Adapter(m_idx, n_genes, src.basal).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    by_group: dict[str, dict[str, list]] = {}
    for p in prs:
        by_group.setdefault(groups[p[0].key], {}).setdefault(p[0].key, []).append(p)
    gkeys = sorted(by_group)
    model.train()
    for _ in range(steps):
        lines_g = by_group[gkeys[rng.integers(len(gkeys))]]
        cand = lines_g[list(lines_g)[rng.integers(len(lines_g))]]
        part = [cand[i] for i in rng.choice(len(cand), size=min(64, len(cand)), replace=False)]
        x, y = r1.batch(src, part, m_idx, dev)
        out = model(x, torch.as_tensor(part[0][0].basal, device=dev))
        copy = torch.zeros_like(out)
        copy[:, model.m_idx] = x
        corr = out - copy
        loss = c.info_nce(copy + corr - corr.mean(0, keepdim=True), y)
        opt.zero_grad()
        loss.backward()
        opt.step()
    model.eval()
    return model


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--extra", type=Path, required=True)
    ap.add_argument("--controls", type=Path, required=True)
    ap.add_argument("--t31", type=Path, required=True)
    ap.add_argument("--steps", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: never overwrite")
    a.out.mkdir(parents=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src, lines, groups = r3.load_all(a.keys, a.extra)
    n_genes = src.d.shape[1]
    m_idx = np.where(~np.isnan(src.d).all(0))[0]
    prs = [(ln, t) for ln in lines for t in ln.targets if t in src.row]
    r1.log(f"fit on {len(lines)} lines ({len(set(groups[l.key] for l in lines))} groups), {len(prs)} pairs, "
           f"{a.steps} steps")
    model = fit(src, groups, prs, m_idx, n_genes, dev, a.steps)
    torch.save(model.state_dict(), a.out / "contr_final.pt")
    meta = {"steps": a.steps, "pairs": len(prs), "lines": sorted(l.key for l in lines), "contexts": {},
            "model_sha256": sha256(a.out / "contr_final.pt")}
    for ctx in "ABC":
        t31 = np.load(a.t31 / f"effects_{ctx}.npz", allow_pickle=False)
        targets, genes = list(map(str, t31["targets"])), np.asarray(t31["genes"], str)
        basal = context_basal(a.controls / f"context_{ctx}.h5ad", genes)
        cov = [i for i, t in enumerate(targets) if t in src.row]
        x = torch.as_tensor(np.stack([src.d[src.row[targets[i]]][m_idx] for i in cov]), device=dev)
        with torch.no_grad():
            out = torch.cat([model(x[s:s + 128], torch.as_tensor(basal, device=dev)) for s in range(0, len(cov), 128)])
        copy = torch.zeros_like(out)
        copy[:, model.m_idx] = x
        corr = (out - copy).double().cpu().numpy()
        mu = corr.mean(0)
        share = float(len(cov) * (mu ** 2).sum() / (corr ** 2).sum())
        d = copy.double().cpu().numpy() + corr - mu
        raw = np.stack([d_to_lfc(row, basal) for row in d])
        ref = np.linalg.norm(t31["lfc"][cov].astype(np.float64), axis=1)
        cur = np.linalg.norm(raw.astype(np.float64), axis=1)
        lfc = np.zeros((len(targets), n_genes), np.float32)
        observed = np.zeros((len(targets), n_genes), bool)
        lfc[cov] = raw * (ref / np.where(cur > 0, cur, 1))[:, None]
        observed[cov] = True
        path = a.out / f"effects_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(targets, dtype=str), genes=genes, lfc=lfc, observed=observed)
        cos31 = [float(np.dot(lfc[i], t31["lfc"][i]) / (np.linalg.norm(lfc[i]) * np.linalg.norm(t31["lfc"][i]) + 1e-12))
                 for i in cov]
        rel = float(np.sqrt((corr - mu) ** 2).mean() / (np.abs(copy.double().cpu().numpy()).mean() + 1e-12))
        meta["contexts"][ctx] = {"file": path.name, "sha256": sha256(path), "covered": len(cov),
                                 "controls_sha256": sha256(a.controls / f"context_{ctx}.h5ad"),
                                 "common_share_before_centring": share, "send_allowed_by_share": share <= 0.5,
                                 "median_cos_with_t31": float(np.median(cos31)),
                                 "mean_abs_correction_over_mean_abs_copy": rel,
                                 "lfc_abs_mean_covered": float(np.abs(lfc[cov]).mean())}
        r1.log(f"{ctx}: covered {len(cov)}; common share {share:.3f}; median cos with t31 {np.median(cos31):.3f}")
    (a.out / "export.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
