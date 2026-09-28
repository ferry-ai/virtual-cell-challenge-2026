"""On-target check of an effect universe: the perturbed gene's own effect, target by target.

A knockdown (CRISPRi) must lower its own target's expression and an activation (CRISPRa) must raise it. If cells
were grouped under the wrong target, or controls mixed with perturbed cells, the own-gene effects would scatter
around zero. For every target of a universe folder (stage-98 chunks + ``index.csv``, read with the atlas's
``Universe``) whose symbol is on the axis, this reads ``raw`` and ``se`` at the target's own column and reports
their distribution: median, quartiles, the share below -0.5 and above +0.5 (natural-log fold change), and the
share with |z| >= 3 in each direction. Measured on the universe as written; no threshold decides anything.

    scripts/py.cmd reports/sorgenti/universo_nuovi_2026-09-27/on_target_check.py --universe NAME=DIR --out FILE.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "trasferimento" / "atlante_2026-09-26"))

from atlas_bench import Universe  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", required=True, metavar="NAME=DIR")
    ap.add_argument("--batch", type=int, default=500)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    name, _, folder = args.universe.partition("=")
    uni = Universe(name, Path(folder))
    axis = {g: i for i, g in enumerate(official_axis().symbols)}
    targets = sorted(t for t in uni.targets if t in axis)
    raw, z = [], []
    for start in range(0, len(targets), args.batch):
        part = targets[start:start + args.batch]
        tab = uni.table(part)
        ix = tab.index()
        for t in part:
            if t in ix:
                r = float(tab.raw[ix[t], axis[t]])
                s = float(tab.se[ix[t], axis[t]])
                raw.append(r)
                z.append(r / s if np.isfinite(s) and s > 0 else np.nan)
    raw, z = np.asarray(raw), np.asarray(z)
    ok = np.isfinite(raw)
    summary = {
        "universe": name, "folder": folder, "targets_on_axis": len(targets), "own_gene_measured": int(ok.sum()),
        "median": float(np.median(raw[ok])), "q25": float(np.quantile(raw[ok], 0.25)),
        "q75": float(np.quantile(raw[ok], 0.75)),
        "share_below_-0.5": float((raw[ok] < -0.5).mean()), "share_above_+0.5": float((raw[ok] > 0.5).mean()),
        "share_z_below_-3": float((z[ok] <= -3).mean()), "share_z_above_+3": float((z[ok] >= 3).mean()),
        "claim_type": "measured on the universe as written: the perturbed gene's own ln fold change",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
