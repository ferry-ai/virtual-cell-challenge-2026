"""F2 of R-V2: production-form effects for a HepG2 bench scored with the real metrics (stage 75).

Stage 75 scores arms against real HepG2 cells (Nadig 2024) with the six members of the
scorer and local anchors (truth = half A, replicate = half B). It reads effects computed
elsewhere through ``--effects NAME=PATH``. This writes three such files, for 300 HepG2 targets
with >= 50 cells that K562 genome-wide also screened (seeded draw), built with the production
code and only K562 as the source (HepG2 targets are essential genes, which the stage-98 CD4
and Orion extractions do not cover):

* ``t16like``: stage 98's K562 table, raw effects, `mix` with gamma 1, x 0.788;
* ``t19like``: the same with the z-shrunk effects, x 1.576;
* ``t20like``: t19like plus stage 100's cis head (`add_cis`, 2 x the median prior within 5 kb),
  with the prior fitted after removing these 300 targets from the K562 pairs.

    scripts/py.cmd reports/banco_hepg2_v2_2026-09-26/build_effects.py --out <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.multisource import mix  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402
from vcc2026.sc_stream import read_frame  # noqa: E402


def load_stage(num: int, name: str):
    spec = importlib.util.spec_from_file_location(f"stage{num}", REPO / "scripts" / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


stage98 = load_stage(98, "98_multisource_effects.py")
stage100 = load_stage(100, "100_build_context_effects.py")
DATA = config.paths().data_root
SEED = 20260926


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hepg2", type=Path, default=DATA / "raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad")
    ap.add_argument("--bulk", type=Path, default=DATA / "external/K562_gwps_raw_bulk_01.h5ad")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--pairs", type=Path, default=REPO / "reports/cis_2026-09-17/k562_neighbour_pairs.csv")
    ap.add_argument("--n-targets", type=int, default=300)
    ap.add_argument("--min-cells", type=int, default=50)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)

    with h5py.File(args.hepg2, "r") as f:
        genes_h = read_frame(f["obs"])["gene"].astype(str)
    counts = genes_h.value_counts()
    with h5py.File(args.bulk, "r") as f:
        labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
    k562 = {lab.split("_")[1] for lab in labels if "non-targeting" not in lab}
    eligible = sorted(t for t, n in counts.items() if t != "non-targeting" and n >= args.min_cells and t in k562)
    rng = np.random.default_rng(SEED)
    targets = sorted(rng.choice(eligible, size=args.n_targets, replace=False).tolist())
    (args.out / "targets.txt").write_text("\n".join(targets) + "\n", encoding="utf-8")

    axis = np.asarray(official_axis().symbols)
    tab = stage98.k562_table(args.bulk, targets, axis)
    targets = [t for t in targets if t in set(tab.targets)]
    (args.out / "targets.txt").write_text("\n".join(targets) + "\n", encoding="utf-8")
    raw_tab = stage98.AxisTable(tab.name, tab.targets, tab.raw, tab.raw, tab.se, tab.n_cells, tab.meta)
    arms = {}
    eff_raw, w_raw = mix([raw_tab], targets, weights={"k562": 1.0}, gamma=1.0, reliability_scale=100.0)
    arms["t16like"] = eff_raw * 0.788
    eff_sh, w_sh = mix([tab], targets, weights={"k562": 1.0}, gamma=1.0, reliability_scale=100.0)
    arms["t19like"] = eff_sh * 1.576
    t20 = arms["t19like"].copy()
    observed = w_sh > 0
    model = stage100.cis_prior(pd.read_csv(args.pairs), targets)
    counts_cis = stage100.add_cis(t20, observed, targets, axis, model, load_coordinates(args.coords), 5000, 2.0)
    arms["t20like"] = t20
    files = {}
    for name, eff in arms.items():
        path = args.out / f"{name}.npz"
        np.savez_compressed(path, targets=np.array(targets), genes=axis, lfc=eff.astype(np.float32))
        files[name] = {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                       "median_abs_q99": float(np.median(np.quantile(np.abs(eff), 0.99, axis=1)))}
    manifest = {"stage": "banco_hepg2_v2_2026-09-26/build_effects.py", "seed": SEED, "eligible": len(eligible),
                "targets": len(targets), "cis": counts_cis, "cis_prior_ln": model.by_bin.tolist(), "files": files,
                "claim_type": "inputs of a bench, not results"}
    with (args.out / "manifest.json").open("x", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
