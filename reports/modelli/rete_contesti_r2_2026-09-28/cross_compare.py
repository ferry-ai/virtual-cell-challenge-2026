"""Reading A of the r2 round (RISULTATI.md): the network on r2 against the network on r1, paired on the same test
targets and genes, with the effect-space diagnostics of encoder_contesto_2026-09-28/compare.py.

For each design and truth context:
* r1: pred_<truth>.npz of the r1 run (train.py on the r1 dataset, seed 0), float32, cast to float16 here;
* r2: the kept float16 predictions of the r2 round (`keep_pred/<design>/<condition>/seed0/pred_<truth>.npz`);
* truth and SE from the r2 dataset (the universes are the same; r2 stores more genes); genes = those both networks
  predict (finite in both), weights as train.py (gene weight of the truth context, 1 / (k SE^2 + tau2)).
Contrasts (skill differences, bootstrap over targets): r2 none - r1 none, and, with --r2-condition ours, r2 ours -
r1 none and r2 ours - r2 none; E2 on the Orion pair for each run.

    scripts/py.cmd reports/modelli/rete_contesti_r2_2026-09-28/cross_compare.py --r1 <r1 run root> --r2 <keep_pred root> \
        --data-r2 C:/Users/ferra/vcc2026-data/processed/rete_contesti_r2 --out <new dir>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
os.environ.setdefault("RETE_CONTESTI_CODE", str(REPO / "reports" / "modelli" / "rete_contesti_2026-09-27"))
sys.path.insert(0, str(REPO / "reports" / "modelli" / "encoder_contesto_2026-09-28"))

import compare as C  # noqa: E402
import pool as P  # noqa: E402

DESIGNS = {  # design: (r1 run folder name, truth contexts)
    "e1_k562": ("e1_k562_s0", ["k562"]),
    "e1_orion": ("e1_hct116_s0", ["orion_hct116"]),
    "e1_cd4": ("e1_cd4_s0", ["cd4_Rest"]),
    "e2_orion": ("e2_orion_s0", ["orion_hct116", "orion_hek293t"]),
}


def on_pool(z: dict, pool: P.Pool, key: str) -> np.ndarray:
    """A prediction arm (full official axis) on the pool's stored genes, float16-rounded, NaN where not predicted."""
    x = np.asarray(z[key], dtype=np.float32)[:, pool.genes_axis]
    return x.astype(np.float16).astype(np.float32)


def load(path: Path, targets: list | None):
    z = C.read_npz(path)
    if targets is not None and z["targets"] != targets:
        order = {t: i for i, t in enumerate(z["targets"])}
        idx = [order[t] for t in targets]
        z = {k: (v[idx] if isinstance(v, np.ndarray) and v.ndim == 2 else v) for k, v in z.items()}
        z["targets"] = targets
    return z


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--r1", type=Path, required=True, help="folder with the r1 run folders (e1_k562_s0, ...)")
    ap.add_argument("--r2", type=Path, required=True, help="keep_pred root of the r2 round")
    ap.add_argument("--data-r2", type=Path, required=True)
    ap.add_argument("--r2-conditions", default="none,ours")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tau2", type=float, default=0.01)
    ap.add_argument("--n-boot", type=int, default=1000)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    pool = P.Pool.from_dir(args.data_r2)
    conds = [c.strip() for c in args.r2_conditions.split(",") if c.strip()]
    rows, e2rows = [], []
    for design, (r1name, truths) in DESIGNS.items():
        blocks = {}
        for truth in truths:
            p1 = args.r1 / r1name / f"pred_{truth}.npz"
            if not p1.exists():
                print(f"skip {design} {truth}: no r1 predictions", flush=True)
                continue
            z1 = load(p1, None)
            targets = z1["targets"]
            arms = {"r1_net": on_pool(z1, pool, "net"), "r1_blind": on_pool(z1, pool, "blind")}
            for c in conds:
                p2 = args.r2 / design / c / "seed0" / f"pred_{truth}.npz"
                if not p2.exists():
                    print(f"  {design} {truth}: no r2 {c} predictions", flush=True)
                    continue
                z2 = load(p2, targets)
                arms[f"r2_{c}_net"] = on_pool(z2, pool, "net")
                arms[f"r2_{c}_blind"] = on_pool(z2, pool, "blind")
            if not any(k.startswith("r2_") for k in arms):
                continue
            raw, se = C.truth_block(pool, truth, targets)
            keep = np.isfinite(arms["r1_net"])
            for k, v in arms.items():
                if k.endswith("_net"):
                    keep &= np.isfinite(v)
            k_se = float(pool.ctx_se_factor[pool.context_index[truth]])
            pairs = [(a, "r1_net") for a in arms if a.startswith("r2_") and a.endswith("_net")]
            pairs += [("r1_net", "r1_blind")] + [(a, a.replace("_net", "_blind")) for a in arms
                                                  if a.startswith("r2_") and a.endswith("_net")]
            if "r2_ours_net" in arms and "r2_none_net" in arms:
                pairs.append(("r2_ours_net", "r2_none_net"))
            res = C.effect_diagnostics(raw, se, arms, C.gene_weight(pool, truth, "context"), k_se, args.tau2, keep,
                                       C.disc_drop_of(pool, targets), np.random.default_rng([0, 3]), pairs, args.n_boot)
            for (a, b), st in res["contrasts"].items():
                for stratum in ("all", "strong"):
                    s = st[stratum]["skill"]
                    rows.append({"design": design, "truth": truth, "a": a, "b": b, "stratum": stratum,
                                 "mean": s["mean"], "lo": s["ci95"][0], "hi": s["ci95"][1], "n": s["n"],
                                 "genes": int(keep.any(axis=0).sum())})
            for name, v in res["arms"].items():
                rows.append({"design": design, "truth": truth, "a": name, "b": "(skill)", "stratum": "all",
                             "mean": v["skill"], "lo": None, "hi": None, "n": res["targets_scored"],
                             "genes": int(keep.any(axis=0).sum())})
            blocks[truth] = (raw, arms, keep, C.gene_weight(pool, truth, "context"))
            print(f"{design} {truth}: " + ", ".join(f"{a}-{b} {st['all']['skill']['mean']:+.4f} "
                                                    f"[{st['all']['skill']['ci95'][0]:+.4f},{st['all']['skill']['ci95'][1]:+.4f}]"
                                                    for (a, b), st in res["contrasts"].items()), flush=True)
        if design == "e2_orion" and len(blocks) == 2:
            (y1, A1, k1, g1), (y2, A2, k2, g2) = blocks["orion_hct116"], blocks["orion_hek293t"]
            nets = [a for a in A1 if a.endswith("_net") and a in A2]
            e2 = C.e2_diagnostics(y1, y2, {a: A1[a] for a in nets}, {a: A2[a] for a in nets}, 0.5 * (g1 + g2),
                                  k1 & k2, np.random.default_rng([0, 5]))
            for a, v in e2.items():
                e2rows.append({"arm": a, "mean": v.get("mean"), "lo": v.get("ci95", [None, None])[0],
                               "hi": v.get("ci95", [None, None])[1], "perm_q975": v.get("perm_q975"),
                               "perm_p": v.get("perm_p")})
                print(f"E2 {a}: {v.get('mean')} {v.get('ci95')} perm q975 {v.get('perm_q975')}", flush=True)
    import pandas as pd
    pd.DataFrame(rows).to_csv(args.out / "contrasts.csv", index=False)
    pd.DataFrame(e2rows).to_csv(args.out / "e2.csv", index=False)
    with (args.out / "summary.json").open("x", encoding="utf-8") as fh:
        json.dump({"stage": "rete_contesti_r2_2026-09-28/cross_compare.py", "r1": str(args.r1), "r2": str(args.r2),
                   "conditions": conds, "tau2": args.tau2,
                   "claim_type": "effect-space diagnostics on held-out public contexts; not VCC scores"}, fh, indent=1)


if __name__ == "__main__":
    main()
