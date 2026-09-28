"""One half of a sums archive's pools, merged into a single pool, as a NEW archive (for split-half reliability).

The Flex-vs-3' cosines of bridge.py (r1) are low; to read them, the agreement of VIPerturb-seq with itself is needed:
the effects estimated from pools {0,1,2,3} against those from pools {4,5,6,7} of the same screen. This keeps the
groups (targets and NTC) of the chosen pools, sums them per target into pool 0, and writes an archive in the format
of kolf_sums (same keys; matrix in Fortran order through kolf_sums._publish), so kolf_effects.py estimates each
half exactly as the full screen was estimated. Genes absent from the file stay NaN; each gene's total over the kept
groups is checked unchanged.

    scripts/py.cmd reports/ponte_flex_2026-09-28/half_pools.py --sums IN.npz --keep-pools 0,1,2,3 --out OUT.npz
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
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "universo_kolf_2026-09-27"))

from kolf_effects import Sums  # noqa: E402
from kolf_sums import _publish  # noqa: E402

BLOCK = 512


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sums", type=Path, required=True)
    ap.add_argument("--keep-pools", required=True, help="comma-separated pool numbers")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    keep_pools = sorted({int(p) for p in args.keep_pools.split(",") if p.strip()})
    s = Sums(args.sums)
    if s.context is not None:
        raise SystemExit("an archive with contexts: not supported here")
    with np.load(args.sums, allow_pickle=False) as z:
        small = {k: z[k] for k in z.files if k != "sums"}
    kept = np.flatnonzero(np.isin(s.pool, keep_pools))
    uniq, inverse = np.unique(s.target[kept], return_inverse=True)
    A = sp.csr_matrix((np.ones(kept.size), (inverse, kept)), shape=(uniq.size, s.ng))
    n_cells = np.asarray(A @ s.n_cells.astype(np.float64)).astype(np.int64)
    total = np.asarray(A @ s.total.astype(np.float64))
    mm = np.memmap(args.sums, dtype="<f4", mode="r", offset=s.data_offset, shape=(s.ng, s.na), order="F")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".half-", dir=args.out.parent) as tmp:
        matrix = Path(tmp) / "sums.npy"
        new = np.lib.format.open_memmap(matrix, mode="w+", dtype="<f4", shape=(uniq.size, s.na), fortran_order=True)
        worst = 0.0
        for a in range(0, s.na, BLOCK):
            b = min(s.na, a + BLOCK)
            old = np.asarray(mm[:, a:b], dtype=np.float64)
            merged = A @ old
            new[:, a:b] = merged.astype(np.float32)
            with np.errstate(invalid="ignore"):
                before, after = np.nansum(old[kept], axis=0), np.nansum(merged, axis=0)
            worst = max(worst, float(np.max(np.abs(before - after) / np.maximum(before, 1.0))))
        new.flush()
        del new
        if worst > 1e-6:
            raise SystemExit(f"gene totals changed by {worst:.2e} (relative)")
        table = dict(small)
        table.update(target=uniq.astype(str), pool=np.zeros(uniq.size, dtype=np.int8), n_cells=n_cells,
                     total_counts=total,
                     groups_sha256=hashlib.sha256(json.dumps([uniq.tolist(), n_cells.tolist(), keep_pools]).encode()).hexdigest())
        _publish(args.out, table, matrix)
    print(f"pools {keep_pools}: {kept.size} of {s.ng} groups -> {uniq.size} targets (NTC included); "
          f"NTC cells {int(n_cells[uniq == 'NTC'].sum())}; gene totals unchanged (max relative {worst:.1e})", flush=True)


if __name__ == "__main__":
    main()
