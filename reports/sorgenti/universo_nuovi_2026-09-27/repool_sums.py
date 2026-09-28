"""Merge the pools of a sums archive: pool -> pool % K, summing counts, cells and libraries, into a NEW archive.

The estimator (`effects_from_pseudobulk` through `kolf_effects.py`) keeps a target's pool only with >= 10 cells.
Screens with few cells per target spread over 8 pools lose most targets (HIPSCI's genome-wide screen: 253 of 4,954
targets with effects at 8 pools, 27/09). Merging pools here avoids re-reading the source counts. Reads the matrix
through a memory map (the archive is checked by `kolf_effects.Sums`), a block of genes at a time: new = A @ old
with A the (new groups x old groups) 0/1 aggregation matrix; axis genes absent from the file stay NaN. Writes the
same keys (and `context` when present) with the matrix in Fortran order, published like `kolf_sums._publish`, and
checks that each gene's total over all groups is unchanged.

    scripts/py.cmd reports/sorgenti/universo_nuovi_2026-09-27/repool_sums.py --sums IN.npz --pools 1 --out OUT.npz
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "sorgenti" / "universo_kolf_2026-09-27"))

from kolf_effects import Sums  # noqa: E402
from kolf_sums import _publish  # noqa: E402

BLOCK = 512


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sums", type=Path, required=True)
    ap.add_argument("--pools", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    if args.pools < 1:
        raise SystemExit("--pools must be >= 1")
    s = Sums(args.sums)
    with np.load(args.sums, allow_pickle=False) as z:
        small = {k: z[k] for k in z.files if k != "sums"}
    context = s.context if s.context is not None else np.full(s.ng, "", dtype=object)
    new_pool = s.pool % args.pools
    keys = np.array([f"{c}|{t}|{p}" for c, t, p in zip(context, s.target, new_pool)], dtype=object)
    uniq, inverse = np.unique(keys, return_inverse=True)
    A = sp.csr_matrix((np.ones(s.ng, dtype=np.float64), (inverse, np.arange(s.ng))), shape=(uniq.size, s.ng))
    n_cells = np.asarray(A @ s.n_cells.astype(np.float64)).astype(np.int64)
    total = np.asarray(A @ s.total.astype(np.float64))
    parts = [k.split("|") for k in uniq]
    out_context = np.array([p[0] for p in parts], dtype=str)
    out_target = np.array([p[1] for p in parts], dtype=str)
    out_pool = np.array([int(p[2]) for p in parts], dtype=np.int8)
    mm = np.memmap(args.sums, dtype="<f4", mode="r", offset=s.data_offset, shape=(s.ng, s.na), order="F")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".repool-", dir=args.out.parent) as tmp:
        matrix = Path(tmp) / "sums.npy"
        new = np.lib.format.open_memmap(matrix, mode="w+", dtype="<f4", shape=(uniq.size, s.na), fortran_order=True)
        worst = 0.0
        for a in range(0, s.na, BLOCK):
            b = min(s.na, a + BLOCK)
            old = np.asarray(mm[:, a:b], dtype=np.float64)
            merged = A @ old                                   # NaN columns stay NaN
            new[:, a:b] = merged.astype(np.float32)
            with np.errstate(invalid="ignore"):
                before, after = np.nansum(old, axis=0), np.nansum(merged, axis=0)
            worst = max(worst, float(np.max(np.abs(before - after) / np.maximum(before, 1.0))))
        new.flush()
        del new
        if worst > 1e-6:
            raise SystemExit(f"gene totals changed by {worst:.2e} (relative)")
        table = dict(small)
        table.update(target=out_target, pool=out_pool, n_cells=n_cells, total_counts=total,
                     groups_sha256=hashlib.sha256(json.dumps([uniq.tolist(), n_cells.tolist()]).encode()).hexdigest())
        if s.context is not None:
            table["context"] = out_context
        _publish(args.out, table, matrix)
    print(f"{s.ng} groups -> {uniq.size} with pools % {args.pools}; gene totals unchanged (max relative {worst:.1e}); "
          f"targets with >= 10 cells in a group: {len(set(out_target[(n_cells >= 10) & (out_target != 'NTC')]))}",
          flush=True)


if __name__ == "__main__":
    main()
