"""Describe corrected CD4 cache states and their differences without fitting or selecting a model.

Small panel matrices only. Pair comparisons use the same finite gene support per pair,
exclude every official perturbation target as a response, and centre each source on its
own panel mean as gamma=1 in production. These are descriptive effect-space quantities,
not the six VCC metrics and not an estimate of A/B/C accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def stats(x) -> dict:
    a = np.asarray(x, float)
    a = a[np.isfinite(a)]
    return {"n": len(a), "median": float(np.median(a)) if len(a) else None,
            "q25": float(np.quantile(a, .25)) if len(a) else None,
            "q75": float(np.quantile(a, .75)) if len(a) else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("C:/Users/ferra/vcc2026-data"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[3]
    panel = pd.read_csv(args.data / "raw/controls/pert_counts.csv").target_gene.tolist()
    axis = pd.read_csv(args.data / "raw/controls/gene_names.csv").gene_name.tolist()
    pos = {g: i for i, g in enumerate(axis)}
    no_panel = ~np.isin(axis, panel)
    basal = pd.read_csv(args.data / "processed/basal_sources_2026-09-28.csv", index_col=0).reindex(axis)
    names = ["cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr", "cd4_mix", "cd4_halfA", "cd4_halfB", "k562"]
    tables, coverage = {}, []
    for name in names:
        with np.load(args.data / "processed/multisource_2026-09-27_r9" / f"{name}.npz", allow_pickle=False) as z:
            targets = z["targets"].astype(str)
            cells = z["n_cells"]
            shrunk = z["shrunk"]
            raw = z["raw"]
            diag = np.array([raw[i, pos[t]] if t in pos else np.nan for i, t in enumerate(targets)])
            counts = np.isfinite(shrunk).sum(axis=1)
            finite = np.isfinite(shrunk)
            centre = np.divide(np.where(finite, shrunk, 0).sum(axis=0, dtype=np.float64), finite.sum(axis=0),
                               out=np.zeros(shrunk.shape[1]), where=finite.sum(axis=0) > 0)
            shrunk -= centre.astype(np.float32)
            tables[name] = (dict(zip(targets, range(len(targets)))), shrunk)
            coverage.append({"source": name, "targets": len(targets), "missing": sorted(set(panel)-set(targets)),
                             "cells": stats(cells), "cells_lt50": int((cells < 50).sum()),
                             "measured_response_genes_per_target": stats(counts),
                             "own_gene_raw_lfc": stats(diag),
                             "reliability_n_over_nplus100": stats(cells / (cells + 100))})
            del raw
    pairs = [("cd4_Rest", "cd4_mix"), ("cd4_Rest", "cd4_Stim8hr"), ("cd4_Rest", "cd4_Stim48hr"),
             ("cd4_Stim8hr", "cd4_Stim48hr"), ("cd4_halfA", "cd4_halfB"),
             ("k562", "cd4_Rest"), ("k562", "cd4_Stim8hr"), ("k562", "cd4_Stim48hr"), ("k562", "cd4_mix")]
    records = []
    for a, b in pairs:
        ia, xa = tables[a]
        ib, xb = tables[b]
        for context in ["A", "B", "C"]:
            cpm = basal[context].to_numpy(float)
            # First-order conversion from natural log fold change to log1p(50k*CPM/1e6).
            x = .05 * cpm
            weight = x / (1 + x)
            for t in panel:
                if t not in ia or t not in ib:
                    continue
                va, vb = xa[ia[t]], xb[ib[t]]
                keep = np.isfinite(va) & np.isfinite(vb) & no_panel
                aa, bb = va[keep].astype(float) * weight[keep], vb[keep].astype(float) * weight[keep]
                ea, eb, dot = float(aa @ aa), float(bb @ bb), float(aa @ bb)
                records.append({"source_a": a, "source_b": b, "context_weight": context, "target": t,
                                "genes": int(keep.sum()), "cosine": dot / np.sqrt(ea*eb) if ea*eb else None,
                                "energy_a": ea, "energy_b": eb, "difference_energy": ea + eb - 2*dot,
                                "energy_ratio_a_over_b": ea / eb if eb else None})
    frame = pd.DataFrame(records)
    frame.to_csv(args.out / "per_target.csv", index=False)
    pair_summary = []
    for (a, b, context), block in frame.groupby(["source_a", "source_b", "context_weight"]):
        pair_summary.append({"source_a": a, "source_b": b, "context_weight": context,
                             "cosine": stats(block.cosine), "energy_ratio_a_over_b": stats(block.energy_ratio_a_over_b),
                             "fraction_difference_energy_over_b": float(block.difference_energy.sum()/block.energy_b.sum())})
    meta_file = repo / "reports/storico/candidate_verification/annotations/cd4_sample_metadata.csv"
    meta = pd.read_csv(meta_file)
    manifest = json.loads((meta_file.parent / "manifest.json").read_text(encoding="utf-8"))[meta_file.name]
    source = {"file": str(meta_file.relative_to(repo)), "rows": len(meta),
              "library_prep_kit_counts": meta.library_prep_kit.value_counts().to_dict(),
              "culture_condition_counts": meta.culture_condition.value_counts().to_dict(),
              "sha256": hashlib.sha256(meta_file.read_bytes()).hexdigest(), "manifest": manifest}
    common_genes = np.isfinite(basal[["A", "B", "C", "cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr"]]).all(axis=1)
    basal_corr = basal.loc[common_genes, ["A", "B", "C", "cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr"]].corr(method="spearman")
    basal_corr.to_csv(args.out / "basal_spearman_common_axis.csv")
    summary = {"claim_type": "descriptive exploratory audit, not VCC accuracy", "source_metadata": source,
               "coverage": coverage, "pairs": pair_summary,
               "caveats": ["CD4 halfA and halfB are independent donor subsets only for Stim48hr; they are not rest-state replicates",
                           "Different states share donors and guides; state correlations are not independent replication ceilings",
                           "Rest versus mix is self-including and cannot establish predictive accuracy",
                           "Basal expression similarity does not establish causal transfer quality"]}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"source_metadata": source, "coverage": coverage, "pairs": pair_summary}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
