"""Second pass of the leave-one-source-out bench: how much shrinkage, and how to pool sources.

Same held-out sources, proxies and gene weights as analyze.py (imported from it). The
variants rebuild each source's effect from its raw fold change and SE:

* ``raw``            -- the t15 recipe (effect raw, gamma 1, reliability 100, equal weights);
* ``zk<k>``          -- local shrinkage raw * z^2 / (z^2 + k), z = raw / se; zk4 is the
  stage-98 ``shrunk`` array;
* ``zk4_ivw``        -- zk4, but sources pooled per (target, gene) by inverse variance
  (1 / se^2, capped at the 99th percentile of each source) instead of cell reliability.

    scripts/py.cmd reports/banco_varianti_2026-09-25/shrink_sweep.py --out reports/banco_varianti_2026-09-25/r2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from analyze import DATA, FAMILY, SOURCES, fidelity_proxy, pds_proxy  # noqa: E402
from vcc2026.multisource import AxisTable, mix  # noqa: E402


def table(cache: Path, name: str, k: float | None) -> AxisTable:
    z = np.load(cache / f"{name}.npz", allow_pickle=True)
    raw, se = z["raw"].astype(np.float64), z["se"].astype(np.float64)
    if k is None:
        main = raw
    else:
        zz = np.divide(raw, se, out=np.zeros_like(raw), where=se > 0) ** 2
        main = raw * zz / (zz + k)
    return AxisTable(name, z["targets"].astype(str).tolist(), main.astype(np.float32), z["raw"], z["se"],
                     z["n_cells"], {})


def ivw_mix(tabs, targets):
    """Inverse-variance pooling of centred effects (gamma 1), per (target, gene)."""
    G = tabs[0].shrunk.shape[1]
    num = np.zeros((len(targets), G))
    den = np.zeros((len(targets), G))
    for tab in tabs:
        rows = tab.rows(targets).astype(np.float64) - tab.common()
        idx = tab.index()
        se = np.full((len(targets), G), np.nan)
        for i, t in enumerate(targets):
            if t in idx:
                se[i] = tab.se[idx[t]]
        w = 1.0 / np.square(se)
        cap = np.nanpercentile(w[np.isfinite(w)], 99)
        w = np.minimum(w, cap)
        ok = np.isfinite(rows) & np.isfinite(w)
        num[ok] += w[ok] * rows[ok]
        den[ok] += w[ok]
    return np.divide(num, den, out=np.zeros_like(num), where=den > 0), den


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "interim/basal_cpm_by_context.csv")
    ap.add_argument("--genes", type=Path, default=DATA / "raw/controls/gene_names.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = pd.read_csv(args.genes)["gene_name"].astype(str).to_numpy()
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    col = {g: i for i, g in enumerate(axis)}
    panel_cols = np.array([col[g] for g in panel if g in col])
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    ctx = {c: basal[c].to_numpy(dtype=float) for c in ("A", "B", "C")}

    variants = {"raw": None, "zk1": 1.0, "zk4": 4.0, "zk16": 16.0, "zk64": 64.0, "zk4_ivw": 4.0}
    rows = []
    for held in SOURCES:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = table(args.cache, held, None)
        tidx = truth.index()
        base_targets = [t for t in panel if t in tidx]
        for name, k in variants.items():
            tabs = [table(args.cache, s, k) for s in preds]
            if name.endswith("_ivw"):
                P, den = ivw_mix(tabs, base_targets)
            else:
                P, den = mix(tabs, base_targets, weights={s: 1.0 for s in preds}, gamma=1.0,
                             reliability_scale=100.0)
            P[den == 0] = 0.0
            has = np.abs(P).sum(axis=1) > 0
            targets = [t for t, h in zip(base_targets, has) if h]
            P = P[has]
            r = np.array([tidx[t] for t in targets])
            T = truth.raw[r].astype(np.float64)
            Z = (truth.raw[r] / truth.se[r]).astype(np.float64)
            tcols = np.array([col.get(t, -1) for t in targets])
            q99 = float(np.nanmedian(np.nanquantile(np.abs(P), 0.99, axis=1)))
            for c, cpm in ctx.items():
                x = 0.05 * cpm
                pds = pds_proxy(P, T, x / (1.0 + x), panel_cols)
                fid = fidelity_proxy(P, T, Z, cpm >= 5.0, tcols)
                row = {"held_out": held, "variant": name, "context_weights": c, "targets": len(targets),
                       "pds_proxy": float(pds.mean()), "median_q99_abs": q99}
                for key, vals in fid.items():
                    row[key] = float(np.nanmean(vals)) if vals.size else None
                rows.append(row)
            print(held, name, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(args.out / "variants.csv", index=False)
    mean = df.groupby(["held_out", "variant"])[["pds_proxy", "prec_200", "prec_800", "median_q99_abs"]].mean()
    delta = (mean["pds_proxy"] - mean.xs("raw", level="variant")["pds_proxy"].reindex(
        mean.index.get_level_values(0)).to_numpy()).rename("pds_minus_raw")
    out = pd.concat([mean, delta], axis=1).round(4)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "banco_varianti_2026-09-25/shrink_sweep.py", "claim_type":
                   "effect-space proxies on public sources, leave one source family out; not VCC scores",
                   "cache": str(args.cache), "summary": out.reset_index().to_dict("records")}, f, indent=1)
    print(out.to_string())


if __name__ == "__main__":
    main()
