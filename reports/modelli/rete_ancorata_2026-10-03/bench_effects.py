"""Pilot lane A (PROTOCOLLO.md §5): the cell network's predicted mean shifts against the bench cube, on the rows of
the held-out line, next to the transfer baselines of the same rows.

For one training (one held-out line group): every C or J group of the held-out keys (eval_groups.json) whose target
key (target_keys.json) is a usable row of a cube table of the same line becomes a row. The truth is the cube's ln
fold change of that table, the same for every arm. Predictions on the cube genes (matched by symbol):
- each arm's shift (<arm>/eval_shifts.npz, cell_data.shift on the model's expected proportions);
- C rows only: the t25 transfer of the bench (reports/modelli/risposta_contesto_2026-10-02: group_mean,
  combine_groups, amplitude 1.576) from the other line groups of the cell corpus, on their tables that the corpus
  also holds ('transfer_cells'), and from every other group of the bench ('transfer_all');
- the bench's generic response without the held-out group ('generic_pseudobulk').
Indices: metrics.score_table of the bench, blocks of at most 300 targets per table. Writes per_target_<group>.csv.gz
and summary.json. Nothing here reads a held-out table for a fit: the cube's held tables are read as truth only.

    py.cmd bench_effects.py --run <training output> --cube <data>/.../cube_r2 --protocol <bench PROTOCOLLO.json>
        --target-keys target_keys.json --held-group HepG2 --out <new folder>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "risposta_contesto_2026-10-02"))
from arms import AMPLITUDE_T25, Cube, generic_vector, gene_weight, table_means  # noqa: E402
from common import coords_path, now_utc, sha256, write_json  # noqa: E402
from fitting import transfer_for  # noqa: E402
from metrics import blocks_of, score_table  # noqa: E402
from splits import Split  # noqa: E402

# line groups of the bench whose cells are in the corpus of the cell network (PROTOCOLLO.md §3)
CELL_GROUPS = ("H1", "HepG2", "RPE1", "K562", "iPSC", "Jurkat", "Neuron")
NOT_IN_CELL_CORPUS = ("k562_viperturb",)       # tables of those groups whose cells the corpus does not hold


class SubCube(Cube):
    """The bench cube restricted to some tables (tables_of drops the others)."""

    def __init__(self, folder: Path, min_cells: float, drop=()):
        super().__init__(folder, min_cells)
        self.dropped = sorted(t for t in self.tables if t in set(drop))

    def tables_of(self, group: str) -> list[str]:
        return [t for t in super().tables_of(group) if t not in self.dropped]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", type=Path, required=True, help="training output: eval_groups.json, <arm>/eval_shifts.npz")
    p.add_argument("--cube", type=Path, required=True)
    p.add_argument("--protocol", type=Path, required=True, help="the bench protocol (min_cells, n_folds, gene table)")
    p.add_argument("--target-keys", type=Path, required=True)
    p.add_argument("--held-group", required=True)
    p.add_argument("--arms", nargs="*", default=None)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    P = json.loads(a.protocol.read_text(encoding="utf-8"))["parameters"]
    cube_all = Cube(a.cube, min_cells=P["min_cells"])
    cube_cells = SubCube(a.cube, P["min_cells"], NOT_IN_CELL_CORPUS)
    held = a.held_group
    if held not in cube_all.groups:
        raise SystemExit(f"{held} is not a group of the cube: {cube_all.groups}")
    # table means of the source tables only (the held group's tables are skipped: they are truth, never fit inputs);
    # for the sources these are the values P3 used
    commons, raw_means = table_means(cube_all, Split("C", held, None, P["n_folds"]))
    coords = pd.read_csv(coords_path(P["gene_coordinates"]), sep="\t")
    ens_to_sym = {str(g).split(".")[0]: s for s, g in zip(coords["symbol"], coords["gene_id"]) if isinstance(g, str)}
    keys_of_symbol = json.loads(a.target_keys.read_text(encoding="utf-8"))
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
    # rows: held-out C and J groups that are usable rows of a cube table of the same line
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
    others_cells = [h for h in CELL_GROUPS if h != held and h in cube_cells.groups]
    others_all = [h for h in cube_all.groups if h != held]
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
            arm_pred = {}
            for arm, m in preds.items():
                x = np.full((len(bk), len(cube_all.genes)), np.nan, np.float32)
                x[:, have_col] = m[br["gi"].to_numpy()][:, col[have_col]].astype(np.float32)
                arm_pred[arm] = x
            is_c = (br["cls"] == "C").to_numpy()
            for name, cube_s, srcs in (("transfer_cells", cube_cells, others_cells),
                                       ("transfer_all", cube_all, others_all)):
                s, support = transfer_for(cube_s, bk, srcs, commons)
                s = s * AMPLITUDE_T25
                s[~is_c] = np.nan                      # J targets were hidden from the network: no transfer row
                arm_pred[name] = s
                arm_pred[f"{name}_support"] = support
            arm_pred["generic_pseudobulk"] = np.broadcast_to(generic, truth.shape).copy()
            support = {n: arm_pred.pop(f"{n}_support") for n in ("transfer_cells", "transfer_all")}
            for name, pred in arm_pred.items():
                sc = score_table(pred, truth, se, w, bk, tpos, block_size=len(bk))
                for i, (_, r) in enumerate(br.iterrows()):
                    records.append(dict(held_group=held, table=t, target_key=r["key"], symbol=r["symbol"],
                                        cls=r["cls"], eval_cells=int(r["cells"]), arm=name,
                                        support_cells=int(support["transfer_cells"][i]),
                                        support_all=int(support["transfer_all"][i]),
                                        **{m: float(v[i]) for m, v in sc.items()}))
    reads_of_held_for_fit = sorted(t for t, purpose in cube_all.reads | cube_cells.reads
                                   if purpose == "fit" and cube_all.group[t] == held)
    if reads_of_held_for_fit:
        raise AssertionError(f"a baseline read the held-out tables {reads_of_held_for_fit}")
    df = pd.DataFrame(records)
    a.out.mkdir(parents=True)
    df.to_csv(a.out / f"per_target_{held}.csv.gz", index=False, compression="gzip")
    metrics = ["pds", "cos", "cos_spec", "mse_ratio", "sign_sig"]
    summary = {"written_utc": now_utc(), "held_group": held, "run": str(a.run), "arms": arms,
               "rows": {c: int((rows["cls"] == c).sum()) for c in ("C", "J")}, "unmatched_groups": unmatched,
               "tables": sorted(rows["table"].unique().tolist()), "sources_cells": others_cells,
               "sources_all": others_all, "dropped_tables_for_cells": cube_cells.dropped,
               "inputs": {"eval_groups": sha256(a.run / "eval_groups.json"), "cube_manifest": sha256(a.cube / "manifest.json"),
                          "target_keys": sha256(a.target_keys),
                          **{arm: sha256(a.run / arm / "eval_shifts.npz") for arm in arms}},
               "means": {c: df[df.cls == c].groupby("arm")[metrics].mean().round(5).to_dict(orient="index")
                         for c in ("C", "J")},
               "note": "lane A of the pilot: effect indices of the bench on the cube rows of the held-out line, not VCC scores"}
    write_json(a.out / "summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("held_group", "rows", "unmatched_groups")}))


if __name__ == "__main__":
    main()
