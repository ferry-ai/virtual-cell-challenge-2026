r"""Download public perturbation datasets into data_root/external.

Defaults to the pseudobulk files, which are what the transfer model trains on
and total well under a gigabyte. The single-cell files are 8-66 GB each and are
only needed for the held-out line that cell-eval2 scores.

Usage:
    .\scripts\py.cmd scripts\10_fetch_external.py                  # default set
    .\scripts\py.cmd scripts\10_fetch_external.py --list
    .\scripts\py.cmd scripts\10_fetch_external.py rpe1_raw_singlecell
"""

from __future__ import annotations

import argparse

from vcc2026.config import paths
from vcc2026.external import REGISTRY, fetch

DEFAULT = ["k562_gwps_raw_bulk", "rpe1_raw_bulk", "k562_essential_raw_bulk"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("keys", nargs="*", help="registry keys to fetch")
    ap.add_argument("--list", action="store_true", help="show the registry and exit")
    ap.add_argument("--no-verify", action="store_true", help="skip md5 verification")
    args = ap.parse_args()

    if args.list:
        for key, entry in sorted(REGISTRY.items(), key=lambda kv: kv[1].size):
            mark = " *" if key in DEFAULT else "  "
            print(f"{mark}{key:<40} {entry.size_gb:8.2f} GB  {entry.name}")
        print("\n* = fetched by default")
        return

    keys = args.keys or DEFAULT
    unknown = [k for k in keys if k not in REGISTRY]
    if unknown:
        raise SystemExit(f"unknown key(s): {unknown}\nrun with --list to see the registry")

    total = sum(REGISTRY[k].size for k in keys) / 1024**3
    print(f"fetching {len(keys)} file(s), {total:.2f} GB total\n")

    for key in keys:
        fetch(key, paths().external, verify=not args.no_verify)


if __name__ == "__main__":
    main()
