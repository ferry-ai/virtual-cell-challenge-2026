"""How much room an expression gate would have on the official contexts A/B/C.

This is not a prediction and not a model. It reads the unperturbed control cells
the task ships -- nothing else -- and counts how many genes, and how many of the
300 targets, sit below each CPM level in each context, plus how many are absent in
one context while well expressed in another. That last number is the only one the
gate can act on: a gene that is low everywhere is compressed by a global amplitude,
not by a context.

It exists because the three-context benchmark cannot answer this. That benchmark
scores on the intersection of three perturbation panels, which already excludes
low-expression genes, so a gate there has almost nothing to act on -- which is a
property of the benchmark's gene universe, not of the idea.

The controls are read with `inference.read_basal_profile`, the reader that already
exists. Nothing is written into the raw bundle.

    scripts/py.cmd scripts/70_context_presence_audit.py --out reports/expression_gate_2026-09-16
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.genes import official_axis
from vcc2026.inference import read_basal_profile
from vcc2026.manifest import RunManifest
from vcc2026.presence import GenePresence, presence_summary

THRESHOLDS = (0.1, 1.0, 5.0, 10.0, 30.0, 100.0)
ABSENT_CPM = 1.0
EXPRESSED_CPM = 10.0


def panel_targets(bundle: Path) -> list[str]:
    """The 300 official targets, read from the bundle's own table."""
    import csv

    with (bundle / "pert_counts.csv").open(encoding="utf-8", newline="") as fh:
        return [row["target_gene"] for row in csv.DictReader(fh)]


def context_block(presence: GenePresence, targets, position) -> dict:
    cpm = presence.cpm
    idx = np.array([position.get(t, -1) for t in targets], dtype=np.int64)
    target_cpm = np.where(idx >= 0, cpm[np.clip(idx, 0, None)], np.nan)
    low = sorted(
        ({"target": t, "cpm": (None if not np.isfinite(v) else float(v))}
         for t, v in zip(targets, target_cpm)
         if not np.isfinite(v) or v < 5.0),
        key=lambda d: (d["cpm"] is not None, d["cpm"]),
    )
    return {
        "context": presence.context,
        "n_cells": presence.n_cells,
        "total_molecules": presence.library,
        "counts_for_a_gene_at_1_cpm": presence.library / 1e6,
        "n_genes": int(cpm.size),
        "n_genes_exactly_zero": int(np.sum(cpm == 0.0)),
        "genes": presence_summary(cpm, thresholds=THRESHOLDS),
        "panel": {
            "n_targets": len(targets),
            "n_on_axis": int(np.sum(idx >= 0)),
            **presence_summary(target_cpm, thresholds=THRESHOLDS),
            "targets_below_5_cpm": low,
        },
    }


def context_specific_absence(cpm_by_context: dict) -> dict:
    """Genes absent in one context and well expressed in another.

    A gene that is low in every context is handled by the global amplitude; only a
    gene that is off *here* and on *there* is something a context gate can use.
    """
    contexts = sorted(cpm_by_context)
    stack = np.vstack([cpm_by_context[c] for c in contexts])
    absent = stack < ABSENT_CPM
    expressed = stack >= EXPRESSED_CPM
    pairs = {}
    for i, dest in enumerate(contexts):
        for j, source in enumerate(contexts):
            if i == j:
                continue
            pairs[f"{source}->{dest}"] = int(np.sum(absent[i] & expressed[j]))
    return {
        "absent_below_cpm": ABSENT_CPM,
        "expressed_at_or_above_cpm": EXPRESSED_CPM,
        "n_genes_absent_in_all_contexts": int(np.sum(absent.all(axis=0))),
        "n_genes_absent_in_at_least_one": int(np.sum(absent.any(axis=0))),
        "n_genes_absent_here_expressed_elsewhere": pairs,
        "note": (
            "The pair counts are the genes a destination gate would compress and a "
            "source gate would not: the only place where destination and source "
            "gates can differ."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--contexts", nargs="*", default=None,
                   help="defaults to the validation contexts of configs/config.yaml")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    paths = config.paths()
    bundle = paths.raw / "controls"
    contexts = args.contexts or list(config.challenge().contexts_validation)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "context_presence.json"
    if dest.exists() and not args.allow_overwrite:
        raise SystemExit(f"{dest} exists; give a new --out")

    axis = official_axis()
    position = axis.position()
    targets = panel_targets(bundle)
    blocks, cpm_by_context = {}, {}
    for ctx in contexts:
        path = bundle / f"context_{ctx}.h5ad"
        basal = read_basal_profile(path, context=ctx)
        if basal.n_genes != len(axis):
            raise SystemExit(
                f"{path}: {basal.n_genes} genes, official axis has {len(axis)}"
            )
        presence = GenePresence.from_basal_profile(basal)
        blocks[ctx] = context_block(presence, targets, position)
        blocks[ctx]["source_file"] = str(path)
        cpm_by_context[ctx] = presence.cpm
        print(f"{ctx}: {basal.n_cells} cells, "
              f"{blocks[ctx]['genes']['n_below_cpm']['5.0']} genes below 5 CPM")

    report = {
        "question": (
            "How many genes and how many of the 300 targets are too lowly expressed "
            "in each official context for a knockdown to push them further down"
        ),
        "what_this_is_not": (
            "Not a prediction, not a model, not a score. Counts on the control cells "
            "the task ships, nothing else."
        ),
        "reader": "vcc2026.inference.read_basal_profile",
        "thresholds_cpm": list(THRESHOLDS),
        "scorer_filter_gene_min_cpm_cell": 5.0,
        "scorer_filter_source": "reports/scorer_2026-09-12/vcc2026_contract.json",
        "contexts": blocks,
        "context_specific_absence": context_specific_absence(cpm_by_context),
    }
    dest.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Quanto spazio avrebbe il gate sui contesti ufficiali",
        "",
        "Conteggi sulle sole cellule di controllo di A, B e C, lette con "
        "`inference.read_basal_profile`. Non è una previsione e non è un punteggio. "
        "Prodotto da `scripts/70_context_presence_audit.py`.",
        "",
        "| contesto | cellule | molecole totali | conteggi attesi per un gene a 1 CPM | "
        "geni a zero | geni < 1 CPM | geni < 5 CPM | bersagli < 5 CPM |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for ctx, block in blocks.items():
        genes, panel = block["genes"], block["panel"]
        lines.append(
            f"| {ctx} | {block['n_cells']:,} | {block['total_molecules']:,.0f} | "
            f"{block['counts_for_a_gene_at_1_cpm']:,.0f} | "
            f"{block['n_genes_exactly_zero']} | {genes['n_below_cpm']['1.0']} | "
            f"{genes['n_below_cpm']['5.0']} | {panel['n_below_cpm']['5.0']} |"
        )
    absence = report["context_specific_absence"]
    lines += [
        "",
        f"Geni sotto {ABSENT_CPM:g} CPM in **tutti** i contesti: "
        f"{absence['n_genes_absent_in_all_contexts']}; in almeno uno: "
        f"{absence['n_genes_absent_in_at_least_one']}.",
        "",
        "Geni spenti in un contesto e accesi (≥ 10 CPM) in un altro — è l'unica parte "
        "su cui un gate di contesto può agire diversamente da un filtro globale:",
        "",
        "| sorgente → destinazione | geni |",
        "| --- | ---: |",
    ]
    for pair, n in absence["n_genes_absent_here_expressed_elsewhere"].items():
        lines.append(f"| {pair} | {n} |")
    (out_dir / "context_presence.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = RunManifest(
        run_id="x001", stage="70_context_presence_audit",
        config={k: str(v) for k, v in vars(args).items()},
    )
    for ctx in contexts:
        manifest.add_input(f"controls_{ctx}", bundle / f"context_{ctx}.h5ad")
    manifest.add_input("panel", bundle / "pert_counts.csv")
    manifest.add_output("report", dest)
    manifest.metrics = {
        ctx: {
            "n_genes_below_5_cpm": blocks[ctx]["genes"]["n_below_cpm"]["5.0"],
            "n_targets_below_5_cpm": blocks[ctx]["panel"]["n_below_cpm"]["5.0"],
        }
        for ctx in contexts
    }
    manifest.note("Read-only on the official control bundle. No prediction was made.")
    manifest.write(out_dir / "manifest_70_context_presence_audit.json",
                   allow_overwrite=args.allow_overwrite)
    print(json.dumps(report["context_specific_absence"], indent=2))


if __name__ == "__main__":
    main()
