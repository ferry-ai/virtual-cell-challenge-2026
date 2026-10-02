"""Compare each private Kaggle dataset of the corpus with its publish receipt on Drive (names and bytes).

The file list and sizes come from the Kaggle API (server side), not from any local copy.
Receipts are small JSON files read from the Drive mount by name.
"""
import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path

SP = Path(__file__).parent
KAGGLE = r"C:\Users\ferra\vcc2026-data\.venv\Scripts\kaggle.exe"
DRIVE_RUNS = Path(r"G:\Il mio Drive\vcc2026\runs")
listing = [l.split("\t") for l in (SP / "inv/drive_listing.tsv").read_text(encoding="utf-8").splitlines()]
receipts = sorted(l[0] for l in listing if len(l) == 3 and "\\receipts\\" in l[0] and "publish_rlab-" in l[0])
latest = {}
for rel in receipts:  # later setup folders sort later; keep the last receipt per dataset
    d = json.loads((DRIVE_RUNS.parent / rel).read_text(encoding="utf-8"))
    latest[d["dataset"]] = (rel, d)
out_dir = SP / "inv/kaggle"
out_dir.mkdir(parents=True, exist_ok=True)
env = {**os.environ, "KAGGLE_CONFIG_DIR": str(Path.home() / ".kaggle")}


def kaggle_files(ref: str) -> list[dict]:
    rows, token = [], None
    while True:
        cmd = [KAGGLE, "datasets", "files", ref, "--csv", "--page-size", "200"] + (["--page-token", token] if token else [])
        p = subprocess.run(cmd, env=env, capture_output=True, text=True)
        text = p.stdout
        token = None
        lines = []
        for line in text.splitlines():
            if line.startswith("Next Page Token = "):
                token = line.split("=", 1)[1].strip()
            elif line.startswith("Warning:") or not line.strip():
                continue
            else:
                lines.append(line)
        rows += list(csv.DictReader(io.StringIO("\n".join(lines))))
        if not token:
            return rows


summary = []
for ref, (rel, d) in sorted(latest.items()):
    files = kaggle_files(ref)
    remote = {r["name"]: int(r["size"]) for r in files}
    expect = {f["file"]: f["bytes"] for f in d["files"]}
    missing = sorted(set(expect) - set(remote))
    size_diff = sorted(k for k in expect if k in remote and remote[k] != expect[k])
    extra = sorted(set(remote) - set(expect))
    rec = {"dataset": ref, "receipt": rel, "receipt_utc": d.get("utc"), "units": d.get("units"), "cells": d.get("cells"),
           "shards_expected": len(expect), "remote_files": len(remote), "missing": missing, "size_differs": size_diff,
           "extra_remote_files": extra, "bytes_expected": sum(expect.values())}
    summary.append(rec)
    (out_dir / f"{ref.split('/')[1]}.files.json").write_text(json.dumps(files, indent=0), encoding="utf-8")
    print(f"{ref:45s} shards {len(expect):4d} remote {len(remote):4d} missing {len(missing):3d} "
          f"size_differs {len(size_diff):3d} extra {extra}", flush=True)
(out_dir / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
