"""Compare this folder's re-runs of the audit's HepG2 analyses with the audit's own outputs, value by value.

    python compare.py        (from this folder; writes comparison.json)
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent / "lead_audit_2026-10-01"
PAIRS = [("data_r1/data_diagnostics.json", "json"), ("data_r1/hepg2_targets.csv", "csv"),
         ("design_r1/design.json", "json")]


def flat(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from flat(v, f"{path}/{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from flat(v, f"{path}[{i}]")
    else:
        yield path, x


def load(p, kind):
    if kind == "json":
        return dict(flat(json.loads(p.read_text(encoding="utf-8"))))
    with p.open(newline="", encoding="utf-8") as fh:
        return {f"[{i}]/{k}": v for i, row in enumerate(csv.DictReader(fh)) for k, v in row.items()}


def main():
    out = {}
    for rel, kind in PAIRS:
        a, b = load(AUDIT / rel, kind), load(HERE / rel, kind)
        diff = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
        out[rel] = {"values_audit": len(a), "values_here": len(b), "different": len(diff),
                    "examples": [{"key": k, "audit": a.get(k), "here": b.get(k)} for k in diff[:10]]}
    (HERE / "comparison.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: {x: v[x] for x in ("values_audit", "values_here", "different")} for k, v in out.items()},
                     indent=1))


if __name__ == "__main__":
    main()
