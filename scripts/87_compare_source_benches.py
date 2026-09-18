"""Stage 87: apply `configs/source_lineage_rule.yaml` to two stage-75 benches.

The two benches differ in ONE thing -- which Replogle screen the effects come from --
and the rule that reads them was written before either existed. This stage does the
reading mechanically, so the verdict is not a narrative choice:

1. the validity gate: same 300 targets, and `replicate`, `baseline` and `null_new`
   identical to `--tol`. Those three read no source, so a difference there means the
   two benches do not share a truth and nothing else in the file is comparable;
2. the raw table, every metric, every arm, oriented so that "+" always means better;
3. the verdict on the rule's primary metric and primary arms.

Raw values only. The `scaled_local` column of a bench uses that bench's own anchors and
is not comparable across runs, let alone with the official anchors.

    python scripts/87_compare_source_benches.py --rule configs/source_lineage_rule.yaml \
        --bench k562=<bench.json> --bench rpe1=<bench.json> --out <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import SCORED, SHORT  # noqa: E402

SOURCE_FREE = ["replicate", "baseline", "null_new"]


def better(metric: str, a: float, b: float) -> float:
    """a - b, signed so that positive always means `a` is the better of the two."""
    return (a - b) if SCORED[metric] == "higher" else (b - a)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rule", type=Path, required=True)
    p.add_argument("--bench", action="append", required=True, metavar="NAME=PATH",
                   help="exactly two, the second being the one the rule names first in `rule`")
    p.add_argument("--challenger", default="rpe1", help="the source the rule's WINS clause is written for")
    p.add_argument("--tol", type=float, default=1e-9, help="tolerance of the validity gate")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if len(args.bench) != 2:
        raise SystemExit("--bench must be given exactly twice")
    if (args.out / "compare.json").exists():
        raise SystemExit(f"{args.out} already holds a comparison; choose a new --out")

    rule = yaml.safe_load(args.rule.read_text(encoding="utf-8"))
    benches, names = {}, []
    for spec in args.bench:
        name, _, path = spec.partition("=")
        benches[name] = json.loads(Path(path).read_text(encoding="utf-8")) | {"_path": str(path)}
        names.append(name)
    challenger = args.challenger
    incumbent = [n for n in names if n != challenger]
    if len(incumbent) != 1:
        raise SystemExit(f"--challenger {challenger!r} is not one of {names}")
    incumbent = incumbent[0]

    # 1. validity gate
    gate: dict[str, object] = {"tol": args.tol, "failures": []}
    ta, tb = benches[challenger]["targets"], benches[incumbent]["targets"]
    gate["same_targets"] = ta == tb
    gate["n_targets"] = [len(ta), len(tb)]
    gate["targets_in_common"] = len(set(ta) & set(tb))
    if not gate["same_targets"]:
        gate["failures"].append(f"target panels differ: {len(set(ta) & set(tb))} shared of {len(ta)}/{len(tb)}")
    for arm in SOURCE_FREE:
        ra = benches[challenger]["results"].get(arm, {}).get("raw")
        rb = benches[incumbent]["results"].get(arm, {}).get("raw")
        if ra is None or rb is None:
            gate["failures"].append(f"{arm}: missing from one of the two benches")
            continue
        for m in SCORED:
            if ra.get(m) is None or rb.get(m) is None:
                continue
            if abs(ra[m] - rb[m]) > args.tol:
                gate["failures"].append(f"{arm}.{m}: {ra[m]:.6g} vs {rb[m]:.6g} (source-free, must be equal)")
    gate["passed"] = not gate["failures"]

    # 2. raw table
    arms = [a for a in benches[challenger]["results"] if a in benches[incumbent]["results"]]
    rows = []
    for arm in arms:
        ra, rb = benches[challenger]["results"][arm], benches[incumbent]["results"][arm]
        row = {"arm": arm,
               f"sig/t_{challenger}": ra.get("n_sig_per_target"),
               f"sig/t_{incumbent}": rb.get("n_sig_per_target")}
        for m in SCORED:
            a, b = ra["raw"].get(m), rb["raw"].get(m)
            row[f"{SHORT[m]}_{challenger}"] = a
            row[f"{SHORT[m]}_{incumbent}"] = b
            row[f"{SHORT[m]}_gain"] = None if None in (a, b) else better(m, a, b)
        rows.append(row)
    table = pd.DataFrame(rows).set_index("arm")

    # 3. the rule
    metric = rule["primary_metric"]
    primary = [a for a in rule["primary_arms"] if a in arms]
    missing = [a for a in rule["primary_arms"] if a not in arms]
    gains = {a: better(metric, benches[challenger]["results"][a]["raw"][metric],
                       benches[incumbent]["results"][a]["raw"][metric]) for a in primary}
    threshold = 0.03
    if missing or not primary:
        verdict = "VOID"
        why = f"primary arms missing from a bench: {missing}"
    elif all(g > 0 for g in gains.values()) and max(gains.values()) >= threshold:
        verdict = f"WINS_{challenger.upper()}"
        why = (f"{challenger} ahead on all {len(primary)} primary arms, largest gap "
               f"{max(gains.values()):.4f} >= {threshold}")
    elif all(g < 0 for g in gains.values()) and min(gains.values()) <= -threshold:
        verdict = f"WINS_{incumbent.upper()}"
        why = (f"{incumbent} ahead on all {len(primary)} primary arms, largest gap "
               f"{-min(gains.values()):.4f} >= {threshold}")
    else:
        verdict = "INCONCLUSIVE"
        why = (f"gaps {[round(g, 4) for g in gains.values()]}: not one-sided on all arms, "
               f"or none reaches {threshold}")
    if not gate["passed"]:
        verdict, why = "VOID", "validity gate failed: " + "; ".join(map(str, gate["failures"][:3]))

    args.out.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out / "compare.csv")
    payload = {
        "stage": "87_compare_source_benches",
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "rule": str(args.rule), "rule_version": rule.get("version"),
        "benches": {n: benches[n]["_path"] for n in names},
        "challenger": challenger, "incumbent": incumbent,
        "validity_gate": gate,
        "primary_metric": metric, "primary_arms": primary,
        "primary_gains_challenger_minus_incumbent": gains,
        "threshold": threshold,
        "verdict": verdict, "why": why,
        "note": ("raw values only; a bench's scaled_local uses its own anchors. HepG2 is not a "
                 "validation context -- see the rule's what_this_cannot_settle."),
    }
    (args.out / "compare.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(table.round(4).to_string())
    print(f"\nvalidity gate: {'PASSED' if gate['passed'] else 'FAILED'}")
    for f in gate["failures"][:10]:
        print(f"  - {f}")
    print(f"verdict: {verdict} -- {why}")
    print(f"wrote {args.out / 'compare.json'}")


if __name__ == "__main__":
    main()
