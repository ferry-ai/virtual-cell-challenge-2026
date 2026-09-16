"""Apply the pre-declared decision rule to an expression-gate run, and say nothing else.

Reads the run's `summary.json` (paired differences) and `results.json` (which gate
each arm chose and what it touched), applies the `decision_rule` of the config that
produced the run, and writes a table, a decision file and the gate rows.

It declares no winner. The rule was written in the config before the run existed;
this script only reports whether each clause is satisfied, on which split, and by
how much. A comparison that is missing or was skipped fails the clause it is needed
by: no evidence promotes nothing.

With `--reference-table` it also compares the run's nine original arms against an
earlier run of the same protocol (m002), which is how "same splits, same metric" is
checked instead of asserted.

    scripts/py.cmd scripts/69_expression_gate_decision.py --run-id x001 --out reports/expression_gate_2026-09-16
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.benchmark.gate import evaluate_decision
from vcc2026.benchmark.protocol import load_yaml_config
from vcc2026.benchmark.run import jsonable
from vcc2026.manifest import RunManifest

GATE_KEYS = ("model", "direction_id", "seed", "pooled_mse_vs_null")


def _fmt(value, digits=4):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "sì" if value else "no"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _gate_rows(rows: list[dict], names: set[str]) -> list[dict]:
    out = []
    for row in rows:
        if row.get("model") not in names or not row.get("gate"):
            continue
        gate = row["gate"]
        out.append({
            **{k: row.get(k) for k in GATE_KEYS},
            "protocol": row.get("protocol"),
            "identity_chosen": gate.get("identity_chosen"),
            "chosen": gate.get("chosen"),
            "why_identity": gate.get("why_identity"),
            "exposure_on_test": gate.get("exposure_on_test"),
            "base_check": gate.get("base_check"),
            "selection_grid": (row.get("selection") or {}).get("grid"),
            "val_targets": len((row.get("selection") or {}).get("val_targets") or []),
        })
    return out


def _clause_table(decision: dict) -> list[str]:
    lines = [
        "## Le clausole, una riga per split",
        "",
        "Positivo = il braccio `a` è **peggio** di `b`. La statistica è la differenza "
        "appaiata per bersaglio (`diff`), la stessa di CP-0013.",
        "",
        "| variante | clausola | a | b | direzione | seed | differenza | IC95 | IC esclude 0 | clausola soddisfatta |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for variant, block in decision["variants"].items():
        for clause in block["clauses"]:
            for split in clause["splits"]:
                ci = split.get("ci95")
                lines.append(
                    f"| {variant} | {clause['id']} | {clause['a']} | {clause['b']} | "
                    f"{split['direction_id']} | {split['seed']} | "
                    f"{_fmt(split.get('mean_a_minus_b'))} | "
                    f"{'—' if not ci else f'[{ci[0]:.4f}, {ci[1]:.4f}]'} | "
                    f"{_fmt(split.get('ci95_excludes_zero'))} | "
                    f"{_fmt(split['holds'])} |"
                )
    return lines


def _gate_table(gate_rows: list[dict]) -> list[str]:
    lines = [
        "",
        "## Che gate è stato scelto, e quanto ha toccato",
        "",
        "| braccio | direzione | seed | identità | midpoint CPM | pendenza | attenuazione + | quota di |Δ| rimossa | MSE/nullo |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in gate_rows:
        chosen = row.get("chosen") or {}
        exposure = row.get("exposure_on_test") or {}
        lines.append(
            f"| {row['model']} | {row['direction_id']} | {row['seed']} | "
            f"{_fmt(chosen.get('identity'))} | {_fmt(chosen.get('midpoint_cpm'), 1)} | "
            f"{_fmt(chosen.get('slope_per_decade'), 1)} | "
            f"{_fmt(chosen.get('positive_attenuation'), 2)} | "
            f"{_fmt(exposure.get('fraction_abs_delta_removed'))} | "
            f"{_fmt(row.get('pooled_mse_vs_null'))} |"
        )
    return lines


def _read_table(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="") as fh:
        return {
            (r["model"], r["protocol"], r["direction_id"], r["seed"]): r
            for r in csv.DictReader(fh)
        }


def compare_with_reference(run_table: Path, reference: Path, protocol: str) -> dict:
    """Same protocol, same splits: the shared rows must carry the same numbers."""
    mine, theirs = _read_table(run_table), _read_table(reference)
    shared = sorted(set(mine) & set(theirs))
    rows, worst = [], 0.0
    for key in shared:
        if key[1] != protocol:
            continue
        deltas = {}
        for field in ("pooled_mse_vs_null", "pearson_median", "coverage_targets"):
            a, b = mine[key].get(field), theirs[key].get(field)
            if a in (None, "") or b in (None, ""):
                continue
            deltas[field] = abs(float(a) - float(b))
            worst = max(worst, deltas[field])
        rows.append({"key": list(key), "abs_diff": deltas})
    return {
        "reference": str(reference),
        "protocol": protocol,
        "n_shared_rows": len(rows),
        "max_abs_diff": worst,
        "identical": worst == 0.0,
        "rows": rows,
        "note": (
            "Rows shared with the reference run. A non-zero difference is not a "
            "failure by itself -- the code moved between the two runs -- but it has "
            "to be reported, not assumed away."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", default="x001")
    p.add_argument("--run-dir", type=Path, default=None)
    p.add_argument("--config", type=Path, default=None)
    p.add_argument("--out", type=Path, required=True,
                   help="a NEW directory; an existing one is refused")
    p.add_argument("--reference-table", type=Path, default=None,
                   help="comparison_table.csv of an earlier run of the same protocol")
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    run_dir = args.run_dir or config.run_dir(args.run_id, create=False)
    cfg_path = args.config or (
        Path(__file__).resolve().parents[1] / "configs" / "benchmark_expression_gate.yaml"
    )
    cfg = load_yaml_config(cfg_path)
    rule = cfg["decision_rule"]
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))

    out_dir = Path(args.out)
    if out_dir.exists() and any(out_dir.iterdir()) and not args.allow_overwrite:
        raise SystemExit(f"{out_dir} is not empty; give a new --out")
    out_dir.mkdir(parents=True, exist_ok=True)

    decision = evaluate_decision(
        summary["paired_differences"],
        rule,
        directions=[d["id"] for d in cfg["directions"]],
        seeds=[int(s) for s in cfg["pilot"]["seeds"]],
    )
    decision["run_id"] = args.run_id
    decision["run_dir"] = str(run_dir)
    decision["config"] = str(cfg_path)
    decision["n_result_rows"] = summary.get("n_result_rows")
    decision["gene_universe"] = summary.get("gene_universe")
    decision["machine"] = summary.get("machine")

    names = {a["name"] for a in cfg["expression_gate"]["arms"]}
    gate_rows = _gate_rows(results["rows"], names)
    decision["n_identity_chosen"] = sum(bool(r["identity_chosen"]) for r in gate_rows)
    decision["n_gate_rows"] = len(gate_rows)

    if args.reference_table:
        decision["reproduction"] = compare_with_reference(
            run_dir / "comparison_table.csv", args.reference_table, rule["protocol"]
        )

    lines = [
        "# Gate di espressione: la regola di decisione applicata ai numeri",
        "",
        f"Run `{args.run_id}`, protocollo `{rule['protocol']}`, statistica "
        f"`{decision['statistic']}`. Generata da `scripts/69_expression_gate_decision.py`, "
        "non a mano.",
        "",
        "La regola è stata scritta in `configs/benchmark_expression_gate.yaml` **prima** "
        f"del run (`fixed_before_the_run: {decision['rule_fixed_before_the_run']}`, "
        f"`owner_confirmed: {decision['owner_confirmed']}`). "
        "Nessun vincitore viene dichiarato: qui si legge solo se le clausole sono "
        "soddisfatte.",
        "",
        "| variante | promossa a candidato |",
        "| --- | --- |",
    ]
    for variant, block in decision["variants"].items():
        lines.append(f"| {variant} | {_fmt(block['promoted_to_candidate'])} |")
    lines += ["", f"Gate identità scelto in {decision['n_identity_chosen']} righe su "
                  f"{decision['n_gate_rows']}.", ""]
    lines += _clause_table(decision)
    lines += ["", "## Letture dichiarate prima del run (non promuovono nulla)", "",
              "| clausola | variante | vale ovunque | split che la rispettano |",
              "| --- | --- | --- | --- |"]
    for reading in decision["reading_clauses"]:
        lines.append(
            f"| {reading['id']} | {reading.get('variant') or '—'} | "
            f"{_fmt(reading['holds'])} | {reading['n_holding']}/{reading['n_splits']} |"
        )
    lines += _gate_table(gate_rows)
    if "reproduction" in decision:
        rep = decision["reproduction"]
        lines += [
            "", "## Riproduzione delle righe condivise con il run di riferimento", "",
            f"Righe condivise: {rep['n_shared_rows']}. Differenza assoluta massima: "
            f"{rep['max_abs_diff']:.2e}. Identiche: {_fmt(rep['identical'])}.",
        ]

    (out_dir / "decision_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "decision.json").write_text(
        json.dumps(jsonable(decision), indent=2), encoding="utf-8")
    (out_dir / "gate_rows.json").write_text(
        json.dumps(jsonable(gate_rows), indent=2), encoding="utf-8")

    manifest = RunManifest(
        run_id=args.run_id, stage="69_expression_gate_decision",
        config={k: str(v) for k, v in vars(args).items()},
    )
    manifest.add_input("config", cfg_path)
    manifest.add_input("summary", run_dir / "summary.json")
    manifest.add_output("decision", out_dir / "decision.json")
    manifest.add_output("table", out_dir / "decision_table.md")
    manifest.metrics = {
        "any_promoted_to_candidate": decision["any_promoted_to_candidate"],
        "n_identity_chosen": decision["n_identity_chosen"],
        "winner_declared": False,
        "not_a_vcc_score": True,
    }
    manifest.note(
        "The rule was fixed in the config before the run. This script applies it; "
        "it does not choose a model and does not adopt anything."
    )
    manifest.write(out_dir / "manifest_69_expression_gate_decision.json",
                   allow_overwrite=args.allow_overwrite)
    print(json.dumps({
        "any_promoted_to_candidate": decision["any_promoted_to_candidate"],
        "n_identity_chosen": decision["n_identity_chosen"],
        "out": str(out_dir),
    }, indent=2))


if __name__ == "__main__":
    main()
