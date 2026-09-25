"""CRISPRi cis head: does an explicit model of promoter-proximal repression add to transfer?

Biology. dCas9-KRAB bound at a target's TSS spreads repressive chromatin over roughly 1-2 kb, so
genes whose TSS sits near the target's (bidirectional promoters above all) go down too, in any
context and whatever the target does. CP-0020 section 3.5 measured it on the K562 genome-wide
pseudobulk (median log2FC about -0.5 within 1 kb, about 0 beyond 20 kb) and found it transfers to
HepG2 (sign concordance 97.5% where |K562 log2FC| > 0.5). No submission has modelled it: the
transferred effects carry it only where a source measured the pair, averaged, centred and
multiplied by the amplitude chosen for the trans part.

Prior. Mean ln fold change by TSS distance bin and orientation (divergent or not), fitted on the
K562 genome-wide pairs of reports/cis_2026-09-17/k562_neighbour_pairs.csv whose target is NOT a
panel target, so no panel target is seen by the prior (it still shares K562's context when K562
is the held-out source).

Leave-one-source-family-out, the loader and pooling of sweep_v2.py (stage 100's own code). Arms,
each on the t16 shape (raw effects x 0.788) and the t19 shape (shrunk x 1.576):
  base          the transferred effects alone;
  cis_replace   neighbour genes within D get the prior, not multiplied by the amplitude;
  cis_min       the more negative of transferred value and prior;
  cis_fill      the prior only where no source measured the pair;
  cis_add       transferred value plus prior;
  cis_shuffled  control: each target gets the prior on another target's neighbour set;
and cis_only (the prior alone, nothing transferred). D = 2, 5, 10 kb.

Metrics per held-out source, one target set for every arm, paired bootstrap over targets:
  PDS proxy (analyze.pds_proxy: log1p weights of A/B/C, panel genes excluded);
  reach proxy: held-out genes with |raw/se| >= 3 at >= 5 CPM in A/B/C, target gene excluded,
  ranked by |prediction| (the scorer's sort key, abs_log2_fold_change); purity = share of the
  ranked prefix with the held-out sign; k* = deepest prefix with purity >= 0.9; reach = k*/N;
  fidelity proxy (analyze.fidelity_proxy) precision and yield at the top 200;
  weighted squared-error ratio against 'no change' (mse_tradeoff.py weights, panel excluded).
Effect-space proxies against noisy public sources: not VCC scores.

    scripts/py.cmd reports/modulo_cis_2026-09-26/cis_bench.py --out reports/modulo_cis_2026-09-26/r1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BENCH = REPO / "reports" / "banco_varianti_2026-09-25"
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(REPO / "src"))

from analyze import DATA, FAMILY, SOURCES, fidelity_proxy, pds_proxy  # noqa: E402
from sweep_v2 import pooled, stage100  # noqa: E402

LN2 = float(np.log(2.0))
BINS = [0, 500, 1000, 2000, 5000, 10000, 20000, 50000]
DMAX = (2000, 5000, 10000)
SHAPES = {"t16": ("raw", 0.788), "t19": ("shrunk", 1.576)}
FLOOR = 0.9
SEED = 20260926
N_BOOT = 2000


def orientation(t_strand: int, t_tss: int, g_strand: int, g_tss: int) -> str:
    if t_strand == g_strand:
        return "tandem"
    if (t_strand == 1 and g_tss < t_tss) or (t_strand == -1 and g_tss > t_tss):
        return "divergent"
    return "convergent"


def load_coords(path: Path) -> pd.DataFrame:
    co = pd.read_csv(path, sep="\t", usecols=["symbol", "chrom", "strand", "tss"])
    return co.drop_duplicates("symbol").set_index("symbol")


def neighbours(targets, co: pd.DataFrame, col: dict, dmax: int) -> pd.DataFrame:
    """Axis genes whose TSS lies within dmax of each target's TSS (target itself excluded)."""
    on_axis = co[co.index.isin(list(col))]
    by_chrom = {c: df.sort_values("tss") for c, df in on_axis.groupby("chrom")}
    out = []
    for t in targets:
        if t not in co.index:
            continue
        c, s, p = co.at[t, "chrom"], int(co.at[t, "strand"]), int(co.at[t, "tss"])
        df = by_chrom.get(c)
        if df is None:
            continue
        tss = df["tss"].to_numpy()
        lo, hi = np.searchsorted(tss, p - dmax, "left"), np.searchsorted(tss, p + dmax, "right")
        strands = df["strand"].to_numpy()
        for g, gs, gp in zip(df.index[lo:hi], strands[lo:hi], tss[lo:hi]):
            if g != t:
                out.append((t, col[g], g, abs(int(gp) - p), orientation(s, p, int(gs), int(gp))))
    return pd.DataFrame(out, columns=["target", "col", "gene", "dist", "orient"])


def fit_prior(pairs_csv: Path, co: pd.DataFrame, panel: set) -> tuple[pd.DataFrame, dict]:
    pr = pd.read_csv(pairs_csv)
    n_all = len(pr)
    pr = pr[~pr["target"].isin(panel)]
    pr = pr[pr["target"].isin(co.index) & pr["gene"].isin(co.index)].copy()
    pr["dist"] = [abs(int(co.at[g, "tss"]) - int(co.at[t, "tss"])) for t, g in zip(pr["target"], pr["gene"])]
    pr["orient"] = [orientation(int(co.at[t, "strand"]), int(co.at[t, "tss"]), int(co.at[g, "strand"]),
                                int(co.at[g, "tss"])) for t, g in zip(pr["target"], pr["gene"])]
    pr["div"] = pr["orient"] == "divergent"
    pr = pr[pr["dist"] < BINS[-1]]
    pr["bin"] = np.searchsorted(BINS, pr["dist"].to_numpy(), side="right") - 1
    rows, table = [], {}
    for b in range(len(BINS) - 1):
        sub = pr[pr["bin"] == b]
        for div in (True, False):
            s = sub[sub["div"] == div]["log2fc"]
            rows.append({"bin": f"[{BINS[b]}, {BINS[b + 1]})", "divergent": div, "n": int(s.size),
                         "mean_log2": float(s.mean()) if s.size else np.nan,
                         "median_log2": float(s.median()) if s.size else np.nan,
                         "share_below_minus_half": float((s < -0.5).mean()) if s.size else np.nan})
            # groups under 30 pairs fall back to the bin's pooled mean
            val = s.mean() if s.size >= 30 else sub["log2fc"].mean()
            table[(b, div)] = float(val) * LN2
    meta = {"pairs_in_file": n_all, "pairs_used_non_panel_targets": int(len(pr)),
            "targets_used": int(pr["target"].nunique())}
    return pd.DataFrame(rows), {"table": table, "meta": meta}


def prior_values(nb: pd.DataFrame, table: dict) -> np.ndarray:
    b = np.searchsorted(BINS, nb["dist"].to_numpy(), side="right") - 1
    return np.array([table[(int(x), o == "divergent")] for x, o in zip(b, nb["orient"])], dtype=np.float64)


def reach_proxy(P, T, Z, gate, tcols) -> np.ndarray:
    out = np.full(P.shape[0], np.nan)
    for i in range(P.shape[0]):
        sig = gate & np.isfinite(Z[i]) & (np.abs(Z[i]) >= 3.0) & np.isfinite(T[i])
        if tcols[i] >= 0:
            sig[tcols[i]] = False
        idx = np.flatnonzero(sig)
        if idx.size == 0:
            continue
        order = idx[np.argsort(-np.abs(P[i, idx]), kind="stable")]
        match = (np.sign(P[i, order]) == np.sign(T[i, order])) & (P[i, order] != 0)
        purity = np.cumsum(match) / np.arange(1, idx.size + 1)
        ok = np.flatnonzero(purity >= FLOOR)
        out[i] = (ok[-1] + 1) / idx.size if ok.size else 0.0
    return out


def truth_z(cache: Path, held: str, truth, targets) -> np.ndarray:
    """raw / se of the held-out source; cd4_mix has no SE, so it is rebuilt from its conditions."""
    tidx = truth.index()
    rows = np.array([tidx[t] for t in targets])
    if held != "cd4_mix":
        return (truth.raw[rows] / truth.se[rows]).astype(np.float32)
    var = np.zeros((len(targets), truth.raw.shape[1]))
    n = np.zeros_like(var)
    for part in json.loads(json.dumps(truth.meta.get("from", []))):
        tab = stage100.load_table(cache, part, "raw")
        pidx = tab.index()
        for i, t in enumerate(targets):
            if t in pidx:
                se = tab.se[pidx[t]].astype(np.float64)
                ok = np.isfinite(se)
                var[i, ok] += se[ok] ** 2
                n[i, ok] += 1
    se = np.where(n > 0, np.sqrt(var) / np.maximum(n, 1), np.nan)
    return (truth.raw[rows] / se).astype(np.float32)


def boot(diff, rng):
    diff = diff[np.isfinite(diff)]
    idx = rng.integers(0, diff.size, size=(N_BOOT, diff.size))
    means = diff[idx].mean(axis=1)
    return float(diff.mean()), [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "interim/basal_cpm_by_context.csv")
    ap.add_argument("--genes", type=Path, default=DATA / "raw/controls/gene_names.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--pairs", type=Path, default=REPO / "reports/cis_2026-09-17/k562_neighbour_pairs.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)

    axis = pd.read_csv(args.genes)["gene_name"].astype(str).to_numpy()
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    col = {g: i for i, g in enumerate(axis)}
    panel_cols = np.array([col[g] for g in panel if g in col])
    keep = np.ones(axis.size, dtype=bool)
    keep[panel_cols] = False
    cpm = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)[["A", "B", "C"]].mean(axis=1).to_numpy()
    x = 0.05 * cpm
    w = (x / (1.0 + x)).astype(np.float32)
    gate = cpm >= 5.0

    co = load_coords(args.coords)
    prior_tab, prior = fit_prior(args.pairs, co, set(panel))
    prior_tab.to_csv(args.out / "prior_k562_non_panel.csv", index=False)
    print(prior_tab.round(3).to_string(), flush=True)
    nb_all = neighbours(panel, co, col, max(DMAX))
    nb_all["prior_ln"] = prior_values(nb_all, prior["table"])
    nb_all.to_csv(args.out / "panel_neighbours_10kb.csv", index=False)

    rng_shuf = np.random.default_rng(SEED)
    summary, pair_diag, per_target_rows = [], [], []
    for held in SOURCES:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = stage100.load_table(args.cache, held, "raw")
        tidx = truth.index()
        base_t = [t for t in panel if t in tidx]
        trans = {}
        for shape, (effect, amp) in SHAPES.items():
            eff, den = pooled(args.cache, preds, base_t, effect)
            trans[shape] = ((eff * amp).astype(np.float32), den)
        ok = np.all([np.abs(e).sum(axis=1) > 0 for e, _ in trans.values()], axis=0)
        targets = [t for t, o in zip(base_t, ok) if o]
        T = truth.raw[np.array([tidx[t] for t in targets])].astype(np.float32)
        Z = truth_z(args.cache, held, truth, targets)
        tcols = np.array([col.get(t, -1) for t in targets])
        trow = {t: i for i, t in enumerate(targets)}
        valid = np.isfinite(T) & keep[None, :]
        Tw = np.where(valid, T * w, 0.0)
        null_t = (Tw.astype(np.float64) ** 2).sum(axis=1)

        def metrics(P):
            pds = pds_proxy(P, T, w, panel_cols)
            reach = reach_proxy(P, T, Z, gate, tcols)
            fid = fidelity_proxy(P, T, Z, gate, tcols)
            Pw = np.where(valid, P * w, 0.0)
            err_t = ((Tw - Pw).astype(np.float64) ** 2).sum(axis=1)
            return pds, reach, fid, err_t

        # neighbour sets on this target list
        per_d = {}
        for d in DMAX:
            nb = nb_all[(nb_all["dist"] < d) & nb_all["target"].isin(trow)]
            ri = np.array([trow[t] for t in nb["target"]], dtype=int)
            ci = nb["col"].to_numpy(dtype=int)
            pv = nb["prior_ln"].to_numpy()
            # shuffled control: permute whole neighbour sets among targets that have one
            owners = sorted(set(ri.tolist()))
            perm = list(owners)
            for _ in range(50):
                rng_shuf.shuffle(perm)
                if all(a != b for a, b in zip(owners, perm)):
                    break
            remap = dict(zip(owners, perm))
            ri_shuf = np.array([remap[r] for r in ri], dtype=int)
            per_d[d] = (ri, ci, pv, ri_shuf, len(owners))

        # diagnostics at cis pairs within 2 kb: is the transferred value already there?
        ri, ci, pv, _, n_own = per_d[2000]
        tv = T[ri, ci]
        m = np.isfinite(tv)
        for shape in SHAPES:
            E = trans[shape][0][ok]
            pvl = E[ri, ci]
            pair_diag.append({"held_out": held, "shape": shape, "pairs_2kb": int(ri.size), "pairs_measured": int(m.sum()),
                              "targets_with_pair": n_own, "truth_mean_ln": float(np.nanmean(tv)),
                              "truth_median_ln": float(np.nanmedian(tv)),
                              "transfer_mean_ln": float(pvl[m].mean()), "transfer_zero_share": float((pvl[m] == 0).mean()),
                              "prior_mean_ln": float(pv[m].mean()),
                              "corr_transfer_truth": float(np.corrcoef(pvl[m], tv[m])[0, 1]),
                              "sign_agree_transfer": float((np.sign(pvl[m]) == np.sign(tv[m])).mean()),
                              "sign_agree_prior": float((np.sign(pv[m]) == np.sign(tv[m])).mean()),
                              "truth_below_minus_0.35ln": float((tv[m] < -0.35).mean())})

        rng = np.random.default_rng(SEED)
        for shape in SHAPES:
            E = trans[shape][0][ok].astype(np.float32)
            den = trans[shape][1][ok]
            ref = metrics(E)
            arms = {"base": None}
            for d in DMAX:
                for kind in ("replace", "min", "fill", "add", "shuffled"):
                    arms[f"cis_{kind}_{d // 1000}kb"] = (kind, d)
            has_nb = np.zeros(len(targets), dtype=bool)
            has_nb[per_d[5000][0]] = True
            for name, spec in arms.items():
                if spec is None:
                    res = ref
                else:
                    kind, d = spec
                    ri, ci, pv, ri_shuf, _ = per_d[d]
                    P = E.copy()
                    if kind == "replace":
                        P[ri, ci] = pv
                    elif kind == "min":
                        P[ri, ci] = np.minimum(P[ri, ci], pv)
                    elif kind == "fill":
                        miss = den[ri, ci] == 0
                        P[ri[miss], ci[miss]] = pv[miss]
                    elif kind == "add":
                        P[ri, ci] = P[ri, ci] + pv
                    elif kind == "shuffled":
                        P[ri_shuf, ci] = pv
                    res = metrics(P)
                    del P
                pds, reach, fid, err_t = res
                row = {"held_out": held, "shape": shape, "arm": name, "targets": len(targets),
                       "pds_proxy": float(np.mean(pds)), "reach_proxy": float(np.nanmean(reach)),
                       "prec_200": float(np.nanmean(fid["prec_200"])), "yield_200": float(np.nanmean(fid["yield_200"])),
                       "mse_ratio": float(err_t.sum() / null_t.sum())}
                for key, v, r in (("pds", pds, ref[0]), ("reach", reach, ref[1])):
                    mdiff, ci95 = boot(v - r, rng) if spec is not None else (0.0, [0.0, 0.0])
                    row[f"{key}_minus_base"] = mdiff
                    row[f"{key}_minus_base_ci95"] = ci95
                    row[f"{key}_minus_base_nb_targets"] = float(np.nanmean((v - r)[has_nb])) if spec is not None else 0.0
                summary.append(row)
                if spec is None or name in ("cis_replace_5kb", "cis_min_5kb"):
                    for t, a, b in zip(targets, pds, reach):
                        per_target_rows.append({"held_out": held, "shape": shape, "arm": name, "target": t,
                                                "pds": float(a), "reach": float(b), "has_neighbour_5kb": bool(has_nb[trow[t]])})
        # the prior alone
        for d in DMAX:
            ri, ci, pv, _, _ = per_d[d]
            P = np.zeros_like(T)
            P[ri, ci] = pv
            pds, reach, fid, err_t = metrics(P)
            summary.append({"held_out": held, "shape": "none", "arm": f"cis_only_{d // 1000}kb", "targets": len(targets),
                            "pds_proxy": float(np.mean(pds)), "reach_proxy": float(np.nanmean(reach)),
                            "prec_200": float(np.nanmean(fid["prec_200"])) if fid["prec_200"].size else np.nan,
                            "yield_200": float(np.nanmean(fid["yield_200"])) if fid["yield_200"].size else np.nan,
                            "mse_ratio": float(err_t.sum() / null_t.sum())})
            del P
        print(held, "done", flush=True)

    s = pd.DataFrame(summary)
    s.to_csv(args.out / "summary.csv", index=False)
    pd.DataFrame(pair_diag).to_csv(args.out / "cis_pairs_2kb.csv", index=False)
    pd.DataFrame(per_target_rows).to_csv(args.out / "per_target.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "modulo_cis_2026-09-26/cis_bench.py",
                   "claim_type": "effect-space proxies against held-out public sources, one target set per held-out "
                                 "source, paired bootstrap over targets; not VCC scores",
                   "cache": str(args.cache), "seed": SEED, "n_boot": N_BOOT, "prior_meta": prior["meta"],
                   "prior_ln": {f"{BINS[b]}-{BINS[b + 1]}|{'div' if dv else 'other'}": v
                                for (b, dv), v in prior["table"].items()},
                   "pairs_2kb": pair_diag, "summary": s.to_dict("records")}, f, indent=1)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    cols = ["held_out", "shape", "arm", "pds_proxy", "pds_minus_base", "pds_minus_base_ci95", "reach_proxy",
            "reach_minus_base", "reach_minus_base_ci95", "prec_200", "mse_ratio"]
    print(pd.DataFrame(pair_diag).round(3).to_string())
    print(s[cols].round(4).to_string())


if __name__ == "__main__":
    main()
