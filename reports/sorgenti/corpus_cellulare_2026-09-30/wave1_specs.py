"""Write the specs of the first ingestion wave of the cell-level corpus (30/09 evening) into jobs_colab/.

Every column name below comes from a measurement, not from memory: the remote inventory (p1_r4/remote/*.json) for
H1 and the Nadig files, and the stage 71 log of 17/09 for the Replogle single-cell files (obs columns gem_group,
gene, gene_id, transcript, gene_transcript, sgID_AB, mitopercent, UMI_count, ...; controls 'non-targeting'; X dense).
Checksums are the ones the hosts publish (md5 on Zenodo and Figshare, crc32c on the Arc bucket) or the ones already
verified on Drive (K562 genome-wide: md5 and sha256 of its fetch record).

    python wave1_specs.py          (refuses to write over an existing spec)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "jobs_colab"
ARC = "https://storage.googleapis.com/arc-institute-virtual-cell-atlas/virtual-cell-challenge/2025/"
ZEN = "https://zenodo.org/api/records/13350497/files/{}/content"
FIG = "https://ndownloader.figshare.com/files/{}"


def source(sid, files, license_, release):
    return {"id": sid, "release": release, "license": license_, "files": files}


def h1(split, fname, size, crc):
    return {"name": f"h1_{split}", "adapter": "h5rows",
            "kwargs": {"path": ARC + f"{split if split != 'val' else 'validation'}/{fname}", "study": f"h1_vcc2025_{split}",
                       "context": "H1", "chemistry": "10x Flex", "modality": "CRISPRi", "axis_csv": "{AXIS}",
                       "block": 20000, "target_col": "target_gene", "control_values": ["non-targeting"],
                       "guides_col": "guide_id", "library_col": "batch"},
            "source": source("h1_vcc2025", [{"role": "counts h5ad", "locator": ARC + (split if split != 'val' else 'validation')
                                              + f"/{fname}", "bytes": size, "crc32c": crc, "sha256": "not recomputed: "
                                              "read by HTTP ranges with ETag checks; the sha256 of this object is in "
                                              "runs/rlab_setup_2026-09-30_r2/receipts/h1_vcc2025_r2/fetch.json"}],
                             "VCC 2025 terms (training allowed, per the 2026 data page)", "Arc bucket, 16/12/2025 objects")}


NADIG = {"target_col": "gene", "control_values": ["non-targeting"], "guides_col": "guide_id", "library_col": "batch",
         "published_depth": "UMI_count"}
REPLOGLE = {"target_col": "gene", "control_values": ["non-targeting"], "guides_col": "sgID_AB",
            "library_col": "gem_group", "published_depth": "UMI_count"}

SPECS = {
    "j04_h1_trainval_r1": {"units": [h1("train", "adata_Training.h5ad", 15482497461, "/Z0row=="),
                                     h1("val", "adata_Validation.h5ad", 6928967541, "EendZg==")],
                           "min_free_out_bytes": 0},
    "j05_jurkat_nadig_r1": {"units": [{"name": "jurkat_nadig", "adapter": "h5rows",
                                       "kwargs": {"path": ZEN.format("NadigOConner2024_jurkat.h5ad"), "study": "jurkat_nadig",
                                                  "context": "Jurkat", "chemistry": "10x 3'", "modality": "CRISPRi",
                                                  "axis_csv": "{AXIS}", "block": 20000, **NADIG},
                                       "source": source("jurkat_nadig", [{"role": "counts h5ad (scPerturb)",
                                                                           "locator": ZEN.format("NadigOConner2024_jurkat.h5ad"),
                                                                           "bytes": 1293665804,
                                                                           "md5": "d8b05d00bfbd686d37ffdd4293bc6c8c"}],
                                                        "CC BY 4.0", "Zenodo 13350497 (scPerturb)"),
                                       "expect": {"rows": [0, 262956]}}],
                            "min_free_out_bytes": 0},
    "j06_k562_gwps_r1": {"units": [
        {"name": f"k562_gwps_{part}", "adapter": "h5rows",
         "kwargs": {"path": "{DRIVE}/data/raw/replogle/K562_gwps_raw_singlecell_01.h5ad", "study": "replogle_k562_gwps",
                    "context": "K562", "chemistry": "10x 3' v3", "modality": "CRISPRi", "axis_csv": "{AXIS}",
                    "block": 20000, "row_range": rows, **REPLOGLE},
         "source": source("replogle_k562_gwps", [{"role": "raw single-cell h5ad", "locator": FIG.format("35775507"),
                                                   "bytes": 65830941948, "md5": "887e3e6a8c8df6eadf7a3030a53c9546",
                                                   "sha256": "b697ef7fedcec2972ec334608f86f2a29cb25e70c81b6725195f4cda60a9de2c",
                                                   "copy": "Drive data/raw/replogle/, verified at its fetch"}],
                          "CC BY 4.0", "Figshare 20029387, Replogle et al. 2022"),
         "expect": {"rows": rows}}
        for part, rows in (("a", [0, 1000000]), ("b", [1000000, 1989578]))],
        "min_free_out_bytes": 0},
    "j07_replogle_ess_rpe1_r1": {"units": [
        {"name": name, "adapter": "h5rows",
         "kwargs": {"path": FIG.format(fid), "study": f"replogle_{name}", "context": ctx, "chemistry": "10x 3' v3",
                    "modality": "CRISPRi", "axis_csv": "{AXIS}", "block": 20000, **REPLOGLE},
         "source": source(f"replogle_{name}", [{"role": "raw single-cell h5ad", "locator": FIG.format(fid), "bytes": size,
                                                 "md5": md5}], "CC BY 4.0", "Figshare 20029387, Replogle et al. 2022")}
        for name, fid, ctx, size, md5 in (("k562_essential", "35773219", "K562", 10661879995, "4f1122ce1c7f13299a68df6459a266d3"),
                                          ("rpe1", "35775606", "RPE1", 8700873216, "not published by Figshare"))],
        "min_free_out_bytes": 0},
}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for job, body in SPECS.items():
        path = OUT / f"{job}_spec.json"
        if path.exists():
            sys.exit(f"refusing: {path} exists")
        path.write_text(json.dumps({"job_id": job, "min_free_stage_bytes": 4 << 30, **body}, indent=1), encoding="utf-8")
        print(path.name, len(body["units"]), "units")


if __name__ == "__main__":
    main()
