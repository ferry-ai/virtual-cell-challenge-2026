"""Stage 83: how many genes a GENERATED prediction calls significant, on official contexts.

`de_wilcoxon_direction_fidelity_yield_raw = k / max(n_pred, n_conf)`. Which of the two
terms is the denominator decides what the metric measured on our submission means:

* `n_pred >= n_conf` -> the value IS our precision, and a low value means our signs are
  wrong;
* `n_pred <  n_conf` -> the value is `k / n_conf`, and a low value can simply mean we did
  not call enough.

`n_pred` needs no perturbed truth: it is the count of genes the scorer's own DE call finds
significant when OUR generated cells are tested against the context's control cells --
both of which we have. `k` and `n_conf` need the held-out perturbed data and are NOT
computed here; this stage says nothing about whether our calls are right.

Reads a packaged prediction (`prediction.h5ad` as written by stage 76) and, per context,
tests a sample of its perturbations against the context's real controls with
`fast_scorer_de` (identical to the scorer's scanpy path, D-037).

It also reports the ON-TARGET log2FC, which every scored member throws away: the cells
labelled with a target must carry that target's own knockdown (about log2(0.15) = -2.74).
A misalignment between labels and effects would leave the direction members at chance
while remaining invisible in the score, so the check belongs here and not in the score.

    python scripts/83_prediction_calls.py --prediction <gen/prediction.h5ad> \
        --out reports/prediction_calls_2026-09-17/p001 --n-targets 20 --ref-cells 9200
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.bench import log  # noqa: E402
from vcc2026.de_tools import ReferencePool, fast_scorer_de  # noqa: E402
from vcc2026.inference import read_csr_rows  # noqa: E402
from vcc2026.sc_stream import read_frame  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prediction", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--controls-dir", type=Path, default=None)
    p.add_argument("--contexts", nargs="+", default=["A", "B", "C"])
    p.add_argument("--n-targets", type=int, default=20)
    p.add_argument("--ref-cells", type=int, default=9200,
                   help="control cells used as the reference pool. The official pool is the whole context "
                        "(18,400): fewer cells have less power, so the count reported here is a LOWER BOUND "
                        "on the official n_pred")
    p.add_argument("--seed", type=int, default=2026)
    args = p.parse_args()
    if (args.out / "calls.json").exists():
        raise SystemExit(f"{args.out} already holds a report")
    args.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    cdir = args.controls_dir or config.paths().raw / "controls"

    with h5py.File(args.prediction, "r") as f:
        obs = read_frame(f["obs"])
        genes = read_frame(f["var"]).index.astype(str).to_numpy()
        shape = tuple(int(s) for s in f["X"].attrs["shape"])
    cols = {c.lower(): c for c in obs.columns}
    pert_col = cols.get("target_gene") or cols.get("gene") or list(obs.columns)[0]
    ctx_col = cols.get("context") or cols.get("cell_type")
    log(f"prediction {shape[0]} x {shape[1]}, columns {list(obs.columns)}")

    out = {}
    for ctx in args.contexts:
        rows_ctx = np.flatnonzero(obs[ctx_col].astype(str).to_numpy() == ctx)
        if rows_ctx.size == 0:
            log(f"{ctx}: no cells, skipped")
            continue
        labels_ctx = obs[pert_col].astype(str).to_numpy()[rows_ctx]
        targets = sorted(pd.unique(labels_ctx))
        pick = sorted(rng.choice(targets, size=min(args.n_targets, len(targets)), replace=False).tolist())
        keep = np.flatnonzero(np.isin(labels_ctx, pick))
        rows = rows_ctx[keep]
        t0 = time.time()
        cells = read_csr_rows(args.prediction, np.sort(rows), shape[1])
        labels = labels_ctx[keep][np.argsort(rows, kind="stable")]

        ctrl_path = cdir / f"context_{ctx}.h5ad"
        with h5py.File(ctrl_path, "r") as f:
            n_ctrl = int(f["X"].attrs["shape"][0])
        ref_rows = np.sort(rng.permutation(n_ctrl)[: min(args.ref_cells, n_ctrl)])
        pool = ReferencePool(read_csr_rows(ctrl_path, ref_rows, shape[1]), genes)
        de = fast_scorer_de(cells, labels, pool)
        frame = pd.DataFrame({c: de[c].to_numpy() for c in ("target", "feature", "log2_fold_change", "p_adj")})
        # Integrity check BEFORE dropping it: the cells labelled with a target must carry that
        # target's own knockdown. The scorer excludes the on-target gene from every direction
        # member, so a label/effect misalignment would be invisible in the score itself.
        on = frame[frame["feature"] == frame["target"]]
        on_lfc = on.set_index("target")["log2_fold_change"].reindex(pick)
        frame = frame[frame["feature"] != frame["target"]]          # the scorer excludes the on-target gene
        sig = frame[frame["p_adj"] < 0.05]
        per_t = sig.groupby("target").size().reindex(pick, fill_value=0)
        up = sig[sig["log2_fold_change"] > 0].groupby("target").size().reindex(pick, fill_value=0)
        out[ctx] = {
            "targets": list(map(str, pick)),
            "ref_cells": int(ref_rows.size), "control_cells_total": n_ctrl,
            "n_pred_mean": float(per_t.mean()), "n_pred_median": float(per_t.median()),
            "n_pred_q10_q90": [float(per_t.quantile(0.1)), float(per_t.quantile(0.9))],
            "n_pred_min_max": [int(per_t.min()), int(per_t.max())],
            "targets_below_10": int((per_t < 10).sum()),
            "frac_up_of_sig": float(up.sum() / max(per_t.sum(), 1)),
            "genes_tested_median": float(frame.groupby("target").size().median()),
            "on_target_log2fc": {str(t): (None if pd.isna(v) else float(v)) for t, v in on_lfc.items()},
            "on_target_log2fc_median": (None if on_lfc.dropna().empty else float(on_lfc.median())),
            "on_target_negative": int((on_lfc < 0).sum()), "on_target_present": int(on_lfc.notna().sum()),
            "seconds": time.time() - t0,
        }
        log(f"{ctx}: on-target log2FC median {out[ctx]['on_target_log2fc_median']}, "
            f"negative {out[ctx]['on_target_negative']}/{out[ctx]['on_target_present']} "
            f"(expected: all negative, about {np.log2(0.15):.2f})")
        log(f"{ctx}: n_pred median {per_t.median():.0f} mean {per_t.mean():.1f} "
            f"(min {per_t.min()}, max {per_t.max()}, <10: {(per_t < 10).sum()}/{len(pick)}), "
            f"up {out[ctx]['frac_up_of_sig']:.2f}, {time.time() - t0:.0f}s")
        del pool, cells

    payload = {
        "stage": "83_prediction_calls", "written_utc": datetime.now(timezone.utc).isoformat(),
        "prediction": str(args.prediction), "args": {k: str(v) for k, v in vars(args).items()},
        "contexts": out,
        "claim_type": ("measured: the number of genes the prediction itself calls significant against real "
                       "control cells (n_pred), a LOWER BOUND on the official one when --ref-cells is below "
                       "the full pool. Says NOTHING about k, n_conf or whether the calls are right"),
    }
    (args.out / "calls.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log("done")


if __name__ == "__main__":
    main()
