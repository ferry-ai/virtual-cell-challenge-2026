"""Stage 2: measure how well a response transfers, and calibrate its amplitude.

The question this stage answers is the one blocking decision D-006 -- whether to
compress predicted amplitude, and by how much -- and it answers it with data
already on disk, without the single-cell evaluation bundle that D-003 waits for.

Protocol. Source signatures predict a held-out context's measured response on
targets shared by both. Targets are split whole into K folds; the shrinkage grid
is searched on training targets only and applied blind to the test targets.
Every cross-context number is framed by two references:

* a **same-line reference** (K562 essential vs K562 genome-wide) -- two
  experiments in one cell line, so its agreement approximates the reliability
  ceiling that measurement noise alone allows. Cross-lineage transfer should be
  read as a fraction of this, not against 1.0.
* an **oracle amplitude**, the least-squares slope of truth on prediction. It is
  the alpha an oracle would choose to minimise MSE, so the gap between it and
  the cross-validated alpha shows whether the selection protocol works.

Why MSE and not correlation selects the amplitude: correlation is scale
invariant, so it is indifferent to alpha and cannot choose one. The competition's
expression metric and its NMAE are not.

This produces no VCC score. It works in pseudobulk log2-fold-change space; the
competition metrics need single-cell counts scored against real controls.

    scripts/py.cmd scripts/41_transfer_experiment.py --run-id e001
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.evaluation import delta_metrics
from vcc2026.manifest import RunManifest
from vcc2026.signatures import SignatureSet
from vcc2026.splits import bootstrap_targets

ALPHA_GRID = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
PRIOR_SD_GRID = [0.1, 0.25, 0.5, 1.0, 4.0]


def build_matrices(src: SignatureSet, dst: SignatureSet):
    """Stack shared targets into aligned (n_targets x n_genes) matrices.

    Returns (targets, src_delta, src_se, dst_delta, mask) where `mask` is the
    per-gene intersection of what both contexts measured. Genes outside it are
    excluded rather than zero-filled: zero-filling both sides would manufacture
    agreement out of a shared absence of evidence.
    """
    src_c = src.collapse_guides()
    dst_c = dst.collapse_guides()
    src_by = {s.target: s for s in src_c}
    dst_by = {s.target: s for s in dst_c}
    targets = sorted(set(src_by) & set(dst_by))
    if not targets:
        return (), None, None, None, None

    n = len(src_c.signatures[0].delta)
    mask = np.ones(n, dtype=bool)
    for s in src_c:
        mask &= s.observed
    for s in dst_c:
        mask &= s.observed

    sd = np.vstack([src_by[t].delta for t in targets]).astype(np.float64)
    ss = np.vstack([src_by[t].se for t in targets]).astype(np.float64)
    dd = np.vstack([dst_by[t].delta for t in targets]).astype(np.float64)
    return tuple(targets), sd[:, mask], ss[:, mask], dd[:, mask], mask


def grid_search(sd, ss, dd, rows) -> dict:
    """Pick (alpha, prior_sd) minimising pooled MSE on `rows`, in closed form.

    For a fixed prior_sd the prediction is `alpha * P` with
    `P = delta * prior_sd^2 / (prior_sd^2 + se^2)`, so pooled MSE is a quadratic
    in alpha:

        MSE(alpha) = (alpha^2 * <P,P> - 2 alpha * <P,Y> + <Y,Y>) / N

    Three inner products per prior_sd therefore score the entire alpha grid, and
    `<P,Y> / <P,P>` is the exact minimiser. This replaces a 30-point search over
    per-target metric computations, which dominated the runtime.
    """
    Y = dd[rows]
    syy = float(np.sum(Y * Y))
    n = Y.size
    best = None
    table = []
    for prior_sd in PRIOR_SD_GRID:
        w = prior_sd**2 / (prior_sd**2 + np.square(ss[rows]))
        P = sd[rows] * w
        spp = float(np.sum(P * P))
        spy = float(np.sum(P * Y))
        oracle = spy / spp if spp > 0 else 0.0
        for alpha in ALPHA_GRID:
            mse = (alpha**2 * spp - 2 * alpha * spy + syy) / n
            table.append({"alpha": alpha, "prior_sd": prior_sd,
                          "mse_vs_null": mse / (syy / n) if syy > 0 else None})
            if best is None or mse < best["mse"]:
                best = {"alpha": alpha, "prior_sd": prior_sd, "mse": mse,
                        "oracle_alpha": oracle}
    best["mse_vs_null"] = best["mse"] / (syy / n) if syy > 0 else None
    best["grid"] = table
    return best


def evaluate_rows(sd, ss, dd, rows, alpha: float, prior_sd: float) -> dict:
    """Per-target proxy metrics for one parameter choice, on given rows."""
    w = prior_sd**2 / (prior_sd**2 + np.square(ss[rows]))
    P = alpha * sd[rows] * w
    Y = dd[rows]
    full = np.ones(P.shape[1], dtype=bool)

    per = [delta_metrics(P[i], Y[i], full) for i in range(P.shape[0])]
    out = {"n_targets": len(per), "alpha": alpha, "prior_sd": prior_sd}
    for key in ("pearson", "spearman", "cosine", "mse",
                "sign_agreement", "sign_agreement_strong"):
        vals = np.array([getattr(m, key) for m in per], dtype=np.float64)
        vals = vals[np.isfinite(vals)]
        out[f"{key}_median"] = float(np.median(vals)) if vals.size else None
    pears = np.array([m.pearson for m in per], dtype=np.float64)
    pears = pears[np.isfinite(pears)]
    out["frac_pearson_gt0"] = float(np.mean(pears > 0)) if pears.size else None
    out["pooled_mse"] = float(np.mean(np.square(P - Y)))
    out["pooled_mse_null"] = float(np.mean(np.square(Y)))
    out["pooled_mse_vs_null"] = (
        out["pooled_mse"] / out["pooled_mse_null"] if out["pooled_mse_null"] > 0 else None
    )
    spp = float(np.sum(P * P))
    out["oracle_alpha_given_shape"] = (
        float(np.sum(P * Y) / spp) * alpha if spp > 0 else None
    )
    out["_per_target_pearson"] = pears
    return out


def run_pair(src: SignatureSet, dst: SignatureSet, *, label: str,
             n_folds: int, seed: int, n_boot: int) -> dict:
    targets, sd, ss, dd, mask = build_matrices(src, dst)
    if not targets or len(targets) < n_folds * 2:
        return {"label": label, "n_shared_targets": len(targets),
                "skipped": "too few shared targets"}

    rng = np.random.default_rng(seed)
    order = rng.permutation(len(targets))
    fold_of = np.empty(len(targets), dtype=int)
    for rank, idx in enumerate(order):
        fold_of[idx] = rank % n_folds

    per_fold, chosen = [], []
    for fold in range(n_folds):
        train = np.flatnonzero(fold_of != fold)
        test = np.flatnonzero(fold_of == fold)
        if train.size == 0 or test.size == 0:
            continue
        best = grid_search(sd, ss, dd, train)
        chosen.append({"fold": fold, "alpha": best["alpha"],
                       "prior_sd": best["prior_sd"],
                       "oracle_alpha_train": best["oracle_alpha"]})
        tuned = evaluate_rows(sd, ss, dd, test, best["alpha"], best["prior_sd"])
        # prior_sd=1e6 makes the shrinkage weight ~1: the raw, unshrunk delta.
        untuned = evaluate_rows(sd, ss, dd, test, 1.0, 1e6)
        null = {
            "pooled_mse": float(np.mean(np.square(dd[test]))),
            "pooled_mse_vs_null": 1.0,
            "pearson_median": 0.0,
        }
        for d in (tuned, untuned):
            d.pop("_per_target_pearson", None)
        per_fold.append({"fold": fold, "n_train_targets": int(train.size),
                         "n_test_targets": int(test.size),
                         "selected": {"alpha": best["alpha"],
                                      "prior_sd": best["prior_sd"]},
                         "tuned": tuned, "untuned_alpha1": untuned, "null": null})

    def avg(key, sub):
        vals = [f[sub].get(key) for f in per_fold if f[sub].get(key) is not None]
        return float(np.mean(vals)) if vals else None

    boot = None
    if per_fold and n_boot:
        alpha = float(np.median([c["alpha"] for c in chosen]))
        prior_sd = float(np.median([c["prior_sd"] for c in chosen]))
        allrows = np.arange(len(targets))
        res = evaluate_rows(sd, ss, dd, allrows, alpha, prior_sd)
        pears = res["_per_target_pearson"]
        if pears.size:
            # Bootstrap over TARGETS, the unit of independence. Cells within a
            # perturbation share a guide, a batch and a knockdown efficiency.
            draws = bootstrap_targets(range(pears.size), n_boot=n_boot, seed=seed)
            meds = np.array([np.median(pears[d]) for d in draws])
            boot = {"statistic": "median Pearson over targets",
                    "params": {"alpha": alpha, "prior_sd": prior_sd},
                    "n_targets": int(pears.size),
                    "point": float(np.median(pears)),
                    "ci95": [float(np.percentile(meds, 2.5)),
                             float(np.percentile(meds, 97.5))],
                    "n_boot": n_boot}

    full = grid_search(sd, ss, dd, np.arange(len(targets)))
    return {
        "label": label,
        "n_shared_targets": len(targets),
        "n_shared_genes": int(mask.sum()),
        "n_folds": len(per_fold),
        "selected_per_fold": chosen,
        "oracle_alpha_all_targets": full["oracle_alpha"],
        "cv_mean": {
            "tuned_pearson_median": avg("pearson_median", "tuned"),
            "untuned_pearson_median": avg("pearson_median", "untuned_alpha1"),
            "tuned_mse_vs_null": avg("pooled_mse_vs_null", "tuned"),
            "untuned_mse_vs_null": avg("pooled_mse_vs_null", "untuned_alpha1"),
            "tuned_sign_agreement_strong": avg("sign_agreement_strong_median", "tuned"),
            "untuned_sign_agreement_strong": avg("sign_agreement_strong_median",
                                                 "untuned_alpha1"),
            "tuned_sign_agreement_all": avg("sign_agreement_median", "tuned"),
            "tuned_cosine_median": avg("cosine_median", "tuned"),
            "tuned_frac_pearson_gt0": avg("frac_pearson_gt0", "tuned"),
        },
        "bootstrap": boot,
        "per_fold": per_fold,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", default="e001")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--signatures", type=Path, default=None,
                   help="reuse an existing signature directory instead of "
                        "<run>/signatures")
    p.add_argument("--n-folds", type=int, default=5)
    p.add_argument("--n-boot", type=int, default=500)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    run = args.out or config.run_dir(args.run_id)
    run.mkdir(parents=True, exist_ok=True)
    # Signatures are expensive (minutes) and immutable, so a new experiment
    # reuses an existing set rather than rebuilding it. This is also what lets a
    # remote job ship one signature directory and run many experiments on it.
    sig_dir = args.signatures or (run / "signatures")
    if not sig_dir.exists():
        raise SystemExit(
            f"{sig_dir} missing; run 40_build_signatures.py first, or pass "
            f"--signatures pointing at an existing signature directory"
        )

    available = {f.stem for f in sig_dir.glob("*.npz")}
    print("available: " + ", ".join(sorted(available)) + "\n")

    pairs = [
        ("k562_gwps", "rpe1_essential", "CROSS-LINEAGE: K562 genome-wide -> RPE1"),
        ("k562_essential", "rpe1_essential", "CROSS-LINEAGE: K562 essential -> RPE1"),
        ("k562_essential", "k562_gwps", "SAME-LINE REFERENCE: K562 ess -> K562 gw"),
    ]

    results = []
    for src_id, dst_id, label in pairs:
        if src_id not in available or dst_id not in available:
            continue
        print(f"=== {label}")
        # Load only the two sets this pair needs and drop them afterwards: three
        # resident at once is ~1.3 GB of dense float32 on a 7.8 GB machine.
        src_set = SignatureSet.read_npz(sig_dir / f"{src_id}.npz")
        dst_set = SignatureSet.read_npz(sig_dir / f"{dst_id}.npz")
        res = run_pair(src_set, dst_set, label=label, n_folds=args.n_folds,
                       seed=args.seed, n_boot=args.n_boot)
        del src_set, dst_set
        gc.collect()

        res["source"], res["target_context"] = src_id, dst_id
        results.append(res)
        cv = res.get("cv_mean", {})
        print(f"    shared targets {res['n_shared_targets']}, "
              f"shared genes {res.get('n_shared_genes')}")
        print(f"    alpha per fold    : {[c['alpha'] for c in res.get('selected_per_fold', [])]}")
        print(f"    prior_sd per fold : {[c['prior_sd'] for c in res.get('selected_per_fold', [])]}")
        print(f"    oracle alpha (all): {res.get('oracle_alpha_all_targets')}")
        print(f"    held-out Pearson  : tuned {cv.get('tuned_pearson_median')}  "
              f"untuned {cv.get('untuned_pearson_median')}")
        print(f"    MSE / null MSE    : tuned {cv.get('tuned_mse_vs_null')}  "
              f"untuned {cv.get('untuned_mse_vs_null')}")
        print(f"    sign agr (strong) : {cv.get('tuned_sign_agreement_strong')}")
        if res.get("bootstrap"):
            b = res["bootstrap"]
            print(f"    bootstrap targets : {b['point']:.4f} "
                  f"[{b['ci95'][0]:.4f}, {b['ci95'][1]:.4f}]  n={b['n_targets']}")
        print()

    payload = {
        "run_id": args.run_id,
        "alpha_grid": ALPHA_GRID,
        "prior_sd_grid": PRIOR_SD_GRID,
        "protocol": (
            "Whole targets split into folds; the shrinkage grid is searched on "
            "training targets only; reported numbers are on held-out targets. "
            "Bootstrap resamples targets, not cells."
        ),
        "caveat": (
            "Pseudobulk log2FC space. These are NOT VCC metrics: the competition "
            "scores single-cell counts against real control cells."
        ),
        "results": results,
    }
    out = run / "transfer_experiment.json"
    if out.exists() and not args.allow_overwrite:
        raise SystemExit(f"{out} exists; use a new --run-id or --allow-overwrite")
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    man = RunManifest(run_id=args.run_id, stage="41_transfer_experiment",
                      config=vars(args), seed=args.seed)
    for k in sorted(available):
        man.add_input(f"signatures:{k}", sig_dir / f"{k}.npz")
    man.add_output("transfer_experiment", out)
    man.metrics = {r["label"]: r.get("cv_mean", {}) for r in results}
    man.note("Amplitude alpha is selected on held-out targets by pooled MSE relative "
             "to the null, not by correlation, which is scale-invariant.")
    man.note("Not a VCC score. Pseudobulk cannot produce one.")
    man.write(run / "manifest_41_transfer_experiment.json",
              allow_overwrite=args.allow_overwrite)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
