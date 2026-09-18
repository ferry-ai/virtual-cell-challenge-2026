"""Stage 90: per-target sign precision (k / n_pred) of bench arms, from `components_<arm>.csv`.

Pooled precision (sum k / sum n_pred, in bench.json) is weighted by the targets that call the
most. This reads the per-target distribution instead, on targets with at least `--min-calls`
declared genes and at least one confident gene in the reference. Exploratory: no rule reads it.

    python scripts/90_per_target_precision.py --bench k562=<run dir> --bench rpe1=<run dir> --out <dir>
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bench", action="append", required=True, metavar="NAME=DIR")
    p.add_argument("--min-calls", type=int, default=10)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.out / "precision.csv").exists():
        raise SystemExit(f"{args.out} already holds a table; choose a new --out")
    rows = []
    for spec in args.bench:
        name, _, run = spec.partition("=")
        for f in sorted(Path(run).glob("components_*.csv")):
            arm = f.stem[len("components_"):]
            c = pd.read_csv(f)
            m = c[(c.n_pred >= args.min_calls) & (c.n_conf > 0)]
            pr = m.k / m.n_pred
            rows.append({"source": name, "arm": arm, "n_targets_all": len(c), "n_targets_used": len(m),
                         "precision_median": pr.median() if len(m) else None,
                         "precision_q25": pr.quantile(0.25) if len(m) else None,
                         "precision_q75": pr.quantile(0.75) if len(m) else None,
                         "n_pred_median_used": m.n_pred.median() if len(m) else None,
                         "precision_pooled_all": c.k.sum() / c.n_pred.sum() if c.n_pred.sum() else None})
    table = pd.DataFrame(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out / "precision.csv", index=False)
    (args.out / "precision.json").write_text(json.dumps({
        "stage": "90_per_target_precision", "finished_utc": datetime.now(timezone.utc).isoformat(),
        "benches": args.bench, "min_calls": args.min_calls, "exploratory": True}, indent=2), encoding="utf-8")
    print(table.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
