"""Stage 5: generate a submission-shaped prediction for the official contexts.

The trial-01 generator, driven by per-context effects files (``--trial trial-ext-profile``,
``--effects CTX=PATH`` with the npz files of stage 100). For every context and perturbation it
takes the context's basal profile, applies the effects with the compositional shift on the
supported genes (D-015), and samples Poisson counts at library sizes resampled from that
context's own controls.

The prediction is streamed one perturbation at a time through the existing
`SubmissionWriter`: a full submission is 360,000 x 18,533 at roughly 11,800
stored values per cell, about 4.2 billion entries, which is ~34 GB as an
uncompressed CSR and cannot be assembled on a 7.8 GiB machine. Nothing here ever
holds more than one 400-cell block.

Two things are written beside the matrix rather than into it:

* the **support** -- which effects files were read and which genes they observe, so a
  pair without evidence is never read later as a measured null (D-009);
* **count-generation diagnostics** comparing generated cells with the real
  controls they imitate, including at zero predicted effect.

The control-resampling trial (trial-00) and the ShrunkTransfer trial (trial-01) left this
stage on 24 September 2026 (D-043); they are in the tag archivio/pre-pulizia-2026-09-24.

    scripts/py.cmd scripts/45_generate_prediction.py --run-id p001 --trial trial-ext-profile \
        --n-perts 6 --contexts A --effects A=<stage-100 dir>/effects_A.npz     # pilot
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
)
from vcc2026.genes import official_axis
from vcc2026.manifest import RunManifest, file_fingerprint
from vcc2026.resources import GiB, peak_rss_bytes, require, snapshot
from vcc2026.sampling import fit_gene_dispersion, resample_library_sizes, sample_counts
from vcc2026.submission import SubmissionWriter
from vcc2026.trials import load_trial, trial_ids

# Blocks sampled for the expensive per-block diagnostics. Every block is
# checked for the cheap invariants; this is the subset that also gets a profile
# comparison against all three basal states.
DIAG_SAMPLE = 12


def panel_targets(n: int | None, controls: Path) -> list[str]:
    """The official perturbation list, or its first `n` for a pilot."""
    frame = pd.read_csv(controls / "pert_counts.csv")
    perts = [str(g) for g in frame["target_gene"]]
    ch = config.challenge()
    if len(perts) != ch.n_perturbations:
        raise SystemExit(
            f"pert_counts.csv holds {len(perts)} perturbations, the contract "
            f"says {ch.n_perturbations}"
        )
    return perts if n is None else perts[:n]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--trial", required=True)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--n-perts", type=int, default=None,
                   help="pilot only: use the first N official perturbations")
    p.add_argument("--contexts", default=None, help="default: A,B,C from the contract")
    p.add_argument("--controls-dir", type=Path, default=None,
                   help="folder with context_<CTX>.h5ad and pert_counts.csv "
                        "(default: <data_root>/raw/controls; a new bundle goes in its own folder)")
    p.add_argument("--cells-per-pert", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--overdispersion", type=float, default=None)
    p.add_argument("--reserve-gib", type=float, default=10.0)
    p.add_argument("--skip-resource-check", action="store_true")
    p.add_argument("--allow-overwrite", action="store_true")
    p.add_argument("--gene-dispersion", action="store_true",
                   help="fit a per-gene Gamma-Poisson dispersion to each context's zero fractions "
                        "(sampling.fit_gene_dispersion) instead of Poisson around the pooled profile")
    p.add_argument("--effects-scale", type=float, default=1.0,
                   help="external_effects: multiply every file's lfc (0 = the null of this generator)")
    p.add_argument("--effects", action="append", default=None, metavar="CTX=PATH",
                   help="external_effects trials: per-context npz from stage 100 "
                        "(targets, genes, lfc in ln units, observed)")
    args = p.parse_args()

    t_start = time.perf_counter()
    try:
        trial = load_trial(args.trial)
    except KeyError:
        raise SystemExit(f"unknown trial {args.trial!r}; known: {trial_ids()}")
    if trial["kind"] != "external_effects":
        raise SystemExit(f"unsupported trial kind {trial['kind']!r}")
    seed = args.seed if args.seed is not None else int(trial["seed"])
    ch = config.challenge()
    cells_per_pert = args.cells_per_pert or int(trial["cells_per_pert"])
    contexts = tuple(
        args.contexts.split(",") if args.contexts else trial["contexts"]
    )
    controls = args.controls_dir or config.paths().raw / "controls"
    targets = panel_targets(args.n_perts, controls)
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
    # Measured on the pilot and carried forward: sampled cells store about
    # 11,800 values each.
    bytes_per_cell = 12_500
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
        path = controls / f"context_{ctx}.h5ad"
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
    gene_phi = {}
    if args.gene_dispersion:
        for ctx, prof in basals.items():
            with h5py.File(prof.source_path, "r") as f:
                idx_ds = f["X/indices"]
                detected = np.zeros(len(axis), dtype=np.int64)
                for lo in range(0, idx_ds.shape[0], 20_000_000):
                    detected += np.bincount(idx_ds[lo:lo + 20_000_000], minlength=len(axis))
            zero_fraction = 1.0 - detected / prof.n_cells
            gene_phi[ctx] = fit_gene_dispersion(prof.profile, prof.library_sizes, zero_fraction, seed=seed)
            expressed = prof.profile > 0
            print(f"  dispersion {ctx}: {int((gene_phi[ctx] > 0).sum()):,} genes overdispersed, "
                  f"median phi {np.median(gene_phi[ctx][expressed]):.3f}")

    # Contexts must be distinguishable for the provenance check to mean
    # anything: if two basal states were identical, a swap would be invisible
    # here too, and that has to be measured rather than assumed.
    cross = {
        f"{a}_vs_{b}": profile_similarity(basal_profiles[a], basal_profiles[b])
        for i, a in enumerate(contexts) for b in contexts[i + 1:]
    }

    # --- the effects ---------------------------------------------------------
    specs = dict(s.partition("=")[::2] for s in (args.effects or []))
    if set(specs) != set(contexts):
        raise SystemExit(f"--effects covers {sorted(specs)} but the contexts are {list(contexts)}")
    ctx_predictions = {}
    axis_index = pd.Index(list(axis.symbols))
    for ctx, path in specs.items():
        z = np.load(path, allow_pickle=False)
        gpos = pd.Index(z["genes"].astype(str)).get_indexer(axis_index)
        if (gpos < 0).any():
            raise SystemExit(f"{path}: {(gpos < 0).sum()} official genes missing from the file")
        rows = {t: i for i, t in enumerate(z["targets"].astype(str))}
        missing = [t for t in targets if t not in rows]
        if missing:
            raise SystemExit(f"{path}: no effects for {len(missing)} targets, e.g. {missing[:3]}")
        lfc, obs_mask = z["lfc"][:, gpos], z["observed"][:, gpos]
        # stage 100 writes ln fold changes; the trial-01 profile takes log2
        ctx_predictions[ctx] = {t: (args.effects_scale * lfc[rows[t]] / np.log(2.0),
                                    obs_mask[rows[t]].astype(bool))
                                for t in targets}
        print(f"effects {ctx}      : {path} ({int(obs_mask.any(axis=0).sum()):,} genes observed)")
    support = {"kind": trial["kind"], "model": "external_effects", "effects_scale": args.effects_scale,
               "effects": {c: file_fingerprint(Path(p)) for c, p in specs.items()}}

    if gene_phi:
        support["gene_dispersion"] = {
            ctx: {"method": "sampling.fit_gene_dispersion: zero-fraction matching, per gene",
                  "genes_overdispersed": int((phi > 0).sum()),
                  "phi_quantiles_expressed": [float(q) for q in np.quantile(phi[basals[ctx].profile > 0], [0.1, 0.5, 0.9])]}
            for ctx, phi in gene_phi.items()}

    # --- generate ------------------------------------------------------------
    t_gen = time.perf_counter()
    per_block = []
    diag_blocks = []
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
            for ti, target in enumerate(targets):
                delta, observed = ctx_predictions[ctx][target]
                profile, detail = predicted_profile(basal.profile, delta, observed)
                libs = resample_library_sizes(basal.library_sizes, cells_per_pert, rng)
                block = sample_counts(
                    profile, libs, rng,
                    max_stored_per_cell=ch.max_stored_per_cell,
                    max_counts_per_cell=ch.max_counts_per_cell,
                    overdispersion=gene_phi.get(ctx, args.overdispersion),
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
                "The generated/real nnz ratio is above 1 even at zero predicted "
                "effect, because a pooled mean profile is less sparse than any "
                "single cell: an artefact of the generator, present before any "
                "prediction is made."
            ),
        },
        "per_block": per_block,
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
    man.add_output("prediction", pred_path)
    man.add_output("diagnostics", diag_path)
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
