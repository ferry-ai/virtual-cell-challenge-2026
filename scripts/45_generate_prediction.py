"""Stage 5: generate a submission-shaped prediction for the official contexts.

Two trials, one code path, so that what is measured about the machinery on the
cheap trial is true of the expensive one:

* ``trial-00-controls`` resamples each context's own real non-targeting control
  cells and labels them with the requested perturbations. No model. Its cells
  are real, so its dispersion is right by construction, which makes it the
  reference against which the generator's artefacts are visible.
* ``trial-01-transfer`` applies the calibrated ShrunkTransfer response to each
  context's basal profile and samples counts from it.

The prediction is streamed one perturbation at a time through the existing
`SubmissionWriter`: a full submission is 360,000 x 18,533 at roughly 11,800
stored values per cell, about 4.2 billion entries, which is ~34 GB as an
uncompressed CSR and cannot be assembled on a 7.8 GiB machine. Nothing here ever
holds more than one 400-cell block.

Three things are written beside the matrix rather than into it:

* the **support mask** -- which targets and genes carry evidence at all, so a
  no-effect fallback is never read later as a measured null (D-009);
* **source-cell provenance** for the control trial, because the submission
  format has no place for it and inventing an obs column would break the
  contract;
* **count-generation diagnostics** comparing generated cells with the real
  controls they imitate, including at zero predicted effect.

    scripts/py.cmd scripts/45_generate_prediction.py --run-id p001 \
        --trial trial-00-controls --n-perts 6            # pilot
    scripts/py.cmd scripts/45_generate_prediction.py --run-id p003 \
        --trial trial-01-transfer --fitted-state <run>/fitted_state.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.inference import (
    count_generation_diagnostics,
    nearest_basal_context,
    predicted_profile,
    profile_similarity,
    read_basal_profile,
    read_csr_rows,
)
from vcc2026.genes import official_axis
from vcc2026.manifest import RunManifest, file_fingerprint
from vcc2026.models import ShrunkTransfer
from vcc2026.resources import GiB, peak_rss_bytes, require, snapshot
from vcc2026.sampling import resample_library_sizes, sample_counts
from vcc2026.signatures import SignatureSet
from vcc2026.submission import SubmissionWriter
from vcc2026.trials import load_trial, trial_ids

# Blocks sampled for the expensive per-block diagnostics. Every block is
# checked for the cheap invariants; this is the subset that also gets a profile
# comparison against all three basal states.
DIAG_SAMPLE = 12


def panel_targets(n: int | None) -> list[str]:
    """The official perturbation list, or its first `n` for a pilot."""
    frame = pd.read_csv(config.paths().raw / "controls" / "pert_counts.csv")
    perts = [str(g) for g in frame["target_gene"]]
    ch = config.challenge()
    if len(perts) != ch.n_perturbations:
        raise SystemExit(
            f"pert_counts.csv holds {len(perts)} perturbations, the contract "
            f"says {ch.n_perturbations}"
        )
    return perts if n is None else perts[:n]


def load_transfer_model(state_path: Path, signatures: Path) -> tuple[ShrunkTransfer, dict]:
    """Rebuild the calibrated model from its saved state."""
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("model") != "shrunk_transfer":
        raise SystemExit(f"{state_path}: unsupported model {state.get('model')!r}")
    params = state["parameters"]
    source_id = state["source_signatures"]["source_id"]
    npz = signatures / f"{source_id}.npz"
    if not npz.exists():
        raise SystemExit(f"{npz} missing")
    recorded = state["source_signatures"]["npz"].get("sha256")
    actual = file_fingerprint(npz).get("sha256")
    if recorded and actual and recorded != actual:
        raise SystemExit(
            f"{npz} does not match the signatures the parameters were selected "
            f"on (sha256 {actual} vs {recorded}); point --signatures at the run "
            f"named in the fitted state"
        )
    return state, (params, source_id, npz)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--trial", required=True)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--fitted-state", type=Path, default=None,
                   help="fitted_state.json from 44_calibrate_transfer (transfer trial)")
    p.add_argument("--signatures", type=Path, default=None)
    p.add_argument("--n-perts", type=int, default=None,
                   help="pilot only: use the first N official perturbations")
    p.add_argument("--contexts", default=None, help="default: A,B,C from the contract")
    p.add_argument("--cells-per-pert", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--overdispersion", type=float, default=None)
    p.add_argument("--reserve-gib", type=float, default=10.0)
    p.add_argument("--skip-resource-check", action="store_true")
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    t_start = time.perf_counter()
    try:
        trial = load_trial(args.trial)
    except KeyError:
        raise SystemExit(f"unknown trial {args.trial!r}; known: {trial_ids()}")
    seed = args.seed if args.seed is not None else int(trial["seed"])
    ch = config.challenge()
    cells_per_pert = args.cells_per_pert or int(trial["cells_per_pert"])
    contexts = tuple(
        args.contexts.split(",") if args.contexts else trial["contexts"]
    )
    targets = panel_targets(args.n_perts)
    is_pilot = args.n_perts is not None or cells_per_pert != ch.cells_per_pert \
        or set(contexts) != set(ch.contexts_validation)

    run = args.out or config.run_dir(args.run_id)
    run.mkdir(parents=True, exist_ok=True)
    pred_path = run / "prediction.h5ad"
    diag_path = run / "generation_diagnostics.json"
    for pth in (pred_path, diag_path):
        if pth.exists() and not args.allow_overwrite:
            raise SystemExit(f"{pth} exists; use a new --run-id")

    n_cells_total = len(targets) * cells_per_pert * len(contexts)
    # Measured on the pilot and carried forward: the control trial stores the
    # real ~6,000 values per cell, the sampled trial about 11,800.
    bytes_per_cell = 6_000 if trial["kind"] == "control_resampling" else 12_500
    est_bytes = n_cells_total * bytes_per_cell
    if not args.skip_resource_check:
        snap = require(disk_bytes=int(est_bytes * 1.3), path=run,
                       reserve_bytes=int(args.reserve_gib * GiB))
    else:
        snap = snapshot(run)

    print(f"trial          : {trial['id']} ({trial['kind']})")
    print(f"shape          : {len(targets)} perturbations x {cells_per_pert} cells "
          f"x {len(contexts)} contexts = {n_cells_total:,} cells")
    print(f"pilot          : {is_pilot}")
    print(f"disk free      : {snap.disk_free_gib:.2f} GiB "
          f"(estimated need {est_bytes / GiB:.2f} GiB)")
    print(f"seed           : {seed}\n")

    axis = official_axis()
    rng = np.random.default_rng(seed)

    # --- basal state of every official context -------------------------------
    t_basal = time.perf_counter()
    basals = {}
    for ctx in contexts:
        path = config.paths().raw / "controls" / f"context_{ctx}.h5ad"
        with h5py.File(path, "r") as f:
            var_names = f["var/_index/values"].asstr()[:]
        if list(var_names) != list(axis.symbols):
            raise SystemExit(
                f"context_{ctx}.h5ad var order does not match gene_names.csv; "
                f"the submission axis contract is broken"
            )
        prof = read_basal_profile(path)
        if prof.context != ctx:
            raise SystemExit(
                f"context_{ctx}.h5ad declares obs.context={prof.context!r}; "
                f"refusing to relabel data"
            )
        basals[ctx] = prof
        print(f"  basal {ctx}: {prof.n_cells:,} cells, median UMI "
              f"{np.median(prof.library_sizes):,.0f}, median detected genes "
              f"{np.median(prof.nnz_per_cell):,.0f}")
    basal_seconds = time.perf_counter() - t_basal
    basal_profiles = {c: b.profile for c, b in basals.items()}

    # Contexts must be distinguishable for the provenance check to mean
    # anything: if two basal states were identical, a swap would be invisible
    # here too, and that has to be measured rather than assumed.
    cross = {
        f"{a}_vs_{b}": profile_similarity(basal_profiles[a], basal_profiles[b])
        for i, a in enumerate(contexts) for b in contexts[i + 1:]
    }

    # --- the model -----------------------------------------------------------
    state = None
    support = {"kind": trial["kind"]}
    predictions: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    if trial["kind"] == "shrunk_transfer":
        if args.fitted_state is None or args.signatures is None:
            raise SystemExit("--fitted-state and --signatures are required for "
                             "the transfer trial")
        state, (params, source_id, npz) = load_transfer_model(
            args.fitted_state, args.signatures
        )
        print(f"\nmodel          : shrunk_transfer alpha={params['alpha']:.4f} "
              f"prior_sd={params['prior_sd']:g} source={source_id}")
        sigs = SignatureSet.read_npz(npz, targets=set(targets))
        model = ShrunkTransfer(
            alpha=float(params["alpha"]), prior_sd=float(params["prior_sd"]),
            source=source_id, collapse_guides=bool(params.get("collapse_guides", True)),
        ).fit(sigs)
        gene_observed = np.zeros(len(axis), dtype=bool)
        covered = []
        for t in targets:
            pred = model.predict(t)
            predictions[t] = (pred.delta, pred.observed)
            if pred.support > 0:
                covered.append(t)
                gene_observed |= pred.observed
        support.update({
            "model": "shrunk_transfer",
            "parameters": params,
            "source_id": source_id,
            "requested_targets": len(targets),
            "covered_targets": len(covered),
            "uncovered_targets": [t for t in targets if t not in set(covered)],
            "n_genes_observed_by_source": int(gene_observed.sum()),
            "n_genes_unobserved_by_source": int((~gene_observed).sum()),
            "fallback_semantics": (
                "An uncovered target and a gene outside the source's feature "
                "universe both receive a no-effect prediction because no "
                "evidence exists for them. That is a FALLBACK, not a measured "
                "null effect (D-009)."
            ),
        })
        print(f"support        : {len(covered)}/{len(targets)} targets covered, "
              f"{int(gene_observed.sum()):,}/{len(axis):,} genes observed by source")
        del sigs
    elif trial["kind"] != "control_resampling":
        raise SystemExit(f"unsupported trial kind {trial['kind']!r}")

    # --- generate ------------------------------------------------------------
    t_gen = time.perf_counter()
    per_block = []
    diag_blocks = []
    provenance = {}
    context_totals = {ctx: np.zeros(len(axis), dtype=np.float64) for ctx in contexts}
    diag_pick = set(
        np.linspace(0, len(targets) * len(contexts) - 1,
                    min(DIAG_SAMPLE, len(targets) * len(contexts))).astype(int).tolist()
    )
    shift_log = []
    block_index = 0

    with SubmissionWriter(
        pred_path, axis.symbols, pert_col=ch.pert_col, context_col=ch.context_col
    ) as writer:
        for ctx in contexts:
            basal = basals[ctx]
            ctrl_path = Path(basal.source_path)
            with h5py.File(ctrl_path, "r") as f:
                indptr = f["X/indptr"][:].astype(np.int64)
            picks = np.zeros((len(targets), cells_per_pert), dtype=np.int32)

            for ti, target in enumerate(targets):
                if trial["kind"] == "control_resampling":
                    if basal.n_cells < cells_per_pert:
                        raise SystemExit(
                            f"context {ctx} has {basal.n_cells} control cells, "
                            f"fewer than the {cells_per_pert} required"
                        )
                    rows = rng.choice(basal.n_cells, size=cells_per_pert,
                                      replace=False)
                    picks[ti] = rows.astype(np.int32)
                    block = read_csr_rows(ctrl_path, rows, len(axis), indptr=indptr)
                    detail = {"compositional_shift_log2": 0.0,
                              "source": "real control cells, resampled"}
                else:
                    delta, observed = predictions[target]
                    profile, detail = predicted_profile(
                        basal.profile, delta, observed
                    )
                    libs = resample_library_sizes(
                        basal.library_sizes, cells_per_pert, rng
                    )
                    block = sample_counts(
                        profile, libs, rng,
                        max_stored_per_cell=ch.max_stored_per_cell,
                        max_counts_per_cell=ch.max_counts_per_cell,
                        overdispersion=args.overdispersion,
                    )
                    shift_log.append(detail["compositional_shift_log2"])

                writer.add(block, target_gene=target, context=ctx)
                block_sum = np.asarray(block.sum(axis=0)).ravel().astype(np.float64)
                context_totals[ctx] += block_sum
                per_block.append({
                    "context": ctx,
                    "target": target,
                    "n_cells": int(block.shape[0]),
                    "nnz": int(block.nnz),
                    "nnz_per_cell": float(block.nnz / block.shape[0]),
                    "max_counts_in_a_cell": float(np.asarray(block.sum(axis=1)).max()),
                    "compositional_shift_log2": detail["compositional_shift_log2"],
                })
                if block_index in diag_pick:
                    best, scores = nearest_basal_context(block_sum, basal_profiles)
                    diag = count_generation_diagnostics(block, basal)
                    diag.update({
                        "context": ctx, "target": target,
                        "nearest_basal_context": best,
                        "similarity_to_each_basal": scores,
                        "label_matches_nearest_basal": best == ctx,
                        "detail": detail,
                    })
                    diag_blocks.append(diag)
                block_index += 1
                if ti % 25 == 0:
                    print(f"    {ctx} {ti + 1}/{len(targets)} "
                          f"({time.perf_counter() - t_gen:.0f}s)")

            if trial["kind"] == "control_resampling":
                prov = run / f"provenance_{ctx}.npz"
                np.savez_compressed(
                    prov, source_row=picks,
                    target=np.array(targets, dtype=object),
                    context=np.array([ctx], dtype=object),
                )
                provenance[ctx] = str(prov)
                print(f"    provenance -> {prov.name}")

        n_obs, nnz = writer.n_obs, writer.nnz

    gen_seconds = time.perf_counter() - t_gen
    size_bytes = pred_path.stat().st_size

    # --- context provenance, at the level a swap would show up ---------------
    context_check = {}
    for ctx in contexts:
        best, scores = nearest_basal_context(context_totals[ctx], basal_profiles)
        context_check[ctx] = {
            "nearest_basal_context": best,
            "similarity_to_each_basal": scores,
            "label_matches_nearest_basal": best == ctx,
        }
    all_match = all(v["label_matches_nearest_basal"] for v in context_check.values())

    peak = peak_rss_bytes()
    total_seconds = time.perf_counter() - t_start
    full_cells = ch.n_cells_total
    scale = full_cells / n_obs if n_obs else None

    diagnostics = {
        "run_id": args.run_id,
        "stage": "45_generate_prediction",
        "trial": {k: trial[k] for k in ("id", "kind", "title", "trains")},
        "seed": seed,
        "is_pilot": is_pilot,
        "shape": {
            "n_perturbations": len(targets),
            "cells_per_pert": cells_per_pert,
            "contexts": list(contexts),
            "n_cells": int(n_obs),
            "n_genes": len(axis),
            "official_full_shape": {
                "n_perturbations": ch.n_perturbations,
                "cells_per_pert": ch.cells_per_pert,
                "n_contexts": len(ch.contexts_validation),
                "n_cells": full_cells,
                "n_genes": ch.n_genes,
            },
        },
        "storage": {
            "stored_entries": int(nnz),
            "stored_entries_per_cell": float(nnz / n_obs) if n_obs else None,
            "per_cell_budget": ch.max_stored_per_cell,
            "global_cap": ch.max_stored_entries,
            "fraction_of_global_cap_at_this_size": float(nnz / ch.max_stored_entries),
            "projected_entries_at_full_shape": (
                float(nnz * scale) if scale else None
            ),
            "projected_fraction_of_cap": (
                float(nnz * scale / ch.max_stored_entries) if scale else None
            ),
            "file_bytes": size_bytes,
            "bytes_per_cell": float(size_bytes / n_obs) if n_obs else None,
            "projected_file_bytes_at_full_shape": (
                float(size_bytes * scale) if scale else None
            ),
        },
        "runtime": {
            "basal_profiles_seconds": basal_seconds,
            "generation_seconds": gen_seconds,
            "total_seconds": total_seconds,
            "seconds_per_block": gen_seconds / len(per_block) if per_block else None,
            "projected_generation_seconds_at_full_shape": (
                gen_seconds * scale if scale else None
            ),
        },
        "memory": {
            "peak_rss_bytes": peak,
            "peak_rss_gib": None if peak is None else peak / GiB,
            "resources_before": snap.as_dict(),
            "resources_after": snapshot(run).as_dict(),
        },
        "support": support,
        "compositional_shift": {
            "n_targets_with_a_shift": len(shift_log),
            "median_abs_log2": float(np.median(np.abs(shift_log))) if shift_log else 0.0,
            "max_abs_log2": float(np.max(np.abs(shift_log))) if shift_log else 0.0,
            "why": (
                "Counts are a composition, so renormalising basal*2**delta to a "
                "library size removes a global factor. The shift is absorbed by "
                "the genes that carry a prediction, so unobserved genes realise "
                "exactly zero change instead of an unintended uniform drift."
            ),
        },
        "context_provenance": {
            "per_context": context_check,
            "all_labels_match_nearest_basal": all_match,
            "basal_cross_similarity": cross,
            "why": (
                "Format validation cannot detect swapped A/B/C data. Every block "
                "here is built from one context's own controls, so each context's "
                "aggregate profile must be nearest to that context's basal "
                "profile. The cross-similarities show the three basal states are "
                "distinguishable, which is what makes the test informative."
            ),
        },
        "count_generation": {
            "sampled_blocks": diag_blocks,
            "zero_effect_artefact_note": (
                "For the control trial the cells ARE real, so any difference "
                "from the controls is resampling only. For the sampled trial the "
                "generated/real nnz ratio is above 1 even at zero predicted "
                "effect, because a pooled mean profile is less sparse than any "
                "single cell: an artefact of the generator, present before any "
                "prediction is made."
            ),
        },
        "per_block": per_block,
        "fitted_state": state,
        "provenance_files": provenance,
        "not_a_score": (
            "This file contains no VCC score. It records what was generated and "
            "what it cost. Nothing here has been uploaded."
        ),
    }
    diag_path.write_text(json.dumps(diagnostics, indent=2, default=str),
                         encoding="utf-8")

    man = RunManifest(run_id=args.run_id, stage="45_generate_prediction",
                      config=vars(args), seed=seed)
    for ctx in contexts:
        man.add_input(f"controls:{ctx}", basals[ctx].source_path)
    if args.fitted_state:
        man.add_input("fitted_state", args.fitted_state)
    man.add_output("prediction", pred_path)
    man.add_output("diagnostics", diag_path)
    for ctx, prov in provenance.items():
        man.add_output(f"provenance:{ctx}", prov)
    man.metrics = {
        "storage": diagnostics["storage"],
        "runtime": diagnostics["runtime"],
        "memory": {"peak_rss_bytes": peak},
        "context_provenance_ok": all_match,
    }
    man.note("No VCC score here. Generation only; nothing uploaded.")
    if is_pilot:
        man.note("PILOT: not a submittable artifact. Coverage is deliberately "
                 "incomplete and vcc prep will reject it.")
    man.write(run / "manifest_45_generate_prediction.json",
              allow_overwrite=args.allow_overwrite)

    print(f"\nwrote {pred_path.name}: {n_obs:,} cells, {nnz:,} stored values, "
          f"{size_bytes / 1024**2:.1f} MB")
    print(f"  stored per cell     : {nnz / n_obs:,.0f} (budget "
          f"{ch.max_stored_per_cell:,})")
    if scale and scale > 1:
        print(f"  projected full run  : {nnz * scale / 1e9:.2f}e9 entries "
              f"({nnz * scale / ch.max_stored_entries:.1%} of cap), "
              f"{size_bytes * scale / GiB:.2f} GiB, "
              f"{gen_seconds * scale / 60:.1f} min")
    print(f"  context provenance  : "
          f"{'OK' if all_match else 'MISMATCH -- investigate before packaging'}")
    print(f"  runtime             : basal {basal_seconds:.0f}s, generation "
          f"{gen_seconds:.0f}s, total {total_seconds:.0f}s")
    print(f"  peak RSS            : "
          f"{'unknown' if peak is None else f'{peak / GiB:.2f} GiB'}")
    print(f"-> {pred_path}\n-> {diag_path}")


if __name__ == "__main__":
    main()
