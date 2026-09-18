"""Stage 82: the official baseline and replicate anchors, solved from two scored submissions.

`vcc status --json` returns, for every scored entry, BOTH forms of each of the six
members: the raw metric (`pds_cosine`, `de_wilcoxon_direction_fidelity_yield_raw`, ...)
and its scaled score (`score_pds`, `score_fid`, ...). The challenge scales with

    scaled = (raw - baseline) / (replicate - baseline)

where the two anchors are properties of the PANEL, not of the submission. Two entries
scored on the same `panel_id` and `anchor_version` therefore give two equations per
member in the same two unknowns, and the system is solved by

    baseline  = (s1*u2 - s2*u1) / (s1 - s2)
    replicate = baseline + (u1 - baseline) / s1

which is exact whenever the two scaled values differ. A member whose scaled value is
clipped (both entries at 0) is left unsolved and reported as a bound.

This turns every local measurement into a comparable number: a raw metric can be placed
against the anchors directly, instead of against a bench's own local anchors, which live
in a different regime (CP-0021).

    python scripts/82_solve_anchors.py --status a.json b.json --out reports/anchors_2026-09-17
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

#: raw member -> its scaled score field, in the order the challenge averages them.
MEMBERS = [
    ("pds_cosine", "score_pds", "higher"),
    ("expr_mse_unbiased_capped_norm", "score_mse", "lower"),
    ("de_wilcoxon_lfc_nmae", "score_nmae", "lower"),
    ("de_wilcoxon_direction_fidelity_yield_raw", "score_fid", "higher"),
    ("de_wilcoxon_direction_reach_raw", "score_reach", "higher"),
    ("de_wilcoxon_sig_jaccard", "score_jac", "higher"),
]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--status", type=Path, nargs="+", required=True,
                   help="two or more `vcc status --json` outputs, same panel and anchor version")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.out / "anchors.json").exists():
        raise SystemExit(f"{args.out} already holds anchors; choose a new --out")
    args.out.mkdir(parents=True, exist_ok=True)

    entries = [json.loads(path.read_text(encoding="utf-8-sig")) for path in args.status]
    panels = {e["panel_id"] for e in entries}
    anchors_v = {e["anchor_version"] for e in entries}
    if len(panels) != 1 or len(anchors_v) != 1:
        raise SystemExit(f"entries do not share a panel/anchor set: {panels} {anchors_v}")

    solved, unsolved = {}, {}
    for raw, scaled, better in MEMBERS:
        pairs = [(e[raw], e[scaled], e["entry_id"]) for e in entries
                 if e.get(raw) is not None and e.get(scaled) is not None]
        pick = None
        for i in range(len(pairs)):
            for j in range(i + 1, len(pairs)):
                if pairs[i][1] != pairs[j][1]:
                    pick = (pairs[i], pairs[j])
                    break
            if pick:
                break
        if pick is None:
            bound = min(u for u, _, _ in pairs) if better == "lower" else max(u for u, _, _ in pairs)
            unsolved[raw] = {"reason": "all scaled values equal (clipped); the system is singular",
                             "scaled_value": pairs[0][1] if pairs else None,
                             "baseline_bound": bound,
                             "bound_meaning": ("baseline is at least as good as the best raw seen, i.e. "
                                               f"{'<=' if better == 'lower' else '>='} {bound}")}
            continue
        (u1, s1, e1), (u2, s2, e2) = pick
        b = (s1 * u2 - s2 * u1) / (s1 - s2)
        r = b + (u1 - b) / s1
        solved[raw] = {"baseline": b, "replicate": r, "better": better,
                       "from": [{"entry_id": e1, "raw": u1, "scaled": s1},
                                {"entry_id": e2, "raw": u2, "scaled": s2}],
                       "check": {e["entry_id"]: (e[raw] - b) / (r - b) for e in entries
                                 if e.get(raw) is not None}}

    payload = {
        "stage": "82_solve_anchors", "written_utc": datetime.now(timezone.utc).isoformat(),
        "panel_id": panels.pop(), "anchor_version": anchors_v.pop(),
        "inputs": [str(p_) for p_ in args.status],
        "entries": [{"entry_id": e["entry_id"], "model_name": e["model_name"],
                     "submission_date": e["submission_date"], "score_avg": e["score_avg"]} for e in entries],
        "anchors": solved, "unsolved": unsolved,
        "claim_type": ("measured: an exact algebraic solution of the challenge's own scaling from two of its "
                       "own scored outputs, not an estimate. It holds for this panel and anchor version only."),
    }
    (args.out / "anchors.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"panel {payload['panel_id']} anchors {payload['anchor_version']}")
    print(f"{'member':44s} {'baseline':>9} {'replicate':>10}   direction")
    for raw, v in solved.items():
        print(f"{raw:44s} {v['baseline']:9.4f} {v['replicate']:10.4f}   {v['better']} is better")
    for raw, v in unsolved.items():
        print(f"{raw:44s} {'unsolved':>9} {'':>10}   {v['bound_meaning']}")
    print("\nre-derived scaled values (must match the server's, to floating point):")
    for raw, v in solved.items():
        print(f"  {raw:44s} " + "  ".join(f"{k}={x:+.4f}" for k, x in v["check"].items()))


if __name__ == "__main__":
    main()
