"""Stage 76: a full submission-shaped prediction from single-cell evidence.

For each official context (A, B, C) this stage fits `vcc2026.generator.ControlModel`
on that context's 18,400 control cells -- the only data the competition gives for
it -- and, for each of the 300 panel targets, samples 400 new cells whose rates are
multiplied by a predicted fold change (`vcc2026.predictor_sc.assemble_log_fc`):

* ``--a-transfer``: the target's own K562 genome-wide effect (stage-71
  accumulators, empirical-Bayes shrunk, matched by symbol);
* ``--a-cis``: the TSS-distance prior fitted on the K562 targets outside the
  panel, applied on the official axis (``--cis-mode fill`` uses it only where the
  transfer term has no measurement);
* ``--a-cis-measured``: genes within 5 kb of the target that K562 measured get this
  multiple of their own K562 effect (neighbour effects transfer: r = 0.57 and 98% sign
  agreement K562 -> HepG2 within 1 kb, measured 2026-09-17);
* ``--a-shared``: the mean K562 effect over the covered panel targets;
* ``--effects CTX=PATH`` with ``--a-effects``: a trained predictor's ln fold changes for the
  panel in that context (stage 92's `pred_C_official_<CTX>_<model>.npz`), added as they are;
* ``--a-common`` with ``--common-bulk``: the response another source's knockdowns share
  (`vcc2026.predictor_sc.common_from_bulk`, panel targets excluded), the same for all;
* the target gene itself gets ``--kd-default`` when no transfer term covers it.
  The scorer excludes that gene everywhere; it only keeps the composition honest.

Cells go straight to `SubmissionWriter` one 400-cell block at a time. The
amplitudes are inputs, chosen from the benches (stages 73 and 75); this stage
decides nothing on its own. It writes diagnostics beside the matrix and never
overwrites.

    python scripts/76_generate_sc_prediction.py --run-id t02 --k562 <stage-71 out> \
        --coords <gene_coordinates tsv> --out <dir> --a-transfer 0.5 --a-cis 1.0
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.bench import log  # noqa: E402
from vcc2026.generator import ControlModel  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.predictor_sc import (  # noqa: E402
    CisModel,
    assemble_log_fc,
    common_from_bulk,
    effects_from_bulk,
    effects_from_group_stats,
    load_coordinates,
)
from vcc2026.sc_stream import read_frame  # noqa: E402
from vcc2026.submission import SubmissionWriter  # noqa: E402


def load_context(path: Path, axis: np.ndarray, rng: np.random.Generator, max_cells: int | None) -> sp.csr_matrix:
    from vcc2026.inference import read_csr_rows

    with h5py.File(path, "r") as f:
        shape = tuple(int(s) for s in f["X"].attrs["shape"])
        idx = f["var/_index"]
        genes = idx["values"][:] if isinstance(idx, h5py.Group) else idx[:]
        genes = np.array([g.decode() if isinstance(g, bytes) else str(g) for g in genes])
        if not np.array_equal(genes, axis):
            raise SystemExit(f"{path}: gene order differs from gene_names.csv")
        if max_cells is None or max_cells >= shape[0]:
            return sp.csr_matrix((f["X/data"][:], f["X/indices"][:], f["X/indptr"][:]), shape=shape)
    rows = np.sort(rng.choice(shape[0], size=max_cells, replace=False))
    return read_csr_rows(path, rows, shape[1])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run-id", required=True)
    src_arg = p.add_mutually_exclusive_group(required=True)
    src_arg.add_argument("--k562", type=Path, help="stage-71 output (single-cell accumulators)")
    src_arg.add_argument("--k562-bulk", type=Path, help="fallback: K562_gwps_raw_bulk_01.h5ad (quasi-Poisson SE)")
    p.add_argument("--coords", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--controls-dir", type=Path, default=None)
    p.add_argument("--contexts", nargs="+", default=["A", "B", "C"])
    p.add_argument("--a-transfer", type=float, default=0.5)
    p.add_argument("--a-cis", type=float, default=1.0)
    p.add_argument("--cis-mode", choices=["fill", "add"], default="fill")
    p.add_argument("--a-cis-measured", type=float, default=0.0)
    p.add_argument("--use-raw", action="store_true", help="transfer the unshrunk source effect (bench 'rawtransfer')")
    p.add_argument("--a-shared", type=float, default=0.0)
    p.add_argument("--effects", action="append", default=None, metavar="CTX=PATH",
                   help="per-context predicted effects (npz: targets, genes, lfc in ln units), e.g. A=pred_A.npz")
    p.add_argument("--a-effects", type=float, default=1.0)
    p.add_argument("--a-common", type=float, default=0.0)
    p.add_argument("--common-bulk", type=Path, default=None)
    p.add_argument("--kd-default", type=float, default=float(np.log(0.15)))
    p.add_argument("--state", choices=["gmm", "kde"], default="kde")
    p.add_argument("--knn", type=int, default=30)
    p.add_argument("--cells", type=int, default=None)
    p.add_argument("--n-targets", type=int, default=None, help="pilot only")
    p.add_argument("--max-control-cells", type=int, default=None,
                   help="fit each context's model on this many controls (low-memory runs)")
    p.add_argument("--cis-pairs", type=Path, default=None,
                   help="stage-77 k562_distance pairs CSV (dist, log2fc): skips fitting the cis model on "
                        "every source target, which the laptop cannot hold")
    p.add_argument("--n-draw", type=int, default=4000)
    p.add_argument("--max-calls", type=int, default=None,
                   help="keep only the K genes with the largest |log fold change| per target and set the "
                        "rest to EXACTLY zero. The scorer's direction fidelity is k / max(n_pred, N_conf) "
                        "with n_pred = the genes the prediction itself calls significant, so a prediction "
                        "that moves thousands of genes cannot score above its own precision. Measured on "
                        "the 2026-09-17 submission: n_pred in the hundreds gave a scaled fidelity of -0.870")
    p.add_argument("--seed", type=int, default=2026)
    args = p.parse_args()

    out = args.out
    pred_path = out / "prediction.h5ad"
    if pred_path.exists() or (out / "generation.json").exists():
        raise SystemExit(f"{out} already holds a prediction; choose a new --out")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ch = config.challenge()
    cells = args.cells or ch.cells_per_pert
    axis = np.asarray(official_axis().symbols)
    cdir = args.controls_dir or config.paths().raw / "controls"
    targets = pd.read_csv(cdir / "pert_counts.csv")["target_gene"].astype(str).tolist()
    if args.n_targets:
        targets = targets[: args.n_targets]
    pilot = bool(args.n_targets) or bool(args.max_control_cells) or cells != ch.cells_per_pert or set(args.contexts) != set(ch.contexts_validation)

    coords = load_coordinates(args.coords)
    panel_set = set(pd.read_csv(cdir / "pert_counts.csv")["target_gene"].astype(str))
    if args.k562 is not None:
        groups = pd.read_csv(args.k562 / "groups.csv")
        stats = np.load(args.k562 / "group_stats.npz")
        k562_names = pd.read_csv(args.k562 / "var.csv", index_col=0)["gene_name"].astype(str).to_numpy()
        src = effects_from_group_stats(stats, groups, k562_names, targets=targets)
        others = sorted((set(groups.loc[~groups.is_ntc, "gene"].astype(str)) - panel_set) & set(coords.index))
        cis_src = None if args.cis_pairs else effects_from_group_stats(stats, groups, k562_names, targets=others)
    else:
        with h5py.File(args.k562_bulk, "r") as f:
            labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
            is_ntc = np.array(["non-targeting" in lab for lab in labels])
            symbols = np.array(["non-targeting" if nt else lab.split("_")[1] for lab, nt in zip(labels, is_ntc)])
            # With --cis-pairs only the panel's rows and the controls are needed: the whole
            # 11,258 x 8,248 matrix in float64 does not fit next to a context on the laptop.
            rows = np.flatnonzero(is_ntc | np.isin(symbols, targets)) if args.cis_pairs else np.arange(labels.size)
            means = f["X"][rows]
            n_cells = f["obs/num_cells_filtered"][:][rows]
            k562_names = read_frame(f["var"])["gene_name"].astype(str).to_numpy()
        labels, is_ntc, symbols = labels[rows], is_ntc[rows], symbols[rows]
        src = effects_from_bulk(means, n_cells, symbols, is_ntc, k562_names, targets=targets)
        others = sorted((set(symbols[~is_ntc]) - panel_set) & set(coords.index))
        cis_src = None if args.cis_pairs else effects_from_bulk(means, n_cells, symbols, is_ntc, k562_names,
                                                                  targets=others)
        del means
    covered = set(src.targets)
    if args.cis_pairs:
        pairs = pd.read_csv(args.cis_pairs)
        pairs = pairs[~pairs["target"].astype(str).isin(panel_set)]
        cis_model = CisModel.from_pairs(pairs, value="log2fc", log_base=2.0)
    else:
        cis_model = CisModel().fit(cis_src, coords)
    del cis_src
    log(f"transfer covers {len(covered)}/{len(targets)} targets; cis bins "
        + " ".join(f"{e}:{v:+.3f}" for e, v in zip(cis_model.edges, cis_model.by_bin)))
    pos = pd.Index(axis).get_indexer(src.genes)
    shared_axis = np.zeros(axis.size)
    shared_axis[pos[pos >= 0]] = src.shrunk.mean(axis=0)[pos >= 0]
    axis_pos = {g: i for i, g in enumerate(axis)}
    ext = {}
    for spec in args.effects or []:
        ctx, _, path = spec.partition("=")
        z = np.load(path)
        gpos = pd.Index(z["genes"].astype(str)).get_indexer(axis)
        rows = {}
        for i, t in enumerate(z["targets"].astype(str)):
            v = np.zeros(axis.size)
            v[gpos >= 0] = z["lfc"][i, gpos[gpos >= 0]]
            rows[t] = v
        missing = [t for t in targets if t not in rows]
        if missing:
            raise SystemExit(f"--effects {ctx}: no prediction for {len(missing)} panel targets, e.g. {missing[:3]}")
        ext[ctx] = rows
        log(f"effects for context {ctx} from {path}: {int((gpos >= 0).sum())} genes on the official axis")
    if ext and set(ext) != set(args.contexts):
        raise SystemExit(f"--effects covers {sorted(ext)} but --contexts is {args.contexts}")
    common_axis, common_info = np.zeros(axis.size), None
    if args.a_common:
        if args.common_bulk is None:
            raise SystemExit("--a-common needs --common-bulk")
        common_axis, common_info = common_from_bulk(args.common_bulk, axis, exclude=panel_set)
        log(f"common term x{args.a_common} from {common_info}")

    diag = {"per_context": {}, "targets": {}}
    with SubmissionWriter(pred_path, axis, pert_col=ch.pert_col, context_col=ch.context_col) as writer:
        for ctx in args.contexts:
            tc = time.time()
            rng = np.random.default_rng([args.seed, ord(ctx)])
            ctrl = load_context(cdir / f"context_{ctx}.h5ad", axis, rng, args.max_control_cells)
            model = ControlModel(state=args.state, knn=args.knn, seed=args.seed, n_draw=args.n_draw).fit(ctrl, log=log)
            ctrl_nnz = float(np.diff(ctrl.indptr).mean())
            del ctrl
            nnz, n_cis, n_up, n_down, n_moved = [], 0, [], [], []
            for ti, t in enumerate(targets):
                lfc = assemble_log_fc(t, axis, src=src, a_transfer=args.a_transfer, use_raw=args.use_raw,
                                      cis=cis_model, coords=coords,
                                      a_cis=args.a_cis, cis_mode=args.cis_mode,
                                      a_cis_measured=args.a_cis_measured,
                                      shared=shared_axis, a_shared=args.a_shared)
                if args.a_common:
                    lfc = np.clip(lfc + args.a_common * common_axis, -3.0, 3.0)
                if ext:
                    lfc = np.clip(lfc + args.a_effects * ext[ctx][t], -3.0, 3.0)
                j = axis_pos.get(t)
                if j is not None and (t not in covered or args.a_transfer == 0):
                    lfc[j] = args.kd_default
                if args.max_calls is not None and args.max_calls < lfc.size:
                    order = np.argpartition(-np.abs(lfc), args.max_calls)[:args.max_calls]
                    capped = np.zeros_like(lfc)
                    capped[order] = lfc[order]
                    if j is not None:
                        capped[j] = lfc[j]      # the knockdown itself is never dropped
                    lfc = capped
                n_moved.append(int((lfc != 0).sum()))
                n_cis += int(np.any(cis_model.vector(t, axis, coords) != 0))
                n_up.append(int((lfc > np.log(1.1)).sum()))
                n_down.append(int((lfc < -np.log(1.1)).sum()))
                block = model.sample(cells, rng, fold_change=np.exp(lfc),
                                     max_stored_per_cell=ch.max_stored_per_cell,
                                     max_counts_per_cell=ch.max_counts_per_cell)
                writer.add(block, target_gene=t, context=ctx)
                nnz.append(block.nnz / block.shape[0])
                if ti % 50 == 0:
                    log(f"  {ctx} {ti + 1}/{len(targets)} nnz/cell {nnz[-1]:.0f} ({time.time() - tc:.0f}s)")
            diag["per_context"][ctx] = {
                "seconds": time.time() - tc, "nnz_per_cell_mean": float(np.mean(nnz)),
                "control_nnz_per_cell": ctrl_nnz, "targets_with_cis_neighbour": n_cis,
                "genes_up_10pct_median": float(np.median(n_up)), "genes_down_10pct_median": float(np.median(n_down)),
                "genes_nonzero_median": float(np.median(n_moved)), "max_calls": args.max_calls,
                "model": model.diagnostics,
            }
            log(f"{ctx}: done in {time.time() - tc:.0f}s, nnz/cell {np.mean(nnz):.0f} (controls {ctrl_nnz:.0f})")
            del model
    payload = {
        "stage": "76_generate_sc_prediction", "run_id": args.run_id,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "is_pilot": pilot, "prediction": str(pred_path), "bytes": pred_path.stat().st_size,
        "n_cells": writer.n_obs, "nnz": writer.nnz,
        "args": {k: str(v) for k, v in vars(args).items()},
        "transfer_covered": sorted(covered), "transfer_missing": sorted(set(targets) - covered),
        "cis_bins": {"edges": list(cis_model.edges), "ln_effect": cis_model.by_bin.tolist(),
                     "n": cis_model.n_by_bin.tolist()},
        "k562_source": str(args.k562 or args.k562_bulk), "k562_meta": src.meta,
        "common_term": common_info, "effects": args.effects, "a_effects": args.a_effects,
        "diagnostics": diag, "seconds_total": time.time() - t0,
        "not_a_score": "a generated file; its quality is measured only by the benches or by a submission",
    }
    (out / "generation.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    log(f"wrote {pred_path} ({writer.n_obs} cells, {writer.nnz} values) in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
