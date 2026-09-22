"""Stage 101: three diagnostics of same-target transfer between stage-98 sources.

Written after stage 98's second run, to put on file three readings first made by hand
on 2026-09-22 (claim types: measurements in effect space, not VCC scores):

1. **Sign agreement** on the genes a source is confident about (|z| > 3 in K562): the
   share with the same sign in CD4 (conditions averaged, raw effects). The scorer's
   direction members reward exactly this, gene by gene.
2. **Amplitudes that minimise squared error** for predicting one source's RAW effects:
   from the other's raw effects, from its shrunk effects, and for the K562 + CD4 mixture
   under the "equidistant new context" model (cross-fitted: each shrunk predictor
   against the other source's raw truth). This is the scale question the t08 recipe
   met: `shared_signal` on shrunk effects gives a scale in shrunk units.
3. **Does mixing sources raise discrimination?** Treating the two CD4 donor halves
   (Stim48hr) as separate contexts: halfA alone, K562 alone, and both mixed, each
   predicting halfB (and the mirror image), by `transfer_report`'s discrimination proxy.

    python scripts/101_transfer_diagnostics.py --cache <stage-98 cache> --out <report dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import log  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.multisource import AxisTable, mix, transfer_report  # noqa: E402

DATA_ROOT = Path("C:/Users/ferra/vcc2026-data")


def load(cache: Path, name: str) -> AxisTable:
    z = np.load(cache / f"{name}.npz", allow_pickle=False)
    return AxisTable(name, z["targets"].astype(str).tolist(), z["shrunk"], z["raw"], z["se"], z["n_cells"],
                     json.loads(str(z["meta"])))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--targets-csv", type=Path, default=DATA_ROOT / "raw/controls/pert_counts.csv")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--z", type=float, default=3.0)
    args = p.parse_args()
    if (args.out / "diagnostics.json").exists():
        raise FileExistsError(args.out / "diagnostics.json")
    args.out.mkdir(parents=True, exist_ok=True)
    axis = np.asarray(official_axis().symbols)
    panel = pd.read_csv(args.targets_csv).iloc[:, 0].astype(str).tolist()
    pcols = np.isin(axis, panel)
    K = load(args.cache, "k562")
    conds = [load(args.cache, f"cd4_{c}") for c in ("Rest", "Stim8hr", "Stim48hr")]
    common = [t for t in panel if t in K.index() and all(t in c.index() for c in conds)]

    def rows(tab, key):
        idx = tab.index()
        return np.vstack([getattr(tab, key)[idx[t]] for t in common]).astype(np.float64)

    Ks, Kr, Kse = rows(K, "shrunk"), rows(K, "raw"), rows(K, "se")
    Cs = np.mean([rows(c, "shrunk") for c in conds], axis=0)
    Cr = np.mean([rows(c, "raw") for c in conds], axis=0)
    ok = np.isfinite(Ks) & np.isfinite(Cs) & np.isfinite(Kr) & np.isfinite(Cr)
    ok[:, pcols] = False

    def m(X, Y):
        return float((X * Y)[ok].mean())

    strong = ok & (np.abs(Kr / Kse) > args.z)
    sign = {"targets": len(common), "pairs_k562_confident": int(strong.sum()), "z": args.z,
            "same_sign_share_in_cd4": float(np.mean(np.sign(Kr[strong]) == np.sign(Cr[strong])))}
    amps = {"raw_to_raw": {"k562_to_cd4": m(Kr, Cr) / m(Kr, Kr), "cd4_to_k562": m(Cr, Kr) / m(Cr, Cr),
                           "corr": m(Kr, Cr) / np.sqrt(m(Kr, Kr) * m(Cr, Cr))},
            "shrunk_to_raw": {"k562_to_cd4": m(Ks, Cr) / m(Ks, Ks), "cd4_to_k562": m(Cs, Kr) / m(Cs, Cs)}}
    ca, cb, aa, bb, ab = m(Ks, Cr), m(Cs, Kr), m(Ks, Ks), m(Cs, Cs), m(Ks, Cs)
    grid = []
    for w in np.linspace(0, 1, 101):
        var_q = w * w * aa + (1 - w) ** 2 * bb + 2 * w * (1 - w) * ab
        cov = w * ca + (1 - w) * cb
        grid.append((cov * cov / var_q, float(w), float(cov / var_q)))
    _, w_best, amp_best = max(grid)
    amps["cross_fit_mixture"] = {"weight_k562": w_best, "amplitude": amp_best,
                                 "model": "new context equally unrelated to both sources; shrunk predictors, raw truth"}
    log(f"sign agreement {sign['same_sign_share_in_cd4']:.4f} on {sign['pairs_k562_confident']} pairs; "
        f"raw a* {amps['raw_to_raw']['k562_to_cd4']:.3f}/{amps['raw_to_raw']['cd4_to_k562']:.3f}; "
        f"cross-fit w {w_best:.2f} amp {amp_best:.3f}")

    A, B = load(args.cache, "cd4_halfA"), load(args.cache, "cd4_halfB")
    both = [t for t in panel if t in K.index() and t in A.index() and t in B.index()]
    pcol_idx = np.flatnonzero(pcols)
    mixing = {}
    for label, tabs, truth in [("k562->halfB", [K], B), ("halfA->halfB", [A], B), ("k562+halfA->halfB", [K, A], B),
                               ("k562->halfA", [K], A), ("halfB->halfA", [B], A), ("k562+halfB->halfA", [K, B], A),
                               ("halfA->k562", [A], K), ("halfA+halfB->k562", [A, B], K)]:
        pred, w = mix(tabs, both, gamma=1.0)
        r = transfer_report(pred, w, truth, both, exclude_cols=pcol_idx)
        mixing[label] = {"pds_proxy_mean": r["pds_proxy_mean"], "purity_top10": r["median"]["purity_top10"],
                         "purity_top50": r["median"]["purity_top50"], "reach_proxy": r["median"]["reach_proxy"]}
        log(f"  {label:>20}: pds~{r['pds_proxy_mean']:.3f}")
    payload = {"stage": "101_transfer_diagnostics", "written_utc": datetime.now(timezone.utc).isoformat(),
               "cache": str(args.cache), "claim_type": "measurements in effect space; not VCC scores",
               "sign_agreement": sign, "amplitudes": amps,
               "mixing_and_discrimination": {"targets": len(both), "gamma": 1.0, "arms": mixing}}
    with open(args.out / "diagnostics.json", "x", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    log(f"wrote {args.out / 'diagnostics.json'}")


if __name__ == "__main__":
    main()
