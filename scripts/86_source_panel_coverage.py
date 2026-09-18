"""Stage 86: how much of a bench panel does a transfer source actually cover?

Stage 75 picks its HepG2 targets from ``eligible = HepG2 targets with >= min-cells
cells AND present in the source``. Two different sources therefore produce two
different benches, and their raw numbers are not comparable. This stage measures,
without running a bench, what each source covers:

* how many HepG2 targets it can speak for (target coverage);
* how many HepG2 genes it measured (gene coverage -- everything else is left at
  zero by ``assemble_log_fc``, so it caps how much of the profile can move);
* how many cells stand behind each of its targets (the transfer's own noise).

It also emits the intersection of the sources' target pools -- the panel a matched
comparison has to be run on -- and replicates stage 75's own draw from each pool, with
and without ``--targets-file``, so the cost of not pinning it is a number and not an
argument.

    python scripts/86_source_panel_coverage.py --hepg2 <h5ad> \
        --source k562=<bulk h5ad> --source rpe1=<bulk h5ad> --out <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.sc_stream import read_frame  # noqa: E402

NTC = "non-targeting"


def bulk_source(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Target symbols, per-row filtered cell counts and gene names -- as stage 75 reads them."""
    with h5py.File(path, "r") as f:
        labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
        n_cells = f["obs/num_cells_filtered"][:]
        genes = read_frame(f["var"])["gene_name"].astype(str).to_numpy()
    is_ntc = np.array([NTC in lab for lab in labels])
    sym = np.array([NTC if nt else lab.split("_")[1] for lab, nt in zip(labels, is_ntc)])
    return sym, np.where(np.isfinite(n_cells), n_cells, 0.0), genes


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hepg2", type=Path, required=True)
    p.add_argument("--source", action="append", required=True, metavar="NAME=PATH",
                   help="a Replogle *_raw_bulk_01.h5ad, named; repeatable")
    p.add_argument("--min-cells", type=int, default=50)
    p.add_argument("--n-targets", type=int, default=300, help="stage-75 panel size, for the selection check")
    p.add_argument("--seed", type=int, default=2026, help="stage-75 seed, for the selection check")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.out / "coverage.json").exists():
        raise SystemExit(f"{args.out} already holds a coverage report; choose a new --out")

    with h5py.File(args.hepg2, "r") as f:
        obs = read_frame(f["obs"])
        var = read_frame(f["var"])
    hepg2_genes = pd.unique(var.index.astype(str).to_numpy())
    sym = obs["gene"].astype(str).to_numpy()
    counts = pd.Series(sym[sym != NTC]).value_counts()
    hepg2_eligible = sorted(counts.index[counts >= args.min_cells])
    print(f"HepG2: {len(hepg2_genes)} genes, {counts.size} targets, "
          f"{len(hepg2_eligible)} with >= {args.min_cells} cells")

    per_source, pools = {}, {}
    for spec in args.source:
        name, _, path = spec.partition("=")
        s_sym, s_cells, s_genes = bulk_source(Path(path))
        targets = sorted(set(s_sym[s_sym != NTC]))
        covered = sorted(set(hepg2_eligible) & set(targets))
        pools[name] = set(covered)
        cells = pd.Series(s_cells[s_sym != NTC]).groupby(pd.Series(s_sym[s_sym != NTC])).sum()
        on_panel = cells.reindex(covered).dropna()
        gene_hit = np.isin(hepg2_genes, np.asarray(s_genes))
        per_source[name] = {
            "path": str(path),
            "n_rows": int(s_sym.size),
            "n_ntc_rows": int((s_sym == NTC).sum()),
            "n_targets": len(targets),
            "n_source_genes": int(pd.unique(np.asarray(s_genes)).size),
            "hepg2_genes_measured": int(gene_hit.sum()),
            "hepg2_gene_coverage": float(gene_hit.mean()),
            "hepg2_targets_covered": len(covered),
            "hepg2_target_coverage": float(len(covered) / max(len(hepg2_eligible), 1)),
            "cells_per_covered_target": {
                "median": float(np.median(on_panel.to_numpy())) if on_panel.size else None,
                "q10_q90": [float(np.quantile(on_panel.to_numpy(), q)) for q in (0.1, 0.9)]
                if on_panel.size else None,
            },
        }
        print(f"{name}: {len(targets)} targets, covers {len(covered)}/{len(hepg2_eligible)} of the HepG2 panel, "
              f"{gene_hit.sum()}/{len(hepg2_genes)} HepG2 genes, "
              f"median {per_source[name]['cells_per_covered_target']['median']} cells/target")

    shared = sorted(set.intersection(*pools.values())) if pools else []
    union = sorted(set.union(*pools.values())) if pools else []
    print(f"shared panel: {len(shared)} targets ({len(union)} in the union)")

    # What that costs a comparison: replicate stage 75's draw, with and without the pin.
    selection = {}
    for restrict in (False, True):
        picks = {}
        for name, pool in pools.items():
            rng = np.random.default_rng(args.seed)
            elig = sorted(pool if not restrict else (pool & set(shared)))
            picks[name] = sorted(rng.choice(elig, size=min(args.n_targets, len(elig)),
                                            replace=False).tolist())
        sets = [set(v) for v in picks.values()]
        key = "with_targets_file" if restrict else "without_targets_file"
        selection[key] = {
            "eligible": {n: len(pools[n] if not restrict else pools[n] & set(shared)) for n in picks},
            "identical": len({tuple(v) for v in picks.values()}) == 1,
            "in_common": len(set.intersection(*sets)),
            "n_drawn": {n: len(v) for n, v in picks.items()},
        }
        print(f"stage-75 draw (seed {args.seed}, n={args.n_targets}) {key}: "
              f"identical={selection[key]['identical']} in_common={selection[key]['in_common']}")

    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage": "86_source_panel_coverage",
        "args": {k: str(v) for k, v in vars(args).items()},
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "hepg2": {"n_genes": int(len(hepg2_genes)), "n_targets": int(counts.size),
                  "n_eligible": len(hepg2_eligible), "min_cells": args.min_cells},
        "sources": per_source,
        "shared_panel_size": len(shared),
        "union_panel_size": len(union),
        "stage75_selection": selection,
    }
    (args.out / "coverage.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (args.out / "shared_targets.txt").write_text("\n".join(shared) + "\n", encoding="utf-8")
    for name, pool in pools.items():
        (args.out / f"targets_{name}.txt").write_text("\n".join(sorted(pool)) + "\n", encoding="utf-8")
    print(f"wrote {args.out / 'coverage.json'}")


if __name__ == "__main__":
    main()
