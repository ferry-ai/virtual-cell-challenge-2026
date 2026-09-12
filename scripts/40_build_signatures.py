"""Stage 1 of the pipeline: registry -> selection -> ingestion -> QC -> signatures.

Reads every enabled local source from `configs/sources.yaml`, builds one
signature per perturbation row on the official 18,533-gene axis with a standard
error and a cell count, and writes a QC report that records every exclusion.

Nothing here is a model. The point of the stage is that the representation
everything downstream consumes is built once, with its uncertainty, and that
the count of rows dropped for each reason is written down rather than inferred.

    scripts/py.cmd scripts/40_build_signatures.py --run-id e001
    scripts/py.cmd scripts/40_build_signatures.py --run-id e001 --sources k562_gwps

Outputs (under the artifact root, or --out):
    <run>/signatures/<source>.npz + .rows.json
    <run>/signature_qc.json
    <run>/manifest_40_build_signatures.json
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
from vcc2026.pseudobulk import PseudobulkFile
from vcc2026.registry import VerificationLevel, load_registry
from vcc2026.signatures import SignatureSet


def panel_targets() -> set[str]:
    csv = config.paths().raw / "controls" / "pert_counts.csv"
    return set(pd.read_csv(csv).target_gene.astype(str))


def open_source(source) -> PseudobulkFile:
    path = config.paths().data_root / source.local_path
    if not path.exists():
        raise FileNotFoundError(f"{source.id}: {path} is missing")
    return PseudobulkFile(
        path=path, source_id=source.id, context=source.cell_context or source.id
    )


def select_targets(files, panel: set[str], mode: str) -> tuple[set[str] | None, dict]:
    """Decide which targets to materialise, before reading any expression.

    A signature set is dense on the 18,533-gene axis, so its memory is linear in
    the number of targets kept: all 9,866 K562 rows would be ~4.7 GB across
    delta and se, on a machine with 7.8 GB total. Selecting first is what makes
    the stage run here at all, and the census that drives it reads only obs.

    Modes:
        panel         -- the 300 competition targets only.
        panel+shared  -- the panel plus every target measured in at least two
                         sources, which is exactly the set on which transfer can
                         be *measured* rather than assumed. The default.
        all           -- everything; expect several GB of RAM.
    """
    census = {f.source_id: f.target_census() for f in files}
    if mode == "all":
        return None, {"mode": mode, "per_source_targets": {k: len(v) for k, v in census.items()}}

    keep = set(panel)
    shared: set[str] = set()
    ids = list(census)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            shared |= set(census[a]) & set(census[b])
    if mode == "panel+shared":
        keep |= shared
    elif mode != "panel":
        raise ValueError(f"unknown targets mode: {mode!r}")

    return keep, {
        "mode": mode,
        "per_source_targets": {k: len(v) for k, v in census.items()},
        "n_panel": len(panel),
        "n_shared_across_sources": len(shared),
        "n_selected": len(keep),
        "rationale": (
            "Targets measured in two or more sources are the only ones on which "
            "cross-context transfer can be measured; the panel is what must "
            "ultimately be predicted."
        ),
    }


def build_one(pf: PseudobulkFile, *, min_cells: int, control: str,
              targets: set[str] | None) -> tuple[SignatureSet, dict]:
    describe = pf.describe()
    sigs, report = pf.load_signatures(
        targets=targets, min_cells=min_cells, control=control
    )
    report["describe"] = describe
    return sigs, report


def signature_qc(sigs: SignatureSet, panel: set[str]) -> dict:
    """Diagnostics that decide whether these estimates can carry a conclusion."""
    delta, se, obs, targets = sigs.stack()
    if len(sigs) == 0:
        return {"n_signatures": 0}
    good = obs & np.isfinite(delta) & np.isfinite(se) & (se > 0)
    z = np.zeros_like(delta)
    z[good] = delta[good] / se[good]

    on_panel = np.array([t in panel for t in targets])
    per_row_strong = (np.abs(z) > 2).sum(axis=1)

    return {
        "n_signatures": len(sigs),
        "n_targets": len(sigs.targets),
        "n_panel_targets": int(len({t for t in targets if t in panel})),
        "n_signatures_on_panel": int(on_panel.sum()),
        "observed_genes_per_signature": float(np.median(obs.sum(axis=1))),
        "median_abs_delta": float(np.median(np.abs(delta[good]))),
        "median_se": float(np.median(se[good])),
        "median_abs_delta_over_se": float(
            np.median(np.abs(delta[good])) / np.median(se[good])
        ),
        "median_genes_with_abs_z_gt_2": float(np.median(per_row_strong)),
        "median_genes_with_abs_z_gt_2_panel": (
            float(np.median(per_row_strong[on_panel])) if on_panel.any() else None
        ),
        "frac_signatures_with_no_strong_gene": float(np.mean(per_row_strong == 0)),
        "median_n_cells": float(np.median([s.n_cells for s in sigs])),
        "interpretation": (
            "median_abs_delta_over_se below 1 means the typical gene-level effect in "
            "this source is smaller than its own sampling error. That bounds what any "
            "transfer from it can achieve, and it is a property of the SOURCE's power, "
            "not a measurement of how large the true effects in A/B/C are."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", default="e001")
    p.add_argument("--out", type=Path, default=None,
                   help="output directory; defaults to <artifact_root>/<run-id>")
    p.add_argument("--sources", nargs="*", default=None,
                   help="source ids; default is every enabled local source")
    p.add_argument("--min-cells", type=int, default=10,
                   help="drop rows backed by fewer cells (a measurement filter, "
                        "never an evaluation filter -- see D-011)")
    p.add_argument("--control", default="non-targeting",
                   choices=["non-targeting", "core_control"])
    p.add_argument("--targets", default="panel+shared",
                   choices=["panel", "panel+shared", "all"],
                   help="which targets to materialise; see select_targets()")
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    out_dir = args.out or config.run_dir(args.run_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    sig_dir = out_dir / "signatures"
    sig_dir.mkdir(exist_ok=True)

    registry = load_registry()
    problems = [x for x in registry.verify(Path(__file__).resolve().parents[1])
                if "signature_qc.json" not in x]
    if problems:
        raise SystemExit("registry inconsistent:\n  " + "\n  ".join(problems))

    wanted = set(args.sources) if args.sources else None
    selected = [
        s for s in registry.enabled()
        if s.local_path and s.verification >= VerificationLevel.USABLE
        and s.local_path.endswith(".h5ad")
        and (wanted is None or s.id in wanted)
    ]
    if not selected:
        raise SystemExit("no enabled local pseudobulk source matched the selection")

    axis = official_axis()
    panel = panel_targets()
    print(f"official axis: {len(axis)} genes; panel: {len(panel)} targets")
    print(f"selected {len(selected)} source(s): {[s.id for s in selected]}\n")

    files = [open_source(s) for s in selected]
    targets, selection = select_targets(files, panel, args.targets)
    print(f"target selection ({selection['mode']}): "
          f"{selection.get('n_selected', 'all')} targets"
          + (f"  [panel {selection['n_panel']} + shared "
             f"{selection['n_shared_across_sources']}]" if targets else ""))
    print(f"  per-source targets available: {selection['per_source_targets']}\n")

    man = RunManifest(run_id=args.run_id, stage="40_build_signatures",
                      config=vars(args) | {"registry_version": registry.version,
                                           "target_selection": selection},
                      seed=None)
    man.add_input("gene_axis", config.paths().raw / "controls" / "gene_names.csv")
    man.add_input("panel", config.paths().raw / "controls" / "pert_counts.csv")

    qc_all = {"_target_selection": selection}
    for source, pf in zip(selected, files):
        print(f"--- {source.id} ({source.cell_context})")
        sigs, report = build_one(pf, min_cells=args.min_cells,
                                 control=args.control, targets=targets)
        qc = signature_qc(sigs, panel)
        qc_all[source.id] = {"ingestion": report, "qc": qc}

        dest = sig_dir / f"{source.id}.npz"
        if dest.exists() and not args.allow_overwrite:
            raise SystemExit(f"{dest} exists; pass --allow-overwrite or use a new --run-id")
        sigs.write_npz(dest)

        man.add_input(f"source:{source.id}", config.paths().data_root / source.local_path)
        man.add_output(f"signatures:{source.id}", dest)
        print(f"    rows used {report['n_perturbation_rows_used']:>6} of {report['n_rows_total']}"
              f"   controls {report['n_control_rows_used']}")
        print(f"    axis genes observed {report['n_axis_genes_observed']:>6}"
              f"   off-axis source genes {report['n_source_genes_off_axis']}")
        print(f"    panel targets {qc['n_panel_targets']:>3}"
              f"   median|d|/se {qc['median_abs_delta_over_se']:.3f}"
              f"   median genes |z|>2 {qc['median_genes_with_abs_z_gt_2']:.0f}")
        print(f"    signatures with no strong gene: "
              f"{qc['frac_signatures_with_no_strong_gene']:.1%}\n")

    qc_path = out_dir / "signature_qc.json"
    if qc_path.exists() and not args.allow_overwrite:
        raise SystemExit(f"{qc_path} exists; use a new --run-id")
    qc_path.write_text(json.dumps(qc_all, indent=2, default=str), encoding="utf-8")
    man.add_output("signature_qc", qc_path)
    man.metrics = {k: v["qc"] for k, v in qc_all.items() if k != "_target_selection"}
    man.note("Signatures are pseudobulk contrasts. They estimate a mean response and "
             "cannot produce a VCC score, which needs single-cell counts.")
    man.note("min_cells filters what counts as a measurement; it is not applied to the "
             "evaluation set, where weak and null targets must remain (D-011).")
    man.write(out_dir / "manifest_40_build_signatures.json",
              allow_overwrite=args.allow_overwrite)

    print(f"-> {qc_path}")
    print(f"-> {out_dir / 'manifest_40_build_signatures.json'}")


if __name__ == "__main__":
    main()
