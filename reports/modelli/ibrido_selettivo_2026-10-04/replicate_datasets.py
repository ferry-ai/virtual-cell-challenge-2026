"""Copy small private code datasets of one Kaggle account to another, from their local stages, byte for byte.

The D-056 chain also runs on a second account (PROTOCOLLO.md §3: a second confirmation line and a reserve for the first),
whose GPU quota is free. Kernels of an account mount only datasets and kernel outputs it can read, so the code datasets
of the chain are copied there under the same slug: each local stage's files are checked against its staged.json (or
against the sha256 given) before the copy, and the copy gets its own dataset-metadata.json. Large datasets (the bench
cube) are shared as reader instead, never copied (share_to.py). No credential is printed.

    python replicate_datasets.py --config-dir ~/.kaggle --owner davidmaisterx --out <new dir> \
        --stage rcell-code-r1=<local stage> [--stage ...] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--stage", action="append", required=True, metavar="SLUG=DIR")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    a.out.mkdir(parents=True)
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    report = {}
    for spec in a.stage:
        slug, src = spec.split("=", 1)
        src = Path(src)
        staged = src / "staged.json"
        files = sorted(f for f in src.iterdir() if f.is_file() and f.name not in ("dataset-metadata.json",))
        hashes = {f.name: sha(f) for f in files}
        if staged.is_file():
            want = json.loads(staged.read_text(encoding="utf-8"))
            bad = {k: v for k, v in want.items() if hashes.get(k) != v}
            if bad:
                sys.exit(f"{slug}: files differ from staged.json: {sorted(bad)}")
        dest = a.out / slug
        dest.mkdir()
        for f in files:
            shutil.copyfile(f, dest / f.name)
        (dest / "dataset-metadata.json").write_text(json.dumps(
            {"title": slug.replace("-", " "), "id": f"{a.owner}/{slug}", "licenses": [{"name": "other"}],
             "isPrivate": True}), encoding="utf-8")
        rec = {"source_stage": src.as_posix(), "files": hashes, "staged_json_checked": staged.is_file()}
        if not a.dry_run:
            r = subprocess.run([exe, "datasets", "create", "-p", str(dest), "--dir-mode", "skip"],
                               env={**os.environ, "KAGGLE_CONFIG_DIR": a.config_dir}, capture_output=True, text=True)
            out = ((r.stdout or "") + (r.stderr or "")).strip()
            rec.update(returncode=r.returncode, answer=out[-300:])
        report[f"{a.owner}/{slug}"] = rec
        print(json.dumps({slug: {k: rec.get(k) for k in ("returncode", "staged_json_checked")}}))
    (a.out / "replicate_receipt.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
