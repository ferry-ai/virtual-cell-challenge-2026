"""Generator x predictor on real HepG2 cells, with the six VCC metrics.

`docs/BENCHMARK_MODULARE.md` section 6 names this as the single experiment that
would reduce the most uncertainty, and m001 could not run it: there were no real
perturbed single cells on disk. There are now.

Two factors, kept apart on purpose:

* **predictor** -- the log2 fold change per target. `null` predicts no change at
  all; the other arms come from a benchmark run that saved its predictions for
  the fold in which HepG2 is the held-out context.
* **generator** -- how a delta becomes counts. `current` is what the submission
  pipeline does: apply the shift to the pooled control profile, resample real
  library sizes, draw Poisson. `ntc_anchored` starts from a real control *cell*
  and shifts it, so the cell's own sparsity and overdispersion survive.

What this can and cannot say. It measures how far each factor moves the score on
one held-out context, with raw metrics only: there are no published anchors for
an external dataset, so nothing here is normalised and nothing is a leaderboard
score. A generator that scores better is not evidence that the predictor is
adequate, and neither is evidence about modularity.

    scripts/py.cmd scripts/56_generator_x_predictor.py \
        --predictions <run>/models/new_context_seen_target_k562_rpe1_to_hepg2_seed2026 \
        --out reports/hepg2_2026-09-14
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.evaluation import score_bundle, scorer_fingerprint
from vcc2026.genes import official_axis
from vcc2026.inference import predicted_profile
from vcc2026.manifest import RunManifest
from vcc2026.pseudobulk import _read_categorical
from vcc2026.sampling import resample_library_sizes, sample_counts

NTC_SOURCE_LEVEL = "control"        # HepG2 mirror's own label
NTC_SCORER_LABEL = "non-targeting"  # what the scorer profile expects
PERT_COL = "target"                 # vcc2026 profile's pert_col
MAX_STORED_PER_CELL = 13_200
MAX_COUNTS_PER_CELL = 1_000_000


def load_predictions(directory: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted(directory.glob("*.predictions.npz")):
        with np.load(path, allow_pickle=True) as handle:
            out[str(handle["arm"])] = {
                "delta": np.asarray(handle["delta"], dtype=np.float64),
                "targets": [str(t) for t in handle["targets"]],
                "observed": np.asarray(handle["observed"], dtype=bool),
                "test_context": str(handle["test_context"]),
                "path": str(path),
            }
    return out


def delta_on_source_genes(
    row: np.ndarray, universe_mask: np.ndarray, gene_positions: np.ndarray
) -> np.ndarray:
    """Put a prediction made on the universe onto this file's gene axis.

    Genes the universe did not cover get 0.0 and are counted, never quietly
    treated as measured-and-unchanged: the caller reports the coverage.
    """
    full = np.zeros(len(universe_mask), dtype=np.float64)
    full[universe_mask] = row
    out = np.zeros(gene_positions.shape[0], dtype=np.float64)
    known = gene_positions >= 0
    out[known] = full[gene_positions[known]]
    return out


def stochastic_round(values: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    floor = np.floor(values)
    return (floor + (rng.random(values.shape) < (values - floor))).astype(np.int64)


def generate_current(
    basal: np.ndarray, delta: np.ndarray, observed: np.ndarray,
    lib_pool: np.ndarray, n_cells: int, rng: np.random.Generator,
) -> tuple[sp.csr_matrix, dict]:
    profile, detail = predicted_profile(basal, delta, observed)
    libs = resample_library_sizes(lib_pool, n_cells, rng)
    counts = sample_counts(
        profile, libs, rng,
        max_stored_per_cell=MAX_STORED_PER_CELL,
        max_counts_per_cell=MAX_COUNTS_PER_CELL,
    )
    return counts, detail


def generate_ntc_anchored(
    ntc_cells: np.ndarray, delta: np.ndarray, observed: np.ndarray,
    basal: np.ndarray, n_cells: int, rng: np.random.Generator,
) -> tuple[sp.csr_matrix, dict]:
    """Shift real control cells instead of sampling around a pooled mean.

    The same compositional shift is used, so the two generators realise the same
    fold changes on the same genes; what differs is the noise the cells carry.
    A gene at zero in the drawn control cell stays at zero -- that is this
    generator's own bias, and the comparison is what measures whether it costs
    more than the Poisson smoothness it removes.
    """
    profile, detail = predicted_profile(basal, delta, observed)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(basal > 0, profile / np.maximum(basal, 1e-12), 1.0)
    ratio = np.where(np.isfinite(ratio), ratio, 1.0)
    picks = rng.integers(0, ntc_cells.shape[0], size=n_cells)
    drawn = ntc_cells[picks].astype(np.float64) * ratio[None, :]
    counts = stochastic_round(drawn, rng)
    counts = np.clip(counts, 0, None)
    detail = dict(detail)
    detail["anchor"] = "real NTC cells, resampled with replacement"
    detail["zero_preserving"] = True
    return sp.csr_matrix(counts.astype(np.float32)), detail


def write_bundle(path: Path, X, obs_targets, var_names) -> Path:
    adata = ad.AnnData(
        X=X if sp.issparse(X) else sp.csr_matrix(X),
        obs=pd.DataFrame({PERT_COL: pd.Categorical(obs_targets)},
                         index=[f"cell{i}" for i in range(len(obs_targets))]),
        var=pd.DataFrame(index=pd.Index(var_names, name=None)),
    )
    adata.write_h5ad(path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5ad", type=Path,
                        default=Path("C:/Users/ferra/vcc2026-data/raw/nadig_hepg2/"
                                     "NadigOConner2024_hepg2.h5ad"))
    parser.add_argument("--predictions", type=Path, required=True,
                        help="a benchmark model directory holding *.predictions.npz")
    parser.add_argument("--arms", nargs="*", default=None,
                        help="which predictor arms to include; default: all found")
    parser.add_argument("--n-targets", type=int, default=30)
    parser.add_argument("--cells-per-target", type=int, default=80)
    parser.add_argument("--ntc-cells", type=int, default=400)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, default=None,
                        help="where the h5ad bundles go; defaults outside the repo")
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / "generator_x_predictor.json"
    if dest.exists() and not args.allow_overwrite:
        raise FileExistsError(f"{dest} exists; give a new --out (never overwrite)")
    work = args.workdir or (config.paths().data_root / "interim" / "hepg2_bundle")
    work.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    predictions = load_predictions(args.predictions)
    if not predictions:
        raise SystemExit(
            f"no *.predictions.npz in {args.predictions}. Run the benchmark with "
            f"evaluation.save_full_predictions: true first."
        )
    contexts = {p["test_context"] for p in predictions.values()}
    if contexts != {"HepG2"}:
        raise SystemExit(f"predictions are for {contexts}, not the HepG2 fold")

    axis = official_axis()
    axis_pos = axis.position()

    with h5py.File(args.h5ad, "r") as handle:
        labels = np.asarray(_read_categorical(handle["obs"], "perturbation"), dtype=str)
        genes = np.asarray(_read_categorical(handle["var"], "gene_name"), dtype=str)
        gene_positions = np.array([axis_pos.get(g, -1) for g in genes], dtype=np.int64)

        any_arm = next(iter(predictions.values()))
        counts_by_target = pd.Series(labels).value_counts()
        eligible = [
            t for t in any_arm["targets"]
            if counts_by_target.get(t, 0) >= args.cells_per_target
        ]
        if len(eligible) < 5:
            raise SystemExit(
                f"only {len(eligible)} held-out targets have "
                f"{args.cells_per_target} cells; lower --cells-per-target"
            )
        order = rng.permutation(len(eligible))
        chosen = sorted(eligible[int(i)] for i in order[: args.n_targets])

        ntc_rows = np.flatnonzero(labels == NTC_SOURCE_LEVEL)
        ntc_rows = np.sort(rng.choice(
            ntc_rows, size=min(args.ntc_cells, ntc_rows.size), replace=False
        ))
        ntc_counts = np.zeros((ntc_rows.size, len(genes)), dtype=np.float64)
        for i, row in enumerate(ntc_rows):
            ntc_counts[i] = handle["X"][int(row), :]

        real_blocks, real_labels = [], []
        for target in chosen:
            rows = np.flatnonzero(labels == target)
            rows = np.sort(rng.choice(
                rows, size=min(args.cells_per_target, rows.size), replace=False
            ))
            block = np.zeros((rows.size, len(genes)), dtype=np.float64)
            for i, row in enumerate(rows):
                block[i] = handle["X"][int(row), :]
            real_blocks.append(block)
            real_labels.extend([target] * rows.size)

    basal = ntc_counts.sum(axis=0)
    lib_pool = ntc_counts.sum(axis=1).astype(np.int64)
    observed_source = np.zeros(len(genes), dtype=bool)
    observed_source[gene_positions >= 0] = True

    real_X = sp.csr_matrix(np.vstack(real_blocks + [ntc_counts]).astype(np.float32))
    real_obs = real_labels + [NTC_SCORER_LABEL] * ntc_rows.size
    real_path = write_bundle(work / "real_hepg2.h5ad", real_X, real_obs, genes)

    # A null predictor is not one of the arms: it is the floor every arm has to
    # beat, and it costs nothing to include.
    arms = dict(predictions)
    if args.arms:
        arms = {k: v for k, v in arms.items() if k in set(args.arms)}
    arms["null_no_change"] = {
        "delta": np.zeros((len(any_arm["targets"]), int(any_arm["observed"].sum()))),
        "targets": any_arm["targets"],
        "observed": any_arm["observed"],
        "test_context": "HepG2",
        "path": "constructed here: delta = 0 for every target",
    }

    generators = {
        "current_poisson_pooled": generate_current,
        "ntc_anchored": generate_ntc_anchored,
    }

    results = []
    for arm_name, arm in sorted(arms.items()):
        index = {t: i for i, t in enumerate(arm["targets"])}
        coverage = []
        for gen_name, generator in generators.items():
            blocks, labels_out = [], []
            details = []
            for target in chosen:
                row = arm["delta"][index[target]]
                delta = delta_on_source_genes(row, arm["observed"], gene_positions)
                covered = observed_source & (gene_positions >= 0)
                coverage.append(float(np.mean(covered)))
                if gen_name == "current_poisson_pooled":
                    counts, detail = generator(
                        basal, delta, covered, lib_pool, args.cells_per_target, rng
                    )
                else:
                    counts, detail = generator(
                        ntc_counts, delta, covered, basal, args.cells_per_target, rng
                    )
                blocks.append(counts)
                labels_out.extend([target] * counts.shape[0])
                details.append(detail)
            pred_X = sp.vstack(blocks + [sp.csr_matrix(ntc_counts.astype(np.float32))],
                               format="csr")
            pred_obs = labels_out + [NTC_SCORER_LABEL] * ntc_rows.size
            pred_path = write_bundle(
                work / f"pred_{arm_name}_{gen_name}.h5ad", pred_X, pred_obs, genes
            )
            scored = score_bundle(pred_path, real_path,
                                  outdir=str(work / f"score_{arm_name}_{gen_name}"))
            # `score_bundle` returns `raw_aggregate` and
            # `per_metric_over_perturbations`. Reading keys that do not exist
            # produced a report whose metric tables were empty while every run
            # reported success -- the failure this repository calls silent.
            raw = scored.get("raw_aggregate") or {}
            per_metric = scored.get("per_metric_over_perturbations") or {}
            if not raw:
                raise RuntimeError(
                    f"{arm_name} x {gen_name}: the scorer returned no aggregate "
                    f"({scored.get('aggregate_error')}). Keys were: {sorted(scored)}"
                )
            results.append({
                "predictor": arm_name,
                "generator": gen_name,
                "metrics_raw": raw,
                "by_metric": {
                    k: {kk: v[kk] for kk in ("mean", "median", "n_finite") if kk in v}
                    for k, v in per_metric.items()
                },
                "all_six_present": scored.get("all_six_present"),
                "all_six_aggregated": scored.get("all_six_aggregated"),
                "aggregate_error": scored.get("aggregate_error"),
                "normalized": scored.get("normalized", False),
                "prediction_source": arm["path"],
                "median_compositional_shift_log2": float(np.median(
                    [d["compositional_shift_log2"] for d in details]
                )),
                "pred_bundle": str(pred_path),
            })
            print(f"scored {arm_name} x {gen_name}", flush=True)

    report = {
        "built_utc": pd.Timestamp.utcnow().isoformat(),
        "context": "HepG2",
        "design": "2 generators x predictors (arms found + a null floor)",
        "real_bundle": str(real_path),
        "n_targets": len(chosen),
        "targets": chosen,
        "cells_per_target": args.cells_per_target,
        "n_ntc_cells": int(ntc_rows.size),
        "target_selection": (
            "the held-out fold's own test targets, filtered only by having enough "
            "cells to sample, then a seeded random subset. Never filtered by effect size."
        ),
        "gene_axis": {
            "axis_used": "the source's own 9,624 genes, shared by prediction and truth",
            "n_genes": int(len(genes)),
            "n_on_official_axis": int((gene_positions >= 0).sum()),
            "note": "this is a local comparison; the official 18,533-gene axis is not "
                    "reconstructed and no leaderboard score is produced",
        },
        "prediction_coverage_mean": float(np.mean(coverage)) if coverage else None,
        "scorer": scorer_fingerprint(),
        "normalisation": {
            "anchors_used": False,
            "why": "there are no published baseline/reference anchors for an external "
                   "dataset; raw aggregates only, explicitly distinct from a VCC score",
        },
        "results": results,
        "limits": [
            "Raw metrics on one external context. Not a VCC score, not a submission.",
            "A better generator says nothing about whether the predictor is adequate.",
            "The NTC-anchored generator cannot lift a gene that is zero in the drawn "
            "control cell: that is its own bias, reported rather than hidden.",
            "Control cells are real and identical in every bundle, as the contract asks.",
        ],
    }
    dest.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    manifest = RunManifest(
        run_id=args.out.name, stage="56_generator_x_predictor",
        config={k: str(v) for k, v in vars(args).items()}, seed=args.seed,
    )
    manifest.add_input("h5ad", args.h5ad)
    manifest.add_output("report", dest)
    manifest.metrics = {
        "n_combinations": len(results),
        "n_targets": len(chosen),
        "cells_per_target": args.cells_per_target,
    }
    manifest.note("Raw metrics only; no anchors were invented for an external dataset.")
    manifest.write(args.out / "manifest_56_generator_x_predictor.json",
                   allow_overwrite=args.allow_overwrite)
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
