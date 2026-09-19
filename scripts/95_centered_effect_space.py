"""Stage 95: the target-SPECIFIC part of an effect prediction, in effect space.

Under squared loss the best predictor is the conditional mean, so where the descriptors carry
little information the mean response is near optimal and nothing can beat it; and a constant
vector still correlates with every target, because knockdowns share a response. Raw per-target
correlation and MSE therefore cannot separate "it predicts this target" from "it predicts what
every target does". This stage removes the mean over the evaluated targets from BOTH the
prediction and the truth and reports:

* ``pearson_centered``  -- correlation of the deviations from the mean response;
* ``skill_vs_mean``     -- 1 - MSE(model) / MSE(mean predictor): positive only if the model
  beats the constant mean of the training labels;
* ``match_rate``        -- of the evaluated targets, the share whose prediction is closest (by
  centered cosine) to its OWN truth rather than to another target's: discrimination, which a
  constant prediction cannot win.

Truth comes from the same source the split was judged against: HepG2 cells (`--hepg2`) or the
K562 bulk labels (`--k562-bulk`). Bootstrap over targets, 2.000 resamples.

    python scripts/95_centered_effect_space.py --pred NAME=<npz> [--pred ...] \
        --hepg2 <h5ad> --mean-pred <npz with the mean predictor> --out <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import log  # noqa: E402
from vcc2026.predictor_sc import effects_from_bulk  # noqa: E402
from vcc2026.sc_effects import eb_shrink, fraction_stats, log_effect  # noqa: E402
from vcc2026.sc_stream import read_frame, read_rows  # noqa: E402


def hepg2_truth(path: Path, targets: list[str], genes: np.ndarray) -> np.ndarray:
    with h5py.File(path, "r") as f:
        sym = read_frame(f["obs"])["gene"].astype(str).to_numpy()
        names = read_frame(f["var"]).index.astype(str).to_numpy()
        pos = pd.Index(names).get_indexer(genes)
        if (pos < 0).any():
            raise SystemExit("a predicted gene is absent from HepG2")
        x = f["X"]
        ctrl = fraction_stats(read_rows(x, np.flatnonzero(sym == "non-targeting")))
        rows = []
        for i, t in enumerate(targets):
            st = fraction_stats(read_rows(x, np.flatnonzero(sym == t)))
            e, s = log_effect(st, ctrl)
            rows.append(eb_shrink(e, s, ctrl.mean > 0)[0][pos])
            if (i + 1) % 50 == 0:
                log(f"  truth for {i + 1}/{len(targets)} targets")
    return np.stack(rows)


def bulk_truth(path: Path, targets: list[str], genes: np.ndarray) -> np.ndarray:
    with h5py.File(path, "r") as f:
        labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
        means, cells = f["X"][:], f["obs/num_cells_filtered"][:]
        names = read_frame(f["var"])["gene_name"].astype(str).to_numpy()
    ntc = np.array(["non-targeting" in lab for lab in labels])
    syms = np.array(["non-targeting" if nt else lab.split("_")[1] for lab, nt in zip(labels, ntc)])
    eff = effects_from_bulk(means, cells, syms, ntc, names, targets=targets)
    pos = pd.Index(eff.genes).get_indexer(genes)
    idx = eff.index()
    return np.stack([eff.shrunk[idx[t]][pos] for t in targets])


def metrics(pred: np.ndarray, truth: np.ndarray, mean_pred: np.ndarray | None, rng, n_boot=2000) -> dict:
    pc, tc = pred - pred.mean(axis=0), truth - truth.mean(axis=0)
    per = np.array([np.corrcoef(a, b)[0, 1] if a.std() > 0 and b.std() > 0 else 0.0 for a, b in zip(pc, tc)])
    mse = ((pred - truth) ** 2).mean(axis=1)
    norm = np.linalg.norm(pc, axis=1)[:, None] * np.linalg.norm(tc, axis=1)[None, :] + 1e-12
    sim = (pc @ tc.T) / norm
    match = (sim.argmax(axis=1) == np.arange(len(pc))).astype(float)
    idx = rng.integers(0, len(per), (n_boot, len(per)))
    out = {"pearson_centered": float(per.mean()),
           "pearson_centered_ci95": np.quantile(per[idx].mean(1), [0.025, 0.975]).tolist(),
           "match_rate": float(match.mean()), "match_rate_ci95": np.quantile(match[idx].mean(1), [0.025, 0.975]).tolist(),
           "mse": float(mse.mean()), "n_targets": int(len(per)), "chance_match": 1.0 / len(per)}
    if mean_pred is not None:
        base = ((mean_pred - truth) ** 2).mean(axis=1)
        skill = 1.0 - mse.mean() / base.mean()
        sk = 1.0 - mse[idx].mean(1) / base[idx].mean(1)
        out |= {"skill_vs_mean": float(skill), "skill_vs_mean_ci95": np.quantile(sk, [0.025, 0.975]).tolist()}
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pred", action="append", required=True, metavar="NAME=NPZ")
    p.add_argument("--hepg2", type=Path, default=None)
    p.add_argument("--k562-bulk", type=Path, default=None)
    p.add_argument("--label", required=True, help="what is being evaluated, e.g. C_hepg2_test")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, default=2026)
    args = p.parse_args()
    if (args.out / f"centered_{args.label}.json").exists():
        raise SystemExit(f"{args.out} already holds {args.label}")
    preds = {}
    for spec in args.pred:
        name, _, path = spec.partition("=")
        z = np.load(path)
        preds[name] = (z["targets"].astype(str).tolist(), z["genes"].astype(str), z["lfc"].astype(np.float64))
    targets, genes, _ = next(iter(preds.values()))
    for name, (t, g, _) in preds.items():
        if t != targets or list(g) != list(genes):
            raise SystemExit(f"{name} is not on the same targets and genes as the others")
    if args.hepg2:
        truth = hepg2_truth(args.hepg2, targets, genes)
    elif args.k562_bulk:
        truth = bulk_truth(args.k562_bulk, targets, genes)
    else:
        raise SystemExit("give --hepg2 or --k562-bulk")
    rng = np.random.default_rng(args.seed)
    mean_pred = preds["mean"][2] if "mean" in preds else None
    out = {name: metrics(arr, truth, mean_pred, rng) for name, (_, _, arr) in preds.items()}
    out["_truth"] = {"source": str(args.hepg2 or args.k562_bulk), "n_targets": len(targets), "n_genes": len(genes),
                     "rms": float(np.sqrt((truth ** 2).mean())),
                     "mean_response_share": float(np.linalg.norm(truth.mean(axis=0)) / np.linalg.norm(truth, axis=1).mean())}
    args.out.mkdir(parents=True, exist_ok=True)
    # exclusive create: two runs started together both pass the check at startup (it happened
    # on 2026-09-19 with J_hepg2_test); the second must fail here, not overwrite the first
    with open(args.out / f"centered_{args.label}.json", "x", encoding="utf-8") as fh:
        fh.write(json.dumps({"stage": "95_centered_effect_space", "finished_utc": datetime.now(timezone.utc).isoformat(),
                             "label": args.label, "results": out}, indent=2))
    print(f"== {args.label}  truth {out['_truth']}")
    for name, m in out.items():
        if name.startswith("_"):
            continue
        s = f" skill_vs_mean {m['skill_vs_mean']:+.4f} [{m['skill_vs_mean_ci95'][0]:+.4f},{m['skill_vs_mean_ci95'][1]:+.4f}]" if "skill_vs_mean" in m else ""
        print(f"{name:14s} pearson_centered {m['pearson_centered']:+.4f} "
              f"[{m['pearson_centered_ci95'][0]:+.4f},{m['pearson_centered_ci95'][1]:+.4f}]  "
              f"match {m['match_rate']:.3f} (chance {m['chance_match']:.3f}){s}")


if __name__ == "__main__":
    main()
