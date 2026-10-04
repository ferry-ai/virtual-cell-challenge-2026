"""Candidate export of the contrastive network in each context's d space (ADDENDUM_1.md, rule of the export).

Model: the phase-2 fit already saved by esporta.py (contr_final.pt, all groups, 100 steps), read back by sha256.
Per context and covered target:
  d     = K562 d-copy + model correction centred over the 272 covered targets (as on the bench);
  genes with 5e4 * p < 0.5 in the context's controls ("unexpressed") get d = 0 and observed False;
  amplitude: the d-norm over the expressed genes equals the d-norm of the t31 effect of that target, converted to
             d with the context's basal on the same genes; lfc = d_to_lfc(d, context basal).
Targets K562 does not cover: lfc 0, observed False (as t31). Stage 45 then applies --effects-scale 2.0 as for t31.
Usage: python esporta_d.py --keys <chiavi> --model <contr_final.pt> --model-sha256 <hex> --controls <raw/controls>
       --t31 <effects_t31 dir> --out <data root>/processed/effects_<name>
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
sys.path.insert(0, str(HERE.parent / "adattatore_contesto_2026-10-04"))
import adattatore as r1  # noqa: E402
from esporta_t32 import context_basal, d_to_lfc  # noqa: E402

EXPRESSED = 0.5  # minimum 5e4 * p


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--model-sha256", required=True)
    ap.add_argument("--controls", type=Path, required=True)
    ap.add_argument("--t31", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if sha256(a.model) != a.model_sha256:
        raise SystemExit("model sha256 mismatch")
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: never overwrite")
    a.out.mkdir(parents=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    z = np.load(a.keys / "replogle_k562_gwps__K562.npz", allow_pickle=False)
    eff = z["eff"].astype(np.float32)
    eff[:, ~np.asarray(z["measured"])] = np.nan
    src = r1.Line(r1.SOURCE, list(map(str, z["targets"])), r1.to_d(eff, z["basal"]), z["basal"].astype(np.float32))
    n_genes = src.d.shape[1]
    m_idx = np.where(~np.isnan(src.d).all(0))[0]
    model = r1.Adapter(m_idx, n_genes, src.basal).to(dev)
    model.load_state_dict(torch.load(a.model, map_location=dev))
    model.eval()
    meta = {"model": str(a.model.name), "model_sha256": a.model_sha256, "expressed_min_5e4p": EXPRESSED,
            "contexts": {}}
    for ctx in "ABC":
        t31 = np.load(a.t31 / f"effects_{ctx}.npz", allow_pickle=False)
        targets, genes = list(map(str, t31["targets"])), np.asarray(t31["genes"], str)
        basal = context_basal(a.controls / f"context_{ctx}.h5ad", genes)
        expressed = 5e4 * np.expm1(basal.astype(np.float64)) / 1e4 >= EXPRESSED
        cov = [i for i, t in enumerate(targets) if t in src.row]
        x = torch.as_tensor(np.stack([np.nan_to_num(src.d[src.row[targets[i]]][m_idx]) for i in cov]), device=dev)
        with torch.no_grad():
            out = torch.cat([model(x[s:s + 128], torch.as_tensor(basal, device=dev)) for s in range(0, len(cov), 128)])
        copy = torch.zeros_like(out)
        copy[:, model.m_idx] = x
        corr = (out - copy).double().cpu().numpy()
        mu = corr.mean(0)
        share = float(len(cov) * (mu ** 2).sum() / (corr ** 2).sum())
        d = copy.double().cpu().numpy() + corr - mu
        d[:, ~expressed] = 0.0
        d31 = r1.to_d(t31["lfc"][cov].astype(np.float32), basal).astype(np.float64)
        d31[:, ~expressed] = 0.0
        ref, cur = np.linalg.norm(d31, axis=1), np.linalg.norm(d, axis=1)
        d *= (ref / np.where(cur > 0, cur, 1))[:, None]
        lfc = np.zeros((len(targets), n_genes), np.float32)
        observed = np.zeros((len(targets), n_genes), bool)
        lfc[cov] = np.stack([d_to_lfc(row, basal) for row in d])
        lfc[np.ix_(cov, np.where(~expressed)[0])] = 0.0
        observed[np.ix_(cov, np.where(expressed)[0])] = True
        path = a.out / f"effects_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(targets, dtype=str), genes=genes, lfc=lfc, observed=observed)
        cos_d = np.sum(d * d31, 1) / (np.linalg.norm(d, axis=1) * np.linalg.norm(d31, axis=1) + 1e-12)
        L31 = t31["lfc"][cov].astype(np.float64)
        cos_l = np.sum(lfc[cov] * L31, 1) / (np.linalg.norm(lfc[cov], axis=1) * np.linalg.norm(L31, axis=1) + 1e-12)
        meas = np.asarray(z["measured"])
        e_U = float((lfc[cov][:, ~meas].astype(np.float64) ** 2).sum() / max((lfc[cov].astype(np.float64) ** 2).sum(), 1e-12))
        meta["contexts"][ctx] = {
            "file": path.name, "sha256": sha256(path), "covered": len(cov), "expressed_genes": int(expressed.sum()),
            "controls_sha256": sha256(a.controls / f"context_{ctx}.h5ad"),
            "common_share_before_centring": share, "send_allowed_by_share": share <= 0.5,
            "median_cos_d_with_t31": float(np.median(cos_d)), "median_cos_lfc_with_t31": float(np.median(cos_l)),
            "lfc_energy_share_on_genes_k562_does_not_measure": e_U,
            "lfc_abs_mean_observed": float(np.abs(lfc[observed]).mean()),
            "t31_lfc_abs_mean_observed": float(np.abs(t31["lfc"][t31["observed"]]).mean()),
            "lfc_abs_max": float(np.abs(lfc).max())}
        r1.log(f"{ctx}: share {share:.3f}; median cos with t31 d {np.median(cos_d):.3f} lfc {np.median(cos_l):.3f}; "
               f"U energy {e_U:.3f}; |lfc| mean {meta['contexts'][ctx]['lfc_abs_mean_observed']:.4f} "
               f"(t31 {meta['contexts'][ctx]['t31_lfc_abs_mean_observed']:.4f}), max {meta['contexts'][ctx]['lfc_abs_max']:.2f}")
    (a.out / "export.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
