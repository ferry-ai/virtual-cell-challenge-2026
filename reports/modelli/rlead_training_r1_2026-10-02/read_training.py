"""Read the R-LEAD training r1 by the rules of PROTOCOLLO.md (written before the run).

    python read_training.py --train <dir with resume_check.json, kernel_done.json, train/ident/eval.json,
                                     train/gen/eval.json> --out lettura.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

B, SEED = 10_000, 0


def paired(a_rows, b_rows, fa, fb):
    """Paired differences fa(a) - fb(b) on the groups (key, symbol) both terms evaluate."""
    a = {(r["key"], r["symbol"]): r.get(fa) for r in a_rows if "skipped" not in r}
    b = {(r["key"], r["symbol"]): r.get(fb) for r in b_rows if "skipped" not in r}
    keys = sorted(k for k in a.keys() & b.keys() if a[k] is not None and b[k] is not None)
    return np.array([a[k] - b[k] for k in keys], float)


def verdict(d):
    if d.size == 0:
        return {"groups": 0, "verdict": "no groups"}
    rng = np.random.default_rng(SEED)
    boots = d[rng.integers(0, d.size, (B, d.size))].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    v = "meglio" if lo > 0 else ("peggio" if hi < 0 else "non distinguibile")
    return {"groups": int(d.size), "mean": float(d.mean()), "ci95": [float(lo), float(hi)], "verdict": v}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--train", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    w = a.train
    done = json.loads((w / "kernel_done.json").read_text())
    resume = json.loads((w / "resume_check.json").read_text())
    ev = {arm: json.loads((w / "train" / arm / "eval.json").read_text()) for arm in ("ident", "gen")}
    pi_c = [r["pi_mean"] for r in ev["ident"]["C"] if "skipped" not in r]
    gate = {"return_code_0": done.get("return_code") == 0, "resume_check_passed": bool(resume.get("passed")),
            "evaluation_complete": all(e["summary"]["evaluation"]["complete"] for e in ev.values()),
            "ident_C_median_pi": float(np.median(pi_c)) if pi_c else None}
    gate["ident_C_pi_not_collapsed"] = gate["ident_C_median_pi"] is not None and gate["ident_C_median_pi"] > 0.05
    gate["passed"] = all(gate[k] for k in ("return_code_0", "resume_check_passed", "evaluation_complete",
                                           "ident_C_pi_not_collapsed"))
    out = {"gate": gate, "summaries": {k: {c: e["summary"][c] for c in ("C", "T", "J")} for k, e in ev.items()}}
    if gate["passed"]:
        out["Q1_C_ident_minus_gen"] = verdict(paired(ev["ident"]["C"], ev["gen"]["C"], "cos_model", "cos_model"))
        out["Q2_C_ident_minus_transfer"] = verdict(paired(ev["ident"]["C"], ev["ident"]["C"], "cos_model", "cos_transfer"))
        out["Q3_J_ident_minus_gen"] = verdict(paired(ev["ident"]["J"], ev["gen"]["J"], "cos_model", "cos_model"))
        out["Q4_C_gen_minus_generic_data"] = verdict(paired(ev["gen"]["C"], ev["gen"]["C"], "cos_model", "cos_generic"))
    a.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "summaries"}, indent=1))


if __name__ == "__main__":
    main()
