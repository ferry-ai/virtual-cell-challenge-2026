"""all vs all + A549 on the five held-out lines (ADDENDUM_A549.md): cosine and PDS index, paired bootstrap, rule.

    python confronto_a549.py --cube <original layout> --cube-a549 <extended layout> --code <cube code> --out <file.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guadagno as G  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cube", type=Path, required=True)
    ap.add_argument("--cube-a549", type=Path, required=True)
    ap.add_argument("--code", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    sys.path.insert(0, str(a.code))
    import arms
    C0, C1 = G.Cubes(arms, a.cube), G.Cubes(arms, a.cube_a549)
    rng = np.random.default_rng(0)
    rec = {"lines": {}}
    for held in G.HELD:
        ctx0, ctx1 = G.Context(C0, held), G.Context(C1, held)
        keys = G.eval_keys(C0, held)
        st = G.transfer(C0, "all", keys, ctx0.commons, {held})
        keys = [k for k, s in zip(keys, st["n"].max(1) > 0) if s][:G.MAX_EVAL]
        T0 = G.transfer(C0, "all", keys, ctx0.commons, {held})["T"]
        T1 = G.transfer(C1, "all", keys, ctx1.commons, {held})["T"]
        A, _, _ = G.group_stats(C1, "A549", "all", keys, ctx1.commons)
        cube = C0.cube
        y, ysd, _ = G.truth(C0, held, keys)
        bl = G.basal_of(cube, cube.tables_of(held))
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        mask = np.isfinite(bl)[None] & np.isfinite(y)
        for i, o in enumerate(G.own_gene_cols(cube, keys)):
            if o >= 0:
                mask[i, o] = False
        ref = np.sqrt((np.where(mask, np.nan_to_num(T0), 0) ** 2).sum(1))
        m0 = G.measures(np.nan_to_num(T0), y, ysd ** 2, x, mask, ref)
        m1 = G.measures(np.nan_to_num(T1), y, ysd ** 2, x, mask, ref)
        cov = np.isfinite(A).any(1)
        mA = G.measures(np.nan_to_num(A), y, ysd ** 2, x, mask, ref)
        line = {"targets": len(keys), "a549_covered": int(cov.sum()),
                "cos_all": float(np.nanmean(m0["cos"])), "cos_all_a549": float(np.nanmean(m1["cos"])),
                "pds_all": float(np.mean(m0["pds"])), "pds_all_a549": float(np.mean(m1["pds"])),
                "cos_a549_alone_on_covered": float(np.nanmean(mA["cos"][cov])) if cov.any() else None,
                "diff_cos": G.boot_diff(m1["cos"], m0["cos"], rng), "diff_pds": G.boot_diff(m1["pds"], m0["pds"], rng),
                "diff_cos_covered": G.boot_diff(m1["cos"][cov], m0["cos"][cov], rng)}
        rec["lines"][held] = line
        print(held, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in line.items()
                                if not k.startswith("diff")}),
              "| dcos", {k: round(v, 4) for k, v in line["diff_cos"].items() if k != "n"},
              "| dpds", {k: round(v, 4) for k, v in line["diff_pds"].items() if k != "n"}, flush=True)
    L = rec["lines"].values()
    mean = float(np.mean([d["diff_cos"]["mean"] for d in L]))
    pos = sum(d["diff_cos"]["lo90"] > 0 for d in L)
    pds_ok = all(d["diff_pds"]["mean"] >= -0.005 for d in L)
    rec["rule"] = {"mean_cos_diff": mean, "lines_lo90_positive": int(pos), "pds_ok_all": bool(pds_ok),
                   "passed": bool(mean >= 0.005 and pos >= 3 and pds_ok)}
    a.out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print("rule:", json.dumps(rec["rule"]), flush=True)


if __name__ == "__main__":
    main()
