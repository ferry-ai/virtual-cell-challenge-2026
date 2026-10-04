"""Pseudobulk rows for stage 98's --extra sources, from the per-target count sums of the cell corpus.

The sums kernel of R-LEAD P4 (reports/modelli/risposta_contesto_2026-10-02/kaggle_sums/, outputs <study>_sums.npz) wrote,
on the 18,533-gene official axis, the summed raw counts of every target's cells (`sums`, `n`) and of the NTC controls
(`ctrl`, `ctrl_n`), with the genes the study measures (`measured`). Stage 98 reads an extra source as an h5ad of summed
rows with obs target / donor / condition / n_cells and the axis symbols as var_names, and runs the live
`effects_from_pseudobulk` on it (PROTOCOLLO.md §4 of this folder: the candidate «più fonti» goes through the same
estimator as the recipe's sources). This writes one such h5ad per study: one row per target and one control row
('non-targeting'), donor = the study, condition 'none'. Genes the study does not measure keep 0 counts in every row and
are listed in uns['unmeasured'], so the estimator's floors treat them as absent, never as measured zeros.

    python sums_to_pseudobulk.py --sums <study>_sums.npz --study jurkat_nadig --out <new .h5ad>
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def convert(sums_path: Path, study: str, axis_symbols: list[str]):
    import anndata as ad
    import pandas as pd
    import scipy.sparse as sp
    z = np.load(sums_path, allow_pickle=False)
    S, n, ctrl = z["sums"], z["n"], z["ctrl"]
    if S.shape[1] != len(axis_symbols) or ctrl.shape[0] != len(axis_symbols):
        raise SystemExit(f"{sums_path}: {S.shape[1]} genes, the official axis has {len(axis_symbols)}")
    ctrl_n = int(z["ctrl_n"][0])
    measured = z["measured"].astype(bool)
    X = np.vstack([S, ctrl[None, :]])
    X[:, ~measured] = 0.0
    if np.any(X < 0) or not np.allclose(X, np.round(X)):
        raise SystemExit(f"{sums_path}: sums must be non-negative integer counts")
    obs = pd.DataFrame({"target": [str(t) for t in z["targets"]] + ["non-targeting"], "donor": study,
                        "condition": "none", "n_cells": np.concatenate([n, [ctrl_n]]).astype(np.int64)})
    obs.index = [f"{study}|{t}" for t in obs["target"]]
    a = ad.AnnData(X=sp.csr_matrix(X.astype(np.float32)), obs=obs, var=pd.DataFrame(index=list(axis_symbols)))
    a.uns["source"] = {"sums": str(sums_path), "sha256": sha256_file(sums_path), "study": study,
                       "targets": int(len(n)), "perturbed_cells": int(n.sum()), "controls": ctrl_n,
                       "genes_measured": int(measured.sum())}
    a.uns["unmeasured"] = [s for s, m in zip(axis_symbols, measured) if not m]
    return a


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sums", type=Path, required=True)
    p.add_argument("--study", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    from vcc2026.genes import official_axis
    axis = list(official_axis().symbols)
    out = convert(a.sums, a.study, axis)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    out.write_h5ad(a.out)
    print(json.dumps({"out": str(a.out), "sha256": sha256_file(a.out), **out.uns["source"]}))


if __name__ == "__main__":
    main()
