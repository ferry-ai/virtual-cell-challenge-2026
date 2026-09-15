"""Context x target census across every signature set on disk.

Answers, per context and per target, the three questions that decide what an
experiment can be run on: how many cells stand behind the estimate, what it was
compared with, and how many genes were actually measured. Observed and
sufficiently supported are separate columns on purpose -- a target seen in two
cells is observed and supports nothing.

    scripts/py.cmd scripts/54_context_target_table.py --out reports/hepg2_2026-09-14
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.genes import official_axis
from vcc2026.manifest import RunManifest
from vcc2026.registry import load_registry

SUPPORT_THRESHOLDS = (10, 30, 50)


def source_rows(signature_dir: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for rows in sorted(signature_dir.glob("*.rows.json")):
        out[rows.name.replace(".rows.json", "")] = json.loads(
            rows.read_text(encoding="utf-8")
        )
    return out


def measured_genes(npz: Path) -> dict:
    with np.load(npz) as handle:
        observed = np.asarray(handle["observed"])
    if observed.ndim == 1:
        return {"n_genes_measured": int(observed.sum()), "constant_across_targets": True}
    constant = bool(np.all(observed == observed[0]))
    return {
        "n_genes_measured": int(observed[0].sum()) if constant
        else int(np.median(observed.sum(axis=1))),
        "constant_across_targets": constant,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--signature-dirs", type=Path, nargs="*", default=None)
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    csv_path = args.out / "context_target_table.csv"
    json_path = args.out / "context_target_summary.json"
    for path in (csv_path, json_path):
        if path.exists() and not args.allow_overwrite:
            raise FileExistsError(f"{path} exists; give a new --out")

    root = config.paths().data_root / "artifacts"
    dirs = args.signature_dirs or [root / "e001" / "signatures", root / "e003" / "signatures"]
    registry = load_registry()

    records = []
    per_source_meta = {}
    for directory in dirs:
        for source_id, rows in source_rows(Path(directory)).items():
            npz = Path(directory) / f"{source_id}.npz"
            # SourceRegistry has __getitem__ and no __contains__: `in` would fall
            # back to iteration and quietly answer False, which is how the first
            # run of this script labelled every context with its source id.
            try:
                context = registry[source_id].cell_context or source_id
            except KeyError:
                context = source_id
            genes = measured_genes(npz) if npz.exists() else {}
            per_source_meta[source_id] = {
                "context": context,
                "signature_dir": str(directory),
                "n_rows": len(rows),
                **genes,
            }
            # Guide-level rows collapse to targets: the unit of every split.
            frame = pd.DataFrame(rows)
            grouped = frame.groupby("target", as_index=False).agg(
                n_cells=("n_cells", "sum"),
                n_control_cells=("n_control_cells", "max"),
                n_rows=("target", "size"),
            )
            grouped["source"] = source_id
            grouped["context"] = context
            grouped["n_genes_measured"] = genes.get("n_genes_measured")
            records.append(grouped)

    table = pd.concat(records, ignore_index=True)
    for threshold in SUPPORT_THRESHOLDS:
        table[f"supported_ge_{threshold}"] = table.n_cells >= threshold
    table = table[[
        "context", "source", "target", "n_cells", "n_rows", "n_control_cells",
        "n_genes_measured", *[f"supported_ge_{t}" for t in SUPPORT_THRESHOLDS],
    ]].sort_values(["context", "source", "target"])
    table.to_csv(csv_path, index=False)

    by_context: dict[str, dict] = {}
    for context, chunk in table.groupby("context"):
        by_context[str(context)] = {
            "sources": sorted(chunk.source.unique().tolist()),
            "n_targets_observed": int(chunk.target.nunique()),
            **{
                f"n_targets_ge_{t}_cells": int(
                    chunk.loc[chunk[f"supported_ge_{t}"], "target"].nunique()
                )
                for t in SUPPORT_THRESHOLDS
            },
            "median_cells_per_target": float(chunk.n_cells.median()),
            "n_genes_measured_by_source": {
                str(s): int(v) for s, v in
                chunk.groupby("source").n_genes_measured.first().items()
            },
        }

    contexts = sorted(by_context)
    sets = {c: set(table.loc[table.context == c, "target"]) for c in contexts}
    pairwise = {
        f"{a}&{b}": len(sets[a] & sets[b])
        for i, a in enumerate(contexts) for b in contexts[i + 1:]
    }
    all_three = set.intersection(*sets.values()) if len(sets) > 1 else set()

    panel_csv = config.paths().raw / "controls" / "pert_counts.csv"
    panel = set(pd.read_csv(panel_csv).target_gene.astype(str)) if panel_csv.exists() else set()

    summary = {
        "built_utc": pd.Timestamp.utcnow().isoformat(),
        "inclusion_criteria": {
            "row_unit": "one signature row per target (guide rows summed into the target)",
            "observed": "the source has at least one usable row for that target",
            "supported": "cells behind the estimate >= threshold; three thresholds are "
                         "reported because a single one hides the shape of the tail",
            "min_cells_already_applied": {
                "e001 pseudobulk sources": 10,
                "nadig_hepg2": 10,
            },
            "not_filtered_by_effect_size": True,
        },
        "per_source": per_source_meta,
        "per_context": by_context,
        "targets_shared_pairwise": pairwise,
        "targets_shared_all_contexts": len(all_three),
        "panel": {
            "n_panel_targets": len(panel),
            "panel_targets_per_context": {
                c: len(sets[c] & panel) for c in contexts
            },
            "note": "0 for a context means this experiment tests transfer between "
                    "contexts, not coverage of the VCC panel",
        },
        "genes": {
            "official_axis": len(official_axis()),
            "note": "a gene absent from a source's var is unmeasured, never unchanged",
        },
    }
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    manifest = RunManifest(
        run_id=args.out.name, stage="54_context_target_table",
        config={"signature_dirs": [str(d) for d in dirs]},
    )
    manifest.add_output("table", csv_path)
    manifest.add_output("summary", json_path)
    manifest.metrics = {
        "n_contexts": len(contexts),
        "targets_shared_all_contexts": len(all_three),
        "pairwise": pairwise,
    }
    manifest.note("Observed and supported are different columns and stay that way.")
    manifest.write(args.out / "manifest_54_context_target_table.json",
                   allow_overwrite=args.allow_overwrite)
    print(json.dumps(summary["per_context"], indent=2))
    print(json.dumps({"pairwise": pairwise, "all": len(all_three)}, indent=2))
    print(f"-> {csv_path}")


if __name__ == "__main__":
    main()
