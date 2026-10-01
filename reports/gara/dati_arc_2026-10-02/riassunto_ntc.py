"""Summarise the NTC guide structure of the official controls, per context.

Reads reports/gara/external_compat/ntc_guide_structure.csv and prints, for A, B and C, the
number of guides and cells, the min/median/max of the per-guide mean library size, the
range of guide ids, and whether all contexts share the same guide ids. Used in RISULTATI.md §2.
Run from the repository root: python reports/gara/dati_arc_2026-10-02/riassunto_ntc.py
"""
import collections
import csv
import statistics

rows = list(csv.DictReader(open("reports/gara/external_compat/ntc_guide_structure.csv")))
by_context = collections.defaultdict(list)
for row in rows:
    by_context[row["context"]].append(row)

for context, group in sorted(by_context.items()):
    sizes = [float(r["mean_library_size"]) for r in group]
    ids = sorted(int(r["ntc_id"].split("-")[-1]) for r in group)
    print(context, len(group), "guides", sum(int(r["n_cells"]) for r in group), "cells",
          "libsize min/med/max", round(min(sizes)), round(statistics.median(sizes)), round(max(sizes)),
          "id range", ids[0], ids[-1])

reference = {r["ntc_id"] for r in by_context["A"]}
print("same ids in all contexts:", all({r["ntc_id"] for r in g} == reference for g in by_context.values()))
