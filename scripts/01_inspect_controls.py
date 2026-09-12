r"""Inspect the downloaded control bundle and report what the data actually looks like.

Answers the questions that shape every modelling decision downstream:
how deep are the cells, how sparse, how far apart are the three contexts, how
much of the perturbation panel is even expressed in each context, and how much
guide-to-guide noise sits in the controls.

Usage:  .\scripts\py.cmd scripts\01_inspect_controls.py
"""

from __future__ import annotations

import json

import anndata as ad
import numpy as np
import pandas as pd

from vcc2026.config import challenge, contexts, paths


def summarize(adata: ad.AnnData, targets: set[str]) -> dict:
    """Per-context statistics, computed without densifying anything."""
    X = adata.X.tocsr()
    umi = np.asarray(X.sum(axis=1)).ravel()
    detected = X.getnnz(axis=1)

    # Mean counts per gene, and the fraction of cells each gene is seen in.
    gene_mean = np.asarray(X.mean(axis=0)).ravel()
    gene_detect_rate = X.getnnz(axis=0) / X.shape[0]

    # Guide-to-guide spread among the 46 non-targeting controls. This is the
    # noise floor: variation with no perturbation behind it at all.
    ntc = adata.obs["ntc_id"].to_numpy()
    guide_means = []
    for g in pd.unique(ntc):
        rows = np.flatnonzero(ntc == g)
        guide_means.append(np.asarray(X[rows].mean(axis=0)).ravel())
    guide_means = np.vstack(guide_means)

    # Log space, because that is where fold changes and DE calls live.
    log_guide = np.log1p(guide_means)
    guide_sd = log_guide.std(axis=0, ddof=1)

    var_names = adata.var_names.to_numpy()
    expressed = gene_detect_rate >= 0.05
    target_mask = np.isin(var_names, list(targets))

    return {
        "n_cells": int(X.shape[0]),
        "n_genes": int(X.shape[1]),
        "nnz": int(X.nnz),
        "nnz_per_cell_mean": float(X.nnz / X.shape[0]),
        "sparsity": float(1 - X.nnz / (X.shape[0] * X.shape[1])),
        "umi_median": float(np.median(umi)),
        "umi_q05": float(np.quantile(umi, 0.05)),
        "umi_q95": float(np.quantile(umi, 0.95)),
        "genes_detected_median": float(np.median(detected)),
        "genes_expressed_5pct": int(expressed.sum()),
        "targets_in_var": int(target_mask.sum()),
        "targets_expressed_5pct": int((target_mask & expressed).sum()),
        "ntc_guide_logsd_median": float(np.median(guide_sd[expressed])),
        "_gene_mean": gene_mean,
        "_gene_detect_rate": gene_detect_rate,
    }


def main() -> None:
    p, c = paths(), challenge()
    bundle = p.raw / "controls"

    genes = pd.read_csv(bundle / "gene_names.csv")["gene_name"].to_numpy()
    perts = pd.read_csv(bundle / "pert_counts.csv")["target_gene"].to_numpy()
    targets = set(perts)

    print(f"gene list        : {len(genes):,} (expected {c.n_genes:,})")
    print(f"perturbations    : {len(perts):,} (expected {c.n_perturbations:,})")
    print(f"first genes      : {', '.join(genes[:5])}")
    print()

    stats, profiles = {}, {}
    for ctx in contexts("validation"):
        adata = ad.read_h5ad(bundle / f"context_{ctx}.h5ad")

        assert np.array_equal(adata.var_names.to_numpy(), genes), \
            f"context {ctx}: var order does not match gene_names.csv"

        s = summarize(adata, targets)
        profiles[ctx] = s.pop("_gene_mean")
        s.pop("_gene_detect_rate")
        stats[ctx] = s

        print(f"--- context {ctx} ---")
        print(f"  shape                 : {s['n_cells']:,} x {s['n_genes']:,}")
        print(f"  stored values         : {s['nnz']:,}  ({s['nnz_per_cell_mean']:,.0f}/cell, "
              f"{s['sparsity']:.1%} sparse)")
        print(f"  UMIs/cell             : median {s['umi_median']:,.0f}  "
              f"[p5 {s['umi_q05']:,.0f} - p95 {s['umi_q95']:,.0f}]")
        print(f"  genes detected/cell   : median {s['genes_detected_median']:,.0f}")
        print(f"  genes expressed (>=5% of cells) : {s['genes_expressed_5pct']:,}")
        print(f"  panel targets present in var    : {s['targets_in_var']}/{len(perts)}")
        print(f"  panel targets expressed         : {s['targets_expressed_5pct']}/{len(perts)}")
        print(f"  NTC guide-to-guide log SD (median over expressed genes): "
              f"{s['ntc_guide_logsd_median']:.4f}")
        print()

        del adata

    # How different are the three contexts from one another? This is the size of
    # the gap the model has to bridge zero-shot.
    print("--- cross-context similarity (Pearson r on log1p mean profiles) ---")
    ctxs = list(profiles)
    logp = {k: np.log1p(v) for k, v in profiles.items()}
    for i, a in enumerate(ctxs):
        for b in ctxs[i + 1:]:
            r = float(np.corrcoef(logp[a], logp[b])[0, 1])
            print(f"  {a} vs {b} : r = {r:.4f}")

    out = p.data_root.parent / "vcc2026-data" / "interim" / "control_stats.json"
    out.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
