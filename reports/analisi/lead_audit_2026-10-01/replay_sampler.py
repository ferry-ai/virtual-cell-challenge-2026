"""Replay the published r2 sampler using actual shard lengths, without reading expression matrices."""
import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CODE = ROOT / "reports/modelli/risposta_biologica_2026-09-30"
sys.path.insert(0, str(CODE))
import cell_data as CD


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    a.out.mkdir(exist_ok=False)
    base = ROOT / "reports/modelli/cellnet_esteso_2026-10-01/esito"
    paths = [base / "prepass_r5/prepass/train_log.jsonl", base / "training_r2/train/shards_resolved.json",
             base / "training_r2/train/config.json", base / "training_r2/train/coverage.json", CODE / "cell_data.py",
             CODE / "train_cellnet.py", Path(__file__)]
    log = [json.loads(s) for s in paths[0].read_text(encoding="utf-8").splitlines()]
    study = {r["shard"]: r["study"] for r in log if r["msg"] == "first read"}
    counts = {r["shard"]: r["training_cells"] for r in log if r["msg"] == "second read"}
    resolved = json.loads(paths[1].read_text())
    cfg = json.loads(paths[2].read_text())
    cov = json.loads(paths[3].read_text())
    lengths = np.array([counts[r["name"]] for r in resolved])
    st = np.array([study[r["name"]] for r in resolved])
    names = sorted(set(st[lengths > 0]))
    six = {s: i for i, s in enumerate(names)}
    shard_st = np.array([six.get(s, -1) for s in st])
    weights = np.array([cfg["study_weights"][s] for s in names])
    W, batch, buffer = (int(cfg["args"][k]) for k in ("roles", "batch", "buffer_shards"))
    parts, load = [[] for _ in range(W)], np.zeros(W)
    for sid in sorted(np.flatnonzero(lengths), key=lambda i: (-lengths[i], i)):
        r = int(np.argmin(load)); parts[r].append(sid); load[r] += lengths[sid]
    rb = [max(1, int(round(batch * W * v / load.sum()))) for v in load]
    assert rb == cov["role_batches"]
    samplers = [CD.EpochSampler([(sid, np.arange(lengths[sid])) for sid in parts[r]], buffer, seed=r) for r in range(W)]
    effective, unweighted, global_norm = np.zeros(len(names)), np.zeros(len(names)), np.zeros(len(names))
    unique_hist = Counter()
    for step in range(cov["steps"]):
        r = step % W
        cells = samplers[r].batch(rb[r])
        ns = np.bincount(shard_st[[s for s, _ in cells]], minlength=len(names))
        unique_hist[int((ns > 0).sum())] += 1
        unweighted += ns
        effective += ns * weights / (ns @ weights)
        global_norm += ns * weights / len(cells)
    assert int(unweighted.sum()) == cov["draws"]
    expected_draws = Counter()
    for r in cov["by_key"]:
        expected_draws[r["key"].split("|", 1)[0]] += r["draws"]
    assert all(unweighted[i] == expected_draws[s] for i, s in enumerate(names)), "replay does not match logged study exposure"
    result = {"steps": cov["steps"], "draws_exactly_match_logged_per_study": True,
              "studies_per_batch": dict(unique_hist), "coefficients_not_gradient_norms": True,
              "study": {s: {"cell_fraction": float(unweighted[i] / unweighted.sum()),
                              "actual_mean_loss_coefficient": float(effective[i] / effective.sum()),
                              "fixed_denominator_coefficient": float(global_norm[i] / global_norm.sum()),
                              "equal_active_studies": 1 / len(names)} for i, s in enumerate(names)}}
    # Exact expected representation of 10 equally-sized shards under the current capped merge.
    expected = np.ones(1)
    for _ in range(9):
        expected = np.r_[expected * .5, .5]
    result["pool_merge_counterexample"] = {"equal_size_shards": 10, "expected_current_share_by_order": expected.tolist(),
                                           "uniform_share": .1, "last_over_first_ratio": float(expected[-1] / expected[0])}
    (a.out / "replay.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (a.out / "manifest.json").write_text(json.dumps({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                                    for p in paths}, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
