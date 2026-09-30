"""The shard contract of R-LAB §4, as code: what every cell-level shard must carry, and a validator.

A shard is one sparse AnnData .h5ad per study x library x block of cells, never a concatenation of
the corpus. It keeps the raw counts of each cell on the assay's native feature axis, the identity
of the cell, its metadata with explicit masks, the depth before any gene filter, and the
provenance of the bytes it came from. Derived views (normalisations, ranks, programmes, pseudobulk)
live in other files and never replace the raw.

    from contracts import validate_shard
    problems = validate_shard("shard.h5ad")      # [] when the shard honours the contract

Used by the shard writer, by validate_shards.py and by the remote jobs, so a shard written on Colab
is judged by the same rules as one written here.
"""
from __future__ import annotations

from pathlib import Path

# obs: one row per cell. Missing values are allowed only where the source has none, and then the
# column holds the explicit value MISSING, never an invented donor, replicate or guide.
OBS_REQUIRED = {
    "cell_key": "study|sample_or_library|original_barcode; unique in the corpus",
    "study": "source id of sources.yaml",
    "library": "sample, lane, channel or pool as published",
    "barcode": "original barcode, untouched",
    "target": "gene symbol of the intended perturbation; NTC, UNASSIGNED or DRUG:<name> otherwise",
    "guides": "the guide set called in the cell, as published (its separator noted in uns); MISSING if none",
    "guide_confidence": "assignment confidence as published, or MISSING",
    "modality": "CRISPRi | CRISPRa | KO | drug | basal",
    "control_kind": "NTC | UNASSIGNED | DMSO | vehicle | none",
    "context": "cell line or cell type as published",
    "donor_or_clone": "as published, or MISSING",
    "batch": "plate, GEM well or batch as published, or MISSING",
    "chemistry": "10x 3' v3 | 10x Flex | ... as published",
    "condition": "stimulus, time and dose as published, or none",
    "depth_native": "total counts of the cell on the native feature axis, before any gene filter",
    "depth_published": "total counts as the file publishes them (may equal depth_native)",
    "depth_on_file_axis": "row sum of X, the counts on the features this shard keeps",
    "n_genes_detected": "genes with at least one count on the native axis",
}
# var: one row per native feature, with its mapping to the official axis. A gene the assay does not
# measure is not a zero: `measured` says which features exist in this assay.
VAR_REQUIRED = {
    "feature_id": "Ensembl id (with version when published) or probe id",
    "symbol": "symbol as published",
    "feature_type": "Gene Expression | probe | ...",
    "measured": "True for every feature the assay measures",
    "official_index": "position on the 18,533-gene official axis, -1 if absent",
    "mapping": "unique | ambiguous | none; an ambiguous mapping is never summed silently",
}
# uns: provenance and parity. A shard without them is refused.
UNS_REQUIRED = {
    "source": "id, release, locator (URL or path) and checksum of the bytes read",
    "read": "how the bytes were read: whole file, byte ranges, streaming; with ETag or hash of blocks",
    "rows": "which cells of the source this shard holds (range or cell-key hash)",
    "parity": "sum of counts, cells, guides and targets before and after writing",
    "contract_version": "1",
    "qc_version": "the QC policy applied, or 'none' for a raw shard",
    "writer": "script, commit and runtime manifest of the writer",
}
CONTRACT_VERSION = "1"


def validate_shard(path: str | Path) -> list[str]:
    """Problems of one shard; an empty list means it honours the contract."""
    import anndata as ad
    import numpy as np
    import scipy.sparse as sp

    problems: list[str] = []
    a = ad.read_h5ad(path, backed="r")
    try:
        missing_obs = sorted(set(OBS_REQUIRED) - set(a.obs.columns))
        missing_var = sorted(set(VAR_REQUIRED) - set(a.var.columns))
        missing_uns = sorted(set(UNS_REQUIRED) - set(a.uns.keys()))
        for kind, names in (("obs", missing_obs), ("var", missing_var), ("uns", missing_uns)):
            if names:
                problems.append(f"{kind} lacks {names}")
        if str(a.uns.get("contract_version", "")) != CONTRACT_VERSION:
            problems.append("contract_version is not 1")
        if "cell_key" in a.obs and not a.obs["cell_key"].is_unique:
            problems.append("cell_key is not unique within the shard")
        x = a.X[:]  # a shard is one block of cells: it fits in memory by construction
        if not sp.issparse(x) or x.format != "csr":
            problems.append("X is not CSR")
        else:
            data = x.data
            if data.size and (np.any(data < 0) or not np.all(np.isfinite(data))):
                problems.append("X has negative or non-finite values")
            if data.size and not np.all(np.equal(np.mod(data, 1), 0)):
                problems.append("X is not integer counts: corrected counts go in a layer, not in X")
            if "depth_on_file_axis" in a.obs and "depth_native" in a.obs:
                depth = np.asarray(x.sum(axis=1)).ravel()
                if not np.allclose(depth, a.obs["depth_on_file_axis"].to_numpy(dtype=float)):
                    problems.append("depth_on_file_axis differs from the row sums of X")
                if np.any(a.obs["depth_native"].to_numpy(dtype=float) < depth - 0.5):
                    problems.append("depth_native is below the counts kept in X")
        parity = a.uns.get("parity", {})
        if isinstance(parity, dict) and "sum_after" in parity and "sum_before" in parity:
            if float(parity["sum_after"]) != float(parity["sum_before"]):
                problems.append("parity: sum of counts changed while writing")
    finally:
        if a.isbacked:
            a.file.close()
    return problems


if __name__ == "__main__":
    import sys
    bad = {p: validate_shard(p) for p in sys.argv[1:]}
    for p, probs in bad.items():
        print(p, "ok" if not probs else "; ".join(probs))
    sys.exit(1 if any(bad.values()) else 0)
