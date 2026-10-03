"""Pilot lane B on HepG2 (PROTOCOLLO.md §5): the six official members on real held-out cells, local scale.

Truth, replicate and baseline as the six-member bench of R-LEAD (vcc2026.bench.Bench: half A of each target's cells and
the controls; half B as the replicate; the scorer's generic profile as the baseline). Arms, on the same targets
(choose_targets.py) and the same genes (HepG2 genes that the model also has):
- effects -> the same generator (trial-01, vcc2026.inference.trial01_cells, the stage-45 path):
  the bench's t25 transfer with the cell corpus's groups and with every group ('transfer_cells', 'transfer_all'),
  and each network arm's predicted mean shift ('<arm>_shift');
- the network's own cells ('<arm>_cells', generate_cells.py on Kaggle).
The first comparison asks which model predicts the mean effect better; the second whether the learned distribution
improves what is delivered. Not a VCC score.

    py.cmd lane_b_hepg2.py --targets <gen>/targets.json --cells-dir <gen> --run <training> --cube <cube_r2>
        --protocol <bench PROTOCOLLO.json> --out <new folder> [--max-controls 2048] [--cap-cells 64]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "risposta_contesto_2026-10-02"))
from arms import AMPLITUDE_T25, Cube, table_means  # noqa: E402
from common import Timer, coords_path, git_state, h5_column, log, now_utc, sha256, write_json  # noqa: E402
from fitting import transfer_for  # noqa: E402
from six_member_hepg2 import read_rows  # noqa: E402
from splits import Split  # noqa: E402

from vcc2026.bench import Bench  # noqa: E402
from vcc2026.config import challenge  # noqa: E402
from vcc2026.inference import trial01_cells  # noqa: E402

F32 = np.float32
CELL_GROUPS = ("H1", "HepG2", "RPE1", "K562", "iPSC", "Jurkat", "Neuron")
GROUP = "HepG2"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--cells-dir", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--cube", type=Path, required=True)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--arms", nargs="+", default=["cells", "mean", "generic"])
    p.add_argument("--max-controls", type=int, default=2048)
    p.add_argument("--cap-cells", type=int, default=64)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--gen-seed", type=int, default=20260912)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    timer = Timer()
    P = json.loads(a.protocol.read_text(encoding="utf-8"))["parameters"]
    targets = json.loads(a.targets.read_text(encoding="utf-8"))
    labels = [t["symbol"] for t in targets]
    tkeys = [t["target_key"] for t in targets]
    cube = Cube(a.cube, min_cells=P["min_cells"])
    hepg2 = Path(json.loads((Path(str(a.cube)).parent / "hepg2_r2" / "manifest.json").read_text(encoding="utf-8"))
                 ["input"]["path"])
    with h5py.File(hepg2, "r") as f:
        cell_gene = h5_column(f["obs/gene"])
        native = h5_column(f["var/gene_name"]).astype(str)
    with np.load(a.run / "eval_observed.npz", allow_pickle=False) as z:
        model_genes = [str(g) for g in z["genes"]]
    mpos = {g: i for i, g in enumerate(model_genes)}
    keep = np.array([g in mpos for g in native])          # the scoring genes: HepG2 genes the model also has
    genes = native[keep]
    rng = np.random.default_rng(a.seed)
    target_rows = {}
    for lab in labels:
        r = np.flatnonzero(cell_gene == lab)
        if r.size > a.cap_cells:
            r = np.sort(rng.choice(r, a.cap_cells, replace=False))
        target_rows[lab] = r
    ctrl = np.flatnonzero(cell_gene == "non-targeting")
    if a.max_controls and ctrl.size > a.max_controls:
        ctrl = np.sort(np.random.default_rng(a.seed + 1).choice(ctrl, a.max_controls, replace=False))
    all_rows = np.sort(np.concatenate(list(target_rows.values()) + [ctrl]))
    log(f"reading {all_rows.size} HepG2 cells ({len(labels)} targets, {ctrl.size} controls), {keep.sum()} genes")
    x = read_rows(hepg2, all_rows)[:, np.flatnonzero(keep)].tocsr()
    remap = {r: i for i, r in enumerate(all_rows)}
    target_rows = {t: np.array([remap[r] for r in v]) for t, v in target_rows.items()}
    ctrl_rows = np.array([remap[r] for r in ctrl])
    a.out.mkdir(parents=True)
    bench = Bench(x, target_rows, ctrl_rows, genes, a.out / "bench", seed=a.seed)
    bench.anchors()
    ctrl_x = x[ctrl_rows]
    basal = np.asarray(ctrl_x.sum(0), dtype=np.float64).ravel()
    libs = np.asarray(ctrl_x.sum(1)).ravel().astype(np.int64)
    ch = challenge()

    # effects on the scoring genes: (targets x genes) ln fold change and the observed mask
    effects = {}
    commons, _ = table_means(cube, Split("C", GROUP, None, P["n_folds"]))
    cpos = pd.Index(cube.genes).get_indexer(genes)
    have = cpos >= 0
    for name, srcs in (("transfer_cells", [h for h in CELL_GROUPS if h != GROUP and h in cube.groups]),
                       ("transfer_all", [h for h in cube.groups if h != GROUP])):
        s, _ = transfer_for(cube, tkeys, srcs, commons)
        lfc = np.zeros((len(tkeys), genes.size), F32)
        lfc[:, have] = s[:, cpos[have]] * AMPLITUDE_T25
        obs = np.zeros_like(lfc, bool)
        obs[:, have] = np.isfinite(s[:, cpos[have]])
        effects[name] = (np.where(obs, np.nan_to_num(lfc), 0.0).astype(F32), obs)
    groups = json.loads((a.run / "eval_groups.json").read_text(encoding="utf-8"))
    gi = {(g["key"], g["symbol"]): i for i, g in enumerate(groups)}
    gpos = np.array([mpos[g] for g in genes])
    for arm in a.arms:
        with np.load(a.run / arm / "eval_shifts.npz", allow_pickle=False) as z:
            pm = z["predicted"]
        rows = [gi[(t["key"], t["symbol"])] for t in targets]
        lfc = pm[rows][:, gpos].astype(F32)
        obs = np.isfinite(lfc)
        effects[f"{arm}_shift"] = (np.where(obs, lfc, 0.0).astype(F32), obs)
    for name, (lfc, obs) in effects.items():
        stream = np.random.default_rng(a.gen_seed)
        blocks, labs = [], []
        for i, t in enumerate(labels):
            n = bench.n_pred(t)
            cells, _ = trial01_cells(basal, lfc[i], obs[i], libs, n, stream,
                                     max_stored_per_cell=ch.max_stored_per_cell,
                                     max_counts_per_cell=ch.max_counts_per_cell)
            blocks.append(cells)
            labs.append(np.full(n, t))
        bench.score(name, sp.vstack(blocks).tocsr(), np.concatenate(labs), {"observed_share": float(obs.mean())})
        log(f"{name} scored ({timer()} s)")
    # the network's own cells
    for arm in a.arms:
        z = np.load(a.cells_dir / f"cells_{arm}.npz", allow_pickle=False)
        gx = sp.csr_matrix((z["data"], z["indices"], z["indptr"]), shape=tuple(z["shape"]))[:, gpos].tocsr()
        lab = z["labels"].astype(str)
        blocks, labs = [], []
        for t in labels:
            rows = np.flatnonzero(lab == t)[:bench.n_pred(t)]
            if rows.size < bench.n_pred(t):
                raise SystemExit(f"{arm}: {rows.size} generated cells for {t}, {bench.n_pred(t)} needed")
            blocks.append(gx[rows])
            labs.append(np.full(rows.size, t))
        bench.score(f"{arm}_cells", sp.vstack(blocks).tocsr(), np.concatenate(labs),
                    {"source": str(a.cells_dir / f"cells_{arm}.npz"), "sha256": sha256(a.cells_dir / f"cells_{arm}.npz")})
        log(f"{arm}_cells scored ({timer()} s)")
    bench.finish(dict(stage="rete_cellulare lane B HepG2", targets=labels, target_keys=tkeys, genes=int(genes.size),
                      cap_cells=a.cap_cells, max_controls=a.max_controls, seed=a.seed, gen_seed=a.gen_seed,
                      generator="trial-01 for effects; the network's NB mixture for its cells", run=str(a.run)))
    write_json(a.out / "run.json", dict(written_utc=now_utc(), git=git_state(), seconds=timer(),
                                        arguments={k: str(v) for k, v in vars(a).items()}))
    log("done")


if __name__ == "__main__":
    main()
