"""Stage 72: what each generator looks like to the scorer when nothing is predicted.

For each official context the control cells are split in two seeded halves.
Half 1 is the only thing a generator may learn from; half 2 plays the scorer's
real control pool. Each arm then emits `--n-pseudo` pseudo-perturbations of
`--cells` cells with NO predicted effect, and the scorer's own DE call
(Wilcoxon, per-target BH, 5-CPM reference gate) is run against half 2 -- by
default through `vcc2026.de_tools.fast_scorer_de`, which returns the scanpy
path's table exactly (D-037); `--de scanpy` runs the scorer's own code.

Arms:

* ``real``  -- disjoint real cells from half 1: what "no effect" looks like
  when the cells are real. The target for every generator.
* ``g0``    -- trial-01's generator: Poisson around the pooled profile.
* ``gmm`` / ``kde`` -- `vcc2026.generator.ControlModel` with the two state
  samplers.

Read per arm: significant genes per pseudo-target (and their sign mix), the
log2FC bias of per-cell CPM means, detected genes per cell, and the
pseudobulk distance to half 2 in the scorer's bulk_lognorm space.

This is a null calibration. It says nothing about predictive skill, and a
generator that calls nothing here is not automatically better: the direction
fidelity metric scores silence as zero (`cell_eval2/metrics/direction.py`,
`direction_fidelity_yield_raw = k / max(n_pred, N_conf)`).

    python scripts/72_generator_null.py --out <dir> --contexts A B C
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
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import log  # noqa: E402
from vcc2026.de_tools import ReferencePool, fast_scorer_de, scorer_de, summarize_de  # noqa: E402
from vcc2026.generator import ControlModel, bulk_lognorm, per_cell_cpm_mean  # noqa: E402
from vcc2026.inference import read_csr_rows  # noqa: E402
from vcc2026.sampling import resample_library_sizes, sample_counts  # noqa: E402


def load_controls(path: Path, max_cells: int | None, rng: np.random.Generator):
    with h5py.File(path, "r") as f:
        shape = tuple(int(s) for s in f["X"].attrs["shape"])
        idx = f["var/_index"]
        genes = idx["values"][:] if isinstance(idx, h5py.Group) else idx[:]
        genes = np.array([g.decode() if isinstance(g, bytes) else str(g) for g in genes], dtype=object)
        if max_cells is None or max_cells >= shape[0]:
            x = sp.csr_matrix((f["X/data"][:], f["X/indices"][:], f["X/indptr"][:]), shape=shape)
            return x, genes
    rows = np.sort(rng.choice(shape[0], size=max_cells, replace=False))
    return read_csr_rows(path, rows, shape[1]), genes


def arm_cells(name, h1, n_pseudo, n_cells, rng, models):
    total = n_pseudo * n_cells
    if name == "real":
        pick = rng.choice(h1.shape[0], size=total, replace=total > h1.shape[0])
        return h1[pick]
    if name == "g0":
        profile = np.asarray(h1.sum(axis=0), dtype=np.float64).ravel()
        libs = np.asarray(h1.sum(axis=1)).ravel()
        blocks = []
        for _ in range(n_pseudo):
            lib = resample_library_sizes(libs, n_cells, rng)
            blocks.append(sample_counts(profile, lib, rng, max_stored_per_cell=h1.shape[1],
                                        max_counts_per_cell=1_000_000))
        return sp.vstack(blocks).tocsr()
    model = models[name]
    return sp.vstack([model.sample(n_cells, rng) for _ in range(n_pseudo)]).tocsr()


def lfc_bias(pred: sp.csr_matrix, ref_cpm: np.ndarray, gate: np.ndarray) -> dict:
    cpm = per_cell_cpm_mean(pred)
    lfc = np.log2((cpm[gate] + 1e-9) / (ref_cpm[gate] + 1e-9))
    return {
        "median": float(np.median(lfc)),
        "mad": float(np.median(np.abs(lfc - np.median(lfc)))),
        "frac_pos": float(np.mean(lfc > 0)),
        "q05_q95": [float(np.quantile(lfc, 0.05)), float(np.quantile(lfc, 0.95))],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--controls-dir", type=Path, default=None)
    p.add_argument("--contexts", nargs="+", default=["A", "B", "C"])
    p.add_argument("--arms", nargs="+", default=["real", "g0", "gmm", "kde"])
    p.add_argument("--n-pseudo", type=int, default=20)
    p.add_argument("--cells", type=int, default=400)
    p.add_argument("--max-cells", type=int, default=None, help="subsample controls (local smoke tests)")
    p.add_argument("--knn", type=int, default=30)
    p.add_argument("--n-pcs", type=int, default=20)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--backend", default="scanpy")
    p.add_argument("--de", choices=["fast", "scanpy"], default="fast",
                   help="fast = vcc2026.de_tools.fast_scorer_de, identical to the scanpy path (D-037); "
                        "the scanpy path took 24 min per arm on Colab and ran the runtime out of memory")
    args = p.parse_args()

    if args.out.exists() and (args.out / "summary.json").exists():
        raise SystemExit(f"{args.out} already holds a summary; choose a new --out")
    args.out.mkdir(parents=True, exist_ok=True)
    cdir = args.controls_dir
    if cdir is None:
        from vcc2026 import config
        cdir = config.paths().raw / "controls"

    summary = {"stage": "72_generator_null", "started_utc": datetime.now(timezone.utc).isoformat(),
               "args": {k: str(v) for k, v in vars(args).items()}, "contexts": {}}
    for ctx in args.contexts:
        rng = np.random.default_rng([args.seed, ord(ctx)])
        t0 = time.time()
        x, genes = load_controls(cdir / f"context_{ctx}.h5ad", args.max_cells, rng)
        perm = rng.permutation(x.shape[0])
        half = x.shape[0] // 2
        h1, h2 = x[np.sort(perm[:half])], x[np.sort(perm[half:])]
        del x
        log(f"{ctx}: controls {h1.shape[0]} + {h2.shape[0]} cells, {h1.shape[1]} genes")
        pool = ReferencePool(h2, genes) if args.de == "fast" else None
        ref_cpm = per_cell_cpm_mean(h2)
        gate = ref_cpm >= 5.0
        ref_pb = bulk_lognorm(h2)
        models = {}
        for name in ("gmm", "kde"):
            if name in args.arms:
                models[name] = ControlModel(state=name, knn=args.knn, n_pcs=args.n_pcs,
                                            seed=args.seed).fit(h1, log=log)
        ctx_out = {"n_h1": int(h1.shape[0]), "n_h2": int(h2.shape[0]), "n_genes_cpm5": int(gate.sum()),
                   "real_nnz_per_cell_h2": float(np.diff(h2.indptr).mean()), "arms": {}}
        for name, m in models.items():
            ctx_out[f"model_{name}"] = m.diagnostics | {"pca_var": m._pca_var}
        for arm in args.arms:
            ta = time.time()
            cells = arm_cells(arm, h1, args.n_pseudo, args.cells, rng, models)
            labels = np.repeat([f"pseudo_{i:02d}" for i in range(args.n_pseudo)], args.cells)
            de = (fast_scorer_de(cells, labels, pool) if pool is not None
                  else scorer_de(cells, labels, h2, genes, backend=args.backend))
            per_t = summarize_de(de)
            per_t.to_csv(args.out / f"de_summary_{ctx}_{arm}.csv")
            pb = []
            for i in range(args.n_pseudo):
                blk = cells[i * args.cells:(i + 1) * args.cells]
                d = bulk_lognorm(blk) - ref_pb
                pb.append(float(np.mean(d**2)))
            ctx_out["arms"][arm] = {
                "n_sig_mean": float(per_t["n_sig"].mean()),
                "n_sig_median": float(per_t["n_sig"].median()),
                "n_sig_max": float(per_t["n_sig"].max()),
                "frac_up_of_sig": float(per_t["n_sig_up"].sum() / max(per_t["n_sig"].sum(), 1)),
                "n_tested_median": float(per_t["n_tested"].median()),
                "nnz_per_cell": float(np.diff(cells.indptr).mean()),
                "lib_median": float(np.median(np.asarray(cells.sum(axis=1)).ravel())),
                "lfc_bias_cpm5": lfc_bias(cells, ref_cpm, gate),
                "pseudobulk_mse_mean": float(np.mean(pb)),
                "seconds": time.time() - ta,
            }
            log(f"{ctx}/{arm}: sig/target mean {ctx_out['arms'][arm]['n_sig_mean']:.1f} "
                f"(up {ctx_out['arms'][arm]['frac_up_of_sig']:.2f}), nnz/cell "
                f"{ctx_out['arms'][arm]['nnz_per_cell']:.0f} vs real {ctx_out['real_nnz_per_cell_h2']:.0f}, "
                f"pb mse {ctx_out['arms'][arm]['pseudobulk_mse_mean']:.3e}, "
                f"lfc bias med {ctx_out['arms'][arm]['lfc_bias_cpm5']['median']:+.4f}")
        ctx_out["seconds"] = time.time() - t0
        summary["contexts"][ctx] = ctx_out
        (args.out / f"context_{ctx}.json").write_text(json.dumps(ctx_out, indent=2))
    summary["finished_utc"] = datetime.now(timezone.utc).isoformat()
    summary["backend"] = args.backend if args.de == "scanpy" else "fast_scorer_de (scanpy-identical, D-037)"
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    log("done")


if __name__ == "__main__":
    main()
