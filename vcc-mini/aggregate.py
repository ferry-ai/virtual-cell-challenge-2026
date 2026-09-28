"""Combine seeds and apply the reading rule to a set of runs.

    python aggregate.py runs/real_*  --out runs/aggregate_<date>.json

Rule (DRAFT, section 12 of the review; it binds only once Alfredo approves it, before the runs):
  - regime CT, the held-out line of each group (K562: the genome-wide experiment K562_gw);
  - reference: whichever of transfer_simple and transfer_gamma1 has the lower validation MSE,
    averaged over the seeds of that fold;
  - per-target metrics are averaged over seeds, then 2,000 paired bootstrap resamples of the
    targets give 95% intervals of (model - reference);
  - a line passes if the MSE interval lies entirely below 0 (model better) and the pds_rank
    interval does not lie entirely above 0 (model not worse);
  - the model passes if at least 3 of the 4 held-out lines pass. J, C and CT_max2 are reported only.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

PRIMARY = {"K562": "K562_gw"}
N_BOOT = 2000


def ci(diff, rng):
    boots = diff[rng.integers(0, len(diff), size=(N_BOOT, len(diff)))].mean(1)
    return dict(mean=float(diff.mean()), lo=float(np.quantile(boots, .025)), hi=float(np.quantile(boots, .975)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--regime", default="CT")
    args = ap.parse_args()
    out = Path(args.out)
    assert not out.exists(), "never overwrite an aggregate"
    rng = np.random.default_rng(2026)
    by_fold = defaultdict(list)
    for r in args.runs:
        rec = json.loads((Path(r) / "results.json").read_text())
        by_fold[(rec["args"]["held"], rec["args"]["fold"])].append((Path(r), rec))

    report = dict(rule="draft, section 12 of the review", regime=args.regime, lines={})
    for (held, fold), runs in sorted(by_fold.items()):
        key = PRIMARY.get(held, held)
        vm = defaultdict(list)
        for _, rec in runs:
            for k, v in rec["reference_val_mse"].items():
                vm[k].append(v)
        ref = min(vm, key=lambda k: np.mean(vm[k]))
        arrays = [np.load(p / "per_target.npz") for p, _ in runs]
        tkey = f"{key}|{args.regime}|targets"
        targets = [a[tkey] for a in arrays if tkey in a]
        if len(targets) != len(runs):
            report["lines"][f"{held}/f{fold}"] = {"skipped": f"regime {args.regime} missing in some seeds"}
            continue
        assert all((t == targets[0]).all() for t in targets), "seeds evaluated different targets"
        avg = lambda meth, m: np.mean([a[f"{key}|{args.regime}|{meth}|{m}"] for a in arrays], axis=0)
        d_mse = avg("model", "mse") - avg(ref, "mse")
        d_pds = avg("model", "pds_rank") - avg(ref, "pds_rank")
        c_mse, c_pds = ci(d_mse, rng), ci(d_pds, rng)
        passed = c_mse["hi"] < 0 and not c_pds["lo"] > 0
        report["lines"][f"{held}/f{fold}"] = dict(
            line=key, seeds=[rec["args"]["seed"] for _, rec in runs], n_targets=int(len(d_mse)),
            reference=ref, reference_val_mse={k: float(np.mean(v)) for k, v in vm.items()},
            model_mse=float(avg("model", "mse").mean()), reference_mse=float(avg(ref, "mse").mean()),
            oracle_mean_mse=float(avg("oracle_mean", "mse").mean()),
            model_pds_rank=float(avg("model", "pds_rank").mean()), reference_pds_rank=float(avg(ref, "pds_rank").mean()),
            delta_mse=c_mse, delta_pds_rank=c_pds, passes=bool(passed))
    lines = [v for v in report["lines"].values() if "passes" in v]
    report["lines_passing"] = sum(v["passes"] for v in lines)
    report["lines_evaluated"] = len(lines)
    report["model_passes"] = report["lines_passing"] >= 3 and len(lines) >= 4
    out.write_text(json.dumps(report, indent=1))
    for name, v in report["lines"].items():
        if "passes" not in v:
            print(name, v)
            continue
        print(f"{name:12s} ref={v['reference']:15s} n={v['n_targets']:4d} "
              f"dMSE {v['delta_mse']['mean']:+.5f} [{v['delta_mse']['lo']:+.5f},{v['delta_mse']['hi']:+.5f}] "
              f"dPDS {v['delta_pds_rank']['mean']:+.3f} [{v['delta_pds_rank']['lo']:+.3f},{v['delta_pds_rank']['hi']:+.3f}] "
              f"{'PASS' if v['passes'] else 'no'}")
    print(f"lines passing {report['lines_passing']}/{report['lines_evaluated']} -> model passes: {report['model_passes']}")


if __name__ == "__main__":
    main()
