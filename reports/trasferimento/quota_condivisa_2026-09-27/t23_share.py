"""The per-gene shared share for the t23 recipe: sigma2 / (sigma2 + tau2) from every complete universe.

The panel bench (share_panel_bench.py, r1) passed its rule with the share estimated on the universes of
the families not held out. The recipe uses the same function (`share_panel_bench.shared_share`: the atlas
bench's moments and blend, CD4's SE variance x 2, targets outside the panel measured in at least two
universes) on every universe complete when t23 was built: K562, CD4 and HCT116 (HEK293T was still
streaming). A gene the universes cannot estimate (measured in fewer than two of them, or without SE)
gets share 0, as in the bench: its transferred value is dropped and only the cis head can move it.
Writes share.csv (gene, share on the official axis) and manifest.json to --out.

    scripts/py.cmd reports/trasferimento/quota_condivisa_2026-09-27/t23_share.py --out reports/trasferimento/quota_condivisa_2026-09-27/t23 \
        --universe k562=<dir> --universe cd4_mix=<dir> --universe orion_hct116=<dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from share_panel_bench import DATA, SEED, Universe, official_axis, shared_share  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", action="append", required=True, metavar="NAME=DIR")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--max-estimation-targets", type=int, default=6000)
    ap.add_argument("--cd4-se-factor", type=float, default=2.0)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = np.asarray(official_axis().symbols)
    panel = set(pd.read_csv(args.panel).iloc[:, 0].astype(str))
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    unis = {}
    for spec in args.universe:
        name, _, folder = spec.partition("=")
        unis[name] = Universe(name, Path(folder))
    share, info = shared_share(unis, list(unis), panel, basal, axis.size, args.cd4_se_factor,
                               args.max_estimation_targets, np.random.default_rng(SEED))
    out_csv = args.out / "share.csv"
    pd.DataFrame({"gene": axis, "share": share}).to_csv(out_csv, index=False, float_format="%.6g")
    manifest = {"script": "reports/trasferimento/quota_condivisa_2026-09-27/t23_share.py",
                "written_utc": datetime.now(timezone.utc).isoformat(),
                "universes": {n: str(u.folder) for n, u in unis.items()}, "seed": SEED,
                "max_estimation_targets": args.max_estimation_targets, "cd4_se_factor": args.cd4_se_factor,
                **info, "genes_share_zero": int((share == 0).sum()), "genes_share_one": int((share == 1).sum()),
                "share_csv_sha256": hashlib.sha256(out_csv.read_bytes()).hexdigest()}
    with (args.out / "manifest.json").open("x", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    print(json.dumps({k: v for k, v in manifest.items() if k != "universes"}, indent=1))


if __name__ == "__main__":
    main()
