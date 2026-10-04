"""Read the noise calibration of the bench by PROTOCOLLO_CONFRONTI.md §9, written before any of its outputs existed.

Per line and number of cells per target (`nb` = the bench's, `n400`): the paired gain g_k = avg(X_wR) - avg(X) at the
same generator seed, for X = all and X = prod, on the six-member mean, on the five members without JAC and on each
member; its mean and standard deviation (n - 1) over the seeds; whether the gain is resolved
(|mean| > 2 sd / sqrt(seeds)); whether one seed of the bench resolves the stored gain (sd at `nb` < half of |stored
gain|); the sd of a single arm across seeds; the ratio of the sd at the two cell counts. Seed 0 at `nb` must reproduce
the r1 lanes within 1e-9. Refuses an existing --out. Not VCC scores; nothing here promotes a candidate.

    py read_noise.py --line HepG2 <noiseB dir> [--line ...] --out <new json>
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
MEMBERS = ["PDS", "MSE", "NMAE", "FID", "REACH", "JAC"]
NO_JAC = ["PDS", "MSE", "NMAE", "FID", "REACH"]
NAME = re.compile(r"^(?P<arm>[a-zA-Z_0-9]+)@(?P<n>nb|n\d+)s(?P<k>\d+)$")
TOL = 1e-9


def stats(v) -> dict:
    v = np.asarray(v, float)
    sd = float(v.std(ddof=1)) if v.size > 1 else float("nan")
    return {"mean": float(v.mean()), "sd": sd, "values": [float(x) for x in v],
            "resolved": bool(abs(v.mean()) > 2 * sd / np.sqrt(v.size)) if v.size > 1 else False}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--line", nargs=2, action="append", required=True, metavar=("NAME", "DIR"))
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    lines = {}
    for name, folder in a.line:
        d = pd.read_csv(Path(folder) / "bench" / "scaled_local.csv", index_col=0)
        r1 = pd.read_csv(HERE / "esito" / f"diag_{name.lower()}_r1" / "scaled_local.csv", index_col=0)
        rows = [(m["arm"], m["n"], int(m["k"]), i) for i in d.index if (m := NAME.match(i))]
        t = pd.DataFrame(rows, columns=["arm", "n", "k", "row"])
        gaps = {arm: float((d.loc[f"{arm}@nbs0", MEMBERS] - r1.loc[arm, MEMBERS]).abs().max())
                for arm in ("all", "all_wR", "prod", "prod_wR")}
        rec = {"reproduces_r1_at_seed_0": all(g <= TOL for g in gaps.values()), "max_gap_to_r1": gaps, "by_n": {}}
        for n, tn in t.groupby("n"):
            seeds = sorted(tn["k"].unique())
            val = lambda arm, cols: np.array([d.loc[f"{arm}@{n}s{k}", cols].mean() for k in seeds])  # noqa: E731
            out = {"seeds": len(seeds)}
            for base in ("all", "prod"):
                g6 = val(f"{base}_wR", MEMBERS) - val(base, MEMBERS)
                g5 = val(f"{base}_wR", NO_JAC) - val(base, NO_JAC)
                stored = float(r1.loc[f"{base}_wR", MEMBERS].mean() - r1.loc[base, MEMBERS].mean())
                out[base] = {"gain_six": stats(g6), "gain_without_JAC": stats(g5),
                             "gain_by_member": {m: stats(val(f"{base}_wR", [m]) - val(base, [m])) for m in MEMBERS},
                             "single_arm_sd_six": {arm: float(val(arm, MEMBERS).std(ddof=1))
                                                   for arm in (base, f"{base}_wR")},
                             "stored_gain_r1": stored,
                             "one_seed_does_not_resolve": bool(np.std(g6, ddof=1) >= 0.5 * abs(stored))}
            rec["by_n"][n] = out
        ns = sorted(rec["by_n"])
        if "nb" in rec["by_n"] and len(ns) == 2:
            other = [n for n in ns if n != "nb"][0]
            rec["sd_ratio_other_over_nb"] = {b: rec["by_n"][other][b]["gain_six"]["sd"]
                                             / rec["by_n"]["nb"][b]["gain_six"]["sd"] for b in ("all", "prod")}
        lines[name] = rec
    n_lines = len(lines)
    unresolved = {b: sum(v["by_n"]["nb"][b]["one_seed_does_not_resolve"] for v in lines.values()) for b in ("all", "prod")}
    summary = {"lines": n_lines, "lines_where_one_seed_does_not_resolve": unresolved,
               "the_bench_at_one_seed_does_not_resolve_the_gain": {b: unresolved[b] >= min(3, n_lines)
                                                                    for b in unresolved},
               "resolved_gains": {n: {b: {"lines_resolved": sum(v["by_n"][n][b]["gain_six"]["resolved"]
                                                                for v in lines.values() if n in v["by_n"]),
                                          "lines_resolved_positive": sum(
                                              v["by_n"][n][b]["gain_six"]["resolved"]
                                              and v["by_n"][n][b]["gain_six"]["mean"] > 0
                                              for v in lines.values() if n in v["by_n"])}
                                      for b in ("all", "prod")}
                                  for n in sorted({n for v in lines.values() for n in v["by_n"]})}}
    out = {"written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "protocol": "reports/modelli/diagnosi_t30_2026-10-04/PROTOCOLLO_CONFRONTI.md §9", "summary": summary,
           "lines": lines, "note": "local scale, lines already read; not VCC scores; no candidate is promoted"}
    a.out.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    for name, v in lines.items():
        for n, o in v["by_n"].items():
            print(name, n, {b: (round(o[b]["gain_six"]["mean"], 4), round(o[b]["gain_six"]["sd"], 4),
                                o[b]["gain_six"]["resolved"], round(o[b]["stored_gain_r1"], 4)) for b in ("all", "prod")},
                  "PDS all", (round(o["all"]["gain_by_member"]["PDS"]["mean"], 4), round(o["all"]["gain_by_member"]["PDS"]["sd"], 4)),
                  "repro", v["reproduces_r1_at_seed_0"])


if __name__ == "__main__":
    main()
