"""Plan or run the multi-source remote catalog. Does not train.

Default is plan-only: no download. Pass --fetch ID to acquire one block
on the current machine. --auto-fetch is for a remote runtime after preflight;
it is ignored on the laptop so 65.8 GiB cannot start here by accident.

    scripts/py.cmd scripts/68_remote_catalog.py --out reports/remote_catalog_2026-09-15
    scripts/py.cmd scripts/68_remote_catalog.py --out reports/remote_catalog_plan --fetch k562_gwps_raw_singlecell
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.remote_catalog import run_catalog

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=None)
    parser.add_argument("--select", nargs="*", default=None,
                        help="block ids to plan; default: catalog default_order")
    parser.add_argument("--fetch", nargs="*", default=None,
                        help="block ids that may download; default: none")
    parser.add_argument("--disk-floor-gib", type=float, default=None)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument(
        "--auto-fetch", action="store_true",
        help="remote only: fetch the next fitting block after preflight",
    )
    parser.add_argument(
        "--allow-ephemeral-large", action="store_true",
        help="allow a >8 GiB fetch onto a disk that dies with the session",
    )
    args = parser.parse_args()
    if args.plan_only:
        fetch_ids: list[str] = []
        auto = False
        plan_only = True
    elif args.fetch:
        fetch_ids = list(args.fetch)
        auto = False
        plan_only = False
    else:
        fetch_ids = []
        auto = bool(args.auto_fetch)
        plan_only = not auto
    report = run_catalog(
        out=args.out,
        repo=REPO,
        fetch_ids=fetch_ids,
        select_ids=args.select,
        catalog_path=args.catalog,
        disk_floor_gib=args.disk_floor_gib,
        plan_only=plan_only,
        auto_fetch=auto,
        allow_ephemeral_large=args.allow_ephemeral_large,
    )
    print(f"wrote {args.out / 'catalog_run.json'}")
    print(f"runtime {report['paths']['runtime']}  persist {report['persist_kind']['kind']}")
    print(f"disk free GiB {report['preflight']['disk_free_bytes'] / 1024**3:.2f}  "
          f"RAM avail GiB {None if report['preflight']['ram_available_bytes'] is None else report['preflight']['ram_available_bytes'] / 1024**3:.2f}")
    for row in report["blocks"]:
        plan = row["plan"]
        print(f"  {plan['block_id']:28} {row['status']:16} {plan['reason']}")


if __name__ == "__main__":
    main()
