"""Stage 75: does a K562 single-cell effect transfer to a context it never saw?

The competition asks for exactly this -- a target's response in a cell type with
no perturbation data -- and HepG2 (Nadig 2024) is the one other CRISPRi
single-cell context on Drive whose targets overlap K562 genome-wide. Here the
truth is real HepG2 cells, and every predictor reads only K562:

* ``transfer_aX``    -- the target's K562 effect (stage-71 accumulators, EB-shrunk),
  mapped by symbol onto HepG2's genes, scaled by X; ``rawtransfer_aX`` unshrunk;
* ``cis_aX``         -- the TSS-distance prior fitted on K562 targets NOT in this bench,
  on genes K562 did not measure;
* ``cismeas_aX``     -- genes within 5 kb of the target that K562 DID measure get X
  times their own K562 effect instead of the transfer amplitude;
* ``shared_aX``      -- the mean K562 effect over the bench's other targets;
* ``common_aX``      -- X times the response shared by a SECOND source's knockdowns
  (`--common-bulk`, mean over its targets minus this bench's), the same for every target;
* ``permcommon_aX``  -- the same values as ``common_aX`` permuted over the genes the source measured
  (own rng, seed+2): the volume control for the common term, with its direction destroyed;
* ``shuffled_aX``    -- another bench target's effect, by a fixed derangement (own rng, seed+1,
  so every other arm draws exactly as before), with that target's own gene zeroed: same
  effect sizes and shared response as ``transfer_aX``, no target identity;
* ``NAME_aX``        -- X times the effects of `--effects NAME=PATH` (stage 92's exports): how a
  separately trained predictor is judged with the same generator, scorer and targets;
* ``g0:``-prefixed arms use trial-01's generator instead of `ControlModel`
  (``g0:transfer_a0.2`` is trial-01's recipe on this context).

Terms combine with ``+``. Scale and anchors come from `vcc2026.bench.Bench`
(truth = half A, point 1 = half B, point 0 = the official baseline). **Not a VCC
score**: HepG2 targets are essential-screen genes and live on ~9.6k genes.

    python scripts/75_bench_hepg2_transfer.py --hepg2 <h5ad> --k562 <stage-71 out> \
        --coords <gene_coordinates tsv> --out <dir>

``--k562-bulk`` takes a Replogle ``*_raw_bulk_01.h5ad`` instead, which is how a source
other than K562 enters here; ``--targets-file`` then pins both runs to the same panel,
without which each source draws its own.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import Bench, log  # noqa: E402
from vcc2026.generator import ControlModel  # noqa: E402
from vcc2026.predictor_sc import (  # noqa: E402
    CisModel,
    assemble_log_fc,
    common_from_bulk,
    derangement,
    effects_from_bulk,
    effects_from_group_stats,
    load_coordinates,
    read_bulk,
)
from vcc2026.sampling import resample_library_sizes, sample_counts  # noqa: E402
from vcc2026.sc_stream import read_frame, read_rows  # noqa: E402

NTC = "non-targeting"
DEFAULT_ARMS = [
    "null_new", "g0:transfer_a0.2", "transfer_a0.25", "transfer_a0.5", "transfer_a1.0",
    "rawtransfer_a0.5", "cismeas_a1.0+cis_a1.0", "transfer_a0.25+cismeas_a1.0+cis_a1.0",
    "transfer_a0.5+cismeas_a1.5+cis_a1.5", "transfer_a0.5+cismeas_a1.0+cis_a1.0+shared_a0.5",
    "g0:transfer_a0.25+cismeas_a1.0+cis_a1.0",
]


def load_effects(specs, genes) -> dict:
    """``NAME=PATH`` npz files (targets, genes, lfc in ln units) -> {NAME: {target: vector on genes}}.

    How an externally trained predictor (stage 92) enters a bench: the same generator, the same
    scorer and the same targets as every other arm. Genes the file lacks get 0.
    """
    out = {}
    for spec in specs or []:
        name, _, path = spec.partition("=")
        if "_a" in name or "+" in name or ":" in name:
            raise SystemExit(f"effects name {name!r} must not contain '_a', '+' or ':'")
        z = np.load(path)
        pos = pd.Index(z["genes"].astype(str)).get_indexer(np.asarray(genes).astype(str))
        rows = {}
        for i, t in enumerate(z["targets"].astype(str)):
            v = np.zeros(len(genes))
            v[pos >= 0] = z["lfc"][i, pos[pos >= 0]]
            rows[t] = v
        out[name] = rows
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hepg2", type=Path, required=True)
    src_arg = p.add_mutually_exclusive_group(required=True)
    src_arg.add_argument("--k562", type=Path, help="stage-71 output (single-cell accumulators)")
    src_arg.add_argument("--k562-bulk", type=Path, help="K562_gwps_raw_bulk_01.h5ad (quasi-Poisson SE)")
    p.add_argument("--coords", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--n-targets", type=int, default=300)
    p.add_argument("--min-cells", type=int, default=50)
    p.add_argument("--control-cells", type=int, default=None, help="cap the NTC pool (local tests)")
    p.add_argument("--targets-file", type=Path, default=None,
                   help="one gene symbol per line: restrict the panel to these. Two sources screen "
                        "different target sets, so without it each source draws a different panel and "
                        "their raw values answer different questions (stage 86 writes the shared list)")
    p.add_argument("--cis-pairs", type=Path, default=None,
                   help="stage-77 k562_neighbour_pairs.csv: take the cis bins from it (bench targets excluded) "
                        "instead of estimating effects for every other K562 target")
    p.add_argument("--common-bulk", type=Path, default=None,
                   help="a Replogle *_raw_bulk_01.h5ad whose shared knockdown response the common_aX term adds")
    p.add_argument("--effects", action="append", default=None, metavar="NAME=PATH",
                   help="predicted effects (npz: targets, genes, lfc) usable as the term NAME_aX")
    p.add_argument("--arms", nargs="+", default=DEFAULT_ARMS)
    p.add_argument("--seed", type=int, default=2026)
    args = p.parse_args()
    if (args.out / "bench.json").exists():
        raise SystemExit(f"{args.out} already holds a bench; choose a new --out")
    rng = np.random.default_rng(args.seed)

    with h5py.File(args.hepg2, "r") as f:
        obs = read_frame(f["obs"])
        var = read_frame(f["var"])
    names = var.index.astype(str).to_numpy()
    _, first = np.unique(names, return_index=True)
    col_keep = np.sort(first)
    genes = names[col_keep]
    sym = obs["gene"].astype(str).to_numpy()

    coords = load_coordinates(args.coords)
    if args.k562 is not None:
        groups = pd.read_csv(args.k562 / "groups.csv")
        stats = np.load(args.k562 / "group_stats.npz")
        k562_names = pd.read_csv(args.k562 / "var.csv", index_col=0)["gene_name"].astype(str).to_numpy()
        k562_targets = set(groups.loc[~groups.is_ntc, "gene"].astype(str))

        def k562_effects(which):
            return effects_from_group_stats(stats, groups, k562_names, targets=which)
    else:
        bulk_means, bulk_cells, bulk_sym, bulk_ntc, k562_names = read_bulk(args.k562_bulk)
        k562_targets = set(bulk_sym[~bulk_ntc])

        def k562_effects(which):
            return effects_from_bulk(bulk_means, bulk_cells, bulk_sym, bulk_ntc, k562_names, targets=which)
    counts = pd.Series(sym[sym != NTC]).value_counts()
    eligible = sorted(t for t in counts.index if counts[t] >= args.min_cells and t in k562_targets)
    if args.targets_file is not None:
        want = {ln.strip() for ln in args.targets_file.read_text(encoding="utf-8").splitlines() if ln.strip()}
        eligible = [t for t in eligible if t in want]
        log(f"panel restricted to {len(eligible)} of the {len(want)} symbols in {args.targets_file}")
    targets = sorted(rng.choice(eligible, size=min(args.n_targets, len(eligible)), replace=False).tolist())
    log(f"HepG2: {len(eligible)} targets with >= {args.min_cells} cells also in K562; using {len(targets)}")

    src = k562_effects(targets)
    targets = [t for t in targets if t in set(src.targets)]
    if args.cis_pairs:
        pairs = pd.read_csv(args.cis_pairs)
        cis_model = CisModel.from_pairs(pairs[~pairs["target"].astype(str).isin(targets)])
    else:
        others = sorted((k562_targets - set(targets)) & set(coords.index))
        cis_model = CisModel().fit(k562_effects(others), coords)
    log("cis bins " + " ".join(f"{e}:{v:+.3f}(n={n})" for e, v, n in
                               zip(cis_model.edges, cis_model.by_bin, cis_model.n_by_bin)))

    target_rows = {t: np.flatnonzero(sym == t) for t in targets}
    ntc_rows = np.flatnonzero(sym == NTC)
    if args.control_cells:
        ntc_rows = np.sort(rng.choice(ntc_rows, size=min(args.control_cells, ntc_rows.size), replace=False))
    all_rows = np.sort(np.concatenate(list(target_rows.values()) + [ntc_rows]))
    log(f"reading {all_rows.size} HepG2 cells")
    x = read_rows(args.hepg2, all_rows)[:, col_keep]
    remap = {r: i for i, r in enumerate(all_rows)}
    target_rows = {t: np.array([remap[r] for r in rows]) for t, rows in target_rows.items()}
    ctrl_rows = np.array([remap[r] for r in ntc_rows])

    bench = Bench(x, target_rows, ctrl_rows, genes, args.out, seed=args.seed)
    bench.anchors()
    model = ControlModel(state="kde", seed=args.seed).fit(bench.ctrl, log=log)
    lib_pool = np.asarray(bench.ctrl.sum(axis=1)).ravel()
    profile = np.asarray(bench.ctrl.sum(axis=0), dtype=np.float64).ravel()

    idx = src.index()
    pos = pd.Index(genes).get_indexer(src.genes)
    shared_axis = np.zeros(len(genes))
    shared_axis[pos[pos >= 0]] = src.shrunk.mean(axis=0)[pos >= 0]
    ext = load_effects(args.effects, genes)
    for name, rows in ext.items():
        missing = [t for t in targets if t not in rows]
        if missing:
            raise SystemExit(f"--effects {name}: no prediction for {len(missing)} bench targets, e.g. {missing[:3]}")
    partner = derangement(targets, args.seed + 1) if any("shuffled_a" in a for a in args.arms) else {}
    common_axis, common_info = np.zeros(len(genes)), None
    if any("common_a" in a for a in args.arms):
        if args.common_bulk is None:
            raise SystemExit("a common_aX arm needs --common-bulk")
        common_axis, common_info = common_from_bulk(args.common_bulk, genes, exclude=targets)
        log(f"common term from {common_info}")
    perm_axis = common_axis.copy()
    nz = np.flatnonzero(common_axis)
    perm_axis[nz] = common_axis[nz][np.random.default_rng(args.seed + 2).permutation(nz.size)]

    for arm in args.arms:
        use_g0 = arm.startswith("g0:")
        terms = arm.split(":", 1)[1] if use_g0 else arm
        blocks, labels = [], []
        for t in targets:
            n = bench.n_pred(t)
            logfc = np.zeros(len(genes))
            if terms != "null_new":
                amp = {"transfer": 0.0, "rawtransfer": 0.0, "cis": 0.0, "cismeas": 0.0, "shared": 0.0,
                       "shuffled": 0.0, "common": 0.0, "permcommon": 0.0}
                for term in terms.split("+"):
                    name, _, a = term.partition("_a")
                    if name in ext:
                        logfc += float(a) * ext[name][t]
                        continue
                    if name not in amp:
                        raise SystemExit(f"unknown term {term!r} in arm {arm!r}")
                    amp[name] = float(a)
                raw = amp["rawtransfer"] > 0
                logfc += assemble_log_fc(t, genes, src=src, a_transfer=amp["rawtransfer"] if raw else amp["transfer"],
                                         use_raw=raw, cis=cis_model, coords=coords, a_cis=amp["cis"],
                                         a_cis_measured=amp["cismeas"])
                if amp["shared"]:
                    own = np.zeros(len(genes))
                    own[pos[pos >= 0]] = src.shrunk[idx[t]][pos >= 0]
                    logfc += amp["shared"] * (shared_axis * len(targets) - own) / (len(targets) - 1)
                if amp["shuffled"]:
                    other = assemble_log_fc(partner[t], genes, src=src, a_transfer=amp["shuffled"])
                    other[genes == partner[t]] = 0.0  # the partner's own knockdown is not a response
                    logfc += other
                if amp["common"]:
                    logfc += amp["common"] * common_axis
                if amp["permcommon"]:
                    logfc += amp["permcommon"] * perm_axis
            fc = np.exp(np.clip(logfc, -3, 3))
            if use_g0:
                blocks.append(sample_counts(profile * fc, resample_library_sizes(lib_pool, n, rng), rng,
                                            max_stored_per_cell=len(genes), max_counts_per_cell=1_000_000))
            else:
                blocks.append(model.sample(n, rng, fold_change=None if terms == "null_new" else fc))
            labels.append(np.full(n, t))
        bench.score(arm, sp.vstack(blocks).tocsr(), np.concatenate(labels))

    bench.finish({"stage": "75_bench_hepg2_transfer", "args": {k: str(v) for k, v in vars(args).items()},
                  "targets": targets, "model": model.diagnostics, "shuffle_partner": partner,
                  "common_term": common_info, "effects": args.effects,
                  "cis_bins": {"edges": list(cis_model.edges), "ln_effect": cis_model.by_bin.tolist(),
                               "n": cis_model.n_by_bin.tolist()}})
    log("done")


if __name__ == "__main__":
    main()
