"""Reproduce exploratory context and donor findings; never overwrite outputs.

Run with scripts/py.cmd -B and --out pointing to a new directory.
This records post-hoc analyses, not a preregistered test or a VCC score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from vcc2026.config import paths
from vcc2026.genes import official_axis

REPO = Path(__file__).resolve().parents[2]
CONTEXTS = ["A549", "BXPC3", "HAP1", "HT29", "K562", "MCF7"]
COLS = ["log2FC_" + c for c in CONTEXTS]


def fingerprint(path):
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest}


def correlation(a, b):
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def panel_analysis(path, out):
    data = pd.read_csv(path)
    if data.duplicated(["target", "pathway", "held_out"]).any():
        raise ValueError("Duplicate target/stimulus/context rows")
    data["dr"] = data.pearson - data.blind_pearson
    pairs = data[["target", "pathway"]].drop_duplicates()
    counts = pairs.groupby("target").size().value_counts().sort_index()
    cross = data.pivot(index=["target", "held_out"], columns="pathway", values="dr")
    cross = cross[["IFNB", "IFNG"]].dropna()
    difference = cross.IFNB - cross.IFNG
    crossover = difference.groupby("target").agg(["mean", "min", "max"])
    crossover.to_csv(out / "stimulus_crossover.csv")
    tnfa = data[data.pathway == "TNFA"].pivot(index="target", columns="held_out", values="dr")
    gap = tnfa.MCF7 - tnfa.drop(columns="MCF7").mean(axis=1)
    pd.DataFrame({"dr_mcf7": tnfa.MCF7, "other_mean": tnfa.drop(columns="MCF7").mean(axis=1),
                  "gap": gap}).to_csv(out / "tnfa_mcf7.csv")
    return {"rows": len(data), "targets": pairs.target.nunique(), "target_stimulus_pairs": len(pairs),
            "stimuli_per_target_counts": counts.to_dict(),
            "ifnb_minus_ifng_mean_dr": float(difference.mean()),
            "ifnb_minus_ifng_without_stat2": float(difference.drop(index="STAT2", level="target").mean()),
            "shared_ifnb_ifng_targets": len(crossover),
            "tnfa_mcf7_gap_mean": float(gap.mean()),
            "tnfa_mcf7_gap_without_three": float(gap.drop(["FADD", "TRAF3", "TRAF2"]).mean()),
            "tnfa_negative_gaps": int((gap < 0).sum()), "tnfa_targets": len(gap)}


def raw_mixscale(archive, out):
    selected = {"STAT2", "STAT1", "JAK1", "USP18", "IFNAR1", "IFNAR2", "TYK2",
                "TRAF3", "TRAF2", "FADD", "TNFRSF1A", "IKBKB", "IKBKG", "NFKB1", "CHUK"}
    frames, excluded = {}, set()
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            match = re.fullmatch(r"(.+)_(IFNB|IFNG|INS|TGFB1|TNFA)_pathway_DE_results.txt", Path(name).name)
            if not match or name.startswith("__MACOSX/"):
                continue
            target, stimulus = match.groups()
            excluded.add(target)
            if target not in selected or stimulus not in {"IFNB", "IFNG", "TNFA"}:
                continue
            with z.open(name) as handle:
                frame = pd.read_csv(handle, sep=r"\s+").set_index("gene_ID")[COLS]
            if not frame.index.is_unique:
                raise ValueError(f"Duplicate genes in {name}")
            frames[target, stimulus] = frame
    matched = []
    for target in ["STAT2", "STAT1", "JAK1"]:
        a, b = frames[target, "IFNB"], frames[target, "IFNG"]
        genes = sorted((set(a.dropna().index) & set(b.dropna().index)) - excluded)
        for stimulus, frame in [("IFNB", a), ("IFNG", b)]:
            array = frame.loc[genes].to_numpy(float)
            for j, context in enumerate(CONTEXTS):
                truth, prediction = array[:, j], np.delete(array, j, axis=1).mean(axis=1)
                matched.append({"target": target, "stimulus": stimulus, "context": context,
                                "genes": len(genes), "pearson": correlation(truth, prediction),
                                "self_log2fc": float(frame.loc[target, COLS[j]]),
                                "response_rms": float(np.sqrt(np.mean(truth ** 2)))})
    pd.DataFrame(matched).to_csv(out / "matched_stimuli.csv", index=False)
    geometry = []
    a = frames["STAT2", "IFNB"]
    for target in ["STAT1", "JAK1", "IFNAR1", "IFNAR2", "TYK2", "USP18"]:
        b = frames[target, "IFNB"]
        genes = sorted((set(a.dropna().index) & set(b.dropna().index)) - excluded)
        for col, context in zip(COLS, CONTEXTS):
            geometry.append({"target": target, "context": context, "genes": len(genes),
                             "pearson_vs_stat2": correlation(a.loc[genes, col], b.loc[genes, col])})
    pd.DataFrame(geometry).to_csv(out / "signed_geometry.csv", index=False)
    tnfa = []
    for (target, stimulus), frame in frames.items():
        if stimulus != "TNFA":
            continue
        genes = sorted(set(frame.dropna().index) - excluded)
        array = frame.loc[genes].to_numpy(float)
        for j, context in enumerate(CONTEXTS):
            tnfa.append({"target": target, "context": context, "genes": len(genes),
                         "pearson": correlation(array[:, j], np.delete(array, j, axis=1).mean(axis=1)),
                         "self_log2fc": float(frame.loc[target, COLS[j]]) if target in frame.index else np.nan})
    pd.DataFrame(tnfa).to_csv(out / "tnfa_raw.csv", index=False)
    return {"excluded_targets": len(excluded), "response_axis": "all measured genes, not restricted to official axis",
            "matched_stat2_genes": next(row["genes"] for row in matched if row["target"] == "STAT2"),
            "signed_medians": pd.DataFrame(geometry).groupby("target").pearson_vs_stat2.median().to_dict()}


def cd4_analysis(cache, axis, panel, out):
    names = ["Rest", "Stim8hr", "Stim48hr", "halfA", "halfB"]
    tables = {}
    for name in names:
        with np.load(cache / f"cd4_{name}.npz", allow_pickle=False) as z:
            tables[name] = {k: z[k] for k in ["targets", "raw", "se", "shrunk", "n_cells"]}
    targets = sorted(set.intersection(*(set(t["targets"]) for t in tables.values())))
    aligned = {}
    keep = ~np.isin(axis, panel)
    for name, table in tables.items():
        if table["raw"].shape[1] != len(axis):
            raise ValueError("CD4 response axis mismatch")
        index = {t: i for i, t in enumerate(table["targets"])}
        rows = [index[t] for t in targets]
        aligned[name] = {k: table[k][rows][:, keep] for k in ["raw", "se", "shrunk"]}
    finite = np.logical_and.reduce([np.isfinite(t["raw"]) for t in aligned.values()])
    summaries, records = [], []
    for left, right in [("Rest", "Stim8hr"), ("Rest", "Stim48hr"),
                        ("Stim8hr", "Stim48hr"), ("halfA", "halfB")]:
        for i, target in enumerate(targets):
            mask = finite[i]
            a, b = aligned[left], aligned[right]
            x, y = a["raw"][i, mask], b["raw"][i, mask]
            sx, sy = a["se"][i, mask], b["se"][i, mask]
            sure = (np.abs(x) >= 2 * sx) & (np.abs(y) >= 2 * sy) & (sx > 0) & (sy > 0)
            records.append({"left": left, "right": right, "target": target, "genes": int(mask.sum()),
                            "pearson": correlation(x, y), "both_z2": int(sure.sum()),
                            "opposing_z2": int(((x * y < 0) & sure).sum())})
        selected_rows = [r for r in records if r["left"] == left and r["right"] == right]
        both = sum(r["both_z2"] for r in selected_rows)
        opposite = sum(r["opposing_z2"] for r in selected_rows)
        summaries.append({"left": left, "right": right, "targets": len(targets),
                          "median_pearson": float(np.nanmedian([r["pearson"] for r in selected_rows])),
                          "both_z2": both, "opposing_z2": opposite,
                          "pooled_opposing_fraction": opposite / both if both else None})
    pd.DataFrame(records).to_csv(out / "cd4_per_target.csv", index=False)
    # Separate sensitivity: pair-only support, not the all-five-source support above.
    a, b = aligned["halfA"], aligned["halfB"]
    rows = []
    for i, target in enumerate(targets):
        mask = np.isfinite(a["raw"][i]) & np.isfinite(b["raw"][i])
        rows.append({"target": target, "genes": int(mask.sum()),
                     **{k: correlation(a[k][i, mask], b[k][i, mask]) for k in ["raw", "shrunk"]}})
    df = pd.DataFrame(rows)
    df.to_csv(out / "cd4_shrink_pair_support.csv", index=False)
    return {"matched_targets": len(targets), "median_common_response_genes": float(np.median(finite.sum(axis=1))),
            "comparisons": summaries, "pair_support_shrink": {"raw_median": float(df.raw.median()),
            "shrunk_median": float(df.shrunk.median()), "median_paired_gain": float((df.shrunk - df.raw).median())}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=paths().data_root)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    root = args.data_root
    archive = root / "external/mixscale_zenodo14518762/DE_results_all_pathway.zip"
    cache = root / "processed/multisource_2026-09-23_r5"
    prior = REPO / "reports/dld1_audit_2026-09-24/mixscale_r1/per_target_context.csv"
    axis_path, panel_path = root / "raw/controls/gene_names.csv", root / "raw/controls/pert_counts.csv"
    inputs = [archive, prior, axis_path, panel_path, Path(__file__),
              *[cache / f"cd4_{n}.npz" for n in ["Rest", "Stim8hr", "Stim48hr", "halfA", "halfB"]]]
    provenance = [fingerprint(p) for p in inputs]
    panel = pd.read_csv(panel_path).iloc[:, 0].astype(str).to_numpy()
    result = {"written_utc": datetime.now(timezone.utc).isoformat(),
              "claim_type": "post-hoc exploratory reanalysis; no training, no independent J test, no VCC score",
              "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
              "inputs": provenance,
              "panel": panel_analysis(prior, args.out),
              "mixscale_raw": raw_mixscale(archive, args.out),
              "cd4": cd4_analysis(cache, np.array(official_axis(axis_path).symbols), panel, args.out)}
    with (args.out / "measurements.json").open("x", encoding="utf-8") as handle:
        json.dump(clean(result), handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps(clean({k: v for k, v in result.items() if k not in {"inputs", "environment"}}), indent=2))


if __name__ == "__main__":
    main()
