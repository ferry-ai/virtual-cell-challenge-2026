"""Extract the scoring contract from the installed cell-eval2, not from prose.

The competition score is an unweighted mean over six metrics x three contexts,
each rescaled as `(u - b) / (r - b)` with b = the published baseline and
r = the measured split-half replicate. What decides strategy is not that formula
but the per-metric CLAMPS: three of the six can go deeply negative and two
effectively cannot, so the downside of a wrong prediction is not symmetric
across metrics. This pulls those numbers out of the package so the asymmetry is
a recorded fact, and so a version bump that moves it fails visibly.

Read-only with respect to the package; writes one file into `--out`.

An existing contract is never overwritten: it is a dated record of what the
installed scorer said that day. `reports/scorer/vcc2026_contract.json` is kept
precisely because it is superseded -- its `floor_note` was wrong, the corrected
re-extraction is `reports/scorer_2026-09-12/`, and the registry (R-002) relies on
both still existing. Re-extract into a new dated destination:

    scripts/py.cmd scripts/17_extract_scorer_contract.py --out reports/scorer_<date>

    scripts/py.cmd scripts/17_extract_scorer_contract.py
"""
from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path

import yaml
from cell_eval2.catalog import CATALOG, PROFILES


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).resolve().parents[1] / "reports/scorer")
    args = parser.parse_args()
    out = args.out / "vcc2026_contract.json"
    if out.exists():
        raise SystemExit(
            f"{out} exists; an extracted contract is evidence of what the installed "
            f"scorer said on one day. Write to a new path, e.g. "
            f"--out reports/scorer_<date>."
        )
    args.out.mkdir(parents=True, exist_ok=True)

    import cell_eval2
    cfg_path = Path(cell_eval2.__file__).parent / "configs/vcc2026.yaml"
    config = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    metrics = {}
    for name in PROFILES["vcc2026"]:
        spec = CATALOG[name]
        s = spec.scoring
        metrics[name] = {
            "scored": bool(s.scored),
            "direction": s.direction,
            "anchor": s.anchor,
            "clamp_low": s.clamp_low,
            "clamp_high": s.clamp_high,
            "metric_min": s.metric_min,
            "penalty": s.penalty,
            "aggregation": spec.agg,
        }
    scored = [n for n, m in metrics.items() if m["scored"]]
    if len(scored) != 6:
        raise ValueError(f"expected 6 scored vcc2026 metrics, found {len(scored)}: {scored}")

    contract = {
        "cell_eval2_version": version("cell-eval2"),
        "vcc_cli_version": version("vcc-cli"),
        "config_path": str(cfg_path),
        "official_config": config,
        "scored_metrics": scored,
        "metrics": metrics,
        "score_formula": "(u - b) / (r - b); b = published baseline, r = split-half replicate",
        "floor_note": (
            "A metric with clamp_low=None and metric_min=0.0 is UNFLOORED: its worst "
            "reachable score is (0 - b) / (r - b), i.e. it depends on that context's "
            "baseline and replicate. clamp_low=-6.0 on de_wilcoxon_lfc_nmae is a hard floor; "
            "clamp_low=0.0 floors the NORMALIZED expr_mse score, not its raw error: "
            "underestimation can still lose positive points. It is not a free-shrinkage guarantee."
        ),
    }
    out.write_text(json.dumps(contract, indent=2), encoding="utf-8")

    print(f"cell-eval2 {contract['cell_eval2_version']}, vcc-cli {contract['vcc_cli_version']}")
    print(f"\nDE: {config['de']['method']}, p_adj<{config['de']['p_adj_threshold']}, "
          f"min|log2FC|={config['de']['min_abs_log2fc']}, fdr_scope={config['de']['fdr_scope']}")
    print(f"gate: mean CPM per cell > {config['filter']['filter_gene_min_cpm_cell']}   "
          f"norm: target_sum={config['target_sum']:.0f}, bulk_target_sum={config['bulk_target_sum']:.0f}")
    print(f"PDS: {config['discrimination']['distance']} distance on the signed delta, "
          f"exclusion_scope={config['discrimination']['exclusion_scope']}, "
          f"tie_policy={config['discrimination']['tie_policy']}")
    print(f"control_source={config['control']!r} / {config['control_source']!r}: "
          "the predicted effect is measured against the REAL control cells")
    print("\n%-42s %-8s %-7s %-10s %s" % ("metric", "dir", "anchor", "clamp_low", "aggregation"))
    for n in scored:
        m = metrics[n]
        print("%-42s %-8s %-7s %-10s %s" % (
            n, m["direction"], m["anchor"],
            "UNFLOORED" if m["clamp_low"] is None else m["clamp_low"], m["aggregation"]))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
