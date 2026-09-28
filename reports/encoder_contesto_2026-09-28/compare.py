"""Put the network runs of a runs.json side by side, per condition: the network's own diagnostics (net - blind,
net - swap, net - emb_blind, net - emb_swap, E2) and the comparison between conditions on the same targets
(numpy and pandas; pool.py of reports/rete_contesti_2026-09-27 reads the dataset for the truth).

    python compare.py --runs-json runs.json --data DATASET --out NEW [--shard 0] [--write-averaged DIR]

Effect-space diagnostics, with train.py's formulas (copied here, and checked against train.py's metrics.json by
selftest_emb.py): per test target the weighted MSE (weights gene weight / (k SE^2 + tau2)), the truth centred on
its mean over the test targets; skill = 1 - sum MSE / sum MSE of predicting 0; weighted cosine; discrimination
among the test targets. A contrast a - b is the mean over targets of (MSE_b - MSE_a) / mean MSE_0 (skill_a -
skill_b), with a bootstrap 95 % interval over targets, on all targets and on the strong stratum. Not VCC scores
and not the r1 proxy: score_pred.py of the network folder reads the averaged folders written by
--write-averaged (net - excl, net - blind, net - swap in its combined proxy).

Outputs in --out (a new folder):
    per_run.csv         every run, from its metrics.json and history.csv: skills, contrasts, E2, and the
                        validation curve (first, best and last validation loss, best step)
    arms.csv            per design, truth and condition, the skill, cosine and discrimination of each arm of the
                        predictions averaged over the common seeds
    within.csv          per condition, net against its controls (blind, swap, emb_blind, emb_swap, transfer,
                        partners), averaged predictions
    between.csv         condition against condition on the same targets and genes: every condition against none,
                        the encoders against pca, ours+X against ours; averaged predictions
    seeds.csv           the same between-condition skill contrasts seed by seed (sign consistency)
    e2.csv              E2 designs: per condition the correlation of the predicted and observed differences, with
                        the permutation control; and the paired difference between conditions
    readout.csv         the mechanical reading of the rule proposed in DISEGNO.md §10 (a proposal until the lead
                        registers it)
    summary.json        all of the above, the seeds used, the runs missing
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def _network_dir() -> Path:
    env = os.environ.get("RETE_CONTESTI_CODE", "")
    for d in ([Path(env)] if env else []) + [HERE, HERE.parent / "rete_contesti_2026-09-27"]:
        if (d / "pool.py").exists():
            return d.resolve()
    raise SystemExit("pool.py (reports/rete_contesti_2026-09-27) not found: set RETE_CONTESTI_CODE")


for _d in (_network_dir(), HERE):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

import corpus as CO  # noqa: E402
import pool as P  # noqa: E402

ARMS = ("net", "blind", "swap", "transfer", "partners", "emb_blind", "emb_swap")
CONTROLS = ("blind", "swap", "emb_blind", "emb_swap", "transfer", "partners")
E2_ARMS = ("net", "blind", "emb_blind", "transfer")
RULE_FLOOR = -0.002


# ---------------------------------------------------------------- train.py's diagnostics (copied, numpy only)

def boot(x, rng, n: int = 1000) -> dict:
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"mean": None, "ci95": [None, None], "sd": None, "n": 0}
    means = np.array([x[rng.integers(0, x.size, x.size)].mean() for _ in range(n)])
    return {"mean": float(x.mean()), "ci95": [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))],
            "sd": float(means.std()), "n": int(x.size)}


def discrimination(pred: np.ndarray, truth: np.ndarray) -> np.ndarray:
    T = pred.shape[0]
    if T < 2:
        return np.full(T, np.nan)
    a = pred / np.maximum(np.linalg.norm(pred, axis=1, keepdims=True), 1e-12)
    b = truth / np.maximum(np.linalg.norm(truth, axis=1, keepdims=True), 1e-12)
    c = a @ b.T
    d = np.diag(c)[:, None]
    rank = (c > d).sum(axis=1) + 0.5 * ((c == d).sum(axis=1) - 1)
    return 1.0 - rank / (T - 1)


def centred(x: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        cnt = np.isfinite(x).sum(axis=0)
        mean = np.divide(np.nansum(x, axis=0), cnt, out=np.zeros(x.shape[1]), where=cnt > 0)
    return x - mean[None, :]


def effect_diagnostics(truth, se, arms: dict, gw, k: float, tau2: float, keep, disc_drop, rng, pairs,
                       n_boot: int = 1000) -> dict:
    """train.effect_diagnostics with the pairs as an argument; also returns the per-target arrays."""
    yc = centred(truth)
    use = keep & np.isfinite(yc) & np.isfinite(se) & (se > 0)
    wt = np.where(use, gw[None, :] / (k * np.where(use, se, 1.0) ** 2 + tau2), 0.0)
    y0 = np.where(use, yc, 0.0)
    wsum = wt.sum(axis=1)
    okt = wsum > 0
    mse0 = np.where(okt, (wt * y0 ** 2).sum(axis=1) / np.maximum(wsum, 1e-12), np.nan)
    norm = float(np.nanmean(mse0)) if np.isfinite(mse0).any() else float("nan")
    cw = np.where(use, gw[None, :], 0.0)
    ydisc = y0 * cw
    ydisc[:, disc_drop] = 0.0
    per, summary = {}, {}
    for name, p in arms.items():
        p0 = np.where(use & np.isfinite(p), p, 0.0)
        mse = np.where(okt, (wt * (p0 - y0) ** 2).sum(axis=1) / np.maximum(wsum, 1e-12), np.nan)
        a, b = p0 * cw, y0 * cw
        cos = (a * b).sum(axis=1) / np.maximum(np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-12)
        pdisc = a.copy()
        pdisc[:, disc_drop] = 0.0
        per[name] = {"mse": mse, "cos": cos, "pds": discrimination(pdisc, ydisc)}
        summary[name] = {"skill": float(1.0 - np.nansum(mse) / np.nansum(mse0)) if np.nansum(mse0) > 0 else None,
                         "cos": float(np.nanmean(cos)), "pds": float(np.nanmean(per[name]["pds"]))}
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(use, np.abs(truth / np.where(use, se, 1.0)), 0.0)
    strength = (z >= 3).sum(axis=1)
    strong = strength >= np.quantile(strength, 0.75)
    contrasts = {}
    for a_, b_ in pairs:
        if a_ not in per or b_ not in per:
            continue
        stats = {}
        for stratum, sel in (("all", np.ones(len(strength), dtype=bool)), ("strong", strong)):
            stats[stratum] = {"skill": boot(((per[b_]["mse"] - per[a_]["mse"]) / norm)[sel], rng, n_boot),
                              "cos": boot((per[a_]["cos"] - per[b_]["cos"])[sel], rng, n_boot),
                              "pds": boot((per[a_]["pds"] - per[b_]["pds"])[sel], rng, n_boot)}
        contrasts[(a_, b_)] = stats
    return {"targets": int(truth.shape[0]), "targets_scored": int(okt.sum()), "strong_targets": int(strong.sum()),
            "arms": summary, "contrasts": contrasts, "per": per, "norm": norm}


def weighted_corr_rows(a: np.ndarray, b: np.ndarray, w: np.ndarray, min_genes: int = 20) -> np.ndarray:
    ok = np.isfinite(a) & np.isfinite(b) & (w > 0)
    ww = np.where(ok, w, 0.0)
    sw = ww.sum(axis=1)
    a0, b0 = np.where(ok, a, 0.0), np.where(ok, b, 0.0)
    ma = (ww * a0).sum(axis=1) / np.maximum(sw, 1e-12)
    mb = (ww * b0).sum(axis=1) / np.maximum(sw, 1e-12)
    da, db = np.where(ok, a0 - ma[:, None], 0.0), np.where(ok, b0 - mb[:, None], 0.0)
    cov = (ww * da * db).sum(axis=1)
    va, vb = (ww * da * da).sum(axis=1), (ww * db * db).sum(axis=1)
    r = np.where((va > 0) & (vb > 0), cov / np.sqrt(np.maximum(va * vb, 1e-300)), 0.0)
    return np.where(ok.sum(axis=1) >= min_genes, r, np.nan)


def e2_diagnostics(y1, y2, arms1: dict, arms2: dict, w, keep, rng, n_perm: int = 200, n_boot: int = 1000) -> dict:
    """train.e2_diagnostics, also returning the per-target correlations."""
    obs = centred(np.where(keep, y1 - y2, np.nan))
    wt = np.where(keep, w[None, :], 0.0)
    out = {}
    for name in arms1:
        if name not in arms2:
            continue
        raw_diff = arms1[name] - arms2[name]
        fin = np.isfinite(raw_diff)
        zero = bool(np.all(np.abs(raw_diff[fin]) < 1e-7)) if fin.any() else True
        dp = centred(np.where(keep, raw_diff, np.nan))
        corr = weighted_corr_rows(dp, obs, wt)
        res = {"predicted_difference_is_zero": zero, **boot(corr, rng, n_boot), "per_target": corr}
        if not zero and np.isfinite(corr).any():
            perm = np.array([np.nanmean(weighted_corr_rows(dp, obs[rng.permutation(obs.shape[0])], wt))
                             for _ in range(n_perm)])
            res.update({"perm_mean": float(np.mean(perm)), "perm_q975": float(np.quantile(perm, 0.975)),
                        "perm_p": float(np.mean(perm >= np.nanmean(corr)))})
        out[name] = res
    return out


# ---------------------------------------------------------------- reading runs

def read_npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        d = {k: z[k] for k in z.files}
    d["targets"] = [str(s) for s in d["targets"]]
    if "meta" in d:
        d["meta"] = json.loads(d["meta"].item())
    return d


def load_run(folder) -> dict:
    """A train.py / train_emb.py output folder: config, metrics, history and the paths of its predictions."""
    folder = Path(folder)
    run = {"folder": folder, "config": json.loads((folder / "config.json").read_text(encoding="utf-8")),
           "metrics": json.loads((folder / "metrics.json").read_text(encoding="utf-8"))}
    hist = folder / "history.csv"
    run["history"] = pd.read_csv(hist) if hist.exists() and hist.stat().st_size > 1 else pd.DataFrame()
    emb = folder / "emb_config.json"
    run["emb_config"] = json.loads(emb.read_text(encoding="utf-8")) if emb.exists() else None
    tt = folder / "test_targets.txt"
    run["test_targets"] = [s for s in tt.read_text(encoding="utf-8").splitlines() if s] if tt.exists() else []
    return run


def run_arms(run: dict, truth: str, pool: P.Pool, keys=ARMS) -> tuple[list, dict, dict]:
    """(targets, arms on the stored genes, meta) of one truth context of a run; transfer and partners at the
    calibrated amplitudes, as train.predict_arms makes them."""
    z = read_npz(run["folder"] / f"pred_{truth}.npz")
    cols = pool.genes_axis
    if not np.array_equal(np.asarray(z["axis_index"], dtype=np.int64), cols):
        raise SystemExit(f"{run['folder']}: its stored genes are not the dataset's")
    meta = z.get("meta", {})
    arms = {}
    for key in ("net", "blind", "swap"):
        if key in keys and key in z:
            arms[key] = np.asarray(z[key][:, cols], dtype=np.float32)
    if "transfer" in keys:
        arms["transfer"] = float(meta["amplitude"]) * np.asarray(z["transfer"][:, cols], dtype=np.float32)
    if "partners" in keys:
        arms["partners"] = float(meta["amplitude_q"]) * np.asarray(z["partners"][:, cols], dtype=np.float32)
    side = run["folder"] / f"predemb_{truth}.npz"
    if side.exists() and any(k in keys for k in ("emb_blind", "emb_swap")):
        e = read_npz(side)
        if e["targets"] != z["targets"]:
            raise SystemExit(f"{side}: targets differ from pred_{truth}.npz")
        for key in ("emb_blind", "emb_swap"):
            if key in keys and key in e:
                arms[key] = np.asarray(e[key][:, cols], dtype=np.float32)
    return z["targets"], arms, meta


def truth_block(pool: P.Pool, context: str, targets: list) -> tuple[np.ndarray, np.ndarray]:
    """raw and SE (float32, stored genes) of the context's rows for the targets, in their order."""
    c = pool.context_index[context]
    rows = pool.ctx_rows[c]
    by_t = {pool.target_names[t]: r for t, r in zip(pool.row_target[rows], rows)}
    absent = [t for t in targets if t not in by_t]
    if absent:
        raise SystemExit(f"{context}: no row for targets {absent[:5]}")
    r = np.array([by_t[t] for t in targets], dtype=np.int64)
    order = np.argsort(r, kind="stable")
    out = []
    for key in ("raw", "se"):
        x = np.empty((r.size, pool.G), dtype=np.float32)
        x[order] = np.asarray(pool.arrays[key][r[order]], dtype=np.float32)
        out.append(x)
    return out[0], out[1]


def gene_weight(pool: P.Pool, context: str, mode: str) -> np.ndarray:
    """pool.Phase.gw of the context's basal row: x / (1 + x), x = 0.05 CPM ("context"), or 1 ("flat")."""
    b = int(pool.ctx_basal[pool.context_index[context]])
    if mode == "flat":
        return np.ones(pool.G, dtype=np.float32)
    x = 0.05 * pool.gene_cpm
    return (x / (1.0 + x)).astype(np.float32)[b]


def disc_drop_of(pool: P.Pool, test_targets: list) -> np.ndarray:
    cols = np.array([pool.tgt_gene[pool.target_index[t]] for t in test_targets if t in pool.target_index],
                    dtype=np.int64)
    return cols[cols >= 0]


def run_metrics(run: dict, pool: P.Pool, truth: str, seed: int = 0) -> dict:
    """train.py's effect diagnostics of one run and truth, recomputed from its saved predictions."""
    targets, arms, _ = run_arms(run, truth, pool)
    raw, se = truth_block(pool, truth, targets)
    a = run["config"]["args"]
    k = float(pool.ctx_se_factor[pool.context_index[truth]])
    keep = np.isfinite(arms["net"])
    pairs = [("net", c) for c in CONTROLS] + [("blind", "transfer")]
    return effect_diagnostics(raw, se, arms, gene_weight(pool, truth, a.get("gene_weight", "context")), k,
                              float(a.get("tau2", 0.01)), keep, disc_drop_of(pool, run["test_targets"]),
                              np.random.default_rng([seed, 3]), pairs)


def contrast_mean(m: dict, a: str, b: str, metric: str = "skill", stratum: str = "all"):
    st = m["contrasts"].get((a, b))
    return None if st is None else st[stratum][metric]["mean"]


# ---------------------------------------------------------------- tables

def contrast_rows(res: dict, base: dict, kind: str) -> list:
    rows = []
    for (a, b), stats in res["contrasts"].items():
        for stratum, per_metric in stats.items():
            for metric, s in per_metric.items():
                rows.append({**base, "kind": kind, "a": a, "b": b, "stratum": stratum, "metric": metric,
                             "mean": s["mean"], "lo": s["ci95"][0], "hi": s["ci95"][1], "n": s["n"]})
    return rows


def comparison_pairs(conds: list) -> list:
    """Every condition against none; encoders (not PCA) against pca; ours+X and ours-X against ours; pca+X
    against pca."""
    pairs = []
    for x in conds:
        if x != "none" and "none" in conds:
            pairs.append((x, "none"))
    for x in conds:
        if x not in ("none",) and not x.startswith("pca") and "pca" in conds:
            pairs.append((x, "pca"))
    for x in conds:
        if x.startswith(("ours+", "ours-")) and "ours" in conds:
            pairs.append((x, "ours"))
        if x.startswith(("pca+", "pca-")) and "pca" in conds:
            pairs.append((x, "pca"))
    return list(dict.fromkeys(pairs))


def validation_curve(hist: pd.DataFrame) -> dict:
    if hist.empty or "val_loss" not in hist.columns:
        return {}
    h = hist.dropna(subset=["val_loss"])
    if h.empty:
        return {}
    i = int(h["val_loss"].to_numpy().argmin())
    return {"val_first": float(h["val_loss"].iloc[0]), "val_best": float(h["val_loss"].iloc[i]),
            "val_last": float(h["val_loss"].iloc[-1]), "best_step": int(h["step"].iloc[i]),
            "evaluations": int(len(h)), "best_at_first": bool(i == 0)}


def per_run_rows(meta: dict, run: dict) -> list:
    rows = []
    base = {k: meta[k] for k in ("id", "design", "condition", "seed")}
    vc = validation_curve(run["history"])
    for truth, d in run["metrics"].get("contexts", {}).items():
        row = {**base, "truth": truth, "targets": d.get("targets"), **vc}
        for arm, s in d.get("arms", {}).items():
            row[f"skill_{arm}"] = s.get("skill")
        for key, st in d.get("contrasts", {}).items():
            s = st["all"]["skill"]
            row[f"{key}_mean"], row[f"{key}_lo"], row[f"{key}_hi"] = s["mean"], s["ci95"][0], s["ci95"][1]
        rows.append(row)
    for pair, arms in run["metrics"].get("e2", {}).items():
        for arm, s in arms.items():
            rows.append({**base, "truth": f"E2 {pair}", "e2_arm": arm, "e2_mean": s.get("mean"),
                         "e2_lo": (s.get("ci95") or [None, None])[0], "e2_hi": (s.get("ci95") or [None, None])[1],
                         "e2_perm_q975": s.get("perm_q975"), "e2_zero": s.get("predicted_difference_is_zero"), **vc})
    return rows


def rule_readout(between: pd.DataFrame, within: pd.DataFrame, e2: pd.DataFrame, seeds: pd.DataFrame,
                 e1_designs: list) -> pd.DataFrame:
    """The proposed rule of DISEGNO.md §10, read mechanically for each comparison (a, b) of between.csv; the E1
    units are the truths of the E1 designs (an E2 design's truths do not count twice)."""
    out = []
    if between.empty:
        return pd.DataFrame()

    def e1_rows(df: pd.DataFrame) -> pd.DataFrame:
        return df[df["design"].isin(e1_designs)] if not df.empty else df

    sk = e1_rows(between[(between["stratum"] == "all") & (between["metric"] == "skill")])
    n = int(len(sk[["design", "truth"]].drop_duplicates())) if not sk.empty else 0
    need = max(n - 1, 1)
    for (a, b), g in between[(between["stratum"] == "all") & (between["metric"] == "skill")].groupby(["a", "b"]):
        g = e1_rows(g)
        pos = int((g["mean"] > 0).sum())
        ci_pos = int((g["lo"] > 0).sum())
        ci_neg = int((g["hi"] < RULE_FLOOR).sum())
        e1 = pos >= need and ci_pos >= 1 and ci_neg == 0
        cond = a.split(":")[0]
        w = e1_rows(within)
        if not w.empty:
            w = w[(w["stratum"] == "all") & (w["metric"] == "skill") & (w["a"] == f"{cond}:net")]
        use = {}
        for ctrl in ("emb_blind", "emb_swap"):
            h = w[w["b"] == f"{cond}:{ctrl}"] if not w.empty else w
            use[ctrl] = (int((h["mean"] > 0).sum()) >= need and int((h["lo"] > 0).sum()) >= 1) if len(h) else None
        e2_ok = None
        if not e2.empty:
            ea = e2[(e2["kind"] == "condition") & (e2["a"] == f"{cond}:net") & (e2["stratum"] == "all")]
            ed = e2[(e2["kind"] == "between") & (e2["a"] == a) & (e2["b"] == b)]
            if len(ea):
                e2_ok = bool(((ea["lo"] > 0) & (ea["mean"] > ea["perm_q975"])).all()
                             and (len(ed) == 0 or (ed["mean"] > 0).all()))
        sg = e1_rows(seeds)
        if not sg.empty:
            sg = sg[(sg["a"] == a) & (sg["b"] == b)]
        same_sign = None
        if len(sg):
            per_unit = sg.groupby(["design", "truth"])["mean"].apply(lambda s: bool((s > 0).all() or (s < 0).all()))
            same_sign = int(per_unit.sum()) >= need
        verdict = e1 and (use["emb_blind"] is not False) and (use["emb_swap"] is not False) \
            and (e2_ok is not False) and (same_sign is not False)
        out.append({"a": a, "b": b, "e1_truths": n, "positive": pos, "ci_above_0": ci_pos,
                    f"ci_below_{RULE_FLOOR}": ci_neg, "e1_passes": e1, "uses_embedding_vs_emb_blind": use["emb_blind"],
                    "right_context_vs_emb_swap": use["emb_swap"], "e2_passes": e2_ok, "seed_signs_agree": same_sign,
                    "passes_proposed_rule": bool(verdict)})
    return pd.DataFrame(out)


# ---------------------------------------------------------------- main

def write_averaged(root: Path, design: str, cond: str, runs: list, truth: str, pool: P.Pool, dtype) -> None:
    """A train.py-shaped folder whose predictions are the mean over the seeds (score_pred.py reads it)."""
    folder = root / design / cond
    folder.mkdir(parents=True, exist_ok=True)
    cfg_path = folder / "config.json"
    if not cfg_path.exists():
        cfg = dict(runs[0]["config"])
        cfg["averaged_over"] = [str(r["folder"]) for r in runs]
        CO.write_json(cfg_path, cfg)
    sums, sides, metas, targets = {}, {}, [], None
    for r in runs:
        z = read_npz(r["folder"] / f"pred_{truth}.npz")
        targets = z["targets"] if targets is None else targets
        if z["targets"] != targets:
            raise SystemExit("averaging runs with different test targets")
        metas.append(z.get("meta", {}))
        for key in ("net", "blind", "swap", "transfer", "partners"):
            if key in z:
                sums[key] = sums.get(key, 0.0) + np.asarray(z[key], dtype=np.float64)
        side = r["folder"] / f"predemb_{truth}.npz"
        if side.exists():
            e = read_npz(side)
            for key in ("emb_blind", "emb_swap"):
                if key in e:
                    sides[key] = sides.get(key, 0.0) + np.asarray(e[key], dtype=np.float64)
    n = len(runs)
    meta = {"averaged_over": n, "context": truth,
            "amplitude": float(np.mean([m.get("amplitude", np.nan) for m in metas])),
            "amplitude_q": float(np.mean([m.get("amplitude_q", np.nan) for m in metas])),
            "transfer_and_partners": "unscaled m and q, averaged over the seeds (identical when the design is)"}
    payload = {"targets": np.array(targets, dtype=str), "axis_index": pool.genes_axis}
    payload.update({k: (v / n).astype(dtype) for k, v in sums.items()})
    payload["meta"] = np.array(json.dumps(meta))
    with open(folder / f"pred_{truth}.npz", "xb") as fh:
        np.savez_compressed(fh, **payload)
    if sides:
        sp = {"targets": np.array(targets, dtype=str), "axis_index": pool.genes_axis}
        sp.update({k: (v / n).astype(dtype) for k, v in sides.items()})
        with open(folder / f"predemb_{truth}.npz", "xb") as fh:
            np.savez_compressed(fh, **sp)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-json", type=Path, required=True)
    ap.add_argument("--data", type=Path, required=True, help="the network dataset (truth)")
    ap.add_argument("--out", type=Path, required=True, help="new folder")
    ap.add_argument("--shard", type=int, default=None, help="only this shard's runs")
    ap.add_argument("--relocate", default="", help="OLD=NEW: the run folders moved from prefix OLD to NEW")
    ap.add_argument("--write-averaged", type=Path, default=None, help="folder for seed-averaged run folders")
    ap.add_argument("--averaged-dtype", choices=["float32", "float16"], default="float32")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--n-perm", type=int, default=200)
    args = ap.parse_args(argv)
    spec = json.loads(args.runs_json.read_text(encoding="utf-8"))
    old, _, new = args.relocate.partition("=")

    def where(path: str) -> Path:
        return Path(new + path[len(old):]) if old and path.startswith(old) else Path(path)

    args.out.mkdir(parents=True, exist_ok=False)
    pool = P.Pool.from_dir(args.data)
    net_runs = [r for r in spec["runs"] if r["kind"] == "network" and (args.shard is None or r["shard"] == args.shard)]
    loaded, missing = {}, []
    for r in net_runs:
        folder = where(r["out"])
        if not (folder / "metrics.json").exists():
            missing.append(r["id"])
            continue
        loaded[r["id"]] = (r, load_run(folder))
    print(f"{len(loaded)} runs read, {len(missing)} missing", flush=True)
    per_run = [row for r, run in loaded.values() for row in per_run_rows(r, run)]
    by_design: dict = {}
    for r, run in loaded.values():
        by_design.setdefault(r["design"], {}).setdefault(r["condition"], {})[int(r["seed"])] = run
    e1_designs = sorted(d for d in by_design if spec["designs"][d]["kind"] == "E1")
    arms_rows, within_rows, between_rows, seed_rows, e2_rows, used = [], [], [], [], [], {}
    for design, conds in sorted(by_design.items()):
        seeds = sorted(set.intersection(*[set(v) for v in conds.values()]))
        used[design] = {"seeds": seeds, "conditions": sorted(conds)}
        if not seeds:
            print(f"{design}: no seed common to every condition; skipped", flush=True)
            continue
        first = conds[sorted(conds)[0]][seeds[0]]
        truths = first["config"]["design"]["truth"]
        tests = {(c, s): tuple(run["test_targets"]) for c, v in conds.items() for s, run in v.items()}
        if len(set(tests.values())) != 1:
            raise SystemExit(f"{design}: the runs do not share their test targets")
        a0 = first["config"]["args"]
        tau2, gmode = float(a0.get("tau2", 0.01)), a0.get("gene_weight", "context")
        drop = disc_drop_of(pool, first["test_targets"])
        pairs_between = [(f"{x}:net", f"{y}:net") for x, y in comparison_pairs(sorted(conds))]
        keep_e2, arms_e2 = {}, {}
        for ti, truth in enumerate(truths):
            avg, seed_net, targets = {}, {}, None
            for cond, by_seed in conds.items():
                sums, count = {}, 0
                for s in seeds:
                    tg, arms, _ = run_arms(by_seed[s], truth, pool)
                    targets = tg if targets is None else targets
                    if tg != targets:
                        raise SystemExit(f"{design} {truth}: predictions with different target orders")
                    for k_, v in arms.items():
                        sums[k_] = sums.get(k_, 0.0) + v.astype(np.float64)
                    seed_net[(cond, s)] = arms["net"]
                    count += 1
                for k_, v in sums.items():
                    avg[f"{cond}:{k_}"] = (v / count).astype(np.float32)
            raw, se = truth_block(pool, truth, targets)
            gw = gene_weight(pool, truth, gmode)
            k = float(pool.ctx_se_factor[pool.context_index[truth]])
            keep = np.logical_and.reduce([np.isfinite(avg[f"{c}:net"]) for c in conds])
            pairs_within = [(f"{c}:net", f"{c}:{x}") for c in conds for x in CONTROLS if f"{c}:{x}" in avg]
            rng = np.random.default_rng([ti, 41])
            res = effect_diagnostics(raw, se, avg, gw, k, tau2, keep, drop, rng, pairs_within + pairs_between,
                                     args.n_boot)
            base = {"design": design, "truth": truth, "seeds": len(seeds)}
            for name, s in res["arms"].items():
                cond, arm = name.split(":", 1)
                arms_rows.append({**base, "condition": cond, "arm": arm, **s})
            within_rows += contrast_rows({"contrasts": {p: v for p, v in res["contrasts"].items() if p in pairs_within}},
                                         base, "within")
            between_rows += contrast_rows({"contrasts": {p: v for p, v in res["contrasts"].items()
                                                         if p in pairs_between}}, base, "between")
            for s in seeds:
                arms_s = {f"{c}:net": seed_net[(c, s)] for c in conds}
                rs = effect_diagnostics(raw, se, arms_s, gw, k, tau2, keep, drop, np.random.default_rng([ti, 43, s]),
                                        pairs_between, 200)
                for (a, b), st in rs["contrasts"].items():
                    x = st["all"]["skill"]
                    seed_rows.append({**base, "seed": s, "a": a, "b": b, "mean": x["mean"], "lo": x["ci95"][0],
                                      "hi": x["ci95"][1]})
            if len(truths) == 2:
                keep_e2[truth] = keep
                arms_e2[truth] = ({k_: v for k_, v in avg.items() if k_.split(":", 1)[1] in E2_ARMS}, raw, gw)
            print(f"{design} {truth}: {len(targets)} targets, {len(conds)} conditions, seeds {seeds}", flush=True)
        if len(truths) == 2 and len(arms_e2) == 2:
            t1, t2 = truths
            (A1, y1, g1), (A2, y2, g2) = arms_e2[t1], arms_e2[t2]
            e2 = e2_diagnostics(y1, y2, A1, A2, 0.5 * (g1 + g2), keep_e2[t1] & keep_e2[t2],
                                np.random.default_rng([7, 47]), args.n_perm, args.n_boot)
            base = {"design": design, "truth": f"{t1}-{t2}", "seeds": len(seeds)}
            for name, s in e2.items():
                e2_rows.append({**base, "kind": "condition", "a": name, "b": "", "stratum": "all", "mean": s["mean"],
                                "lo": s["ci95"][0], "hi": s["ci95"][1], "n": s["n"],
                                "zero": s["predicted_difference_is_zero"], "perm_q975": s.get("perm_q975"),
                                "perm_p": s.get("perm_p")})
            for a, b in pairs_between:
                if a in e2 and b in e2:
                    d = boot(e2[a]["per_target"] - e2[b]["per_target"], np.random.default_rng([7, 53]), args.n_boot)
                    e2_rows.append({**base, "kind": "between", "a": a, "b": b, "stratum": "all", "mean": d["mean"],
                                    "lo": d["ci95"][0], "hi": d["ci95"][1], "n": d["n"]})
        if args.write_averaged is not None:
            dtype = np.float16 if args.averaged_dtype == "float16" else np.float32
            for cond, by_seed in conds.items():
                for truth in truths:
                    write_averaged(args.write_averaged, design, cond, [by_seed[s] for s in seeds], truth, pool, dtype)
    tables = {"per_run": pd.DataFrame(per_run), "arms": pd.DataFrame(arms_rows), "within": pd.DataFrame(within_rows),
              "between": pd.DataFrame(between_rows), "seeds": pd.DataFrame(seed_rows), "e2": pd.DataFrame(e2_rows)}
    tables["readout"] = rule_readout(tables["between"], tables["within"], tables["e2"], tables["seeds"], e1_designs)
    for name, df in tables.items():
        df.to_csv(args.out / f"{name}.csv", index=False)
    CO.write_json(args.out / "summary.json", {
        "stage": "encoder_contesto_2026-09-28/compare.py", "runs_json": str(args.runs_json), "data": str(args.data),
        "claim_type": "effect-space diagnostics on held-out public contexts; not VCC scores and not the r1 proxy",
        "runs_read": sorted(loaded), "runs_missing": missing, "designs": used, "e1_designs": e1_designs,
        "rule": "DISEGNO.md §10, proposed; binding only once the lead registers it",
        "tables": {k: v.to_dict(orient="records") for k, v in tables.items() if k != "per_run"}})
    pd.set_option("display.width", 250)
    if not tables["between"].empty:
        b = tables["between"]
        print(b[(b["stratum"] == "all") & (b["metric"] == "skill")][["design", "truth", "a", "b", "mean", "lo", "hi"]]
              .round(4).to_string(index=False))
    if not tables["readout"].empty:
        print(tables["readout"].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
