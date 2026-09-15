"""Source cards for Replogle SC, H1, CD4, Srivatsan, McFaline, Tahoe, scBaseCount.

Fills the mandatory sheet from evidence that already exists in this repository
plus public record URLs. Does not download atlases. A drug dataset is not a
CRISPRi label. Observational atlases are not knockdown supervision.

    scripts/py.cmd scripts/64_source_cards.py --out reports/source_cards_2026-09-15
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.manifest import RunManifest
from vcc2026.source_card import Field, SourceCard, validate_card

REPO = Path(__file__).resolve().parents[1]
COV = REPO / "reports/candidate_verification/coverage_summary.json"
SOURCES = REPO / "configs/sources.yaml"


def _cov() -> dict:
    return json.loads(COV.read_text(encoding="utf-8"))


def card_replogle_sc() -> SourceCard:
    return SourceCard(
        source_id="replogle_k562_gwps_singlecell",
        title="Replogle 2022 K562 genome-wide Perturb-seq, single-cell",
        study_id=Field("figshare 20029387", "cited", "configs/sources.yaml"),
        version=Field("processed record DOI 10.25452/figshare.plus.20029387",
                      "cited", "configs/sources.yaml"),
        primary_url=Field("https://figshare.com/articles/dataset/20029387",
                          "cited", "configs/sources.yaml"),
        license=Field("CC BY 4.0", "cited", "configs/sources.yaml"),
        perturbation_class=Field("CRISPRi", "cited", "configs/sources.yaml"),
        cell_context=Field("K562", "cited", "configs/sources.yaml"),
        donor_state_batch=Field("gem_group / batch in the raw single-cell object",
                                "cited", "docs/PIANO_OPERATIVO_2026-09-15.md"),
        n_targets=Field(None, "missing",
                        note="genome-wide design; local pseudobulk already covers 272/300"),
        id_mapping=Field("obs.gene / gene_transcript on the GEO-style objects",
                         "cited", "configs/sources.yaml"),
        count_kind=Field("raw single-cell counts (not the local per-cell-mean pseudobulk)",
                         "cited", "configs/sources.yaml"),
        ntc_field=Field("obs.gene == 'non-targeting' on related Nadig/Replogle objects",
                        "cited", "reports/candidate_verification/"),
        guides=Field(None, "missing"),
        cells_per_target=Field(None, "missing"),
        n_genes_measured=Field(None, "missing"),
        remote_bytes=Field(
            {"ReplogleWeissman2022_K562_gwps.h5ad": 8_805_466_154,
             "profile_declared_sc": [61.3e9, 9.9e9, 8.1e9]},
            "cited",
            "https://zenodo.org/records/13350497",
            note="61.3/9.9/8.1 GB are profile declarations, not bytes measured this session",
        ),
        temporary_bytes=Field(None, "missing"),
        checksum=Field("md5:13db594f8f1d2ccb88fec44a13e414dc on the scPerturb K562 gwps mirror",
                       "cited", "https://zenodo.org/records/13350497"),
        panel_overlap=Field(
            {"observed_targets": 272, "list_source": "local k562_gwps pseudobulk, not this file"},
            "derived",
            "reports/candidate_verification/coverage_summary.json",
            note="coverage is of the local PSEUDOBULK, not a proof the single-cell file was opened",
        ),
        training_overlap=Field(
            {"same_experiment_as": "k562_gwps pseudobulk already local"},
            "derived",
            "configs/sources.yaml",
        ),
        decision="defer",
        decision_note=(
            "Adds real cells for validation/generator work on a line we already "
            "train from as pseudobulk. Not a new biological context. Download "
            "only a bounded extract after remote preflight; do not replace the "
            "local baseline until an ablation says so."
        ),
    )


def card_h1() -> SourceCard:
    return SourceCard(
        source_id="vcc2025_h1",
        title="VCC 2025 H1 complete (local metadata only)",
        study_id=Field("VCC2025 H1", "cited", "configs/sources.yaml"),
        version=Field(None, "missing"),
        primary_url=Field("virtualcellchallenge.org / Arc atlas", "cited",
                          "docs/PIANO_OPERATIVO_2026-09-15.md"),
        license=Field(None, "missing"),
        perturbation_class=Field("CRISPRi", "cited", "docs/PROGETTO.md"),
        cell_context=Field("H1 hESC", "cited", "docs/PROGETTO.md"),
        donor_state_batch=Field(None, "missing"),
        n_targets=Field(None, "missing"),
        id_mapping=Field(None, "missing"),
        count_kind=Field(None, "missing",
                         note="local copy has four metadata CSV and no RNA matrix"),
        ntc_field=Field(None, "missing"),
        guides=Field(None, "missing"),
        cells_per_target=Field(None, "missing"),
        n_genes_measured=Field(None, "missing"),
        remote_bytes=Field(None, "missing"),
        temporary_bytes=Field(None, "missing"),
        checksum=Field(None, "missing"),
        panel_overlap=Field(
            {"shared_targets_cited": 25,
             "list_source": "docs/PROGETTO.md local vcc2025 metadata"},
            "cited",
            "docs/PROGETTO.md",
        ),
        training_overlap=Field(
            {"local_rna": False},
            "measured",
            "C:/Users/ferra/vcc2026-data/external/vcc2025/",
        ),
        decision="defer",
        decision_note=(
            "Need a file manifest and the RNA matrix. Pluripotent lineage matches "
            "none of A/B/C. Useful as an extra perturbed context once RNA exists."
        ),
    )


def card_cd4() -> SourceCard:
    cov = _cov().get("cd4_D1_Rest") or {}
    return SourceCard(
        source_id="cd4_marson",
        title="Zhu/Dann/Marson primary CD4 Perturb-seq",
        study_id=Field("GSE314342", "cited", "configs/sources.yaml"),
        version=Field("GEO public since 2026-02-06", "cited", "configs/sources.yaml"),
        primary_url=Field(
            "https://genome-scale-tcell-perturb-seq.s3.amazonaws.com/marson2025_data/",
            "cited", "configs/sources.yaml",
        ),
        license=Field(None, "missing"),
        perturbation_class=Field("CRISPRi", "cited", "configs/sources.yaml"),
        cell_context=Field("primary human CD4 T cells, multiple donors",
                           "cited", "configs/sources.yaml"),
        donor_state_batch=Field("Rest vs Stimulated kept separate; donor in object names",
                                "cited", "configs/sources.yaml"),
        n_targets=Field(None, "missing", note="library design is not n_targets usable"),
        id_mapping=Field("guide_id joined to sgRNA_library_curated.csv",
                         "measured", "reports/candidate_verification/pilot/"),
        count_kind=Field("float32 CSR, non-negative integers in the 64-cell pilot",
                         "measured",
                         "reports/candidate_verification/pilot/cd4_D1_Rest_64.manifest.json"),
        ntc_field=Field("guide_type == 'non-targeting' AND low_quality == False",
                        "measured", "configs/sources.yaml"),
        guides=Field("sgrna_id in the curated library", "cited", "configs/sources.yaml"),
        cells_per_target=Field(
            {"targets_min_30": cov.get("targets_with_at_least_30_cells"),
             "targets_min_100": cov.get("targets_with_at_least_100_cells")},
            "measured",
            str(COV),
        ),
        n_genes_measured=Field(cov.get("output_gene_overlap"), "measured", str(COV)),
        remote_bytes=Field(1_735_835_115_866, "cited", "configs/sources.yaml"),
        temporary_bytes=Field(None, "missing"),
        checksum=Field(None, "missing"),
        panel_overlap=Field(
            {
                "library_targets": 297,
                "observed_targets": cov.get("observed_targets"),
                "targets_min_30": cov.get("targets_with_at_least_30_cells"),
                "list_source": str(COV),
            },
            "measured",
            str(COV),
        ),
        training_overlap=Field(
            {"pilot_cells": 64, "full_objects_not_local": True},
            "measured",
            "reports/candidate_verification/pilot/cd4_D1_Rest_64.manifest.json",
        ),
        decision="defer",
        decision_note=(
            "Highest panel coverage among candidates, nearest lineage to context A, "
            "but 1.7 TB single-cell. Reopen after Jiang/Jurkat audits. Do not double-"
            "count GEO, Zenodo and the S3 mirror as three sources."
        ),
    )


def card_srivatsan() -> SourceCard:
    return SourceCard(
        source_id="srivatsan_sciplex3",
        title="Srivatsan 2020 sci-Plex 3 (188 compounds)",
        study_id=Field("SrivatsanTrapnell2020_sciplex3", "cited",
                       "https://zenodo.org/records/13350497"),
        version=Field("scPerturb 1.4", "cited", "https://zenodo.org/records/13350497"),
        primary_url=Field(
            "https://zenodo.org/api/records/13350497/files/SrivatsanTrapnell2020_sciplex3.h5ad/content",
            "cited", "https://zenodo.org/records/13350497",
        ),
        license=Field("cc-by-4.0", "cited", "https://zenodo.org/records/13350497"),
        perturbation_class=Field("drug", "cited", "docs/PIANO_OPERATIVO_2026-09-15.md"),
        cell_context=Field(["K562", "A549", "MCF7"], "cited",
                           "arxiv:2604.13986 (PRiMeFlow dataset description)"),
        donor_state_batch=Field("dose present; PRiMeFlow kept highest dose only",
                                "cited", "arxiv:2604.13986"),
        n_targets=Field(188, "cited", "docs/PIANO_OPERATIVO_2026-09-15.md",
                        note="compounds, not genes"),
        id_mapping=Field(None, "missing"),
        count_kind=Field(None, "missing", note="h5ad not opened this session"),
        ntc_field=Field(None, "missing", note="vehicle controls must be verified before use"),
        guides=Field(None, "missing", note="no CRISPR guides"),
        cells_per_target=Field(None, "missing"),
        n_genes_measured=Field(None, "missing"),
        remote_bytes=Field(2_526_631_614, "cited", "https://zenodo.org/records/13350497"),
        temporary_bytes=Field(None, "missing"),
        checksum=Field("md5:c9e70629505d98c7ca1a837f62b14e89", "cited",
                       "https://zenodo.org/records/13350497"),
        panel_overlap=Field(
            None, "missing",
            note="drug names are not gene targets; overlap with the 300 is not defined this way",
        ),
        training_overlap=Field(
            {"pretraining_only": True, "not_knockdown_labels": True},
            "derived",
            "docs/PIANO_OPERATIVO_2026-09-15.md",
        ),
        decision="exclude",
        decision_note=(
            "Pharmacological. Useful at most as pretraining or a context descriptor. "
            "No knockdown labels. Not in the first acquisition wave."
        ),
    )


def card_mcfaline() -> SourceCard:
    return SourceCard(
        source_id="mcfaline_sciplex_gxe",
        title="McFaline-Figueroa 2024 sci-Plex-GxE",
        study_id=Field("McFaline-Figueroa sci-Plex-GxE", "cited",
                       "https://cole-trapnell-lab.github.io/papers/mcfaline-sci-plex-gxe/"),
        version=Field(None, "missing"),
        primary_url=Field(
            "https://cole-trapnell-lab.github.io/papers/mcfaline-sci-plex-gxe/",
            "cited",
            "docs/PIANO_OPERATIVO_2026-09-15.md",
        ),
        license=Field(None, "missing"),
        perturbation_class=Field("combo_genetic_chemical", "cited",
                                 "docs/PIANO_OPERATIVO_2026-09-15.md"),
        cell_context=Field(None, "missing"),
        donor_state_batch=Field(None, "missing",
                                note="dose/time/vehicle must be verified before merging"),
        n_targets=Field(None, "missing"),
        id_mapping=Field(None, "missing"),
        count_kind=Field(None, "missing"),
        ntc_field=Field(None, "missing", note="vehicle is not an NTC guide"),
        guides=Field(None, "missing"),
        cells_per_target=Field(None, "missing"),
        n_genes_measured=Field(None, "missing"),
        remote_bytes=Field(None, "missing"),
        temporary_bytes=Field(None, "missing"),
        checksum=Field(None, "missing"),
        panel_overlap=Field(None, "missing"),
        training_overlap=Field(
            {"combined_effect_is_not_simple_crispri": True},
            "derived",
            "docs/PIANO_OPERATIVO_2026-09-15.md",
        ),
        decision="defer",
        decision_note=(
            "Genetic plus chemical. Do not treat the combined arm as CRISPRi. "
            "After Jiang/Jurkat: verify mechanism, vehicle controls, separable arms."
        ),
    )


def card_tahoe() -> SourceCard:
    return SourceCard(
        source_id="tahoe_100m",
        title="Tahoe-100M (Virtual Cell Atlas)",
        study_id=Field("Tahoe-100M", "cited",
                       "https://arcinstitute.org/tools/virtualcellatlas"),
        version=Field(None, "missing"),
        primary_url=Field("https://github.com/ArcInstitute/arc-virtual-cell-atlas/",
                          "cited", "docs/PIANO_OPERATIVO_2026-09-15.md"),
        license=Field(None, "missing"),
        perturbation_class=Field("drug", "cited", "docs/PIANO_OPERATIVO_2026-09-15.md"),
        cell_context=Field(None, "missing"),
        donor_state_batch=Field(None, "missing"),
        n_targets=Field(None, "missing"),
        id_mapping=Field(None, "missing"),
        count_kind=Field(None, "missing"),
        ntc_field=Field(None, "missing"),
        guides=Field(None, "missing"),
        cells_per_target=Field(None, "missing"),
        n_genes_measured=Field(None, "missing"),
        remote_bytes=Field(None, "missing", note="atlas scale; not for this machine"),
        temporary_bytes=Field(None, "missing"),
        checksum=Field(None, "missing"),
        panel_overlap=Field(None, "missing"),
        training_overlap=Field(
            {"no_drug_to_knockdown_equivalence": True},
            "derived",
            "docs/PIANO_OPERATIVO_2026-09-15.md",
        ),
        decision="exclude",
        decision_note="Pharmacological atlas. No automatic drug → knockdown map. D-005.",
    )


def card_scbasecount() -> SourceCard:
    return SourceCard(
        source_id="scbasecount",
        title="scBaseCount (Virtual Cell Atlas)",
        study_id=Field("scBaseCount", "cited",
                       "https://arcinstitute.org/tools/virtualcellatlas"),
        version=Field(None, "missing"),
        primary_url=Field("https://github.com/ArcInstitute/arc-virtual-cell-atlas/",
                          "cited", "docs/PIANO_OPERATIVO_2026-09-15.md"),
        license=Field(None, "missing"),
        perturbation_class=Field("observational", "cited",
                                 "docs/PIANO_OPERATIVO_2026-09-15.md"),
        cell_context=Field(None, "missing"),
        donor_state_batch=Field(None, "missing"),
        n_targets=Field(None, "missing"),
        id_mapping=Field(None, "missing"),
        count_kind=Field(None, "missing"),
        ntc_field=Field(None, "missing"),
        guides=Field(None, "missing"),
        cells_per_target=Field(None, "missing"),
        n_genes_measured=Field(None, "missing"),
        remote_bytes=Field(None, "missing"),
        temporary_bytes=Field(None, "missing"),
        checksum=Field(None, "missing"),
        panel_overlap=Field(None, "missing"),
        training_overlap=Field(
            {"observational_is_not_crispri_label": True},
            "derived",
            "docs/PIANO_OPERATIVO_2026-09-15.md",
        ),
        decision="exclude",
        decision_note="Observational atlas. May describe basal state; does not label knockdowns.",
    )


CARDS = (
    card_replogle_sc,
    card_h1,
    card_cd4,
    card_srivatsan,
    card_mcfaline,
    card_tahoe,
    card_scbasecount,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / "source_cards.json"
    if dest.exists():
        raise FileExistsError(f"{dest} exists; give a new --out")

    cards = [fn() for fn in CARDS]
    payload = {
        "n": len(cards),
        "cards": [c.as_dict() for c in cards],
        "errors": {c.source_id: validate_card(c) for c in cards},
        "decisions": {c.source_id: c.decision for c in cards},
        "claim": "derived from cited local evidence; no new matrix was opened",
    }
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for card in cards:
        path = args.out / f"{card.source_id}.json"
        path.write_text(json.dumps(card.as_dict(), indent=2) + "\n", encoding="utf-8")
    table = args.out / "decisions.md"
    lines = [
        "# Source-card decisions — 15 September 2026",
        "",
        "Compiled from existing local evidence and public records. "
        "Not a new measurement of any matrix.",
        "",
        "| ID | Class | Decision | Why |",
        "|---|---|---|---|",
    ]
    for card in cards:
        pert = card.perturbation_class.value
        lines.append(
            f"| `{card.source_id}` | {pert} | **{card.decision}** | {card.decision_note} |"
        )
    table.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = RunManifest(
        run_id=args.out.name, stage="64_source_cards", config={},
    )
    manifest.add_output("cards", dest)
    manifest.write(args.out / "manifest_64_source_cards.json")
    print(f"wrote {dest}")
    for card in cards:
        print(f"  {card.source_id:32} {card.decision}")


if __name__ == "__main__":
    main()
