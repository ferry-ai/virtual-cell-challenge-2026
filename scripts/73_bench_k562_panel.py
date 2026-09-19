"""Stage 73: the six scored metrics on real K562 CRISPRi cells of the panel targets.

K562 genome-wide covers 272 of the panel's 300 targets; stage 71 extracts their
cells. `vcc2026.bench.Bench` turns them into a val-shaped problem (truth = half A,
point 1 = half B, point 0 = the official baseline) and every arm here changes one
thing:

* ``null_g0``   -- trial-01's generator (Poisson around the pooled profile), no effect;
* ``null_new``  -- `ControlModel`, no effect. Direction fidelity reads 0 here by
  construction (no calls), which is the trap a clean generator walks into alone;
* ``oracle_aX`` -- the target's own effect estimated from its half B (EB-shrunk),
  scaled by X. An in-context upper bound for any transfer, not a model;
* ``shared_aX`` -- the mean of those effects over the OTHER targets (leave one out);
* ``cis_aX``    -- the TSS-distance prior, fitted on every NON-panel K562 target
  (stage-71 accumulators), exactly as production fits it;
* ``common_aX`` -- X times the response shared by another source's knockdowns
  (`--common-bulk`, `vcc2026.predictor_sc.common_from_bulk`, bench targets excluded);
* ``NAME_aX``       -- X times the effects of `--effects NAME=PATH` (stage 92's exports);
* ``permcommon_aX`` -- the same values permuted over the measured genes (rng seed+2): the
  volume control of ``common_aX``, with its direction destroyed.

**Not a VCC score**: K562, about 85 cells per side, our anchors. It shows how the
metrics respond to amplitude, sparsity and a shared response.

    python scripts/73_bench_k562_panel.py --k562 <stage-71 out> --out <dir>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import Bench, load_effects, log  # noqa: E402
from vcc2026.generator import ControlModel  # noqa: E402
from vcc2026.predictor_sc import (  # noqa: E402
    CisModel,
    SourceEffects,
    common_from_bulk,
    effects_from_group_stats,
    load_coordinates,
)
from vcc2026.sampling import resample_library_sizes, sample_counts  # noqa: E402
from vcc2026.sc_effects import eb_shrink, fraction_stats, log_effect  # noqa: E402

CONTROL = "non-targeting"


def load_cells(k562: Path):
    import anndata as ad

    groups = pd.read_csv(k562 / "groups.csv")
    keep = set(groups.loc[groups.in_panel | groups.is_ntc, "group"])
    xs, obs, var = [], [], None
    for p in sorted(k562.glob("cells_part*.h5ad")):
        a = ad.read_h5ad(p)
        col = "gene_transcript" if "gene_transcript" in a.obs else "group_label"
        m = a.obs[col].astype(str).isin(keep).to_numpy()
        xs.append(a.X[m])
        obs.append(a.obs.loc[m])
        var = a.var
    obs = pd.concat(obs)
    sym = obs["gene"].astype(str) if "gene" in obs else obs[col].astype(str).str.split("_").str[1]
    return sp.vstack(xs).tocsr(), sym.to_numpy(), var


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--k562", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--coords", type=Path, default=None)
    p.add_argument("--control-cells", type=int, default=12000)
    p.add_argument("--arms", nargs="+", default=[
        "null_g0", "null_new", "oracle_a0.5", "oracle_a1.0", "shared_a1.0", "cis_a1.0",
        "oracle_a1.0+shared_a1.0"])
    p.add_argument("--common-bulk", type=Path, default=None,
                   help="a Replogle *_raw_bulk_01.h5ad whose shared knockdown response common_aX adds")
    p.add_argument("--effects", action="append", default=None, metavar="NAME=PATH",
                   help="predicted effects (npz: targets, genes, lfc) usable as the term NAME_aX")
    p.add_argument("--targets-file", type=Path, default=None,
                   help="one symbol per line: restrict the bench to these targets (a tune/eval split)")
    p.add_argument("--max-targets", type=int, default=None)
    p.add_argument("--min-cells", type=int, default=40)
    p.add_argument("--seed", type=int, default=2026)
    args = p.parse_args()
    if (args.out / "bench.json").exists():
        raise SystemExit(f"{args.out} already holds a bench; choose a new --out")

    x, sym, var = load_cells(args.k562)
    names = var["gene_name"].astype(str).to_numpy() if "gene_name" in var else var.index.astype(str).to_numpy()
    _, first = np.unique(names, return_index=True)
    keep = np.sort(first)
    x, genes = x[:, keep], names[keep]
    rng = np.random.default_rng(args.seed)
    ntc = rng.permutation(np.flatnonzero(sym == CONTROL))
    ctrl_rows, src_ctrl_rows = ntc[: args.control_cells], ntc[args.control_cells:]
    counts = pd.Series(sym[sym != CONTROL]).value_counts()
    targets = sorted(t for t in counts.index if counts[t] >= args.min_cells and t in set(genes))
    if args.targets_file is not None:
        want = {ln.strip() for ln in args.targets_file.read_text(encoding="utf-8").splitlines() if ln.strip()}
        targets = [t for t in targets if t in want]
        log(f"targets restricted to {len(targets)} of the {len(want)} symbols in {args.targets_file}")
    if args.max_targets:
        targets = targets[: args.max_targets]
    bench = Bench(x, {t: np.flatnonzero(sym == t) for t in targets}, ctrl_rows, genes, args.out, seed=args.seed)
    bench.anchors()

    # Half-B effects against an independent control (the leftover NTC cells).
    src_ctrl = fraction_stats(x[src_ctrl_rows])
    usable = src_ctrl.mean > 0
    shrunk, raw, se = [], [], []
    for t in targets:
        st = fraction_stats(x[bench.half_b[t]])
        e, s = log_effect(st, src_ctrl)
        shrunk.append(eb_shrink(e, s, usable & (st.mean > 0))[0])
        raw.append(np.where(usable, e, 0.0))
        se.append(s)
    src = SourceEffects(genes, targets, np.vstack(shrunk), np.vstack(raw), np.vstack(se),
                        np.array([bench.half_b[t].size for t in targets]), src_ctrl.mean)
    shared_sum = src.shrunk.sum(axis=0)
    cis_model = None
    if args.coords:
        coords = load_coordinates(args.coords)
        stats = np.load(args.k562 / "group_stats.npz")
        groups = pd.read_csv(args.k562 / "groups.csv")
        others = sorted(set(groups.loc[~groups.in_panel & ~groups.is_ntc, "gene"].astype(str)) & set(coords.index))
        cis_src = effects_from_group_stats(stats, groups, names, targets=others)
        cis_model = CisModel().fit(cis_src, coords)
        log(f"cis model from {len(cis_src.targets)} non-panel targets: "
            + " ".join(f"{e}:{v:+.3f}(n={n})" for e, v, n in zip(cis_model.edges, cis_model.by_bin, cis_model.n_by_bin)))
        del cis_src
    ext = load_effects(args.effects, genes)
    for name, rows in ext.items():
        missing = [t for t in targets if t not in rows]
        if missing:
            raise SystemExit(f"--effects {name}: no prediction for {len(missing)} bench targets, e.g. {missing[:3]}")
    common_axis, common_info = np.zeros(len(genes)), None
    if any("common_a" in a for a in args.arms):
        if args.common_bulk is None:
            raise SystemExit("a common_aX arm needs --common-bulk")
        common_axis, common_info = common_from_bulk(args.common_bulk, genes, exclude=targets)
        log(f"common term from {common_info}")
    perm_axis = common_axis.copy()
    nz = np.flatnonzero(common_axis)
    perm_axis[nz] = common_axis[nz][np.random.default_rng(args.seed + 2).permutation(nz.size)]
    model = ControlModel(state="kde", seed=args.seed).fit(bench.ctrl, log=log)
    lib_pool = np.asarray(bench.ctrl.sum(axis=1)).ravel()
    profile = np.asarray(bench.ctrl.sum(axis=0), dtype=np.float64).ravel()

    for arm in args.arms:
        if "cis" in arm and cis_model is None:
            log(f"skip {arm}: no --coords")
            continue
        blocks, labels = [], []
        for i, t in enumerate(targets):
            n = bench.n_pred(t)
            if arm == "null_g0":
                blocks.append(sample_counts(profile, resample_library_sizes(lib_pool, n, rng), rng,
                                            max_stored_per_cell=len(genes), max_counts_per_cell=1_000_000))
                labels.append(np.full(n, t))
                continue
            logfc = np.zeros(len(genes))
            for term in arm.split("+"):
                name, _, amp = term.partition("_a")
                a = float(amp) if amp else 0.0
                if name == "oracle":
                    logfc += a * src.shrunk[i]
                elif name == "shared":
                    logfc += a * (shared_sum - src.shrunk[i]) / (len(targets) - 1)
                elif name == "cis":
                    logfc += a * cis_model.vector(t, genes, coords)
                elif name in ext:
                    logfc += a * ext[name][t]
                elif name == "common":
                    logfc += a * common_axis
                elif name == "permcommon":
                    logfc += a * perm_axis
                elif name != "null_new":
                    raise SystemExit(f"unknown term {term!r} in arm {arm!r}")
            fc = None if arm == "null_new" else np.exp(np.clip(logfc, -3, 3))
            blocks.append(model.sample(n, rng, fold_change=fc))
            labels.append(np.full(n, t))
        bench.score(arm, sp.vstack(blocks).tocsr(), np.concatenate(labels))

    bench.finish({"stage": "73_bench_k562_panel", "args": {k: str(v) for k, v in vars(args).items()},
                  "model": model.diagnostics, "targets": targets, "common_term": common_info,
                  "effects": args.effects})
    log("done")


if __name__ == "__main__":
    main()
