"""Stage 88: read two stage-75 benches at matched call volume, not at matched amplitude.

On the HepG2 bench `de_wilcoxon_direction_fidelity_yield_raw` grows with the number of genes
a prediction declares significant (CP-0021), so two sources compared at the same amplitude
also differ in how much they call. This stage gives two readings, kept apart on purpose:

1. **pre-registered** (`reports/source_lineage_2026-09-18/PRIMA_DEI_RISULTATI.md` §1): each
   source's primary arms give points (sig/t, metric); the metric is interpolated piecewise
   linearly in log(sig/t), ONLY inside the sig/t range both sources cover, and the gap is read
   at every breakpoint in that range (the gap is linear between them, so these hold its
   extremes). It matches MEAN calls per target, not their distribution across targets: an
   approximate volume correction, not a causal one;
2. **exploratory, chosen after the results**: for each challenger arm, the incumbent arm
   closest in log(sig/t), kept if the two differ by less than `--max-ratio`; the per-target
   metric (from `per_pert_<arm>.csv`) is compared on targets defined in BOTH arms, with a
   paired bootstrap over targets. That interval covers which targets were drawn, not the
   generator's randomness nor the half A / half B split.

    python scripts/88_matched_volume_reading.py --bench k562=<run dir> --bench rpe1=<run dir> \
        --challenger rpe1 --out <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PRIMARY = ["transfer_a0.5", "transfer_a1.0", "transfer_a2.0"]
METRIC = "de_wilcoxon_direction_fidelity_yield_raw"


def curve(bench: dict, arms: list[str], metric: str) -> pd.DataFrame:
    rows = [{"arm": a, "sig_t": bench["results"][a]["n_sig_per_target"],
             "value": bench["results"][a]["raw"][metric]} for a in arms]
    return pd.DataFrame(rows).sort_values("sig_t").reset_index(drop=True)


def interp(c: pd.DataFrame, x: float) -> float:
    return float(np.interp(np.log(x), np.log(c["sig_t"].to_numpy()), c["value"].to_numpy()))


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bench", action="append", required=True, metavar="NAME=DIR",
                   help="a stage-75 output directory (bench.json + per_pert_<arm>.csv); exactly two")
    p.add_argument("--challenger", default="rpe1")
    p.add_argument("--arms", nargs="+", default=PRIMARY)
    p.add_argument("--metric", default=METRIC)
    p.add_argument("--threshold", type=float, default=0.03, help="the rule's gap, for the pre-registered reading")
    p.add_argument("--max-ratio", type=float, default=1.5, help="exploratory pairing: max sig/t ratio")
    p.add_argument("--boot", type=int, default=10000)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if len(args.bench) != 2:
        raise SystemExit("--bench must be given exactly twice")
    if (args.out / "matched_volume.json").exists():
        raise SystemExit(f"{args.out} already holds a reading; choose a new --out")

    dirs = dict(spec.split("=", 1) for spec in args.bench)
    dirs = {k: Path(v) for k, v in dirs.items()}
    ch = args.challenger
    inc = next(k for k in dirs if k != ch)
    benches = {k: json.loads((d / "bench.json").read_text(encoding="utf-8")) for k, d in dirs.items()}
    curves = {k: curve(b, args.arms, args.metric) for k, b in benches.items()}

    # 1. pre-registered: interpolation inside the common sig/t range
    lo = max(c["sig_t"].min() for c in curves.values())
    hi = min(c["sig_t"].max() for c in curves.values())
    pre: dict[str, object] = {"common_sig_t_range": [lo, hi] if lo <= hi else None}
    if lo <= hi:
        xs = sorted({lo, hi} | {x for c in curves.values() for x in c["sig_t"] if lo <= x <= hi})
        pts = [{"sig_t": x, ch: interp(curves[ch], x), inc: interp(curves[inc], x),
                "gap": interp(curves[ch], x) - interp(curves[inc], x)} for x in xs]
        gaps = [q["gap"] for q in pts]
        amp_gaps = [benches[ch]["results"][a]["raw"][args.metric] - benches[inc]["results"][a]["raw"][args.metric]
                    for a in args.arms]
        pre |= {"points": pts, "gap_min": min(gaps), "gap_max": max(gaps),
                "gap_at_same_amplitude": dict(zip(args.arms, amp_gaps)),
                "reading": ("the advantage attenuates under an approximate volume correction"
                            if (min(gaps) < args.threshold or min(gaps) * max(gaps) < 0)
                            else f"the advantage attenuates but stays >= {args.threshold} at matched mean calls")}
    else:
        pre["reading"] = "the sig/t ranges do not overlap: volume and direction are not separable here"

    # 2. exploratory: paired per-target comparison at nearest volume
    rng = np.random.default_rng(args.seed)
    pairs = []
    for a in args.arms:
        x = benches[ch]["results"][a]["n_sig_per_target"]
        b = min(args.arms, key=lambda arm: abs(np.log(benches[inc]["results"][arm]["n_sig_per_target"] / x)))
        y = benches[inc]["results"][b]["n_sig_per_target"]
        if max(x, y) / min(x, y) > args.max_ratio:
            continue
        per = {}
        for name, arm in ((ch, a), (inc, b)):
            f = pd.read_csv(dirs[name] / f"per_pert_{arm}.csv")
            per[name] = f[f.metric == args.metric].set_index("perturbation")["value"]
        both = per[ch].dropna().index.intersection(per[inc].dropna().index)
        d = (per[ch][both] - per[inc][both]).to_numpy()
        boot = np.array([d[rng.integers(0, d.size, d.size)].mean() for _ in range(args.boot)])
        pairs.append({f"{ch}_arm": a, f"{inc}_arm": b, f"{ch}_sig_t": x, f"{inc}_sig_t": y,
                      "n_targets_both_defined": int(d.size), "mean_diff": float(d.mean()),
                      "ci95": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))],
                      "frac_targets_challenger_higher": float(np.mean(d > 0)),
                      "frac_targets_equal": float(np.mean(d == 0))})

    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage": "88_matched_volume_reading",
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {k: {"dir": str(d), "bench_md5": md5(d / "bench.json")} for k, d in dirs.items()},
        "challenger": ch, "incumbent": inc, "metric": args.metric, "arms": args.arms,
        "curves": {k: c.to_dict(orient="records") for k, c in curves.items()},
        "preregistered_matched_mean_volume": pre,
        "exploratory_paired_nearest_volume": {
            "chosen_after_results": True, "max_ratio": args.max_ratio, "boot": args.boot, "seed": args.seed,
            "covers": "target sampling only; not generator randomness, not the half A/B split",
            "pairs": pairs},
    }
    (args.out / "matched_volume.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for k, c in curves.items():
        print(k, " ".join(f"({r.sig_t:.1f}, {r.value:.4f})" for r in c.itertuples()))
    print("pre-registered:", json.dumps(pre, indent=1))
    print("exploratory:", json.dumps(pairs, indent=1))
    print(f"wrote {args.out / 'matched_volume.json'}")


if __name__ == "__main__":
    main()
