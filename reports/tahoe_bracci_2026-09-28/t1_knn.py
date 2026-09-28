"""T1, reduced (RISULTATI.md, registered at 04:23 on 28/09): does a line's basal state (its DMSO profile) predict how
its response to a drug departs from the other lines' average response?

Leave one line out. For each drug-dose d measured in the held-out line L and in at least --min-lines other lines:
* blind: the gene-wise mean response of the other lines to d;
* knn: the mean response to d of the k training lines (among those with d) most similar to L in basal state;
* swap: the same, with the neighbours of another line L' (drawn with a fixed seed; L' != L, neighbours exclude L').
Basal state: per line, DMSO counts summed over plates (the Tahoe corpus), log1p CPM, standardised over the training
lines on their 2,000 most variable genes; similarity = Pearson correlation. Everything is computed without L.
Per pair (L, d), on the genes finite in the truth and in the three arms: MSE of each arm and of predicting 0; skill =
1 - sum MSE / sum MSE0 over the pairs. Contrasts knn - blind and knn - swap as skill differences, 95 % intervals by
bootstrap over held-out lines (2,000 resamples, seed 0). Descriptive: k = 3 and 10, by dose, the strong stratum.

    python t1_knn.py --effects EFFECTS_DIR --basal tahoe.npz --out NEW
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def basal_by_line(npz: Path) -> tuple[list, np.ndarray]:
    z = np.load(npz, allow_pickle=False)
    meta = pd.read_csv(npz.with_suffix(".csv"), keep_default_na=False, na_values=[""])
    counts = z["counts"].astype(np.float64)
    lib = z["library"].astype(np.float64)
    lines = sorted(meta["cellosaurus"].astype(str).unique())
    measured = np.isfinite(counts).all(axis=0)
    out = []
    for ln in lines:
        rows = np.flatnonzero(meta["cellosaurus"].astype(str).to_numpy() == ln)
        c = np.nansum(counts[rows], axis=0)
        out.append(np.log1p(1e6 * c / lib[rows].sum()))
    x = np.vstack(out)
    x[:, ~measured] = np.nan
    return lines, x


def neighbours(x: np.ndarray, target: int, pool: list, k: int, n_hvg: int) -> list:
    """The k lines of `pool` most similar to `target`; genes and standardisation from `pool` only."""
    xp = x[pool]
    ok = np.isfinite(xp).all(axis=0) & np.isfinite(x[target])
    var = np.where(ok, np.nanvar(xp, axis=0), -1.0)
    hv = np.argsort(var)[::-1][:n_hvg]
    mu, sd = xp[:, hv].mean(axis=0), xp[:, hv].std(axis=0) + 1e-6
    zp = (xp[:, hv] - mu) / sd
    zt = (x[target, hv] - mu) / sd
    zp = zp - zp.mean(axis=1, keepdims=True)
    zt = zt - zt.mean()
    sim = (zp @ zt) / (np.linalg.norm(zp, axis=1) * np.linalg.norm(zt) + 1e-12)
    order = np.argsort(sim)[::-1][:k]
    return [pool[i] for i in order]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--effects", type=Path, required=True)
    ap.add_argument("--basal", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--k-extra", default="3,10")
    ap.add_argument("--min-lines", type=int, default=10)
    ap.add_argument("--n-hvg", type=int, default=2000)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    e = np.load(args.effects / "effects.npz", allow_pickle=False)
    y_all = e["shrunk"].astype(np.float32)
    ecl, edrug, edose = e["cell_line"].astype(str), e["drug"].astype(str), e["dose"].astype(str)
    blines, bx = basal_by_line(args.basal)
    lines = sorted(set(blines) & set(ecl.tolist()))
    bidx = {ln: i for i, ln in enumerate(blines)}
    x = bx[[bidx[ln] for ln in lines]]
    li = {ln: i for i, ln in enumerate(lines)}
    arm = np.array([f"{d}|{v}" for d, v in zip(edrug, edose)])
    row_of = {}
    for r, (ln, a) in enumerate(zip(ecl, arm)):
        if ln in li:
            row_of[(li[ln], a)] = r
    arms = sorted(set(arm.tolist()))
    have = {a: [l for l in range(len(lines)) if (l, a) in row_of] for a in arms}
    rng = np.random.default_rng(args.seed)
    ks = [args.k] + [int(k) for k in args.k_extra.split(",") if k.strip()]
    recs = []
    for L in range(len(lines)):
        others = [l for l in range(len(lines)) if l != L]
        Lp = int(rng.choice(others))
        for a in arms:
            if (L, a) not in row_of:
                continue
            train = [l for l in have[a] if l != L]
            if len(train) < args.min_lines:
                continue
            y = y_all[row_of[(L, a)]].astype(np.float64)
            ytr = np.vstack([y_all[row_of[(l, a)]] for l in train]).astype(np.float64)
            with np.errstate(invalid="ignore"):
                blind = np.nanmean(ytr, axis=0)
            preds = {"blind": blind}
            for k in ks:
                nb = neighbours(x, L, train, k, args.n_hvg)
                sw_pool = [l for l in train if l != Lp]
                sw = neighbours(x, Lp, sw_pool, k, args.n_hvg)
                with np.errstate(invalid="ignore"):
                    preds[f"knn{k}"] = np.nanmean(np.vstack([y_all[row_of[(l, a)]] for l in nb]), axis=0)
                    preds[f"swap{k}"] = np.nanmean(np.vstack([y_all[row_of[(l, a)]] for l in sw]), axis=0)
            ok = np.isfinite(y)
            for p in preds.values():
                ok &= np.isfinite(p)
            if ok.sum() < 100:
                continue
            rec = {"line": lines[L], "arm": a, "drug": a.split("|")[0], "dose": a.split("|")[1], "genes": int(ok.sum()),
                   "train_lines": len(train), "mse0": float(np.mean(y[ok] ** 2)),
                   "blind_norm": float(np.linalg.norm(blind[ok]))}
            for name, p in preds.items():
                rec[f"mse_{name}"] = float(np.mean((p[ok] - y[ok]) ** 2))
            recs.append(rec)
    df = pd.DataFrame(recs)
    df.to_csv(args.out / "per_pair.csv", index=False)

    def skill(d: pd.DataFrame, name: str) -> float:
        return float(1.0 - d[f"mse_{name}"].sum() / d["mse0"].sum())

    def contrast(d: pd.DataFrame, a: str, b: str) -> dict:
        byline = d.groupby("line")
        per = pd.DataFrame({"a": byline[f"mse_{a}"].sum(), "b": byline[f"mse_{b}"].sum(), "m0": byline["mse0"].sum()})
        point = float((per.b.sum() - per.a.sum()) / per.m0.sum())
        r = np.random.default_rng(args.seed)
        n = len(per)
        boots = []
        for _ in range(args.n_boot):
            s = per.iloc[r.integers(0, n, n)]
            boots.append((s.b.sum() - s.a.sum()) / s.m0.sum())
        return {"mean": point, "ci95": [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))],
                "lines": n, "pairs": int(len(d))}

    k0 = args.k
    out = {"stage": "tahoe_bracci_2026-09-28/t1_knn.py", "lines": len(lines), "arms": len(arms), "pairs": int(len(df)),
           "k": k0, "claim_type": "exploratory bench on Tahoe drug arms; not a VCC score"}
    out["skill"] = {name: skill(df, name) for name in ["blind"] + [f"{p}{k}" for k in ks for p in ("knn", "swap")]}
    out["rule"] = {"knn_minus_blind": contrast(df, f"knn{k0}", "blind"),
                   "knn_minus_swap": contrast(df, f"knn{k0}", f"swap{k0}")}
    r = out["rule"]
    out["passes"] = bool(r["knn_minus_blind"]["ci95"][0] > 0 and r["knn_minus_swap"]["ci95"][0] > 0)
    out["descriptive"] = {f"k{k}": {"knn_minus_blind": contrast(df, f"knn{k}", "blind"),
                                    "knn_minus_swap": contrast(df, f"knn{k}", f"swap{k}")} for k in ks[1:]}
    out["by_dose"] = {dose: {"pairs": int(len(g)), "knn_minus_blind": contrast(g, f"knn{k0}", "blind")}
                      for dose, g in df.groupby("dose") if g["line"].nunique() >= 5}
    strong = df[df["blind_norm"] >= df["blind_norm"].quantile(0.75)]
    out["strong"] = {"pairs": int(len(strong)), "knn_minus_blind": contrast(strong, f"knn{k0}", "blind"),
                     "knn_minus_swap": contrast(strong, f"knn{k0}", f"swap{k0}")}
    with (args.out / "summary.json").open("x", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: out[k] for k in ("lines", "arms", "pairs", "skill", "rule", "passes")}, indent=1))


if __name__ == "__main__":
    main()
