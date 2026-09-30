"""Held-target predictive 3-prime-to-Flex bridge; protocol: PROTOCOLLO_PONTE.md.

Use --plan-only to inspect indices, --self-test for synthetic checks. Real runs require
a new --out directory. No network, cloud, full-universe matrices or submission writes.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports/trasferimento/atlante_2026-09-26"))
from atlas_bench import Universe  # noqa: E402
from vcc2026.resources import peak_rss_bytes  # noqa: E402

SEED = 20260929
ARMS = [(1, 200), (1, 50), (0, 200), (0, 50)]  # tie order: conservative first


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def check_memory(budget: int) -> None:
    peak = peak_rss_bytes()
    if peak is None:
        raise RuntimeError("Memory measurement unavailable; cannot enforce the registered budget")
    if peak > budget * 1024**2:
        raise MemoryError(f"Measured peak {peak / 1024**2:.1f} MiB exceeds {budget} MiB")


class OneChunkUniverse(Universe):
    """Use the existing reader with a single cached chunk, instead of its default two."""

    def _load(self, file: str) -> dict:
        if file not in self._cache:
            self._cache.clear()
        return super()._load(file)


def aligned(uni: Universe, targets: list[str], field: str, genes: int) -> np.ndarray:
    out = np.full((len(targets), genes), np.nan, np.float32)
    present = [t for t in targets if t in uni.targets]
    if present:
        table = uni.table(present)
        lookup = {t: i for i, t in enumerate(targets)}
        rows = [lookup[t] for t in table.targets]
        out[rows] = getattr(table, field)
    return out


class Moments:
    def __init__(self, genes: int):
        self.values = {k: np.zeros(genes, np.float64) for k in
                       ["n", "x", "a", "b", "xx", "aa", "bb", "xa", "xb", "ab"]}

    def add(self, x, a, b, mask) -> None:
        ok = mask & np.isfinite(x) & np.isfinite(a) & np.isfinite(b)
        x, a, b = (np.where(ok, z, 0).astype(np.float64) for z in (x, a, b))
        self.values["n"] += ok.sum(axis=0)
        for key, value in [("x", x), ("a", a), ("b", b), ("xx", x*x), ("aa", a*a),
                           ("bb", b*b), ("xa", x*a), ("xb", x*b), ("ab", a*b)]:
            self.values[key] += value.sum(axis=0)

    def finish(self, basal, min_pairs=20) -> dict:
        s = self.values
        n = np.maximum(s["n"], 1)
        means = {k: s[k] / n for k in ("x", "a", "b")}
        centered = {k: s[k] - s[k[0]] * s[k[1]] / n for k in ("xx", "aa", "bb", "xa", "xb", "ab")}
        good = (s["n"] >= min_pairs) & (centered["xx"] > 0) & (centered["aa"] > 0) & (centered["bb"] > 0) & (basal >= 5)
        den = np.sqrt(np.maximum(centered["aa"] * centered["bb"], 0))
        reliability = np.clip(np.divide(centered["ab"], den, out=np.zeros_like(den), where=den > 0), 0, 1)
        x = .05 * np.nan_to_num(basal)
        weight = x / (1+x)
        betas, scalars = {}, {}
        for train_half in ("a", "b"):
            cov = centered["x" + train_half]
            ols = np.clip(np.divide(cov, centered["xx"], out=np.zeros_like(cov), where=centered["xx"] > 0), 0, 2)
            total_x = np.sum(centered["xx"][good] * weight[good]**2)
            scalar = np.clip(np.sum(cov[good] * weight[good]**2) / total_x, 0, 2) if total_x > 0 else 0.0
            scalars[train_half] = float(scalar)
            betas[train_half] = {}
            for prior, k in ARMS:
                q = reliability * s["n"] / (s["n"] + k)
                betas[train_half][f"p{prior}_k{k}"] = q * ols + (1-q) * prior
        return {"means": means, "reliability": reliability, "n": s["n"], "support": good,
                "weight": weight, "betas": betas, "scalars": scalars}


def make_mask(targets, axis, coords, excluded) -> np.ndarray:
    mask = np.broadcast_to(~np.isin(axis, list(excluded)), (len(targets), len(axis))).copy()
    chrom = coords.reindex(axis).chrom.astype(str).to_numpy()
    tss = coords.reindex(axis).tss.to_numpy(float)
    for i, target in enumerate(targets):
        mask[i, axis == target] = False
        if target in coords.index:
            near = (chrom == str(coords.at[target, "chrom"])) & (np.abs(tss - float(coords.at[target, "tss"])) <= 5000)
            mask[i, near] = False
    return mask


def batches(names, size):
    names = sorted(names)
    for start in range(0, len(names), size):
        yield names[start:start+size]


def read_batch(unis, names, genes, budget):
    x = aligned(unis["x"], names, "shrunk", genes)
    check_memory(budget)
    a = aligned(unis["a"], names, "raw", genes)
    check_memory(budget)
    b = aligned(unis["b"], names, "raw", genes)
    check_memory(budget)
    return x, a, b


def score(target, direction, arm, pred, truth, support, weight, missing_x) -> dict:
    good = support & np.isfinite(truth)
    if not missing_x:
        good &= np.isfinite(pred)
    if good.sum() < 100:
        return {"target": target, "direction": direction, "arm": arm, "status": "insufficient_truth_support",
                "genes": int(good.sum()), "missing_input": missing_x}
    p = np.zeros(good.sum()) if missing_x else pred[good].astype(float) * weight[good]
    y = truth[good].astype(float) * weight[good]
    pe, ye, dot = float(p @ p), float(y @ y), float(p @ y)
    cosine = dot / np.sqrt(pe*ye) if pe > 0 and ye > 0 else 0.0
    return {"target": target, "direction": direction, "arm": arm, "status": "ok", "genes": int(good.sum()),
            "missing_input": missing_x, "cosine": cosine, "prediction_energy": pe, "truth_energy": ye,
            "squared_error": float(np.sum((p-y)**2))}


def evaluate(names, unis, axis, coords, panel, model, arms, batch, budget) -> pd.DataFrame:
    records = []
    for block in batches(names, batch):
        x, a, b = read_batch(unis, block, len(axis), budget)
        masks = make_mask(block, axis, coords, panel) & model["support"]
        for train_half, truth_half, y in [("a", "b", b), ("b", "a", a)]:
            for i, target in enumerate(block):
                direction = f"fit_{train_half}_truth_{truth_half}"
                if target not in unis[truth_half].targets:
                    records.extend({"target": target, "direction": direction, "arm": arm, "status": "missing_truth"} for arm in arms)
                    continue
                missing_x = target not in unis["x"].targets
                source = x[i] - model["means"]["x"]
                truth = y[i] - model["means"][truth_half]
                for arm in arms:
                    if arm == "identity":
                        beta = 1.0
                    elif arm == "scalar":
                        beta = model["scalars"][train_half]
                    elif arm == "zero":
                        beta = 0.0
                    else:
                        beta = model["betas"][train_half][arm]
                    records.append(score(target, direction, arm, source * beta, truth, masks[i],
                                         model["weight"], missing_x))
        check_memory(budget)
    return pd.DataFrame(records)


def paired_deltas(frame, arm):
    good = frame.loc[frame.status == "ok"]
    wide = good.pivot(index=["target", "direction"], columns="arm", values="cosine")
    return (wide[arm] - wide.identity).rename("delta").dropna()


def choose(frame) -> tuple[str, list[dict]]:
    rows = []
    for prior, k in ARMS:
        name = f"p{prior}_k{k}"
        d = paired_deltas(frame, name).groupby(level="target").mean()
        own = frame[(frame.arm == name) & (frame.status == "ok")]
        own_cosine = float(own.groupby("target").cosine.mean().mean())
        rows.append({"arm": name, "targets": len(d), "mean_cosine_gain": float(d.mean()),
                     "mean_cosine": own_cosine, "nonzero_prediction_energy": bool(own.prediction_energy.sum() > 0)})
    eligible = [x for x in rows if x["mean_cosine"] > 0 and x["nonzero_prediction_energy"]]
    if not eligible:
        return "identity", rows
    best = max(x["mean_cosine_gain"] for x in eligible)
    if best < .005:
        return "identity", rows
    picked = next(x["arm"] for x in eligible if x["mean_cosine_gain"] >= best - .001 and x["mean_cosine_gain"] >= .005)
    return picked, rows


def summarize(frame, arm) -> dict:
    good = frame.loc[frame.status == "ok"]
    d = paired_deltas(frame, arm)
    by_target = d.groupby(level="target").mean().to_numpy(float)
    rng = np.random.default_rng(SEED+1)
    draws = np.array([rng.choice(by_target, size=len(by_target), replace=True).mean() for _ in range(2000)]) if len(by_target) else np.array([])
    mean = float(by_target.mean()) if len(by_target) else None
    ci = [float(v) for v in np.quantile(draws, [.025, .975])] if len(draws) else None
    directional = {str(k): float(v) for k, v in d.groupby(level="direction").mean().items()}
    metrics = []
    for name, block in good.groupby("arm"):
        den = block.truth_energy.sum()
        metrics.append({"arm": name, "targets": int(block.target.nunique()), "target_half_pairs": len(block),
                        "mean_cosine": float(block.cosine.mean()),
                        "mse_ratio_to_zero": float(block.squared_error.sum()/den) if den else None,
                        "energy_ratio_to_truth": float(block.prediction_energy.sum()/den) if den else None,
                        "missing_input_pairs": int(block.missing_input.sum())})
    return {"mean_cosine_gain": mean, "ci95": ci, "targets_with_paired_metrics": len(by_target),
            "direction_mean_gains": directional, "metrics": metrics,
            "statuses": frame.groupby(["arm", "status"]).size().to_dict() if frame.empty else
                        [{"arm": str(a), "status": str(s), "pairs": int(n)} for (a,s),n in frame.groupby(["arm", "status"]).size().items()],
            "passes_internal_mapping": bool(mean is not None and mean >= .005 and ci[0] > 0 and all(v > 0 for v in directional.values()))}


def self_test() -> None:
    rng = np.random.default_rng(6)
    x = rng.normal(size=(2000, 8))
    slopes = np.linspace(.15, 1.6, 8)
    a, b = x*slopes + rng.normal(0, .02, x.shape), x*slopes + rng.normal(0, .02, x.shape)
    m = Moments(8)
    m.add(x[:1000], a[:1000], b[:1000], np.ones((1000,8), bool))
    m.add(x[1000:], a[1000:], b[1000:], np.ones((1000,8), bool))
    fit = m.finish(np.full(8, 100.0))
    assert np.max(np.abs(fit["betas"]["a"]["p0_k50"] - slopes)) < .05
    assert fit["support"].all() and np.min(fit["reliability"]) > .98
    masked = Moments(8)
    mask = np.ones(x.shape, bool); mask[:,0] = False
    masked.add(x,a,b,mask)
    assert not masked.finish(np.full(8,100.0))["support"][0]
    s = score("t", "a_b", "zero", np.zeros(110), np.ones(110), np.ones(110,bool), np.ones(110), False)
    assert s["cosine"] == 0 and s["squared_error"] == s["truth_energy"] == 110
    holdout_x = rng.normal(size=(256, 8))
    holdout_y = holdout_x*slopes + rng.normal(0,.02,holdout_x.shape)
    mapped = holdout_x*fit["betas"]["a"]["p0_k50"]
    cosine = lambda p: np.sum(p*holdout_y,axis=1) / np.sqrt(np.sum(p*p,axis=1)*np.sum(holdout_y*holdout_y,axis=1))
    assert float(np.mean(cosine(mapped)-cosine(holdout_x))) > .05
    print("Synthetic checks passed: slope recovery, masking, null scoring, held-out improvement")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("C:/Users/ferra/vcc2026-data"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--memory-budget-mib", type=int, default=700)
    args = parser.parse_args()
    if args.self_test:
        self_test(); return
    if args.out is None:
        parser.error("--out is required for plan and real runs")
    if args.batch < 1 or args.batch > 64:
        parser.error("--batch must be 1..64 to preserve the memory design")
    args.out.mkdir(parents=True, exist_ok=False)
    folders = {"x": ("k562", "universe_k562_2026-09-26"),
               "a": ("viperturb", "universe_viperturb_2026-09-28_halfa"),
               "b": ("viperturb", "universe_viperturb_2026-09-28_halfb"),
               "full": ("viperturb", "universe_viperturb_2026-09-27_p1")}
    unis = {k: OneChunkUniverse(name, args.data/"processed"/folder) for k,(name,folder) in folders.items()}
    axis = pd.read_csv(args.data/"raw/controls/gene_names.csv").gene_name.to_numpy(str)
    panel = set(pd.read_csv(args.data/"raw/controls/pert_counts.csv").target_gene)
    available = sorted((unis["x"].targets & unis["a"].targets & unis["b"].targets) - panel)
    if len(available) < 2000:
        raise ValueError(f"Need 2000 non-panel targets for the frozen split; found {len(available)}")
    order = np.random.default_rng(SEED).permutation(available).tolist()
    split = {"train": order[:1200], "validation": order[1200:1600], "test": order[1600:2000],
             "reserve": order[2000:], "panel": sorted(panel & unis["full"].targets)}
    assert not any(set(split[a]) & set(split[b]) for a,b in [("train","validation"),("train","test"),("validation","test")])
    assert not panel & set(split["train"] + split["validation"] + split["test"])
    provenance = {k: {"path": str(u.folder), "targets_in_index": len(u.targets),
                      "index_sha256": hashlib.sha256((u.folder/"index.csv").read_bytes()).hexdigest(),
                      "manifest_sha256": hashlib.sha256((u.folder/"manifest.json").read_bytes()).hexdigest()}
                  for k,u in unis.items()}
    write_json(args.out/"split.json", split)
    write_json(args.out/"provenance.json", {"seed": SEED, "sources": provenance,
               "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "protocol_sha256": hashlib.sha256((HERE/"PROTOCOLLO_PONTE.md").read_bytes()).hexdigest(),
               "mode": "plan_only" if args.plan_only else "real_run", "batch": args.batch,
               "memory_budget_mib": args.memory_budget_mib})
    coverage = [{"target": t, **{f"has_{k}": t in u.targets for k,u in unis.items()}} for t in split["panel"]]
    pd.DataFrame(coverage).to_csv(args.out/"panel_coverage.csv", index=False)
    print(json.dumps({"split_counts": {k:len(v) for k,v in split.items()}, "mode": "plan_only" if args.plan_only else "real_run"}), flush=True)
    if args.plan_only:
        return
    coords = pd.read_csv(args.data/"external/annotation/gene_coordinates_gencode_v50.tsv", sep="\t").drop_duplicates("symbol").set_index("symbol")
    basal = pd.read_csv(args.data/"processed/basal_sources_2026-09-28.csv", index_col=0).reindex(axis).viperturb.to_numpy(float)
    moments = Moments(len(axis))
    for i, block in enumerate(batches(split["train"], args.batch)):
        x,a,b = read_batch(unis,block,len(axis),args.memory_budget_mib)
        moments.add(x,a,b,make_mask(block,axis,coords,panel))
        if i % 10 == 0:
            print(f"training blocks completed {i+1}; peak MiB {peak_rss_bytes()/1024**2:.1f}", flush=True)
    model = moments.finish(basal)
    if model["support"].sum() < 100:
        raise ValueError("Fewer than 100 genes meet training-only support; no predictive comparison is defined")
    columns = {"gene": axis, "training_pairs": model["n"], "support": model["support"], "reliability": model["reliability"]}
    columns.update({f"mean_{k}":v for k,v in model["means"].items()})
    columns.update({f"beta_fit_{half}_{name}":v for half,arms in model["betas"].items() for name,v in arms.items()})
    pd.DataFrame(columns).to_csv(args.out/"coefficients.csv", index=False)
    arms = [f"p{p}_k{k}" for p,k in ARMS] + ["identity", "scalar", "zero"]
    val = evaluate(split["validation"],unis,axis,coords,panel,model,arms,args.batch,args.memory_budget_mib)
    val.to_csv(args.out/"validation_per_target.csv", index=False)
    selected, validation = choose(val)
    write_json(args.out/"selection.json", {"selected": selected, "validation": validation, "scalars": model["scalars"]})
    if selected == "identity":
        write_json(args.out/"summary.json", {"status": "no_candidate_selected", "selection": validation,
                   "test_evaluated": False, "peak_rss_bytes": peak_rss_bytes()})
        print("No candidate selected; test targets were not evaluated", flush=True)
        return
    arms = [selected, "identity", "scalar", "zero"]
    summary = {"status": "evaluated", "selected": selected, "scalars": model["scalars"], "support_genes": int(model["support"].sum())}
    for phase in ["test", "panel"]:
        result = evaluate(split[phase],unis,axis,coords,panel,model,arms,args.batch,args.memory_budget_mib)
        result.to_csv(args.out/f"{phase}_per_target.csv", index=False)
        summary[phase] = summarize(result, selected)
    summary["panel_consistent"] = bool(summary["panel"]["mean_cosine_gain"] is not None and summary["panel"]["mean_cosine_gain"] >= 0)
    summary["claim_type"] = "internal held-target cross-study effect-space test, not VCC accuracy or new-cell-line validation"
    for u in unis.values():
        u._cache.clear()
    gc.collect()
    summary["peak_rss_bytes"] = peak_rss_bytes()
    write_json(args.out/"summary.json",summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
