"""Production effects of the `all` transfer for contexts A, B, C (stage-45 external_effects layout).

T = Davide's transfer (arms.group_mean per group, combine_groups at equal weight) over every group of the cube,
table commons over all their keys (no line is held out for A/B/C), times the t25 amplitude 1.576. Targets and gene axis
are copied from a reference effects folder (the 300 panel targets in their order, the official axis); cube genes
carry T, the other genes lfc 0 observed False; a target without any source stays all 0, observed False.

    python esporta_all.py --cube <layout> --code <cube code> --ref <effects folder> --out <new folder>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guadagno as G  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cube", type=Path, required=True)
    ap.add_argument("--code", type=Path, required=True)
    ap.add_argument("--ref", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: never overwrite")
    sys.path.insert(0, str(a.code))
    import arms
    C = G.Cubes(arms, a.cube)
    cube = C.cube
    commons = G.table_means(cube, set())
    by_symbol = {}
    for k, s in cube.symbol.items():
        by_symbol.setdefault(s, set()).add(k)
    a.out.mkdir(parents=True)
    meta = {"cube_manifest_sha256": sha(a.cube / "manifest.json"), "groups": C.groups("all", set()),
            "amplitude": G.AMP, "contexts": {}}
    for ctx in "ABC":
        ref = np.load(a.ref / f"effects_{ctx}.npz", allow_pickle=False)
        targets, genes = [str(t) for t in ref["targets"]], np.asarray(ref["genes"], str)
        keys = [next(iter(by_symbol[t])) if len(by_symbol.get(t, ())) == 1 else None for t in targets]
        have = [i for i, k in enumerate(keys) if k is not None]
        st = G.transfer(C, "all", [keys[i] for i in have], commons, set())
        # parity with Davide's functions on the first 20 covered keys
        pk = [keys[i] for i in have[:20]]
        refT, _ = arms.combine_groups([arms.group_mean(cube, g, pk, commons) for g in C.groups("all", set())])
        if not np.allclose(np.nan_to_num(refT, nan=9), np.nan_to_num(st["T"][:20], nan=9), atol=1e-5):
            raise SystemExit("transfer parity failed")
        gpos = pd.Index(genes).get_indexer(cube.genes)
        if (gpos < 0).any():
            raise SystemExit("cube genes missing from the reference axis")
        lfc = np.zeros((len(targets), len(genes)), np.float32)
        obs = np.zeros((len(targets), len(genes)), bool)
        T = st["T"] * G.AMP
        fin = np.isfinite(T)
        for j, i in enumerate(have):
            lfc[i, gpos[fin[j]]] = T[j, fin[j]]
            obs[i, gpos[fin[j]]] = True
        path = a.out / f"effects_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(targets, dtype=str), genes=genes, lfc=lfc, observed=obs)
        covered = int(obs.any(1).sum())
        support = st["n"].max(1)
        meta["contexts"][ctx] = {"file": path.name, "sha256": sha(path), "targets": len(targets),
                                 "mapped_to_cube": len(have), "covered": covered,
                                 "groups_per_target_median": float(np.median(support)) if len(support) else 0.0,
                                 "groups_per_target_hist": np.bincount(support.astype(int)).tolist(),
                                 "lfc_abs_mean_covered": float(np.abs(lfc[obs]).mean()) if obs.any() else 0.0}
        print(ctx, json.dumps({k: v for k, v in meta["contexts"][ctx].items() if k != "sha256"}), flush=True)
    (a.out / "export.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
