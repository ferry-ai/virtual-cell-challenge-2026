"""Stage 3: run the REAL scorer end-to-end on a bundle where the truth is known.

This is the only stage that produces genuine VCC metrics, and it does so without
any perturbed data, by exploiting a fact about the official controls: the 18,400
control cells of each context carry 46 distinct NTC guide identities (`obs.ntc_id`).
Splitting those guides into disjoint groups manufactures "perturbations" whose
true effect is *known to be zero* -- different non-targeting guides in the same
cells.

Two things get measured that nothing else can measure yet:

1. **The false-positive floor.** Any differential expression the scorer calls
   between one NTC group and another is noise. Its size sets the level below
   which a real prediction cannot be distinguished from nothing, and it is a
   property of the real data and the real scorer, not a simulation.
2. **The submission path.** The prediction is generated through the same
   `SubmissionWriter` and `sample_counts` used for a real submission, so a
   defect in count sampling, density caps or gene ordering surfaces here rather
   than at the deadline.

What this stage is NOT: a measure of whether we can predict a perturbation. The
truth is zero everywhere by construction. The adversarial review is explicit
that an NTC-vs-NTC test must never be read as a response-prediction benchmark,
and a run that beat the null here would mean a leak, not a discovery.

    scripts/py.cmd scripts/42_null_calibration.py --run-id n001 --context A
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.evaluation import VCC_SCORED_METRICS, score_bundle
from vcc2026.genes import official_axis
from vcc2026.inference import read_csr_rows
from vcc2026.manifest import RunManifest
from vcc2026.sampling import resample_library_sizes, sample_counts
from vcc2026.submission import SubmissionWriter


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", default="n001")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--context", default="A", choices=["A", "B", "C"])
    p.add_argument("--n-pseudo", type=int, default=6,
                   help="number of pseudo-perturbation groups of NTC guides")
    p.add_argument("--cells-per-pseudo", type=int, default=300)
    p.add_argument("--n-control-cells", type=int, default=3000)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--overdispersion", type=float, default=None)
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    run = args.out or config.run_dir(args.run_id)
    run.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    ch = config.challenge()
    axis = official_axis()
    ctrl_path = config.paths().raw / "controls" / f"context_{args.context}.h5ad"

    with h5py.File(ctrl_path, "r") as f:
        cats = f["obs/ntc_id/categories"].asstr()[:]
        codes = f["obs/ntc_id/codes"][:]
        n_cells, n_genes = tuple(f["X"].attrs["shape"])
        var_names = f["var/_index/values"].asstr()[:]
    if list(var_names) != list(axis.symbols):
        raise SystemExit("control var order does not match gene_names.csv; "
                         "the submission axis contract is broken")

    # Pseudo-perturbations are labelled with REAL panel gene symbols, not
    # invented names. cell-eval2 0.16.0 requires every perturbation label to
    # resolve to a gene in the feature index -- it raises rather than silently
    # excluding nothing, because excluding nothing "would otherwise return a
    # plausible wrong number". Labelling these groups NTCGROUP0.. fails that
    # check, and using real symbols also exercises the panel exclusion the
    # official config applies (discrimination.exclusion_scope = "panel").
    panel = pd.read_csv(config.paths().raw / "controls" / "pert_counts.csv")
    on_axis = [g for g in panel.target_gene.astype(str) if g in set(axis.symbols)]
    if len(on_axis) < args.n_pseudo:
        raise SystemExit("not enough panel targets on the official axis")
    labels = on_axis[: args.n_pseudo]

    guides = np.arange(len(cats))
    rng.shuffle(guides)
    if args.n_pseudo + 1 > len(guides):
        raise SystemExit(f"only {len(guides)} NTC guides available")

    # Disjoint guide groups. Splitting on the GUIDE, not the cell, is what makes
    # this a real null: cells sharing a guide share its capture batch and any
    # guide-specific artefact, so a cell-level split would understate the floor.
    groups = np.array_split(guides[: args.n_pseudo * 2], args.n_pseudo)
    control_guides = guides[args.n_pseudo * 2:]
    if len(control_guides) == 0:
        raise SystemExit("no guides left for the control arm; lower --n-pseudo")

    print(f"context {args.context}: {n_cells} cells, {len(cats)} NTC guides")
    print(f"{args.n_pseudo} pseudo-perturbations from disjoint guide groups; "
          f"{len(control_guides)} guides form the control arm\n")

    real_blocks, real_labels = [], []
    for i, grp in enumerate(groups):
        rows = np.flatnonzero(np.isin(codes, grp))
        if rows.size < args.cells_per_pseudo:
            raise SystemExit(f"group {i} has only {rows.size} cells")
        pick = rng.choice(rows, size=args.cells_per_pseudo, replace=False)
        # Row by row out of the CSR datasets: the control file holds 110M stored values,
        # and loading X whole is ~880 MB before anything else happens.
        real_blocks.append(read_csr_rows(ctrl_path, np.sort(pick), n_genes))
        real_labels.append((labels[i], args.cells_per_pseudo))

    ctrl_rows = np.flatnonzero(np.isin(codes, control_guides))
    pick_ctrl = rng.choice(
        ctrl_rows, size=min(args.n_control_cells, ctrl_rows.size), replace=False
    )
    control_block = read_csr_rows(ctrl_path, np.sort(pick_ctrl), n_genes)

    real_path = run / f"real_{args.context}.h5ad"
    pred_path = run / f"pred_{args.context}.h5ad"
    for pth in (real_path, pred_path):
        if pth.exists() and not args.allow_overwrite:
            raise SystemExit(f"{pth} exists; use a new --run-id")

    cfg = config.challenge()
    with SubmissionWriter(real_path, axis.symbols, pert_col="target",
                          context_col="context") as w:
        for (label, _), block in zip(real_labels, real_blocks):
            w.add(block, target_gene=label, context=args.context)
        w.add(control_block, target_gene=cfg.ntc_label, context=args.context)
    print(f"real bundle  : {real_path.name}  "
          f"{sum(n for _, n in real_labels) + control_block.shape[0]} cells")

    # The null prediction: the control profile itself, resampled to the observed
    # depth distribution. This is exactly NullModel -- no change anywhere.
    profile = np.asarray(control_block.sum(axis=0)).ravel().astype(np.float64)
    observed_libs = np.asarray(control_block.sum(axis=1)).ravel().astype(np.int64)
    with SubmissionWriter(pred_path, axis.symbols, pert_col="target",
                          context_col="context") as w:
        for label, n in real_labels:
            libs = resample_library_sizes(observed_libs, n, rng)
            block = sample_counts(
                profile, libs, rng,
                max_stored_per_cell=cfg.max_stored_per_cell,
                max_counts_per_cell=cfg.max_counts_per_cell,
                overdispersion=args.overdispersion,
            )
            w.add(block, target_gene=label, context=args.context)
        libs = resample_library_sizes(observed_libs, control_block.shape[0], rng)
        w.add(
            sample_counts(profile, libs, rng,
                          max_stored_per_cell=cfg.max_stored_per_cell,
                          max_counts_per_cell=cfg.max_counts_per_cell,
                          overdispersion=args.overdispersion),
            target_gene=cfg.ntc_label, context=args.context,
        )
    print(f"pred bundle  : {pred_path.name}\n")

    print("running cell-eval2 ...")
    result = score_bundle(pred_path, real_path, profile="vcc2026",
                          outdir=run / "scorer")
    result["design"] = {
        "context": args.context,
        "n_pseudo_perturbations": args.n_pseudo,
        "cells_per_pseudo": args.cells_per_pseudo,
        "n_control_cells": int(control_block.shape[0]),
        "guide_groups": [[cats[g] for g in grp] for grp in groups],
        "control_guides": [cats[g] for g in control_guides],
        "seed": args.seed,
        "overdispersion": args.overdispersion,
        "true_effect": "zero by construction: all cells are non-targeting controls",
    }
    result["interpretation"] = (
        "Any non-trivial DE here is a false positive. These numbers are the "
        "noise floor of the real data under the real scorer, NOT evidence that "
        "a perturbation can be predicted."
    )

    out = run / f"null_calibration_{args.context}.json"
    if out.exists() and not args.allow_overwrite:
        raise SystemExit(f"{out} exists; use a new --run-id")
    out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print(f"\nscorer: cell-eval2 {result['scorer']['cell_eval2']} "
          f"(matches D-008: {result['scorer']['matches_decision_D008']})")
    print(f"all six scored metrics present: {result['all_six_present']}")
    if result.get("missing_scored_metrics"):
        print(f"MISSING: {result['missing_scored_metrics']}")
    if result.get("aggregate_error"):
        print("\naggregation refused (expected on a true-null reference):")
        print("  " + result["aggregate_error"][:400])
    print("\nper-perturbation metric summary:")
    for k in sorted(result.get("per_metric_over_perturbations", {})):
        v = result["per_metric_over_perturbations"][k]
        if not isinstance(v, dict) or "median" not in v:
            continue
        star = " *" if k in VCC_SCORED_METRICS else "  "
        print(f"  {star} {k:46s} median={v['median']}  "
              f"n_finite={v['n_finite']}/{v['n_perturbations']}")
    if result["raw_aggregate"]:
        print("\nraw aggregate metrics:")
        for k, v in sorted(result["raw_aggregate"].items()):
            star = " *" if k in VCC_SCORED_METRICS else "  "
            print(f"  {star} {k:46s} {v}")

    man = RunManifest(run_id=args.run_id, stage="42_null_calibration",
                      config=vars(args), seed=args.seed)
    man.add_input("controls", ctrl_path)
    man.add_output("real_bundle", real_path)
    man.add_output("pred_bundle", pred_path)
    man.add_output("null_calibration", out)
    man.metrics = {"aggregate": result["raw_aggregate"],
                   "per_metric": result.get("per_metric_over_perturbations", {})}
    man.note("Truth is zero by construction; this is a false-positive floor, not "
             "a response-prediction benchmark.")
    man.note("Raw metrics only: the competition's (u-b)/(r-b) rescaling needs a "
             "published baseline and a replicate anchor we do not have.")
    man.write(run / f"manifest_42_null_calibration_{args.context}.json",
              allow_overwrite=args.allow_overwrite)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
