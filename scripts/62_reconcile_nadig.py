"""Reconcile Nadig HepG2 GEO vs scPerturb mirror vs Jurkat. No new download.

Compares three photographs that already exist, plus the live Zenodo record
for the Jurkat mirror (sizes and md5 only). Does not open the 1.29 GB Jurkat
file and does not treat the mirror as a second experiment.

    scripts/py.cmd scripts/62_reconcile_nadig.py --out reports/nadig_reconcile_2026-09-15
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.manifest import RunManifest
from vcc2026.resources import GiB, snapshot
from vcc2026.runtime import disk_peak_estimate
from vcc2026.source_card import Field, SourceCard

REPO = Path(__file__).resolve().parents[1]
ZENODO_SC_PERTURB = "https://zenodo.org/api/records/13350497"
JURKAT_KEY = "NadigOConner2024_jurkat.h5ad"
HEPG2_KEY = "NadigOConner2024_hepg2.h5ad"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def obs_keys(probe: dict) -> list[str]:
    obs = probe.get("obs") or {}
    return sorted(k for k in obs if k != "__categories")


def zenodo_file(record: dict, key: str) -> dict | None:
    for item in record.get("files") or []:
        if item.get("key") == key:
            return item
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / "nadig_reconciliation.json"
    if dest.exists():
        raise FileExistsError(f"{dest} exists; give a new --out")

    geo_hepg2 = load_json(REPO / "reports/candidate_verification/hepg2_probe.json")
    geo_jurkat = load_json(REPO / "reports/candidate_verification/jurkat_probe.json")
    coverage = load_json(REPO / "reports/candidate_verification/coverage_summary.json")
    acquisition = load_json(REPO / "reports/hepg2_2026-09-14/acquisition.json")
    audit = load_json(REPO / "reports/hepg2_2026-09-14/nadig_hepg2_audit.json")

    request = Request(ZENODO_SC_PERTURB, headers={"Accept": "application/json",
                                                  "User-Agent": "vcc2026-audit"})
    with urlopen(request, timeout=60) as response:
        zenodo = json.loads(response.read().decode("utf-8"))
    jurkat_z = zenodo_file(zenodo, JURKAT_KEY)
    hepg2_z = zenodo_file(zenodo, HEPG2_KEY)

    geo_hepg2_shape = (geo_hepg2.get("X") or {}).get("shape")
    geo_jurkat_shape = (geo_jurkat.get("X") or {}).get("shape")
    mirror_shape = ((audit.get("declared") or {}).get("X") or {}).get("shape")
    geo_hepg2_ntc = (geo_hepg2.get("ntc_labels") or {}).get("non-targeting")
    geo_jurkat_ntc = (geo_jurkat.get("ntc_labels") or {}).get("non-targeting")

    hepg2_diff = {
        "same_experiment": True,
        "mirror_is_not_replication": True,
        "shape_geo": geo_hepg2_shape,
        "shape_mirror": mirror_shape,
        "shape_match": geo_hepg2_shape == mirror_shape,
        "ntc_geo_label": "obs.gene == 'non-targeting'",
        "ntc_geo_count": geo_hepg2_ntc,
        "ntc_mirror_label": "obs.perturbation == 'control'",
        "ntc_mirror_count": 4976,
        "ntc_count_match": geo_hepg2_ntc == 4976,
        "obs_keys_geo": obs_keys(geo_hepg2),
        "obs_keys_mirror": [
            c["name"] for c in (audit.get("declared") or {}).get("obs_columns") or []
        ],
        "bytes_geo_declared": {
            "value": "5.2 GB",
            "claim": "cited",
            "source": "reports/hepg2_2026-09-14/acquisition.json provenance.primary_archive",
        },
        "bytes_mirror_declared": (hepg2_z or {}).get("size"),
        "bytes_mirror_acquired": acquisition["bytes"]["received"],
        "md5_mirror_match": acquisition["digests"]["md5_match"],
        "claim": "measured",
        "sources": [
            "reports/candidate_verification/hepg2_probe.json",
            "reports/hepg2_2026-09-14/nadig_hepg2_audit.json",
            "reports/hepg2_2026-09-14/acquisition.json",
        ],
    }

    jurkat_inventory = {
        "geo_shape": geo_jurkat_shape,
        "geo_dtype": (geo_jurkat.get("X") or {}).get("dtype"),
        "geo_obs_keys": obs_keys(geo_jurkat),
        "geo_ntc_label": "obs.gene == 'non-targeting'",
        "geo_ntc_count": geo_jurkat_ntc,
        "panel_observed_targets": (coverage.get("jurkat") or {}).get("observed_targets"),
        "output_gene_overlap": (coverage.get("jurkat") or {}).get("output_gene_overlap"),
        "zenodo_mirror": {
            "key": JURKAT_KEY,
            "size": (jurkat_z or {}).get("size"),
            "checksum": (jurkat_z or {}).get("checksum"),
            "url": ((jurkat_z or {}).get("links") or {}).get("self"),
        } if jurkat_z else None,
        "schema_like_geo_hepg2": obs_keys(geo_jurkat) == obs_keys(geo_hepg2),
        "on_disk": False,
        "claim": "measured",
    }

    resources = snapshot(args.out)
    jurkat_bytes = (jurkat_z or {}).get("size")
    peak = disk_peak_estimate(
        input_bytes=int(jurkat_bytes or 0),
        decompressed_bytes=None,
        derived_bytes=None,
        export_bytes=None,
    ) if jurkat_bytes else None

    card = SourceCard(
        source_id="nadig_jurkat",
        title="Nadig 2025 Jurkat Perturb-seq",
        study_id=Field("GSE264667", "cited",
                       "reports/candidate_verification/jurkat_probe.json"),
        version=Field("GEO original probed 2026-09-12; scPerturb mirror listed on Zenodo 13350497",
                      "cited", ZENODO_SC_PERTURB),
        primary_url=Field(
            ((jurkat_z or {}).get("links") or {}).get("self") or
            "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE264nnn/GSE264667/suppl/",
            "cited",
            ZENODO_SC_PERTURB,
        ),
        license=Field("cc-by-4.0", "cited", ZENODO_SC_PERTURB,
                      note="declared on the scPerturb collection; competition compatibility not verified"),
        perturbation_class=Field("CRISPRi", "cited",
                                 "configs/sources.yaml"),
        cell_context=Field("Jurkat", "cited", "configs/sources.yaml"),
        donor_state_batch=Field(
            {"gem_group": True, "batch_on_mirror": "unverified_until_opened"},
            "derived",
            "reports/candidate_verification/jurkat_probe.json",
        ),
        n_targets=Field(None, "missing",
                        note="perturbation count not stored as n_unique in the GEO probe"),
        id_mapping=Field("obs.gene / var.gene_name on the GEO original",
                         "measured",
                         "reports/candidate_verification/jurkat_probe.json"),
        count_kind=Field("dense float32; count samples integral on GEO probe",
                         "measured",
                         "reports/candidate_verification/jurkat_probe.json"),
        ntc_field=Field("obs.gene == 'non-targeting' on GEO original (12,013 cells)",
                        "measured",
                        "reports/candidate_verification/jurkat_probe.json",
                        note="mirror may rename, as HepG2 did"),
        guides=Field("obs.sgID_AB present on GEO original",
                     "measured",
                     "reports/candidate_verification/jurkat_probe.json"),
        cells_per_target=Field(None, "missing",
                               note="paper reports median 83; not re-counted here"),
        n_genes_measured=Field(geo_jurkat_shape[1] if geo_jurkat_shape else None,
                               "measured" if geo_jurkat_shape else "missing",
                               "reports/candidate_verification/jurkat_probe.json"),
        remote_bytes=Field(jurkat_bytes, "measured", ZENODO_SC_PERTURB) if jurkat_bytes else Field(
            None, "missing"
        ),
        temporary_bytes=Field(None, "missing",
                              note="dense GEO object is ~9.4 GB; do not materialise"),
        checksum=Field((jurkat_z or {}).get("checksum"), "cited",
                       ZENODO_SC_PERTURB) if jurkat_z else Field(None, "missing"),
        panel_overlap=Field(
            {
                "observed_targets": (coverage.get("jurkat") or {}).get("observed_targets"),
                "output_gene_overlap": (coverage.get("jurkat") or {}).get("output_gene_overlap"),
                "list_source": "reports/candidate_verification/coverage_summary.json",
            },
            "measured",
            "reports/candidate_verification/coverage_summary.json",
        ),
        training_overlap=Field(
            {"useful_as": "held-out T-lymphoblast context; 0/300 panel coverage"},
            "derived",
            "reports/candidate_verification/coverage_summary.json",
        ),
        decision="acquire",
        decision_note=(
            "Fourth perturbed context for the existing benchmark, after a remote "
            "runtime measures disk. Mirror 1.29 GB vs GEO ~9.4 GB. Expect the "
            "same label rename as HepG2. Not a panel-coverage source."
        ),
    )

    report = {
        "hepg2_geo_vs_mirror": hepg2_diff,
        "jurkat": jurkat_inventory,
        "source_card": card.as_dict(),
        "disk": {
            "free_bytes": resources.disk_free_bytes,
            "jurkat_mirror_bytes": jurkat_bytes,
            "leaves_10gib_floor": (
                None if jurkat_bytes is None else
                (resources.disk_free_bytes - jurkat_bytes) >= 10 * GiB
            ),
            "peak_estimate": peak,
        },
        "decision": {
            "hepg2_original": "do_not_download — same experiment as the acquired mirror",
            "jurkat_mirror": "candidate fourth context; download after runtime preflight",
            "jurkat_geo_original": "do_not_download if the mirror is used",
        },
        "not_done": [
            "Jurkat file not opened",
            "mirror obs labels not verified on Jurkat",
            "barcode/guide equality GEO vs mirror not measured on Jurkat",
        ],
        "claim_types_used": ["measured", "cited", "derived", "missing"],
    }
    dest.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    (args.out / "source_card_nadig_jurkat.json").write_text(
        json.dumps(card.as_dict(), indent=2) + "\n", encoding="utf-8"
    )
    manifest = RunManifest(
        run_id=args.out.name, stage="62_reconcile_nadig", config={},
    )
    manifest.add_output("reconciliation", dest)
    manifest.note("Jurkat matrix was not downloaded.")
    manifest.write(args.out / "manifest_62_reconcile_nadig.json")
    print(f"wrote {dest}")
    print(f"HepG2 shape match: {hepg2_diff['shape_match']}  "
          f"NTC count match: {hepg2_diff['ntc_count_match']}")
    print(f"Jurkat mirror bytes: {jurkat_bytes}  "
          f"panel observed: {jurkat_inventory['panel_observed_targets']}")


if __name__ == "__main__":
    main()
