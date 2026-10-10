"""Paired comparison of the JEPA ablation arms (ABLAZIONE_JEPA.md): per held-out line, per-target cosine and PDS of the
`rete` arm of two runs on the same targets; paired bootstrap 2000 draws, 90% interval; the registered rule.

    python confronta_ablazione.py --runs ref=<dir> nojepa=<dir> nosig=<dir> jepa03=<dir> --out <json>
"""
import argparse
import json
from pathlib import Path

import numpy as np


def load(d: Path) -> dict:
    return json.loads((d / "result.json").read_text(encoding="utf-8"))


def boot(a, b, rng, n=2000):
    a, b = np.array(a, float), np.array(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    d = (a - b)[ok]
    m = d[rng.integers(0, len(d), (n, len(d)))].mean(1)
    return {"mean": float(d.mean()), "lo90": float(np.quantile(m, 0.05)), "hi90": float(np.quantile(m, 0.95)),
            "n": int(len(d))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    runs = {k: load(Path(v)) for k, v in (r.split("=", 1) for r in a.runs)}
    rng = np.random.default_rng(0)
    out = {"pairs": {}}
    for p, q in (("ref", "nojepa"), ("ref", "nosig"), ("jepa03", "ref")):
        if p not in runs or q not in runs:
            continue
        lines = {}
        for L in runs[p]["lines"]:
            A, B = runs[p]["lines"][L]["per_target"], runs[q]["lines"][L]["per_target"]
            lines[L] = {m: boot(A[f"rete_{m}"], B[f"rete_{m}"], rng) for m in ("cos", "pds")}
        out["pairs"][f"{p}-{q}"] = lines
    ref = out["pairs"].get("ref-nojepa", {})
    if ref:
        cos = [v["cos"]["mean"] for v in ref.values()]
        pds = [v["pds"]["mean"] for v in ref.values()]
        above = sum(v["cos"]["lo90"] > 0 for v in ref.values())
        out["rule"] = {"mean_cos": float(np.mean(cos)), "lines_lo90_above_0": int(above), "mean_pds": float(np.mean(pds)),
                       "jepa_serves": bool(np.mean(cos) >= 0.005 and above >= 3 and np.mean(pds) >= -0.005)}
    a.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, lines in out["pairs"].items():
        print(k, {L: (round(v["cos"]["mean"], 4), round(v["cos"]["lo90"], 4), round(v["pds"]["mean"], 4))
                  for L, v in lines.items()})
    print("rule", out.get("rule"))


if __name__ == "__main__":
    main()
