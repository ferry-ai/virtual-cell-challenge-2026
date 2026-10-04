"""Anchors of the transfer-anchored cell network, version 4 (PROTOCOLLO.md of this folder), for one held-out line group H.

The anchor of a (line group L, target t) is the bench's t25 transfer of t (reports/modelli/risposta_contesto_2026-10-02:
group_mean, combine_groups, amplitude 1.576) from the source groups other than L and H. Rows:
- every (L, t) with at least one admitted training cell (class 'train') of an anchored modality in the prepass state,
  role 'train';
- the held-out line's C evaluation groups, as (H, t), from every source group but H, role 'eval'.
Hidden targets (the state's 'hidden', classes J and T) get no row; a row without any source is left out. The anchored
modality is CRISPRi only (--modalities), as in version 3.

Two changes from version 3 (reports/modelli/rete_ancorata_2026-10-03/anchors.py):
- the table means subtracted by group_mean (gamma = 1) are computed on the rows of regime J: no row of a hidden target
  enters them, from any table (Codex's review of 3/10, P1; PROTOCOLLO §9 of version 3). A hidden target is a key whose
  R-LEAD hash fold is the state's hidden fold, a key of a symbol the state hides, or a key whose cube symbol it hides:
  the union, so that a key spelled differently in the cube and in the target keys cannot slip through. Changing the
  responses of hidden targets changes no anchor (test_anchors_v4.py);
- --sources says which bench tables feed the transfer:
    cells       the cell corpus's line groups, without the k562_viperturb table (version 3, lane A 'transfer_cells');
    all         every group and table of the bench cube: CD4T (three states), HCT116, HEK293T and K562 VIPerturb join
                as aggregates (D-053: every eligible context in the role its data allow);
    production  the tables of the t22/t25 recipe: k562_gwps, the three CD4T states, hct116, hek293t.
  The manifest records the rule, the tables, the most sources a row can have (max_sources, the divisor of the support
  feature) and the hidden keys left out of the means.

Writes anchors.npz (rows [R, G] float16 on the model's genes, NaN where no source measures a gene; support [R]; U [G, k],
the top-k gene directions of the training rows), anchors.json (one entry per row) and manifest.json.

    python anchors.py --prepass <dir with prepass.pkl> --cube <cube_r2> --protocol <bench PROTOCOLLO.json> \
        --target-keys target_keys.json --sources all --out <new dir> [--bench-code <dir of arms.py ...>] [--rank 32]
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
PRODUCTION_TABLES = ("k562_gwps", "cd4_rest", "cd4_stim8hr", "cd4_stim48hr", "hct116", "hek293t")
SOURCES = ("cells", "all", "production")
MODALITIES = ("CRISPRi",)                      # the modality of the bench's effects
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


def source_cube(arms, folder, min_cells, sources: str):
    """The bench cube restricted to the tables of a source rule (tables_of drops the others; groups without a table
    are no longer groups of the cube)."""
    class SourceCube(arms.Cube):
        def __init__(self):
            super().__init__(folder, min_cells)
            if sources == "cells":
                keep = [t for t in self.tables if self.group[t] in CELL_GROUPS and t not in NOT_IN_CELL_CORPUS]
            elif sources == "production":
                keep = [t for t in self.tables if t in PRODUCTION_TABLES]
            elif sources == "all":
                keep = list(self.tables)
            else:
                raise ValueError(sources)
            self.kept = keep
            self.dropped = sorted(t for t in self.tables if t not in keep)
            self.groups = sorted({self.group[t] for t in keep})

        def tables_of(self, group):
            return [t for t in super().tables_of(group) if t in self.kept]
    return SourceCube()


def hidden_keys(cube, st, keys_of_symbol: dict, fold: int, n_folds: int, splits) -> set:
    """The keys whose rows may not enter the table means: the hash fold of the state's hidden fold, the keys of the
    symbols the state hides (by the target keys), and the cube keys whose symbol it hides."""
    hidden_symbols = set(st.get("hidden", ()))
    out = set()
    for t in cube.tables:
        for k in cube.keys_of(t):
            if splits.target_fold(k, n_folds) == fold or cube.symbol.get(k) in hidden_symbols:
                out.add(k)
    out |= {keys_of_symbol.get(s) or f"SYM:{s}" for s in hidden_symbols}
    return out


def j_table_means(cube, held: str, forbidden: set, block: int = 1000):
    """Per table of the sources (the held-out group's tables skipped): mean shrunk and mean raw over the usable rows
    whose key is not forbidden. arms.table_means with the regime-J row rule made explicit."""
    shr, raw = {}, {}
    G = len(cube.genes)
    for t in cube.tables:
        if cube.group[t] == held:
            continue
        keys = [k for k in cube.keys_of(t) if k not in forbidden]
        sums = {"shrunk": np.zeros(G), "raw": np.zeros(G)}
        cnts = {"shrunk": np.zeros(G), "raw": np.zeros(G)}
        for b0 in range(0, len(keys), block):
            for kind in sums:
                x, _ = cube.get(t, kind, keys[b0:b0 + block])
                ok = np.isfinite(x)
                sums[kind] += np.where(ok, x, 0).sum(0)
                cnts[kind] += ok.sum(0)
        shr[t] = np.divide(sums["shrunk"], cnts["shrunk"], out=np.zeros(G), where=cnts["shrunk"] > 0).astype(np.float32)
        raw[t] = np.divide(sums["raw"], cnts["raw"], out=np.full(G, np.nan), where=cnts["raw"] > 0).astype(np.float32)
    return shr, raw


def training_pairs(st, modalities=MODALITIES) -> dict:
    """Symbols with at least one admitted training cell of an anchored modality, per line group of the cell's key."""
    train = st["classes"].index("train")
    group_of_key = [st["key_group"][k] for k in st["key_names"]]
    mods = np.array([m in set(modalities) for m in st["modalities"]], bool)
    out = defaultdict(set)
    for s in st["shards"]:
        sel = (np.asarray(s["admitted"], bool) & ~np.asarray(s["control"], bool)
               & (np.asarray(s["cls"]) == train) & (np.asarray(s["tgt"]) >= 0) & mods[np.asarray(s["mod"])])
        if not sel.any():
            continue
        pairs = np.unique(np.stack([np.asarray(s["key"])[sel], np.asarray(s["tgt"])[sel]], 1), axis=0)
        for k, t in pairs.tolist():
            out[group_of_key[k]].add(st["symbols"][t])
    return out


def sources_for(row_group: str, held: str, cube_groups) -> list:
    return [h for h in sorted(cube_groups) if h not in (row_group, held)]


def jobs_of(st, modalities=MODALITIES) -> list:
    """(row group, role, symbols): the training pairs of every group, then the held-out line's C groups."""
    held = st["holdout_group"]
    hidden = set(st.get("hidden", ()))
    pairs = training_pairs(st, modalities)
    if held in pairs:
        raise AssertionError(f"training cells of the held-out group {held}")
    leaked = sorted(set().union(*pairs.values()) & hidden) if pairs else []
    if leaked:
        raise AssertionError(f"hidden symbols with training cells: {leaked[:5]}")
    c_syms = sorted({g["symbol"] for g in st["eval_groups"] if g["class"] == "C"} - hidden)
    return [(L, "train", sorted(s)) for L, s in sorted(pairs.items())] + [(held, "eval", c_syms)]


def compute(st, cube_src, commons, keys_of_symbol, transfer_for, amplitude, basis, rank=32, log=print,
            modalities=MODALITIES):
    """Rows, their index and the projection U, on the model's genes (st['genes'])."""
    held = st["holdout_group"]
    model_genes = [str(g) for g in st["genes"]]
    mpos = {g: i for i, g in enumerate(model_genes)}
    cube_col = np.array([mpos.get(g, -1) for g in cube_src.genes], np.int64)
    have = cube_col >= 0
    G = len(model_genes)
    rows, index = [], []
    for L, role, syms in jobs_of(st, modalities):
        srcs = sources_for(L, held, cube_src.groups)
        if L in srcs or held in srcs:
            raise AssertionError(f"sources of {L} include {L} or {held}")
        if not srcs or not syms:
            log(json.dumps({"group": L, "role": role, "symbols": len(syms), "sources": srcs, "rows": 0}))
            continue
        keys = [keys_of_symbol.get(s) or f"SYM:{s}" for s in syms]
        kept = 0
        for b0 in range(0, len(keys), BLOCK):
            s, support = transfer_for(cube_src, keys[b0:b0 + BLOCK], srcs, commons)
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


def check(st, index, forbidden=None) -> dict:
    """The leakage checks: no source equal to the row's group or the held-out one, no hidden target with a row, roles
    as expected, and (version 4) no row of a target whose key is among the keys kept out of the means."""
    held, hidden = st["holdout_group"], set(st.get("hidden", ()))
    bad_src = [r for r in index if r["group"] in r["sources"] or held in r["sources"]]
    bad_hidden = [r for r in index if r["symbol"] in hidden]
    bad_role = [r for r in index if (r["role"] == "eval") != (r["group"] == held)]
    bad_key = [r for r in index if forbidden is not None and r["target_key"] in forbidden]
    return {"own_or_held_in_sources": len(bad_src), "hidden_with_anchor": len(bad_hidden),
            "role_mismatch": len(bad_role), "row_of_a_key_kept_out_of_the_means": len(bad_key),
            "passed": not (bad_src or bad_hidden or bad_role or bad_key)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prepass", type=Path, required=True)
    p.add_argument("--cube", type=Path, required=True)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--target-keys", type=Path, required=True)
    p.add_argument("--sources", choices=SOURCES, required=True)
    p.add_argument("--bench-code", type=Path, default=HERE.parent / "risposta_contesto_2026-10-02")
    p.add_argument("--rank", type=int, default=32)
    p.add_argument("--modalities", nargs="+", default=list(MODALITIES))
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
    args = st.get("args", {})
    if str(args.get("hidden_fold", "None")) == "None":
        raise SystemExit("the prepass state has no hidden fold: version 4 anchors need regime J means")
    fold, n_folds = int(args["hidden_fold"]), int(args.get("n_folds", P["n_folds"]))
    if n_folds != int(P["n_folds"]):
        raise SystemExit(f"the prepass state has {n_folds} folds, the bench protocol {P['n_folds']}")
    cube_all = arms.Cube(a.cube, min_cells=P["min_cells"])
    cube_src = source_cube(arms, a.cube, P["min_cells"], a.sources)
    if held not in cube_all.groups:
        raise SystemExit(f"{held} is not a group of the cube")
    keys_of_symbol = json.loads(a.target_keys.read_text(encoding="utf-8"))
    forbidden = hidden_keys(cube_all, st, keys_of_symbol, fold, n_folds, splits)
    commons, _ = j_table_means(cube_all, held, forbidden)
    R, index, U = compute(st, cube_src, commons, keys_of_symbol, fitting.transfer_for, arms.AMPLITUDE_T25,
                          fitting.basis, a.rank, modalities=a.modalities)
    checks = check(st, index, forbidden)
    if not checks["passed"]:
        raise AssertionError(f"anchor checks failed: {checks}")
    reads_of_held = sorted(t for t, purpose in cube_all.reads | cube_src.reads
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
    source_groups = [g for g in cube_src.groups if g != held]
    manifest = {"held_group": held, "rows": int(R.shape[0]), "genes": int(R.shape[1]), "rank": int(U.shape[1]),
                "anchored_modalities": list(a.modalities), "version": 4,
                "sources": {"rule": a.sources, "groups": source_groups, "tables": cube_src.kept,
                            "dropped_tables": cube_src.dropped},
                "max_sources": max(1, len(source_groups)),
                "commons": {"regime": "J", "hidden_fold": fold, "n_folds": n_folds,
                            "keys_kept_out": len(forbidden), "rule": "table means of the source tables without the "
                            "held-out group's tables and without every row of a hidden target (hash fold, hidden "
                            "symbols by target keys, hidden symbols by cube symbol)"},
                "rows_by_group": dict(sorted(by.items())), "amplitude": arms.AMPLITUDE_T25, "checks": checks,
                "seconds": round(time.time() - t0, 1),
                "inputs": {"prepass_pkl": sha(a.prepass / "prepass.pkl"), "cube_manifest": sha(a.cube / "manifest.json"),
                           "protocol": sha(a.protocol), "target_keys": sha(a.target_keys),
                           **{f"bench_{m}": sha(Path(mod.__file__)) for m, mod in
                              (("arms", arms), ("fitting", fitting), ("splits", splits))}},
                "outputs": {"anchors_npz": sha(a.out / "anchors.npz"), "anchors_json": sha(a.out / "anchors.json")}}
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("held_group", "rows", "genes", "rank", "rows_by_group", "checks",
                                                "max_sources")}))


if __name__ == "__main__":
    main()
