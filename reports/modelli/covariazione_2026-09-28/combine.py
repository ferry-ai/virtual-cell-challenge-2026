"""Combine Part A (run_parte_a.py, Kaggle) and Part B (run_parte_b.py, laptop) of action 6 into verdict.json, with the
rule registered in RISULTATI.md of this folder (covar.decide: W1-W7, the "mappa" and "uso" readings, the verdict).

Reads Part A's pairs.csv, ceilings.csv, m3a.csv, counts.csv and manifest.json; from the Part B folders (one or
more, e.g. the calibration run and the rest) calibration.json, w4.csv, w5.csv and the S0 rows of pairs.csv. Checks
that Part A used the same calibration.json Part B wrote (sha256), and that every run was in the registered
configuration; a mismatch is written into the verdict, never silently accepted. Output: a NEW folder.

    scripts/py.cmd reports/modelli/covariazione_2026-09-28/combine.py --parte-a <A> --parte-b <B1>,<B2> --out <new folder>
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import covar as C  # noqa: E402


def read_csvs(folders, name) -> pd.DataFrame | None:
    parts = [pd.read_csv(f / f"{name}.csv") for f in folders if (f / f"{name}.csv").exists()]
    return pd.concat(parts, ignore_index=True) if parts else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parte-a", type=Path, required=True)
    ap.add_argument("--parte-b", required=True, help="one or more Part B folders, comma-separated")
    ap.add_argument("--out", type=Path, required=True, help="new folder; refused if it exists")
    args = ap.parse_args()
    A = args.parte_a
    B = [Path(x.strip()) for x in args.parte_b.split(",") if x.strip()]
    args.out.mkdir(parents=True, exist_ok=False)
    notes = []
    tabs = {k: pd.read_csv(A / f"{k}.csv") for k in ("pairs", "ceilings", "m3a", "counts")}
    man_a = json.loads((A / "manifest.json").read_text(encoding="utf-8"))
    cal_paths = [f / "calibration.json" for f in B if (f / "calibration.json").exists()]
    if len(cal_paths) != 1:
        sys.exit(f"exactly one Part B folder must hold calibration.json; found {len(cal_paths)}")
    cal = json.loads(cal_paths[0].read_text(encoding="utf-8"))
    sha_b = C.sha256_file(cal_paths[0])
    used = man_a.get("counts_manifest", man_a).get("calibration") or {}
    if used.get("sha256") != sha_b:
        notes.append(f"ATTENZIONE: la parte A ha usato una calibrazione diversa ({used.get('sha256')}) da quella "
                     f"della parte B ({sha_b})")
    man_b = [json.loads((f / "manifest.json").read_text(encoding="utf-8")) for f in B if (f / "manifest.json").exists()]
    reg = {"parte_a": bool(man_a.get("registered_configuration")),
           "parte_b": [bool(m.get("registered_configuration")) for m in man_b],
           "calibration": bool(cal.get("registered_configuration"))}
    if not (reg["parte_a"] and all(reg["parte_b"]) and reg["calibration"]):
        notes.append("ATTENZIONE: almeno una parte non gira nella configurazione registrata (vedi registered)")
    pairs_b = read_csvs(B, "pairs")
    s0 = pairs_b[pairs_b["stratum"] == "S0"] if pairs_b is not None else None
    verdict = C.decide(tabs["pairs"], tabs["ceilings"], tabs["m3a"], kappa_pb=float(cal["kappa_pseudobulk"]),
                       w4=read_csvs(B, "w4"), w5=read_csvs(B, "w5"), s0_pairs=s0, counts=tabs["counts"])
    verdict["notes"] = notes + verdict["notes"]
    inputs = {str(p): C.sha256_file(p) for p in [*(A / f"{k}.csv" for k in tabs), A / "manifest.json", cal_paths[0],
                                                 *(f / f"{k}.csv" for f in B for k in ("w4", "w5", "pairs"))]
              if p.exists()}
    doc = {"stage": "covariazione_2026-09-28/combine.py", "argv": sys.argv,
           "written_utc": datetime.now(timezone.utc).isoformat(),
           "claim_type": "measured, effect space, public sources; no number here is a VCC score",
           "registered": reg, "inputs_sha256": inputs, **verdict}
    (args.out / "verdict.json").write_text(json.dumps(C.jsonable(doc), indent=1, ensure_ascii=False), encoding="utf-8")
    C.log(f"verdetto: {verdict['verdetto']}  (mappa {verdict['mappa']}, uso {verdict['uso']}); "
          f"pending {verdict['pending']}; notes {verdict['notes']}")


if __name__ == "__main__":
    main()
