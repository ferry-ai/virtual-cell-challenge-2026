"""Stage 94: apply `configs/conditioned_rule.yaml` to the two test benches -- KEEP or DISCARD.

Reads the HepG2 and K562 test benches (stages 75 and 73 with stage 92's effects at the
amplitudes stage 93 chose on the validation benches), scores every arm in official-anchor
units, and evaluates the rule's five conditions with paired bootstraps over targets. Writes the
verdict and the full raw table, so the numbers the verdict rests on are next to it.

    python scripts/94_conditioned_verdict.py --rule configs/conditioned_rule.yaml \
        --hepg2 <hepg2 test dir> --k562 <k562 test dir> --picks <dir with picks_*.json> \
        --anchors <anchors.json> --status <t03 status json> --out <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench_score import (  # noqa: E402
    SCORED,
    calibration,
    consistency,
    member_means,
    paired_bootstrap,
    per_target,
    score,
)

MIN_GAIN = 0.01


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rule", type=Path, required=True)
    p.add_argument("--hepg2", type=Path, required=True)
    p.add_argument("--k562", type=Path, required=True)
    p.add_argument("--picks", type=Path, required=True)
    p.add_argument("--anchors", type=Path, required=True)
    p.add_argument("--status", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.out / "verdict.json").exists():
        raise SystemExit(f"{args.out} already holds a verdict; choose a new --out")
    rule = yaml.safe_load(args.rule.read_text(encoding="utf-8"))
    anchors = json.loads(args.anchors.read_text(encoding="utf-8"))["anchors"]
    status = json.loads(args.status.read_text(encoding="utf-8-sig"))
    picks = {k: json.loads((args.picks / f"picks_{k}.json").read_text(encoding="utf-8"))["picks"] for k in ("hepg2", "k562")}
    t03 = rule["families"]["fixed_arms"]["t03"]
    ratio = calibration(args.hepg2, t03, status)

    def arm(kind, fam, perm=False):
        return f"{fam}{'perm' if perm else ''}_a{picks[kind][fam]}"

    # every arm of both benches, raw and scored
    rows = []
    for kind, run, rat in (("hepg2", args.hepg2, ratio), ("k562", args.k562, None)):
        bench = json.loads((run / "bench.json").read_text(encoding="utf-8"))["results"]
        for a, res in bench.items():
            if not (run / f"per_pert_{a}.csv").exists():
                continue
            mm = member_means(per_target(run, a))
            rows.append({"bench": kind, "arm": a, "score": score(mm, anchors, rat), "sig_t": res["n_sig_per_target"],
                         **{m: res["raw"][m] for m in SCORED},
                         "max_abs_consistency_gap": max(consistency(run, a).values())})
    table = pd.DataFrame(rows)

    def cmp(kind, a, b):
        run, rat = (args.hepg2, ratio) if kind == "hepg2" else (args.k562, None)
        return {"a": a, "b": b, **paired_bootstrap(run, a, b, anchors, rat)}

    c = {
        "Cnet_vs_t03": cmp("hepg2", arm("hepg2", "Cnet"), t03),
        "Cnet_vs_Cridge": cmp("hepg2", arm("hepg2", "Cnet"), arm("hepg2", "Cridge")),
        "Cnet_vs_Cnetperm": cmp("hepg2", arm("hepg2", "Cnet"), arm("hepg2", "Cnet", perm=True)),
        "Jnet_vs_Jridge": cmp("hepg2", arm("hepg2", "Jnet"), arm("hepg2", "Jridge")),
        "Tnet_vs_Tridge": cmp("k562", arm("k562", "Tnet"), arm("k562", "Tridge")),
    }
    extra = {
        "Jnet_vs_Jnetperm": cmp("hepg2", arm("hepg2", "Jnet"), arm("hepg2", "Jnet", perm=True)),
        "Tnet_vs_Tnetperm": cmp("k562", arm("k562", "Tnet"), arm("k562", "Tnet", perm=True)),
        "Cnet_vs_transfer": cmp("hepg2", arm("hepg2", "Cnet"), arm("hepg2", "transfer")),
        "Cridge_vs_t03": cmp("hepg2", arm("hepg2", "Cridge"), t03),
        "Jnet_vs_Jnbr": cmp("hepg2", arm("hepg2", "Jnet"), arm("hepg2", "Jnbr")),
        "Tnet_vs_Tmean": cmp("k562", arm("k562", "Tnet"), arm("k562", "Tmean")),
    }

    def gain(d):
        return d["diff"] >= MIN_GAIN and d["ci95"][0] > 0

    conditions = {
        "Cnet_beats_t03": gain(c["Cnet_vs_t03"]),
        "Cnet_beats_Cridge": gain(c["Cnet_vs_Cridge"]),
        "Cnet_uses_context": gain(c["Cnet_vs_Cnetperm"]),
        "J_guard_not_worse_than_ridge": c["Jnet_vs_Jridge"]["ci95"][1] >= 0,
        "T_guard_not_worse_than_ridge": c["Tnet_vs_Tridge"]["ci95"][1] >= 0,
    }
    verdict = "KEEP" if all(conditions.values()) else "DISCARD"
    args.out.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out / "arms.csv", index=False)
    (args.out / "verdict.json").write_text(json.dumps({
        "stage": "94_conditioned_verdict", "finished_utc": datetime.now(timezone.utc).isoformat(),
        "rule": str(args.rule), "rule_md5": hashlib.md5(args.rule.read_bytes()).hexdigest(),
        "benches": {"hepg2": str(args.hepg2), "k562": str(args.k562)}, "picks": picks, "calibration": ratio,
        "decisive": c, "conditions": conditions, "verdict": verdict, "reported_not_decisive": extra,
        "bootstrap_covers": "target sampling only; not generator randomness nor the half A/B split",
    }, indent=2), encoding="utf-8")
    print(table.round(4).to_string(index=False))
    for k, d in {**c, **extra}.items():
        print(f"{k:22s} {d['diff']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}] n={d['n_targets']}")
    for k, v in conditions.items():
        print(f"  {k}: {'yes' if v else 'NO'}")
    print(f"VERDICT: {verdict}")


if __name__ == "__main__":
    main()
