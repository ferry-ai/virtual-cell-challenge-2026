"""Audit frozen view metadata against pinned ESM2; never read response arrays."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from pie_adapter import sha256, unique
from run_sufficient_probe import load_features


def audit(releases, esm2, output):
    if output.exists():
        raise FileExistsError(output)
    expected = {
        "embeddings.npy": "427b867ccfddf2050686815b97063e2ceeb4044bc48c67b6baa8d3778f0bebcd",
        "meta.json": "6f8d9b56215c628a60d0f05ae635a65a6d6567a138f49c2c94863aa136f3d25c",
    }
    meta = json.loads((esm2 / "meta.json").read_text(encoding="utf-8"))
    keys = unique(meta["keys"], "ESM2 keys")
    features, available, provenance = load_features(esm2, expected, keys)
    if not available.all() or not np.isfinite(features).all():
        raise ValueError("invalid observed ESM2 features")
    del features
    known = set(keys)
    result = dict(utc=datetime.now(timezone.utc).isoformat(),
                  esm2_sha256=expected, esm2_shape=[len(keys), meta["dim"]],
                  feature_provenance=provenance, biological_response_arrays_read=False,
                  feature_values_verified_finite=True, model_fit=False,
                  matching="exact symbols; no inferred aliases", releases=[])
    for release_path in releases:
        release = json.loads(release_path.read_text(encoding="utf-8"))
        for name in ("view", "inputs", "split"):
            item = release[name]
            path = Path(item["path"])
            if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
                raise ValueError(f"release artifact mismatch: {name}")
        view = json.loads(Path(release["view"]["path"]).read_text(encoding="utf-8"))
        targets, counts, contexts, missing_rows = set(), Counter(), {}, Counter()
        total_weight = missing_weight = 0.0
        for chunk in view["chunks"]:
            cid = chunk["context_id"]
            row = contexts.setdefault(cid, dict(rows=0, missing_rows=0, weight=0.0,
                                                missing_weight=0.0, missing_targets=set()))
            if len(chunk["targets"]) != len(chunk["weights"]):
                raise ValueError("target/weight length mismatch")
            for target, weight in zip(chunk["targets"], chunk["weights"]):
                weight = float(weight)
                if not np.isfinite(weight) or weight <= 0:
                    raise ValueError("invalid row weight")
                targets.add(target)
                counts[cid] += 1
                row["rows"] += 1
                row["weight"] += weight
                total_weight += weight
                if target not in known:
                    row["missing_rows"] += 1
                    row["missing_weight"] += weight
                    row["missing_targets"].add(target)
                    missing_rows[target] += 1
                    missing_weight += weight
        if dict(counts) != view["expected_rows_by_context"]:
            raise ValueError("context inventory mismatch")
        for row in contexts.values():
            row["missing_targets"] = sorted(row["missing_targets"])
        result["releases"].append(dict(
            regime=release["regime"], release_path=str(release_path),
            release_sha256=sha256(release_path), view_sha256=release["view"]["sha256"],
            split_sha256=release["split"]["sha256"], rows=sum(counts.values()),
            distinct_targets=len(targets), exact_feature_targets=len(targets & known),
            missing_targets=sorted(targets-known), missing_rows=sum(missing_rows.values()),
            missing_rows_by_target=dict(sorted(missing_rows.items())),
            total_weight=total_weight, missing_weight=missing_weight,
            missing_weight_fraction=missing_weight/total_weight,
            contexts=contexts, rows_dropped=0, contexts_dropped=0))
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--release", type=Path, action="append", required=True)
    p.add_argument("--esm2", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = audit(args.release, args.esm2, args.out)
    for item in result["releases"]:
        print(json.dumps({k:item[k] for k in ("regime", "rows", "distinct_targets",
              "exact_feature_targets", "missing_rows", "missing_weight_fraction")}))
