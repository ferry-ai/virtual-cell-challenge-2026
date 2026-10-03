"""Anchors of the transfer-anchored cell network (PROTOCOLLO.md §2), for one held-out line group H.

The anchor of a (line group L, target t) is the bench's t25 transfer of t (reports/modelli/risposta_contesto_2026-10-02:
group_mean, combine_groups, amplitude 1.576, the table means without the held-out group's tables) from the cell
corpus's line groups other than L and H, on the bench tables whose cells the corpus holds: lane A's 'transfer_cells'
(no k562_viperturb). Rows:
- every (L, t) with at least one admitted training cell (class 'train') in the prepass state, role 'train';
- the held-out line's C evaluation groups, as (H, t), from every cell group but H, role 'eval'.
Hidden targets (the state's 'hidden', classes J and T) get no row; a row without any source is left out: the training
then adds nothing and tells the network so.

Writes anchors.npz (rows [R, G] float16 on the model's genes, NaN where no source measures a gene; support [R], the
source groups that have the target; U [G, k], the top-k gene directions of the training rows), anchors.json (one entry
per row: group, symbol, target key, role, sources, support) and manifest.json (inputs, sha256, counts, checks).

    python anchors.py --prepass <dir with prepass.pkl> --cube <cube_r2> --protocol <bench PROTOCOLLO.json> \
        --target-keys target_keys.json --out <new dir> [--bench-code <dir of arms.py ...>] [--rank 32]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CELL_GROUPS = ("H1", "HepG2", "RPE1", "K562", "iPSC", "Jurkat", "Neuron")
NOT_IN_CELL_CORPUS = ("k562_viperturb",)       # tables of those groups whose cells the corpus does not hold
BLOCK = 500


def sha(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def bench(code_dir: Path):
    """The bench's functions, imported from its research folder (or the copy a Kaggle kernel unpacked)."""
    sys.path.insert(0, str(code_dir))
    import arms
    import fitting
    import splits
    return arms, fitting, splits


def training_pairs(st) -> dict:
    """Symbols with at least one admitted training cell, per line group of the cell's key."""
    train = st["classes"].index("train")
    group_of_key = [st["key_group"][k] for k in st["key_names"]]
    out = defaultdict(set)
    for s in st["shards"]:
        sel = (np.asarray(s["admitted"], bool) & ~np.asarray(s["control"], bool)
               & (np.asarray(s["cls"]) == train) & (np.asarray(s["tgt"]) >= 0))
        if not sel.any():
            continue
        pairs = np.unique(np.stack([np.asarray(s["key"])[sel], np.asarray(s["tgt"])[sel]], 1), axis=0)
        for k, t in pairs.tolist():
            out[group_of_key[k]].add(st["symbols"][t])
    return out


def sources_for(row_group: str, held: str, cube_groups) -> list:
    return [h for h in CELL_GROUPS if h not in (row_group, held) and h in cube_groups]


def jobs_of(st) -> list:
    """(row group, role, symbols): the training pairs of every group, then the held-out line's C groups."""
    held = st["holdout_group"]
    hidden = set(st.get("hidden", ()))
    pairs = training_pairs(st)
    if held in pairs:
        raise AssertionError(f"training cells of the held-out group {held}")
    leaked = sorted(set().union(*pairs.values()) & hidden) if pairs else []
    if leaked:
        raise AssertionError(f"hidden symbols with training cells: {leaked[:5]}")
    c_syms = sorted({g["symbol"] for g in st["eval_groups"] if g["class"] == "C"} - hidden)
    return [(L, "train", sorted(s)) for L, s in sorted(pairs.items())] + [(held, "eval", c_syms)]


def compute(st, cube_cells, commons, keys_of_symbol, transfer_for, amplitude, basis, rank=32, log=print):
    """Rows, their index and the projection U, on the model's genes (st['genes'])."""
    held = st["holdout_group"]
    model_genes = [str(g) for g in st["genes"]]
    mpos = {g: i for i, g in enumerate(model_genes)}
    cube_col = np.array([mpos.get(g, -1) for g in cube_cells.genes], np.int64)
    have = cube_col >= 0
    G = len(model_genes)
    rows, index = [], []
    for L, role, syms in jobs_of(st):
        srcs = sources_for(L, held, cube_cells.groups)
        if L in srcs or held in srcs:
            raise AssertionError(f"sources of {L} include {L} or {held}")
        if not srcs or not syms:
            log(json.dumps({"group": L, "role": role, "symbols": len(syms), "sources": srcs, "rows": 0}))
            continue
        keys = [keys_of_symbol.get(s) or f"SYM:{s}" for s in syms]
        kept = 0
        for b0 in range(0, len(keys), BLOCK):
            s, support = transfer_for(cube_cells, keys[b0:b0 + BLOCK], srcs, commons)
            for i in np.flatnonzero(support > 0):
                v = np.full(G, np.nan, np.float32)
                v[cube_col[have]] = s[i, have] * amplitude
                rows.append(v.astype(np.float16))
                index.append({"group": L, "symbol": syms[b0 + i], "target_key": keys[b0 + i], "role": role,
                              "sources": srcs, "support": int(support[i])})
                kept += 1
        log(json.dumps({"group": L, "role": role, "symbols": len(syms), "sources": srcs, "rows": kept}))
    R = np.stack(rows) if rows else np.zeros((0, G), np.float16)
    train = np.array([r["role"] == "train" for r in index], bool)
    U = basis(np.nan_to_num(R[train].astype(np.float32)), rank) if train.any() else np.zeros((G, 0), np.float32)
    return R, index, U


def check(st, index) -> dict:
    """The leakage checks of PROTOCOLLO.md §6, on the written index."""
    held, hidden = st["holdout_group"], set(st.get("hidden", ()))
    bad_src = [r for r in index if r["group"] in r["sources"] or held in r["sources"]]
    bad_hidden = [r for r in index if r["symbol"] in hidden]
    bad_role = [r for r in index if (r["role"] == "eval") != (r["group"] == held)]
    return {"own_or_held_in_sources": len(bad_src), "hidden_with_anchor": len(bad_hidden),
            "role_mismatch": len(bad_role), "passed": not (bad_src or bad_hidden or bad_role)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prepass", type=Path, required=True)
    p.add_argument("--cube", type=Path, required=True)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--target-keys", type=Path, required=True)
    p.add_argument("--bench-code", type=Path, default=HERE.parent / "risposta_contesto_2026-10-02")
    p.add_argument("--rank", type=int, default=32)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    t0 = time.time()
    arms, fitting, splits = bench(a.bench_code)
    P = json.loads(a.protocol.read_text(encoding="utf-8"))["parameters"]
    with open(a.prepass / "prepass.pkl", "rb") as fh:
        st = pickle.load(fh)
    held = st["holdout_group"]

    class SubCube(arms.Cube):
        """The bench cube without the tables whose cells the corpus does not hold (lane A's 'transfer_cells')."""

        def __init__(self, folder, min_cells, drop=()):
            super().__init__(folder, min_cells)
            self.dropped = sorted(t for t in self.tables if t in set(drop))

        def tables_of(self, group):
            return [t for t in super().tables_of(group) if t not in self.dropped]

    cube_all = arms.Cube(a.cube, min_cells=P["min_cells"])
    cube_cells = SubCube(a.cube, P["min_cells"], NOT_IN_CELL_CORPUS)
    if held not in cube_all.groups:
        raise SystemExit(f"{held} is not a group of the cube")
    commons, _ = arms.table_means(cube_all, splits.Split("C", held, None, P["n_folds"]))
    keys_of_symbol = json.loads(a.target_keys.read_text(encoding="utf-8"))
    R, index, U = compute(st, cube_cells, commons, keys_of_symbol, fitting.transfer_for, arms.AMPLITUDE_T25,
                          fitting.basis, a.rank)
    checks = check(st, index)
    if not checks["passed"]:
        raise AssertionError(f"anchor checks failed: {checks}")
    reads_of_held = sorted(t for t, purpose in cube_all.reads | cube_cells.reads
                           if purpose == "fit" and cube_all.group[t] == held)
    if reads_of_held:
        raise AssertionError(f"an anchor read the held-out tables {reads_of_held}")
    a.out.mkdir(parents=True)
    np.savez(a.out / "anchors.npz", rows=R, support=np.array([r["support"] for r in index], np.int16),
             U=U.astype(np.float32), genes=np.array([str(g) for g in st["genes"]]))
    (a.out / "anchors.json").write_text(json.dumps(index), encoding="utf-8")
    by = defaultdict(int)
    for r in index:
        by[f"{r['role']}:{r['group']}"] += 1
    manifest = {"held_group": held, "rows": int(R.shape[0]), "genes": int(R.shape[1]), "rank": int(U.shape[1]),
                "rows_by_group": dict(sorted(by.items())), "dropped_tables": cube_cells.dropped,
                "amplitude": arms.AMPLITUDE_T25, "checks": checks, "seconds": round(time.time() - t0, 1),
                "inputs": {"prepass_pkl": sha(a.prepass / "prepass.pkl"), "cube_manifest": sha(a.cube / "manifest.json"),
                           "protocol": sha(a.protocol), "target_keys": sha(a.target_keys),
                           **{f"bench_{m}": sha(Path(mod.__file__)) for m, mod in
                              (("arms", arms), ("fitting", fitting), ("splits", splits))}},
                "outputs": {"anchors_npz": sha(a.out / "anchors.npz"), "anchors_json": sha(a.out / "anchors.json")}}
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("held_group", "rows", "genes", "rank", "rows_by_group", "checks")}))


if __name__ == "__main__":
    main()
