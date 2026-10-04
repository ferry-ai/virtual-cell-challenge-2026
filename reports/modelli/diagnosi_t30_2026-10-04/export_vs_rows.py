"""The correction exported for A/B/C against the corrections the bench evaluated, from the files already on disk.

Export side (processed/ibrido_selettivo_2026-10-04/export_abc_r2 and the t25 effects regenerated on 4/10), per context,
on the corrected targets and the (target, gene) pairs observed in t25:
- common share  ||mean_i v_i||^2 / mean_i ||v_i||^2  of R, of the added correction w R (t30 - t25), of the t25
  effects, of the hybrid effects and of the anchor passed through the network's estimator s(A);
- RMS of each, the per-target ratio RMS(R)/RMS(T) of the selector input, cosines per target between R, t25 and s(A)
  (how far the baseline R was added to is from the anchor R was learned against), cosine of the common vectors of two
  contexts;
- mean pairwise cosine between targets' effects before and after, and a truth-free retrieval check: the rank of
  t25_i among all t25_j by cosine distance from hybrid_i (1.0 = the hybrid still points to its own t25 effect first).
Bench side (reports/modelli/ibrido_selettivo_2026-10-04/esito): the same common share and ratio as stored in each
line's rows_summary.json, the selector inputs of the rows, and the weights given on the rows.
Selector inputs: z-scores of the export against the frozen standardisation, and the share of export targets outside
the range and the 1-99 % band of the development rows the selector was fitted on.
Nothing here reads a truth of A/B/C (none exists locally) and nothing is a score.

    .\\scripts\\py.cmd reports/modelli/diagnosi_t30_2026-10-04/export_vs_rows.py --out <new json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = Path(os.environ.get("VCC2026_DATA_ROOT", "C:/Users/ferra/vcc2026-data"))
EXPORT = DATA / "processed/ibrido_selettivo_2026-10-04/export_abc_r2"
T25 = DATA / "processed/effects_t25_regen_2026-10-04"
ESITO = REPO / "reports/modelli/ibrido_selettivo_2026-10-04/esito"
FEATURES = {"f_support": "f_support", "f_concordance": "f_concordance", "f_log_ratio": "ibrido__f_log_ratio",
            "f_cos_rt": "ibrido__f_cos_rt", "f_expression": "f_expression"}
DEV, CONF = ("H1", "HepG2", "RPE1"), ("Jurkat", "K562")
Q = [0.01, 0.1, 0.5, 0.9, 0.99]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def common_share(v: np.ndarray) -> float:
    e = float((v ** 2).sum(1).mean())
    return float((v.mean(0) ** 2).sum() / e) if e > 0 else 0.0


def rms(v: np.ndarray, ok: np.ndarray) -> float:
    return float(np.sqrt((v[ok] ** 2).mean())) if ok.any() else float("nan")


def cos_rows(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    na, nb = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
    return np.where((na > 0) & (nb > 0), (a * b).sum(1) / np.maximum(na * nb, 1e-30), np.nan)


def cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-30))


def mean_pairwise_cos(v: np.ndarray) -> float:
    u = v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-30)
    n = u.shape[0]
    return float(((u.sum(0) ** 2).sum() - n) / (n * (n - 1)))


def retrieval(query: np.ndarray, ref: np.ndarray) -> dict:
    """For each row i: the share of other rows j with ref_j at least as close (cosine) to query_i as ref_i is."""
    q = query / np.maximum(np.linalg.norm(query, axis=1, keepdims=True), 1e-30)
    r = ref / np.maximum(np.linalg.norm(ref, axis=1, keepdims=True), 1e-30)
    sim = q @ r.T
    own = np.diag(sim)
    beaten = ((sim >= own[:, None]).sum(1) - 1) / (sim.shape[0] - 1)
    return {"score_mean": float(1 - beaten.mean()), "targets_not_first": int((beaten > 0).sum()),
            "targets": int(sim.shape[0])}


def quantiles(x) -> dict:
    x = np.asarray(x, float)
    return {"mean": float(x.mean()), **{f"q{int(q * 100):02d}": float(v) for q, v in zip(Q, np.quantile(x, Q))},
            "min": float(x.min()), "max": float(x.max())}


def export_side() -> tuple[dict, dict]:
    out, commons, files = {}, {}, {}
    for c in "ABC":
        with np.load(EXPORT / f"correction_{c}.npz", allow_pickle=False) as z:
            R, SA = z["R"].astype(np.float64), z["s_anchor"].astype(np.float64)
        with np.load(T25 / f"effects_{c}.npz", allow_pickle=False) as z:
            lfc, obs = z["lfc"].astype(np.float64), z["observed"]
        with np.load(EXPORT / f"effects_{c}.npz", allow_pickle=False) as z:
            hyb = z["lfc"].astype(np.float64)
        t = pd.read_csv(ESITO / f"export_abc_r2/targets_{c}.csv")
        files[c] = {f: sha(EXPORT / f) for f in (f"correction_{c}.npz", f"effects_{c}.npz")}
        el = t["eligible"].to_numpy()
        ok = obs[el] & np.isfinite(R[el])
        Rz = np.where(ok, R[el], 0.0)
        Tz = np.where(obs[el], lfc[el], 0.0)
        Hz = np.where(obs[el], hyb[el], 0.0)
        Az = np.where(ok & np.isfinite(SA[el]), SA[el], 0.0)
        added = Hz - Tz
        w = t.loc[el, "w"].to_numpy()
        commons[c] = Rz.mean(0)
        proj = (Rz * Tz).sum(1) / np.maximum((Tz * Tz).sum(1), 1e-30)
        out[c] = {
            "corrected_targets": int(el.sum()), "pairs": int(ok.sum()),
            "common_share": {"R": common_share(Rz), "added_wR": common_share(added), "t25": common_share(Tz),
                             "hybrid": common_share(Hz), "s_anchor": common_share(Az)},
            "rms": {"R": rms(Rz, ok), "added_wR": rms(added, ok), "t25": rms(Tz, obs[el]), "s_anchor": rms(Az, ok),
                    "R_common_vector": float(np.sqrt((commons[c] ** 2).mean())),
                    "t25_common_vector": float(np.sqrt((Tz.mean(0) ** 2).mean()))},
            "ratio_rms_R_over_T_selector_input": quantiles(np.exp(t.loc[el, "ibrido__f_log_ratio"])),
            "ratio_rms_R_over_t25": quantiles(np.sqrt((Rz ** 2).sum(1) / np.maximum((Tz ** 2).sum(1), 1e-30))),
            "cos_per_target": {"t25_vs_s_anchor": quantiles(cos_rows(Tz, Az)), "R_vs_t25": quantiles(cos_rows(Rz, Tz)),
                               "R_vs_s_anchor": quantiles(cos_rows(Rz, Az)),
                               "R_specific_vs_t25": quantiles(cos_rows(Rz - commons[c], Tz))},
            "projection_of_R_on_t25": quantiles(proj),
            "cos_common_R_vs_common_t25": cos(commons[c], Tz.mean(0)),
            "mean_pairwise_cos_between_targets": {"t25": mean_pairwise_cos(Tz), "hybrid": mean_pairwise_cos(Hz),
                                                  "R": mean_pairwise_cos(Rz)},
            "retrieval_of_own_t25_effect": {"hybrid": retrieval(Hz, Tz), "t25_plus_R_w1": retrieval(Tz + Rz, Tz),
                                            "hybrid_without_common": retrieval(Tz + w[:, None] * (Rz - commons[c]), Tz)},
            "w": quantiles(w),
            "features": {k: quantiles(t.loc[el, col]) for k, col in FEATURES.items()}}
    out["cos_of_common_R_between_contexts"] = {f"{x}{y}": cos(commons[x], commons[y]) for x, y in ("AB", "AC", "BC")}
    return out, files


def bench_side() -> tuple[dict, pd.DataFrame]:
    out, frames = {}, []
    for line in (*DEV, *CONF):
        folder = ESITO / f"rows_{line.lower()}_r1/rows"
        rows = pd.read_csv(folder / f"rows_{line}.csv.gz")
        rows["line"] = line
        frames.append(rows)
        diag = [d for d in json.loads((folder / "rows_summary.json").read_text(encoding="utf-8"))["diagnostics_of_R"]
                if d["arm"] == "ibrido"]
        n = np.array([d["rows"] for d in diag], float)
        wfile = (ESITO / f"selector_lolo_r1/weights_{line}.json" if line in DEV else
                 ESITO / f"selector_apply_{line.lower()}_r1/weights_{line}.json")
        wsel = json.loads(wfile.read_text(encoding="utf-8"))["selective"]["ibrido"]
        out[line] = {"rows": int(len(rows)), "tables": sorted(rows["table"].unique().tolist()), "blocks": len(diag),
                     "common_share_R": {"weighted_mean": float(np.average([d["common_share"] for d in diag], weights=n)),
                                        "min": float(min(d["common_share"] for d in diag)),
                                        "max": float(max(d["common_share"] for d in diag))},
                     "ratio_rms_R_over_T_pooled": float(np.average([d["ratio_rms"] for d in diag], weights=n)),
                     "ratio_rms_R_over_T_per_row": quantiles(np.exp(rows["ibrido__f_log_ratio"])),
                     "w": quantiles(list(wsel.values())),
                     "features": {k: quantiles(rows[col]) for k, col in FEATURES.items()}}
    return out, pd.concat(frames, ignore_index=True)


def feature_shift(rows: pd.DataFrame) -> dict:
    frozen = json.loads((ESITO / "selector_final_r1/selector_final.json").read_text(encoding="utf-8"))["models"]["ibrido"]
    dev = rows[rows["line"].isin(DEV)]
    out = {"selector": {"theta_intercept_then_features": frozen["theta"], "features": frozen["features"],
                        "mu": frozen["mu"], "sd": frozen["sd"], "fit_rows": frozen["rows"],
                        "fit_rows_by_line": dev.groupby("line").size().to_dict()}, "contexts": {}}
    for c in "ABC":
        t = pd.read_csv(ESITO / f"export_abc_r2/targets_{c}.csv")
        t = t[t["eligible"]]
        rec = {}
        for (k, col), mu, sd, th in zip(FEATURES.items(), frozen["mu"], frozen["sd"], frozen["theta"][1:]):
            z = (t[col] - mu) / sd
            lo, hi = dev[col].quantile(0.01), dev[col].quantile(0.99)
            rec[k] = {"z_mean": float(z.mean()), "z_q10": float(z.quantile(0.1)), "z_q90": float(z.quantile(0.9)),
                      "share_beyond_2_sd": float((z.abs() > 2).mean()),
                      "share_outside_dev_range": float(((t[col] < dev[col].min()) | (t[col] > dev[col].max())).mean()),
                      "share_outside_dev_q01_q99": float(((t[col] < lo) | (t[col] > hi)).mean()),
                      "contribution_to_logit_mean": float((th * z).mean())}
        out["contexts"][c] = rec
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    exp, files = export_side()
    bench, rows = bench_side()
    out = {"written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "inputs_sha256": files,
           "export": exp, "bench_rows": bench, "selector_inputs": feature_shift(rows),
           "note": ("diagnostics of effects and corrections; no truth of A/B/C is read and nothing here is a score; the "
                    "retrieval check measures how far the hybrid moved from the t25 effect, not whether it is right")}
    a.out.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    for c in "ABC":
        e = exp[c]
        print(c, "share", {k: round(v, 3) for k, v in e["common_share"].items()}, "rms", {k: round(v, 4) for k, v in e["rms"].items()})
        print("  ratio R/T sel", round(e["ratio_rms_R_over_T_selector_input"]["q50"], 3), "R/t25", round(e["ratio_rms_R_over_t25"]["q50"], 3),
              "cos t25~sA", round(e["cos_per_target"]["t25_vs_s_anchor"]["q50"], 3), "R~t25", round(e["cos_per_target"]["R_vs_t25"]["q50"], 3),
              "Rspec~t25", round(e["cos_per_target"]["R_specific_vs_t25"]["q50"], 3), "proj", round(e["projection_of_R_on_t25"]["q50"], 3),
              "cosRbar~Tbar", round(e["cos_common_R_vs_common_t25"], 3))
        print("  pairwise", {k: round(v, 4) for k, v in e["mean_pairwise_cos_between_targets"].items()}, "retrieval", e["retrieval_of_own_t25_effect"])
        print("  features z", {k: (round(v["z_mean"], 2), round(v["share_outside_dev_q01_q99"], 2), round(v["contribution_to_logit_mean"], 3))
                               for k, v in out["selector_inputs"]["contexts"][c].items()})
    print("between contexts", exp["cos_of_common_R_between_contexts"])
    for line, b in bench.items():
        print(line, b["rows"], "share", round(b["common_share_R"]["weighted_mean"], 3), "ratio pooled", round(b["ratio_rms_R_over_T_pooled"], 3),
              "ratio row q50", round(b["ratio_rms_R_over_T_per_row"]["q50"], 3), "w q50", round(b["w"]["q50"], 3), (round(b["w"]["min"], 2), round(b["w"]["max"], 2)))


if __name__ == "__main__":
    main()
