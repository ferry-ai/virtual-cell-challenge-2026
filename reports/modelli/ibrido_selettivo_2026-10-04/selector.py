"""The selector and the fixed mixture of the D-056 hybrid (PROTOCOLLO.md §4 and §6), fitted on rows of other lines.

A row (hybrid_lanes.py rows) is one C target of one held-out line with, per arm, a = sum om R^2 / sum om and
b = sum om R (y - T) / sum om: the change of the weighted squared error of T + w R against the truth is a w^2 - 2 b w.
- fixed mixture: w_fix = clip(sum b / sum a, 0, 1) over the fitting rows;
- selector: w = sigmoid(b0 + z . beta), z the five inputs standardised on the fitting rows (log(1 + support),
  concordance, log(RMS(R)/RMS(T)), cos(R, T), control expression of the target gene); it minimises
  sum(a w^2 - 2 b w) / sum(a) + alpha |beta|^2 (alpha = 0.01, intercept free), from beta = 0, b0 = 0. Amendment of
  PROTOCOLLO.md §12 (4/10, before any output was read): the frozen form, mean(a w^2 - 2 b w) + |beta|^2, is not
  scale-free, and its penalty made the selector a constant mixture whatever the data (test_selector).
Nothing here reads the line the weights are applied to beyond its inputs (support, concordance, R, T, expression).

    py selector.py lolo  --rows H1=<rows_H1.csv.gz> HepG2=<...> RPE1=<...> --out <new dir>
        -> for each line: weights_<line>.json fitted on the other lines; summary.json (out-of-fold benefit per line)
    py selector.py final --rows H1=... HepG2=... RPE1=... --out <new dir>
        -> selector_final.json fitted on every given line (the frozen system of the confirmation lines)
    py selector.py apply --selector <selector_final.json> --rows Jurkat=<rows_Jurkat.csv.gz> --out <new dir>
        -> weights_<line>.json from the frozen selector
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ARMS = ("ibrido", "ibrido_mean")
SHARED = ("f_support", "f_concordance")
PER_ARM = ("f_log_ratio", "f_cos_rt")
LAST = ("f_expression",)
ALPHA = 0.01                    # PROTOCOLLO.md §12: with the objective divided by sum(a)


def features(df: pd.DataFrame, arm: str) -> np.ndarray:
    """The five inputs; a missing value is 0 (PROTOCOLLO.md §4: the control expression of a target gene the line's
    table does not measure is 0), so one missing input never turns the whole fit into NaN."""
    cols = [*SHARED, *(f"{arm}__{c}" for c in PER_ARM), *LAST]
    return np.nan_to_num(df[cols].to_numpy(np.float64), nan=0.0, posinf=0.0, neginf=0.0)


def usable(df: pd.DataFrame, arm: str) -> np.ndarray:
    return np.isfinite(df[f"{arm}__a"].to_numpy(float)) & np.isfinite(df[f"{arm}__b"].to_numpy(float))


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def fit(df: pd.DataFrame, arm: str) -> dict:
    ok = usable(df, arm)
    X = features(df, arm)[ok]
    a = df[f"{arm}__a"].to_numpy(float)[ok]
    b = df[f"{arm}__b"].to_numpy(float)[ok]
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd > 0, sd, 1.0)
    Z = (X - mu) / sd
    sa, sb = a.sum(), b.sum()
    w_fix = float(np.clip(sb / sa, 0.0, 1.0)) if sa > 0 else 0.0
    from scipy.optimize import minimize

    scale = sa if sa > 0 else 1.0           # PROTOCOLLO.md §12: a scale-free objective

    def obj(theta):
        w = sigmoid(theta[0] + Z @ theta[1:])
        loss = np.sum(a * w * w - 2 * b * w) / scale + ALPHA * float(theta[1:] @ theta[1:])
        dw = w * (1 - w) * (2 * a * w - 2 * b) / scale
        g = np.concatenate([[dw.sum()], Z.T @ dw + 2 * ALPHA * theta[1:]])
        return loss, g

    res = minimize(obj, np.zeros(Z.shape[1] + 1), jac=True, method="L-BFGS-B")
    theta = res.x
    w_sel = sigmoid(theta[0] + Z @ theta[1:])
    return {"arm": arm, "rows": int(ok.sum()), "w_fix": w_fix, "theta": theta.tolist(), "mu": mu.tolist(),
            "sd": sd.tolist(), "features": [*SHARED, *PER_ARM, *LAST], "alpha": ALPHA,
            "converged": bool(res.success), "objective": float(res.fun),
            "fit_benefit": {"selector": float(-np.mean(a * w_sel ** 2 - 2 * b * w_sel)),
                            "fixed": float(-np.mean(a * w_fix ** 2 - 2 * b * w_fix)),
                            "network_w1": float(-np.mean(a - 2 * b))}}


def apply(model: dict, df: pd.DataFrame) -> np.ndarray:
    X = features(df, model["arm"])
    Z = (X - np.asarray(model["mu"])) / np.asarray(model["sd"])
    th = np.asarray(model["theta"])
    w = sigmoid(th[0] + np.nan_to_num(Z) @ th[1:])
    return w


def benefit(df: pd.DataFrame, arm: str, w) -> dict:
    """Out-of-fold change of the weighted squared error (positive = better than T), overall and by weight band."""
    ok = usable(df, arm)
    a = df[f"{arm}__a"].to_numpy(float)
    b = df[f"{arm}__b"].to_numpy(float)
    w = np.broadcast_to(np.asarray(w, float), a.shape)
    gain = -(a * w * w - 2 * b * w)
    hi, lo = ok & (w > 0.5), ok & (w < 0.1)
    rel = gain / np.where(df["ibrido__base"].to_numpy(float) > 0, df["ibrido__base"].to_numpy(float), np.nan)
    return {"rows": int(ok.sum()), "mean_gain": float(np.nanmean(gain[ok])) if ok.any() else None,
            "mean_relative_gain": float(np.nanmean(rel[ok])) if ok.any() else None,
            "share_rows_improved": float(np.mean(gain[ok] > 0)) if ok.any() else None,
            "w_mean": float(np.mean(w[ok])) if ok.any() else None,
            "rows_w_above_0.5": int(hi.sum()), "gain_w_above_0.5": float(np.mean(gain[hi])) if hi.any() else None,
            "rows_w_below_0.1": int(lo.sum()), "gain_w_below_0.1": float(np.mean(gain[lo])) if lo.any() else None,
            "gain_if_w1": float(np.mean(-(a - 2 * b)[ok])) if ok.any() else None}


def read_rows(specs) -> dict:
    out = {}
    for s in specs:
        line, path = s.split("=", 1)
        out[line] = (pd.read_csv(path), Path(path))
    return out


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def weights_doc(df, models: dict, fit_on: list, line: str, src: dict, with_benefit: bool = True) -> dict:
    """The weights of one line. with_benefit=False (frozen system on a confirmation line) reads only the inputs of the
    rows, never a or b: the weights are written before any reading of that line's outcome."""
    doc = {"line": line, "fit_on": fit_on, "fixed": {}, "selective": {}, "models": models,
           "rows_sha256": src, "written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    for arm in ARMS:
        w = apply(models[arm], df)
        doc["fixed"][arm] = models[arm]["w_fix"]
        doc["selective"][arm] = {k: float(x) for k, x in zip(df["target_key"], w)}
        if with_benefit:
            doc.setdefault("oof_benefit", {})[arm] = {"selector": benefit(df, arm, w),
                                                      "fixed": benefit(df, arm, models[arm]["w_fix"]),
                                                      "network_w1": benefit(df, arm, 1.0)}
    return doc


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["lolo", "final", "apply"])
    p.add_argument("--rows", nargs="+", required=True, metavar="LINE=CSV")
    p.add_argument("--selector", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    rows = read_rows(a.rows)
    src = {line: sha(path) for line, (_, path) in rows.items()}
    a.out.mkdir(parents=True)
    if a.cmd == "lolo":
        summary = {"rule": "PROTOCOLLO.md §6: for each line, selector and w_fix fitted on the rows of the other lines",
                   "lines": {}}
        for line, (df, _) in rows.items():
            others = [x for x in rows if x != line]
            fit_df = pd.concat([rows[x][0] for x in others], ignore_index=True)
            models = {arm: fit(fit_df, arm) for arm in ARMS}
            doc = weights_doc(df, models, others, line, {x: src[x] for x in others})
            (a.out / f"weights_{line}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
            summary["lines"][line] = {"fit_on": others, "oof_benefit": doc["oof_benefit"],
                                      "w_fix": doc["fixed"], "weights_sha256": sha(a.out / f"weights_{line}.json")}
        (a.out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
        print(json.dumps({k: v["weights_sha256"][:12] for k, v in summary["lines"].items()}))
    elif a.cmd == "final":
        fit_df = pd.concat([df for df, _ in rows.values()], ignore_index=True)
        models = {arm: fit(fit_df, arm) for arm in ARMS}
        doc = {"rule": "PROTOCOLLO.md §6: the frozen system of the confirmation lines, fitted on every development line",
               "fit_on": sorted(rows), "rows_sha256": src, "models": models,
               "written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        (a.out / "selector_final.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
        print(json.dumps({"selector_final_sha256": sha(a.out / "selector_final.json")}))
    else:
        frozen = json.loads(a.selector.read_text(encoding="utf-8"))
        for line, (df, _) in rows.items():
            doc = weights_doc(df, frozen["models"], frozen["fit_on"], line, frozen["rows_sha256"], with_benefit=False)
            doc["selector_sha256"] = sha(a.selector)
            (a.out / f"weights_{line}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
            print(json.dumps({"line": line, "weights_sha256": sha(a.out / f"weights_{line}.json")}))


if __name__ == "__main__":
    main()
