"""Is transferability a property of the target? Per-target PDS proxies of r1, compared across sources.

Reads ``r1/per_target_base.csv`` (the t15 recipe, A weights, each source held out in turn) and
writes the Spearman correlation of the per-target proxy between every pair of held-out sources,
with the share of targets above 0.9 and below 0.5. The same numbers were first printed from a
scratch copy of this code on 25 September; the review asked for them in an output.

    scripts/py.cmd reports/banco_varianti_2026-09-25/per_target_consistency.py --out reports/banco_varianti_2026-09-25/r9
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    d = pd.read_csv(HERE / "r1" / "per_target_base.csv")
    w = d.pivot(index="target", columns="held_out", values="pds_proxy_A")
    rho = w.corr(method="spearman")
    pairs = {f"{a} ~ {b}": float(rho.loc[a, b]) for i, a in enumerate(rho.index) for b in rho.columns[i + 1:]}
    out = {"stage": "banco_varianti_2026-09-25/per_target_consistency.py",
           "claim_type": "effect-space proxy per target, t15 recipe; not VCC scores",
           "targets_per_source": {k: int(v) for k, v in w.notna().sum().items()},
           "spearman_pairs": pairs,
           "spearman_range": [min(pairs.values()), max(pairs.values())],
           "share_above_0.9": {k: float(v) for k, v in (w > 0.9).mean().items()},
           "share_below_0.5": {k: float(v) for k, v in (w < 0.5).mean().items()}}
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
