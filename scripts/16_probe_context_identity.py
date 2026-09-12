"""Identify what cell types the anonymized contexts A/B/C actually are.

The challenge hides the three cell lines. Their basal transcriptomes do not: a
marker panel plus a pipeline-robust contrast against the local Replogle lines
places each context on a lineage. Which lineage each context belongs to decides
which public perturbation atlas is worth downloading, so this runs before any
acquisition.

Read-only. Writes the per-context basal CPM profile to interim/ (derived data)
and small summaries to reports/context_identity/.

    scripts/py.cmd scripts/16_probe_context_identity.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import spearmanr

#: Lineage markers, chosen to be mutually exclusive between the lineages a
#: CRISPRi screen is plausibly run in. Absence is as informative as presence,
#: so panels stay here verbatim rather than being filtered to expressed genes.
MARKER_PANELS: dict[str, list[str]] = {
    "T_lymphoid": ["CD3D", "CD3E", "CD3G", "CD2", "CD7", "LCK", "ZAP70", "TRAC",
                   "TRBC1", "TRBC2", "CD1A", "CD1B", "RAG1", "RAG2", "DNTT",
                   "TAL1", "MYB", "GATA3", "PTPRC"],
    "erythroid_K562": ["HBG1", "HBG2", "HBZ", "GATA1", "GYPA", "KLF1", "ALAS2"],
    "epithelial": ["EPCAM", "KRT8", "KRT18", "KRT19", "CDH1", "CLDN4", "TACSTD2"],
    "squamous_basal": ["TP63", "KRT5", "KRT13", "KRT14", "KRT15", "KRT6A", "KRT4",
                       "SOX2", "DSP", "PKP1", "SFN", "CSTA"],
    "mesenchymal": ["VIM", "COL1A1", "FN1", "THY1", "S100A4", "ACTA2", "SERPINE1"],
    "eye_field_RPE": ["CLU", "PAX6", "LHX2", "MITF", "TFAP2A", "OTX2", "BEST1", "RAX"],
    "pluripotent": ["POU5F1", "NANOG", "LIN28A", "SOX2", "DNMT3B", "SALL4",
                    "TDGF1", "L1TD1", "ZFP42"],
    "hepatic": ["ALB", "AFP", "APOA1", "TTR", "HNF4A", "SERPINA1"],
    "myeloid": ["LYZ", "SPI1", "CSF1R", "ITGAM"],
    "sex_chrY": ["DDX3Y", "EIF1AY", "UTY", "KDM5D"],
    "proliferation": ["MKI67", "TOP2A", "CCNB1", "PCNA"],
}

REPLOGLE_REFS = {"K562": "K562_gwps_raw_bulk_01.h5ad", "RPE1": "rpe1_raw_bulk_01.h5ad"}


def basal_cpm(path: Path, n_vars_expected: int) -> tuple[np.ndarray, np.ndarray]:
    """Mean per-cell CPM and detection rate, streamed. CPM per cell, then averaged:
    the order matters and is the one the scorer's DE gate uses."""
    a = ad.read_h5ad(path, backed="r")
    try:
        if a.n_vars != n_vars_expected:
            raise ValueError(f"{path.name}: {a.n_vars} genes, expected {n_vars_expected}")
        total = np.zeros(a.n_vars, dtype=np.float64)
        detected = np.zeros(a.n_vars, dtype=np.int64)
        for start in range(0, a.n_obs, 2048):
            x = sparse.csr_matrix(a.X[start:start + 2048], dtype=np.float64)
            lib = np.asarray(x.sum(axis=1)).ravel()
            if (lib <= 0).any():
                raise ValueError(f"{path.name}: empty cell in rows {start}..")
            total += np.asarray(x.multiply((1e6 / lib)[:, None]).sum(axis=0)).ravel()
            detected += x.getnnz(axis=0)
        return total / a.n_obs, detected / a.n_obs
    finally:
        a.file.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("C:/Users/ferra/vcc2026-data"))
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).resolve().parents[1] / "reports/context_identity")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    bundle = args.data_root / "raw/controls"
    genes = pd.read_csv(bundle / "gene_names.csv")["gene_name"].astype(str).tolist()

    cpm, det = {}, {}
    for ctx in ("A", "B", "C"):
        cpm[ctx], det[ctx] = basal_cpm(bundle / f"context_{ctx}.h5ad", len(genes))
    profile = pd.DataFrame(cpm, index=pd.Index(genes, name="gene_name"))
    interim = args.data_root / "interim"
    interim.mkdir(parents=True, exist_ok=True)
    profile.to_csv(interim / "basal_cpm_by_context.csv")

    # --- markers ---------------------------------------------------------
    rows = []
    for panel, panel_genes in MARKER_PANELS.items():
        for g in panel_genes:
            if g not in profile.index:
                rows.append({"panel": panel, "gene": g, "on_gene_axis": False})
                continue
            i = profile.index.get_loc(g)
            rows.append({"panel": panel, "gene": g, "on_gene_axis": True,
                         **{f"{c}_cpm": float(cpm[c][i]) for c in "ABC"},
                         **{f"{c}_det": float(det[c][i]) for c in "ABC"}})
    markers = pd.DataFrame(rows)
    markers.to_csv(args.out / "markers.csv", index=False)

    # --- contrast test, robust to the processing-pipeline offset ----------
    # Absolute profiles from two different pipelines correlate mostly on the
    # pipeline. Contrasts taken INSIDE each source cancel that offset, so
    # corr(RPE1 - K562, context - mean(other two)) is a fair lineage question.
    refs = {}
    for label, name in REPLOGLE_REFS.items():
        v = ad.read_h5ad(args.data_root / "external" / name).var
        s = pd.Series(v["mean"].to_numpy(), index=v["gene_name"].astype(str))
        refs[label] = s[~s.index.duplicated()]
    shared = sorted(set(genes) & set(refs["K562"].index) & set(refs["RPE1"].index))
    d_ref = np.log1p(refs["RPE1"].loc[shared].to_numpy()) - np.log1p(refs["K562"].loc[shared].to_numpy())
    log_ctx = np.log1p(profile.loc[shared])
    contrast = {}
    for c in "ABC":
        other = log_ctx[[x for x in "ABC" if x != c]].mean(axis=1).to_numpy()
        e = log_ctx[c].to_numpy() - other
        contrast[c] = {"spearman_vs_RPE1_minus_K562": float(spearmanr(d_ref, e)[0]),
                       "pearson_vs_RPE1_minus_K562": float(np.corrcoef(d_ref, e)[0, 1])}

    # --- similarity on one shared gene space -----------------------------
    m = pd.DataFrame({c: profile.loc[shared, c] for c in "ABC"})
    for label in refs:
        m[label] = refs[label].loc[shared].to_numpy()
    sim = np.log1p(m).corr(method="spearman")

    summary = {
        "n_shared_genes_for_comparison": len(shared),
        "contrast_test": contrast,
        "contrast_reading": "positive = closer to RPE1 than to K562; negative = the reverse",
        "spearman_log1p_shared_space": json.loads(sim.to_json()),
        "caveats": [
            "Marker expression places a lineage; it does not name a cell line.",
            "Replogle var['mean'] comes from a different pipeline: only contrasts are comparable.",
            "Absence of a marker can be a capture artifact for low-abundance transcripts.",
        ],
    }
    (args.out / "context_identity.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\nbasal profile -> {interim / 'basal_cpm_by_context.csv'}")
    print(f"markers        -> {args.out / 'markers.csv'}")


if __name__ == "__main__":
    main()
