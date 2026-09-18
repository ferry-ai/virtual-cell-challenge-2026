"""Stage 79: the fast DE path against the scorer's own CPU DE, on real cells.

`vcc2026.de_tools.fast_scorer_de` replaces `cell_eval2.de_compute.compute_de`
(scanpy backend) in the benches because the scorer ranks every group together with
the whole control pool, which costs hours at 300 targets. A replacement is only
usable if it returns the same table. This stage checks that on real HepG2 cells:
same rows, same log2FC, same p-values, same significance calls, and reports the
largest differences and the two timings.

    python scripts/79_fast_de_parity.py --out reports/fast_de_2026-09-17
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
from vcc2026.de_tools import ReferencePool, de_frame, fast_scorer_de, scorer_config, scorer_de  # noqa: E402
from vcc2026.sc_stream import read_frame  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--n-targets", type=int, default=8)
    p.add_argument("--cells", type=int, default=80)
    p.add_argument("--control-cells", type=int, default=1500)
    p.add_argument("--seed", type=int, default=1)
    args = p.parse_args()
    if (args.out / "parity.json").exists():
        raise SystemExit(f"{args.out} already holds a report")
    args.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    path = config.paths().raw / "nadig_hepg2" / "NadigOConner2024_hepg2.h5ad"
    with h5py.File(path, "r") as f:
        obs = read_frame(f["obs"])
        names = read_frame(f["var"]).index.astype(str).to_numpy()
    sym = obs["gene"].astype(str).to_numpy()
    counts = pd.Series(sym[sym != "non-targeting"]).value_counts()
    targets = sorted(rng.choice(counts.index[counts >= args.cells].to_numpy(), args.n_targets, replace=False))
    ctrl_rows = np.sort(rng.choice(np.flatnonzero(sym == "non-targeting"), args.control_cells, replace=False))
    t_rows = np.sort(np.concatenate([rng.choice(np.flatnonzero(sym == t), args.cells, replace=False) for t in targets]))
    rows = np.sort(np.concatenate([ctrl_rows, t_rows]))
    with h5py.File(path, "r") as f:
        x = sp.vstack([sp.csr_matrix(f["X"][rows[i:i + 1000]]) for i in range(0, rows.size, 1000)]).tocsr()
    _, first = np.unique(names, return_index=True)
    keep = np.sort(first)
    x, genes = x[:, keep], names[keep]
    pos = {r: i for i, r in enumerate(rows)}
    ctrl = x[[pos[r] for r in ctrl_rows]]
    cells = x[[pos[r] for r in t_rows]]
    labels = sym[t_rows]

    t0 = time.time()
    slow = de_frame(scorer_de(cells, labels, ctrl, genes, backend="scanpy"))
    t1 = time.time()
    fast = de_frame(fast_scorer_de(cells, labels, ReferencePool(ctrl, genes)))
    t2 = time.time()
    m = slow.merge(fast, on=["target", "feature"], suffixes=("_s", "_f"))
    lp = np.abs(np.log10(m.p_value_s.clip(lower=1e-300)) - np.log10(m.p_value_f.clip(lower=1e-300)))
    sig_s, sig_f = m.p_adj_s < 0.05, m.p_adj_f < 0.05
    report = {
        "stage": "79_fast_de_parity",
        "written_utc": datetime.now(timezone.utc).isoformat(),
        "data": {"source": str(path), "targets": list(map(str, targets)), "cells_per_target": args.cells,
                 "control_cells": args.control_cells, "genes": int(genes.size)},
        "scorer": {"cell_eval2_config": "vcc2026", "backend": "scanpy",
                   "p_adj_threshold": scorer_config().de.p_adj_threshold},
        "rows": {"scanpy": int(len(slow)), "fast": int(len(fast)), "joined": int(len(m))},
        "max_abs_dlog10_p": float(lp.max()),
        "max_abs_dlfc": float(np.nanmax(np.abs(m.log2_fold_change_s - m.log2_fold_change_f))),
        "max_abs_dp_adj": float(np.abs(m.p_adj_s - m.p_adj_f).max()),
        "significant": {"scanpy": int(sig_s.sum()), "fast": int(sig_f.sum()), "disagree": int((sig_s != sig_f).sum())},
        "seconds": {"scanpy": t1 - t0, "fast": t2 - t1},
    }
    (args.out / "parity.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
