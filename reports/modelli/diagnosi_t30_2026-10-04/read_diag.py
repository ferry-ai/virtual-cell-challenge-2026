"""Read the diagnostic lanes by the rules of PROTOCOLLO_CONFRONTI.md §4, written before any of their outputs existed.

For each line: validity (parity, and `all`, `all_wR`, `prod` reproducing the stored `transfer`, `ibrido_selettivo`,
`transfer_prod_J` of the D-056 lane B within 1e-9), then D (C1), P and Q (C2), S, K, G (C3), the amplitude pair, on the
six-member mean and, as the declared secondary reading, on the five members without JAC. Thresholds are constants of
the protocol. Refuses an existing --out. Not VCC scores; nothing here promotes a candidate.

    py read_diag.py --line HepG2 <diagB dir> [--line H1 <dir> ...] --out <new json>
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
STORED = HERE.parent / "ibrido_selettivo_2026-10-04" / "esito"
MEMBERS = ["PDS", "MSE", "NMAE", "FID", "REACH", "JAC"]
NO_JAC = ["PDS", "MSE", "NMAE", "FID", "REACH"]
REPRODUCES = {"all": "transfer", "all_wR": "ibrido_selettivo", "prod": "transfer_prod_J"}
TOL = 1e-9
C1_MEAN, C2_MEAN, C3_MEAN, C3_SHARE = -0.010, -0.020, 0.010, 0.5


def table(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, index_col=0)


def line_quantities(d: pd.DataFrame, cols: list) -> dict:
    avg = d[cols].mean(1)
    return {"G": avg["all_wR"] - avg["all"], "G_prod": avg["prod_wR"] - avg["prod"],
            "D": (avg["prod_wR"] - avg["prod"]) - (avg["all_wR"] - avg["all"]),
            "S": avg["all_wRspec"] - avg["all"], "K": avg["all_wRcom"] - avg["all"],
            "S_prod": avg["prod_wRspec"] - avg["prod"], "K_prod": avg["prod_wRcom"] - avg["prod"],
            "dose": avg["all_wRdose"] - avg["all"], "dose_prod": avg["prod_wRdose"] - avg["prod"],
            "x15": avg["prod_wR_x15"] - avg["prod_x15"]}


def verdicts(q: dict, pds: dict, n: int) -> dict:
    need = max(n - 1, 1)
    mean = lambda k, src=q: sum(v[k] for v in src.values()) / n  # noqa: E731
    neg = lambda k, src=q: sum(v[k] < 0 for v in src.values())  # noqa: E731
    pos = lambda k, src=q: sum(v[k] > 0 for v in src.values())  # noqa: E731
    mD, mP, mQ, mS, mK, mG = mean("D"), mean("P", pds), mean("Q", pds), mean("S"), mean("K"), mean("G")
    c1 = ("sostenuta sul banco" if neg("D") >= need and mD <= C1_MEAN else
          "smentita sul banco" if mD >= 0 else "non distinta")
    c2 = ("sostenuta" if neg("P", pds) >= need and mP <= C2_MEAN else "smentita" if mP >= 0 else "non distinta")
    c3 = ("guadagno portato dalla parte comune" if mK >= C3_SHARE * mG and mS < C3_MEAN else
          "guadagno specifico" if pos("S") >= need and mS >= C3_MEAN else "misto")
    return {"lines": n, "lines_needed": need, "C1": {"mean_D": mD, "lines_D_negative": neg("D"), "verdict": c1},
            "C2": {"mean_P": mP, "lines_P_negative": neg("P", pds), "mean_Q": mQ, "verdict": c2},
            "C3": {"mean_S": mS, "mean_K": mK, "mean_G": mG, "lines_S_positive": pos("S"), "verdict": c3},
            "amplitude": {"mean_gain_x15": mean("x15"), "mean_gain_x1": mean("G_prod")}}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--line", nargs=2, action="append", required=True, metavar=("NAME", "DIR"))
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    lines, excluded = {}, {}
    for name, folder in a.line:
        folder = Path(folder)
        d = table(folder / "bench" / "scaled_local.csv")
        stored = table(STORED / f"lanes_{name.lower()}_r1" / "laneB" / "bench" / "scaled_local.csv")
        parity = json.loads((folder / "parity.json").read_text(encoding="utf-8"))
        gaps = {arm: float((d.loc[arm, MEMBERS] - stored.loc[ref, MEMBERS]).abs().max())
                for arm, ref in REPRODUCES.items()}
        valid = bool(parity["cells_equal"]) and all(g <= TOL for g in gaps.values())
        rec = {"valid": valid, "parity": parity["cells_equal"], "max_gap_to_stored": gaps,
               "effects": json.loads((folder / "effects_diagnostics.json").read_text(encoding="utf-8")),
               "members": d[MEMBERS].round(6).to_dict(orient="index")}
        if valid:
            rec["six"] = line_quantities(d, MEMBERS)
            rec["five_without_JAC"] = line_quantities(d, NO_JAC)
            rec["pds"] = {"P": float(d.loc["all_wRdose", "PDS"] - d.loc["all_wR", "PDS"]),
                          "Q": float(d.loc["all_wRspec", "PDS"] - d.loc["all_wR", "PDS"]),
                          "prod_wR_minus_prod": float(d.loc["prod_wR", "PDS"] - d.loc["prod", "PDS"]),
                          "all_wR_minus_all": float(d.loc["all_wR", "PDS"] - d.loc["all", "PDS"])}
            lines[name] = rec
        else:
            excluded[name] = rec
    out = {"written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "protocol": "reports/modelli/diagnosi_t30_2026-10-04/PROTOCOLLO_CONFRONTI.md §4",
           "thresholds": {"C1_mean": C1_MEAN, "C2_mean": C2_MEAN, "C3_mean": C3_MEAN, "C3_share": C3_SHARE,
                          "reproduction_tolerance": TOL},
           "lines": lines, "excluded": excluded,
           "note": "diagnostic readings on lines already read; local scale, not VCC scores; no candidate is promoted"}
    if lines:
        n = len(lines)
        pds = {k: v["pds"] for k, v in lines.items()}
        out["primary_six_members"] = verdicts({k: v["six"] for k, v in lines.items()}, pds, n)
        out["secondary_without_JAC"] = verdicts({k: v["five_without_JAC"] for k, v in lines.items()}, pds, n)
    a.out.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("primary_six_members", "secondary_without_JAC") if k in out}, default=float))


if __name__ == "__main__":
    main()
