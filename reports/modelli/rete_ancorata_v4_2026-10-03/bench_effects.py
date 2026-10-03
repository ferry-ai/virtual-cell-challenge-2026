"""Lane A of version 4 (PROTOCOLLO.md §6): the cell network's predicted mean shifts against the bench cube, on the rows
of the held-out line, next to transfer references computed with regime-J table means.

A copy of version 3's lane A (reports/modelli/rete_ancorata_2026-10-03/bench_effects.py) with two changes:
- the table means (gamma = 1 term) and the generic response leave out every row of a hidden target, by the rule of
  anchors.py (hash fold of the prepass state, hidden symbols by target keys and by cube symbol); the number of keys left
  out is compared with the anchors' manifest when --anchors-manifest is given (they must be equal);
- three transfer references, one per source rule of anchors.py: transfer_all_J (the definition of version 4's anchor),
  transfer_cells_J (version 3's sources), transfer_prod_J (the tables of the t22/t25 recipe).

For one training (one held-out line group): every C or J group of the held-out keys (eval_groups.json) whose target key
(target_keys.json) is a usable row of a cube table of the same line becomes a row. The truth is the cube's ln fold change
of that table, the same for every arm. Indices: metrics.score_table of the bench, blocks of at most pds_block targets
per table. Nothing here reads a held-out table for a fit: the held tables are read as truth only.

    py.cmd bench_effects.py --run <training output> --cube <cube_r2> --protocol <bench PROTOCOLLO.json> \
        --target-keys target_keys.json --held-group HepG2 --splits <prepass splits.json> --out <new folder> \
        [--anchors-manifest <anchors_<line>_all/manifest.json>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "risposta_contesto_2026-10-02"))
import anchors as A  # noqa: E402
import splits as SPLITS  # noqa: E402
from arms import AMPLITUDE_T25, Cube, generic_vector, gene_weight  # noqa: E402
from common import coords_path, now_utc, sha256, write_json  # noqa: E402
from fitting import transfer_for  # noqa: E402
from metrics import blocks_of, score_table  # noqa: E402

REFERENCES = (("transfer_all_J", "all"), ("transfer_cells_J", "cells"), ("transfer_prod_J", "production"))


def hidden_from_splits(path: Path):
    """Hidden symbols, fold and number of folds of a prepass, from its splits.json."""
    s = json.loads(path.read_text(encoding="utf-8"))
    rule = s["hidden_rule"].split()
    fold, n_folds = int(rule[rule.index("fold") + 1]), int(rule[rule.index("of") + 1])
    return set(s["hidden_symbols"]), fold, n_folds


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", type=Path, required=True, help="training output: eval_groups.json, <arm>/eval_shifts.npz")
    p.add_argument("--cube", type=Path, required=True)
    p.add_argument("--protocol", type=Path, required=True, help="the bench protocol (min_cells, n_folds, gene table)")
    p.add_argument("--target-keys", type=Path, required=True)
    p.add_argument("--held-group", required=True)
    p.add_argument("--splits", type=Path, required=True, help="splits.json of the training's prepass (hidden symbols)")
    p.add_argument("--anchors-manifest", type=Path)
    p.add_argument("--arms", nargs="*", default=None)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    P = json.loads(a.protocol.read_text(encoding="utf-8"))["parameters"]
    cube_all = Cube(a.cube, min_cells=P["min_cells"])
    held = a.held_group
    if held not in cube_all.groups:
        raise SystemExit(f"{held} is not a group of the cube: {cube_all.groups}")
    import arms as ARMS
    hidden, fold, n_folds = hidden_from_splits(a.splits)
    keys_of_symbol = json.loads(a.target_keys.read_text(encoding="utf-8"))
    forbidden = A.hidden_keys(cube_all, {"hidden": sorted(hidden)}, keys_of_symbol, fold, n_folds, SPLITS)
    if a.anchors_manifest:
        kept_out = json.loads(a.anchors_manifest.read_text(encoding="utf-8"))["commons"]["keys_kept_out"]
        if kept_out != len(forbidden):
            raise SystemExit(f"{len(forbidden)} keys left out of the means here, {kept_out} in the anchors")
    commons, raw_means = A.j_table_means(cube_all, held, forbidden)
    cubes = {name: A.source_cube(ARMS, a.cube, P["min_cells"], rule) for name, rule in REFERENCES}
    coords = pd.read_csv(coords_path(P["gene_coordinates"]), sep="\t")
    ens_to_sym = {str(g).split(".")[0]: s for s, g in zip(coords["symbol"], coords["gene_id"]) if isinstance(g, str)}
    groups = json.loads((a.run / "eval_groups.json").read_text(encoding="utf-8"))
    with np.load(a.run / "eval_observed.npz", allow_pickle=False) as z:
        model_genes = [str(g) for g in z["genes"]]
    arms = a.arms or sorted(d.name for d in a.run.iterdir() if (d / "eval_shifts.npz").is_file())
    preds = {}
    for arm in arms:
        with np.load(a.run / arm / "eval_shifts.npz", allow_pickle=False) as z:
            preds[arm] = z["predicted"]
    mpos = {g: i for i, g in enumerate(model_genes)}
    col = np.array([mpos.get(g, -1) for g in cube_all.genes], np.int64)      # cube gene -> model gene
    have_col = col >= 0
    table_of = {}
    for t in cube_all.tables_of(held):
        for k in cube_all.keys_of(t):
            table_of.setdefault(k, t)
    rows, unmatched = [], {"no_key_in_cube": 0, "not_held": 0}
    for gi, g in enumerate(groups):
        if g["class"] not in ("C", "J"):
            unmatched["not_held"] += 1
            continue
        k = keys_of_symbol.get(g["symbol"]) or f"SYM:{g['symbol']}"
        t = table_of.get(k)
        if t is None:
            unmatched["no_key_in_cube"] += 1
            continue
        rows.append(dict(gi=gi, cls=g["class"], key=k, symbol=g["symbol"], table=t, cells=g["evaluated_cells"]))
    rows = pd.DataFrame(rows).drop_duplicates(["table", "key"])
    sources = {name: [h for h in cb.groups if h != held] for name, cb in cubes.items()}
    generic = generic_vector(cube_all, raw_means, {held})
    records = []
    for t, rt in rows.groupby("table"):
        keys = rt["key"].tolist()
        w = gene_weight(cube_all.basal[t])
        for blk in blocks_of(keys, P["pds_block"]):
            bk = [keys[i] for i in blk]
            br = rt.iloc[blk]
            truth, _ = cube_all.get(t, "raw", bk, purpose="truth")
            se, _ = cube_all.get(t, "se", bk, purpose="truth")
            tpos = cube_all.target_gene_positions(bk, ens_to_sym)
            arm_pred, support = {}, {}
            for arm, m in preds.items():
                x = np.full((len(bk), len(cube_all.genes)), np.nan, np.float32)
                x[:, have_col] = m[br["gi"].to_numpy()][:, col[have_col]].astype(np.float32)
                arm_pred[arm] = x
            is_c = (br["cls"] == "C").to_numpy()
            for name, cb in cubes.items():
                s, sup = transfer_for(cb, bk, sources[name], commons)
                s = s * AMPLITUDE_T25
                s[~is_c] = np.nan                      # J targets were hidden from the network: no transfer row
                arm_pred[name] = s
                support[name] = sup
            arm_pred["generic_pseudobulk"] = np.broadcast_to(generic, truth.shape).copy()
            for name, pred in arm_pred.items():
                sc = score_table(pred, truth, se, w, bk, tpos, block_size=len(bk))
                for i, (_, r) in enumerate(br.iterrows()):
                    records.append(dict(held_group=held, table=t, target_key=r["key"], symbol=r["symbol"],
                                        cls=r["cls"], eval_cells=int(r["cells"]), arm=name,
                                        **{f"support_{n}": int(support[n][i]) for n in support},
                                        **{m: float(v[i]) for m, v in sc.items()}))
    reads_of_held_for_fit = sorted(t for cb in (cube_all, *cubes.values()) for t, purpose in cb.reads
                                   if purpose == "fit" and cube_all.group[t] == held)
    if reads_of_held_for_fit:
        raise AssertionError(f"a baseline read the held-out tables {reads_of_held_for_fit}")
    df = pd.DataFrame(records)
    a.out.mkdir(parents=True)
    df.to_csv(a.out / f"per_target_{held}.csv.gz", index=False, compression="gzip")
    metrics = ["pds", "cos", "cos_spec", "mse_ratio", "sign_sig"]
    summary = {"written_utc": now_utc(), "held_group": held, "run": str(a.run), "arms": arms,
               "rows": {c: int((rows["cls"] == c).sum()) for c in ("C", "J")}, "unmatched_groups": unmatched,
               "tables": sorted(rows["table"].unique().tolist()), "sources": sources,
               "commons": {"regime": "J", "hidden_fold": fold, "n_folds": n_folds, "keys_kept_out": len(forbidden)},
               "inputs": {"eval_groups": sha256(a.run / "eval_groups.json"), "cube_manifest": sha256(a.cube / "manifest.json"),
                          "target_keys": sha256(a.target_keys), "splits": sha256(a.splits),
                          **{arm: sha256(a.run / arm / "eval_shifts.npz") for arm in arms}},
               "means": {c: df[df.cls == c].groupby("arm")[metrics].mean().round(5).to_dict(orient="index")
                         for c in ("C", "J")},
               "note": "lane A of version 4: effect indices of the bench on the cube rows of the held-out line, regime-J "
                       "means, not VCC scores"}
    write_json(a.out / "summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("held_group", "rows", "unmatched_groups", "commons")}))


if __name__ == "__main__":
    main()
