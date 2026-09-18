"""Stage 74: genomic coordinates for the official gene axis, from a GENCODE GTF.

CRISPRi silences a promoter, and the silencing reaches neighbouring promoters:
on the K562 genome-wide pseudobulk, genes whose TSS lies within 1 kb of the
target's move by a median log2FC of -0.50 (994 head-to-head pairs), against
-0.02 at 20-100 kb. Predicting that needs the TSS of every gene a submission
writes, i.e. the 18,533 symbols of `gene_names.csv`.

Source, and why this one: on 2026-09-17 Ensembl BioMart answered "Service
unavailable" and the Ensembl REST API answered HTTP 500 to every request, so the
coordinates come from GENCODE's own release file,
`gencode.v50.basic.annotation.gtf.gz` from
https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/latest_release/
(79,970,394 bytes, md5 11e77cf1d4b78b43f57d608e3f7f2202, equal to the release's
MD5SUMS). The file must already be in `<data_root>/external/annotation/`; this
stage verifies its md5 and never downloads.

A symbol is matched to a GENCODE `gene_name` directly, then through HGNC's
previous and alias symbols (`interim/encoder_inputs_2026-09-14/hgnc_complete_set`).
Only chr1-22, X, Y, M are kept. Unresolved symbols are listed, never guessed.
Writes `gene_coordinates_gencode_v50.tsv` and a JSON manifest; refuses to
overwrite.

    python scripts/74_fetch_gene_coordinates.py
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402

GTF_NAME = "gencode.v50.basic.annotation.gtf.gz"
GTF_MD5 = "11e77cf1d4b78b43f57d608e3f7f2202"
MAIN = {f"chr{i}" for i in range(1, 23)} | {"chrX", "chrY", "chrM"}
ATTR = re.compile(r'(\w+) "([^"]*)"')


def md5sum(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def read_genes(gtf: Path) -> pd.DataFrame:
    rows = []
    with gzip.open(gtf, "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if parts[2] != "gene" or parts[0] not in MAIN:
                continue
            attrs = dict(ATTR.findall(parts[8]))
            start, end, strand = int(parts[3]), int(parts[4]), parts[6]
            rows.append({
                "gene_name": attrs.get("gene_name"), "gene_id": attrs.get("gene_id"),
                "gene_type": attrs.get("gene_type"), "chrom": parts[0], "start": start, "end": end,
                "strand": 1 if strand == "+" else -1, "tss": start if strand == "+" else end,
            })
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--annotation-dir", type=Path, default=None)
    p.add_argument("--hgnc", type=Path, default=None)
    args = p.parse_args()

    ann = args.annotation_dir or config.paths().external / "annotation"
    gtf = ann / GTF_NAME
    tsv = ann / "gene_coordinates_gencode_v50.tsv"
    man = ann / "gene_coordinates_gencode_v50.json"
    if tsv.exists() or man.exists():
        raise SystemExit(f"{tsv} already exists; not overwriting")
    digest = md5sum(gtf)
    if digest != GTF_MD5:
        raise SystemExit(f"{gtf}: md5 {digest} != published {GTF_MD5}")

    genes = read_genes(gtf)
    # One record per name: prefer protein-coding, then the longest span.
    genes["span"] = genes["end"] - genes["start"]
    genes["pc"] = genes["gene_type"] == "protein_coding"
    genes = genes.sort_values(["gene_name", "pc", "span"], ascending=[True, False, False])
    by_name = genes.drop_duplicates("gene_name").set_index("gene_name")

    symbols = list(official_axis().symbols)
    resolved = {s: (s, "gene_name") for s in symbols if s in by_name.index}
    hgnc_path = args.hgnc or (config.paths().interim / "encoder_inputs_2026-09-14" / "hgnc_complete_set")
    n_alias = 0
    if hgnc_path.exists():
        h = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
        lookup: dict[str, str] = {}
        for _, rec in h[["symbol", "prev_symbol", "alias_symbol"]].fillna("").iterrows():
            names = [rec["symbol"]] + rec["prev_symbol"].split("|") + rec["alias_symbol"].split("|")
            current = [n for n in names if n in by_name.index]
            if not current:
                continue
            for n in names:
                if n and n not in lookup:
                    lookup[n] = current[0]
        for s in symbols:
            if s not in resolved and s in lookup:
                resolved[s] = (lookup[s], "hgnc_alias")
                n_alias += 1
    rows = []
    for s in symbols:
        if s not in resolved:
            continue
        name, via = resolved[s]
        rec = by_name.loc[name]
        rows.append({"symbol": s, "gencode_name": name, "gene_id": rec["gene_id"], "gene_type": rec["gene_type"],
                     "chrom": rec["chrom"], "start": int(rec["start"]), "end": int(rec["end"]),
                     "strand": int(rec["strand"]), "tss": int(rec["tss"]), "resolved_via": via})
    frame = pd.DataFrame(rows)
    frame.to_csv(tsv, sep="\t", index=False)
    unresolved = [s for s in symbols if s not in resolved]
    man.write_text(json.dumps({
        "stage": "74_fetch_gene_coordinates",
        "written_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(gtf), "source_md5": digest,
        "source_url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/latest_release/" + GTF_NAME,
        "why_not_ensembl": "BioMart 'Service unavailable' and REST HTTP 500 on 2026-09-17",
        "output": str(tsv), "output_sha256": hashlib.sha256(tsv.read_bytes()).hexdigest(),
        "n_axis": len(symbols), "n_resolved": len(frame), "n_via_hgnc_alias": n_alias,
        "n_unresolved": len(unresolved), "unresolved_sample": unresolved[:60],
        "tss_rule": "gene start on + strand, gene end on - strand (gene-level, not transcript-level)",
    }, indent=2), encoding="utf-8")
    print(f"resolved {len(frame)}/{len(symbols)} ({n_alias} via HGNC alias); unresolved {len(unresolved)}")


if __name__ == "__main__":
    main()
