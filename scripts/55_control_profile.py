"""Basal NTC profile of a single-cell source, saved for the benchmark to load.

`extract_control_profile` reads a Replogle-style pseudobulk file, whose obs
carries `gene_transcript` and `num_cells_filtered`. A harmonised single-cell
mirror has neither. The profile itself is the same quantity either way -- the
cell-weighted NTC mean as log1p CPM on the official axis -- so it is built here
once and written next to the signatures instead of teaching the benchmark two
file formats.

Only the NTC rows are read: 4,976 of 145,473 cells for HepG2, so this is a
fraction of a full pass.

    scripts/py.cmd scripts/55_control_profile.py --source-id nadig_hepg2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import h5py
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.genes import align_to_axis, official_axis
from vcc2026.manifest import RunManifest
from vcc2026.pseudobulk import _read_categorical
from vcc2026.registry import load_registry


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", default="nadig_hepg2")
    parser.add_argument("--h5ad", type=Path, default=None)
    parser.add_argument("--perturbation-column", default="perturbation")
    parser.add_argument("--ntc-level", default="control")
    parser.add_argument("--out", type=Path, default=None,
                        help="defaults to the e003 signature directory")
    parser.add_argument("--block-rows", type=int, default=512)
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()

    registry = load_registry()
    source = registry[args.source_id]
    path = args.h5ad or (config.paths().data_root / source.local_path)
    out_dir = args.out or (config.paths().data_root / "artifacts" / "e003" / "signatures")
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{args.source_id}.control_profile.npz"
    if dest.exists() and not args.allow_overwrite:
        raise FileExistsError(f"{dest} exists; give a new --out")

    axis = official_axis()
    with h5py.File(path, "r") as handle:
        labels = np.asarray(
            _read_categorical(handle["obs"], args.perturbation_column), dtype=str
        )
        genes = np.asarray(_read_categorical(handle["var"], "gene_name"), dtype=str)
        rows = np.flatnonzero(labels == args.ntc_level)
        if rows.size == 0:
            raise SystemExit(
                f"no cell has {args.perturbation_column} == {args.ntc_level!r}; "
                f"nothing is assumed about which cells are controls"
            )
        counts = np.zeros(len(genes), dtype=np.float64)
        for lo in range(0, rows.size, args.block_rows):
            idx = rows[lo : lo + args.block_rows]
            block = np.asarray(handle["X"][int(idx.min()) : int(idx.max()) + 1, :],
                               dtype=np.float64)
            counts += block[idx - idx.min(), :].sum(axis=0)

    library = float(counts.sum())
    aligned = align_to_axis(counts[None, :], genes, ["control"],
                            duplicate_policy="sum", axis=axis)
    cpm = np.zeros(len(axis), dtype=np.float64)
    cpm[aligned.observed] = 1e6 * aligned.values[0, aligned.observed] / library
    log1p_cpm = np.log1p(cpm)

    np.savez_compressed(
        dest,
        log1p_cpm=log1p_cpm.astype(np.float64),
        observed=aligned.observed,
        n_cells=np.array(float(rows.size)),
        library=np.array(library),
        context=np.array(source.cell_context or args.source_id),
        source_id=np.array(args.source_id),
        provenance=np.array(
            f"NTC cells of {args.source_id} ({args.perturbation_column} == "
            f"{args.ntc_level!r}), cell-weighted mean, log1p CPM on the official "
            f"axis. Query-context NTCs are allowed inputs under the VCC task and "
            f"are given to every arm."
        ),
    )

    summary = {
        "source_id": args.source_id,
        "context": source.cell_context,
        "n_ntc_cells": int(rows.size),
        "library": library,
        "n_genes_observed": int(aligned.observed.sum()),
        "n_source_genes_off_axis": len(aligned.dropped),
        "path": str(dest),
    }
    (out_dir / f"{args.source_id}.control_profile.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    manifest = RunManifest(
        run_id=out_dir.parent.name, stage="55_control_profile",
        config={k: str(v) for k, v in vars(args).items()},
    )
    manifest.add_input("h5ad", path)
    manifest.add_output("profile", dest)
    manifest.metrics = summary
    manifest.note("Only NTC rows were read.")
    manifest.write(out_dir.parent / f"manifest_55_{args.source_id}.json",
                   allow_overwrite=args.allow_overwrite)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
