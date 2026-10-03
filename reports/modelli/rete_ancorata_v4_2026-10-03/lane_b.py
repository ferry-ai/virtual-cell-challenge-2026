"""Lane B of version 4 (PROTOCOLLO.md §6): the six official members, local scale, on the real cells and targets of the r3
lane B (out_gen_<line>_r3*/real_cells.npz and targets.json), for the arms of version 4.

A copy of version 3's lane B (reports/modelli/rete_ancorata_2026-10-03/lane_b.py) with the transfer references of
version 4: transfer_all_J (the definition of version 4's anchor), transfer_cells_J and transfer_prod_J, all with
regime-J table means (anchors.py's rule, keys left out checked against the anchors' manifest when given).

Arms, on the chosen targets and on the genes the held-out key measures:
- effects -> the same generator (trial-01): the three transfer references and each network arm's predicted mean shift
  (ancorata, ancorata_mean, ancora_sola);
- the networks' own cells (generate_cells.py, with the anchors), for the trained arms.
Not a VCC score.

    py.cmd lane_b.py --held-group H1 --real <r3 gen>/real_cells.npz --targets <r3 gen>/targets.json --cells-dir <v4 gen>
        --run <v4 training>/train --cube <cube_r2> --protocol <bench PROTOCOLLO.json> --target-keys target_keys.json
        --splits <prepass splits.json> [--anchors-manifest <anchors_<line>_all/manifest.json>] --out <new folder>
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
import anchors as A  # noqa: E402
import splits as SPLITS  # noqa: E402
from arms import AMPLITUDE_T25, Cube  # noqa: E402
from bench_effects import REFERENCES, hidden_from_splits  # noqa: E402
from common import Timer, git_state, log, now_utc, sha256, write_json  # noqa: E402
from fitting import transfer_for  # noqa: E402

from vcc2026.bench import Bench  # noqa: E402
from vcc2026.config import challenge  # noqa: E402
from vcc2026.inference import trial01_cells  # noqa: E402

F32 = np.float32
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
    p.add_argument("--target-keys", type=Path, required=True)
    p.add_argument("--splits", type=Path, required=True)
    p.add_argument("--anchors-manifest", type=Path)
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
    import arms as ARMS
    cube = Cube(a.cube, min_cells=P["min_cells"])
    hidden, fold, n_folds = hidden_from_splits(a.splits)
    keys_of_symbol = json.loads(a.target_keys.read_text(encoding="utf-8"))
    forbidden = A.hidden_keys(cube, {"hidden": sorted(hidden)}, keys_of_symbol, fold, n_folds, SPLITS)
    if a.anchors_manifest:
        kept_out = json.loads(a.anchors_manifest.read_text(encoding="utf-8"))["commons"]["keys_kept_out"]
        if kept_out != len(forbidden):
            raise SystemExit(f"{len(forbidden)} keys left out of the means here, {kept_out} in the anchors")
    commons, _ = A.j_table_means(cube, held, forbidden)
    cpos = pd.Index(cube.genes).get_indexer(genes)
    have = cpos >= 0
    effects = {}
    for name, rule in REFERENCES:
        cb = A.source_cube(ARMS, a.cube, P["min_cells"], rule)
        s, _ = transfer_for(cb, tkeys, [h for h in cb.groups if h != held], commons)
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
    bench.finish(dict(stage=f"rete_ancorata v4 lane B {held}", targets=labels, target_keys=tkeys, genes=int(genes.size),
                      real=str(a.real), real_sha256=sha256(a.real), seed=a.seed, gen_seed=a.gen_seed,
                      commons={"regime": "J", "keys_kept_out": len(forbidden)},
                      generator="trial-01 for effects; the network's NB for its cells", run=str(a.run)))
    write_json(a.out / "run.json", dict(written_utc=now_utc(), git=git_state(), seconds=timer(),
                                        arguments={k: str(v) for k, v in vars(a).items()}))
    log("done")


if __name__ == "__main__":
    main()
