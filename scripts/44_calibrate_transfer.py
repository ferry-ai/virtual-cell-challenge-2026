"""Stage 4: calibrate ShrunkTransfer by NESTED cross-validation on held-out targets.

Stage 41 measured that amplitude is selectable rather than guessable, with a
single-level fold loop: the grid was searched on training targets and reported
on the test fold. Two things it did are not good enough to hang a submission
parameter on.

* Its bootstrap interval was computed on **all** targets using the parameters
  the folds had already chosen, so the interval described the training data.
* A single level cannot separate "how well does this parameter generalise" from
  "which parameter should we ship". The same fold answered both.

So this stage uses an outer loop purely for reporting and an inner loop purely
for selection. For each outer fold, the shrinkage scale `prior_sd` is chosen by
cross-validated error *inside* the outer-training targets, the amplitude `alpha`
is then refitted in closed form on all of those training targets, and the pair
is applied blind to the outer-test targets. Every target therefore ends up with
exactly one prediction made by parameters selected without it, and the bootstrap
resamples that out-of-fold set.

The parameters that a submission will actually use are selected separately, by
the same protocol run over the whole development set, and reported as such --
not as the held-out estimate.

Three leakage rules, enforced rather than documented:

* **Guides of a target never separate.** `collapse_guides` reduces every guide
  and TSS row of a target to one estimate before splitting, so the unit of
  splitting is the target. The script asserts the split is disjoint.
* **A held-out reference response is never read.** `alpha` and `prior_sd` are
  functions of training rows only, and there is no response basis to fit.
* **Coverage masks must not carry held-out information.** The gene mask is the
  intersection of what both sources measure. The script checks that per-target
  coverage is constant within each source -- so the mask is a property of the
  dataset, not of the held-out rows -- and falls back to train-only masks if it
  is not.

    scripts/py.cmd scripts/44_calibrate_transfer.py --run-id c001 \
        --signatures <artifact_root>/e001/signatures

This produces NO VCC score. It is pseudobulk log2 fold change space; the
competition scores single-cell counts against real control cells.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.evaluation import delta_metrics
from vcc2026.manifest import RunManifest, file_fingerprint
from vcc2026.resources import peak_rss_bytes, snapshot
from vcc2026.signatures import SignatureSet
from vcc2026.splits import bootstrap_targets

# prior_sd = 1e6 makes the per-gene shrinkage weight ~1, i.e. the raw unshrunk
# delta. It is in the grid so "no shrinkage" competes on equal footing.
PRIOR_SD_GRID = [0.05, 0.1, 0.25, 0.5, 1.0, 4.0, 1e6]
ALPHA_MAX = 2.0
ALPHA_REPORT_GRID = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]


def _shared_targets(src_npz: Path, dst_npz: Path) -> list[str]:
    """Targets both sides measure, read from the small row sidecars.

    The sidecar is a few hundred kilobytes; the arrays are hundreds of
    megabytes. Deciding what to load before loading it is the same discipline
    stage 40 applies to target selection, for the same reason.
    """
    def targets_of(path: Path) -> set[str]:
        rows = json.loads(path.with_suffix(".rows.json").read_text(encoding="utf-8"))
        return {r["target"] for r in rows}

    return sorted(targets_of(src_npz) & targets_of(dst_npz))


def _collapse_one(npz: Path, targets, want_se: bool):
    """Load one signature set, collapse its guides, return dense arrays.

    Loaded and released one side at a time: the raw set and its collapsed form
    are each several hundred megabytes, and holding both sides of the pair at
    once has already exhausted this machine (CP-0003 §3.7).
    """
    sigs = SignatureSet.read_npz(npz, targets=targets).collapse_guides()
    by = {s.target: s for s in sigs}
    missing = [t for t in targets if t not in by]
    if missing:
        raise SystemExit(f"{npz.name}: {len(missing)} expected targets absent")
    first = by[targets[0]].observed
    constant = all(np.array_equal(s.observed, first) for s in sigs)
    observed = first.copy()
    if not constant:
        for s in sigs:
            observed &= s.observed
    audit = {
        "n_signatures_after_collapse": len(sigs),
        "coverage_constant_across_targets": bool(constant),
        "n_genes_observed": int(observed.sum()),
    }
    delta = np.vstack([by[t].delta for t in targets]).astype(np.float64)
    se = (
        np.vstack([by[t].se for t in targets]).astype(np.float64) if want_se else None
    )
    n_guides = np.array([by[t].meta.get("n_guides", 1) for t in targets])
    del sigs, by
    gc.collect()
    return delta, se, observed, audit, n_guides


def collapsed_matrices(src_npz: Path, dst_npz: Path):
    """Shared targets as aligned matrices, plus a coverage-leakage audit.

    Guides collapse BEFORE anything is split, which is what keeps every guide
    and every TSS row of a target on one side of every fold.
    """
    targets = _shared_targets(src_npz, dst_npz)
    if not targets:
        raise SystemExit("no shared targets between the two signature sets")

    dd_full, _, dst_obs, dst_audit, _ = _collapse_one(dst_npz, targets, want_se=False)
    sd_full, ss_full, src_obs, src_audit, n_guides = _collapse_one(
        src_npz, targets, want_se=True
    )

    mask = src_obs & dst_obs
    sd = np.ascontiguousarray(sd_full[:, mask])
    ss = np.ascontiguousarray(ss_full[:, mask])
    dd = np.ascontiguousarray(dd_full[:, mask])
    del sd_full, ss_full, dd_full
    gc.collect()

    constant_both = (
        src_audit["coverage_constant_across_targets"]
        and dst_audit["coverage_constant_across_targets"]
    )
    audit = {
        "source": src_audit,
        "destination": dst_audit,
        "n_genes_intersection": int(mask.sum()),
        "leakage_note": (
            "Per-target coverage is constant within each source, so the shared "
            "gene mask is a property of the two datasets and carries no "
            "information about which targets were held out."
            if constant_both else
            "Coverage is NOT constant across targets within a source: the shared "
            "mask depends on which targets are present, and this script's "
            "assumption does not hold."
        ),
        "coverage_constant_both_sides": bool(constant_both),
    }
    return tuple(targets), sd, ss, dd, mask, audit, n_guides


def sufficient_statistics(sd, ss, dd):
    """Per-target inner products, one set per candidate `prior_sd`.

    For a fixed `prior_sd` the prediction is `alpha * P` with
    `P = delta * prior_sd^2 / (prior_sd^2 + se^2)`, so pooled squared error over
    any set of rows S is

        SSE(alpha) = alpha^2 * sum_S <P,P> - 2 alpha * sum_S <P,Y> + sum_S <Y,Y>

    Three per-row scalars therefore describe every row subset and every alpha
    exactly. Precomputing them turns the whole nested loop into arithmetic on
    length-n_targets vectors, instead of rebuilding a 2,350 x 6,714 matrix once
    per fold.
    """
    syy = np.einsum("ij,ij->i", dd, dd)
    stats = {}
    for prior_sd in PRIOR_SD_GRID:
        w = prior_sd**2 / (prior_sd**2 + np.square(ss))
        P = sd * w
        stats[prior_sd] = {
            "spp": np.einsum("ij,ij->i", P, P),
            "spy": np.einsum("ij,ij->i", P, dd),
        }
        del w, P
    gc.collect()
    return syy, stats


def _sse(stat, syy, rows, alpha):
    spp = stat["spp"][rows].sum()
    spy = stat["spy"][rows].sum()
    return alpha**2 * spp - 2 * alpha * spy + syy[rows].sum()


def _best_alpha(stat, rows):
    """Closed-form MSE minimiser over alpha on `rows`, clipped to [0, ALPHA_MAX]."""
    spp = stat["spp"][rows].sum()
    if spp <= 0:
        return 0.0
    return float(np.clip(stat["spy"][rows].sum() / spp, 0.0, ALPHA_MAX))


def fold_assignment(n: int, n_folds: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    order = rng.permutation(n)
    fold_of = np.empty(n, dtype=int)
    for rank, idx in enumerate(order):
        fold_of[idx] = rank % n_folds
    return fold_of


def select_parameters(syy, stats, rows, *, n_folds: int, seed: int) -> dict:
    """Choose (alpha, prior_sd) using ONLY `rows`.

    `prior_sd` is scored by cross-validated error inside `rows`; `alpha` is then
    refitted in closed form on all of `rows`. Nothing outside `rows` is touched.
    """
    fold_of = fold_assignment(rows.size, n_folds, seed)
    table = []
    for prior_sd in PRIOR_SD_GRID:
        stat = stats[prior_sd]
        ratios = []
        for fold in range(n_folds):
            tr = rows[fold_of != fold]
            va = rows[fold_of == fold]
            if tr.size == 0 or va.size == 0:
                continue
            alpha = _best_alpha(stat, tr)
            null_sse = syy[va].sum()
            if null_sse <= 0:
                continue
            ratios.append(_sse(stat, syy, va, alpha) / null_sse)
        table.append({
            "prior_sd": prior_sd,
            "inner_folds": len(ratios),
            "cv_mse_vs_null": float(np.mean(ratios)) if ratios else None,
            "cv_mse_vs_null_sd": float(np.std(ratios)) if len(ratios) > 1 else None,
        })
    scored = [r for r in table if r["cv_mse_vs_null"] is not None]
    if not scored:
        raise SystemExit("inner selection produced no usable fold")
    best = min(scored, key=lambda r: r["cv_mse_vs_null"])
    prior_sd = best["prior_sd"]
    alpha = _best_alpha(stats[prior_sd], rows)
    return {
        "alpha": alpha,
        "prior_sd": prior_sd,
        "inner_n_folds": n_folds,
        "inner_selection_table": table,
        "inner_cv_mse_vs_null_at_choice": best["cv_mse_vs_null"],
        "n_selection_targets": int(rows.size),
    }


def per_target_metrics(sd, ss, dd, rows, alpha, prior_sd) -> list:
    """Proxy metrics per target, for the rows a fold held out."""
    w = prior_sd**2 / (prior_sd**2 + np.square(ss[rows]))
    P = alpha * sd[rows] * w
    Y = dd[rows]
    full = np.ones(P.shape[1], dtype=bool)
    return [delta_metrics(P[i], Y[i], full) for i in range(P.shape[0])]


def aggregate(pooled: dict, key: str) -> float | None:
    vals = np.asarray(pooled[key], dtype=np.float64)
    vals = vals[np.isfinite(vals)]
    return float(np.median(vals)) if vals.size else None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", default="c001")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--signatures", type=Path, required=True)
    p.add_argument("--source", default="k562_gwps")
    p.add_argument("--target", default="rpe1_essential",
                   help="development destination; NOT an official context")
    p.add_argument("--outer-folds", type=int, default=5)
    p.add_argument("--inner-folds", type=int, default=4)
    p.add_argument("--n-boot", type=int, default=1000)
    p.add_argument("--seed", type=int, default=20260912)
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    t0 = time.perf_counter()
    run = args.out or config.run_dir(args.run_id)
    run.mkdir(parents=True, exist_ok=True)
    out = run / "calibration.json"
    state_path = run / "fitted_state.json"
    for pth in (out, state_path):
        if pth.exists() and not args.allow_overwrite:
            raise SystemExit(f"{pth} exists; use a new --run-id")

    src_npz = args.signatures / f"{args.source}.npz"
    dst_npz = args.signatures / f"{args.target}.npz"
    for pth in (src_npz, dst_npz):
        if not pth.exists():
            raise SystemExit(f"{pth} missing; run 40_build_signatures.py first")

    print(f"development experiment: {args.source} -> {args.target}")
    targets, sd, ss, dd, mask, audit, n_guides = collapsed_matrices(src_npz, dst_npz)
    n_t = len(targets)
    print(f"shared targets {n_t}, shared genes {int(mask.sum())}, "
          f"median guides/target {float(np.median(n_guides)):.1f}")
    if not audit["coverage_constant_both_sides"]:
        raise SystemExit(
            "per-target coverage is not constant within a source; the constant-"
            "coverage assumption behind the shared gene mask does not hold and "
            "this script would need per-fold train-only masks"
        )

    syy, stats = sufficient_statistics(sd, ss, dd)

    # --- outer loop: reporting only ------------------------------------------
    fold_of = fold_assignment(n_t, args.outer_folds, args.seed)
    all_rows = np.arange(n_t)
    oof = {k: np.full(n_t, np.nan) for k in
           ("pearson", "spearman", "cosine", "mse", "sign_strong", "n_strong")}
    oof_alpha = np.full(n_t, np.nan)
    oof_prior = np.full(n_t, np.nan)
    per_fold = []

    for fold in range(args.outer_folds):
        train = all_rows[fold_of != fold]
        test = all_rows[fold_of == fold]
        if train.size == 0 or test.size == 0:
            continue
        overlap = set(train.tolist()) & set(test.tolist())
        if overlap:
            raise SystemExit(f"outer fold {fold}: {len(overlap)} targets on both sides")
        sel = select_parameters(syy, stats, train, n_folds=args.inner_folds,
                                seed=args.seed + 1000 + fold)
        alpha, prior_sd = sel["alpha"], sel["prior_sd"]

        n_vals = test.size * int(mask.sum())
        null_mse = float(syy[test].sum() / n_vals)
        tuned_mse = float(_sse(stats[prior_sd], syy, test, alpha) / n_vals)
        full_amp_mse = float(_sse(stats[1e6], syy, test, 1.0) / n_vals)

        mets = per_target_metrics(sd, ss, dd, test, alpha, prior_sd)
        for i, row in enumerate(test):
            oof["pearson"][row] = mets[i].pearson
            oof["spearman"][row] = mets[i].spearman
            oof["cosine"][row] = mets[i].cosine
            oof["mse"][row] = mets[i].mse
            oof["sign_strong"][row] = mets[i].sign_agreement_strong
            oof["n_strong"][row] = mets[i].n_strong
            oof_alpha[row] = alpha
            oof_prior[row] = prior_sd

        grid_on_test = [
            {"alpha": a,
             "mse_vs_null": float(_sse(stats[prior_sd], syy, test, a) / n_vals / null_mse)}
            for a in ALPHA_REPORT_GRID
        ] if null_mse > 0 else []

        per_fold.append({
            "fold": fold,
            "n_train_targets": int(train.size),
            "n_test_targets": int(test.size),
            "selected": {"alpha": alpha, "prior_sd": prior_sd},
            "inner_selection": sel,
            "held_out": {
                "pooled_mse": tuned_mse,
                "pooled_mse_null": null_mse,
                "mse_vs_null_selected": tuned_mse / null_mse if null_mse > 0 else None,
                "mse_vs_null_zero_response": 1.0,
                "mse_vs_null_full_amplitude": (
                    full_amp_mse / null_mse if null_mse > 0 else None
                ),
                "median_pearson": float(np.nanmedian(
                    [m.pearson for m in mets])) if mets else None,
            },
            "mse_vs_null_by_alpha_on_held_out": grid_on_test,
        })
        print(f"  fold {fold}: alpha={alpha:.4f} prior_sd={prior_sd:g} "
              f"-> held-out MSE/null {tuned_mse / null_mse:.4f} "
              f"(alpha=1 unshrunk {full_amp_mse / null_mse:.4f})")

    # --- out-of-fold summary, the honest held-out estimate --------------------
    finite = np.isfinite(oof["mse"])
    n_vals_all = int(finite.sum()) * int(mask.sum())
    oof_pooled_mse = float(np.nansum(oof["mse"][finite] * int(mask.sum())) / n_vals_all)
    oof_null_mse = float(syy[finite].sum() / n_vals_all)

    boot = None
    pears = oof["pearson"][np.isfinite(oof["pearson"])]
    if args.n_boot and pears.size:
        draws = bootstrap_targets(range(pears.size), n_boot=args.n_boot, seed=args.seed)
        meds = np.array([np.median(pears[d]) for d in draws])
        idx = np.flatnonzero(finite)
        mse_i = oof["mse"][idx]
        null_i = syy[idx] / int(mask.sum())
        rdraws = bootstrap_targets(range(idx.size), n_boot=args.n_boot, seed=args.seed + 7)
        ratios = np.array([mse_i[d].sum() / null_i[d].sum() for d in rdraws])
        boot = {
            "unit": "target (out-of-fold predictions only)",
            "n_targets": int(pears.size),
            "n_boot": args.n_boot,
            "median_pearson": {
                "point": float(np.median(pears)),
                "ci95": [float(np.percentile(meds, 2.5)),
                         float(np.percentile(meds, 97.5))],
            },
            "pooled_mse_vs_null": {
                "point": float(mse_i.sum() / null_i.sum()),
                "ci95": [float(np.percentile(ratios, 2.5)),
                         float(np.percentile(ratios, 97.5))],
            },
            "frac_pearson_gt0": float(np.mean(pears > 0)),
        }

    # --- parameters to ship: same protocol, whole development set -------------
    production = select_parameters(syy, stats, all_rows,
                                   n_folds=args.inner_folds, seed=args.seed + 99)
    production["in_sample_mse_vs_null"] = float(
        _sse(stats[production["prior_sd"]], syy, all_rows, production["alpha"])
        / syy.sum()
    )
    production["full_amplitude_mse_vs_null_in_sample"] = float(
        _sse(stats[1e6], syy, all_rows, 1.0) / syy.sum()
    )
    print(f"\nproduction parameters: alpha={production['alpha']:.4f} "
          f"prior_sd={production['prior_sd']:g}")
    print(f"  selected on all {n_t} development targets by the same inner protocol")
    print(f"  honest held-out estimate is the out-of-fold number, not this one")

    elapsed = time.perf_counter() - t0
    peak = peak_rss_bytes()

    payload = {
        "run_id": args.run_id,
        "stage": "44_calibrate_transfer",
        "development_experiment": {
            "source": args.source,
            "destination": args.target,
            "n_shared_targets": n_t,
            "n_shared_genes": int(mask.sum()),
            "median_guides_per_target": float(np.median(n_guides)),
            "coverage_audit": audit,
        },
        "protocol": {
            "outer_folds": args.outer_folds,
            "inner_folds": args.inner_folds,
            "seed": args.seed,
            "prior_sd_grid": PRIOR_SD_GRID,
            "alpha_selection": (
                "closed-form MSE minimiser on the selection rows, clipped to "
                f"[0, {ALPHA_MAX}]"
            ),
            "description": (
                "Outer folds report; inner folds select. prior_sd is scored by "
                "cross-validated error within the outer-training targets, alpha "
                "is refitted on all outer-training targets, and the pair is "
                "applied blind to the outer-test targets. Guides of a target are "
                "collapsed before splitting, so a target never straddles a fold."
            ),
        },
        "per_outer_fold": per_fold,
        "out_of_fold": {
            "n_targets": int(finite.sum()),
            "pooled_mse": oof_pooled_mse,
            "pooled_mse_null_zero_response": oof_null_mse,
            "mse_vs_null": oof_pooled_mse / oof_null_mse if oof_null_mse > 0 else None,
            "median_pearson": aggregate(oof, "pearson"),
            "median_spearman": aggregate(oof, "spearman"),
            "median_cosine": aggregate(oof, "cosine"),
            "median_sign_agreement_strong": aggregate(oof, "sign_strong"),
            "median_n_strong_genes": aggregate(oof, "n_strong"),
            "alpha_used": {
                "min": float(np.nanmin(oof_alpha)),
                "max": float(np.nanmax(oof_alpha)),
                "median": float(np.nanmedian(oof_alpha)),
            },
            "prior_sd_used": sorted({float(v) for v in oof_prior if np.isfinite(v)}),
        },
        "comparators_out_of_fold": {
            "zero_predicted_response": {
                "mse_vs_null": 1.0,
                "note": "By definition the null: MSE equals mean(truth^2).",
            },
            "full_amplitude_transfer": {
                "mse_vs_null": float(
                    _sse(stats[1e6], syy, np.flatnonzero(finite), 1.0)
                    / syy[finite].sum()
                ),
                "note": "alpha=1, no shrinkage. Not fold-dependent: it has no "
                        "fitted parameter, so its in-sample and held-out values "
                        "coincide.",
            },
        },
        "bootstrap": boot,
        "runtime_seconds": elapsed,
        "peak_rss_bytes": peak,
        "resources_after": snapshot(run).as_dict(),
        "caveat": (
            "PROXY METRICS, NOT VCC SCORES. Everything here is pseudobulk log2 "
            "fold change space on K562 and RPE1. The competition scores "
            "single-cell counts against real held-out control cells in contexts "
            "A/B/C, where no perturbation is observable. What transfers from "
            "this experiment is the calibration method (D-012), not the numbers."
        ),
    }
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    state = {
        "model": "shrunk_transfer",
        "parameters": {
            "alpha": production["alpha"],
            "prior_sd": production["prior_sd"],
            "collapse_guides": True,
        },
        "source_signatures": {
            "source_id": args.source,
            "npz": file_fingerprint(src_npz),
            "rows_json": file_fingerprint(src_npz.with_suffix(".rows.json")),
        },
        "selected_by": {
            "run_id": args.run_id,
            "development_experiment": f"{args.source} -> {args.target}",
            "protocol": "inner cross-validated prior_sd, closed-form alpha",
            "calibration_report": str(out),
        },
        "reconstruct": (
            "ShrunkTransfer(alpha=..., prior_sd=..., source=source_id, "
            "collapse_guides=True).fit(SignatureSet.read_npz(npz))"
        ),
        "transferability_warning": (
            "alpha and prior_sd were measured on a K562 -> RPE1 pair. Applying "
            "them to contexts A/B/C is a HYPOTHESIS, not a measurement: no "
            "perturbation is observable in those contexts."
        ),
        "seed": args.seed,
    }
    state_path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")

    man = RunManifest(run_id=args.run_id, stage="44_calibrate_transfer",
                      config=vars(args), seed=args.seed)
    man.add_input("signatures:source", src_npz)
    man.add_input("signatures:destination", dst_npz)
    man.add_output("calibration", out)
    man.add_output("fitted_state", state_path)
    man.metrics = {
        "out_of_fold": payload["out_of_fold"],
        "comparators": payload["comparators_out_of_fold"],
        "production_parameters": state["parameters"],
    }
    man.note("Nested CV: inner folds select, outer folds report. The bootstrap "
             "resamples out-of-fold targets only.")
    man.note("Proxy metrics in pseudobulk log2FC space. Not a VCC score.")
    man.write(run / "manifest_44_calibrate_transfer.json",
              allow_overwrite=args.allow_overwrite)

    print(f"\nout-of-fold (held-out) MSE/null : {payload['out_of_fold']['mse_vs_null']:.4f}")
    print(f"  zero predicted response       : 1.0000")
    print(f"  full-amplitude transfer       : "
          f"{payload['comparators_out_of_fold']['full_amplitude_transfer']['mse_vs_null']:.4f}")
    print(f"out-of-fold median Pearson      : {payload['out_of_fold']['median_pearson']}")
    if boot:
        ci = boot["pooled_mse_vs_null"]["ci95"]
        print(f"  bootstrap MSE/null 95% CI     : [{ci[0]:.4f}, {ci[1]:.4f}]")
    print(f"runtime {elapsed:.1f}s, peak RSS "
          f"{'unknown' if peak is None else f'{peak / 1024**3:.2f} GiB'}")
    print(f"-> {out}\n-> {state_path}")


if __name__ == "__main__":
    main()
