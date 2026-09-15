"""Run the remote-ingest contract, or pack the tiny upload bundle.

The notebook `notebooks/remote_ingest_hepg2.ipynb` calls the same functions.
This script is what we can execute locally without Kaggle CLI.

    scripts/py.cmd scripts/67_remote_ingest.py --out reports/remote_2026-09-15
    scripts/py.cmd scripts/67_remote_ingest.py --prepare-bundle C:/Users/ferra/vcc2026-data/interim/remote_bundle

Multi-source Colab ingest is `scripts/68_remote_catalog.py` and the same notebook.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.remote_ingest import prepare_upload_bundle, run_job

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--prepare-bundle", type=Path, default=None)
    parser.add_argument("--fetch-jiang", action="store_true")
    parser.add_argument("--download-hepg2", action="store_true",
                        help="fetch HepG2 from Zenodo even if a local copy exists")
    parser.add_argument("--disk-floor-gib", type=float, default=None)
    args = parser.parse_args()

    if args.prepare_bundle is not None:
        record = prepare_upload_bundle(args.prepare_bundle, repo=REPO)
        print(json.dumps(record, indent=2, default=str))
        return
    if args.out is None:
        raise SystemExit("need --out or --prepare-bundle")
    report = run_job(
        out=args.out,
        repo=REPO,
        skip_hepg2_download=not args.download_hepg2,
        fetch_jiang=args.fetch_jiang,
        disk_floor_gib=args.disk_floor_gib,
    )
    parity = report.get("hepg2_parity") or {}
    print(f"wrote {args.out / 'remote_ingest.json'}")
    print(f"runtime {report['paths']['runtime']}  remote={report['paths']['remote']}")
    print(f"hepg2 parity ok: {parity.get('ok')}  md5 {parity.get('md5')}")
    print(f"resume interrupted at {report['resume_selftest']['interrupted_at']} "
          f"done={report['resume_selftest']['resumed_done']}")
    print(f"jiang: {report['jiang_tgfb']['decision']} — {report['jiang_tgfb']['reason']}")


if __name__ == "__main__":
    main()
