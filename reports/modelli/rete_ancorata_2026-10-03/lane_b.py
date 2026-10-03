"""Lane B of the transfer-anchored network (version 3, PROTOCOLLO.md §5): a copy of
reports/modelli/rete_cellulare_2026-10-03/lane_b.py with the arms of version 3 (shifts of ancorata, ancorata_mean and
ancora_sola; cells of the trained arms only) and the transfer in two definitions: transfer_cells as lane A builds it
(the cell corpus's groups without the k562_viperturb table, the primary rule's reference) and transfer_cells_r3 as
the r3 lane B built it (whole groups), for continuity.

The r3 docstring follows. Pilot lane B for any held-out line (PROTOCOLLO.md §5): the six official members, local scale, on the real cells that
extract_cells.py took from the corpus shards (the same rule and the same Bench as lane_b_hepg2.py, which reads the local
HepG2 file instead).

Arms, on the chosen targets (choose_targets.py) and on the genes the held-out key measures:
- effects -> the same generator (trial-01): the bench's t25 transfer with the cell corpus's groups and with every group,
  and each network arm's predicted mean shift;
- the network's own cells (generate_cells.py).
Not a VCC score.

    py.cmd lane_b.py --held-group H1 --real <gen>/real_cells.npz --targets <gen>/targets.json --cells-dir <gen>
        --run <training> --cube <cube_r2> --protocol <bench PROTOCOLLO.json> --out <new folder>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "risposta_contesto_2026-10-02"))
from arms import AMPLITUDE_T25, Cube, table_means  # noqa: E402
from common import Timer, git_state, log, now_utc, sha256, write_json  # noqa: E402
from fitting import transfer_for  # noqa: E402
from splits import Split  # noqa: E402

from vcc2026.bench import Bench  # noqa: E402
from vcc2026.config import challenge  # noqa: E402
from vcc2026.inference import trial01_cells  # noqa: E402

F32 = np.float32
CELL_GROUPS = ("H1", "HepG2", "RPE1", "K562", "iPSC", "Jurkat", "Neuron")
NOT_IN_CELL_CORPUS = ("k562_viperturb",)       # tables of those groups whose cells the corpus does not hold
CONTROL = "non-targeting"


def load_csr(path: Path):
    z = np.load(path, allow_pickle=False)
    x = sp.csr_matrix((z["data"], z["indices"], z["indptr"]), shape=tuple(z["shape"]))
    return x, z["labels"].astype(str), z["genes"].astype(str)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--held-group", required=True)
    p.add_argument("--real", type=Path, required=True)
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--cells-dir", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--cube", type=Path, required=True)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--arms", nargs="+", default=["ancorata", "ancorata_mean", "ancora_sola"])
    p.add_argument("--cell-arms", nargs="+", default=["ancorata", "ancorata_mean"])
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--gen-seed", type=int, default=20260912)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    timer = Timer()
    P = json.loads(a.protocol.read_text(encoding="utf-8"))["parameters"]
    held = a.held_group
    x, lab, genes = load_csr(a.real)
    targets = [t for t in json.loads(a.targets.read_text(encoding="utf-8")) if (lab == t["symbol"]).sum() >= 4]
    labels = [t["symbol"] for t in targets]
    tkeys = [t["target_key"] for t in targets]
    target_rows = {t: np.flatnonzero(lab == t) for t in labels}
    ctrl_rows = np.flatnonzero(lab == CONTROL)
    a.out.mkdir(parents=True)
    log(f"{held}: {len(labels)} targets, {ctrl_rows.size} controls, {genes.size} genes")
    bench = Bench(x, target_rows, ctrl_rows, genes, a.out / "bench", seed=a.seed)
    bench.anchors()
    ctrl_x = x[ctrl_rows]
    basal = np.asarray(ctrl_x.sum(0), dtype=np.float64).ravel()
    libs = np.asarray(ctrl_x.sum(1)).ravel().astype(np.int64)
    ch = challenge()
    cube = Cube(a.cube, min_cells=P["min_cells"])

    class SubCube(Cube):
        def tables_of(self, group):
            return [t for t in super().tables_of(group) if t not in NOT_IN_CELL_CORPUS]

    cube_cells = SubCube(a.cube, min_cells=P["min_cells"])
    commons, _ = table_means(cube, Split("C", held, None, P["n_folds"]))
    cpos = pd.Index(cube.genes).get_indexer(genes)
    have = cpos >= 0
    effects = {}
    cells_srcs = [h for h in CELL_GROUPS if h != held and h in cube.groups]
    for name, cb, srcs in (("transfer_cells", cube_cells, cells_srcs), ("transfer_cells_r3", cube, cells_srcs),
                           ("transfer_all", cube, [h for h in cube.groups if h != held])):
        s, _ = transfer_for(cb, tkeys, srcs, commons)
        lfc = np.zeros((len(tkeys), genes.size), F32)
        obs = np.zeros_like(lfc, bool)
        lfc[:, have] = s[:, cpos[have]] * AMPLITUDE_T25
        obs[:, have] = np.isfinite(s[:, cpos[have]])
        effects[name] = (np.where(obs, np.nan_to_num(lfc), 0.0).astype(F32), obs)
    with np.load(a.run / "eval_observed.npz", allow_pickle=False) as z:
        model_genes = pd.Index([str(g) for g in z["genes"]])
    mcol = model_genes.get_indexer(genes)
    if (mcol < 0).any():
        raise SystemExit(f"{int((mcol < 0).sum())} real genes are not model genes")
    groups = json.loads((a.run / "eval_groups.json").read_text(encoding="utf-8"))
    gi = {(g["key"], g["symbol"]): i for i, g in enumerate(groups)}
    for arm in a.arms:
        with np.load(a.run / arm / "eval_shifts.npz", allow_pickle=False) as z:
            pm = z["predicted"]
        lfc = pm[[gi[(t["key"], t["symbol"])] for t in targets]][:, mcol].astype(F32)
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
    for arm in a.cell_arms:
        gx, glab, ggenes = load_csr(a.cells_dir / f"cells_{arm}.npz")
        gcol = pd.Index(ggenes).get_indexer(genes)
        gx = gx[:, gcol].tocsr()
        blocks, labs = [], []
        for t in labels:
            rows = np.flatnonzero(glab == t)[:bench.n_pred(t)]
            if rows.size < bench.n_pred(t):
                raise SystemExit(f"{arm}: {rows.size} generated cells for {t}, {bench.n_pred(t)} needed")
            blocks.append(gx[rows])
            labs.append(np.full(rows.size, t))
        bench.score(f"{arm}_cells", sp.vstack(blocks).tocsr(), np.concatenate(labs),
                    {"sha256": sha256(a.cells_dir / f"cells_{arm}.npz")})
        log(f"{arm}_cells scored ({timer()} s)")
    bench.finish(dict(stage=f"rete_cellulare lane B {held}", targets=labels, target_keys=tkeys, genes=int(genes.size),
                      real=str(a.real), real_sha256=sha256(a.real), seed=a.seed, gen_seed=a.gen_seed,
                      generator="trial-01 for effects; the network's NB mixture for its cells", run=str(a.run)))
    write_json(a.out / "run.json", dict(written_utc=now_utc(), git=git_state(), seconds=timer(),
                                        arguments={k: str(v) for k, v in vars(a).items()}))
    log("done")


if __name__ == "__main__":
    main()
