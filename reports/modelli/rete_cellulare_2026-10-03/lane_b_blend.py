"""Descriptive check of MISCELE.md: the transfer blended with the network's predicted shift, on the six members.

The same targets, real cells, truth, replicate and baseline as lane B (lane_b.py, same seeds); arms through the same
trial-01 generator: transfer_cells, cells_shift and blend_w = w * transfer + (1 - w) * network on the genes where the
transfer is observed (where the network has no value the transfer stays). Not a VCC score, not an adoption.

    py.cmd lane_b_blend.py --held-group H1 --real <gen>/real_cells.npz --targets <gen>/targets.json --run <training>
        --cube <cube_r2> --protocol <bench PROTOCOLLO.json> --out <new folder>
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "risposta_contesto_2026-10-02"))
from arms import AMPLITUDE_T25, Cube, table_means  # noqa: E402
from common import Timer, git_state, log, now_utc, sha256, write_json  # noqa: E402
from fitting import transfer_for  # noqa: E402
from lane_b import CELL_GROUPS, CONTROL, load_csr  # noqa: E402
from splits import Split  # noqa: E402

from vcc2026.bench import Bench  # noqa: E402
from vcc2026.config import challenge  # noqa: E402
from vcc2026.inference import trial01_cells  # noqa: E402

F32 = np.float32
WEIGHTS = (0.5, 0.75, 0.25)          # primary first (MISCELE.md)


def blend(t_lfc: np.ndarray, t_obs: np.ndarray, n_lfc: np.ndarray, n_obs: np.ndarray, w: float):
    """w * transfer + (1 - w) * network where both are observed, the transfer alone where the network is missing,
    nothing where the transfer is missing: the observed mask stays the transfer's (MISCELE.md)."""
    mix = np.where(t_obs & n_obs, w * t_lfc + (1 - w) * n_lfc, t_lfc)
    return np.where(t_obs, mix, 0.0).astype(F32), t_obs.copy()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--held-group", required=True)
    p.add_argument("--real", type=Path, required=True)
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--cube", type=Path, required=True)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--arm", default="cells")
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
    bench = Bench(x, target_rows, ctrl_rows, genes, a.out / "bench", seed=a.seed)
    bench.anchors()
    ctrl_x = x[ctrl_rows]
    basal = np.asarray(ctrl_x.sum(0), dtype=np.float64).ravel()
    libs = np.asarray(ctrl_x.sum(1)).ravel().astype(np.int64)
    ch = challenge()
    cube = Cube(a.cube, min_cells=P["min_cells"])
    commons, _ = table_means(cube, Split("C", held, None, P["n_folds"]))
    cpos = pd.Index(cube.genes).get_indexer(genes)
    have = cpos >= 0
    s, _ = transfer_for(cube, tkeys, [h for h in CELL_GROUPS if h != held and h in cube.groups], commons)
    t_lfc = np.zeros((len(tkeys), genes.size), F32)
    t_obs = np.zeros_like(t_lfc, bool)
    t_lfc[:, have] = s[:, cpos[have]] * AMPLITUDE_T25
    t_obs[:, have] = np.isfinite(s[:, cpos[have]])
    t_lfc = np.where(t_obs, np.nan_to_num(t_lfc), 0.0).astype(F32)
    with np.load(a.run / "eval_observed.npz", allow_pickle=False) as z:
        model_genes = pd.Index([str(g) for g in z["genes"]])
    mcol = model_genes.get_indexer(genes)
    if (mcol < 0).any():
        raise SystemExit(f"{int((mcol < 0).sum())} real genes are not model genes")
    groups = json.loads((a.run / "eval_groups.json").read_text(encoding="utf-8"))
    gi = {(g["key"], g["symbol"]): i for i, g in enumerate(groups)}
    with np.load(a.run / a.arm / "eval_shifts.npz", allow_pickle=False) as z:
        pm = z["predicted"]
    n_lfc = pm[[gi[(t["key"], t["symbol"])] for t in targets]][:, mcol].astype(F32)
    n_obs = np.isfinite(n_lfc)
    n_lfc = np.where(n_obs, n_lfc, 0.0).astype(F32)
    effects = {"transfer_cells": (t_lfc, t_obs), f"{a.arm}_shift": (n_lfc, n_obs)}
    for w in WEIGHTS:
        effects[f"blend_{int(round(100 * w))}"] = blend(t_lfc, t_obs, n_lfc, n_obs, w)
    log(f"{held}: {len(labels)} targets; network observed on {float((t_obs & n_obs).sum() / max(t_obs.sum(), 1)):.3f} "
        f"of the transfer's observed cells")
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
    bench.finish(dict(stage=f"rete_cellulare blend check {held}", targets=labels, target_keys=tkeys,
                      weights=list(WEIGHTS), arm=a.arm, real=str(a.real), real_sha256=sha256(a.real),
                      seed=a.seed, gen_seed=a.gen_seed, run=str(a.run), prespecified="MISCELE.md"))
    write_json(a.out / "run.json", dict(written_utc=now_utc(), git=git_state(), seconds=timer(),
                                        arguments={k: str(v) for k, v in vars(a).items()}))
    log("done")


if __name__ == "__main__":
    main()
