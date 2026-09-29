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
* ``NAME_aX``       -- X times the effects of `--effects NAME=PATH` (stage 100's npz files);
* ``permcommon_aX`` -- the same values permuted over the measured genes (rng seed+2): the
  volume control of ``common_aX``, with its direction destroyed.

Terms join with ``+``. An arm without a prefix is sampled by `ControlModel` (ln fold change
clipped at +-3). A prefix picks the generator of the submissions instead (`parse_arm`):

* ``g0:``  -- trial-01, stage 45's path (`vcc2026.inference.trial01_cells`): the arm's ln fold
  change goes to log2, `predicted_profile` applies it with the ``observed`` mask and the
  compositional shift (log2 clipped at 6), then Poisson counts at library sizes resampled from
  the bench's control pool, whose summed counts are the basal profile. The mask of an
  ``--effects`` term is its npz ``observed`` (stage 100 marks an excluded or gated gene as
  observed with 0, so it takes the shift as in production); any other term marks its nonzero
  genes. The storage cap of a submission (about 13,200 values per cell) cannot bind on the
  bench's 8,246 genes. Stage 75's ``g0:`` has no mask and no shift and clips ln at 3, so the
  two differ;
* ``g0d:`` -- the same with a per-gene Gamma-Poisson dispersion (stage 45's ``--gene-dispersion``),
  fitted once with `sampling.fit_gene_dispersion` on the control pool's profile, library sizes
  and zero fractions, seed ``--seed``.

``--gen-seeds S ...`` scores every arm once per seed, as ``<arm>@s<S>``, each drawn from its own
``numpy.random.default_rng(S)``; the split into halves, the control pool and the baseline stay
on ``--seed``, so arms of one seed share their random numbers. Without it one stream, seeded by
``--seed``, draws the NTC split and then every arm in order, as before (b002 reproduces).

**Not a VCC score**: K562, about 85 cells per side, our anchors. It shows how the
metrics respond to amplitude, sparsity and a shared response.

    python scripts/73_bench_k562_panel.py --k562 <stage-71 out> --out <dir>
    python scripts/73_bench_k562_panel.py --k562 <stage-71 out> --out <dir> --control-cells 8000 \
        --seed 2026 --gen-seeds 1 2 3 --effects t22=<t22.npz> --arms g0:t22_a1.0 g0d:t22_a1.0
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
from vcc2026.inference import trial01_cells  # noqa: E402
from vcc2026.predictor_sc import (  # noqa: E402
    CisModel,
    SourceEffects,
    common_from_bulk,
    effects_from_group_stats,
    load_coordinates,
)
from vcc2026.sampling import fit_gene_dispersion, resample_library_sizes, sample_counts  # noqa: E402
from vcc2026.sc_effects import eb_shrink, fraction_stats, log_effect  # noqa: E402

CONTROL = "non-targeting"
GENERATORS = ("g0", "g0d")      # the prefixes of `parse_arm`; no prefix is ControlModel


def parse_arm(arm: str) -> tuple[str | None, list[str]]:
    """(generator, terms) of an arm: ``g0:`` or ``g0d:`` pick trial-01's generator (with a per-gene
    dispersion for ``g0d``), no prefix keeps `ControlModel`. Any other prefix is refused."""
    prefix, sep, body = arm.partition(":")
    if not sep:
        return None, arm.split("+")
    if prefix not in GENERATORS or not body:
        raise SystemExit(f"arm {arm!r}: unknown generator prefix {prefix + ':'!r} "
                         f"(known: {', '.join(g + ':' for g in GENERATORS)}, or none for ControlModel)")
    return prefix, body.split("+")


def arm_key(arm: str, gen_seed: int | None) -> str:
    """The name an arm is scored under: ``<arm>@s<S>`` with ``--gen-seeds``, else the arm itself."""
    return arm if gen_seed is None else f"{arm}@s{gen_seed}"


def control_basal(ctrl: sp.csr_matrix) -> np.ndarray:
    """The control pool's summed counts per gene in float64, the basal profile of the ``g0`` arms
    (stage 45 sums its controls in float64 too, `inference.read_basal_profile`)."""
    return np.bincount(ctrl.indices, weights=ctrl.data, minlength=ctrl.shape[1])


def control_dispersion(ctrl: sp.csr_matrix, basal: np.ndarray, lib_pool: np.ndarray, seed: int) -> np.ndarray:
    """Per-gene Gamma-Poisson dispersion matched to the control pool's zero fractions, as stage 45's
    ``--gene-dispersion`` fits it on a context's controls (`sampling.fit_gene_dispersion`)."""
    detected = np.bincount(ctrl.indices[ctrl.data > 0], minlength=ctrl.shape[1])
    return fit_gene_dispersion(basal, lib_pool, 1.0 - detected / ctrl.shape[0], seed=seed)


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
    p.add_argument("--gen-seeds", type=int, nargs="+", default=None, metavar="S",
                   help="score every arm once per generator seed, as <arm>@s<S>; split, controls and "
                        "baseline stay on --seed")
    args = p.parse_args()
    if (args.out / "bench.json").exists():
        raise SystemExit(f"{args.out} already holds a bench; choose a new --out")
    if args.gen_seeds is not None and len(set(args.gen_seeds)) != len(args.gen_seeds):
        raise SystemExit(f"--gen-seeds must be distinct, got {args.gen_seeds}")
    generators = {arm: parse_arm(arm)[0] for arm in args.arms}      # refuses an unknown prefix up front

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
    ext = load_effects(args.effects, genes, with_observed=True)      # {name: {target: (ln lfc, observed)}}
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
    model = None
    if any(g is None and arm != "null_g0" for arm, g in generators.items()):
        model = ControlModel(state="kde", seed=args.seed).fit(bench.ctrl, log=log)
    lib_pool = np.asarray(bench.ctrl.sum(axis=1)).ravel()
    profile = np.asarray(bench.ctrl.sum(axis=0), dtype=np.float64).ravel()
    basal, phi, generator_info = None, None, {"gen_seeds": args.gen_seeds}
    if any(g is not None for g in generators.values()):
        basal = control_basal(bench.ctrl)
        generator_info["g0"] = {"basal_total_counts": float(basal.sum()), "control_cells": int(bench.ctrl.shape[0]),
                                "path": "vcc2026.inference.trial01_cells (stage 45's sequence)"}
    if "g0d" in generators.values():
        phi = control_dispersion(bench.ctrl, basal, lib_pool, args.seed)
        expressed = basal > 0
        generator_info["g0d"] = {"method": "sampling.fit_gene_dispersion on the control pool, seed --seed",
                                 "genes_overdispersed": int((phi > 0).sum()),
                                 "phi_quantiles_expressed": [float(q) for q in np.quantile(phi[expressed], [0.1, 0.5, 0.9])]}
        log(f"g0d: {generator_info['g0d']['genes_overdispersed']} genes overdispersed, "
            f"median phi {generator_info['g0d']['phi_quantiles_expressed'][1]:.3f}")

    for arm in args.arms:
        if "cis" in arm and cis_model is None:
            log(f"skip {arm}: no --coords")
            continue
        generator, terms = parse_arm(arm)
        for gen_seed in args.gen_seeds or [None]:
            gen_rng = rng if gen_seed is None else np.random.default_rng(gen_seed)
            blocks, labels = [], []
            for i, t in enumerate(targets):
                n = bench.n_pred(t)
                if arm == "null_g0":
                    blocks.append(sample_counts(profile, resample_library_sizes(lib_pool, n, gen_rng), gen_rng,
                                                max_stored_per_cell=len(genes), max_counts_per_cell=1_000_000))
                    labels.append(np.full(n, t))
                    continue
                logfc = np.zeros(len(genes))
                observed = np.zeros(len(genes), dtype=bool)
                for term in terms:
                    name, _, amp = term.partition("_a")
                    a = float(amp) if amp else 0.0
                    if name == "oracle":
                        part = a * src.shrunk[i]
                    elif name == "shared":
                        part = a * (shared_sum - src.shrunk[i]) / (len(targets) - 1)
                    elif name == "cis":
                        part = a * cis_model.vector(t, genes, coords)
                    elif name in ext:
                        vec, mask = ext[name][t]
                        part = a * vec
                        observed |= mask
                    elif name == "common":
                        part = a * common_axis
                    elif name == "permcommon":
                        part = a * perm_axis
                    elif name == "null_new":
                        continue
                    else:
                        raise SystemExit(f"unknown term {term!r} in arm {arm!r}")
                    logfc += part
                    if name not in ext:
                        observed |= part != 0
                if generator is None:
                    fc = None if arm == "null_new" else np.exp(np.clip(logfc, -3, 3))
                    blocks.append(model.sample(n, gen_rng, fold_change=fc))
                else:
                    blocks.append(trial01_cells(basal, logfc, observed, lib_pool, n, gen_rng,
                                                max_stored_per_cell=len(genes), max_counts_per_cell=1_000_000,
                                                overdispersion=phi if generator == "g0d" else None)[0])
                labels.append(np.full(n, t))
            bench.score(arm_key(arm, gen_seed), sp.vstack(blocks).tocsr(), np.concatenate(labels))

    bench.finish({"stage": "73_bench_k562_panel", "args": {k: str(v) for k, v in vars(args).items()},
                  "model": None if model is None else model.diagnostics, "generators": generator_info,
                  "targets": targets, "common_term": common_info, "effects": args.effects})
    log("done")


if __name__ == "__main__":
    main()
