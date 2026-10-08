"""Training-only feature imputation and explicit C/T/J query guards."""
import numpy as np

POLICY = "training_weighted_mean_plus_missing_indicator_v1"


def prepare_features(features, available, n_train, row_indices, weights, policy):
    if policy != POLICY:
        raise ValueError("explicit missing-feature policy required")
    x = np.asarray(features, dtype=np.float64)
    available = np.asarray(available, dtype=bool)
    indices = np.asarray(row_indices)
    weights = np.asarray(weights, dtype=np.float64)
    if x.ndim != 2 or available.shape != (len(x),) or not 0 < n_train <= len(x):
        raise ValueError("invalid feature axes")
    if indices.shape != weights.shape or indices.ndim != 1 or indices.dtype.kind not in "iu":
        raise ValueError("invalid row weights/map")
    if not len(indices) or np.any(indices < 0) or np.any(indices >= n_train):
        raise ValueError("invalid training map")
    if not np.isfinite(weights).all() or np.any(weights <= 0):
        raise ValueError("positive finite weights required")
    if not np.isfinite(x[available]).all():
        raise ValueError("nonfinite observed feature")
    mass = np.bincount(indices, weights=weights, minlength=n_train)
    if np.any(mass <= 0):
        raise ValueError("every training feature must be consumed")
    known = available[:n_train]
    if not known.any():
        raise ValueError("no observed training features")
    mean = np.average(x[:n_train][known], axis=0, weights=mass[known])
    filled = np.empty((len(x), x.shape[1]+1), dtype=np.float64)
    filled[:, :-1] = x
    filled[~available, :-1] = mean
    filled[:, -1] = ~available
    receipt = dict(policy=POLICY, training_targets=n_train,
                   missing_training_targets=int((~known).sum()),
                   missing_training_rows=int((~known[indices]).sum()),
                   missing_training_weight=float(mass[~known].sum()),
                   total_training_weight=float(mass.sum()),
                   imputation_uses_query_features=False, imputation_uses_responses=False,
                   rows_dropped=0, query_missing_policy="specific unsupported; generic exported separately")
    return filled, mean, receipt


def validate_queries(regime, targets, groups, context_ids, queries):
    if regime not in {"C", "T", "J", "production"}:
        raise ValueError("invalid regime")
    if not queries:
        raise ValueError("empty queries")
    seen_targets, seen_groups, seen_ids = set(targets), set(groups), set(context_ids)
    mapping = dict(zip(context_ids, groups))
    for q in queries:
        if any(not isinstance(q.get(k), str) or not q[k] for k in ("target", "context_id", "context_group")):
            raise ValueError("canonical query identifiers required")
        if q.get("protected", False):
            raise ValueError("protected queries forbidden")
        if q["context_id"] in mapping and q["context_group"] != mapping[q["context_id"]]:
            raise ValueError("query context identity mismatch")
        if regime in {"C", "J"} and q["context_group"] in seen_groups:
            raise ValueError("query context reached training")
        if regime in {"T", "J"} and q["target"] in seen_targets:
            raise ValueError("query target reached training")
        if regime == "C" and q["target"] not in seen_targets:
            raise ValueError("C query target unseen in training")
        if regime == "T" and q["context_id"] not in seen_ids:
            raise ValueError("T query context unseen in training")
