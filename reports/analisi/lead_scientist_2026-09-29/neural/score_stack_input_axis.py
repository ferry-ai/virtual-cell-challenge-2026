"""Score frozen Stack and transfer predictions on public HepG2 truth, separately.

Run only after inference completes. This process never imports Stack or changes
predictions. All 12 preregistered targets and every available truth cell are used.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, replace
import importlib.metadata
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import scipy.sparse as sp

import stack_input_axis_pilot as pilot
from vcc2026.bench import Bench, SCORED, to_anndata
from vcc2026.de_tools import ReferencePool, fast_scorer_de, scorer_config

FIVE = tuple(m for m in SCORED if m != "expr_mse_unbiased_capped_norm")


def validate_prediction(adata, targets, genes):
    if list(adata.var_names) != list(genes):
        raise ValueError("Prediction gene axis differs from prepared controls")
    if "gene" not in adata.obs:
        raise ValueError("Prediction lacks gene labels")
    labels = adata.obs.gene.astype(str).to_numpy()
    counts = pd.Series(labels).value_counts().to_dict()
    if counts != dict.fromkeys(targets, pilot.N_OUTPUT):
        raise ValueError("Prediction must have exactly 400 cells for every planned target")
    x = sp.csr_matrix(adata.X)
    pilot.validate_counts(x)
    if np.diff(x.indptr).max() > 12000 or np.asarray(x.sum(axis=1)).max() > 1000000:
        raise ValueError("Per-cell submission caps violated")
    return x, labels


class FrozenTruthBench(Bench):
    """Same full-truth construction as the preregistered generator bench."""

    def __init__(self, real_x, real_labels, controls, genes, targets, out):
        self.out, self.genes, self.targets = out, np.asarray(genes), sorted(targets)
        self.ctrl, self.seed = controls, pilot.SEED
        self.rng = np.random.default_rng(self.seed)
        cfg = scorer_config()
        self.cfg = replace(cfg, device="cpu", de=replace(cfg.de, backend="scanpy"))
        self.real_ad = to_anndata(sp.vstack([real_x, controls], format="csr"),
            np.r_[real_labels, np.full(controls.shape[0], pilot.CONTROL)], genes)
        self.pool = ReferencePool(controls, genes)
        self.de_real = fast_scorer_de(real_x, real_labels, self.pool)
        self.results = {}


def contrast(stack, transfer, anchors):
    """Five official-anchor slopes / six; keep MSE separate, as preregistered."""
    stack, transfer = stack[list(FIVE)], transfer[list(FIVE)]
    a, b = stack.to_numpy(float), transfer.to_numpy(float)
    if not np.array_equal(np.isfinite(a), np.isfinite(b)):
        raise ValueError("Eligibility changed between arms; pilot cannot be promoted")
    if not np.isfinite(a).any(axis=0).all():
        raise ValueError("At least one member has no eligible target")
    slopes = np.array([1 / (anchors[m]["replicate"] - anchors[m]["baseline"]) for m in FIVE])
    d = (a - b) * slopes / 6
    contributions = np.nanmean(d, axis=0)
    projection = float(contributions.sum())
    pds_delta = float(np.nanmean(a[:, 0] - b[:, 0]))
    indices = np.random.default_rng(pilot.SEED).integers(0, len(a), (2000, len(a)))
    sampled = d[indices]
    n = np.isfinite(sampled).sum(axis=1)
    boot = np.divide(np.nansum(sampled, axis=1), n,
                     out=np.full(n.shape, np.nan, dtype=float), where=n > 0).sum(axis=1)
    finite = np.isfinite(boot)
    return {"delta_projection": projection, "delta_pds_raw": pds_delta,
            "member_contributions": dict(zip(FIVE, map(float, contributions))),
            "eligible_targets_per_member": dict(zip(FIVE, np.isfinite(a).sum(0).tolist())),
            "paired_target_bootstrap_ci95_descriptive": np.quantile(boot, [.025, .975]).tolist() if finite.all() else None,
            "bootstrap_complete_fraction": float(finite.mean()),
            "proceed_to_distinct_confirmation": bool(projection > 0 and pds_delta >= 0),
            "rule": "projection > 0 AND mean PDS not lower; 12 development targets, exploratory only"}


def per_target(path, targets):
    table = pd.read_csv(path)
    if table.duplicated(["perturbation", "metric"]).any():
        raise ValueError("Duplicate per-target metrics")
    if set(table.perturbation.astype(str)) != set(targets):
        raise ValueError("Scorer target set differs from the 12 registered targets")
    result = table.pivot(index="perturbation", columns="metric", values="value").reindex(index=targets)
    if "pds_cosine" not in result or not np.isfinite(result["pds_cosine"].to_numpy(float)).all():
        raise ValueError("PDS must be present and finite for all registered targets")
    return result


def verify_inference_provenance(infer, bundle, bundle_sha):
    if bundle.get("adapter_sha256") != pilot.PREPARATION_ADAPTER_SHA:
        raise ValueError("Bundle preparation is not frozen pilot A")
    expected = {"bundle_sha256": bundle_sha, "adapter_sha256": pilot.sha(pilot.__file__),
                "preparation_adapter_sha256": pilot.PREPARATION_ADAPTER_SHA,
                "ab_protocol_sha256": pilot.AB_PROTOCOL_SHA, "input_axis_policy": pilot.INPUT_AXIS_POLICY,
                "checkpoint_sha256": pilot.CHECKPOINT_SHA, "genelist_sha256": pilot.GENELIST_SHA}
    for field, value in expected.items():
        if infer.get(field) != value:
            raise ValueError(f"Prediction provenance differs from registration: {field}")


def verify_aggregation(table, raw):
    """MSE is a ratio of sums, unlike the five mean-aggregated scored members."""
    for metric in FIVE:
        actual, expected = table[metric].mean(), raw[metric]
        if expected is not None and (not np.isfinite(actual) or abs(actual - expected) > 1e-8):
            raise ValueError(f"Per-target aggregation disagrees with scorer: {metric}")
    numerator, denominator = "expr_mse_unbiased_capped", "expr_distance_unbiased"
    if numerator not in table or denominator not in table:
        return {"mse_identity": "components unavailable; authoritative scorer aggregate retained"}
    n, d = table[numerator].to_numpy(float), table[denominator].to_numpy(float)
    use = np.isfinite(n) & np.isfinite(d)
    if not use.any() or d[use].sum() <= 0:
        return {"mse_identity": "nonpositive/absent denominator; authoritative scorer aggregate retained"}
    ratio = float(n[use].sum() / d[use].sum())
    expected = raw["expr_mse_unbiased_capped_norm"]
    if expected is None or abs(ratio - expected) > 1e-8:
        raise ValueError("MSE ratio-of-sums disagrees with scorer aggregate")
    return {"mse_identity": "verified ratio of summed capped numerator to summed distance",
            "numerator_sum": float(n[use].sum()), "denominator_sum": float(d[use].sum()),
            "ratio": ratio, "eligible_targets": int(use.sum())}


def main():
    import anndata as ad
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["bundle", "prediction", "truth", "anchors", "out"]:
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    bundle = json.loads((a.bundle / "bundle.json").read_text())
    finished = json.loads((a.prediction / "finished.json").read_text())
    infer = json.loads((a.prediction / "inference_manifest.json").read_text())
    targets = bundle["targets"]
    if len(targets) != 12 or finished["targets"] != targets or finished["cells_per_target"] != 400:
        raise ValueError("Prediction target registration differs")
    verify_inference_provenance(infer, bundle, pilot.sha(a.bundle / "bundle.json"))
    if a.truth.stat().st_size != bundle["destination_size"]:
        raise ValueError("Public destination source differs from preparation")
    for name in ["destination_controls.h5ad", "transfer.npz"]:
        if pilot.sha(a.bundle / name) != bundle["files"][name]:
            raise ValueError("Prepared controls/effects changed")
    controls = ad.read_h5ad(a.bundle / "destination_controls.h5ad")
    if set(controls.obs.gene.astype(str)) != {pilot.CONTROL}:
        raise ValueError("Expected destination controls only")
    genes, cols = pilot.unique_first(pilot.genes_of(a.truth))
    if list(genes) != list(controls.var_names):
        raise ValueError("Truth axis differs from the prepared destination axis")
    # Validate every prediction before opening any perturbed truth expression.
    predictions = {}
    for arm in ["transfer", "stack"]:
        obj = ad.read_h5ad(a.prediction / f"prediction_{arm}.h5ad")
        predictions[arm] = validate_prediction(obj, targets, genes)
    a.out.mkdir(parents=True)
    pilot.write_json(a.out / "evaluation_manifest.json", {"status": "registered_before_truth_expression_read",
        "targets": targets, "bundle_sha256": pilot.sha(a.bundle / "bundle.json"),
        "anchors_sha256": pilot.sha(a.anchors), "scoring_code_sha256": pilot.sha(__file__),
        "prediction_hashes": {arm: pilot.sha(a.prediction / f"prediction_{arm}.h5ad") for arm in predictions},
        "versions": {m: importlib.metadata.version(m) for m in ["cell-eval2", "scanpy", "numpy", "scipy", "anndata"]},
        "truth": "all cells per target; fixed real controls from inference preparation",
        "not_vcc_score": True, "pretraining_holdout_verified": False})
    selected = pilot.rows_for_labels(a.truth, targets)
    if any(len(selected[t]) == 0 for t in targets):
        raise ValueError("Public truth has an empty preregistered target")
    rows = np.sort(np.concatenate([selected[t] for t in targets]))
    labels = np.empty(len(rows), dtype=object)
    for target in targets:
        labels[np.searchsorted(rows, selected[target])] = target
    real_x = pilot.read_rows(a.truth, rows)[:, cols]
    bench = FrozenTruthBench(real_x, labels, sp.csr_matrix(controls.X), genes, targets, a.out)
    pilot.write_json(a.out / "scorer_config.json", json.loads(json.dumps(asdict(bench.cfg), default=str)))
    for arm, (x, y) in predictions.items():
        bench.score(arm, x, y)
        pilot.write_json(a.out / f"result_{arm}.json", bench.results[arm])
    tables = {arm: per_target(a.out / f"per_pert_{arm}.csv", targets) for arm in predictions}
    aggregate_checks = {arm: verify_aggregation(table, bench.results[arm]["raw"])
                        for arm, table in tables.items()}
    anchors = json.loads(a.anchors.read_text())["anchors"]
    summary = contrast(tables["stack"], tables["transfer"], anchors)
    summary |= {"raw": {k: v["raw"] for k, v in bench.results.items()},
                "aggregation_checks": aggregate_checks,
                "truth_cells_per_target": {t: len(selected[t]) for t in targets},
                "claim": "Paired 12-target development pilot; five-member projection, MSE reported separately; not a VCC score",
                "scope_caveat": "PDS uses this 12-target local panel and is not directly comparable with a 48/96/300-target panel",
                "pretraining_holdout_verified": False}
    pilot.write_json(a.out / "pilot_comparison.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
