"""Stage 81: apply the trial-02 rule to the two bench results, mechanically.

The rule is `configs/trial02_rule.yaml`, written before either bench had a result.
This stage reads the HepG2 transfer bench (primary) and the K562 panel bench
(sanity), applies the rule as written and prints the stage-76 arguments of the
chosen arm -- or says that no arm qualifies. It chooses nothing the rule does not
say; a human can still decide not to generate or not to submit.

    python scripts/81_choose_trial02.py --hepg2 <h002/bench.json> --k562 <b002/bench.json> \
        --out reports/trial02_decision_2026-09-17
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

STAGE76 = {"transfer": "--a-transfer {a}", "rawtransfer": "--a-transfer {a} --use-raw",
           "cismeas": "--a-cis-measured {a}", "cis": "--a-cis {a}", "shared": "--a-shared {a}"}


def parse_arm(arm: str) -> dict[str, float]:
    if arm.startswith("g0:") or arm in ("null_new", "null_g0", "replicate", "baseline"):
        return {}
    out = {}
    for term in arm.split("+"):
        name, _, amp = term.partition("_a")
        if name not in STAGE76:
            return {}
        out[name] = float(amp)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hepg2", type=Path, required=True)
    p.add_argument("--k562", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.out / "decision.json").exists():
        raise SystemExit(f"{args.out} already holds a decision")
    args.out.mkdir(parents=True, exist_ok=True)
    h = json.loads(args.hepg2.read_text(encoding="utf-8"))["results"]
    k = json.loads(args.k562.read_text(encoding="utf-8"))["results"]

    rep_sig = h["replicate"]["n_sig_per_target"]
    t01 = h.get("g0:rawtransfer_a0.2", {}).get("scaled_local", {})
    trial01 = t01.get("avg")
    nmae_floor = (t01.get("de_wilcoxon_lfc_nmae") if t01.get("de_wilcoxon_lfc_nmae") is not None else 0.0) - 0.10
    rows = []
    for arm, res in h.items():
        amps = parse_arm(arm)
        if not amps:
            continue
        sc = res["scaled_local"]
        guard_calls = res["n_sig_per_target"] >= 0.5 * rep_sig or (sc.get("de_wilcoxon_direction_fidelity_yield_raw") or -9) >= -0.2
        guard_nmae = (sc.get("de_wilcoxon_lfc_nmae") or -9) >= nmae_floor
        rows.append({"arm": arm, "avg": sc.get("avg"), "fid": sc.get("de_wilcoxon_direction_fidelity_yield_raw"),
                     "nmae": sc.get("de_wilcoxon_lfc_nmae"), "sig_per_target": res["n_sig_per_target"],
                     "guard_calls": bool(guard_calls), "guard_nmae": bool(guard_nmae), "amps": amps})
    eligible = [r for r in rows if r["guard_calls"] and r["guard_nmae"] and r["avg"] is not None]
    decision = {"stage": "81_choose_trial02", "written_utc": datetime.now(timezone.utc).isoformat(),
                "rule": "configs/trial02_rule.yaml", "inputs": [str(args.hepg2), str(args.k562)],
                "rule_version": 2, "nmae_floor": nmae_floor,
                "replicate_sig_per_target_hepg2": rep_sig, "trial01_recipe_avg_hepg2": trial01,
                "candidates": sorted(rows, key=lambda r: -(r["avg"] if r["avg"] is not None else -9))}
    chosen = None
    if eligible:
        best = max(r["avg"] for r in eligible)
        close = [r for r in eligible if r["avg"] >= best - 0.02]
        close.sort(key=lambda r: (not ("cismeas" in r["amps"] and "cis" in r["amps"]),
                                  r["amps"].get("transfer", r["amps"].get("rawtransfer", 0.0)), -r["avg"]))
        chosen = close[0]
    if chosen is not None and trial01 is not None and chosen["avg"] <= trial01:
        decision["stop"] = f"best eligible avg {chosen['avg']:.4f} does not beat trial-01's recipe {trial01:.4f}"
        chosen = None
    cap_note = None
    if chosen is not None:
        o1 = k.get("oracle_a1.0", {}).get("scaled_local", {}).get("avg")
        o2 = k.get("oracle_a2.0", {}).get("scaled_local", {}).get("avg")
        amps = dict(chosen["amps"])
        key = "transfer" if "transfer" in amps else ("rawtransfer" if "rawtransfer" in amps else None)
        if key and o1 is not None and o2 is not None and o2 < o1 and amps[key] > 1.0:
            cap_note = f"K562 oracle peaks at or below 1.0 ({o1:.3f} vs {o2:.3f} at 2.0): transfer capped at 1.0"
            amps[key] = 1.0
        args76 = " ".join(STAGE76[n].format(a=a) for n, a in amps.items())
        decision.update({"chosen_arm": chosen["arm"], "chosen_amplitudes": amps, "stage76_args": args76,
                         "cap_note": cap_note})
    else:
        decision.setdefault("stop", "no arm passes the guards")
    (args.out / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    for r in decision["candidates"]:
        print(f"{r['arm']:50s} avg {r['avg']!s:>8.8} fid {r['fid']!s:>8.8} nmae {r['nmae']!s:>8.8} "
              f"sig/t {r['sig_per_target']:7.1f} calls_ok {r['guard_calls']} nmae_ok {r['guard_nmae']}")
    print("trial-01 recipe avg:", trial01)
    print("DECISION:", decision.get("stage76_args") or decision.get("stop"), "|", cap_note or "")


if __name__ == "__main__":
    main()
