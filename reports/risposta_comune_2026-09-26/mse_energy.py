"""A local predictor of the official mse member: predicted energy against the published raw values.

claude2's analysis (agenti/membro_mse_claude2.md) writes the member, in expectation, as
u = 1 + ||d_hat||^2 / D - 2 <d_hat, d> / D, with d_hat the predicted pseudobulk delta in the scorer's
space (log1p of 5e4 x composition), d the real one, D the real effects' summed energy. This computes
E = sum over targets and genes (own gene out) of (mu_pred - mu_ctrl)^2 from each submitted effects
file and the A/B/C control CPM, with the trial-01 profile step (|log2 FC| clipped at 6, composition
renormalised over the observed genes, as reports/banco_varianti_2026-09-25/noise_sim2.realise), and
fits the published raw u against E over the six trial-01-generator submissions that have both.
No cells are generated; the sampling corrections are assumed not to bind (claude2, section 2).

    scripts/py.cmd reports/risposta_comune_2026-09-26/mse_energy.py --out reports/risposta_comune_2026-09-26/r2
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("C:/Users/ferra/vcc2026-data")
TS = 5e4
LN2 = np.log(2.0)
OFFICIAL = {  # published raw expr_mse_unbiased_capped_norm, reports/trial_*/status_*.json
    "t08": 1.152371863720626, "t10": 1.2970197825606362, "t11": 1.1290387149435794,
    "t15": 1.5794312874980363, "t17": 1.5021517492639624, "t20": 3.877523999907396,
}
EFFECTS = {"t08": "effects_t08_2026-09-22", "t10": "effects_t10_2026-09-23", "t11": "effects_t11_2026-09-23",
           "t12": "effects_t12_2026-09-23", "t15": "effects_t15_2026-09-23", "t16": "effects_t16_2026-09-24",
           "t17": "effects_t17_2026-09-24", "t18": "effects_t18_2026-09-25", "t19": "effects_t19_2026-09-25",
           "t20": "effects_t20_2026-09-26", "t22": "effects_t22_2026-09-26"}


def energy(path: Path, basal: pd.DataFrame) -> dict:
    out = {}
    for c in ("A", "B", "C"):
        z = np.load(path / f"effects_{c}.npz")
        genes = z["genes"].astype(str)
        targets = z["targets"].astype(str)
        lfc = z["lfc"].astype(np.float64)
        obs = z["observed"] if "observed" in z.files else np.abs(lfc) > 0
        p = np.nan_to_num(basal.reindex(genes)[c].to_numpy(dtype=float)) / 1e6
        d = np.clip(lfc / LN2, -6.0, 6.0)
        b = p[None, :] * obs
        moved = (b * np.exp2(d)).sum(axis=1)
        flat = b.sum(axis=1)
        shift = np.log2(np.divide(flat, moved, out=np.ones_like(flat), where=moved > 0))
        real_ln = np.where(obs, (d + shift[:, None]) * LN2, 0.0)
        mu_c = np.log1p(TS * p)
        diff = np.log1p(TS * p[None, :] * np.exp(real_ln)) - mu_c[None, :]
        col = {g: i for i, g in enumerate(genes)}
        for i, t in enumerate(targets):
            if t in col:
                diff[i, col[t]] = 0.0
        out[c] = float((diff ** 2).sum())
    out["mean"] = float(np.mean([out[c] for c in ("A", "B", "C")]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    basal = pd.read_csv(args.basal).set_index("gene_name")
    rows = []
    for name, folder in EFFECTS.items():
        path = DATA / "processed" / folder
        if not (path / "effects_A.npz").exists():
            continue
        e = energy(path, basal)
        rows.append({"trial": name, "E_mean": e["mean"], "E_A": e["A"], "E_B": e["B"], "E_C": e["C"],
                     "official_raw": OFFICIAL.get(name)})
        print(name, round(e["mean"], 2), OFFICIAL.get(name), flush=True)
    df = pd.DataFrame(rows)
    fit = df.dropna(subset=["official_raw"])
    x, y = fit["E_mean"].to_numpy(), fit["official_raw"].to_numpy() - 1.0
    slope0 = float((x * y).sum() / (x * x).sum())                     # through the origin: u - 1 = E / D
    A = np.column_stack([np.ones_like(x), x])
    (icpt, slope1), *_ = np.linalg.lstsq(A, y, rcond=None)
    pred0 = 1.0 + slope0 * df["E_mean"]
    pred1 = 1.0 + icpt + slope1 * df["E_mean"]
    df["pred_through_origin"], df["pred_with_intercept"] = pred0, pred1
    resid0 = (1.0 + slope0 * x) - (y + 1.0)
    resid1 = (1.0 + icpt + slope1 * x) - (y + 1.0)
    summary = {"stage": "risposta_comune_2026-09-26/mse_energy.py",
               "claim_type": "energy computed from submitted effects files; fit against published raw values; an "
                             "interpretation of the member, not a measurement of the real effects",
               "points": int(len(fit)), "D_through_origin": 1.0 / slope0 if slope0 > 0 else None,
               "fit_through_origin_max_abs_residual": float(np.abs(resid0).max()),
               "fit_with_intercept": {"intercept": float(icpt), "slope": float(slope1),
                                      "max_abs_residual": float(np.abs(resid1).max())},
               "rows": df.to_dict(orient="records")}
    df.to_csv(args.out / "energy.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, default=float)
    pd.set_option("display.width", 200)
    print(df.round(4).to_string(index=False))
    print({k: v for k, v in summary.items() if k != "rows"})


if __name__ == "__main__":
    main()
