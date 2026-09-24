"""Leave-one-source-out bench of recipe variants, in effect space. Proxies, not VCC scores.

For each held-out source H, the panel effects of H are predicted from the OTHER sources of
the stage-98 cache with `vcc2026.multisource.mix`, under variants of the t15 recipe, and the
prediction is compared with H's own effects through two proxies of official members:

* PDS proxy -- cosine between a target's predicted effects and every held-out target's
  effects, genes weighted as the scorer's log1p pseudobulk (bulk_target_sum 5e4) weighs a
  small effect in an official context, x / (1 + x) with x = 0.05 * CPM of that context; all
  300 panel genes excluded (exclusion_scope 'panel'); rank of the true target among the
  held-out targets, midrank ties, denominator n - 1; mean over targets.
* fidelity proxy -- per target, the top N genes by |predicted effect| among genes at
  >= 5 CPM in the context (the scorer's DE gate), target gene excluded, held-out effect
  finite and non-zero. precision = share with the held-out sign (significance not required,
  as the scorer's k); yield = k / max(N, n_conf), n_conf = held-out genes with |raw/se| >= 3.

Variants change direction or ranking only: both proxies ignore a global amplitude.

    scripts/py.cmd reports/banco_varianti_2026-09-25/analyze.py --out reports/banco_varianti_2026-09-25/r1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.multisource import AxisTable, mix  # noqa: E402

DATA = config.paths().data_root
SOURCES = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]
FAMILY = {"k562": "k562", "cd4_mix": "cd4", "orion_hct116": "orion", "orion_hek293t": "orion"}
TOP_N = (50, 200, 800)
SEED = 20260925


def load(cache: Path, name: str, effect: str) -> AxisTable:
    z = np.load(cache / f"{name}.npz", allow_pickle=True)
    main = z["raw"] if effect == "raw" else z["shrunk"]
    return AxisTable(name, z["targets"].astype(str).tolist(), main, z["raw"], z["se"], z["n_cells"], {})


def consensus_factor(tables, targets, weights) -> np.ndarray:
    """|weighted sum| / weighted sum of |x| over sources, per (target, gene): 1 when all agree."""
    G = tables[0].shrunk.shape[1]
    s = np.zeros((len(targets), G))
    a = np.zeros((len(targets), G))
    for tab in tables:
        w = float(weights.get(tab.name, 1.0))
        rows = tab.rows(targets).astype(np.float64)
        rows = rows - tab.common()          # same centring as gamma 1
        ok = np.isfinite(rows)
        s[ok] += w * rows[ok]
        a[ok] += w * np.abs(rows[ok])
    return np.divide(np.abs(s), a, out=np.zeros_like(s), where=a > 0)


def predict(variant: str, preds: list[str], cache: Path, targets: list[str]) -> np.ndarray:
    effect = "shrunk" if variant == "shrunk_g1" else "raw"
    tabs = [load(cache, n, effect) for n in preds]
    w = {n: 1.0 for n in preds}
    gamma = {"g0": 0.0, "g05": 0.5}.get(variant, 1.0)
    eff, den = mix(tabs, targets, weights=w, gamma=gamma, reliability_scale=100.0)
    if variant.startswith("consensus"):
        c = consensus_factor(tabs, targets, w)
        eff = eff * (c ** (2 if variant == "consensus2" else 1))
    eff[den == 0] = 0.0
    return eff


def pds_proxy(P, T, weight, panel_cols):
    """Mean over targets of 1 - rank / (n - 1), cosine, midrank; T NaN = unmeasured."""
    w = weight.copy()
    w[panel_cols] = 0.0
    A = P * w
    B = np.nan_to_num(T) * w
    na = np.linalg.norm(A, axis=1)
    nb = np.linalg.norm(B, axis=1)
    cos = (A @ B.T) / np.maximum(np.outer(na, nb), 1e-12)
    n = cos.shape[0]
    d = np.diag(cos)
    greater = (cos > d[:, None]).sum(axis=1)
    ties = (cos == d[:, None]).sum(axis=1) - 1
    per = 1.0 - (greater + 0.5 * ties) / max(n - 1, 1)
    return per


def fidelity_proxy(P, T, Z, gate, target_cols):
    out = {f"prec_{n}": [] for n in TOP_N}
    out.update({f"yield_{n}": [] for n in TOP_N})
    out.update({f"up_{n}": [] for n in TOP_N})
    out["n_conf"] = []
    for i in range(P.shape[0]):
        ok = gate & np.isfinite(T[i]) & (T[i] != 0) & (P[i] != 0)
        if target_cols[i] >= 0:
            ok[target_cols[i]] = False
        idx = np.flatnonzero(ok)
        if idx.size < 50:
            continue
        order = idx[np.argsort(-np.abs(P[i, idx]), kind="stable")]
        same = np.sign(P[i, order]) == np.sign(T[i, order])
        up = P[i, order] > 0
        conf = int((np.abs(Z[i, idx]) >= 3).sum())
        out["n_conf"].append(conf)
        for n in TOP_N:
            k = int(same[:n].sum())
            m = min(n, same.size)
            out[f"prec_{n}"].append(k / m)
            out[f"yield_{n}"].append(k / max(m, conf) if max(m, conf) > 0 else np.nan)
            out[f"up_{n}"].append(float(up[:n].mean()))
    return {k: np.asarray(v, dtype=float) for k, v in out.items()}


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
    assert basal.notna().all().all(), "basal CPM table does not cover the axis"
    ctx = {c: basal[c].to_numpy(dtype=float) for c in ("A", "B", "C")}

    variants = ["base_g1", "g0", "g05", "shrunk_g1", "consensus1", "consensus2"]
    rng = np.random.default_rng(SEED)
    rows, per_target = [], []
    for held in SOURCES:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = load(args.cache, held, "raw")
        tidx = truth.index()
        for variant in variants + ["shuffled_base"]:
            v = "base_g1" if variant == "shuffled_base" else variant
            targets = [t for t in panel if t in tidx]
            P = predict(v, preds, args.cache, targets)
            has = np.abs(P).sum(axis=1) > 0
            targets = [t for t, h in zip(targets, has) if h]
            P = P[has]
            if variant == "shuffled_base":
                P = P[rng.permutation(len(targets))]
            r = np.array([tidx[t] for t in targets])
            T = truth.raw[r].astype(np.float64)       # held-out effect, not shrunk
            Z = (truth.raw[r] / truth.se[r]).astype(np.float64)
            tcols = np.array([col.get(t, -1) for t in targets])
            for c, cpm in ctx.items():
                x = 0.05 * cpm
                pds = pds_proxy(P, T, x / (1.0 + x), panel_cols)
                fid = fidelity_proxy(P, T, Z, cpm >= 5.0, tcols)
                row = {"held_out": held, "predictors": "+".join(preds), "variant": variant, "context_weights": c,
                       "targets": len(targets), "pds_proxy": float(pds.mean())}
                for k, vals in fid.items():
                    row[k] = float(np.nanmean(vals)) if vals.size else None
                rows.append(row)
                if variant == "base_g1" and c == "A":
                    for t, p in zip(targets, pds):
                        per_target.append({"held_out": held, "target": t, "pds_proxy_A": float(p)})
            print(held, variant, "done", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(args.out / "variants.csv", index=False)
    pd.DataFrame(per_target).to_csv(args.out / "per_target_base.csv", index=False)
    mean = (df.groupby(["held_out", "variant"])[["pds_proxy", "prec_200", "prec_800", "yield_800", "up_800"]]
              .mean().round(4))
    src = Path(args.cache)
    meta = {"stage": "banco_varianti_2026-09-25/analyze.py", "claim_type":
            "effect-space proxies on public sources, leave one source family out; not VCC scores",
            "cache": str(src), "cache_sha256": {s: hashlib.sha256((src / f"{s}.npz").read_bytes()).hexdigest()
                                                 for s in SOURCES},
            "seed": SEED, "top_n": TOP_N, "variants": variants + ["shuffled_base"],
            "mean_over_contexts": mean.reset_index().to_dict("records")}
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump(meta, f, indent=1, default=str)
    print(mean.to_string())


if __name__ == "__main__":
    main()
