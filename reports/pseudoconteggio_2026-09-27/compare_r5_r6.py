"""What a library-scaled pseudocount changes: stage-98 cache r5 (constant) against a new cache, source by source.

For each source: whether the arrays are identical (K562 goes through `effects_from_bulk` and must be),
the genes that read as induced (or repressed) by more than 90 % of the panel knockdowns, the six
Y-chromosome genes, and how much the per-target profiles moved. Writes ``confronto_r5_<tag>.json`` to --out.
r6 used a pseudocount at the geometric mean of the two totals, r7 the one the code keeps (in the smaller
group's units).

    scripts/py.cmd reports/pseudoconteggio_2026-09-27/compare_r5_r6.py --out reports/pseudoconteggio_2026-09-27 --new <data>/processed/multisource_2026-09-27_r7 --tag r7
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402

DATA = config.paths().data_root
Y = ["USP9Y", "UTY", "KDM5D", "ZFY", "DDX3Y", "EIF1AY"]
SOURCES = ["k562", "cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr", "cd4_halfA", "cd4_halfB", "cd4_mix",
           "orion_hct116", "orion_hek293t"]


def one_sided(raw: np.ndarray, min_targets: int = 100) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = np.isfinite(raw).sum(0)
    pos = np.where(n > 0, (raw > 0).sum(0) / np.maximum(n, 1), np.nan)
    ok = n >= min_targets
    return ok & (pos > 0.9), ok & (pos < 0.1), pos


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--r5", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--new", type=Path, default=DATA / "processed/multisource_2026-09-27_r6")
    ap.add_argument("--tag", default="r6")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    axis = np.asarray(official_axis().symbols)
    yi = [int(np.flatnonzero(axis == g)[0]) for g in Y]
    out = {"script": "reports/pseudoconteggio_2026-09-27/compare_r5_r6.py",
           "written_utc": datetime.now(timezone.utc).isoformat(), "r5": str(args.r5), args.tag: str(args.new),
           "claim_type": "measurement on the stage-98 panel caches (ln fold changes); not VCC scores", "sources": {}}
    for s in SOURCES:
        a, b = np.load(args.r5 / f"{s}.npz", allow_pickle=True), np.load(args.new / f"{s}.npz", allow_pickle=True)
        assert list(a["targets"]) == list(b["targets"]), s
        rec = {"targets": int(len(a["targets"]))}
        rec["identical"] = all(np.array_equal(a[k], b[k], equal_nan=True) for k in ("shrunk", "raw", "se", "n_cells"))
        for tag, z in (("r5", a), (args.tag, b)):
            raw = np.asarray(z["raw"], dtype=np.float64)
            up, down, _ = one_sided(raw)
            sh = np.asarray(z["shrunk"], dtype=np.float64)
            rec[tag] = {"genes_induced_by_over_90pct": int(up.sum()), "genes_repressed_by_over_90pct": int(down.sum()),
                        "first_induced": [str(g) for g in axis[up][:12]],
                        "y_mean_abs_shrunk": {g: (float(np.nanmean(np.abs(sh[:, i]))) if np.isfinite(sh[:, i]).any()
                                                  else None) for g, i in zip(Y, yi)},
                        "median_gene_mean_abs_shrunk": float(np.nanmedian(np.nanmean(np.abs(sh), axis=0)))}
        if not rec["identical"]:
            sa, sb = np.asarray(a["shrunk"], dtype=np.float64), np.asarray(b["shrunk"], dtype=np.float64)
            both = np.isfinite(sa) & np.isfinite(sb)
            corr = []
            for t in range(sa.shape[0]):
                m = both[t]
                if m.sum() > 50 and sa[t, m].std() > 0 and sb[t, m].std() > 0:
                    corr.append(float(np.corrcoef(sa[t, m], sb[t, m])[0, 1]))
            diff = np.abs(sa - sb)[both]
            rec["change"] = {"per_target_corr_shrunk_median": float(np.median(corr)),
                             "per_target_corr_shrunk_q10": float(np.quantile(corr, 0.1)),
                             "entries_changed_over_0.01": float((diff > 0.01).mean()),
                             f"energy_ratio_{args.tag}_over_r5": float(np.nansum(sb ** 2) / np.nansum(sa ** 2)),
                             "mask_mismatches": int((np.isfinite(sa) != np.isfinite(sb)).sum()),
                             "newly_unmeasured": int((np.isfinite(sa) & ~np.isfinite(sb)).sum()),
                             "entries_identical": float((sa[both] == sb[both]).mean())}
        out["sources"][s] = rec
        print(s, "identical" if rec["identical"] else rec.get("change"),
              "| induced >90%:", rec["r5"]["genes_induced_by_over_90pct"], "->", rec[args.tag]["genes_induced_by_over_90pct"],
              "| repressed >90%:", rec["r5"]["genes_repressed_by_over_90pct"], "->", rec[args.tag]["genes_repressed_by_over_90pct"])
    with (args.out / f"confronto_r5_{args.tag}.json").open("x", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
