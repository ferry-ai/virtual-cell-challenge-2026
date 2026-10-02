"""The corrected control reservoir (step A, cellnet_rlead_2026-10-01) on the real HepG2 controls, beside the audit's
reconstruction of the old one (design_r1/design.json, same raw file, same libraries, same pool size 2048, ctrl_k 64).

Libraries are obs/batch, controls obs/gene == "non-targeting", the cell identity is "hepg2_nadig|<batch>|<obs index>".
The order check draws the pool from the cells in file order, in reverse order and split into 8 shards in a random
order: the corrected rule must give the same rows every time. No QC is applied (as in the audit's reconstruction).

    python pool_corrected.py --raw <NadigOConner2024_hepg2.h5ad> --out pool_r1
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
RLEAD = HERE.parents[1] / "modelli" / "cellnet_rlead_2026-10-01"
sys.path.insert(0, str(RLEAD))
sys.path.insert(0, str(HERE.parent / "lead_audit_2026-10-01"))
import cell_data as CD  # noqa: E402
from analyze_hepg2 import column  # noqa: E402

KEY, SEED, POOL, CTRL_K, MIN_LIB = "hepg2_nadig|HepG2", 0, 2048, 64, 64


def draw(rows, libs, ids):
    """Corrected pool from control rows given in any order: per library, the rows of smallest priority."""
    n_by_lib = Counter(libs[rows])
    alloc, size = CD.allocate_pool(dict(n_by_lib), POOL, MIN_LIB)
    keep = []
    for lib, k in alloc.items():
        r = rows[libs[rows] == lib]
        keep.append(CD.bottom_k(r, [CD.priority(SEED, KEY, ids[i]) for i in r], k))
    return np.sort(np.concatenate(keep)), alloc, size


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(exist_ok=False)
    with h5py.File(a.raw, "r") as f:
        labels, batch = column(f["obs/gene"]), column(f["obs/batch"])
        index = column(f["obs"][f["obs"].attrs.get("_index", "_index")])
    ids = np.array([f"hepg2_nadig|{b}|{i}" for b, i in zip(batch, index)])
    ctrl = np.flatnonzero(labels == "non-targeting")
    pool, alloc, size = draw(ctrl, batch, ids)
    rng = np.random.default_rng(7)
    shards = np.array_split(ctrl, 8)
    orders = {"file": ctrl, "reverse": ctrl[::-1],
              "shards_shuffled": np.concatenate([shards[i] for i in rng.permutation(8)])}
    same = {k: bool(np.array_equal(draw(v, batch, ids)[0], pool)) for k, v in orders.items()}
    all_counts, pool_counts = Counter(batch[ctrl]), Counter(batch[pool])
    pert = labels != "non-targeting"
    old = json.loads((HERE / "design_r1" / "design.json").read_text(encoding="utf-8"))["controls"]
    res = {
        "scope": "real HepG2 controls, no QC; libraries = obs/batch; same raw file as the audit (sha256 below)",
        "controls": int(len(ctrl)), "libraries": len(all_counts), "pool_size_asked": POOL, "pool_size_used": int(size),
        "pool_rows": int(len(pool)), "ctrl_k": CTRL_K, "min_per_library": MIN_LIB,
        "libraries_with_ctrl_k_native": sum(n >= CTRL_K for n in all_counts.values()),
        "libraries_with_ctrl_k_in_pool": {"old_reservoir": old["libraries_with_64_in_pool"],
                                          "corrected": sum(n >= CTRL_K for n in pool_counts.values())},
        "fraction_perturbed_cells_whose_library_has_ctrl_k_in_pool": {
            "old_reservoir": old["fraction_perturbed_cells_with_pool_library_64"],
            "corrected": float(np.mean([pool_counts[b] >= CTRL_K for b in batch[pert]])),
            "upper_bound_native": float(np.mean([all_counts[b] >= CTRL_K for b in batch[pert]]))},
        "libraries_below_ctrl_k_native": {str(b): int(n) for b, n in sorted(all_counts.items()) if n < CTRL_K},
        "same_pool_whatever_the_order": same,
        "inclusion_probability_by_library": {str(b): round(alloc[b] / all_counts[b], 4) for b in sorted(all_counts)},
        "pool_per_library": {str(b): int(pool_counts[b]) for b in sorted(all_counts)},
    }
    (a.out / "pool.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    h = hashlib.sha256()
    with a.raw.open("rb") as fh:
        for b in iter(lambda: fh.read(16 << 20), b""):
            h.update(b)
    man = {"raw": {"name": a.raw.name, "bytes": a.raw.stat().st_size, "sha256": h.hexdigest()},
           "code": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (Path(__file__).resolve(), RLEAD / "cell_data.py")}}
    (a.out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("inclusion_probability_by_library", "pool_per_library")},
                     indent=1))


if __name__ == "__main__":
    main()
