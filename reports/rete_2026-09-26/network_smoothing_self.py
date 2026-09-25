"""r2 of network_smoothing.py: partner means from stage 100's partner_effects (each partner's own gene left out).

Subunits of one complex give similar knockdown responses (Replogle 2022). For a target that the
sources measured, the mean K562 response of its STRING physical partners (combined score >= 700;
all K562 genome-wide targets except the target itself, from the universe cache) may add signal
the target's own noisy transfer lacks. This is the same-target setting of the submissions (C
regime), unlike reports/bersagli_nuovi_2026-09-26 (targets no source measured).

Held-out sources CD4, HCT116 and HEK293T only: when K562 itself is held out, K562 partners would
bring its own context in. Predictors: the other families, as sweep_v2.pooled. Arms, t19 shape
(shrunk x 1.576) plus the t20 cis head (2 x median prior within 5 kb):
  t20like              transferred + cis;
  t20like+net<lam>     + lam x partners' mean K562 effect (centred over K562 targets), lam 0.05-0.4;
  t20like+netshuf<lam> control: another target's partner mean (fixed derangement).
PDS proxy (analyze.pds_proxy), paired bootstrap over targets. Proxies, not VCC scores.

    scripts/py.cmd reports/rete_2026-09-26/network_smoothing.py \
        --universe C:/Users/ferra/vcc2026-data/processed/universe_k562_2026-09-26 --out reports/rete_2026-09-26/r2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "reports" / "modulo_cis_2026-09-26"))

from cis_bench import DATA, FAMILY, SEED, boot, pds_proxy, pooled, stage100  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402

HELD = ["cd4_mix", "orion_hct116", "orion_hek293t"]
SOURCES = ["k562", "cd4_mix", "orion_hct116", "orion_hek293t"]
LAMBDAS = (0.05, 0.1, 0.2, 0.4)


def partner_means(folder: Path, panel: list[str], links: pd.DataFrame, gene_cols: np.ndarray, n_genes: int):
    """Mean K562 effect (centred over all K562 targets) of each panel target's partners, target excluded."""
    idx = pd.read_csv(folder / "index.csv")
    uni = set(idx["target"].astype(str))
    groups = (links[links["a"].isin(set(panel)) & links["b"].isin(uni) & (links["a"] != links["b"])]
              .groupby("a")["b"].apply(lambda v: sorted(set(v))))
    need = sorted({p for t in groups.index for p in groups[t]})
    rows, total, count = {}, np.zeros(gene_cols.size), 0
    for chunk in sorted(idx["chunk"].unique()):
        z = np.load(folder / chunk, allow_pickle=False)
        t = z["targets"].astype(str)
        sh = np.nan_to_num(z["shrunk"][:, gene_cols]).astype(np.float32)
        total += sh.sum(axis=0)
        count += sh.shape[0]
        for i, name in enumerate(t):
            if name in need:
                rows[name] = sh[i]
        del z, sh
    mean_all = (total / max(count, 1)).astype(np.float32)
    out = np.zeros((len(panel), n_genes), dtype=np.float32)
    n_with = 0
    for i, t in enumerate(panel):
        if t in groups.index:
            vals = [rows[p] for p in groups[t] if p in rows]
            if vals:
                out[i, gene_cols] = np.mean(vals, axis=0) - mean_all
                n_with += 1
    return out, n_with


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", type=Path, required=True)
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "interim/basal_cpm_by_context.csv")
    ap.add_argument("--genes", type=Path, default=DATA / "raw/controls/gene_names.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--pairs", type=Path, default=REPO / "reports/cis_2026-09-17/k562_neighbour_pairs.csv")
    ap.add_argument("--string-links", type=Path, default=DATA / "interim/encoder_inputs_2026-09-14/string_physical_links")
    ap.add_argument("--string-info", type=Path, default=DATA / "interim/encoder_inputs_2026-09-14/string_protein_info")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = pd.read_csv(args.genes)["gene_name"].astype(str).to_numpy()
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    col = {g: i for i, g in enumerate(axis)}
    panel_cols = np.array([col[g] for g in panel if g in col])
    cpm = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)[["A", "B", "C"]].mean(axis=1).to_numpy()
    x = 0.05 * cpm
    w = (x / (1.0 + x)).astype(np.float32)

    # r2: stage 100's partner_effects, which leaves each partner's own gene out of the mean
    assoc, counts = stage100.partner_effects(panel, args.universe, args.string_links, args.string_info, 700, axis)
    net = np.stack([assoc.get(t, np.zeros(axis.size, dtype=np.float32)) for t in panel])
    n_with = counts["targets_with_partners"]
    prow = {t: i for i, t in enumerate(panel)}
    print(f"panel targets with a scored partner: {n_with}", flush=True)
    cis_model = stage100.cis_prior(pd.read_csv(args.pairs), panel)
    coords = load_coordinates(args.coords)

    rows = []
    rng = np.random.default_rng(SEED)
    for held in HELD:
        preds = [s for s in SOURCES if FAMILY[s] != FAMILY[held]]
        truth = stage100.load_table(args.cache, held, "raw")
        tidx = truth.index()
        base_t = [t for t in panel if t in tidx]
        eff, den = pooled(args.cache, preds, base_t, "shrunk")
        ok = np.abs(eff).sum(axis=1) > 0
        targets = [t for t, o in zip(base_t, ok) if o]
        E = (eff[ok] * 1.576).astype(np.float32)
        obs = den[ok] > 0
        stage100.add_cis(E, obs, targets, axis, cis_model, coords, 5000, 2.0)
        T = truth.raw[np.array([tidx[t] for t in targets])].astype(np.float32)
        N = net[np.array([prow[t] for t in targets])]
        order = np.arange(len(targets))
        perm = order.copy()
        for _ in range(100):
            rng.shuffle(perm)
            if not np.any(perm == order):
                break
        ref = pds_proxy(E, T, w, panel_cols)
        rows.append({"held_out": held, "arm": "t20like", "targets": len(targets), "pds_proxy": float(ref.mean()),
                     "minus_t20like": 0.0, "ci95": [0.0, 0.0]})
        for lam in LAMBDAS:
            for name, M in ((f"net{lam}", N), (f"netshuf{lam}", N[perm])):
                v = pds_proxy(E + lam * M, T, w, panel_cols)
                d, ci = boot(v - ref, rng)
                rows.append({"held_out": held, "arm": f"t20like+{name}", "targets": len(targets),
                             "pds_proxy": float(v.mean()), "minus_t20like": d, "ci95": ci})
        print(held, "done", flush=True)
    s = pd.DataFrame(rows)
    s.to_csv(args.out / "summary.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "rete_2026-09-26/network_smoothing_self.py", "claim_type": "effect-space proxies; not VCC scores",
                   "panel_targets_with_partner": n_with, "rows": rows}, f, indent=1)
    pd.set_option("display.width", 200)
    print(s.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
