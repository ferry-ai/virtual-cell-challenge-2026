"""Stage 77: how strongly CRISPRi represses genes near its target, and whether that transfers.

Two measurements, both from files already on the laptop:

1. **Distance curve (K562).** For every K562 genome-wide target with GENCODE
   coordinates, the log2 ratio of each expressed gene's mean fraction in the
   target's cells to its mean fraction in the non-targeting cells, binned by the
   distance between the two TSSs (`K562_gwps_raw_bulk_01.h5ad`, per-cell means).
2. **Transfer (K562 -> HepG2).** For targets perturbed in both screens, the same
   quantity for neighbours within 5 kb, computed in HepG2 from single cells
   (`NadigOConner2024_hepg2.h5ad`, read in blocks) and compared with K562.

The panel section counts, per official context, the targets with a neighbour
expressed at >= 10 CPM in the context's controls (`interim/basal_cpm_by_context.csv`).

This is a measurement of an effect and of its agreement across two contexts. It is
not a score, and HepG2 targets are essential-screen genes.

    python scripts/77_cis_effect_report.py --out reports/cis_2026-09-17
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.manifest import file_fingerprint  # noqa: E402
from vcc2026.predictor_sc import bulk_symbols, load_coordinates  # noqa: E402
from vcc2026.sc_stream import read_frame  # noqa: E402

EDGES = [0, 500, 1000, 2000, 5000, 10000, 20000, 50000]
PSEUDO = 1e-7


def near_pairs(targets, coords, max_dist):
    by_chrom = {c: s for c, s in coords.groupby("chrom")}
    for t in targets:
        if t not in coords.index:
            continue
        c, tss = coords.at[t, "chrom"], int(coords.at[t, "tss"])
        sub = by_chrom[c]
        d = (sub["tss"] - tss).abs()
        near = sub[(d <= max_dist) & (sub.index != t)]
        for g, dist in zip(near.index, (near["tss"] - tss).abs()):
            yield t, g, int(dist)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--coords", type=Path, default=None)
    p.add_argument("--k562-bulk", type=Path, default=None)
    p.add_argument("--hepg2", type=Path, default=None)
    args = p.parse_args()
    if (args.out / "cis_effect.json").exists():
        raise SystemExit(f"{args.out} already holds a report")
    args.out.mkdir(parents=True, exist_ok=True)
    paths = config.paths()
    coords_path = args.coords or paths.external / "annotation" / "gene_coordinates_gencode_v50.tsv"
    bulk_path = args.k562_bulk or paths.external / "K562_gwps_raw_bulk_01.h5ad"
    hepg2_path = args.hepg2 or paths.raw / "nadig_hepg2" / "NadigOConner2024_hepg2.h5ad"
    coords = load_coordinates(coords_path)

    with h5py.File(bulk_path, "r") as f:
        kfrac = f["X"][:]  # float32, normalized in place below (the laptop has ~1 GB free)
        klab = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
        kgenes = read_frame(f["var"])["gene_name"].astype(str).to_numpy()
    kfrac /= kfrac.sum(axis=1, keepdims=True)
    kntc, ksym = bulk_symbols(klab)
    kctrl = kfrac[kntc].mean(axis=0, dtype=np.float64)
    kpos = {g: i for i, g in enumerate(kgenes)}
    rows_by_sym = pd.Series(np.arange(ksym.size)).groupby(ksym).apply(list).to_dict()

    def k562_lfc(t, g):
        j = kpos[g]
        return float(np.mean([np.log2((float(kfrac[r, j]) + PSEUDO) / (kctrl[j] + PSEUDO)) for r in rows_by_sym[t]]))

    # 1. distance curve
    curve_rows = []
    for t, g, dist in near_pairs(sorted(set(ksym[~kntc])), coords, EDGES[-1]):
        if g in kpos and kctrl[kpos[g]] >= 2e-5:
            curve_rows.append((t, g, dist, k562_lfc(t, g)))
    curve = pd.DataFrame(curve_rows, columns=["target", "gene", "dist", "log2fc"])
    curve.to_csv(args.out / "k562_neighbour_pairs.csv", index=False)
    curve["bin"] = pd.cut(curve["dist"], EDGES, right=False)
    table = curve.groupby("bin", observed=True)["log2fc"].agg(
        n="count", median="median", mean="mean", frac_below_minus_half=lambda s: float((s < -0.5).mean()))
    table.to_csv(args.out / "k562_distance_curve.csv")

    # 2. transfer to HepG2
    with h5py.File(hepg2_path, "r") as f:
        hobs = read_frame(f["obs"])
        hgenes = read_frame(f["var"]).index.astype(str).to_numpy()
    hpos = {g: i for i, g in enumerate(hgenes)}
    hsym = hobs["gene"].astype(str).to_numpy()
    shared = sorted((set(hsym) - {"non-targeting"}) & set(ksym[~kntc]))
    pairs = [(t, g, d) for t, g, d in near_pairs(shared, coords, 5000)
             if g in hpos and g in kpos and kctrl[kpos[g]] >= 2e-5]
    targets = sorted({t for t, _, _ in pairs})
    cols = sorted({hpos[g] for _, g, _ in pairs})
    colidx = {c: i for i, c in enumerate(cols)}
    want = {t: i for i, t in enumerate(targets)}
    code = np.array([want.get(s, -1) for s in hsym])
    is_ntc = hsym == "non-targeting"
    acc = np.zeros((len(targets), len(cols)))
    n_t = np.zeros(len(targets))
    ctrl_acc = np.zeros(len(cols))
    n_c = 0
    rows = np.flatnonzero((code >= 0) | is_ntc)
    with h5py.File(hepg2_path, "r") as f:
        x = f["X"]
        for i in range(0, rows.size, 1000):
            r = rows[i:i + 1000]
            blk = x[r].astype(np.float64)
            frac = blk[:, cols] / blk.sum(axis=1, keepdims=True)
            m = code[r] >= 0
            np.add.at(acc, code[r][m], frac[m])
            np.add.at(n_t, code[r][m], 1)
            ctrl_acc += frac[is_ntc[r]].sum(axis=0)
            n_c += int(is_ntc[r].sum())
    hctrl = ctrl_acc / n_c
    trans_rows = []
    for t, g, dist in pairs:
        ci = colidx[hpos[g]]
        if hctrl[ci] < 2e-5:
            continue
        h = float(np.log2((acc[want[t], ci] / n_t[want[t]] + PSEUDO) / (hctrl[ci] + PSEUDO)))
        trans_rows.append((t, g, dist, k562_lfc(t, g), h, int(n_t[want[t]])))
    trans = pd.DataFrame(trans_rows, columns=["target", "gene", "dist", "k562_log2fc", "hepg2_log2fc", "hepg2_cells"])
    trans.to_csv(args.out / "k562_hepg2_neighbours.csv", index=False)
    summary = {}
    for name, sub in (("le_1kb", trans[trans.dist <= 1000]), ("1_5kb", trans[(trans.dist > 1000) & (trans.dist <= 5000)])):
        strong = sub.k562_log2fc.abs() > 0.5
        summary[name] = {
            "n_pairs": int(len(sub)),
            "median_k562": float(sub.k562_log2fc.median()),
            "median_hepg2": float(sub.hepg2_log2fc.median()),
            "pearson": float(np.corrcoef(sub.k562_log2fc, sub.hepg2_log2fc)[0, 1]),
            "sign_agreement_k562_abs_gt_0.5": float((np.sign(sub.k562_log2fc) == np.sign(sub.hepg2_log2fc))[strong].mean()),
            "n_k562_abs_gt_0.5": int(strong.sum()),
        }

    # 3. panel exposure
    panel = pd.read_csv(paths.raw / "controls" / "pert_counts.csv")["target_gene"].astype(str).tolist()
    cpm = pd.read_csv(paths.interim / "basal_cpm_by_context.csv", index_col=0)
    expo = {}
    panel_pairs = pd.DataFrame(list(near_pairs(panel, coords, 5000)), columns=["target", "gene", "dist"])
    panel_pairs = panel_pairs[~panel_pairs.gene.isin(panel)]
    for ctx in ("A", "B", "C"):
        e = panel_pairs[panel_pairs.gene.map(lambda g: cpm[ctx].get(g, 0.0)) >= 10]
        expo[ctx] = {"targets_neighbour_le_1kb": int(e[e.dist <= 1000].target.nunique()),
                     "targets_neighbour_le_5kb": int(e.target.nunique()),
                     "neighbours_not_measured_in_k562": int((~e.gene.isin(kpos)).sum())}

    payload = {
        "stage": "77_cis_effect_report",
        "written_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {k: file_fingerprint(v) for k, v in
                   (("coords", coords_path), ("k562_bulk", bulk_path), ("hepg2", hepg2_path))},
        "k562_distance_curve_log2": {str(k): v for k, v in table.to_dict(orient="index").items()},
        "k562_to_hepg2": summary,
        "panel_exposure_cpm10": expo,
        "claim_type": "measurement (K562 pseudobulk means; HepG2 single cells), not a score",
        "caveats": [
            "K562 side uses the published per-cell-mean pseudobulk, pooled over guides/transcripts per symbol",
            "HepG2 targets are essential-screen genes; the panel's are not",
            "TSS is gene-level (GENCODE v50 basic), not transcript-level",
        ],
    }
    (args.out / "cis_effect.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(table.round(3).to_string())
    print(json.dumps(summary, indent=1))
    print(json.dumps(expo, indent=1))


if __name__ == "__main__":
    main()
