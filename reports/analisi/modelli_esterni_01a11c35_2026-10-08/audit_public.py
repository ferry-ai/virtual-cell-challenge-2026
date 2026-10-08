"""Inspect public metadata only; never fetch array payloads, weights or labels."""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

PINS = {
    "sources": ("datasets", "arcinstitute/PIE_sources", "cb1aaa4e7655605bdc70a9bd77bbd62016b8c7d7"),
    "data": ("datasets", "arcinstitute/PIE_replogle_nadig_essential", "20c9faef76fc96fdc809871340bd93499413dfe7"),
    "splits": ("datasets", "arcinstitute/PIE_splits", "396ab9563175ee887750c9eed7ccaea6f5fdbf50"),
    "model": ("models", "arcinstitute/PIE_replogle_wdataset", "055c7a2cabdaff5659121c64fa2b609c231fc5be"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--controls", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    receipts = []

    def get(url):
        with urlopen(Request(url, headers={"User-Agent": "VCC2026-metadata-audit"}), timeout=60) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("metadata size guard exceeded")
        receipts.append(dict(url=url, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        return json.loads(raw)

    catalog = {}
    for key, (kind, repo, rev) in PINS.items():
        data = get(f"https://huggingface.co/api/{kind}/{repo}/revision/{rev}?blobs=true")
        if data["sha"] != rev:
            raise ValueError("revision mismatch")
        catalog[key] = data
    _, source_repo, source_rev = PINS["sources"]
    esm = get(f"https://huggingface.co/datasets/{source_repo}/resolve/{source_rev}/esm2/meta.json")
    _, data_repo, data_rev = PINS["data"]
    meta = get(f"https://huggingface.co/datasets/{data_repo}/resolve/{data_rev}/preprocessed/meta.json")
    local = {}
    for name, column in (("gene_names.csv", "gene_name"), ("pert_counts.csv", "target_gene")):
        path = args.controls/name
        raw = path.read_bytes()
        local[name] = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(),
                           values=[r[column] for r in csv.DictReader(raw.decode("utf-8-sig").splitlines())])
    sources = {"esm2", "ncbi_text", "string_space", "depmap_gene_effect", "context_text", "perturbation_text", "gene_text"}
    files = []
    for key, entry in catalog.items():
        kind, repo, rev = PINS[key]
        for f in entry["siblings"]:
            name = f["rfilename"]
            selected = ((key == "sources" and name.split("/")[0] in sources and not name.endswith("descriptions.json"))
                        or (key == "data" and name.startswith("preprocessed/"))
                        or (key == "model" and name in {"hepg2/best_auprc.ckpt", "hepg2/config.yaml", "hepg2/data_stats.json", "MODEL_LICENSE.md", "MODEL_ACCEPTABLE_USE_POLICY.md"})
                        or (key == "splits" and name.startswith("replogle_wdataset/") and "/hepg2/" in name))
            if selected:
                files.append(dict(repo=repo, revision=rev, path=name, bytes=f["size"],
                                  sha256=f.get("lfs", {}).get("sha256"), git_blob=f.get("blobId"),
                                  url=f"https://huggingface.co/{'datasets/' if kind == 'datasets' else ''}{repo}/resolve/{rev}/{name}"))
    genes, targets = set(local["gene_names.csv"]["values"]), set(local["pert_counts.csv"]["values"])
    result = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(), pins=PINS,
                  fetched_metadata=receipts, acquisition_plan=files,
                  total_planned_bytes=sum(f["bytes"] for f in files),
                  esm2_planned_bytes=sum(f["bytes"] for f in files if f["path"].startswith("esm2/")),
                  local_inputs={k: {a:b for a,b in v.items() if a != "values"} for k,v in local.items()},
                  coverage=dict(official_genes=len(genes), pie_genes=len(meta["genes"]),
                                exact_response_intersection=len(genes & set(meta["genes"])),
                                official_targets=len(targets), esm2_target_matches=len(targets & set(esm["keys"])),
                                esm2_missing_targets=sorted(targets-set(esm["keys"])),
                                targets_seen_in_pie_dataset=len(targets & set(meta["pert_to_id"])),
                                note="Exact symbol match only, not an alias audit or admission decision"),
                  esm2_provenance=esm["provenance"],
                  downloaded_weights_or_arrays=False)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("total_planned_bytes", "esm2_planned_bytes", "coverage")}, indent=2))


if __name__ == "__main__":
    main()
