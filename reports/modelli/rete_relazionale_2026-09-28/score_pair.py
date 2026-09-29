"""score_pred.py with extra arms from other prediction files and extra contrasts: the combined proxy of rel0 - none
(r1's network) and of cardnb - partners, paired on the same test targets.

A copy of reports/modelli/rete_contesti_2026-09-27/score_pred.py (not edited); only these are added:
* --extra NAME=SOURCE[:KEY] (repeatable): an arm NAME read from array KEY (default net) of SOURCE, a run folder
  (its pred_<truth>.npz) or an .npz path where {truth} stands for the truth context; its targets must be the
  run's, in the same order. An extra arm is treated as the network's own: the reference's values in the holes near
  the target (own gene, cis window), then rescaled to the reference's detectable genes (match_detectable);
* --contrast A:B (repeatable): contrasts added to the regime's list; E2 also covers the extra arms.
Everything else, measures and bootstrap included, is score_pred.py's. Proxies, not VCC scores.

    scripts/py.cmd reports/modelli/rete_relazionale_2026-09-28/score_pair.py --run AVG/e1_k562/rel0 \n        --extra none=AVG/e1_k562/none --contrast net:none --out <new dir> --universe k562=<dir> ...
    scripts/py.cmd reports/modelli/rete_relazionale_2026-09-28/score_pair.py --run AVG/j_k562/rel0 \n        --extra none=AVG/j_k562/none --extra "cardnb=AVG/j_k562/rel0/predrel_{truth}.npz:cardnb" \n        --contrast net:none --contrast cardnb:partners --out <new dir> --universe k562=<dir> ...

score_pred.py's description follows.

Score a train.py run with the proxies of the gated bench (reports/modelli/modello_contesto_2026-09-27/gated_bench.py).

Runs locally with the project venv (it imports gated_bench.py, hence share_panel_bench.py and cis_bench.py). For a
run folder (one design) and each truth context of it, from pred_<context>.npz (targets, net, blind, swap, and the
network's own inputs: `transfer` = m, renamed own_m, and `partners` = q):

* regime C: rebuilds the bench's reference arms for the same test targets exactly as gated_bench.py does, from the
  production sources (gated_bench.TRAIN_SOURCES) minus the families the run held out: `transfer` (equal-weight mix,
  gamma 1, x 1.576, plus the cis head) and `excl` (the same on the genes the universes can estimate, rescaled);
* regimes J and T: the test targets' outcomes are hidden, so no transfer of them is a fair baseline; the reference
  is the stage-100 fallback for unmeasured targets, `partners` = 0.1 x q + the cis head (q from the run: partners'
  profiles in the visible families, hidden targets never among them), and `cis` = the cis head alone;
* the network's arms get the reference's values on each target's own gene and cis window (the network predicts
  nothing there: those genes are out of its loss), then every arm but the reference is rescaled to the reference's
  detectable genes with the cis head outside the scale (`match_detectable`), as gated_bench does;
* E1 measures: PDS in effect space; PDS and nMAE through the trial-01 profile model and a 400-cell pseudobulk (A/B/C
  basal, 3 seeds); combined 0.36 dPDS_gen - 0.27 dnMAE_gen with a paired bootstrap; all test targets and the strong
  stratum (top quartile of |Z| >= 3 genes in the truth, own gene out);
* E2 when the run has two truth contexts: gated_bench's correlation of the predicted difference with the observed one
  on genes farther than 5 kb from the TSS, centred over the test targets, with its permutation control.
Contrasts, C: net-excl (candidate), net-blind (context use), net-swap (the right context), net-transfer, own_m-excl
(what the network's inputs add, e.g. more sources), net-own_m (what the architecture adds). J/T: net-partners,
net-blind, net-swap, net-cis, partners-cis. Proxies against public sources, not VCC scores.

    scripts/py.cmd reports/modelli/rete_contesti_2026-09-27/score_pred.py --run <train.py output> --out <new dir> \
        --universe k562=<dir> --universe cd4_mix=<dir> --universe orion_hct116=<dir> --universe orion_hek293t=<dir> \
        --universe <each truth context of the run>=<dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "reports" / "trasferimento" / "quota_condivisa_2026-09-27"))
sys.path.insert(0, str(REPO / "reports" / "modelli" / "modello_contesto_2026-09-27"))

from gated_bench import N_PERM, TRAIN_SOURCES, centred, near_mask, rows, transfer, weighted_corr  # noqa: E402
from share_panel_bench import (  # noqa: E402
    AMPLITUDE, DATA, SEED, W_NMAE, W_PDS, Universe, add_cis, boot, cis_prior, detectable_threshold, family,
    load_coordinates, match_detectable, official_axis, pds_proxy, rank_pds, realise, shared_share,
)

CONTRASTS_C = [("net", "excl"), ("net", "blind"), ("net", "swap"), ("net", "transfer"), ("own_m", "excl"),
               ("net", "own_m"), ("blind", "excl")]
CONTRASTS_NEW = [("net", "partners"), ("net", "blind"), ("net", "swap"), ("net", "cis"), ("partners", "cis")]
STRING_WEIGHT = 0.1        # the stage-100 association weight (reports/trasferimento/bersagli_nuovi_2026-09-26/)


from vcc2026.config import repo_file  # noqa: E402


def parse_extra(spec: str) -> tuple[str, str, str]:
    """NAME=SOURCE[:KEY] -> (name, source, key); a Windows drive colon is not a key separator."""
    name, sep, rest = spec.partition("=")
    if not sep or not name or not rest:
        raise SystemExit(f"--extra {spec!r}: expected NAME=SOURCE[:KEY]")
    src, colon, key = rest.rpartition(":")
    if not colon or not key or "/" in key or "\\" in key or not src or len(src) == 1:
        src, key = rest, "net"
    return name, src, key


def extra_path(source: str, truth: str) -> Path:
    p = Path(source.replace("{truth}", truth))
    return p / f"pred_{truth}.npz" if p.is_dir() else p


def load_extras(specs: list, truths: list, test: list) -> dict:
    """{truth: {name: array on the full axis}} of every --extra, checked against the run's test targets."""
    out = {t: {} for t in truths}
    for spec in specs:
        name, src, key = parse_extra(spec)
        for t in truths:
            path = extra_path(src, t)
            with np.load(path, allow_pickle=False) as z:
                if [str(x) for x in z["targets"]] != test:
                    raise SystemExit(f"--extra {name}: {path} has other test targets (or another order) than the run")
                if key not in z.files:
                    raise SystemExit(f"--extra {name}: no array {key!r} in {path} (has {z.files})")
                out[t][name] = np.asarray(z[key], dtype=np.float32)
    return out


def parse_contrasts(specs: list) -> list:
    pairs = []
    for spec in specs:
        a, sep, b = spec.partition(":")
        if not sep or not a or not b:
            raise SystemExit(f"--contrast {spec!r}: expected A:B")
        pairs.append((a, b))
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True, help="a train.py output folder")
    ap.add_argument("--universe", action="append", required=True, metavar="NAME=DIR")
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-27.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--recipe", type=Path, default=REPO / "configs/recipes/t22.json")
    ap.add_argument("--max-estimation-targets", type=int, default=6000)
    ap.add_argument("--cd4-se-factor", type=float, default=2.0)
    ap.add_argument("--extra", action="append", default=[], metavar="NAME=SOURCE[:KEY]")
    ap.add_argument("--contrast", action="append", default=[], metavar="A:B")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    added = parse_contrasts(args.contrast)
    args.out.mkdir(parents=True, exist_ok=False)
    config = json.loads((args.run / "config.json").read_text(encoding="utf-8"))
    regime = config["design"]["regime"]
    new_targets = regime in ("J", "T")
    truths = config["design"]["truth"]
    hidden_fams = {family(h) for h in config["design"]["hidden_contexts"]}
    axis = np.asarray(official_axis().symbols)
    G = axis.size
    col = {g: i for i, g in enumerate(axis)}
    panel = set(pd.read_csv(args.panel).iloc[:, 0].astype(str))
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    cis_spec = json.loads(args.recipe.read_text(encoding="utf-8"))["cis"]
    pairs = pd.read_csv(repo_file(cis_spec["pairs"]))
    coords = load_coordinates(args.coords)
    unis = {}
    for spec in args.universe:
        name, _, folder = spec.partition("=")
        unis[name] = Universe(name, Path(folder))
    missing = [t for t in truths if t not in unis]
    if missing:
        raise SystemExit(f"no --universe for the truth contexts {missing}")
    preds = {t: np.load(args.run / f"pred_{t}.npz", allow_pickle=False) for t in truths}
    test = [str(t) for t in preds[truths[0]]["targets"]]
    for t in truths[1:]:
        if [str(x) for x in preds[t]["targets"]] != test:
            raise SystemExit("the truth contexts of the run have different test targets")
    extras = load_extras(args.extra, truths, test)
    cpm_abc = basal[["A", "B", "C"]].mean(axis=1).to_numpy()
    xa = 0.05 * cpm_abc
    w_eval = (xa / (1.0 + xa)).astype(np.float32)
    gate_abc = cpm_abc >= 5.0
    thr = detectable_threshold(cpm_abc)
    rng = np.random.default_rng([SEED, 20])
    excluded = panel | set(test)
    cis_model = cis_prior(pairs, sorted(excluded))
    k_h = np.zeros((len(test), G), dtype=np.float32)
    add_cis(k_h, np.zeros(k_h.shape, dtype=bool), test, axis, cis_model, coords, int(cis_spec["max_distance_bp"]),
            float(cis_spec.get("scale", 1.0)))
    near = near_mask(test, axis, coords)
    tg = np.array([col.get(t, -1) for t in test], dtype=np.int64)
    own_cols = tg[tg >= 0]
    keep = np.ones(G, dtype=bool)
    keep[own_cols] = False
    train, rinfo = [], None
    if not new_targets:
        train = [n for n in TRAIN_SOURCES if n in unis and family(n) not in hidden_fams]
        if not train:
            raise SystemExit("no production source outside the held-out families")
        rho, rinfo = shared_share(unis, train, excluded, basal, G, args.cd4_se_factor, args.max_estimation_targets, rng)
        keep_gene = rho > 0
        tx_c = (np.nan_to_num(transfer(unis, train, test)) * AMPLITUDE).astype(np.float32)
    print(f"regime {regime}; train sources {train}; {len(test)} test targets; shared share {rinfo}", flush=True)
    contrasts = list(dict.fromkeys((CONTRASTS_NEW if new_targets else CONTRASTS_C) + added))

    summary, e2_rows = [], []
    for ti, h in enumerate(truths):
        z = preds[h]
        # the reference arm and the values the network's holes near the target take
        if new_targets:
            tx = (STRING_WEIGHT * np.nan_to_num(z["partners"])).astype(np.float32)
        else:
            tx = tx_c
        base = (tx + k_h).astype(np.float32)

        def filled(arr: np.ndarray) -> np.ndarray:
            a = np.asarray(arr, dtype=np.float32).copy()
            hole = ~np.isfinite(a) & near
            a[hole] = tx[hole]
            return np.nan_to_num(a)

        def rescaled(signal: np.ndarray) -> tuple[np.ndarray, float]:
            arm, s = match_detectable(np.nan_to_num(signal), base, thr, gate_abc, offset=k_h)
            return arm.astype(np.float32), float(s)

        scales = {}
        if new_targets:
            arms = {"partners": base, "cis": k_h.copy()}
        else:
            arms = {"transfer": base}
            arms["excl"], scales["excl"] = rescaled(tx * keep_gene[None, :])
        for name, key in (("net", "net"), ("blind", "blind"), ("swap", "swap"), ("own_m", "transfer")):
            if key in z.files and not (new_targets and key == "transfer"):
                arms[name], scales[name] = rescaled(filled(z[key]))
        for name, arr in extras[h].items():
            if name in arms:
                raise SystemExit(f"--extra {name}: the name is taken by an arm of the run")
            arms[name], scales[name] = rescaled(filled(arr))
        y, se = rows(unis[h], test, G)
        Zt = y / np.where(np.isfinite(se) & (se > 0), se, np.nan)
        own = np.zeros(y.shape, dtype=bool)
        own[np.arange(len(test))[tg >= 0], tg[tg >= 0]] = True
        sig = np.isfinite(y) & (np.abs(np.nan_to_num(Zt)) >= 3) & gate_abc[None, :] & ~own
        strength = sig.sum(axis=1)
        strong = strength >= np.quantile(strength, 0.75)
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
            base_energy = max(float((np.asarray(base, np.float64) ** 2).sum()), 1e-12)
            per[name] = {"pds": pds_proxy(E, y, w_eval, own_cols), "pds_gen": np.mean(pds_gen, axis=0),
                         "nmae_gen": np.nanmean(nmae_gen, axis=0),
                         "energy": float((np.asarray(E, np.float64) ** 2).sum()) / base_energy}
            print(f"{h}: {name} evaluated", flush=True)
        combo = {k: W_PDS * v["pds_gen"] - W_NMAE * v["nmae_gen"] for k, v in per.items()}
        brng = np.random.default_rng([SEED, 21, ti])
        for a, b in contrasts:
            if a not in per or b not in per:
                continue
            d = combo[a] - combo[b]
            dp = np.asarray(per[a]["pds"], float) - np.asarray(per[b]["pds"], float)
            for stratum, sel in (("all", np.ones(len(test), dtype=bool)), ("strong", strong)):
                ok_d, ok_p = sel & np.isfinite(d), sel & np.isfinite(dp)
                est, ci = boot(d[ok_d], brng) if ok_d.any() else (float("nan"), [float("nan")] * 2)
                pest, pci = boot(dp[ok_p], brng) if ok_p.any() else (float("nan"), [float("nan")] * 2)
                summary.append({"held_out": h, "regime": regime, "stratum": stratum, "arm": a, "against": b,
                                "targets": int(ok_d.sum()), "combined_minus": est, "combined_ci95": ci,
                                "pds_minus": pest, "pds_ci95": pci, "energy_ratio": per[a]["energy"],
                                "scale": scales.get(a)})
        pd.DataFrame(summary).to_csv(args.out / "summary_partial.csv", index=False)

    if len(truths) == 2:
        h1, h2 = truths
        y1, se1 = rows(unis[h1], test, G)
        y2, se2 = rows(unis[h2], test, G)
        own2 = np.zeros(y1.shape, dtype=bool)
        own2[np.arange(len(test))[tg >= 0], tg[tg >= 0]] = True

        def n_sig(y, se):
            zz = y / np.where(np.isfinite(se) & (se > 0), se, np.nan)
            return (np.isfinite(y) & (np.abs(np.nan_to_num(zz)) >= 3) & gate_abc[None, :] & ~own2).sum(axis=1)

        strength = np.minimum(n_sig(y1, se1), n_sig(y2, se2))
        strong = strength >= np.quantile(strength, 0.75)
        xw = 0.05 * np.nanmean(np.vstack([basal[h1].to_numpy(dtype=float), basal[h2].to_numpy(dtype=float)]), axis=0)
        wg = np.nan_to_num(xw / (1.0 + xw)).astype(np.float32)
        obs = centred(y1 - y2)
        z1, z2 = preds[h1], preds[h2]
        keys = (("net", "net"), ("blind", "blind")) + ((("own_m", "transfer"),) if not new_targets else ())
        pairs_ = {name: (z1[key], z2[key]) for name, key in keys if key in z1.files and key in z2.files}
        pairs_.update({name: (extras[h1][name], extras[h2][name]) for name in extras[h1]})
        for ai, (name, (p1, p2)) in enumerate(pairs_.items()):
            raw_diff = np.nan_to_num(p1) - np.nan_to_num(p2)
            zero = bool(np.all(np.abs(raw_diff) < 1e-7))
            dpred = centred(raw_diff)
            wt = np.where(near, 0.0, wg[None, :])
            corr = np.array([weighted_corr(dpred[i], obs[i], wt[i]) for i in range(len(test))])
            for si, (stratum, sel) in enumerate((("all", np.ones(len(test), dtype=bool)), ("strong", strong))):
                idx = np.flatnonzero(sel)
                ok = np.isfinite(corr[idx])
                if ok.any():
                    est, ci = boot(corr[idx][ok], np.random.default_rng([SEED, 22, ai, si]))
                else:
                    est, ci = float("nan"), [float("nan"), float("nan")]
                perm = []
                if not zero:
                    prng = np.random.default_rng([SEED, 23, ai, si])
                    for _ in range(N_PERM):
                        j = idx[prng.permutation(idx.size)]
                        cp = np.array([weighted_corr(dpred[i], obs[jj], wt[i]) for i, jj in zip(idx, j)])
                        perm.append(float(np.nanmean(cp)))
                perm = np.asarray(perm)
                e2_rows.append({"pair": f"{h1}-{h2}", "stratum": stratum, "arm": name, "targets": int(ok.sum()),
                                "mean_corr": est, "ci95": ci, "predicted_difference_is_zero": zero,
                                "perm_mean": float(perm.mean()) if perm.size else None,
                                "perm_q975": float(np.quantile(perm, 0.975)) if perm.size else None,
                                "perm_p": float((perm >= est).mean()) if perm.size else None})
    pd.DataFrame(summary).to_csv(args.out / "summary.csv", index=False)
    pd.DataFrame(e2_rows).to_csv(args.out / "e2.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "rete_relazionale_2026-09-28/score_pair.py", "run": str(args.run), "regime": regime,
                   "extras": [list(parse_extra(e)) for e in args.extra], "added_contrasts": added,
                   "truths": truths, "train_sources": train, "shared_share": rinfo,
                   "args": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                   "claim_type": "effect-space and generator-model proxies against held-out public sources; not VCC scores",
                   "summary": summary, "e2": e2_rows}, fh, indent=1, default=str)
    pd.set_option("display.width", 250)
    if summary:
        print(pd.DataFrame(summary)[["held_out", "stratum", "arm", "against", "targets", "combined_minus",
                                     "combined_ci95", "pds_minus", "energy_ratio"]].round(4).to_string(index=False))
    if e2_rows:
        print(pd.DataFrame(e2_rows).to_string(index=False))


if __name__ == "__main__":
    main()
