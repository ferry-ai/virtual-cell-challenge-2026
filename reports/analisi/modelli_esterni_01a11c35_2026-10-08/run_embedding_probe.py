"""Fit frozen ESM2 -> native effects on an owner-supplied, hash-pinned fold.

No scoring or test truth is accepted. The output is frozen native-scale effects,
not a promoted generator input. The owner supplies modality/exclusion/coverage
decisions and weights; this runner refuses silently missing training features.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import time

import numpy as np

from embedding_ridge import MaskedRidge
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


def run(manifest_path, out):
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
    if sha256(train_path) != manifest["train"]["sha256"]:
        raise ValueError("training release differs from frozen manifest")
    started = time.monotonic()
    with np.load(train_path, allow_pickle=False) as train:
        targets, contexts = train["targets"].tolist(), train["context_groups"].tolist()
        context_ids = train["context_ids"].tolist()
        genes = unique(train["genes"].tolist(), "response genes")
        effects, mask, weights = train["effects"], train["observed"], train["weights"]
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
    if regime not in {"C", "J", "production"}: raise ValueError("invalid regime")
    if regime in {"C", "J"} and any(q["context_group"] in set(contexts) for q in queries):
        raise ValueError("query context reached training")
    if regime == "J" and any(q["target"] in set(targets) for q in queries):
        raise ValueError("J query target reached training")
    if regime == "C" and any(q["target"] not in set(targets) for q in queries):
        raise ValueError("C query target unseen in training")
    all_targets = targets+[q["target"] for q in queries]
    features, available, provenance = load_features(Path(manifest["esm2"]["path"]),
                                                   manifest["esm2"]["sha256"], all_targets)
    if not available[:len(targets)].all():
        missing = sorted({t for t, a in zip(targets, available[:len(targets)]) if not a})
        raise ValueError(f"missing training descriptors require explicit upstream policy: {missing}")
    model = MaskedRidge(alpha=manifest["alpha"]).fit(
        features[:len(targets)], effects, mask, row_contexts=contexts, row_targets=targets,
        excluded_contexts=manifest["excluded_contexts"], excluded_targets=manifest["excluded_targets"],
        sample_weight=weights)
    pred, support = model.predict(features[len(targets):], available[len(targets):])
    out.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(out/"native_predictions.npz", effects=pred, observed=support,
        genes=np.asarray(genes), targets=np.asarray([q["target"] for q in queries]),
        context_groups=np.asarray([q["context_group"] for q in queries]),
        context_ids=np.asarray([q["context_id"] for q in queries]),
        generic=np.broadcast_to(model.generic, pred.shape),
        generic_observed=np.broadcast_to(model.support, pred.shape))
    np.savez_compressed(out/"ridge.npz", coef=model.coef, intercept=model.intercept,
                        feature_mean=model.feature_mean, feature_scale=model.feature_scale,
                        support=model.support, generic=model.generic)
    receipt = dict(manifest=manifest, manifest_sha256=sha256(manifest_path),
                   code={p:sha256(Path(__file__).parent/p) for p in
                         ("run_embedding_probe.py", "embedding_ridge.py", "pie_adapter.py")},
                   exposure=model.receipt, feature_provenance=provenance,
                   consumed_rows_by_context=dict(Counter(context_ids)),
                   consumed_rows_by_lineage=dict(Counter(contexts)),
                   context_lineages=lineage_by_id,
                   query_features_available=int(available[len(targets):].sum()),
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
