"""Turn the network's predictions for A, B, C into stage-45 effect files: the network's direction at t25's amplitude.

The network (train.py, --predict-contexts A,B,C) writes `pred_<context>.npz` with `targets`, `net`, `blind`,
`transfer` on the official axis (NaN where it does not predict). Trained on raw effects of random genome-wide
targets, its calibrated amplitude is tiny (A about 0.006 on 27/09), so its scale is not a submission scale. This
keeps everything of a reference submission (t25's effects: `effects_<context>.npz` with `targets`, `genes`, `lfc`,
`observed`) except the direction on the genes the network models:
* G_t = genes where the network's prediction is finite, the reference marks the gene observed, and the gene is
  neither the target itself nor within --cis-bp of its TSS (the reference's knockdown and cis head stay);
* on G_t the reference row is replaced by the network's row scaled to the reference row's norm on G_t, so each
  target keeps the reference's energy there; a target the network lacks, or with a zero row, keeps the reference.
The observed masks are the reference's. Per context and target it reports the cosine between the network and the
reference on G_t, and the same for the network's blind arm: how different the submission is, measured before any
score. Writes NEW `effects_<context>.npz` in the reference's format, plus `conversion.json`.

    scripts/py.cmd reports/modelli/rete_contesti_2026-09-27/to_effects.py --run <folder with pred_A.npz ...> \
        --reference C:/Users/ferra/vcc2026-data/processed/effects_t25_2026-09-27 --out <new folder>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = Path("C:/Users/ferra/vcc2026-data")


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na > 0 and nb > 0 else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--cis-bp", type=int, default=5000)
    ap.add_argument("--contexts", default="A,B,C")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    coords = pd.read_csv(args.coords, sep="\t").drop_duplicates("symbol").set_index("symbol")
    report = {"stage": "rete_contesti_2026-09-27/to_effects.py", "run": str(args.run),
              "reference": str(args.reference), "cis_bp": args.cis_bp, "contexts": {}}
    for c in [s.strip() for s in args.contexts.split(",") if s.strip()]:
        ref = np.load(args.reference / f"effects_{c}.npz", allow_pickle=False)
        pred = np.load(args.run / f"pred_{c}.npz", allow_pickle=False)
        genes = ref["genes"].astype(str)
        rtargets = ref["targets"].astype(str)
        lfc = ref["lfc"].astype(np.float32).copy()
        observed = ref["observed"].astype(bool)
        if pred["net"].shape[1] != genes.size:
            raise SystemExit(f"{c}: prediction axis {pred['net'].shape[1]} != reference axis {genes.size}")
        prow = {t: i for i, t in enumerate(pred["targets"].astype(str))}
        col = {g: i for i, g in enumerate(genes)}
        chrom = coords.reindex(genes)["chrom"].astype(str).to_numpy()
        tss = coords.reindex(genes)["tss"].to_numpy(dtype=float)
        cos_net, cos_blind, replaced, kept = [], [], 0, []
        for i, t in enumerate(rtargets):
            if t not in prow:
                kept.append(t)
                continue
            net = pred["net"][prow[t]].astype(np.float64)
            blind = pred["blind"][prow[t]].astype(np.float64)
            window = np.zeros(genes.size, dtype=bool)
            if t in col:
                window[col[t]] = True
            if t in coords.index:
                window |= (chrom == str(coords.at[t, "chrom"])) & (np.abs(tss - float(coords.at[t, "tss"])) <= args.cis_bp)
            g = np.isfinite(net) & observed[i] & ~window & np.isfinite(lfc[i])
            r = lfc[i, g].astype(np.float64)
            n = net[g]
            nn = np.linalg.norm(n)
            if not g.any() or nn == 0:
                kept.append(t)
                continue
            cos_net.append(cosine(n, r))
            cos_blind.append(cosine(blind[g], r) if np.isfinite(blind[g]).all() else float("nan"))
            lfc[i, g] = (n * (np.linalg.norm(r) / nn)).astype(np.float32)
            replaced += 1
        np.savez_compressed(args.out / f"effects_{c}.npz", targets=rtargets, genes=genes, lfc=lfc, observed=observed)
        cn, cb = np.asarray(cos_net), np.asarray(cos_blind)
        report["contexts"][c] = {
            "targets": int(rtargets.size), "replaced": replaced, "kept_reference": kept,
            "cosine_net_vs_reference": {"median": float(np.nanmedian(cn)), "q10": float(np.nanquantile(cn, 0.1)),
                                        "q90": float(np.nanquantile(cn, 0.9))},
            "cosine_blind_vs_reference_median": float(np.nanmedian(cb)),
            "network_meta": json.loads(str(pred["meta"])) if "meta" in pred.files else None}
        print(f"{c}: {replaced} of {rtargets.size} targets replaced; cosine net vs reference median "
              f"{np.nanmedian(cn):.3f} (q10 {np.nanquantile(cn, 0.1):.3f}, q90 {np.nanquantile(cn, 0.9):.3f}); "
              f"blind vs reference median {np.nanmedian(cb):.3f}", flush=True)
    with (args.out / "conversion.json").open("x", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)


if __name__ == "__main__":
    main()
