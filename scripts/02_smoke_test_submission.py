r"""Round-trip the submission machinery on a handful of perturbations.

Builds a tiny context-mean prediction, reads it back with anndata, and checks
every format rule the challenge enforces. Cheap enough to run after any change
to sampling or writing, and it never touches the network.

Usage:  .\scripts\py.cmd scripts\02_smoke_test_submission.py
"""

from __future__ import annotations

import anndata as ad
import numpy as np
import pandas as pd

from vcc2026.config import challenge, paths
from vcc2026.sampling import resample_library_sizes, sample_counts
from vcc2026.submission import SubmissionWriter

N_PERTS = 3
CONTEXTS = ("A", "B", "C")   # prep rejects a file missing any context


def main() -> None:
    p, c = paths(), challenge()
    bundle = p.raw / "controls"
    rng = np.random.default_rng(0)

    genes = pd.read_csv(bundle / "gene_names.csv")["gene_name"].to_numpy()
    perts = pd.read_csv(bundle / "pert_counts.csv")["target_gene"].to_numpy()[:N_PERTS]

    out = p.predictions / "smoke.h5ad"
    out.parent.mkdir(parents=True, exist_ok=True)

    with SubmissionWriter(out, genes) as w:
        for ctx in CONTEXTS:
            adata = ad.read_h5ad(bundle / f"context_{ctx}.h5ad")
            X = adata.X.tocsr()
            profile = np.asarray(X.mean(axis=0)).ravel()
            observed_lib = np.asarray(X.sum(axis=1)).ravel().astype(np.int64)
            del adata, X

            for gene in perts:
                lib = resample_library_sizes(observed_lib, c.cells_per_pert, rng)
                block = sample_counts(
                    profile,
                    lib,
                    rng,
                    max_stored_per_cell=c.max_stored_per_cell,
                    max_counts_per_cell=c.max_counts_per_cell,
                )
                w.add(block, target_gene=gene, context=ctx)
            print(f"  context {ctx}: {len(perts)} perturbations written")

        n_obs, nnz = w.n_obs, w.nnz

    size_mb = out.stat().st_size / 1024**2
    print(f"\nwrote {out.name}: {n_obs:,} cells, {nnz:,} stored values, {size_mb:.1f} MB")

    # --- read back and check every rule prep enforces ---
    back = ad.read_h5ad(out)
    X = back.X.tocsr()

    expected = len(CONTEXTS) * N_PERTS * c.cells_per_pert
    checks = {
        "shape": (back.shape == (expected, c.n_genes), f"{back.shape}"),
        "gene order preserved": (
            np.array_equal(back.var_names.to_numpy(), genes.astype(str)), "",
        ),
        "obs columns": (
            {c.pert_col, c.context_col} <= set(back.obs.columns), f"{list(back.obs.columns)}",
        ),
        "counts are whole": (bool(np.all(X.data == np.floor(X.data))), ""),
        "counts non-negative": (bool(np.all(X.data >= 0)), ""),
        "counts finite": (bool(np.all(np.isfinite(X.data))), ""),
        "no stored zeros": (int((X.data == 0).sum()) == 0, ""),
        "no non-targeting rows": (
            c.ntc_label not in set(back.obs[c.pert_col].astype(str)), "",
        ),
        "cells per pert exact": (
            bool((back.obs.groupby([c.context_col, c.pert_col], observed=True)
                  .size() == c.cells_per_pert).all()), "",
        ),
        "under density cap": (
            X.nnz / X.shape[0] <= c.max_stored_per_cell,
            f"{X.nnz / X.shape[0]:,.0f}/cell vs cap {c.max_stored_per_cell:,}",
        ),
        "under count cap": (
            float(np.asarray(X.sum(axis=1)).max()) <= c.max_counts_per_cell, "",
        ),
    }

    print()
    failed = 0
    for name, (ok, detail) in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
        failed += not ok

    umi = np.asarray(X.sum(axis=1)).ravel()
    print(f"\n  sampled UMIs/cell   : median {np.median(umi):,.0f}")
    print(f"  sampled genes/cell  : median {np.median(X.getnnz(axis=1)):,.0f}")
    print(f"  (controls were      : median 20,109 UMIs, 6,147 genes)")

    if failed:
        raise SystemExit(f"\n{failed} check(s) failed")
    print("\nall checks passed")


if __name__ == "__main__":
    main()
