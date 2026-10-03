"""Which datasets and how many cells really enter a training, and why the others stay out (the owner's question of 30/09).

From one prepass (qc.json, splits.json, prepass_done.json, train_log.jsonl) and, when given, its training
(coverage.json): per study and key, the cells read, the controls, the cells admitted, the training cells, the cells
drawn, the rejections by rule, the held-out keys, and the loss share each line group actually carried. Writes a
Markdown table and a JSON next to it.

    python inventory.py --prepass <prepass dir> [--training <training dir>] --out <new file>.md
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prepass", type=Path, required=True)
    p.add_argument("--training", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    qc = json.loads((a.prepass / "qc.json").read_text(encoding="utf-8"))
    sp = json.loads((a.prepass / "splits.json").read_text(encoding="utf-8"))
    done = json.loads((a.prepass / "prepass_done.json").read_text(encoding="utf-8"))
    cells = defaultdict(Counter)
    for line in (a.prepass / "train_log.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("msg") == "first read":
            cells[r["study"]]["cells"] += int(r["cells"])
        if r.get("msg") == "second read":
            cells[r["shard"].split("__")[0]]["training_shard_cells"] += int(r["training_cells"])
    rejected = defaultdict(Counter)
    for kr, n in qc["rejected"].items():
        study, context, reason = kr.split("|", 2)
        rejected[f"{study}|{context}"][reason] += n
    by_unit = sp["loss_weights"]["training_cells_by_unit"]
    weights = sp["loss_weights"]["by_unit"]
    cov = json.loads((a.training / "coverage.json").read_text(encoding="utf-8")) if a.training else None
    drawn = {r["key"]: r for r in cov["by_key"]} if cov else {}
    held = set(sp["held_keys"])
    keys = sorted(set(qc["controls_per_key"]) | set(rejected))
    rows = []
    for k in keys:
        group = next((g for g, ks in sp["line_groups"].items() if k in ks), "?")
        unit = f"{group}::{k.split('|', 1)[0]}"
        rows.append({"key": k, "group": group, "held_out": k in held, "controls": qc["controls_per_key"].get(k, 0),
                     "rejected": dict(rejected.get(k, {})), "training_cells_of_unit": by_unit.get(unit),
                     "unit_weight": weights.get(unit), "admitted_offered": drawn.get(k, {}).get("admitted_offered"),
                     "distinct_drawn": drawn.get(k, {}).get("distinct_drawn")})
    lines = [f"# Inventario delle cellule: linea esclusa {sp['holdout_group']}", "",
             f"Prepass: {done['cells']} cellule lette in {done['shards']} shard, {done['admitted_training_cells']} "
             f"ammesse per il training, {done['evaluation_groups']} gruppi di valutazione, serbatoio di "
             f"{done.get('pool_rows')} controlli.", "",
             "| Chiave (studio\\|contesto) | Gruppo | Esclusa | Controlli | Rifiutate (regola: cellule) | Training dell'unità | "
             "Peso | Offerte | Viste |", "|---|---|---|---:|---|---:|---:|---:|---:|"]
    for r in rows:
        rej = ", ".join(f"{k}: {v}" for k, v in sorted(r["rejected"].items(), key=lambda kv: -kv[1])) or "—"
        lines.append(f"| `{r['key'].replace('|', chr(92) + '|')}` | {r['group']} | {'sì' if r['held_out'] else ''} | {r['controls']} | {rej} | "
                     f"{r['training_cells_of_unit'] or ''} | {round(r['unit_weight'], 4) if r['unit_weight'] else ''} | "
                     f"{r['admitted_offered'] or ''} | {r['distinct_drawn'] or ''} |")
    if cov:
        lines += ["", "Quote della loss per gruppo, dalle cellule estratte: " +
                  ", ".join(f"{g} {v:.3f}" for g, v in cov["loss_shares"]["by_group"].items()) + "."]
    lines += ["", "Classi dopo il QC: " + json.dumps(sp["roles_after_qc"]["cells_whose_class_changed"]) +
              f"; simboli addestrati {sp['roles_after_qc']['trained_symbols_after_qc']} "
              f"(prima del QC {sp['roles_after_qc']['trained_symbols_before_qc']})."]
    a.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    a.out.with_suffix(".json").write_text(json.dumps({"rows": rows, "prepass_done": done,
                                                      "loss_shares": cov["loss_shares"] if cov else None},
                                                     indent=1), encoding="utf-8")
    print(f"{len(rows)} keys -> {a.out}")


if __name__ == "__main__":
    main()
