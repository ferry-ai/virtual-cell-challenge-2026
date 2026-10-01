"""Read local HepG2 counts in blocks: developmental signal, sampling and metric diagnostics only."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def column(node):
    if isinstance(node, h5py.Group):
        cats = np.array([x.decode() if isinstance(x, bytes) else str(x) for x in node["categories"][:]])
        return cats[node["codes"][:]]
    a = node[:]
    return np.array([x.decode() if isinstance(x, bytes) else str(x) for x in a])


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(4 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def cosine(a, b):
    return float(a @ b / max(float(np.linalg.norm(a)*np.linalg.norm(b)), 1e-30))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--raw", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(exist_ok=False)
    mod = ROOT / "reports/modelli"
    p5 = mod / "cellnet_esteso_2026-10-01/esito/prepass_r5/prepass/splits.json"
    p7 = mod / "cellnet_completo_2026-10-01/esito/prepass_r7/prepass/splits.json"
    ep = mod / "cellnet_esteso_2026-10-01/esito/training_r2/train/desc/eval.json"
    s5, s7, ev = [json.loads(p.read_text(encoding="utf-8")) for p in (p5, p7, ep)]
    h5, h7 = set(s5["hidden_symbols"]), set(s7["hidden_symbols"])
    split_change = {"r5_hidden": len(h5), "r7_hidden": len(h7), "intersection": len(h5 & h7),
                    "jaccard": len(h5 & h7) / len(h5 | h7), "r5_hidden_now_not_hidden": len(h5 - h7),
                    "r7_hidden_previously_not_hidden": len(h7 - h5),
                    "r2_C_now_explicitly_hidden": [r["symbol"] for r in ev["C"] if r["symbol"] in h7],
                    "r2_J_previously_explicitly_hidden_now_not": [r["symbol"] for r in ev["J"] if r["symbol"] in h5-h7]}
    targets = sorted({r["symbol"] for cl in ("C", "J") for r in ev[cl] if "skipped" not in r})
    selected = set(targets)
    target_pos = {t: i+1 for i, t in enumerate(targets)}
    target_pos["non-targeting"] = 0
    with h5py.File(a.raw, "r") as f:
        labels = column(f["obs/gene"])
        genes = column(f["var/gene_name"])
        X = f["X"]
        G = len(genes)
        rows_group = np.array([target_pos.get(t, -1) for t in labels])
        rng = np.random.default_rng(20261001)
        halves = rng.integers(0, 2, len(labels))
        sums = np.zeros((len(targets)+1, 2, G), np.float64)
        props = np.zeros_like(sums)
        ns = np.zeros((len(targets)+1, 2), np.int64)
        depth_sums = np.zeros((len(targets)+1, 2), np.float64)
        integer = True
        for start in range(0, len(labels), 569):
            end = min(start+569, len(labels))
            x = np.asarray(X[start:end], dtype=np.float32)
            integer = integer and bool(np.equal(x, np.floor(x)).all())
            lib = x.sum(1)
            grp = rows_group[start:end]; half = halves[start:end]
            for g in np.unique(grp[grp >= 0]):
                for h in (0, 1):
                    ok = (grp == g) & (half == h) & (lib > 0)
                    if ok.any():
                        sums[g, h] += x[ok].sum(0, dtype=np.float64)
                        props[g, h] += (x[ok] / lib[ok, None]).sum(0, dtype=np.float64)
                        ns[g, h] += int(ok.sum())
                        depth_sums[g, h] += float(lib[ok].sum())
        raw_meta = {"shape": list(X.shape), "all_read_values_integral": integer, "controls": int(ns[0].sum()),
                    "axis": "9624 source-native genes, no official score; no new QC or alias reconciliation"}
    pos = {g: i for i, g in enumerate(genes)}
    bulk = sums / np.maximum(sums.sum(-1, keepdims=True), 1)
    mean_prop = props / np.maximum(ns[:, :, None], 1)
    ctrl_full = props[0].sum(0) / ns[0].sum()
    ctrl_bulk = sums[0].sum(0) / sums[0].sum()
    rows = []
    for t in targets:
        i = target_pos[t]
        mp = props[i].sum(0) / ns[i].sum()
        bp = sums[i].sum(0) / sums[i].sum()
        ok = (mp > 0) & (ctrl_full > 0)
        delta = np.zeros(G); delta[ok] = np.log(mp[ok]+1e-9)-np.log(ctrl_full[ok]+1e-9)
        top = np.argsort(-abs(delta))[:200]
        own = pos.get(t, -1)
        cross = (mean_prop[i, 0] > 0) & (mean_prop[i, 1] > 0) & (mean_prop[0, 0] > 0) & (mean_prop[0, 1] > 0)
        d0 = np.log1p(50000*bulk[i, 0])-np.log1p(50000*bulk[0, 0])
        d1 = np.log1p(50000*bulk[i, 1])-np.log1p(50000*bulk[0, 1])
        trans = np.ones(G, bool)
        if own >= 0:
            trans[own] = False
        de_bulk = np.log1p(1e6*bp)-np.log1p(1e6*ctrl_bulk)
        de_cell = np.log1p(1e6*mp)-np.log1p(1e6*ctrl_full)
        rows.append({"target": t, "cells": int(ns[i].sum()), "cis_in_top200": bool(own in top),
                     "cis_lfc": float(delta[own]) if own >= 0 else None,
                     "cis_energy_share_top200": float(delta[own]**2/max(float(delta[top]@delta[top]), 1e-30)) if own >= 0 else None,
                     "split_half_bulk_cosine_trans": cosine(d0[trans], d1[trans]),
                     "bulk_cell_equal_weight_cosine": cosine(de_bulk[trans], de_cell[trans]),
                     "depth_relative_control": float(depth_sums[i].sum()/ns[i].sum() / (depth_sums[0].sum()/ns[0].sum())),
                     "defined_lfc_genes": int(ok.sum())})
    row_map = {r["target"]: r for r in rows}
    strata = {}
    for cl in ("C", "J"):
        rr = [row_map[r["symbol"]] for r in ev[cl] if r["symbol"] in row_map]
        strata[cl] = {"targets": len(rr), "median_cells": float(np.median([r["cells"] for r in rr])),
                       "median_split_half_trans_cosine": float(np.median([r["split_half_bulk_cosine_trans"] for r in rr])),
                       "mean_split_half_trans_cosine": float(np.mean([r["split_half_bulk_cosine_trans"] for r in rr])),
                       "cis_in_top200_fraction": float(np.mean([r["cis_in_top200"] for r in rr])),
                       "median_cis_top200_energy": float(np.median([r["cis_energy_share_top200"] for r in rr if r["cis_energy_share_top200"] is not None])),
                       "median_depth_relative": float(np.median([r["depth_relative_control"] for r in rr]))}
    counts = Counter(labels)
    result = {"scope": "exploratory source-native analysis, not a rerun of QC or scorer and not an independent test",
              "raw": raw_meta, "split_change": split_change, "strata": strata,
              "median_raw_cells_evaluated": float(np.median([counts[t] for t in selected])),
              "median_raw_cells_not_evaluated": float(np.median([n for t,n in counts.items() if t not in selected and t != 'non-targeting'])),
              "total_perturbation_labels": len(counts)-1,
              "largest_cis_energy": sorted(rows, key=lambda r: -(r['cis_energy_share_top200'] or 0))[:10],
              "least_agreement_bulk_equal_cell": sorted(rows, key=lambda r:r['bulk_cell_equal_weight_cosine'])[:10]}
    (a.out / "data_diagnostics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with (a.out / "hepg2_targets.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (a.out / "manifest.json").write_text(json.dumps({str(p): {"sha256": sha(p), "bytes": p.stat().st_size}
                                                   for p in (a.raw, p5, p7, ep, Path(__file__))}, indent=2), encoding="utf-8")
    print(json.dumps({"raw": raw_meta, "strata": strata, "split_change": {k: len(v) if isinstance(v,list) else v for k,v in split_change.items()},
                      "median_raw_cells_evaluated": result['median_raw_cells_evaluated'],
                      "median_raw_cells_not_evaluated": result['median_raw_cells_not_evaluated']}, indent=2))


if __name__ == "__main__":
    main()
