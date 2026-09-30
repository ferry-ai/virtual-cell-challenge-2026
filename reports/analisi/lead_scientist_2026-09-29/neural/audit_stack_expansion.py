"""Metadata-only Stack coverage and prospective disjoint target proposals.

No HepG2 outcomes, counts, training, generation or uploads are read/performed.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import statistics


def rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def select(candidates, n=12):
    return sorted(candidates, key=lambda t: hashlib.sha256(f"StackConfirm:20260929:{t}".encode()).hexdigest())[:n]


def describe(targets, counts):
    thresholds = [1, 40, 64, 128]
    return {"targets": len(targets), "n_cells_sum": sum(counts[t] for t in targets),
            "by_min_cells": {str(n): sorted(t for t in targets if counts[t] >= n) for n in thresholds},
            "count_by_min_cells": {str(n): sum(counts[t] >= n for t in targets) for n in thresholds},
            "median_positive": statistics.median([counts[t] for t in targets if counts[t] > 0]) if any(counts[t] > 0 for t in targets) else None}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["source", "panel", "genes", "generator-manifest", "pilot-plan", "out"]:
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    groups, var = rows(a.source / "groups.csv"), rows(a.source / "var.csv")
    panel = {r["target_gene"] for r in rows(a.panel)}
    genes = [r["gene_name"] for r in rows(a.genes)]
    source_genes = [r["gene_name"] for r in var]
    selected, original = Counter(), Counter()
    ntc_selected, ntc_original = 0, 0
    for r in groups:
        if r["is_ntc"] == "True":
            ntc_selected += int(r["n_selected"])
            ntc_original += int(r["n_cells_obs"])
        else:
            selected[r["gene"]] += int(r["n_selected"])
            original[r["gene"]] += int(r["n_cells_obs"])
    manifest = json.loads(a.generator_manifest.read_text())
    pilot = json.loads(a.pilot_plan.read_text())["targets"]
    development, confirmation, eligible = map(set, [manifest["development"], manifest["confirmation"], manifest["eligible"]])
    reserve = eligible - development - confirmation
    report = json.loads((a.source / "report.json").read_text())
    result = {"claim": "measured metadata coverage; target proposals before Stack pilot scores; no HepG2 outcomes read",
        "source": str(a.source), "source_report_md5_original": report["md5"], "source_finished_utc": report["finished_utc"],
        "hashes": {str(path): sha(path) for path in [a.panel, a.genes, a.generator_manifest, a.pilot_plan,
                                                          a.source / "groups.csv", a.source / "var.csv", a.source / "report.json"]},
        "grouping": "gene_transcript records aggregated by gene, keeping NTC separately",
        "axis": {"raw_columns": len(source_genes), "unique_symbols": len(set(source_genes)),
                 "official_genes": len(genes), "intersection_official": len(set(source_genes) & set(genes)),
                 "duplicate_symbols": {g: n for g, n in Counter(source_genes).items() if n > 1}},
        "controls": {"original": ntc_original, "selected": ntc_selected, "need_for_prompt": 512},
        "current_panel_subset": describe(panel, selected), "current_panel_original": describe(panel, original),
        "stage73_default_eligible": sorted(t for t in panel if selected[t] >= 40 and t in set(source_genes)),
        "pilot_in_subset": {t: selected[t] for t in pilot},
        "development_subset": describe(development, selected), "confirmation_subset": describe(confirmation, selected),
        "reserve_subset": describe(reserve, selected),
        "reserve_original": describe(reserve, original),
        "confirmation_rule": "First12 ascending SHA256('StackConfirm:20260929:<target>') from HepG2 reserve, original K562>=64; no automatic substitution",
        "confirmation_targets_original": select(t for t in reserve if original[t] >= 64),
        "confirmation_targets_subset_only": select(t for t in reserve if selected[t] >= 64),
        "production_targets_subset_ge64": sorted(t for t in panel if selected[t] >= 64),
        "production_fallback_targets": sorted(t for t in panel if selected[t] < 64),
        "files": {q.name: q.stat().st_size for q in sorted(a.source.glob("cells_part*.h5ad"))},
        "subset_total_cells": report["selected_cells"], "counts_per_panel_target": {t: selected[t] for t in sorted(panel)}}
    confirm = result["confirmation_targets_original"]
    production = result["production_targets_subset_ge64"]
    result["io"] = {"all_shards_bytes": sum(result["files"].values()),
        "confirmation_original_selected_cells_with_ntc": sum(min(original[t], 128) for t in confirm) + 512,
        "production_selected_cells_with_ntc": sum(min(selected[t], 128) for t in production) + 512,
        "confirmation_raw_count_payload_bytes": (sum(min(original[t], 128) for t in confirm) + 512) * 8248 * 4,
        "production_raw_count_payload_bytes": (sum(min(selected[t], 128) for t in production) + 512) * 8248 * 4}
    with a.out.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({"panel_subset": result["current_panel_subset"]["count_by_min_cells"],
        "panel_original": result["current_panel_original"]["count_by_min_cells"],
        "stage73_default": len(result["stage73_default_eligible"]), "axis": result["axis"],
        "controls": result["controls"], "subset_dev": result["development_subset"]["count_by_min_cells"],
        "subset_confirmation": result["confirmation_subset"]["count_by_min_cells"],
        "subset_reserve": result["reserve_subset"]["count_by_min_cells"],
        "confirmation_original": confirm, "confirmation_subset": result["confirmation_targets_subset_only"],
        "io": result["io"]}, indent=2))


if __name__ == "__main__":
    main()
