"""Stage 89: apply `configs/specificity_rule.yaml` to two stage-75 benches with shuffled arms.

``shuffled_aX`` gives each target another target's source effect: same source, same amplitude,
same effect sizes, no target identity. What transfer gains over it is target-specific; what it
does not is carried by anything all signatures share. Mechanically, in the rule's order:

1. reproducibility gate: the anchors and the transfer arms must equal the earlier benches
   (`--reference`), which drew the same random numbers; otherwise nothing is read;
2. per source and amplitude, S = fidelity(transfer) - fidelity(shuffled), paired per target;
3. at the volume-matched pair, the source gap split into a common and a specific part;
4. the verdicts, with a paired bootstrap over targets (target sampling only).

    python scripts/89_specificity_reading.py --rule configs/specificity_rule.yaml \
        --bench k562=<run dir> --bench rpe1=<run dir> \
        --reference k562=<bench.json> --reference rpe1=<bench.json> --out <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

GATE_ARMS = ["replicate", "baseline", "null_new", "transfer_a0.5", "transfer_a1.0", "transfer_a2.0"]
AMPS = ["0.5", "1.0", "2.0"]


def per_target(run: Path, arm: str, metric: str) -> pd.Series:
    f = pd.read_csv(run / f"per_pert_{arm}.csv")
    return f[f.metric == metric].set_index("perturbation")["value"]


def boot_ci(cols: dict[str, np.ndarray], n: int, seed: int) -> dict[str, list[float]]:
    """Percentile 95% intervals of several per-target means, resampled JOINTLY over targets."""
    rng = np.random.default_rng(seed)
    size = next(iter(cols.values())).size
    idx = rng.integers(0, size, (n, size))
    return {k: [float(np.quantile(v[idx].mean(axis=1), 0.025)), float(np.quantile(v[idx].mean(axis=1), 0.975))]
            for k, v in cols.items()}


def excludes_zero(ci: list[float]) -> bool:
    return ci[0] > 0 or ci[1] < 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rule", type=Path, required=True)
    p.add_argument("--bench", action="append", required=True, metavar="NAME=DIR")
    p.add_argument("--reference", action="append", required=True, metavar="NAME=BENCH_JSON")
    p.add_argument("--challenger", default="rpe1")
    p.add_argument("--pair", nargs=2, default=["0.5", "1.0"], metavar=("CH_AMP", "INC_AMP"),
                   help="the volume-matched amplitudes of the rule's decomposition (challenger, incumbent)")
    p.add_argument("--tol", type=float, default=1e-9)
    p.add_argument("--boot", type=int, default=10000)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.out / "specificity.json").exists():
        raise SystemExit(f"{args.out} already holds a reading; choose a new --out")
    rule = yaml.safe_load(args.rule.read_text(encoding="utf-8"))
    metric = rule["metric"]
    floor = float(rule.get("practical_floor", 0.0))
    runs = {k: Path(v) for k, v in (s.split("=", 1) for s in args.bench)}
    refs = {k: Path(v) for k, v in (s.split("=", 1) for s in args.reference)}
    ch = args.challenger
    inc = next(k for k in runs if k != ch)
    benches = {k: json.loads((d / "bench.json").read_text(encoding="utf-8")) for k, d in runs.items()}
    old = {k: json.loads(v.read_text(encoding="utf-8")) for k, v in refs.items()}

    # 1. reproducibility gate
    failures = []
    for k in runs:
        if benches[k]["targets"] != old[k]["targets"]:
            failures.append(f"{k}: target panel differs from the reference")
        for arm in GATE_ARMS:
            new, ref = benches[k]["results"].get(arm), old[k]["results"].get(arm)
            if new is None or ref is None:
                failures.append(f"{k}.{arm}: missing")
                continue
            for m, v in ref["raw"].items():
                if v is not None and (new["raw"].get(m) is None or abs(new["raw"][m] - v) > args.tol):
                    failures.append(f"{k}.{arm}.{m}: {new['raw'].get(m)} vs reference {v}")
    gate = {"passed": not failures, "failures": failures[:20], "tol": args.tol}

    # 2. specificity per source and amplitude
    spec: dict[str, dict] = {}
    for k, run in runs.items():
        spec[k] = {}
        for a in AMPS:
            t, s = per_target(run, f"transfer_a{a}", metric), per_target(run, f"shuffled_a{a}", metric)
            both = t.dropna().index.intersection(s.dropna().index)
            d = (t[both] - s[both]).to_numpy()
            ci = boot_ci({"S": d}, args.boot, args.seed)["S"]
            res = benches[k]["results"]
            spec[k][a] = {"S_mean": float(d.mean()), "ci95": ci, "n_targets": int(d.size),
                          "fidelity_transfer": res[f"transfer_a{a}"]["raw"][metric],
                          "fidelity_shuffled": res[f"shuffled_a{a}"]["raw"][metric],
                          "sig_t_transfer": res[f"transfer_a{a}"]["n_sig_per_target"],
                          "sig_t_shuffled": res[f"shuffled_a{a}"]["n_sig_per_target"],
                          "components_transfer": res[f"transfer_a{a}"].get("components"),
                          "components_shuffled": res[f"shuffled_a{a}"].get("components")}
        rows = [spec[k][a] for a in AMPS]
        if all(r["ci95"][0] > 0 and r["S_mean"] >= floor for r in rows):
            spec[k]["verdict"] = "SPECIFIC"
        elif all(not excludes_zero(r["ci95"]) or abs(r["S_mean"]) < floor for r in rows):
            spec[k]["verdict"] = "NOT_SPECIFIC"
        else:
            spec[k]["verdict"] = "MIXED"

    # 3. decomposition of the source gap at the volume-matched pair
    ca, ia = args.pair
    s = {(k, kind): per_target(runs[k], f"{kind}_a{amp}", metric)
         for k, amp in ((ch, ca), (inc, ia)) for kind in ("transfer", "shuffled")}
    common_idx = s[(ch, "transfer")].dropna().index
    for v in s.values():
        common_idx = common_idx.intersection(v.dropna().index)
    tr_c, sh_c = s[(ch, "transfer")][common_idx].to_numpy(), s[(ch, "shuffled")][common_idx].to_numpy()
    tr_i, sh_i = s[(inc, "transfer")][common_idx].to_numpy(), s[(inc, "shuffled")][common_idx].to_numpy()
    parts = {"gap": tr_c - tr_i, "common": sh_c - sh_i, "specific": (tr_c - sh_c) - (tr_i - sh_i)}
    cis = boot_ci(parts, args.boot, args.seed)
    dec = {"pair": {ch: f"transfer_a{ca}/shuffled_a{ca}", inc: f"transfer_a{ia}/shuffled_a{ia}"},
           "n_targets": int(common_idx.size), **{k: {"mean": float(v.mean()), "ci95": cis[k]} for k, v in parts.items()}}
    present = {k: excludes_zero(cis[k]) and abs(float(parts[k].mean())) >= floor for k in ("common", "specific")}
    for k in present:
        dec[k]["present"] = present[k]
    cc, sc = present["common"], present["specific"]
    dec["verdict"] = ("BOTH" if cc and sc else "MAINLY_COMMON" if cc else "MAINLY_SPECIFIC" if sc else "UNDETERMINED")
    if not gate["passed"]:
        for k in runs:
            spec[k]["verdict"] = "VOID"
        dec["verdict"] = "VOID"

    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage": "89_specificity_reading", "finished_utc": datetime.now(timezone.utc).isoformat(),
        "rule": str(args.rule), "rule_version": rule.get("version"),
        "rule_md5": hashlib.md5(args.rule.read_bytes()).hexdigest(),
        "inputs": {k: {"dir": str(d), "bench_md5": hashlib.md5((d / "bench.json").read_bytes()).hexdigest(),
                       "reference": str(refs[k])} for k, d in runs.items()},
        "metric": metric, "practical_floor": floor, "boot": args.boot, "seed": args.seed,
        "bootstrap_covers": "target sampling only; not generator randomness, not the half A/B split",
        "reproducibility_gate": gate, "specificity": spec, "decomposition": dec,
    }
    (args.out / "specificity.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"reproducibility gate: {'PASSED' if gate['passed'] else 'FAILED'}")
    for f in failures[:10]:
        print("  -", f)
    for k in runs:
        print(k, spec[k]["verdict"], " ".join(
            f"a{a}: S={spec[k][a]['S_mean']:+.4f} [{spec[k][a]['ci95'][0]:+.4f},{spec[k][a]['ci95'][1]:+.4f}] "
            f"sig/t {spec[k][a]['sig_t_transfer']:.0f}/{spec[k][a]['sig_t_shuffled']:.0f}" for a in AMPS))
    print("decomposition", dec["verdict"], {k: dec[k] for k in ("gap", "common", "specific")})
    print(f"wrote {args.out / 'specificity.json'}")


if __name__ == "__main__":
    main()
