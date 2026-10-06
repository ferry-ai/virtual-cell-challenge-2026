"""t36 effects: the 'all' base plus w * R from Davide's export_abc (prediction_t36_2026-10-06/prediction.json).

Step 5 of export_abc.py, with the 'all' base in place of t25: lfc_base + w R on the (target, gene) pairs observed in the
base, elsewhere unchanged. Parity: w = 0 must return the base arrays exactly. Writes stage 100's format.

    python combina_R.py --base <effects_all dir> --corr <export_abc_r2 dir> --out <new dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

R_KEYS = ("R", "r", "correction", "delta")
W_COLS = ("w", "weight", "w_ibrido")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pick(names, options, what):
    hit = [o for o in options if o in names]
    if len(hit) != 1:
        raise SystemExit(f"{what}: expected exactly one of {options}, found {list(names)}")
    return hit[0]


def combine(base, R, w):
    """base: (targets, genes) lfc, observed; R aligned (targets, genes); w per target."""
    lfc, obs = base
    out = lfc.astype(np.float64) + np.where(obs, w[:, None] * np.nan_to_num(R.astype(np.float64)), 0.0)
    return out.astype(lfc.dtype)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--corr", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    a.out.mkdir(parents=True)
    man = {"base": str(a.base), "corr": str(a.corr), "contexts": {}}
    for C in "ABC":
        bp, cp, tp = a.base / f"effects_{C}.npz", a.corr / f"correction_{C}.npz", a.corr / f"targets_{C}.csv"
        b = np.load(bp)
        c = np.load(cp, allow_pickle=False)
        t = pd.read_csv(tp)
        btg, bgn = [str(x) for x in b["targets"]], [str(x) for x in b["genes"]]
        rk = pick(c.files, R_KEYS, f"{cp.name} correction array")
        ctg = [str(x) for x in c["targets"]] if "targets" in c.files else None
        cgn = [str(x) for x in c["genes"]] if "genes" in c.files else None
        if cgn is not None and cgn != bgn:
            raise SystemExit(f"{C}: gene axis of the correction differs from the base")
        if ctg is None:
            raise SystemExit(f"{C}: correction without a targets array")
        R = np.zeros(b["lfc"].shape, np.float64)
        ci = {x: i for i, x in enumerate(ctg)}
        for i, x in enumerate(btg):
            if x in ci:
                R[i] = c[rk][ci[x]].astype(np.float64)
        tcol = pick(t.columns, ("target", "target_gene", "symbol"), f"{tp.name} target column")
        wcol = pick(t.columns, W_COLS, f"{tp.name} weight column")
        wmap = dict(zip(t[tcol].astype(str), t[wcol].astype(float).fillna(0.0)))
        w = np.array([wmap.get(x, 0.0) for x in btg])
        if not ((w >= 0) & (w <= 1)).all():
            raise SystemExit(f"{C}: w outside [0, 1]")
        base = (b["lfc"], b["observed"])
        if not np.array_equal(combine(base, R, np.zeros_like(w)), b["lfc"]):
            raise SystemExit(f"{C}: parity with w = 0 failed")
        lfc = combine(base, R, w)
        op = a.out / f"effects_{C}.npz"
        np.savez(op, targets=b["targets"], genes=b["genes"], lfc=lfc, observed=b["observed"])
        dl = (lfc.astype(np.float64) - b["lfc"])[b["observed"]]
        man["contexts"][C] = {"base_sha256": sha(bp), "corr_sha256": sha(cp), "targets_csv_sha256": sha(tp),
                              "out_sha256": sha(op), "targets": len(btg), "targets_with_R": int(sum(x in ci for x in btg)),
                              "targets_w_gt_0": int((w > 0).sum()), "w_median_nonzero": float(np.median(w[w > 0])) if (w > 0).any() else 0.0,
                              "parity_w0": True, "mean_abs_change_observed": float(np.abs(dl).mean()),
                              "base_mean_abs_observed": float(np.abs(b["lfc"][b["observed"]]).mean()),
                              "r_key": rk, "w_col": wcol}
        print(C, json.dumps(man["contexts"][C]), flush=True)
    (a.out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
