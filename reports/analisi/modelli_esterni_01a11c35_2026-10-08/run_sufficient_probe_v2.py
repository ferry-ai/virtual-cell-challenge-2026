"""Fit target-only ESM2 ridge with exact weighted sufficient statistics.

No scoring or test truth is accepted. The output is frozen native-scale effects,
not a promoted generator input. The owner supplies modality/exclusion/coverage
decisions and weights; missing features have an explicit training-only policy.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import time

import numpy as np

from target_sufficient_ridge_v2 import TargetSufficientRidge
from chunk_store_v2 import load_store
from feature_policy import prepare_features, validate_queries
from pie_adapter import sha256, unique


def load_features(root, expected, targets):
    for filename in ("meta.json", "embeddings.npy"):
        if sha256(root/filename) != expected[filename]:
            raise ValueError(f"embedding checksum mismatch: {filename}")
    meta = json.loads((root/"meta.json").read_text(encoding="utf-8"))
    keys = unique(meta["keys"], "embedding keys")
    if meta.get("name") != "esm2" or meta.get("layout") != "dense" or meta.get("index") != "pert":
        raise ValueError("expected dense target-indexed ESM2")
    embedding = np.load(root/"embeddings.npy", mmap_mode="r", allow_pickle=False)
    if embedding.shape != (len(keys), meta["dim"]) or embedding.dtype != np.dtype(meta["dtype"]):
        raise ValueError("embedding metadata/array mismatch")
    index = {name:i for i,name in enumerate(keys)}
    available = np.array([target in index for target in targets], dtype=bool)
    result = np.full((len(targets), meta["dim"]), np.nan)
    for i, target in enumerate(targets):
        if available[i]: result[i] = embedding[index[target]]
    return result, available, meta["provenance"]


def run(manifest_path, out, progress=None):
    manifest_path, out = Path(manifest_path), Path(out)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if out.exists(): raise FileExistsError(out)
    if manifest.get("schema_version") != 1 or manifest.get("protocol_status") != "agreed":
        raise ValueError("agreed frozen protocol required")
    if not manifest.get("validation_review") or not manifest.get("quantity") or not manifest.get("normalization"):
        raise ValueError("validation review and units required")
    if manifest.get("mode") not in {"development", "production"}:
        raise ValueError("protected test scoring is not this runner's responsibility")
    if manifest.get("modality") != "CRISPRi":
        raise ValueError("this probe admits only explicitly reconciled CRISPRi")
    train_path = Path(manifest["train"]["path"])
    started = time.monotonic()
    effects, mask, train, store_receipt = load_store(train_path, manifest["train"]["sha256"])
    for name in ("quantity", "normalization", "modality", "regime", "release_sha256", "split_manifest_sha256"):
        if store_receipt["source_manifest"][name] != manifest[name]:
            raise ValueError("store units/modality/release/split differ from fit contract")
    targets, contexts = train["targets"].tolist(), train["context_groups"].tolist()
    context_ids = train["context_ids"].tolist()
    genes = unique(train["genes"].tolist(), "response genes")
    weights = train["weights"]
    if len(context_ids) != len(targets) or len(contexts) != len(targets):
        raise ValueError("row metadata lengths differ")
    if any(not isinstance(c, str) or not c for c in context_ids + contexts + targets):
        raise ValueError("nonempty canonical row identifiers required")
    if dict(Counter(context_ids)) != manifest["expected_rows_by_context"]:
        raise ValueError("D-053 expected/consumed context inventory differs")
    lineage_by_id = {}
    for context_id, context_group in zip(context_ids, contexts):
        if lineage_by_id.setdefault(context_id, context_group) != context_group:
            raise ValueError("one context_id maps to multiple lineage groups")
    if len(set(zip(context_ids, targets))) != len(targets):
        raise ValueError("duplicate context-target rows; reconcile technical strata upstream")
    queries = manifest["queries"]
    if not queries or len({(q["context_id"], q["target"]) for q in queries}) != len(queries):
        raise ValueError("empty or duplicate queries")
    if any(q.get("protected", False) for q in queries):
        raise ValueError("protected queries forbidden")
    regime = manifest["regime"]
    validate_queries(regime, targets, contexts, context_ids, queries)
    feature_targets = list(dict.fromkeys(targets))
    feature_index = {target:i for i,target in enumerate(feature_targets)}
    row_feature_indices = np.asarray([feature_index[t] for t in targets],dtype=np.int64)
    n_features = len(feature_targets)
    all_targets = feature_targets+[q["target"] for q in queries]
    features, available, provenance = load_features(Path(manifest["esm2"]["path"]),
                                                   manifest["esm2"]["sha256"], all_targets)
    features, imputation_mean, policy_receipt = prepare_features(
        features, available, n_features, row_feature_indices, weights,
        manifest.get("missing_feature_policy"))
    if manifest["alpha"] != 1.0:
        raise ValueError("first real probe preregisters alpha=1")
    model = TargetSufficientRidge(alpha=manifest["alpha"]).fit(
        features[:n_features], effects, mask, row_contexts=contexts, row_targets=targets,
        feature_targets=feature_targets, row_feature_indices=row_feature_indices,
        excluded_contexts=manifest["excluded_contexts"], excluded_targets=manifest["excluded_targets"],
        sample_weight=weights, gene_block=manifest.get("gene_block", 64),
        factor_cache=manifest.get("factor_cache", 2),row_block=manifest.get("row_block",128), progress=progress)
    pred, support = model.predict(features[n_features:], available[n_features:])
    out.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(out/"native_predictions.npz", effects=pred, observed=support,
        genes=np.asarray(genes), targets=np.asarray([q["target"] for q in queries]),
        context_groups=np.asarray([q["context_group"] for q in queries]),
        context_ids=np.asarray([q["context_id"] for q in queries]),
        generic=np.broadcast_to(model.generic, pred.shape),
        generic_observed=np.broadcast_to(model.support, pred.shape),
        esm2_observed=available[n_features:])
    np.savez_compressed(out/"ridge.npz", coef=model.coef, intercept=model.intercept,
                        feature_mean=model.feature_mean, feature_scale=model.feature_scale,
                        support=model.support, generic=model.generic,
                        imputation_mean=imputation_mean,
                        feature_policy=np.asarray(manifest["missing_feature_policy"]))
    receipt = dict(manifest=manifest, manifest_sha256=sha256(manifest_path),
                   code={p:sha256(Path(__file__).parent/p) for p in
                         ("run_sufficient_probe_v2.py", "target_sufficient_ridge_v2.py",
                          "embedding_ridge.py", "chunk_store_v2.py", "pie_adapter.py", "feature_policy.py")},
                   store_receipt=store_receipt,
                   exposure=model.receipt, feature_provenance=provenance,
                   feature_policy=policy_receipt,
                   missing_training_targets=[t for t,a in zip(feature_targets,available[:n_features]) if not a],
                   consumed_rows_by_context=dict(Counter(context_ids)),
                   consumed_rows_by_lineage=dict(Counter(contexts)),
                   context_lineages=lineage_by_id,
                   query_features_available=int(available[n_features:].sum()),
                   queries=len(queries), seconds=time.monotonic()-started,
                   native_predictions_sha256=sha256(out/"native_predictions.npz"),
                   model_sha256=sha256(out/"ridge.npz"),
                   scientific_benefit="not_scored", emitter_compatibility="not_established")
    (out/"manifest.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.manifest, args.out)
    print(json.dumps({key:result[key] for key in ("queries", "query_features_available", "seconds", "scientific_benefit")}))
