"""Stage 93: choose each family's amplitude on a VALIDATION bench and write the test bench's arms.

`configs/conditioned_rule.yaml`, `amplitude_selection`: per family, the amplitude with the
highest official-anchor score on the validation bench (ties to the smaller). The test bench
then runs each family once, plus the fixed arms and the context ablations at the network's
amplitude. Runs inside the Colab job between the two benches, so the choice cannot see the
test targets.

    python scripts/93_pick_amplitudes.py --rule configs/conditioned_rule.yaml --kind hepg2 \
        --val <val bench dir> --anchors <anchors.json> --status <t03 status json> --out <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench_score import calibration, member_means, per_target, score  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rule", type=Path, required=True)
    p.add_argument("--kind", choices=["hepg2", "k562"], required=True)
    p.add_argument("--val", type=Path, required=True)
    p.add_argument("--anchors", type=Path, required=True)
    p.add_argument("--status", type=Path, default=None, help="t03's vcc status (hepg2 calibration)")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.out / f"picks_{args.kind}.json").exists():
        raise SystemExit(f"{args.out} already holds picks for {args.kind}")
    rule = yaml.safe_load(args.rule.read_text(encoding="utf-8"))
    anchors = json.loads(args.anchors.read_text(encoding="utf-8"))["anchors"]
    fixed = rule["families"]["fixed_arms"]
    ratio = None
    if args.kind == "hepg2":
        status = json.loads(args.status.read_text(encoding="utf-8-sig"))
        ratio = calibration(args.val, fixed["t03"], status)
    amps = [float(a) for a in rule["families"]["amplitudes"]]
    picks, table = {}, {}
    for fam in rule["families"][args.kind]:
        scores = {a: score(member_means(per_target(args.val, f"{fam}_a{a}")), anchors, ratio) for a in amps}
        best = max(scores.values())
        picks[fam] = min(a for a, s in scores.items() if s == best)
        table[fam] = scores
    arms = ["null_new"] + ([fixed["t03"]] if args.kind == "hepg2" else ["oracle_a2.0"])
    arms += [f"{fam}_a{picks[fam]}" for fam in picks]
    arms += [f"{fam}perm_a{picks[fam]}" for fam in picks if fam.endswith("net")]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"picks_{args.kind}.json").write_text(json.dumps(
        {"stage": "93_pick_amplitudes", "kind": args.kind, "val_bench": str(args.val), "calibration": ratio,
         "scores": {f: {str(a): s for a, s in t.items()} for f, t in table.items()}, "picks": picks, "test_arms": arms},
        indent=2), encoding="utf-8")
    (args.out / f"arms_{args.kind}.txt").write_text("\n".join(arms) + "\n", encoding="utf-8")
    for f, t in table.items():
        print(f, {a: round(s, 4) for a, s in t.items()}, "->", picks[f])
    print("test arms:", " ".join(arms))


if __name__ == "__main__":
    main()
