"""Specification of the missing single-cell bundle for generator × predictor.

The six VCC metrics need real perturbed counts and real controls. This module
does not download atlases and does not synthesise a reference. It writes the
fields, coverage, estimated size and acquisition path of the smallest candidate
that would unlock that experiment.
"""

from __future__ import annotations

from datetime import datetime, timezone

__all__ = ["missing_bundle_spec"]


def missing_bundle_spec(inventory: dict) -> dict:
    """Concrete missing-bundle record, derived from the inventory + registry notes."""
    local_perturbed_sc = [
        s for s in inventory.get("sources", [])
        if s.get("matrix_kind") == "single_cell_counts"
        and s.get("file", {}).get("exists")
        and s.get("id") != "vcc_controls"
    ]
    hepg2_on_disk = any(
        s.get("id") == "nadig_hepg2" and (s.get("file") or {}).get("exists")
        for s in inventory.get("sources", [])
    )
    candidates = []
    # Smallest complete perturbed single-cell objects with explicit NTCs.
    # HepG2 was acquired 2026-09-14; on_disk follows the inventory, not this comment.
    candidates.append({
        "id": "nadig_hepg2",
        "why_smallest": (
            "Roadmap R-1: 0.851 GB compressed, 145,473 × 9,624, 4,976 NTC. "
            "Smallest complete perturbed object with explicit NTCs."
        ),
        "accession": "GSE264667",
        "context": "HepG2",
        "n_cells_declared": 145473,
        "n_genes_declared": 9624,
        "n_ntc_declared": 4976,
        "bytes_declared": 5614460941,
        "bytes_compressed_estimate": 851_000_000,
        "panel_targets_observed": 0,
        "on_disk": hepg2_on_disk,
        "role_if_acquired": (
            "methodological evaluation bundle: generator × predictor on real "
            "perturbed cells. NOT a benchmark of the 300-target panel."
        ),
        "read_mode": "chunked; do not materialise the dense matrix (~5.6 GB)",
        "license_note": "public GEO; confirm before any submission use",
    })
    candidates.append({
        "id": "rpe1_singlecell",
        "why": (
            "Roadmap R-1 alternative: 1.237 GB compressed, 247,914 × 8,749, "
            "11,485 NTC. Same experiment as the local RPE1 pseudobulk."
        ),
        "accession": "figshare 20029387 / file 35775606",
        "context": "RPE1",
        "n_cells_declared": 247914,
        "n_genes_declared": 8749,
        "n_ntc_declared": 11485,
        "bytes_declared": 8700873216,
        "bytes_compressed_estimate": 1_237_000_000,
        "panel_targets_observed": 0,
        "on_disk": False,
        "role_if_acquired": (
            "pairs with local RPE1 pseudobulk: same biological context, "
            "real single-cell counts for the six VCC metrics."
        ),
        "read_mode": "chunked; dense is ~8.7 GB",
        "do_not_use": "file 35775554 is the NORMALIZED twin",
    })

    fields = {
        "matrix": {
            "X": "non-negative integer (or integer-valued) counts, CSR or dense float that is integral",
            "input_type": "counts",
            "gene_axis": (
                "source symbols aligned to the official 18,533 with an observed "
                "mask; unmeasured genes stay masked"
            ),
        },
        "obs": {
            "target_gene": "perturbed gene symbol or the NTC label",
            "context": "biological context, one value for the bundle",
            "guide_id": "if present, kept; same-target guides stay together",
            "donor": "if present, never pooled across donors",
            "batch": "if present, NTCs must be matchable per batch",
            "n_cells_min_per_target": (
                "enough to run DE; the competition asks 400 predicted cells, "
                "the bundle can be smaller if declared"
            ),
        },
        "controls": {
            "real_NTC_required": True,
            "control_source": "real",
            "do_not_replace_with_synthetic_cells": True,
            "matched_to": "same context, preferably same batch/donor",
        },
        "scoring": {
            "metrics": [
                "pds_cosine",
                "expr_mse_unbiased_capped_norm",
                "de_wilcoxon_lfc_nmae",
                "de_wilcoxon_direction_fidelity_yield_raw",
                "de_wilcoxon_direction_reach_raw",
                "de_wilcoxon_sig_jaccard",
            ],
            "backend_must_be_recorded": True,
            "anchors": (
                "without published b and r, report raw aggregates and a local "
                "normalisation explicitly distinct from the leaderboard"
            ),
        },
    }

    return {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "status": "missing",
        "execute_six_metrics": False,
        "n_local_perturbed_single_cell_sources": len(local_perturbed_sc),
        "local_perturbed_single_cell_ids": [s["id"] for s in local_perturbed_sc],
        "required_fields": fields,
        "candidates_not_acquired": candidates,
        "acquisition": {
            "do_not_download_atlases": True,
            "select_one_candidate": True,
            "byte_budget": (
                "the smaller of the two candidates is ~0.85 GB compressed; "
                "keep ≥10 GiB free (D-005)"
            ),
            "after_download": (
                "chunked subset of perturbed cells + paired NTCs, written as "
                "an evaluation bundle with a new --out, never overwriting "
                "existing reports"
            ),
        },
        "what_this_does_not_show": [
            "A better generator is not evidence that the predictor is adequate.",
            "A better generator is not evidence that modularity is useless.",
            "Zero panel overlap: this bundle would not score the 300 VCC targets.",
        ],
        "estimated_bundle_pilot": {
            "n_targets": 30,
            "cells_per_target": 80,
            "n_ntc": 400,
            "n_genes_if_rpe1": 8749,
            "dense_float32_bytes_estimate": 30 * 80 * 8749 * 4 + 400 * 8749 * 4,
            "note": (
                "30 × 80 + 400 NTC at 8,749 genes, float32 dense ≈ 98 MB. "
                "CSR of integer counts would be smaller. This is a planning "
                "figure, not a measurement."
            ),
        },
    }
