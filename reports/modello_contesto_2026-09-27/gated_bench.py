"""E1 and E2 for the gated target x context model, on held-out cell-line families of the genome-wide universes.

The model (`gated.py`): y_hat = A * s(t, c) * h(g, c) * m(t, g) + k(t, g), four parameters shared by every
context, the context read only from its basal expression. Here m is the transfer with the genes the universes
cannot estimate excluded (the `excl` arm, which passed the t23 ablation, reports/ablazione_t23_2026-09-27/), so
the gates model what the context adds on top of the current best form. Two tests (design in
`agenti/disegno_claude2.md`, section 3):
* **E1**, one family held out at a time (truths `k562`, `cd4_mix`, `orion_hct116`, `orion_hek293t`; a held-out
  Orion line takes its family out): `gated` against `excl`, against its blind version (every context given the
  training-source average) and against a swapped context, with the combined proxy 0.36 dPDS_gen - 0.27
  dnMAE_gen of `share_panel_bench.py` (same generator model and seeds). Every arm but `transfer` is rescaled
  with `match_detectable` to the transfer's detectable genes, as in the atlas, so arms differ in direction,
  not in overall amplitude. The test targets' own genes are left out of the PDS terms, as in the atlas.
* **E2**, two contexts held out together (`orion_hct116` with `orion_hek293t`; `cd4_Rest` with `cd4_Stim48hr`):
  per target, the weighted correlation between the predicted difference pred_1 - pred_2 and the observed one
  y_1 - y_2, on genes farther than 5 kb from the target's TSS, after removing from both differences their mean
  over the test targets (gene by gene), so that a difference common to every target (the lines' templates)
  does not count; a permutation control pairs each target's predicted difference with another target's
  observed one. `excl` and the blind model predict no difference by construction.
The gates are fitted inside the training families only: each training family F is predicted by the transfer
from the other training families (leave one family out inside training), with the basal reference of the
features taken from those same other families; up to --fit-targets targets per family, none a test or panel
target; the target's own gene out of the loss; the amplitude of the fit is the weighted least-squares slope of
(y - k) on m. The share rho and the cis head come from training data only, with the test targets excluded.
A design whose gate fit does not converge, after up to two restarts from where L-BFGS-B stopped (a point the
restarts cannot move by more than 1e-6 of the objective counts as converged), is reported and not evaluated. Each design draws its targets and its
bootstrap and permutation samples from its own seed (SEED, design index), so a run of a subset (--designs)
repeats the full run's draws. Every E1 contrast and E2 correlation is also reported on the **strong stratum**:
the test targets in the top quartile of significant genes in the held-out truth (|Z| >= 3 on genes detectable in
A/B/C, own gene out; for E2 the smaller of the two truths' counts), the kind of target the VCC organisers chose.
The selection uses the truth only and is the same for every arm.
Proxies against public sources, not VCC scores.

    scripts/py.cmd reports/modello_contesto_2026-09-27/gated_bench.py --out <new dir> \
        --universe k562=<dir> --universe cd4_mix=<dir> --universe cd4_Rest=<dir> --universe cd4_Stim48hr=<dir> \
        --universe orion_hct116=<dir> --universe orion_hek293t=<dir>   [--smoke]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "reports" / "quota_condivisa_2026-09-27"))
sys.path.insert(0, str(HERE))

from share_panel_bench import (  # noqa: E402
    AMPLITUDE, DATA, SEED, W_NMAE, W_PDS, Universe, add_cis, boot, cis_prior, detectable_threshold, family,
    load_coordinates, match_detectable, mix, official_axis, pds_proxy, rank_pds, realise, shared_share,
)

import gated  # noqa: E402

E1_TRUTHS = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]
E2_PAIRS = [("orion_hct116", "orion_hek293t"), ("cd4_Rest", "cd4_Stim48hr")]
TRAIN_SOURCES = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]   # the CD4 conditions are truths only
NEAR_BP = 5000
N_PERM = 200


def rows(uni: Universe, targets: list[str], G: int) -> tuple[np.ndarray, np.ndarray]:
    """raw and SE of ``targets`` in ``uni`` (NaN rows where it lacks a target)."""
    raw = np.full((len(targets), G), np.nan, dtype=np.float32)
    se = np.full((len(targets), G), np.nan, dtype=np.float32)
    have = [t for t in targets if t in uni.targets]
    if have:
        tab = uni.table(have)
        ix = tab.index()
        for i, t in enumerate(targets):
            if t in ix:
                raw[i], se[i] = tab.raw[ix[t]], tab.se[ix[t]]
    return raw, se


def transfer(unis: dict, sources: list[str], targets: list[str]) -> np.ndarray:
    """The production transfer (equal weights, gamma 1), unscaled; NaN where no source measured a pair."""
    tables = []
    for n in sources:
        have = [t for t in targets if t in unis[n].targets]
        if have:
            tables.append(unis[n].table(have))
    m, d = mix(tables, targets, weights={t.name: 1.0 for t in tables}, gamma=1.0, reliability_scale=100.0)
    return np.where(d > 0, m, np.nan).astype(np.float32)


def near_mask(targets: list[str], axis: np.ndarray, coords: pd.DataFrame) -> np.ndarray:
    """True where a gene lies within NEAR_BP of the target's TSS on its chromosome, or is the target."""
    chrom = coords.reindex(axis)["chrom"].astype(str).to_numpy()
    tss = coords.reindex(axis)["tss"].to_numpy(dtype=float)
    out = np.zeros((len(targets), axis.size), dtype=bool)
    col = {g: i for i, g in enumerate(axis)}
    for i, t in enumerate(targets):
        if t in col:
            out[i, col[t]] = True
        if t in coords.index:
            c, p = str(coords.at[t, "chrom"]), float(coords.at[t, "tss"])
            out[i] |= (chrom == c) & (np.abs(tss - p) <= NEAR_BP)
    return out


def weighted_corr(a: np.ndarray, b: np.ndarray, w: np.ndarray) -> float:
    ok = np.isfinite(a) & np.isfinite(b) & (w > 0)
    if ok.sum() < 20:
        return float("nan")
    a, b, w = a[ok].astype(np.float64), b[ok].astype(np.float64), w[ok].astype(np.float64)
    ma, mb = np.average(a, weights=w), np.average(b, weights=w)
    va, vb = np.average((a - ma) ** 2, weights=w), np.average((b - mb) ** 2, weights=w)
    if va <= 0 or vb <= 0:
        return 0.0
    return float(np.average((a - ma) * (b - mb), weights=w) / np.sqrt(va * vb))


def centred(x: np.ndarray) -> np.ndarray:
    """x minus its mean over targets, gene by gene (NaN-aware)."""
    with np.errstate(invalid="ignore"):
        mean = np.nanmean(np.where(np.isfinite(x), x, np.nan), axis=0)
    return x - np.nan_to_num(mean)[None, :]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", action="append", required=True, metavar="NAME=DIR")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--essential", type=Path, default=DATA / "external/K562_essential_raw_bulk_01.h5ad")
    ap.add_argument("--recipe", type=Path, default=REPO / "configs/recipes/t22.json")
    ap.add_argument("--test-targets", type=int, default=1000)
    ap.add_argument("--fit-targets", type=int, default=400)
    ap.add_argument("--max-estimation-targets", type=int, default=6000)
    ap.add_argument("--cd4-se-factor", type=float, default=2.0)
    ap.add_argument("--tau2", type=float, default=0.01)
    ap.add_argument("--lam", type=float, default=1.0)
    ap.add_argument("--l-min", type=float, default=float(np.log1p(5.0)))
    ap.add_argument("--smoke", action="store_true", help="60 test, 120 fit, 400 estimation targets; one design each")
    ap.add_argument("--designs", default=None,
                    help="comma-separated subset, e.g. E1:k562,E2:orion_hct116+orion_hek293t (default: all)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.smoke:
        args.test_targets, args.fit_targets, args.max_estimation_targets = 60, 120, 400
    args.out.mkdir(parents=True, exist_ok=False)
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:7.0f}s] {m}", flush=True)  # noqa: E731

    axis = np.asarray(official_axis().symbols)
    G = axis.size
    col = {g: i for i, g in enumerate(axis)}
    panel = set(pd.read_csv(args.panel).iloc[:, 0].astype(str))
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    with h5py.File(args.essential, "r") as fh:
        labels = [s.decode() for s in fh["obs/gene_transcript"][:]]
    essential = {lab.split("_")[1] for lab in labels if "non-targeting" not in lab}
    cis_spec = json.loads(args.recipe.read_text(encoding="utf-8"))["cis"]
    pairs = pd.read_csv(REPO / cis_spec["pairs"])
    coords = load_coordinates(args.coords)
    unis = {}
    for spec in args.universe:
        name, _, folder = spec.partition("=")
        unis[name] = Universe(name, Path(folder))
        log(f"universe {name}: {len(unis[name].targets)} targets")
    cpm_abc = basal[["A", "B", "C"]].mean(axis=1).to_numpy()
    xa = 0.05 * cpm_abc
    w_eval = (xa / (1.0 + xa)).astype(np.float32)
    gate_abc = cpm_abc >= 5.0
    thr = detectable_threshold(cpm_abc)
    lvec = {n: np.log1p(basal[n].to_numpy(dtype=np.float32)) for n in unis}

    designs = [("E1", (h,)) for h in E1_TRUTHS] + [("E2", p) for p in E2_PAIRS]
    labels = [f"{k}:{'+'.join(t)}" for k, t in designs]
    if args.smoke:
        chosen = ["E1:orion_hek293t", f"E2:{'+'.join(E2_PAIRS[0])}"]
    elif args.designs:
        chosen = [s.strip() for s in args.designs.split(",") if s.strip()]
        unknown = sorted(set(chosen) - set(labels))
        if unknown:
            raise SystemExit(f"unknown designs {unknown}; choose among {labels}")
    else:
        chosen = labels
    summary, e2_rows, params_rows = [], [], []
    for di, ((kind, truths), label) in enumerate(zip(designs, labels)):
        if label not in chosen:
            continue
        rng = np.random.default_rng([SEED, di])
        if any(t not in unis for t in truths):
            log(f"{kind} {truths}: a truth universe is missing, skipped")
            continue
        fams_out = {family(t) for t in truths}
        train = [n for n in TRAIN_SOURCES if n in unis and family(n) not in fams_out]
        if len(train) < 2:
            log(f"{kind} {truths}: fewer than two training sources, skipped")
            continue
        count = {}
        for n in train:
            for t in unis[n].targets:
                count[t] = count.get(t, 0) + 1
        pool = sorted(t for t in set.intersection(*(unis[t].targets for t in truths))
                      if count.get(t, 0) >= 2 and t not in panel and t not in essential
                      and (kind == "E1" or t in coords.index))
        test = sorted(rng.choice(pool, size=min(args.test_targets, len(pool)), replace=False).tolist())
        tset = set(test)
        excluded = panel | tset
        rho, rinfo = shared_share(unis, train, excluded, basal, G, args.cd4_se_factor,
                                  args.max_estimation_targets, rng)
        keep_gene = rho > 0                                   # the `excl` form: genes the universes can estimate
        rho_gate = np.where(keep_gene, rho, np.nan).astype(np.float32)
        cis_model = cis_prior(pairs, sorted(excluded))

        def cis_for(targets: list[str]) -> np.ndarray:
            k = np.zeros((len(targets), G), dtype=np.float32)
            add_cis(k, np.zeros(k.shape, dtype=bool), targets, axis, cis_model, coords,
                    int(cis_spec["max_distance_bp"]), float(cis_spec.get("scale", 1.0)))
            return k

        log(f"{kind} {truths}: train {train}, {len(test)} test targets of {len(pool)}; rho {rinfo}")

        # ---- fit the gates inside training: each family F against the transfer from the other families
        ctx_names = list(train) + list(truths)
        context_l = np.vstack([lvec[n] for n in ctx_names])
        fams = []
        for fname in sorted({family(n) for n in train}):
            members = [n for n in train if family(n) == fname]
            others = [n for n in train if family(n) != fname]
            if not others:
                continue
            source_o = np.vstack([lvec[n] for n in others])
            for n in members:
                cand = sorted(t for t in unis[n].targets if t not in excluded and t not in essential
                              and any(t in unis[o].targets for o in others))
                if not cand:
                    continue
                fit_t = sorted(rng.choice(cand, size=min(args.fit_targets, len(cand)), replace=False).tolist())
                y, se = rows(unis[n], fit_t, G)
                tg = np.array([col.get(t, -1) for t in fit_t], dtype=np.int64)
                own = np.zeros(y.shape, dtype=bool)
                own[np.arange(len(fit_t))[tg >= 0], tg[tg >= 0]] = True
                y = np.where(np.isfinite(se) & (se > 0) & ~own, y, np.nan).astype(np.float32)
                se = np.where(np.isfinite(y), se, 0.0).astype(np.float32)
                m = np.where(keep_gene[None, :], transfer(unis, others, fit_t), np.nan).astype(np.float32)
                meas = np.array([[t in unis[s].targets for t in fit_t] for s in others], dtype=bool)
                feats = gated.gate_features(context_l, source_o, tg, meas, rho_gate, l_min=args.l_min)
                fams.append(gated.Family(y=y, se=se, m=m, k=cis_for(fit_t), features=feats,
                                         context=ctx_names.index(n)))
        x = 0.05 * np.nanmean(np.vstack([basal[n].to_numpy(dtype=float) for n in train]), axis=0)
        gw = np.nan_to_num(x / (1.0 + x)).astype(np.float32)
        num = den = 0.0
        for f in fams:
            use = np.isfinite(f.y) & np.isfinite(f.m)
            w = np.where(use, gw[None, :] / (f.se ** 2 + args.tau2), 0.0)
            num += float(np.sum(w * np.where(use, (f.y - f.k) * f.m, 0.0)))
            den += float(np.sum(w * np.where(use, f.m * f.m, 0.0)))
        a_fit = num / den if den > 0 else 1.0
        res = gated.fit(fams, gw, A=a_fit, tau2=args.tau2, lam=args.lam)
        # L-BFGS-B stops with ABNORMAL when its line search cannot lower an objective summed from float32 blocks
        # (ftol 1e-12): restart from where it stopped; two restarts that change the objective by at most 1e-6 of
        # its value mean a stationary point at numerical precision, accepted as converged (amendment before r1)
        restarts, stationary = 0, False
        while not res.success and "ABNORMAL" in str(res.message) and restarts < 2:
            before = float(res.fun)
            res = gated.fit(fams, gw, A=a_fit, tau2=args.tau2, lam=args.lam, initial=res.x)
            restarts += 1
            if not res.success and abs(before - float(res.fun)) <= 1e-6 * abs(before):
                stationary = True
                break
        converged = bool(res.success) or stationary
        p = res.x
        params_rows.append({"design": kind, "truths": "+".join(truths), "train": "+".join(train),
                            "fit_families": len(fams), "a_fit": a_fit, "alpha1": p[0], "alpha2": p[1],
                            "beta1": p[2], "beta3": p[3], "success": bool(res.success), "message": str(res.message),
                            "restarts": restarts, "stationary": stationary, "converged": converged,
                            "grad_max": float(np.max(np.abs(res.jac))) if getattr(res, "jac", None) is not None else None,
                            "objective": float(res.fun)})
        log(f"{kind} {truths}: A_fit {a_fit:.3f}, params {np.round(p, 4).tolist()}, success {res.success}, "
            f"restarts {restarts}, stationary {stationary}")
        if not converged:
            log(f"{kind} {truths}: the gate fit did not converge; design not evaluated (it does not pass)")
            continue

        # ---- predictions for the held-out truth(s); every arm but `transfer` rescaled to its detectable genes
        m_h = transfer(unis, train, test)
        k_h = cis_for(test)
        tg = np.array([col.get(t, -1) for t in test], dtype=np.int64)
        source_l = np.vstack([lvec[n] for n in train])
        meas = np.array([[t in unis[s].targets for t in test] for s in train], dtype=bool)
        feats = gated.gate_features(context_l, source_l, tg, meas, rho_gate, l_min=args.l_min)
        tx = np.nan_to_num(m_h) * AMPLITUDE
        base = (tx + k_h).astype(np.float32)
        m_excl = np.where(keep_gene[None, :], m_h, np.nan).astype(np.float32)
        zero_k = np.zeros_like(k_h)

        def rescaled(signal: np.ndarray) -> np.ndarray:
            arm, _ = match_detectable(np.nan_to_num(signal), base, thr, gate_abc, offset=k_h)
            return arm.astype(np.float32)

        def gated_signal(context: int, blind: bool = False) -> np.ndarray:
            return gated.predict(p, m_excl, zero_k, feats, context, A=1.0, blind=blind)

        own_cols = tg[tg >= 0]
        if kind == "E1":
            h = truths[0]
            y, se = rows(unis[h], test, G)
            swap_ctx = int(rng.integers(0, len(train)))
            arms = {"transfer": base, "excl": rescaled(tx * keep_gene[None, :]), "share": rescaled(tx * rho[None, :]),
                    "gated": rescaled(gated_signal(ctx_names.index(h))),
                    "gated_blind": rescaled(gated_signal(ctx_names.index(h), blind=True)),
                    "gated_swap": rescaled(gated_signal(swap_ctx))}
            keep = np.ones(G, dtype=bool)
            keep[own_cols] = False                            # test targets' own genes out of the PDS terms
            Zt = y / np.where(np.isfinite(se) & (se > 0), se, np.nan)
            own = np.zeros(y.shape, dtype=bool)
            own[np.arange(len(test))[tg >= 0], tg[tg >= 0]] = True
            sig = np.isfinite(y) & (np.abs(np.nan_to_num(Zt)) >= 3) & gate_abc[None, :] & ~own
            strength = sig.sum(axis=1)
            strong = strength >= np.quantile(strength, 0.75)
            log(f"E1 {h}: strong stratum {int(strong.sum())} targets (>= {np.quantile(strength, 0.75):.0f} "
                f"significant genes; median over test targets {np.median(strength):.0f})")
            observed = np.abs(base) > 0
            per = {}
            for name, E in arms.items():
                pds_gen, nmae_gen = [], []
                for c in ("A", "B", "C"):
                    cpm = basal[c].to_numpy(dtype=float)
                    xc = 0.05 * cpm
                    lv = keep & (cpm > 0)
                    Tl = (np.log1p(xc * np.exp(np.clip(np.nan_to_num(y), -20, 20))) - np.log1p(xc))[:, lv]
                    for seed in (1, 2, 3):
                        noisy, _, _ = realise(E, cpm, observed | (np.abs(E) > 0), np.random.default_rng([seed, ord(c)]))
                        D = (np.log1p(xc * np.exp(np.clip(noisy, -20, 20))) - np.log1p(xc))[:, lv]
                        pds_gen.append(rank_pds(D, Tl))
                        err = np.where(sig, np.abs(noisy - np.nan_to_num(y)), 0.0).sum(axis=1)
                        ref = np.where(sig, np.abs(np.nan_to_num(y)), 0.0).sum(axis=1)
                        nmae_gen.append(np.where(ref > 0, err / np.maximum(ref, 1e-12), np.nan))
                per[name] = {"pds": pds_proxy(E, y, w_eval, own_cols), "pds_gen": np.mean(pds_gen, axis=0),
                             "nmae_gen": np.nanmean(nmae_gen, axis=0),
                             "energy": float((np.asarray(E, np.float64) ** 2).sum() / (np.asarray(base, np.float64) ** 2).sum())}
            combo = {k: W_PDS * v["pds_gen"] - W_NMAE * v["nmae_gen"] for k, v in per.items()}
            brng = np.random.default_rng([SEED, di, 1])
            contrasts = [(n, "transfer") for n in arms if n != "transfer"] + \
                        [("gated", "excl"), ("gated", "gated_blind"), ("gated", "gated_swap")]
            for a, b in contrasts:
                d = combo[a] - combo[b]
                dp = np.asarray(per[a]["pds"], float) - np.asarray(per[b]["pds"], float)
                for stratum, sel in (("all", np.ones(len(test), dtype=bool)), ("strong", strong)):
                    est, ci = boot(d[sel & np.isfinite(d)], brng)
                    pest, pci = boot(dp[sel & np.isfinite(dp)], brng)
                    summary.append({"held_out": h, "stratum": stratum, "arm": a, "against": b,
                                    "targets": int((sel & np.isfinite(d)).sum()), "combined_minus": est,
                                    "combined_ci95": ci, "pds_minus": pest, "pds_ci95": pci,
                                    "energy_ratio": per[a]["energy"]})
            log(f"E1 {h}: evaluated")
        else:
            h1, h2 = truths
            y1, se1 = rows(unis[h1], test, G)
            y2, se2 = rows(unis[h2], test, G)
            own2 = np.zeros(y1.shape, dtype=bool)
            own2[np.arange(len(test))[tg >= 0], tg[tg >= 0]] = True

            def n_sig(y: np.ndarray, se: np.ndarray) -> np.ndarray:
                z = y / np.where(np.isfinite(se) & (se > 0), se, np.nan)
                return (np.isfinite(y) & (np.abs(np.nan_to_num(z)) >= 3) & gate_abc[None, :] & ~own2).sum(axis=1)

            strength = np.minimum(n_sig(y1, se1), n_sig(y2, se2))
            strong = strength >= np.quantile(strength, 0.75)
            log(f"E2 {h1}-{h2}: strong stratum {int(strong.sum())} targets (>= {np.quantile(strength, 0.75):.0f} "
                f"significant genes in both truths)")
            near = near_mask(test, axis, coords)
            xw = 0.05 * np.nanmean(np.vstack([basal[h1].to_numpy(dtype=float), basal[h2].to_numpy(dtype=float)]), axis=0)
            wg = np.nan_to_num(xw / (1.0 + xw)).astype(np.float32)
            obs = centred(y1 - y2)
            preds = {"gated": (gated_signal(ctx_names.index(h1)), gated_signal(ctx_names.index(h2))),
                     "gated_blind": (gated_signal(ctx_names.index(h1), True), gated_signal(ctx_names.index(h2), True)),
                     "excl": (m_excl, m_excl)}
            for ai, (name, (p1, p2)) in enumerate(preds.items()):
                raw_diff = np.nan_to_num(p1) - np.nan_to_num(p2)
                zero = bool(np.all(np.abs(raw_diff) < 1e-7))
                dpred = centred(raw_diff)
                wt = np.where(near, 0.0, wg[None, :])
                corr = np.array([weighted_corr(dpred[i], obs[i], wt[i]) for i in range(len(test))])
                for si, (stratum, sel) in enumerate((("all", np.ones(len(test), dtype=bool)), ("strong", strong))):
                    idx = np.flatnonzero(sel)
                    ok = np.isfinite(corr[idx])
                    if ok.any():
                        est, ci = boot(corr[idx][ok], np.random.default_rng([SEED, di, 2, ai, si]))
                    else:
                        est, ci = float("nan"), [float("nan"), float("nan")]
                    perm = []
                    if not zero:
                        prng = np.random.default_rng([SEED, di, 3, ai, si])
                        for _ in range(N_PERM):
                            j = idx[prng.permutation(idx.size)]         # another target's observed difference
                            cp = np.array([weighted_corr(dpred[i], obs[jj], wt[i]) for i, jj in zip(idx, j)])
                            perm.append(float(np.nanmean(cp)))
                    perm = np.asarray(perm)
                    e2_rows.append({"pair": f"{h1}-{h2}", "stratum": stratum, "arm": name, "targets": int(ok.sum()),
                                    "mean_corr": est, "ci95": ci, "predicted_difference_is_zero": zero,
                                    "perm_mean": float(perm.mean()) if perm.size else None,
                                    "perm_q975": float(np.quantile(perm, 0.975)) if perm.size else None,
                                    "perm_p": float((perm >= est).mean()) if perm.size else None})
            log(f"E2 {h1}-{h2}: evaluated")
        # partial copies after every design, so an interruption keeps what was measured
        pd.DataFrame(summary).to_csv(args.out / "summary_partial.csv", index=False)
        pd.DataFrame(e2_rows).to_csv(args.out / "e2_partial.csv", index=False)
        pd.DataFrame(params_rows).to_csv(args.out / "params_partial.csv", index=False)
    pd.DataFrame(summary).to_csv(args.out / "summary.csv", index=False)
    pd.DataFrame(e2_rows).to_csv(args.out / "e2.csv", index=False)
    pd.DataFrame(params_rows).to_csv(args.out / "params.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "modello_contesto_2026-09-27/gated_bench.py", "args": vars(args),
                   "claim_type": "effect-space and generator-model proxies against held-out public sources; not VCC scores",
                   "summary": summary, "e2": e2_rows, "params": params_rows}, fh, indent=1, default=str)
    pd.set_option("display.width", 250)
    if summary:
        print(pd.DataFrame(summary)[["held_out", "stratum", "arm", "against", "targets", "combined_minus", "combined_ci95",
                                     "pds_minus", "energy_ratio"]].round(4).to_string(index=False))
    if e2_rows:
        print(pd.DataFrame(e2_rows).to_string(index=False))
    print(pd.DataFrame(params_rows).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
