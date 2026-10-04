"""Technical acceptance of one D-056 training (PROTOCOLLO.md §10), from its receipts only (no evaluation file).

Conditions of version 4's §5: exit code 0; no twin differing from its manifest; no drawn cell of a class other than
train; exposure passed (every complete window and the run within the tolerance, every unit drawn; version 5 adds the
effective shares without the validation cells); health at step 5,000 passed; evaluation complete within its budget;
anchors with regime-J table means and their manifest checks passed. Version 5 adds: validation cells with loss weight 0
(val.json) and guard.json with every check. A stop by guard is an outcome, not a rejection.
Reads <dir>/kernel_done.json, <dir>/train/{config,coverage,exposure,health,done,val,guard,verify}.json; writes
<dir>/acceptance.json and prints it.

    python accept_training.py <fetched folder of rcell-d056-train-<line>-r1>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def read(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def main() -> None:
    d = Path(sys.argv[1])
    t = d / "train"
    kd, cfg, cov, exp, health, done, val, guard, verify = (read(p) for p in (
        d / "kernel_done.json", t / "config.json", t / "coverage.json", t / "exposure.json", t / "health.json",
        t / "done.json", t / "val.json", t / "guard.json", t / "verify.json"))
    anc = (cfg or {}).get("anchors") or {}
    checks = {
        "exit_code_0": bool(kd) and kd.get("return_code") == 0,
        "twins_verified": bool(verify) and not verify.get("differ") and not verify.get("bad"),
        "no_leakage": bool(cov) and bool(cov["leakage_check"]["passed"]),
        "exposure_passed": bool(exp) and bool(exp.get("passed")),
        "effective_shares_passed": bool(exp) and bool(exp.get("effective_passed")),
        "health_passed": bool(health) and bool(health.get("passed")),
        "evaluation_complete": bool(done) and bool(done.get("evaluation_complete")),
        "anchors_regime_J": (anc.get("commons") or {}).get("regime") == "J"
                            and bool((anc.get("manifest_checks") or {}).get("passed")),
        "validation_zero_weight": bool(val) and bool(val.get("zero_weight_passed")),
        "guard_checks_written": bool(guard) and len(guard.get("checks", [])) > 0,
    }
    out = {"folder": str(d), "accepted": all(checks.values()), "checks": checks,
           "stop": (cov or {}).get("stop"), "steps": (cov or {}).get("steps"), "epochs": (cov or {}).get("epochs_done"),
           "throughput": (cov or {}).get("throughput"), "exported": (val or {}).get("exported"),
           "guard_checks": len((guard or {}).get("checks", [])),
           "validation_pairs": len((val or {}).get("pairs", [])), "val_draws": (val or {}).get("val_draws"),
           "effective_max_abs_deviation": (exp or {}).get("effective_max_abs_deviation"),
           "rule": "PROTOCOLLO.md §10 of reports/modelli/ibrido_selettivo_2026-10-04"}
    (d / "acceptance.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
