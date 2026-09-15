"""Probe Jiang/Mixscale from public records. No Seurat object is downloaded.

The operational plan's first data priority. What this script can establish
without opening an RDS:

* Zenodo file list, sizes, md5, license, URLs (live GET of the record).
* HTTP headers of each file (HEAD or a 1-byte Range).
* Contents of files under --max-download-bytes (readme, tiny RDS genelists).
* A source card whose panel overlap stays missing until a target list is read.
* A pilot proposal: smallest Seurat block (TGFB), hold out one entire cell
  line, do not treat stimulus as a new line, do not use study-wide DE as
  features for unseen targets.

RAM for readRDS is not measured here and is not invented.

    scripts/py.cmd scripts/61_probe_jiang.py --out reports/jiang_2026-09-15
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.manifest import RunManifest
from vcc2026.resources import GiB, snapshot
from vcc2026.runtime import disk_peak_estimate
from vcc2026.source_card import Field, SourceCard, validate_card

ZENODO_API = "https://zenodo.org/api/records/14518762"
MIXSCALE = "https://github.com/satijalab/Mixscale"
GEO = "GSE281048"
PAPER = "https://doi.org/10.1038/s41556-025-01622-z"
CELL_LINES = ("A549", "MCF7", "HT29", "HAP1", "BxPC3", "K562")
STIMULI = ("IFNB", "IFNG", "TGFB", "TNFA", "INS")


def http_json(url: str, *, timeout: int = 60) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "vcc2026-audit"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def http_headers(url: str, *, timeout: int = 60) -> dict:
    """HEAD, falling back to a 1-byte Range GET if HEAD is refused."""
    headers = {"User-Agent": "vcc2026-audit"}
    try:
        request = Request(url, method="HEAD", headers=headers)
        with urlopen(request, timeout=timeout) as response:
            return {
                "method": "HEAD",
                "status": response.status,
                "headers": {k.lower(): v for k, v in response.headers.items()},
            }
    except (HTTPError, URLError, ValueError):
        request = Request(url, headers={**headers, "Range": "bytes=0-0"})
        with urlopen(request, timeout=timeout) as response:
            return {
                "method": "GET_RANGE",
                "status": response.status,
                "headers": {k.lower(): v for k, v in response.headers.items()},
            }


def http_download(url: str, dest: Path, *, max_bytes: int, timeout: int = 120) -> dict:
    if dest.exists():
        raise FileExistsError(f"{dest} exists")
    request = Request(url, headers={"User-Agent": "vcc2026-audit"})
    with urlopen(request, timeout=timeout) as response:
        status = response.status
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise RuntimeError(f"{url} exceeded download cap {max_bytes}")
    dest.write_bytes(data)
    return {
        "path": str(dest),
        "bytes": len(data),
        "md5": hashlib.md5(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "status": status,
        "claim": "measured",
    }


def md5_from_zenodo(checksum: str) -> str | None:
    if checksum.startswith("md5:"):
        return checksum.split(":", 1)[1]
    return checksum or None


def build_card(record: dict, files: list[dict], downloaded: list[dict]) -> SourceCard:
    seurat = [f for f in files if f["key"].startswith("Seurat_object_") and f["key"].endswith(".rds")]
    meta = record.get("metadata") or {}
    license_id = (meta.get("license") or {}).get("id")
    version = meta.get("version")
    return SourceCard(
        source_id="jiang_mixscale",
        title="Jiang 2025 Mixscale Perturb-seq (six lines × five stimuli)",
        study_id=Field(GEO, "cited", PAPER),
        version=(
            Field(version, "cited", ZENODO_API) if version
            else Field(None, "missing", note="Zenodo metadata.version absent")
        ),
        primary_url=Field("https://zenodo.org/records/14518762", "measured", ZENODO_API),
        license=Field(license_id, "cited", ZENODO_API) if license_id else Field(
            None, "missing", note="Zenodo record had no license.id"
        ),
        perturbation_class=Field("CRISPRi", "cited", PAPER),
        cell_context=Field(list(CELL_LINES), "cited", PAPER),
        donor_state_batch=Field(
            {
                "stimuli": list(STIMULI),
                "stimulation_hours": 24,
                "note": (
                    "Six lines × five stimuli are not thirty independent lines. "
                    "K562 is already a local training context."
                ),
            },
            "cited",
            PAPER,
        ),
        n_targets=Field(
            None, "missing",
            note="paper reports >1500 perturbations; no target list was opened here",
        ),
        id_mapping=Field(None, "missing", note="RDS not opened"),
        count_kind=Field(
            None, "missing",
            note="Seurat default is often log-normalised data; RNA@counts must be verified after conversion",
        ),
        ntc_field=Field(
            None, "missing",
            note="paper and Mixscale vignette use NT/neg; column name in these RDS is unverified",
        ),
        guides=Field(None, "missing"),
        cells_per_target=Field(None, "missing"),
        n_genes_measured=Field(None, "missing"),
        remote_bytes=Field(
            {f["key"]: f["size"] for f in files},
            "measured",
            ZENODO_API,
        ),
        temporary_bytes=Field(None, "missing", note="RDS deserialisation RAM is unmeasured"),
        checksum=Field(
            {f["key"]: f.get("checksum") for f in files},
            "cited",
            ZENODO_API,
        ),
        panel_overlap=Field(
            None, "missing",
            note="no target list was read; do not infer coverage from 1500 perturbations",
        ),
        training_overlap=Field(
            {"k562_already_local": True, "same_experiment": False},
            "derived",
            "configs/sources.yaml",
            note="K562 in Jiang is a new experiment on a known line, not a new line",
        ),
        extra_target_sample=Field(
            None, "missing",
            note="retain extra-panel targets only after a list exists",
        ),
        decision="probe",
        decision_note=(
            "Metadata record is live. Do not acquire an RDS until a remote "
            "runtime has measured RAM for readRDS and NTC pairing is specified. "
            f"Small files downloaded: {[d['path'] for d in downloaded] or 'none'}."
        ),
    )


def propose_pilot(files: list[dict], free_bytes: int) -> dict:
    seurat = [
        f for f in files
        if f["key"].startswith("Seurat_object_") and "Bulk" not in f["key"]
    ]
    smallest = min(seurat, key=lambda f: f["size"]) if seurat else None
    peak = None
    if smallest is not None:
        peak = disk_peak_estimate(
            input_bytes=int(smallest["size"]),
            decompressed_bytes=None,
            derived_bytes=None,
            export_bytes=None,
            margin=0.25,
        )
    return {
        "candidate_block": smallest,
        "why_this_block": (
            "Smallest Seurat object by declared bytes. Size is not evidence of "
            "effect strength."
        ) if smallest else "no Seurat object in the record",
        "hold_out": (
            "One entire cell line, all of its wells in this block. Do not hold "
            "out a stimulus and call it a new context. Do not train on K562 "
            "here and treat K562 Replogle as independent confirmation of the "
            "same line."
        ),
        "forbidden_features": (
            "DE_results_all_pathway.zip is Mixscale weighted DE on the whole "
            "study. It must not become a target descriptor for unseen targets."
        ),
        "conversion": {
            "format": "Seurat RDS",
            "requires": ["R", "Seurat"],
            "readRDS_ram_bytes": None,
            "readRDS_ram_claim": "missing",
            "note": "File size is not RAM. Do not invent a multiplier.",
        },
        "disk_peak_estimate": peak,
        "local_disk_free_bytes": free_bytes,
        "local_fits_under_10gib_floor": (
            None if smallest is None else
            (free_bytes - smallest["size"]) >= 10 * GiB
        ),
        "claim": "proposal",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-download-bytes", type=int, default=2_000_000)
    parser.add_argument("--skip-headers", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / "jiang_probe.json"
    if dest.exists():
        raise FileExistsError(f"{dest} exists; give a new --out")

    resources = snapshot(args.out)
    record = http_json(ZENODO_API)
    files = record.get("files") or []
    headers = []
    if not args.skip_headers:
        for item in files:
            url = item["links"]["self"]
            try:
                headers.append({"key": item["key"], **http_headers(url)})
            except Exception as exc:  # noqa: BLE001
                headers.append({
                    "key": item["key"],
                    "error": f"{type(exc).__name__}: {exc}",
                    "claim": "measured",
                })

    downloaded = []
    small_dir = args.out / "small_files"
    small_dir.mkdir(exist_ok=True)
    for item in files:
        if item["size"] > args.max_download_bytes:
            continue
        path = small_dir / item["key"]
        try:
            downloaded.append({
                "key": item["key"],
                "declared_md5": md5_from_zenodo(item.get("checksum") or ""),
                **http_download(item["links"]["self"], path,
                               max_bytes=args.max_download_bytes),
            })
        except Exception as exc:  # noqa: BLE001
            downloaded.append({
                "key": item["key"],
                "error": f"{type(exc).__name__}: {exc}",
            })

    card = build_card(record, files, [d for d in downloaded if "bytes" in d])
    card_errors = validate_card(card)
    seurat_bytes = sum(
        f["size"] for f in files
        if f["key"].startswith("Seurat_object_") and "Bulk" not in f["key"]
    )
    report = {
        "claim_types_used": ["measured", "cited", "derived", "missing", "proposal"],
        "zenodo": {
            "id": record.get("id"),
            "doi": record.get("doi"),
            "title": record.get("title"),
            "version": (record.get("metadata") or {}).get("version"),
            "license": (record.get("metadata") or {}).get("license"),
            "n_files": len(files),
            "seurat_perturb_seq_bytes": seurat_bytes,
        },
        "files": [
            {
                "key": f["key"],
                "size": f["size"],
                "checksum": f.get("checksum"),
                "url": f["links"]["self"],
            }
            for f in files
        ],
        "headers": headers,
        "downloaded_small_files": downloaded,
        "cell_lines_cited": list(CELL_LINES),
        "stimuli_cited": list(STIMULI),
        "geo_accession": GEO,
        "geo_page_live": False,
        "geo_page_note": "Direct GEO HTML is browser-gated; not opened here.",
        "mixscale_repo": MIXSCALE,
        "paper": PAPER,
        "source_card": card.as_dict(),
        "source_card_errors": card_errors,
        "pilot": propose_pilot(files, resources.disk_free_bytes),
        "resources": resources.as_dict(),
        "not_done": [
            "RDS not downloaded",
            "RDS not deserialised",
            "NTC column not verified",
            "panel overlap not counted",
            "GEO supplementary not fetched",
        ],
    }
    dest.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    card_path = args.out / "source_card.json"
    card_path.write_text(json.dumps(card.as_dict(), indent=2) + "\n", encoding="utf-8")
    manifest = RunManifest(
        run_id=args.out.name, stage="61_probe_jiang",
        config={"max_download_bytes": args.max_download_bytes},
    )
    manifest.add_output("probe", dest)
    manifest.add_output("source_card", card_path)
    manifest.note("RDS objects were not downloaded. Panel overlap is missing.")
    manifest.write(args.out / "manifest_61_probe_jiang.json")
    print(f"wrote {dest}")
    print(f"seurat bytes {seurat_bytes}  small files {len(downloaded)}")
    print(f"panel overlap: missing (no target list)")
    print(f"pilot block: {report['pilot']['candidate_block']}")


if __name__ == "__main__":
    main()
