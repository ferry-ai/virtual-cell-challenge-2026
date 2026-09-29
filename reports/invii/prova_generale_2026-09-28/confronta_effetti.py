"""Step 6 of the dress rehearsal: parity of two stage-100 effects folders, array by array.

For each context of ``--mine`` (or ``--contexts``), ``effects_<ctx>.npz`` is compared with the
reference folder's file of the same context (or of ``--mapping`` NEW=OLD): same targets in the same
order, same genes, the largest |lfc difference|, and the ``observed`` masks. The registered rule
(protocol, step 6; prediction 3) is max |d lfc| <= 1e-6 with ``observed`` identical. The npz
sha256 is not compared: it depends on zip metadata and on cd4_mix's 1.5e-8 rounding.

    scripts/py.cmd reports/invii/prova_generale_2026-09-28/confronta_effetti.py ^
        --mine <data_root>/processed/effects_prova_parita_t22_2026-09-28 ^
        --reference <data_root>/processed/effects_t22_2026-09-26 ^
        --out reports/invii/prova_generale_2026-09-28/parita_effetti_t22.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from comune import write_new_json  # noqa: E402

TOLERANCE = 1e-6


def compare(mine: Path, ref: Path, tolerance: float = TOLERANCE) -> dict:
    with np.load(mine, allow_pickle=False) as a, np.load(ref, allow_pickle=False) as b:
        out = {"mine": str(mine), "reference": str(ref),
               "same_targets": a["targets"].astype(str).tolist() == b["targets"].astype(str).tolist(),
               "same_genes": a["genes"].astype(str).tolist() == b["genes"].astype(str).tolist()}
        if not (out["same_targets"] and out["same_genes"]):
            out["rule_passed"] = False
            return out
        la, lb = a["lfc"], b["lfc"]
        d = np.abs(la.astype(np.float64) - lb.astype(np.float64))
        out.update({"max_abs_diff": float(d.max()), "entries_differing": int((d > 0).sum()),
                    "entries_above_tolerance": int((d > tolerance).sum()),
                    "observed_mismatches": int((a["observed"] != b["observed"]).sum()), "tolerance": tolerance})
    out["rule_passed"] = out["entries_above_tolerance"] == 0 and out["observed_mismatches"] == 0
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mine", type=Path, required=True)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--contexts", nargs="*", default=None)
    ap.add_argument("--mapping", nargs="*", default=[], metavar="NEW=OLD")
    ap.add_argument("--out", type=Path, required=True, help="a new JSON")
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    mapping = dict(s.split("=", 1) for s in args.mapping)
    contexts = args.contexts or sorted(p.stem.removeprefix("effects_") for p in args.mine.glob("effects_*.npz"))
    report = {"script": "reports/invii/prova_generale_2026-09-28/confronta_effetti.py",
              "written_utc": datetime.now(timezone.utc).isoformat(), "per_context": {}}
    for c in contexts:
        r = compare(args.mine / f"effects_{c}.npz", args.reference / f"effects_{mapping.get(c, c)}.npz")
        report["per_context"][c] = r
        print(f"{c}: passed {r['rule_passed']}, max |d lfc| {r.get('max_abs_diff', float('nan')):.3g}, "
              f"observed mismatches {r.get('observed_mismatches')}")
    report["rule_passed"] = bool(contexts) and all(r["rule_passed"] for r in report["per_context"].values())
    write_new_json(args.out, report)
    print(f"rule passed: {report['rule_passed']} -> {args.out}")


if __name__ == "__main__":
    main()
