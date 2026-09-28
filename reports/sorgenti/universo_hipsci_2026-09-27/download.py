"""Download the HIPSCI CRISPRi records from Figshare (MIT), file by file, each checked against its published md5.

Feng et al. 2025, "A genome-scale single cell CRISPRi map of trans gene regulation across many human
pluripotent stem cell lines": Figshare articles 26819743 (log fold-change tables, correlations, scripts) and
27989294 (per-cell RNA and guide UMI counts, cell metadata). The owner's go of 27/09 covers both
(reports/sorgenti/ricerca_sorgenti_2026-09-27/RISULTATI.md). The file list, sizes and md5 come from the Figshare API
at run time; a file already present with the right md5 is skipped; a download goes to `<name>.part` and is
renamed only after its md5 matches. Writes `manifest.json` (API metadata, local sha256) into --out.

    scripts/py.cmd reports/sorgenti/universo_hipsci_2026-09-27/download.py --out <data_root>/external/hipsci
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ARTICLES = (26819743, 27989294)


def digest(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fetch(client: httpx.Client, url: str, dest: Path, size: int, md5: str, tries: int = 5) -> None:
    part = dest.with_name(dest.name + ".part")
    for attempt in range(1, tries + 1):
        try:
            have = part.stat().st_size if part.exists() else 0
            headers = {"Range": f"bytes={have}-"} if have else {}
            with client.stream("GET", url, headers=headers) as r:
                if have and r.status_code != 206:
                    part.unlink()
                    have = 0
                    continue
                r.raise_for_status()
                with part.open("ab" if have else "wb") as fh:
                    for chunk in r.iter_bytes(4 * 1024 * 1024):
                        fh.write(chunk)
            if part.stat().st_size != size:
                raise IOError(f"{dest.name}: {part.stat().st_size} bytes, expected {size}")
            if digest(part, "md5") != md5:
                part.unlink()
                raise IOError(f"{dest.name}: md5 mismatch, part removed")
            part.rename(dest)
            return
        except (httpx.HTTPError, IOError) as exc:
            print(f"  attempt {attempt} failed: {exc}", flush=True)
            time.sleep(min(60, 5 * attempt))
    raise SystemExit(f"{dest.name}: gave up after {tries} attempts")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(timeout=120, follow_redirects=True)
    records = []
    for art in ARTICLES:
        meta = client.get(f"https://api.figshare.com/v2/articles/{art}").json()
        records.append({"article": art, "title": meta["title"], "license": meta["license"]["name"],
                        "doi": meta.get("doi"), "files": meta["files"]})
    todo = [f for r in records for f in r["files"]]
    print(f"{len(todo)} files, {sum(f['size'] for f in todo) / 1e9:.2f} GB", flush=True)
    for f in sorted(todo, key=lambda f: f["size"]):
        dest = args.out / f["name"]
        if dest.exists() and dest.stat().st_size == f["size"] and digest(dest, "md5") == f["computed_md5"]:
            print(f"skip {f['name']} (present, md5 ok)", flush=True)
            continue
        t0 = time.time()
        fetch(client, f["download_url"], dest, f["size"], f["computed_md5"])
        print(f"got {f['name']}: {f['size'] / 1e9:.2f} GB in {time.time() - t0:.0f} s", flush=True)
    for r in records:
        for f in r["files"]:
            f["local_sha256"] = digest(args.out / f["name"], "sha256")
    manifest = {"script": "reports/sorgenti/universo_hipsci_2026-09-27/download.py",
                "finished_utc": datetime.now(timezone.utc).isoformat(), "records": records}
    with (args.out / "manifest.json").open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    print("done", flush=True)


if __name__ == "__main__":
    main()
