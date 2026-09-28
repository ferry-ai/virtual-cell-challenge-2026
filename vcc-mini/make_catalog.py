"""Freeze catalog.json: every file the Drive loader may fetch, with its size and checksum.

Sizes and checksums come from the hosts' own APIs at the time this script runs:
Figshare (md5), Zenodo (md5), Hugging Face (sha256 of the LFS object, pinned revision),
S3 (Content-Length only: the ETag is multipart and is not a checksum of the file).

Tiers, all off in the notebook except "mini":
    mini           the five pseudobulk/scPerturb files of the local bench      ~2.7 GB
    sc_replogle    K562 essential and RPE1 single-cell raw counts              ~19.4 GB
    sc_k562_gw     K562 genome-wide single-cell raw counts                     ~65.8 GB
    cd4            Marson 2025 CD4 genome-wide pseudobulk (licence not stated) ~44.6 GB
    orion_hct116   X-Atlas/Orion HCT116, 109 parquet (CC-BY-NC-SA-4.0)         ~46.6 GB
    orion_hek293t  X-Atlas/Orion HEK293T, 223 parquet (CC-BY-NC-SA-4.0)        ~79.7 GB
"""
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ORION_REPO = "Xaira-Therapeutics/X-Atlas-Orion"
CD4_URL = "https://genome-scale-tcell-perturb-seq.s3.amazonaws.com/marson2025_data/GWCD4i.pseudobulk_merged.h5ad"


def get(url):
    return json.load(urllib.request.urlopen(url, timeout=60))


def main():
    entries = []
    fig = {f["name"]: f for f in get("https://api.figshare.com/v2/articles/20029387/files?page_size=100")}
    fig_lic = get("https://api.figshare.com/v2/articles/20029387")["license"]["name"]
    replogle = "Replogle et al. 2022, Figshare+ 10.25452/figshare.plus.20029387"
    for tier, name in [("mini", "K562_essential_raw_bulk_01.h5ad"), ("mini", "K562_gwps_raw_bulk_01.h5ad"),
                       ("mini", "rpe1_raw_bulk_01.h5ad"),
                       ("sc_replogle", "K562_essential_raw_singlecell_01.h5ad"),
                       ("sc_replogle", "rpe1_raw_singlecell_01.h5ad"),
                       ("sc_k562_gw", "K562_gwps_raw_singlecell_01.h5ad")]:
        f = fig[name]
        entries.append(dict(tier=tier, file=name, url=f["download_url"], bytes=f["size"],
                            algo="md5", checksum=f["computed_md5"], source=replogle, license=fig_lic))
    z = get("https://zenodo.org/api/records/13350497")
    zl = z["metadata"]["license"]["id"]
    for f in z["files"]:
        if f["key"] in ("NadigOConner2024_hepg2.h5ad", "NadigOConner2024_jurkat.h5ad"):
            entries.append(dict(tier="mini", file=f["key"], url=f["links"]["self"], bytes=f["size"],
                                algo="md5", checksum=f["checksum"].split(":")[1],
                                source="Nadig, O'Conner et al. 2025 via scPerturb, Zenodo 10.5281/zenodo.13350497",
                                license=zl))
    head = urllib.request.urlopen(urllib.request.Request(CD4_URL, method="HEAD"), timeout=60)
    entries.append(dict(tier="cd4", file="GWCD4i.pseudobulk_merged.h5ad", url=CD4_URL,
                        bytes=int(head.headers["Content-Length"]), algo="size_only", checksum=None,
                        source="Zhu, Dann, Marson et al. 2025, GEO GSE314342, public S3 bucket",
                        license="not stated by the source: check before any use beyond research"))
    info = get(f"https://huggingface.co/api/datasets/{ORION_REPO}")
    rev = info["sha"]
    lic = [t.split(":", 1)[1] for t in info.get("tags", []) if t.startswith("license:")]
    tree = get(f"https://huggingface.co/api/datasets/{ORION_REPO}/tree/{rev}/data?recursive=true")
    for f in sorted((f for f in tree if f["type"] == "file"), key=lambda f: f["path"]):
        name = f["path"].split("/")[-1]
        line = name.split("_")[0]
        entries.append(dict(tier=f"orion_{line.lower()}", file=name,
                            url=f"https://huggingface.co/datasets/{ORION_REPO}/resolve/{rev}/{f['path']}",
                            bytes=f["size"], algo="sha256", checksum=f["lfs"]["oid"],
                            source=f"X-Atlas/Orion (Xaira), Hugging Face {ORION_REPO} at {rev}",
                            license=lic[0] if lic else None))
    tiers = {}
    for e in entries:
        t = tiers.setdefault(e["tier"], dict(files=0, bytes=0))
        t["files"] += 1
        t["bytes"] += e["bytes"]
    cat = dict(frozen_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), tiers=tiers, files=entries)
    (ROOT / "catalog.json").write_text(json.dumps(cat, indent=1))
    for k, v in tiers.items():
        print(f"{k:14s} {v['files']:4d} files {v['bytes'] / 1e9:8.2f} GB")


if __name__ == "__main__":
    main()
