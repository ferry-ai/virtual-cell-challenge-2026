"""Read the labels of the units of a spec from their remote files, before any job: controls and unassigned cells per
context, the labels the prepass will resolve to single genes, combinations or nothing, and the features that map to
the official axis. Reads obs and var only (a few MB per file), never the matrix.

    python smoke_labels.py jobs_colab/<job>_spec.json --axis <gene_names.csv> --out <new json>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "modelli" / "risposta_biologica_2026-09-30"))
import adapters  # noqa: E402
import cell_data as CD  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("spec", type=Path)
    p.add_argument("--axis", required=True)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    axis = [l.strip().split(",")[0] for l in open(a.axis, encoding="utf-8") if l.strip()][1:]
    axis_set = set(axis)
    spec = json.loads(a.spec.read_text(encoding="utf-8"))
    report = {"spec": a.spec.name, "units": {}}
    for u in spec["units"]:
        kw = u["kwargs"]
        f = adapters._h5_open(kw["path"])
        try:
            obs, var = f["obs"], f["var"]
            target = adapters._h5_column(obs, kw.get("target_col", "perturbation")).astype(str)
            rx = re.compile(kw["control_pattern"]) if kw.get("control_pattern") else None
            is_ctrl = np.isin(target, kw.get("control_values", ["control"]))
            if rx is not None:
                is_ctrl |= np.array([bool(rx.search(t)) for t in target])
            unassigned = np.isin(target, ["nan", "<NA>", "", "None", "MISSING"]) & ~is_ctrl
            ctx = adapters._h5_column(obs, kw["context_col"]).astype(str) if kw.get("context_col") else \
                np.array([kw["context"]] * target.size)
            lib = adapters._h5_column(obs, kw["library_col"]) if kw.get("library_col") else None
            vindex = var.attrs.get("_index", "_index")
            vindex = vindex.decode() if isinstance(vindex, bytes) else str(vindex)
            symbols = list(adapters._h5_column(var, kw.get("var_symbol_col") or vindex))
        finally:
            f.close()
        mapped = int(sum(s in axis_set for s in symbols))
        kinds = Counter()
        per_label = Counter(target[~is_ctrl & ~unassigned])
        resolved = Counter()
        for lab, n in per_label.items():
            kind, found = CD.parse_label(lab, axis_set)
            kinds[kind] += n
            if kind == "single":
                resolved[found[0]] += n
        by_ctx = {}
        for c in sorted(set(ctx)):
            m = ctx == c
            by_ctx[c] = {"cells": int(m.sum()), "controls": int((m & is_ctrl).sum()),
                         "unassigned": int((m & unassigned).sum())}
        report["units"][u["name"]] = {
            "cells": int(target.size), "features": len(symbols), "features_on_axis": mapped,
            "contexts": by_ctx, "perturbed_cells_by_kind": dict(kinds), "single_gene_targets": len(resolved),
            "top_single": resolved.most_common(5),
            "unresolved_examples": [l for l, _ in per_label.most_common(400)
                                    if CD.parse_label(l, axis_set)[0] == "unresolved"][:8],
            "libraries": int(len(set(lib))) if lib is not None else None}
        print(u["name"], json.dumps(report["units"][u["name"]], ensure_ascii=False)[:900], flush=True)
    a.out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
