"""Recompute exploratory diagnostics from CellNet r2 and prepasses, without opening reserves."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MODEL = ROOT / "reports/modelli"
INPUTS = {}


def read(path):
    data = path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    return json.loads(data)


def stats(rows):
    fields = ["ll_gain_vs_no_effect", "ll_gain_vs_unknown_target", "cos_model", "cos_transfer", "cos_generic", "pi_mean", "cells", "admitted_cells"]
    out = {"groups": len(rows), "unique_symbols": len({r["symbol"] for r in rows})}
    for f in fields:
        a = np.array([r[f] for r in rows if r.get(f) is not None], float)
        if len(a):
            out[f] = {"mean": float(a.mean()), "median": float(np.median(a)), "positive": float((a > 0).mean()), "n": len(a)}
    out["likelihood_positive_cosine_negative"] = sum(r["ll_gain_vs_unknown_target"] > 0 and r["cos_model"] < 0 for r in rows)
    paired = [r["cos_model"] - r["cos_transfer"] for r in rows if r.get("cos_transfer") is not None]
    if paired:
        a = np.array(paired)
        rng = np.random.default_rng(20261001)
        boot = np.array([rng.choice(a, len(a), replace=True).mean() for _ in range(3000)])
        out["model_minus_transfer"] = {"mean": float(a.mean()), "win_fraction": float((a > 0).mean()),
                                      "exploratory_target_bootstrap_95": np.quantile(boot, [.025, .975]).tolist(),
                                      "caveat": "one held-out context; targets are not independent biological families"}
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(exist_ok=False)
    base = MODEL / "cellnet_esteso_2026-10-01/esito/training_r2/train"
    arms = {arm: read(base / arm / "eval.json") for arm in ("desc", "ident")}
    results, flat = {}, []
    for arm, ev in arms.items():
        results[arm] = {}
        for cl in ("C", "T", "J"):
            rows = [r for r in ev[cl] if "skipped" not in r]
            by_key = defaultdict(list)
            for r in rows:
                by_key[r["key"]].append(r)
                flat.append({"arm": arm, "class": cl, **r})
            results[arm][cl] = {"all": stats(rows), "by_key": {k: stats(v) for k, v in sorted(by_key.items())}}
            macro = [np.mean([r["cos_model"] for r in v]) for v in by_key.values()]
            results[arm][cl]["context_key_macro_cosine"] = float(np.mean(macro))
    coverage = read(base / "coverage.json")
    cfg = read(base / "config.json")
    by_study = defaultdict(lambda: {"cells": 0, "draws": 0, "contexts": []})
    for r in coverage["by_key"]:
        s = r["key"].split("|", 1)[0]
        by_study[s]["cells"] += r["admitted_offered"]
        by_study[s]["draws"] += r["draws"]
        by_study[s]["contexts"].append(r["key"])
    total = sum(v["cells"] for v in by_study.values())
    for k, v in by_study.items():
        v["cell_fraction"] = v["cells"] / total
        v["loss_weight"] = cfg["study_weights"][k]
    datasets = {}
    for label, rel in [("r5", "cellnet_esteso_2026-10-01/esito/prepass_r5/prepass"),
                       ("r7", "cellnet_completo_2026-10-01/esito/prepass_r7/prepass")]:
        q = read(MODEL / rel / "qc.json")
        spl = read(MODEL / rel / "splits.json")
        done = read(MODEL / rel / "prepass_done.json")
        datasets[label] = {"done": done, "classes": spl["admitted_cells_by_class"],
                           "hidden_symbols": len(spl["hidden_symbols"]), "controls": q["controls_per_key"],
                           "rejected": q["rejected"], "control_quantiles": q["control_quantiles"],
                           "kinds": spl["labels"]["cells_by_kind_and_study"],
                           "republications": q["identity"]["declared_republications"],
                           "content_matches": q["identity"]["content_matches_across_keys"]}
    out = {"created_utc": datetime.now(timezone.utc).isoformat(), "claim_type": "exploratory, post hoc, not VCC scores",
           "evaluation": results, "training_composition": dict(by_study), "datasets": datasets}
    (a.out / "diagnostics.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    with (a.out / "target_diagnostics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(flat[0]))
        w.writeheader(); w.writerows(flat)
    INPUTS[str(Path(__file__).relative_to(ROOT))] = {"sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (a.out / "manifest.json").write_text(json.dumps(INPUTS, indent=2), encoding="utf-8")
    print(json.dumps({"T_by_key": {k: {"n": v["groups"], "cos": v["cos_model"]["mean"],
                                             "generic": v["cos_generic"]["mean"],
                                             "ll_specific": v["ll_gain_vs_unknown_target"]["mean"],
                                             "contradictory": v["likelihood_positive_cosine_negative"]}
                                       for k, v in results["desc"]["T"]["by_key"].items()},
                      "C": results["desc"]["C"]["all"], "J": results["desc"]["J"]["all"],
                      "composition": dict(by_study)}, indent=2))


if __name__ == "__main__":
    main()
