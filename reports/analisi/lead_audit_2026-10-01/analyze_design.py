"""Post-hoc composition, control-pool and complementarity diagnostics from recorded inputs."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import h5py
import numpy as np

from analyze_hepg2 import column

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--raw", required=True, type=Path)
    a = p.parse_args(); a.out.mkdir(exist_ok=False)
    es = ROOT / "reports/modelli/cellnet_esteso_2026-10-01/esito"
    q = json.loads((es / "prepass_r5/prepass/qc.json").read_text())
    config = json.loads((es / "training_r2/train/config.json").read_text())
    ev = json.loads((es / "training_r2/train/desc/eval.json").read_text())
    logs = [json.loads(l) for l in (es / "prepass_r5/prepass/train_log.jsonl").read_text().splitlines()]
    resolved = json.loads((es / "training_r2/train/shards_resolved.json").read_text())
    rows = {r["shard"]: r["cells"] for r in logs if r["msg"] == "first read"}
    sids = [(sid, r["name"]) for sid,r in enumerate(resolved) if r["name"].startswith("hepg2_nadig__")]
    key = "hepg2_nadig|HepG2"
    ki = sorted(q["masks"]["by_key"]).index(key)
    pool_size = 2048
    ctrl_k = int(config["args"]["ctrl_k"])
    with h5py.File(a.raw) as f:
        labels = column(f["obs/gene"]); batch = column(f["obs/batch"])
    assert (labels == "non-targeting").sum() == q["controls_per_key"][key]
    pool = np.array([], dtype=np.int64)
    merge = np.random.default_rng([0, 22, ki])
    start = 0; counts_by_shard = []
    for sid, name in sids:
        stop = start + rows[name]
        ix = start + np.flatnonzero(labels[start:stop] == "non-targeting")
        counts_by_shard.append(len(ix))
        if len(ix) > pool_size:
            ix = np.sort(np.random.default_rng([0, 21, sid, ki]).choice(ix, pool_size, replace=False))
        if len(pool):
            both = np.r_[pool, ix]
            if len(both) > pool_size:
                both = both[np.sort(merge.choice(len(both), pool_size, replace=False))]
            pool = both
        else:
            pool = ix
        start = stop
    assert start == len(labels)
    all_counts = Counter(batch[labels == "non-targeting"])
    pool_counts = Counter(batch[pool])
    pert = labels != "non-targeting"
    pool_info = {"scope": "reconstruction from raw metadata and r5 shard order; no QC-rejected HepG2 controls",
                 "controls_by_shard": counts_by_shard, "pool_size": len(pool), "ctrl_k": ctrl_k,
                 "libraries_native": len(all_counts), "libraries_with_64_native": sum(n >= ctrl_k for n in all_counts.values()),
                 "libraries_with_64_in_pool": sum(n >= ctrl_k for n in pool_counts.values()),
                 "fraction_perturbed_cells_with_native_library_64": float(np.mean([all_counts[b] >= ctrl_k for b in batch[pert]])),
                 "fraction_perturbed_cells_with_pool_library_64": float(np.mean([pool_counts[b] >= ctrl_k for b in batch[pert]])),
                 "pool_per_library": dict(sorted(pool_counts.items()))}
    cr = [r for r in ev["C"] if r.get("cos_transfer") is not None]
    baseline = np.array([r["cos_transfer"] for r in cr]); model = np.array([r["cos_model"] for r in cr])
    complement = {"target_oracle_best_cosine": float(np.maximum(model, baseline).mean()),
                  "transfer_cosine": float(baseline.mean()), "model_cosine": float(model.mean()),
                  "oracle_gain": float(np.maximum(model-baseline, 0).mean()),
                  "caveat": "uses test truth; unattainable selector benchmark, not an ensemble result or VCC score",
                  "largest_model_wins": [{"target":r['symbol'], "delta":r['cos_model']-r['cos_transfer']} for r in
                                         sorted(cr, key=lambda r: r['cos_model']-r['cos_transfer'], reverse=True)[:12]]}
    result = {"controls": pool_info, "complementarity": complement}
    (a.out / "design.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    paths = [es / "prepass_r5/prepass/qc.json", es / "training_r2/train/config.json", es / "training_r2/train/desc/eval.json",
             es / "prepass_r5/prepass/train_log.jsonl", es / "training_r2/train/shards_resolved.json", Path(__file__)]
    (a.out / "manifest.json").write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, indent=2), encoding="utf-8")
    print(json.dumps({"controls": {k:v for k,v in pool_info.items() if k != 'pool_per_library'}, "complementarity": complement}, indent=2))


if __name__ == "__main__":
    main()
