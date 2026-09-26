"""The multi-source atlas bench: thousands of held-out targets per line, genome-wide universes as inputs.

The panel benches of 26 September (reports/trasferimento_appreso_2026-09-26/, trasferimento_gerarchico,
quattro_sorgenti) test on ~270 targets per held-out source, so their intervals are wide, and the
hierarchical model estimated its per-gene variances from the same ~270 targets. Here every source is a
genome-wide universe (reports/universo_2026-09-26/: K562, CD4, Orion HCT116 and HEK293T). For a held-out
line H (its family excluded from everything: an Orion line held out leaves K562 and CD4 as inputs):

* test targets: a seeded sample of targets measured in H and in at least two input sources, none of the
  300 panel targets;
* estimation targets: every other target measured in at least two input sources, also outside the panel,
  disjoint from the test targets (at most --max-estimation-targets, seeded). The per-gene variances of
  the hierarchical model (the moments of `multisource.eb_components`, CD4's SE variance times
  --cd4-se-factor for its donors, the same blend with expression bins) are accumulated over them in
  blocks, never loading a universe whole, on effects centred per source over the estimation targets;
* arms on the test targets, all with the cis head of the t20/t22 recipe (its prior refitted without the
  panel and without the test targets):
  - `t22like`: equal-weight `mix` of shrunk effects, gamma 1, reliability n/(n+100), x 1.576: the t22
    recipe's shape with the held-out family's sources removed;
  - `prog_<k>`: t22like's transferred part projected on the first k principal components of the inputs'
    pooled centred responses over (up to --program-targets of) the estimation targets, the response
    programs of thousands of knockdowns, on expressed genes, log1p-weighted;
  - `eb_panel`: the posterior mean of `eb_pool` with variances from the test targets' own inputs, as
    stage 100's pooling block does on the panel;
  - `eb_atlas`: the same posterior, the variances from the estimation targets;
  - `share_atlas`: t22like's transferred part times sigma2 / (sigma2 + tau2), the share of each gene's
    response that the lines have in common, from the estimation targets;
  - `agree_target`: t22like's transferred part times, per target, the inputs' agreement: their
    cross-covariance over the energy of their mean on expressed genes (log1p-weighted), shrunk toward
    the pooled ratio with the median target's energy as pseudo-count, clipped to [0, 1];
  every arm but t22like scaled to t22like's median count of detectable genes (`match_detectable`);
* proxies as reports/quattro_sorgenti_2026-09-26: PDS, reach and sign precision at 200 in effect space;
  PDS and nMAE after the trial-01 profile step and a 400-cell pseudobulk (A/B/C basal, 3 seeds each);
  the combined difference 0.36 dPDS_gen - 0.27 dnMAE_gen against t22like, paired bootstrap over the
  test targets. The test targets' own genes are left out of the PDS, as the panel's are in the panel
  benches.
Regime C for each test target (measured in other lines; H never enters). Not VCC scores.

    scripts/py.cmd reports/atlante_2026-09-26/atlas_bench.py --out reports/atlante_2026-09-26/r1 \
        --universe k562=<dir> --universe cd4_mix=<dir> --universe orion_hct116=<dir> --universe orion_hek293t=<dir>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "modulo_cis_2026-09-26"))
sys.path.insert(0, str(REPO / "reports" / "banco_varianti_2026-09-25"))
sys.path.insert(0, str(REPO / "reports" / "trasferimento_appreso_2026-09-26"))

from cis_bench import SEED, boot, pds_proxy, reach_proxy  # noqa: E402
from lct_bench2 import precision_at  # noqa: E402
from noise_sim import rank_pds  # noqa: E402
from noise_sim2 import realise  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.multisource import AxisTable, eb_components, eb_pool, mix  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402
from vcc2026.priors import add_cis, cis_prior  # noqa: E402
from vcc2026.transfer_model import detectable_threshold, match_detectable, mixture_se  # noqa: E402

DATA = Path("C:/Users/ferra/vcc2026-data")
AMPLITUDE = 1.576
BLOCK = 200
W_PDS, W_NMAE = 0.36, 0.27
BIN_WEIGHT, N_BINS = 100.0, 50       # as multisource.eb_components
BASE = "t22like"
CD4_PARTS = ("cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr")


def family(name: str) -> str:
    return name.split("_")[0]


class Universe:
    """Rows of a genome-wide universe folder (stage-98 npz chunks + index.csv), read on demand.

    ``index.csv`` names each target's chunk as a file name (K562, Orion) or a number (CD4, whose files
    are ``<name>_<chunk:03d>.npz``); a target with an empty chunk has no effect row and is dropped."""

    def __init__(self, name: str, folder: Path):
        self.name, self.folder = name, folder
        idx = pd.read_csv(folder / "index.csv")
        idx = idx[idx["chunk"].notna() & (idx["chunk"].astype(str).str.strip() != "")].copy()
        if pd.api.types.is_numeric_dtype(idx["chunk"]):
            idx["file"] = [f"{name}_{int(c):03d}.npz" for c in idx["chunk"]]
        else:
            idx["file"] = idx["chunk"].astype(str)
        self.file_of = dict(zip(idx["target"].astype(str), idx["file"]))
        self.targets = set(self.file_of)
        self._cache: dict[str, dict] = {}
        self._parts: list | None = None

    def _load(self, file: str) -> dict:
        if file not in self._cache:
            if len(self._cache) >= 2:
                self._cache.pop(next(iter(self._cache)))
            z = np.load(self.folder / file, allow_pickle=False)
            self._cache[file] = {"targets": {t: i for i, t in enumerate(z["targets"].astype(str))},
                                 **{k: z[k] for k in ("raw", "shrunk", "se", "n_cells")}}
        return self._cache[file]

    def table(self, targets: list[str]) -> AxisTable:
        """The rows of ``targets`` this universe has, in the order given (grouped by file to read each once)."""
        by_file: dict[str, list[str]] = {}
        for t in targets:
            f = self.file_of.get(t)
            if f is not None:
                by_file.setdefault(f, []).append(t)
        found = {}
        for f, ts in by_file.items():
            z = self._load(f)
            for t in ts:
                i = z["targets"].get(t)
                if i is not None:   # copies: a view would keep the whole chunk alive
                    found[t] = (z["raw"][i].copy(), z["shrunk"][i].copy(), z["se"][i].copy(), z["n_cells"][i])
        kept = [t for t in targets if t in found]
        if not kept:
            raise ValueError(f"{self.name}: none of the targets")
        raw = np.vstack([found[t][0] for t in kept]).astype(np.float32)
        shrunk = np.vstack([found[t][1] for t in kept]).astype(np.float32)
        se = np.vstack([found[t][2] for t in kept]).astype(np.float32)
        tab = AxisTable(self.name, kept, shrunk, raw, se, np.asarray([found[t][3] for t in kept]))
        if self.name == "cd4_mix" and not np.isfinite(tab.se[np.isfinite(tab.raw)]).any():
            # the mixed table keeps no SE (as the stage-98 cache): the mixture's, from the conditions
            if self._parts is None:
                self._parts = [Universe(p, self.folder) for p in CD4_PARTS]
            parts = []
            for u in self._parts:
                have = [t for t in kept if t in u.targets]
                if have:
                    parts.append(u.table(have))
            tab.se = mixture_se(parts, kept, tab.raw.shape[1])
        return tab


def blend(v: np.ndarray, n: np.ndarray, expr: np.ndarray, has: np.ndarray) -> np.ndarray:
    """eb_components' last step: v blended with its median over genes of similar expr, weight n / (n + 100)."""
    edges = np.quantile(expr[has], np.linspace(0, 1, N_BINS + 1)[1:-1]) if has.any() else np.array([])
    b = np.digitize(np.nan_to_num(expr, nan=-1.0), edges)
    med = np.array([np.median(v[has & (b == k)]) if (has & (b == k)).any() else 0.0 for k in range(N_BINS)])
    return np.where(has, (n * v + BIN_WEIGHT * med[b]) / (n + BIN_WEIGHT), 0.0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", action="append", required=True, metavar="NAME=DIR")
    ap.add_argument("--held-out", nargs="+", default=None, help="sources to hold out (default: every one)")
    ap.add_argument("--test-targets", type=int, default=1000)
    ap.add_argument("--max-estimation-targets", type=int, default=6000)
    ap.add_argument("--min-inputs", type=int, default=2, help="smoke tests only may lower it")
    ap.add_argument("--programs", type=int, nargs="*", default=[20, 50, 150])
    ap.add_argument("--program-targets", type=int, default=3000)
    ap.add_argument("--cd4-se-factor", type=float, default=2.0, help="k of CD4's SE variance (donors)")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--recipe", type=Path, default=REPO / "configs/recipes/t22.json")
    ap.add_argument("--save", type=Path, default=None, help="optional folder for the arms and truth per held-out line")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    if args.save is not None:
        args.save.mkdir(parents=True, exist_ok=False)
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:7.0f}s] {m}", flush=True)  # noqa: E731
    axis = np.asarray(official_axis().symbols)
    G = axis.size
    col = {g: i for i, g in enumerate(axis)}
    panel = set(pd.read_csv(args.panel).iloc[:, 0].astype(str))
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    cpm_abc = basal[["A", "B", "C"]].mean(axis=1).to_numpy()
    xa = 0.05 * cpm_abc
    w_eval = (xa / (1.0 + xa)).astype(np.float32)
    gate = cpm_abc >= 5.0
    thr = detectable_threshold(cpm_abc)
    det = lambda E: float(np.median(((np.abs(E) > thr[None, :]) & gate[None, :]).sum(axis=1)))  # noqa: E731
    cis_spec = json.loads(args.recipe.read_text(encoding="utf-8"))["cis"]
    cis_pairs = pd.read_csv(REPO / cis_spec["pairs"])
    coords = load_coordinates(args.coords)
    unis = {}
    for spec in args.universe:
        name, _, folder = spec.partition("=")
        unis[name] = Universe(name, Path(folder))
        log(f"{name}: {len(unis[name].targets)} targets with effects")
    rng = np.random.default_rng(SEED)
    rows_out, meta = [], []
    for held in (args.held_out or list(unis)):
        inputs = [n for n in unis if family(n) != family(held)]
        if len(inputs) < args.min_inputs:
            log(f"{held}: fewer than {args.min_inputs} input sources, skipped")
            continue
        ks = [args.cd4_se_factor if family(n) == "cd4" else 1.0 for n in inputs]
        count = {t: sum(t in unis[n].targets for n in inputs) for t in set().union(*(unis[n].targets for n in inputs))}
        eligible = sorted(t for t, c in count.items() if c >= args.min_inputs and t not in panel)
        test_pool = [t for t in eligible if t in unis[held].targets]
        test = sorted(rng.choice(test_pool, size=min(args.test_targets, len(test_pool)), replace=False).tolist())
        test_set = set(test)
        est = [t for t in eligible if t not in test_set]
        if len(est) > args.max_estimation_targets:
            est = sorted(rng.choice(est, size=args.max_estimation_targets, replace=False).tolist())
        log(f"{held}: inputs {inputs}, {len(test)} test targets (of {len(test_pool)}), {len(est)} estimation targets")
        expr = np.log1p(np.nanmean(np.vstack([basal[n].to_numpy(dtype=float) for n in inputs]), axis=0))

        def block(part):
            ys, ses = [], []
            for n in inputs:
                have = [t for t in part if t in unis[n].targets]
                y = np.full((len(part), G), np.nan, dtype=np.float32)
                se = np.full((len(part), G), np.nan, dtype=np.float32)
                if have:
                    tab = unis[n].table(have)
                    ix = tab.index()
                    for i, t in enumerate(part):
                        if t in ix:
                            y[i] = tab.raw[ix[t]]
                            se[i] = tab.se[ix[t]]
                ys.append(y)
                ses.append(se)
            return ys, ses

        # pass 1: each input's mean over the estimation targets (the centre gamma 1 removes)
        tot = {n: np.zeros(G) for n in inputs}
        cnt = {n: np.zeros(G) for n in inputs}
        for b0 in range(0, len(est), BLOCK):
            ys, _ = block(est[b0:b0 + BLOCK])
            for n, y in zip(inputs, ys):
                tot[n] += np.nansum(y, axis=0, dtype=np.float64)
                cnt[n] += np.isfinite(y).sum(axis=0)
        centre = {n: np.divide(tot[n], cnt[n], out=np.zeros(G), where=cnt[n] > 0) for n in inputs}
        # pass 2: moments of the hierarchical model and the response programs
        s_num, s_den, ex, n_ex, pair_t, obs_t = (np.zeros(G) for _ in range(6))
        prog_rows, prog_left = [], args.program_targets
        for b0 in range(0, len(est), BLOCK):
            part = est[b0:b0 + BLOCK]
            ys, ses = block(part)
            ys = [(y - centre[n][None, :]) for n, y in zip(inputs, ys)]   # float64
            ses = [se.astype(np.float64) for se in ses]
            if prog_left > 0:
                stack = np.stack(ys)
                with np.errstate(invalid="ignore"):
                    pooled = np.nanmean(stack, axis=0)
                keep_rows = np.isfinite(pooled).any(axis=1)
                take = np.nan_to_num(pooled[keep_rows])[:prog_left]
                prog_rows.append(take.astype(np.float32))
                prog_left -= take.shape[0]
                del stack, pooled
            pair_any = np.zeros((len(part), G), dtype=bool)
            for i in range(len(ys)):
                for j in range(i + 1, len(ys)):
                    ok = np.isfinite(ys[i]) & np.isfinite(ys[j])
                    s_num += np.where(ok, ys[i] * ys[j], 0.0).sum(axis=0)
                    s_den += ok.sum(axis=0)
                    pair_any |= ok
            obs_any = np.zeros((len(part), G), dtype=bool)
            for y, se, k in zip(ys, ses, ks):
                ok = np.isfinite(y) & np.isfinite(se)
                ex += np.where(ok, y * y - k * se * se, 0.0).sum(axis=0)
                n_ex += ok.sum(axis=0)
                obs_any |= ok
            pair_t += pair_any.sum(axis=0)
            obs_t += obs_any.sum(axis=0)
        sigma2_raw = np.divide(s_num, s_den, out=np.zeros(G), where=s_den > 0)
        tau2_raw = np.divide(ex, n_ex, out=np.zeros(G), where=n_ex > 0) - sigma2_raw
        has = (s_den > 0) & (n_ex > 0) & np.isfinite(expr)
        sigma2 = blend(np.maximum(sigma2_raw, 0.0), pair_t, expr, has)
        tau2 = blend(np.maximum(tau2_raw, 0.0), obs_t, expr, has)
        log(f"{held}: variances from {int(np.median(pair_t[gate]))} targets per expressed gene (median); "
            f"median sigma2 {np.median(sigma2[gate]):.4g}, tau2 {np.median(tau2[gate]):.4g}")
        P = np.vstack(prog_rows) if prog_rows else np.zeros((0, G), dtype=np.float32)
        n_prog = P.shape[0]
        wg = w_eval[gate]
        Pg = P[:, gate] * wg[None, :]                   # programs on expressed genes, log1p-weighted
        del P
        Pg -= Pg.mean(axis=0, keepdims=True)
        # principal axes through the (targets x targets) Gram matrix: the same V as an SVD, less memory
        evals, U = np.linalg.eigh(Pg.astype(np.float64) @ Pg.T.astype(np.float64))
        order = np.argsort(evals)[::-1]
        evals, U = np.maximum(evals[order], 0.0), U[:, order]
        kmax = max(args.programs) if args.programs else 0
        Vt = ((U[:, :kmax].T @ Pg) / np.sqrt(np.maximum(evals[:kmax], 1e-12))[:, None]).astype(np.float32)
        explained = evals / max(float(evals.sum()), 1e-12)
        log(f"{held}: programs from {n_prog} targets; variance in the first "
            + "/".join(str(k) for k in args.programs) + " components "
            + "/".join(f"{explained[:k].sum():.3f}" for k in args.programs))
        del Pg, U

        # the test targets: inputs, cis head, arms
        tabs = {}
        for n in inputs:
            have = [t for t in test if t in unis[n].targets]
            if have:
                tabs[n] = unis[n].table(have)
        truth = unis[held].table(test)
        assert truth.targets == test, "truth rows out of order"
        T = len(test)
        cis_model = cis_prior(cis_pairs, sorted(panel | test_set))
        cis = np.zeros((T, G), dtype=np.float32)
        add_cis(cis, np.zeros((T, G), dtype=bool), test, axis, cis_model, coords,
                int(cis_spec["max_distance_bp"]), float(cis_spec.get("scale", 1.0)))
        used = [n for n in inputs if n in tabs]
        m, d = mix([tabs[n] for n in used], test, weights={n: 1.0 for n in used}, gamma=1.0, reliability_scale=100.0)
        tx = (np.where(d > 0, m, 0.0) * AMPLITUDE).astype(np.float32)
        del m, d
        ys, ses = [], []
        for n in inputs:
            y = np.full((T, G), np.nan, dtype=np.float32)
            se = np.full((T, G), np.nan, dtype=np.float32)
            if n in tabs:
                ix = tabs[n].index()
                for i, t in enumerate(test):
                    if t in ix:
                        y[i] = tabs[n].raw[ix[t]]
                        se[i] = tabs[n].se[ix[t]]
                del tabs[n]
            with np.errstate(invalid="ignore"):
                y -= np.nan_to_num(np.nanmean(y, axis=0))[None, :].astype(np.float32)   # centred on the test targets, as on the panel
            ys.append(y)
            ses.append(se)
        base = (tx + cis).astype(np.float32)
        arms = {BASE: base}
        for k in args.programs:
            V = Vt[:k]
            proj = np.zeros_like(tx)
            coef = (tx[:, gate] * wg[None, :]) @ V.T
            proj[:, gate] = (coef @ V) / np.where(wg > 0, wg, 1.0)[None, :]
            arms[f"prog_{k}"] = match_detectable(proj.astype(np.float32), base, thr, gate, offset=cis)[0]
            del proj, coef
        # per-target agreement of the inputs: cross-input covariance over the variance of their mean,
        # on expressed genes with the scorer's log1p weights (the target-level analogue of sigma2 / total)
        a = [np.where(np.isfinite(y[:, gate]), y[:, gate], np.nan) * wg[None, :] for y in ys]
        cross, npair = np.zeros(T), 0
        for i in range(len(a)):
            for j in range(i + 1, len(a)):
                cross += np.nansum(a[i] * a[j], axis=1)
                npair += 1
        cross /= max(npair, 1)
        with np.errstate(invalid="ignore"):
            mean_in = np.nanmean(np.stack(a), axis=0)
        var_mean = np.nansum(mean_in * mean_in, axis=1)
        # the per-target ratio is noisy with two or three inputs: shrunk toward the pooled ratio, with a
        # pseudo-energy equal to the median target's (a typical target is half its own, half the pool's)
        pooled_ratio = float(cross.sum() / max(var_mean.sum(), 1e-12))
        kappa = float(np.median(var_mean))
        agree = np.clip((cross + kappa * pooled_ratio) / np.maximum(var_mean + kappa, 1e-12), 0.0, 1.0).astype(np.float32)
        del a, mean_in
        s2_panel, t2_panel = eb_components(ys, ses, ks, expr)
        scales = {}
        for label, (s2, t2) in {"eb_panel": (s2_panel, t2_panel), "eb_atlas": (sigma2, tau2)}.items():
            theta = eb_pool(ys, ses, ks, s2, t2)
            arms[label], scales[label] = match_detectable(theta, base, thr, gate, offset=cis)
            del theta
        del ys, ses
        share = np.divide(sigma2, sigma2 + tau2, out=np.zeros(G), where=(sigma2 + tau2) > 0).astype(np.float32)
        arms["share_atlas"], scales["share_atlas"] = match_detectable(tx * share[None, :], base, thr, gate, offset=cis)
        arms["agree_target"], scales["agree_target"] = match_detectable(tx * agree[:, None], base, thr, gate, offset=cis)
        log(f"{held}: arms {list(arms)}")

        # truth and proxies
        y_true = truth.raw.astype(np.float32)
        with np.errstate(divide="ignore", invalid="ignore"):
            z_true = (y_true / truth.se).astype(np.float32)
        del truth
        tcols = np.array([col.get(t, -1) for t in test])
        own = np.zeros((T, G), dtype=bool)
        own[np.arange(T)[tcols >= 0], tcols[tcols >= 0]] = True
        sig = np.isfinite(y_true) & (np.abs(np.nan_to_num(z_true)) >= 3) & gate[None, :] & ~own
        test_cols = tcols[tcols >= 0]
        keep = np.ones(G, dtype=bool)
        keep[test_cols] = False
        observed = np.abs(base) > 0
        if args.save is not None:
            np.savez_compressed(args.save / f"{held}.npz", targets=np.array(test), truth=y_true, **arms)
        prec = {name: precision_at(E, y_true, gate, tcols) for name, E in arms.items()}
        cohort = np.all([np.isfinite(v) for v in prec.values()], axis=0)
        e_base = float((np.asarray(base, np.float64) ** 2).sum())
        per = {}
        for name, E in arms.items():
            pds_gen, nmae_gen = [], []
            for c in ("A", "B", "C"):
                cpm = basal[c].to_numpy(dtype=float)
                x = 0.05 * cpm
                lv = keep & (cpm > 0)
                Tl = (np.log1p(x * np.exp(np.clip(np.nan_to_num(y_true), -20, 20))) - np.log1p(x))[:, lv]
                for seed in (1, 2, 3):
                    noisy, _, _ = realise(E, cpm, observed | (np.abs(E) > 0), np.random.default_rng([seed, ord(c)]))
                    D = (np.log1p(x * np.exp(np.clip(noisy, -20, 20))) - np.log1p(x))[:, lv]
                    pds_gen.append(rank_pds(D, Tl))
                    err = np.where(sig, np.abs(noisy - np.nan_to_num(y_true)), 0.0).sum(axis=1)
                    ref = np.where(sig, np.abs(np.nan_to_num(y_true)), 0.0).sum(axis=1)
                    nmae_gen.append(np.where(ref > 0, err / np.maximum(ref, 1e-12), np.nan))
                    del noisy, D
                del Tl
            per[name] = {"pds": pds_proxy(E, y_true, w_eval, test_cols), "reach": reach_proxy(E, y_true, z_true, gate, tcols),
                         "prec": prec[name], "pds_gen": np.mean(pds_gen, axis=0), "nmae_gen": np.nanmean(nmae_gen, axis=0),
                         "energy_ratio": float((np.asarray(E, np.float64) ** 2).sum()) / max(e_base, 1e-12),
                         "detectable_median": det(E)}
            log(f"{held}: {name} evaluated")
        brng = np.random.default_rng([SEED, len(rows_out)])
        for name, v in per.items():
            row = {"held_out": held, "arm": name, "test_targets": T, "pds_proxy": float(np.mean(v["pds"])),
                   "reach_proxy": float(np.nanmean(v["reach"])), "prec_200_shared": float(np.nanmean(v["prec"][cohort])),
                   "pds_gen": float(np.mean(v["pds_gen"])), "nmae_gen": float(np.nanmean(v["nmae_gen"])),
                   "energy_ratio": v["energy_ratio"], "detectable_median": v["detectable_median"],
                   "scale": scales.get(name)}
            if name != BASE:
                b = per[BASE]
                for key in ("pds", "reach", "pds_gen", "nmae_gen"):
                    diff = np.asarray(v[key], dtype=np.float64) - np.asarray(b[key], dtype=np.float64)
                    row[f"{key}_minus_base"], row[f"{key}_ci95"] = boot(diff[np.isfinite(diff)], brng)
                dp, ci = boot((v["prec"] - b["prec"])[cohort], brng)
                row["prec_minus_base"], row["prec_ci95"] = dp, ci
                combo = W_PDS * (v["pds_gen"] - b["pds_gen"]) - W_NMAE * (v["nmae_gen"] - b["nmae_gen"])
                row["combined_minus_base"], row["combined_ci95"] = boot(combo[np.isfinite(combo)], brng)
            rows_out.append(row)
        meta.append({"held_out": held, "inputs": inputs, "cd4_se_factor": args.cd4_se_factor, "test_targets": T,
                     "test_pool": len(test_pool), "estimation_targets": len(est),
                     "pair_targets_median_expressed": float(np.median(pair_t[gate])),
                     "sigma2_median_atlas": float(np.median(sigma2[gate])), "tau2_median_atlas": float(np.median(tau2[gate])),
                     "sigma2_median_panel": float(np.median(s2_panel[gate])), "tau2_median_panel": float(np.median(t2_panel[gate])),
                     "share_median_atlas": float(np.median(share[gate])),
                     "agree_quantiles": [float(q) for q in np.quantile(agree, [0.1, 0.25, 0.5, 0.75, 0.9])],
                     "agree_pooled_ratio": pooled_ratio,
                     "program_targets": int(n_prog),
                     "program_variance_first": {str(k): float(explained[:k].sum()) for k in args.programs},
                     "cis_targets_with_a_neighbour": int((np.abs(cis) > 0).any(axis=1).sum())})
        pd.DataFrame(rows_out).to_csv(args.out / "summary_partial.csv", index=False)
        log(f"{held}: done")
        del arms, per, y_true, z_true, sig, tabs, cis, tx, base
    pd.DataFrame(rows_out).to_csv(args.out / "summary.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "atlante_2026-09-26/atlas_bench.py", "claim_type": "effect-space and generator-model "
                   "proxies on thousands of held-out targets outside the panel; regime C; not VCC scores",
                   "args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
                   "runs": meta, "rows": rows_out}, fh, indent=1, default=float)
    pd.set_option("display.width", 250)
    s = pd.DataFrame(rows_out)
    cols = ["held_out", "arm", "test_targets", "pds_gen_minus_base", "nmae_gen_minus_base", "combined_minus_base",
            "combined_ci95", "pds_minus_base", "prec_minus_base", "energy_ratio", "detectable_median"]
    print(s[[c for c in cols if c in s.columns]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
