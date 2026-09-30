"""Generate paired Poisson cells from exact frozen profiles and score all 6 arms.

No Stack import/inference, fitting, outcome-based choices or partial verdicts.
The complete prospective protocol is PROTOCOLLO_STACK_CONFERMA.md.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

import stack_pilot as pilot
import score_stack_pilot as scorer
import stack_confirmation_pack as packer
from stack_confirmation_pack import EXPECTED
import vcc2026
from vcc2026.sampling import resample_library_sizes, sample_counts

PROTOCOL_SHA = "2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2"
SCORER_HELPER_SHA = "2d4dc6503c5ac58c6ca8ad2f3002b5d37c6293818a2179559c3fa68a0537ff37"
ANCHORS_SHA = "1821f7af101034a83361577051fe686858602b212becd64548d3ff7517e4f52e"
PILOT_SHA = "b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508"
SEEDS = (1, 2, 3)
ARMS = ("transfer", "stack")
FIVE = scorer.FIVE


def target_rng(seed, target):
    hashed = hashlib.sha256(target.encode("utf-8")).digest()
    words = [int.from_bytes(hashed[i:i + 4], "little") for i in (0, 4)]
    return np.random.default_rng(np.random.SeedSequence([int(seed), *words]))


class PoissonObserver:
    """Observe cap incidence without changing draws or returned count arrays."""
    def __init__(self, rng, count_cap=1000000, storage_cap=12000):
        self.rng, self.count_cap, self.storage_cap = rng, count_cap, storage_cap
        self.diagnostics = {}

    def poisson(self, rates):
        counts = self.rng.poisson(rates)
        totals = counts.sum(axis=1)
        hot = np.flatnonzero(totals > self.count_cap)
        nnz_after_count_cap = np.count_nonzero(counts, axis=1)
        # This computes only the diagnostic for the same deterministic cap rule;
        # the original array and RNG are left untouched for sample_counts.
        for i in hot:
            nnz_after_count_cap[i] = np.count_nonzero(np.floor(counts[i] * (self.count_cap / totals[i])))
        self.diagnostics = {"count_cap_cells": int(len(hot)),
            "storage_cap_cells": int(np.sum(nnz_after_count_cap > self.storage_cap)),
            "raw_poisson_max_total": int(totals.max(initial=0))}
        return counts


def generate_profile(profile, libraries, target, seed):
    rng = target_rng(seed, target)
    sizes = resample_library_sizes(libraries, 400, rng)
    observer = PoissonObserver(rng)
    x = sample_counts(profile, sizes, observer, max_stored_per_cell=12000,
                      max_counts_per_cell=1000000, overdispersion=None)
    pilot.validate_counts(x)
    detail = {"target": target, "seed": seed, "cells": 400,
        "input_library_cap_cells": int(np.sum(sizes > 1000000)),
        "sampled_libraries_sha256": hashlib.sha256(sizes.tobytes()).hexdigest(),
        "max_output_total": float(np.asarray(x.sum(axis=1)).max()),
        "max_output_nnz": int(np.diff(x.indptr).max()), **observer.diagnostics}
    return x, detail


def validate_profiles(profiles, targets, genes):
    required = {"targets", "genes", "transfer", "stack", "basal", "library_sizes", "shared"}
    if set(profiles) != required:
        raise ValueError("Profile archive field set differs")
    if list(profiles["targets"]) != list(targets) or list(profiles["genes"]) != list(genes):
        raise ValueError("Frozen profile target/gene axes differ")
    if len(set(targets)) != len(targets) or len(set(genes)) != len(genes):
        raise ValueError("Duplicated profile target/gene identifiers")
    if profiles["targets"].dtype.kind not in "US" or profiles["genes"].dtype.kind not in "US":
        raise ValueError("Axes must have explicit non-object string dtype")
    for arm in ARMS:
        x = profiles[arm]
        if x.dtype != np.float64 or x.shape != (len(targets), len(genes)):
            raise ValueError("Profiles require exact float64 values on the complete axis")
        if not np.isfinite(x).all() or np.any(x < 0) or np.any(x.sum(1) <= 0):
            raise ValueError("Invalid profile mass")
    shared = profiles["shared"]
    if shared.dtype != bool or shared.shape != (len(genes),) or not shared.any():
        raise ValueError("Invalid shared measurement mask")
    if not np.array_equal(profiles["transfer"][:, ~shared], profiles["stack"][:, ~shared]):
        raise ValueError("Stack changed the fallback outside shared support")
    if not np.allclose(profiles["transfer"].sum(1), profiles["stack"].sum(1), rtol=1e-12, atol=0):
        raise ValueError("Stack changed baseline total mass")
    for key, expected_shape in (("basal", (len(genes),)), ("library_sizes", (2000,))):
        values = profiles[key]
        if values.dtype != np.float64 or values.shape != expected_shape or not np.isfinite(values).all() or np.any(values < 0):
            raise ValueError(f"Invalid {key}")
    if np.any(profiles["library_sizes"] <= 0):
        raise ValueError("Zero-library destination controls")


def inference_log2_effect(lfc, numpy_version):
    """Reproduce the recorded inference dtype promotion; never edit exported q0.

    NumPy 1.x demoted the float64 log(2) scalar for a float32 array. NEP50
    retains that scalar dtype in 2.x. This affects the verification guard only.
    """
    major = int(str(numpy_version).split('.')[0])
    if major not in (1, 2):
        raise ValueError('Unreviewed inference NumPy promotion semantics')
    values = np.asarray(lfc)
    if values.dtype not in (np.dtype('float32'), np.dtype('float64')):
        raise ValueError('Unreviewed frozen transfer dtype')
    dtype = values.dtype if major == 1 else np.dtype('float64')
    return np.divide(values, np.asarray(np.log(2.), dtype=dtype), dtype=dtype)


def decision(delta, per_seed, interval, pds_delta, valid=True):
    if not valid or interval is None or len(interval) != 2 or len(per_seed) != 3:
        return False
    values = [delta, pds_delta, *per_seed, *interval]
    return bool(np.isfinite(values).all() and delta >= .005 and all(d > 0 for d in per_seed)
                and 0 < interval[0] <= interval[1] and pds_delta >= 0)


def compare(candidate, reference, anchors, bootstrap_indices=None):
    """One target draw shared across seeds/heads; never filter incomplete draws."""
    a, b = np.asarray(candidate, dtype=float), np.asarray(reference, dtype=float)
    if a.shape != b.shape or a.ndim != 3 or a.shape[0] != 3 or a.shape[2] != len(FIVE):
        raise ValueError("Need complete 3-seed by target by 5-member arrays")
    if a.shape[1] == 0 or np.isinf(a).any() or np.isinf(b).any():
        raise ValueError("No targets or infinite metric values")
    mask = np.isfinite(a)
    if not np.array_equal(mask, np.isfinite(b)) or not np.all(mask == mask[:1]):
        raise ValueError("Metric eligibility changed between arms or seeds")
    pds_index = FIVE.index("pds_cosine")
    if not mask[:, :, pds_index].all() or not mask.any(axis=1).all():
        raise ValueError("Missing PDS or entirely ineligible member")
    spans = np.array([anchors[m]["replicate"] - anchors[m]["baseline"] for m in FIVE])
    if not np.isfinite(spans).all() or np.any(spans == 0):
        raise ValueError("Invalid anchor spans")
    slopes = 1 / spans
    differences = (a - b) * slopes[None, None, :] / 6
    per_seed = np.nanmean(differences, axis=1).sum(axis=1)
    counts = np.isfinite(differences).sum(axis=0)
    averaged = np.divide(np.nansum(differences, axis=0), counts,
                        out=np.full(counts.shape, np.nan), where=counts > 0)
    if bootstrap_indices is None:
        bootstrap_indices = np.random.default_rng(20260929).integers(0, a.shape[1], (2000, a.shape[1]))
    bootstrap_indices = np.asarray(bootstrap_indices)
    if (bootstrap_indices.ndim != 2 or bootstrap_indices.shape[1] != a.shape[1]
            or bootstrap_indices.shape[0] == 0 or bootstrap_indices.dtype.kind not in "iu"
            or np.any(bootstrap_indices < 0) or np.any(bootstrap_indices >= a.shape[1])):
        raise ValueError("Invalid paired target bootstrap indices")
    drawn = averaged[bootstrap_indices]
    n = np.isfinite(drawn).sum(axis=1)
    bootstrap = np.divide(np.nansum(drawn, axis=1), n,
        out=np.full(n.shape, np.nan), where=n > 0).sum(axis=1)
    complete = np.isfinite(bootstrap)
    interval = np.quantile(bootstrap, [.025, .975], method="linear").tolist() if complete.all() else None
    delta, pds_delta = float(per_seed.mean()), float(np.mean(a[:, :, pds_index] - b[:, :, pds_index]))
    summary = {"delta_projection": delta, "per_seed_delta": per_seed.tolist(),
        "seed_sd": float(per_seed.std(ddof=1)), "mean_pds_raw_delta": pds_delta,
        "paired_target_bootstrap_ci95": interval, "bootstrap_complete_fraction": float(complete.mean()),
        "eligible_targets_per_member": dict(zip(FIVE, mask[0].sum(0).tolist())),
        "member_contributions": dict(zip(FIVE, np.nanmean(averaged, axis=0).tolist())),
        "passes_confirmation": decision(delta, per_seed, interval, pds_delta),
        "status": "complete" if complete.all() else "inconclusive_missing_bootstrap_head",
        "bootstrap_scope": "Targets paired; fixed controls, profiles, seeds and full-panel PDS ranks. No ranks recomputed per draw."}
    return summary, bootstrap


def run(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    protocol = Path(__file__).with_name("PROTOCOLLO_STACK_CONFERMA.md")
    if (pilot.sha(scorer.__file__) != SCORER_HELPER_SHA or pilot.sha(args.anchors) != ANCHORS_SHA
            or pilot.sha(pilot.__file__) != PILOT_SHA or pilot.sha(protocol) != PROTOCOL_SHA):
        raise ValueError("Frozen scorer helper or official anchors differ")
    bundle = json.loads((args.bundle / "bundle.json").read_text(encoding="utf-8"))
    infer = json.loads((args.profiles / "inference_manifest.json").read_text(encoding="utf-8"))
    finished = json.loads((args.profiles / "finished.json").read_text(encoding="utf-8"))
    targets = bundle["targets"]
    if targets != EXPECTED or finished["targets"] != targets or finished["final_poisson_seeds"] != list(SEEDS):
        raise ValueError("Confirmation target or seed registration differs")
    if (finished.get("status") != "profiles_exported_no_final_cells_no_scores"
            or finished.get("stack_seed") != pilot.SEED or finished.get("protocol_sha256") != PROTOCOL_SHA
            or finished.get("profile_dtype") != "float64"):
        raise ValueError("Profile export is incomplete or was not generated under this protocol")
    if bundle["protocol_sha256"] != PROTOCOL_SHA or bundle["scoring_code_sha256"] != pilot.sha(__file__):
        raise ValueError("Confirmation protocol or scorer changed after planning")
    expected = {"bundle_sha256": pilot.sha(args.bundle / "bundle.json"),
        "adapter_sha256": bundle["inference_adapter_sha256"], "protocol_sha256": PROTOCOL_SHA,
        "preparation_adapter_sha256": bundle["adapter_sha256"],
        "checkpoint_sha256": pilot.CHECKPOINT_SHA, "genelist_sha256": pilot.GENELIST_SHA}
    for key, value in expected.items():
        if infer.get(key) != value:
            raise ValueError(f"Inference provenance differs: {key}")
    if pilot.sha(args.profiles / "profiles.npz") != finished["profile_sha256"]:
        raise ValueError("Frozen exact profile archive changed")
    if args.truth.stat().st_size != bundle["destination_size"]:
        raise ValueError("Public destination truth source differs")
    for name, expected_sha in bundle["files"].items():
        if Path(name).name != name or pilot.sha(args.bundle / name) != expected_sha:
            raise ValueError("Prepared input changed or has an invalid filename")
    controls = ad.read_h5ad(args.bundle / "destination_controls.h5ad")
    if controls.n_obs != 2000 or set(controls.obs.gene.astype(str)) != {pilot.CONTROL}:
        raise ValueError("Expected same 2000 true destination controls")
    genes, columns = pilot.unique_first(pilot.genes_of(args.truth))
    if list(genes) != list(controls.var_names):
        raise ValueError("Truth and control gene axes differ")
    with np.load(args.profiles / "profiles.npz", allow_pickle=False) as z:
        profiles = {name: z[name] for name in z.files}
    validate_profiles(profiles, targets, genes)
    if int(profiles["shared"].sum()) != infer["shared_genes"]:
        raise ValueError("Shared profile support differs from inference manifest")
    basal = np.asarray(controls.X.sum(axis=0), dtype=np.float64).ravel()
    libraries = np.asarray(controls.X.sum(axis=1), dtype=np.float64).ravel()
    if not np.array_equal(profiles["basal"], basal) or not np.array_equal(profiles["library_sizes"], libraries):
        raise ValueError("Profile archive controls differ from experimental controls")
    with np.load(args.bundle / "transfer.npz", allow_pickle=False) as z:
        if list(z["targets"]) != targets or list(z["genes"]) != list(genes):
            raise ValueError("Frozen transfer axis differs")
        inference_numpy = infer["versions"]["numpy"]
        log2_effects = inference_log2_effect(z["lfc"], inference_numpy)
        reconstructed = np.stack([pilot.predicted_profile(basal, log2_effects[i], z["observed"][i])[0] for i in range(12)])
    exact_q0 = np.array_equal(reconstructed, profiles["transfer"])
    if not np.allclose(reconstructed, profiles["transfer"], rtol=1e-12, atol=0):
        raise ValueError("Exported baseline differs from exact frozen transfer")
    baseline_guard = {"inference_numpy": inference_numpy, "division_dtype": str(log2_effects.dtype),
        "bit_identical_reconstruction": bool(exact_q0), "relative_tolerance_for_arithmetic_only": 1e-12,
        "max_relative_error": float(np.max(np.abs(reconstructed-profiles['transfer'])/
                                           np.maximum(np.abs(profiles['transfer']),1e-300))),
        "sampled_profile": "Exact exported float64 q0; never replaced by reconstructed values"}
    # Record all runtime identities before decoding any destination outcome.
    # The byte hash reads the immutable H5AD as a stream, not expression values.
    input_paths = [args.bundle / "bundle.json", args.profiles / "inference_manifest.json",
        args.profiles / "finished.json", args.profiles / "profiles.npz", args.truth, args.anchors,
        *[args.bundle / name for name in bundle["files"]]]
    inputs = {str(p): {"bytes": p.stat().st_size, "sha256": pilot.sha(p)} for p in input_paths}
    if bundle.get("destination_sha256") is not None and inputs[str(args.truth)]["sha256"] != bundle["destination_sha256"]:
        raise ValueError("Public truth content differs from the preparation identity")
    code_paths = [Path(__file__), Path(pilot.__file__), Path(scorer.__file__), Path(packer.__file__), protocol,
                  *sorted(Path(vcc2026.__file__).parent.glob("*.py"))]
    args.out.mkdir(parents=True)
    pilot.write_json(args.out / "evaluation_manifest.json", {"status": "registered_before_truth_expression_read",
        "targets": targets, "seeds": list(SEEDS), "arms": list(ARMS), "cells_per_target": 400,
        "profile_sha256": finished["profile_sha256"], "protocol_sha256": PROTOCOL_SHA,
        "scoring_code_sha256": pilot.sha(__file__), "inference_provenance": expected,
        "input_files": inputs, "code_sha256": {str(p): pilot.sha(p) for p in code_paths},
        "baseline_reconstruction_guard": baseline_guard,
        "anchors_sha256": ANCHORS_SHA, "versions": {p: importlib.metadata.version(p) for p in ["cell-eval2", "scanpy", "numpy", "scipy", "anndata"]},
        "claim": "One prospective fixed candidate; final verdict only after all six scores; not a VCC score"})
    selected = pilot.rows_for_labels(args.truth, targets)
    if any(len(selected[t]) == 0 for t in targets):
        raise ValueError("Missing preregistered target truth")
    rows = np.sort(np.concatenate([selected[t] for t in targets]))
    labels = np.empty(len(rows), dtype=object)
    for target in targets:
        labels[np.searchsorted(rows, selected[target])] = target
    real_x = pilot.read_rows(args.truth, rows)[:, columns]
    bench = scorer.FrozenTruthBench(real_x, labels, sp.csr_matrix(controls.X), genes, targets, args.out)
    pilot.write_json(args.out / "scorer_config.json", json.loads(json.dumps(asdict(bench.cfg), default=str)))
    tables, diagnostics, aggregation = {}, {}, {}
    for seed in SEEDS:
        for arm in ARMS:
            name, blocks, details = f"{arm}_s{seed}", [], []
            for i, target in enumerate(targets):
                x, detail = generate_profile(profiles[arm][i], libraries, target, seed)
                blocks.append(x); details.append(detail)
            x = sp.vstack(blocks, format="csr")
            pred_labels = np.repeat(targets, 400)
            if x.shape != (4800, len(genes)) or any(d["max_output_total"] > 1000000 or d["max_output_nnz"] > 12000 for d in details):
                raise ValueError("Generated cardinality or caps differ from protocol")
            diagnostics[name] = details
            pilot.write_json(args.out / f"generation_{name}.json", details)
            bench.score(name, x, pred_labels)
            pilot.write_json(args.out / f"result_{name}.json", bench.results[name])
            tables[name] = scorer.per_target(args.out / f"per_pert_{name}.csv", targets)
            aggregation[name] = scorer.verify_aggregation(tables[name], bench.results[name]["raw"])
            del blocks, x
    for seed in SEEDS:
        if [x["sampled_libraries_sha256"] for x in diagnostics[f"transfer_s{seed}"]] != [x["sampled_libraries_sha256"] for x in diagnostics[f"stack_s{seed}"]]:
            raise ValueError("Unpaired final library samples")
    anchors = json.loads(args.anchors.read_text(encoding="utf-8"))["anchors"]
    candidate = np.stack([tables[f"stack_s{s}"][list(FIVE)].to_numpy(float) for s in SEEDS])
    reference = np.stack([tables[f"transfer_s{s}"][list(FIVE)].to_numpy(float) for s in SEEDS])
    summary, bootstrap = compare(candidate, reference, anchors)
    np.savez_compressed(args.out / "bootstrap.npz", delta_projection=bootstrap)
    summary |= {"raw": {name: result["raw"] for name, result in bench.results.items()},
        "aggregation_checks": aggregation, "truth_cells_per_target": {t: len(selected[t]) for t in targets},
        "protocol_sha256": PROTOCOL_SHA, "bootstrap_sha256": pilot.sha(args.out / "bootstrap.npz"),
        "claim": "Local confirmation above frozen K562 transfer, not evidence above t25/t28 or clean pretraining holdout"}
    summary['mse_raw_delta_per_seed'] = [
        float(bench.results[f'stack_s{s}']['raw']['expr_mse_unbiased_capped_norm']-
              bench.results[f'transfer_s{s}']['raw']['expr_mse_unbiased_capped_norm'])
        if all(bench.results[f'{arm}_s{s}']['raw']['expr_mse_unbiased_capped_norm'] is not None
               for arm in ARMS) else None for s in SEEDS]
    pilot.write_json(args.out / "confirmation_comparison.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "profiles", "truth", "anchors", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
