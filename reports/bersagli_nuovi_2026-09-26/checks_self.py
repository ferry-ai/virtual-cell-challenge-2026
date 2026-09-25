"""r4: the STRING arms of r1-r3 again, with each partner's own gene left out of the partner mean.

r1-r3 averaged the partners' full K562 rows, so the association vector of a target carried every
partner's knockdown of itself, a strong negative value at the partner's own gene that is not a
response to the target. Production (`partner_effects` of stage 100) now leaves those genes out;
this rerun uses that very function, with every panel target excluded from partners and from the
centre (no outcome of the targets treated as new). No common response in any arm, as r3.

    scripts/py.cmd reports/bersagli_nuovi_2026-09-26/checks_self.py --out reports/bersagli_nuovi_2026-09-26/r4
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from linear_new_targets import DATA, REPO, SEED, boot, pds_proxy, stage100  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402

LAMBDAS = (0.1, 0.25, 0.5, 1.0, 2.0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", type=Path, default=DATA / "processed/universe_k562_2026-09-26")
    ap.add_argument("--cache", type=Path, default=DATA / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--basal", type=Path, default=DATA / "interim/basal_cpm_by_context.csv")
    ap.add_argument("--genes", type=Path, default=DATA / "raw/controls/gene_names.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--pairs", type=Path, default=REPO / "reports/cis_2026-09-17/k562_neighbour_pairs.csv")
    ap.add_argument("--links", type=Path, default=DATA / "interim/encoder_inputs_2026-09-14/string_physical_links")
    ap.add_argument("--info", type=Path, default=DATA / "interim/encoder_inputs_2026-09-14/string_protein_info")
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

    assoc, counts = stage100.partner_effects(panel, args.universe, args.links, args.info, 700, axis,
                                             exclude=frozenset(panel))
    print(counts, flush=True)
    cis_model = stage100.cis_prior(pd.read_csv(args.pairs), panel)
    coords = load_coordinates(args.coords)
    rows = []
    rng = np.random.default_rng(SEED)
    for held in ("k562", "cd4_mix", "orion_hct116", "orion_hek293t"):
        tab = stage100.load_table(args.cache, held, "raw")
        tidx = tab.index()
        targets = [t for t in panel if t in tidx]
        T = tab.raw[np.array([tidx[t] for t in targets])].astype(np.float32)
        cis = np.zeros((len(targets), axis.size), dtype=np.float32)
        stage100.add_cis(cis, np.zeros_like(cis, dtype=bool), targets, axis, cis_model, coords, 5000, 2.0)
        S = np.stack([assoc.get(t, np.zeros(axis.size, dtype=np.float32)) for t in targets])
        ref = pds_proxy(cis, T, w, panel_cols)
        rows.append({"held_out": held, "arm": "cis", "targets": len(targets), "pds_proxy": float(ref.mean()),
                     "minus_cis": 0.0, "ci95": [0.0, 0.0]})
        v = pds_proxy(S, T, w, panel_cols)
        rows.append({"held_out": held, "arm": "string700", "targets": len(targets), "pds_proxy": float(v.mean()),
                     "minus_cis": float((v - ref).mean()), "ci95": None})
        for lam in LAMBDAS:
            v = pds_proxy(lam * S + cis, T, w, panel_cols)
            d, ci = boot(v - ref, rng)
            rows.append({"held_out": held, "arm": f"{lam}*string700+cis", "targets": len(targets),
                         "pds_proxy": float(v.mean()), "minus_cis": d, "ci95": ci})
        print(held, "done", flush=True)
    s = pd.DataFrame(rows)
    s.to_csv(args.out / "string_lambda.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "bersagli_nuovi_2026-09-26/checks_self.py", "claim_type": "effect-space proxies; not VCC scores",
                   "partner_counts": counts, "rows": rows}, f, indent=1)
    pd.set_option("display.width", 200)
    print(s.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
