"""Were the competition panel's targets among the targets the bench evaluated? And how do the two sets differ?

Exploratory, written after export_on_line_controls_r2.json (no registered rule). From stored files only:
- per bench line, how many of the 300 panel targets (and of the 230 corrected ones) are among the C rows the selector
  was fitted or evaluated on, and among the lane B targets;
- per-target RMS of the transfer T and of the correction R, support and concordance: the bench rows of each line
  against the corrected panel targets of each competition context (the same definitions: hybrid_lanes.selector_stats).

    .\\scripts\\py.cmd reports/modelli/diagnosi_t30_2026-10-04/panel_vs_rows_targets.py --out <new json>
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ESITO = HERE.parent / "ibrido_selettivo_2026-10-04" / "esito"
LINES = ("H1", "HepG2", "RPE1", "Jurkat", "K562")


def q(x) -> dict:
    x = np.asarray(x, float)
    return {"n": int(x.size), "q10": float(np.quantile(x, 0.1)), "q50": float(np.median(x)),
            "q90": float(np.quantile(x, 0.9)), "mean": float(x.mean())}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    panel = {c: pd.read_csv(ESITO / f"export_abc_r2/targets_{c}.csv") for c in "ABC"}
    t = panel["A"]
    corrected = set(t.loc[t["eligible"], "target_key"])
    overlap, rows_stats = {}, {}
    for line in LINES:
        rows = pd.read_csv(ESITO / f"rows_{line.lower()}_r1/rows/rows_{line}.csv.gz")
        bench = json.loads((ESITO / f"lanes_{line.lower()}_r1/laneB/bench/bench.json").read_text(encoding="utf-8"))
        keys, lane = set(rows["target_key"]), set(bench["target_keys"])
        overlap[line] = {"rows": int(len(rows)), "row_targets": len(keys),
                         "panel_targets_in_rows": int(t["target_key"].isin(keys).sum()),
                         "corrected_panel_targets_in_rows": len(corrected & keys),
                         "laneB_targets": len(lane), "panel_targets_in_laneB": int(t["target_key"].isin(lane).sum())}
        rows_stats[line] = {"rms_t": q(rows["ibrido__rms_t"]), "rms_r": q(rows["ibrido__rms_r"]),
                            "ratio": q(rows["ibrido__rms_r"] / rows["ibrido__rms_t"]), "support": q(rows["support"]),
                            "concordance": q(rows["f_concordance"]), "expression": q(rows["f_expression"])}
    export_stats = {}
    for c, df in panel.items():
        e = df[df["eligible"]]
        export_stats[c] = {"rms_t": q(e["rms_t"]), "rms_r": q(e["rms_r"]), "ratio": q(e["rms_r"] / e["rms_t"]),
                           "support": q(e["support"]), "concordance": q(e["f_concordance"]),
                           "expression": q(e["f_expression"])}
    dev = [overlap[n]["rows"] for n in ("H1", "HepG2", "RPE1")]
    dev_panel = [overlap[n]["panel_targets_in_rows"] for n in ("H1", "HepG2", "RPE1")]
    out = {"written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "claim_type": "exploratory, read after export_on_line_controls_r2.json; no registered rule",
           "panel_targets": int(len(t)), "corrected_panel_targets": len(corrected), "overlap": overlap,
           "selector_fit_rows": {"rows": int(sum(dev)), "rows_of_panel_targets": int(sum(dev_panel)),
                                 "share": float(sum(dev_panel) / sum(dev))},
           "bench_rows": rows_stats, "export_corrected_panel_targets": export_stats,
           "note": "the anchor T of the panel targets is the same for A, B and C; R depends on the context's controls"}
    a.out.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(overlap, indent=0), json.dumps(out["selector_fit_rows"]))
    for n, s in {**rows_stats, **export_stats}.items():
        print(n, {k: round(v["q50"], 4) for k, v in s.items()})


if __name__ == "__main__":
    main()
