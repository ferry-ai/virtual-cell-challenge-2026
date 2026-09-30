"""Select one preregistered development variant after both complete results.

No destination truth, confirmation outcomes, model inference or fitting is read.
Baseline cells are compared exactly using bounded CSR hashing, not file-format
identity. Every comparison, provenance and metric file is hashed in the receipt.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

import stack_pilot as pilot

HERE = Path(__file__).resolve().parent
AB_SHA = "181d7a00b1f5957948e2daf9fcd1f66fae9adb35dbf78aab59a5b2c006133506"
BUNDLE_SHA = "16cf30126a7c46ec651c8ed8262b19353e1a3ab07c4dd445590a8a040e36fc29"
ANCHORS_SHA = "1821f7af101034a83361577051fe686858602b212becd64548d3ff7517e4f52e"
ADAPTERS = {"A": "b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508",
            "B": "a85b752dbd5042fde45611e80a6a942733bb19de6c4a00a03ab71db33a90d2a4"}
SCORERS = {"A": "2d4dc6503c5ac58c6ca8ad2f3002b5d37c6293818a2179559c3fa68a0537ff37",
           "B": "74607f249fc36642e74a374e45c32157391b875888efe715163642674045b28c"}
FIVE = ("pds_cosine", "de_wilcoxon_lfc_nmae", "de_wilcoxon_direction_fidelity_yield_raw",
        "de_wilcoxon_direction_reach_raw", "de_wilcoxon_sig_jaccard")
MSE = "expr_mse_unbiased_capped_norm"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def choose(candidates):
    if set(candidates) != {"A", "B"}:
        raise ValueError("Both complete candidates are required")
    eligible = []
    for variant in ("A", "B"):
        row = candidates[variant]
        d, p = row["delta_projection"], row["delta_pds_raw"]
        if not math.isfinite(d) or not math.isfinite(p):
            raise ValueError("Non-finite development comparison")
        valid = bool(d > 0 and p >= 0)
        if row["proceed_to_distinct_confirmation"] is not valid:
            raise ValueError("Recorded pilot gate is inconsistent")
        if valid:
            eligible.append(variant)
    if not eligible:
        return None
    if len(eligible) == 1:
        return eligible[0]
    return "B" if candidates["B"]["delta_projection"] > candidates["A"]["delta_projection"] else "A"


def table(path, targets):
    raw = pd.read_csv(path)
    if set(raw.perturbation.astype(str)) != set(targets) or raw.duplicated(["perturbation", "metric"]).any():
        raise ValueError("Per-target file has missing/extra/duplicated entries")
    result = raw.pivot(index="perturbation", columns="metric", values="value").reindex(targets)
    if not set(FIVE).issubset(result.columns):
        raise ValueError("Missing scored member")
    return result


def verify_tables(tables, comparisons, anchors):
    """Compare four eligibility masks, exact baseline metrics, and reported D/P."""
    reference = None
    for variant in ("A", "B"):
        for arm in ("transfer", "stack"):
            values = tables[variant][arm][list(FIVE)].to_numpy(float)
            if np.isinf(values).any() or not np.isfinite(values[:, 0]).all():
                raise ValueError("Infinite member or missing PDS")
            mask = np.isfinite(values)
            if not mask.any(axis=0).all():
                raise ValueError("Entirely ineligible scored member")
            if reference is not None and not np.array_equal(mask, reference):
                raise ValueError("Per-target/member eligibility differs across A/B arms")
            reference = mask
    ta, tb = tables["A"]["transfer"], tables["B"]["transfer"]
    if set(ta.columns) != set(tb.columns):
        raise ValueError("Transfer diagnostic metric set differs")
    cols = sorted(ta.columns)
    if not np.array_equal(ta[cols].to_numpy(float), tb[cols].to_numpy(float), equal_nan=True):
        raise ValueError("Transfer per-target scores are not exactly identical")
    spans = np.asarray([anchors[m]["replicate"] - anchors[m]["baseline"] for m in FIVE], dtype=float)
    if not np.isfinite(spans).all() or np.any(spans == 0):
        raise ValueError("Invalid anchors")
    slopes = 1 / spans
    for variant in ("A", "B"):
        a, b = [tables[variant][arm][list(FIVE)].to_numpy(float) for arm in ("stack", "transfer")]
        delta = float(np.nanmean((a - b) * slopes / 6, axis=0).sum())
        pds = float(np.nanmean(a[:, 0] - b[:, 0]))
        summary = comparisons[variant]
        # The comparison JSON retains the original unrounded float64 result.
        # Tolerance only detects cross-runtime arithmetic differences; choice
        # below always uses the original values with an exact A tie-break.
        if not np.allclose([delta, pds], [summary["delta_projection"], summary["delta_pds_raw"]], rtol=0, atol=1e-12):
            raise ValueError("Comparison cannot be reconstructed from per-target members")
        for arm in ("transfer", "stack"):
            frame = tables[variant][arm]
            raw = summary["raw"][arm]
            for metric in FIVE:
                if not np.isclose(np.nanmean(frame[metric]), raw[metric], rtol=0, atol=1e-10):
                    raise ValueError("Reported aggregate differs from per-target mean")
            if {"expr_mse_unbiased_capped", "expr_distance_unbiased"}.issubset(frame.columns):
                n, d = frame["expr_mse_unbiased_capped"].to_numpy(float), frame["expr_distance_unbiased"].to_numpy(float)
                valid = np.isfinite(n) & np.isfinite(d)
                if valid.any() and d[valid].sum() > 0:
                    ratio = n[valid].sum() / d[valid].sum()
                    if raw[MSE] is None or not np.isclose(ratio, raw[MSE], rtol=0, atol=1e-10):
                        raise ValueError("MSE ratio-of-sums differs")
    if comparisons["A"]["truth_cells_per_target"] != comparisons["B"]["truth_cells_per_target"]:
        raise ValueError("Development truth cell counts differ")
    return {"four_arm_eligibility_identical": True, "transfer_metric_values_exact": True,
            "comparison_reconstruction_tolerance": 1e-12, "selection_uses_original_float64": True}


def h5_strings(group, name):
    """Read plain, categorical and nullable H5AD text without loading X."""
    node = group[name]
    if isinstance(node, h5py.Group):
        if "categories" in node:
            codes = node["codes"][:]
            if np.any(codes < 0):
                raise ValueError("Missing cell/gene identity")
            categories = np.asarray(h5_strings(node, "categories"), dtype=str)
            return categories[codes].tolist()
        if "values" not in node or ("mask" in node and node["mask"][:].any()):
            raise ValueError("Unsupported or missing cell/gene identity")
        node = node["values"]
    return node.asstr()[:].tolist()


def prediction_fingerprint(path):
    """Exact ordered cell labels, gene axis and canonical CSR values; bounded RAM."""
    h = hashlib.sha256()
    with h5py.File(path, "r") as f:
        labels = h5_strings(f["obs"], "gene")
        index = f["var"].attrs.get("_index", "_index")
        if isinstance(index, bytes):
            index = index.decode()
        genes = h5_strings(f["var"], "gene_name" if "gene_name" in f["var"] else index)
        x = f["X"]
        if not isinstance(x, h5py.Group) or x.attrs.get("encoding-type") not in ("csr_matrix", b"csr_matrix"):
            raise ValueError("Expected CSR prediction for exact comparison")
        shape = [int(i) for i in x.attrs["shape"]]
        if shape != [len(labels), len(genes)]:
            raise ValueError("Prediction metadata/matrix dimensions differ")
        h.update(json.dumps({"labels": labels, "genes": genes, "shape": shape}, separators=(",", ":")).encode())
        for field, dtype in (("indptr", "<i8"), ("indices", "<i8"), ("data", "<f8")):
            h.update(field.encode())
            ds = x[field]
            for start in range(0, len(ds), 1048576):
                values = np.asarray(ds[start:start + 1048576], dtype=dtype)
                if field == "data" and (not np.isfinite(values).all() or np.any(values < 0) or np.any(values != np.floor(values))):
                    raise ValueError("Invalid raw prediction counts")
                h.update(values.tobytes())
    return {"sha256": h.hexdigest(), "shape": shape,
            "method": "Exact ordered labels/genes and CSR indptr/indices/data, canonical little-endian int64/float64"}


def provenance(evaluation, inference, finished, bundle, variant):
    if (evaluation.get("status") != "registered_before_truth_expression_read"
            or evaluation.get("targets") != bundle["targets"]
            or finished.get("targets") != bundle["targets"] or finished.get("cells_per_target") != 400
            or evaluation.get("bundle_sha256") != BUNDLE_SHA or evaluation.get("anchors_sha256") != ANCHORS_SHA
            or evaluation.get("scoring_code_sha256") != SCORERS[variant]):
        raise ValueError("Scoring provenance differs: " + variant)
    expected = {"bundle_sha256": BUNDLE_SHA, "adapter_sha256": ADAPTERS[variant],
                "checkpoint_sha256": pilot.CHECKPOINT_SHA, "genelist_sha256": pilot.GENELIST_SHA}
    if variant == "B":
        expected |= {"preparation_adapter_sha256": ADAPTERS["A"], "ab_protocol_sha256": AB_SHA,
                     "input_axis_policy": "own_measured_support"}
    if any(inference.get(k) != v for k, v in expected.items()):
        raise ValueError("Inference provenance differs: " + variant)


def run(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    if pilot.sha(HERE / "PROTOCOLLO_STACK_AB.md") != AB_SHA or pilot.sha(args.bundle / "bundle.json") != BUNDLE_SHA:
        raise ValueError("Frozen AB protocol or common bundle changed")
    if pilot.sha(args.anchors) != ANCHORS_SHA:
        raise ValueError("Official anchors changed")
    bundle = read_json(args.bundle / "bundle.json")
    if len(bundle["targets"]) != 12 or bundle["adapter_sha256"] != ADAPTERS["A"]:
        raise ValueError("Expected original pilot preparation")
    inputs = {}
    def record(name, path):
        inputs[name] = {"path": str(path), "bytes": Path(path).stat().st_size, "sha256": pilot.sha(path)}
        return inputs[name]["sha256"]
    record("bundle", args.bundle / "bundle.json")
    record("anchors", args.anchors)
    for name in ("source_00.h5ad", "destination_controls.h5ad", "transfer.npz"):
        if record(name, args.bundle / name) != bundle["files"][name]:
            raise ValueError("Common controls or transfer effects changed")
    tables, comparisons, evaluations, inferences, configs, fingerprints = {}, {}, {}, {}, {}, {}
    for variant in ("A", "B"):
        run_dir, pred_dir = getattr(args, "run_" + variant.lower()), getattr(args, "prediction_" + variant.lower())
        for name in ("pilot_comparison.json", "evaluation_manifest.json", "scorer_config.json"):
            record(variant + "/" + name, run_dir / name)
        for name in ("inference_manifest.json", "finished.json"):
            record(variant + "/" + name, pred_dir / name)
        comparisons[variant] = read_json(run_dir / "pilot_comparison.json")
        evaluations[variant] = read_json(run_dir / "evaluation_manifest.json")
        inferences[variant] = read_json(pred_dir / "inference_manifest.json")
        configs[variant] = read_json(run_dir / "scorer_config.json")
        provenance(evaluations[variant], inferences[variant], read_json(pred_dir / "finished.json"), bundle, variant)
        tables[variant] = {}
        for arm in ("transfer", "stack"):
            if record(variant + "/prediction_" + arm, pred_dir / f"prediction_{arm}.h5ad") != evaluations[variant]["prediction_hashes"][arm]:
                raise ValueError("Scored prediction file changed")
            record(variant + "/per_pert_" + arm, run_dir / f"per_pert_{arm}.csv")
            tables[variant][arm] = table(run_dir / f"per_pert_{arm}.csv", bundle["targets"])
        fingerprints[variant] = prediction_fingerprint(pred_dir / "prediction_transfer.h5ad")
    if configs["A"] != configs["B"] or evaluations["A"]["versions"] != evaluations["B"]["versions"]:
        raise ValueError("Scoring environment or configuration differs")
    for key in ("shared_genes", "model_genes", "batch_size", "rng_note", "versions"):
        if inferences["A"].get(key) != inferences["B"].get(key):
            raise ValueError("Inference configuration differs beyond registered input support: " + key)
    if fingerprints["A"] != fingerprints["B"]:
        raise ValueError("Transfer counts/ordered axes differ exactly; resolve before selection")
    diagnostics = verify_tables(tables, comparisons, read_json(args.anchors)["anchors"])
    selected = choose(comparisons)
    candidates = {v: {"comparison_sha256": inputs[v + "/pilot_comparison.json"]["sha256"],
        "evaluation_manifest_sha256": inputs[v + "/evaluation_manifest.json"]["sha256"],
        "delta_projection": comparisons[v]["delta_projection"], "delta_pds_raw": comparisons[v]["delta_pds_raw"],
        "eligible": comparisons[v]["proceed_to_distinct_confirmation"]} for v in ("A", "B")}
    result = {"status": "selection_complete", "ab_protocol_sha256": AB_SHA, "selector_sha256": pilot.sha(__file__),
        "selected_variant": selected, "candidates": candidates, "targets": bundle["targets"],
        "bundle_sha256": BUNDLE_SHA, "input_files": inputs, "transfer_fingerprints": fingerprints,
        "checks": diagnostics | {"controls_exact_common_bundle": True, "transfer_counts_axes_exact": True,
                                 "scoring_environment_identical": True},
        "rule": "D>0 and PDS>=0; greatest original float64 D; exact tie A; one selected confirmation only",
        "claim": "Development selection only; no confirmation outcome read, no automatic inference or submission authority"}
    args.out.mkdir(parents=True)
    pilot.write_json(args.out / "selection_manifest.json", result)
    print(json.dumps({"selected_variant": selected, "candidates": candidates}, indent=2))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("run-a", "run-b", "prediction-a", "prediction-b", "bundle", "anchors", "out"):
        p.add_argument("--" + name, required=True, type=Path)
    run(p.parse_args())


if __name__ == "__main__":
    main()
