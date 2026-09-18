"""Stage 80: how many significant genes a predictor configuration makes, in an official context.

Direction fidelity is ``k / max(n_pred, N_conf)``: a prediction that calls too few genes
is scored as if it knew nothing (D-035). The number of calls is not a parameter of the
predictor, it is a consequence of its amplitudes, of which genes it moves, and of the
generator. This stage measures it where it matters -- on an official context's own
control cells -- without any perturbed cell and without a score:

* a `ControlModel` is fitted on ``--fit-cells`` controls of the context;
* a DISJOINT set of ``--ref-cells`` controls plays the scorer's control pool;
* for each configuration, ``--cells`` cells are generated for each of ``--n-targets``
  panel targets covered by the K562 source, and the scorer's DE call
  (`fast_scorer_de`, identical to the CPU path, D-037) counts the significant genes;
* a real-cell arm (disjoint controls, no effect) gives the floor.

The docstrings of cell_eval2 0.16.0 put 12-30% of val targets below 10 significant
genes and some above 500; this stage says where each configuration lands, nothing about
whether its calls are right.

    python scripts/80_call_budget.py --out reports/call_budget_2026-09-17 --context A \
        --configs "t0.5+m1+c1" "t1+m1+c1" "t2+m1+c1"
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
from vcc2026.de_tools import ReferencePool, fast_scorer_de  # noqa: E402
from vcc2026.generator import ControlModel  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.inference import read_csr_rows  # noqa: E402
from vcc2026.predictor_sc import (  # noqa: E402
    CisModel,
    assemble_log_fc,
    effects_from_bulk,
    effects_from_group_stats,
    load_coordinates,
)
from vcc2026.sc_stream import read_frame  # noqa: E402

KEYS = {"t": "a_transfer", "r": "a_raw_transfer", "m": "a_cis_measured", "c": "a_cis", "s": "a_shared"}


def parse_config(text: str) -> dict:
    out = {v: 0.0 for v in KEYS.values()}
    for term in text.split("+"):
        if term == "null":
            continue
        out[KEYS[term[0]]] = float(term[1:])
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--context", default="A")
    p.add_argument("--configs", nargs="+", default=["null", "m1+c1", "t0.5+m1+c1", "t1+m1+c1", "t2+m1+c1",
                                                    "r0.25+m1+c1", "r0.5+m1+c1"])
    p.add_argument("--fit-cells", type=int, default=3000)
    p.add_argument("--ref-cells", type=int, default=1500)
    p.add_argument("--cells", type=int, default=400)
    p.add_argument("--n-targets", type=int, default=20)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--k562", type=Path, default=None, help="stage-71 output; default: the local pseudobulk")
    p.add_argument("--cis-pairs", type=Path, default=Path("reports/cis_2026-09-17/k562_neighbour_pairs.csv"))
    p.add_argument("--contexts", nargs="+", default=None, help="several contexts in one run")
    p.add_argument("--max-calls", type=int, default=None,
                   help="keep only the K largest |lfc| genes per target, the rest exactly 0")
    args = p.parse_args()
    if (args.out / "call_budget.json").exists():
        raise SystemExit(f"{args.out} already holds a report")
    args.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    paths = config.paths()
    axis = np.asarray(official_axis().symbols)
    panel = pd.read_csv(paths.raw / "controls" / "pert_counts.csv")["target_gene"].astype(str).tolist()

    if args.k562 is not None:
        groups = pd.read_csv(args.k562 / "groups.csv")
        stats = np.load(args.k562 / "group_stats.npz")
        names = pd.read_csv(args.k562 / "var.csv", index_col=0)["gene_name"].astype(str).to_numpy()
        src = effects_from_group_stats(stats, groups, names, targets=panel)
        bulk = args.k562
    else:
        bulk = paths.external / "K562_gwps_raw_bulk_01.h5ad"
        with h5py.File(bulk, "r") as f:
            labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
            is_ntc = np.array(["non-targeting" in lab for lab in labels])
            symbols = np.array(["non-targeting" if nt else lab.split("_")[1] for lab, nt in zip(labels, is_ntc)])
            rows = np.flatnonzero(is_ntc | np.isin(symbols, panel))
            means = f["X"][rows]
            n_cells = f["obs/num_cells_filtered"][:][rows]
            names = read_frame(f["var"])["gene_name"].astype(str).to_numpy()
        src = effects_from_bulk(means, n_cells, symbols[rows], is_ntc[rows], names, targets=panel)
        del means
    coords = load_coordinates(paths.external / "annotation" / "gene_coordinates_gencode_v50.tsv")
    pairs = pd.read_csv(args.cis_pairs)
    cis = CisModel.from_pairs(pairs[~pairs["target"].isin(panel)])
    targets = sorted(rng.choice(src.targets, size=min(args.n_targets, len(src.targets)), replace=False).tolist())
    pos = pd.Index(axis).get_indexer(src.genes)
    shared = np.zeros(axis.size)
    shared[pos[pos >= 0]] = src.shrunk.mean(axis=0)[pos >= 0]

    results_by_context = {}
    for ctx in (args.contexts or [args.context]):
        results = {}
        ctrl_path = paths.raw / "controls" / f"context_{ctx}.h5ad"
        with h5py.File(ctrl_path, "r") as f:
            n_ctrl = int(f["X"].attrs["shape"][0])
        perm = rng.permutation(n_ctrl)
        fit_rows = np.sort(perm[: args.fit_cells])
        ref_rows = np.sort(perm[args.fit_cells: args.fit_cells + args.ref_cells])
        real_rows = perm[args.fit_cells + args.ref_cells:]
        fit = read_csr_rows(ctrl_path, fit_rows, axis.size)
        model = ControlModel(state="kde", seed=args.seed, n_draw=1500).fit(fit, log=log)
        del fit
        pool = ReferencePool(read_csr_rows(ctrl_path, ref_rows, axis.size), axis)
        log(f"context {ctx}: model on {args.fit_cells}, reference pool {args.ref_cells}, "
            f"{pool.kept.size} genes pass the 5-CPM gate; {len(targets)} targets")

        # floor: real cells, no effect
        blocks = [read_csr_rows(ctrl_path, np.sort(rng.choice(real_rows, args.cells, replace=False)), axis.size)
                  for _ in range(min(5, len(targets)))]
        de = fast_scorer_de(sp.vstack(blocks).tocsr(), np.repeat([f"real{i}" for i in range(len(blocks))], args.cells), pool)
        sig = de.filter(de["p_adj"] < 0.05)
        results["real_cells"] = {"sig_per_target_mean": sig.height / len(blocks)}
        log(f"real cells: {results['real_cells']['sig_per_target_mean']:.1f} sig/target")

        for text in args.configs:
            cfg = parse_config(text)
            t0 = time.time()
            blocks, labs, moved = [], [], []
            for t in targets:
                lfc = np.zeros(axis.size)
                if any(cfg.values()):
                    raw = cfg["a_raw_transfer"] > 0
                    lfc = assemble_log_fc(t, axis, src=src, a_transfer=cfg["a_raw_transfer"] if raw else cfg["a_transfer"],
                                          use_raw=raw, cis=cis, coords=coords, a_cis=cfg["a_cis"],
                                          a_cis_measured=cfg["a_cis_measured"], shared=shared, a_shared=cfg["a_shared"])
                j = np.flatnonzero(axis == t)
                if args.max_calls is not None and args.max_calls < lfc.size:
                    order = np.argpartition(-np.abs(lfc), args.max_calls)[:args.max_calls]
                    capped = np.zeros_like(lfc)
                    capped[order] = lfc[order]
                    lfc = capped
                if j.size:
                    lfc[j] = np.log(0.15)
                moved.append(int((np.abs(lfc) > np.log(1.1)).sum()))
                blocks.append(model.sample(args.cells, rng, fold_change=np.exp(lfc)))
                labs.append(np.full(args.cells, t))
            de = fast_scorer_de(sp.vstack(blocks).tocsr(), np.concatenate(labs), pool)
            frame = pd.DataFrame({c: de[c].to_numpy() for c in ("target", "feature", "log2_fold_change", "p_adj")})
            frame = frame[frame["feature"] != frame["target"]]
            sig = frame[frame["p_adj"] < 0.05]
            per_t = sig.groupby("target").size().reindex(targets, fill_value=0)
            results[text] = {
                "amplitudes": cfg,
                "sig_per_target_mean": float(per_t.mean()),
                "sig_per_target_median": float(per_t.median()),
                "sig_per_target_q10_q90": [float(per_t.quantile(0.1)), float(per_t.quantile(0.9))],
                "targets_below_10_calls": int((per_t < 10).sum()),
                "frac_up": float((sig["log2_fold_change"] > 0).mean()) if len(sig) else None,
                "genes_moved_10pct_median": float(np.median(moved)),
                "seconds": time.time() - t0,
            }
            log(f"{text}: sig/target mean {per_t.mean():.1f} median {per_t.median():.0f} "
                f"(<10 calls: {(per_t < 10).sum()}/{len(targets)}), moved>10% median {np.median(moved):.0f}")

        results_by_context[ctx] = results
    payload = {
        "stage": "80_call_budget", "written_utc": datetime.now(timezone.utc).isoformat(),
        "contexts": list(results_by_context), "targets": targets, "source": str(bulk),
        "source_note": ("stage-71 single-cell accumulators" if args.k562 is not None else
                        "K562 pseudobulk means with quasi-Poisson SE (effects_from_bulk)"),
        "args": {k: str(v) for k, v in vars(args).items()},
        "results": results_by_context,
        "claim_type": "count of significant calls a configuration produces; says nothing about their sign",
    }
    (args.out / "call_budget.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
