r"""Check how much of the official challenge panel the Replogle data actually covers.

Two independent coverage questions decide whether a transfer model is even
possible, and they are easy to conflate:

1. **Perturbation coverage** -- of the 300 genes the challenge asks us to knock
   down, how many were knocked down in K562 and in RPE1? A target perturbed in
   neither line has no measured response to transfer from.
2. **Gene-space coverage** -- the challenge scores all 18,533 genes, but the
   published pseudobulk carries only ~8,000. Genes outside that space get no
   signal from this dataset and need either another source or a fallback.

Also reports the shared panel: targets measured in *both* lines, which is what
a leave-one-line-out harness can validate in both directions.

Usage:  .\scripts\py.cmd scripts\11_check_target_coverage.py
"""

from __future__ import annotations

import json
import re

import anndata as ad
import numpy as np
import pandas as pd

from vcc2026.config import paths

# obs index looks like "10005_ZBTB4_P1_ENSG00000174282":
# <numeric id>_<gene symbol>_<promoter>_<ensembl id>
_PERT = re.compile(
    r"^\d+_(?P<symbol>.+?)_(?P<promoter>P[0-9P]*|ENST[^_]+)_(?P<ensembl>ENSG\d+|nan)$"
)

SOURCES = {
    "K562 genome-wide": "K562_gwps_raw_bulk_01.h5ad",
    "K562 essential": "K562_essential_raw_bulk_01.h5ad",
    "RPE1": "rpe1_raw_bulk_01.h5ad",
}


def parse_perturbations(index: pd.Index) -> pd.DataFrame:
    """Split the composite obs index into symbol / promoter / ensembl columns."""
    rows = []
    unparsed = []
    for raw in index:
        m = _PERT.match(str(raw))
        if m:
            rows.append((str(raw), m["symbol"], m["promoter"], m["ensembl"]))
        else:
            unparsed.append(str(raw))
    df = pd.DataFrame(rows, columns=["raw", "symbol", "promoter", "ensembl"])
    return df, unparsed


def main() -> None:
    p = paths()
    bundle = p.raw / "controls"

    challenge_genes = pd.read_csv(bundle / "gene_names.csv")["gene_name"].to_numpy()
    targets = pd.read_csv(bundle / "pert_counts.csv")["target_gene"].to_numpy()
    target_set = set(targets)
    gene_set = set(challenge_genes)

    print(f"challenge panel : {len(targets)} perturbations")
    print(f"challenge genes : {len(challenge_genes):,}")
    print()

    covered: dict[str, set[str]] = {}       # challenge targets each source hits
    all_symbols: dict[str, set[str]] = {}   # every perturbation each source has
    report: dict[str, dict] = {}

    for label, fname in SOURCES.items():
        a = ad.read_h5ad(p.external / fname)
        perts, unparsed = parse_perturbations(a.obs_names)

        symbols = set(perts["symbol"])
        hit = target_set & symbols
        covered[label] = hit
        all_symbols[label] = symbols

        src_genes = set(a.var["gene_name"].astype(str))
        gene_overlap = gene_set & src_genes

        # Is X counts, log, or z-scored? The answer decides all downstream math.
        X = np.asarray(a.X)
        sample = X[: min(500, X.shape[0])]

        print(f"--- {label} ---")
        print(f"  matrix                  : {a.shape[0]:,} perturbations x {a.shape[1]:,} genes")
        print(f"  unique perturbed symbols: {len(symbols):,}"
              + (f"   ({len(unparsed)} unparsed)" if unparsed else ""))
        print(f"  promoters used          : {sorted(perts['promoter'].unique())[:6]}")
        print(f"  CHALLENGE TARGETS HIT   : {len(hit)}/{len(targets)}  ({len(hit)/len(targets):.1%})")
        print(f"  challenge genes present : {len(gene_overlap):,}/{len(challenge_genes):,}"
              f"  ({len(gene_overlap)/len(challenge_genes):.1%})")
        print(f"  X range                 : [{sample.min():.3f}, {sample.max():.3f}]  "
              f"mean {sample.mean():.3f}  median {np.median(sample):.3f}")
        print()

        report[label] = {
            "n_perturbations": int(a.shape[0]),
            "n_genes": int(a.shape[1]),
            "unique_symbols": len(symbols),
            "targets_hit": len(hit),
            "challenge_genes_present": len(gene_overlap),
        }
        del a, X

    # --- 1. Can we transfer a response for the genes the challenge asks about? ---
    hit_any = set().union(*covered.values())
    missing = target_set - hit_any

    print("=== challenge panel coverage ===")
    for label, hit in covered.items():
        print(f"  {label:<20}: {len(hit):>3}/{len(targets)}")
    print(f"  {'ANY source':<20}: {len(hit_any):>3}/{len(targets)}")
    print(f"  {'NO source':<20}: {len(missing):>3}/{len(targets)}")
    if missing:
        shown = sorted(missing)[:15]
        print(f"    uncovered: {', '.join(shown)}"
              + (f" ... (+{len(missing) - len(shown)})" if len(missing) > len(shown) else ""))
    print()

    # --- 2. What can the leave-one-line-out harness actually validate on? ---
    # Panel overlap alone does not establish biological non-essentiality.
    # Shared perturbations test cross-context transfer, but an essential-gene
    # panel can differ strongly from the challenge's target/effect distribution.
    shared = all_symbols["K562 genome-wide"] & all_symbols["RPE1"]
    print("=== leave-one-line-out harness panel (K562 gwps vs RPE1) ===")
    print(f"  perturbations in K562 gwps : {len(all_symbols['K562 genome-wide']):,}")
    print(f"  perturbations in RPE1      : {len(all_symbols['RPE1']):,}")
    print(f"  measured in BOTH lines     : {len(shared):,}   <- validates both directions")
    print(f"  of which challenge targets : {len(shared & target_set)}")

    report["challenge_coverage"] = {
        label: sorted(hit) for label, hit in covered.items()
    }
    report["uncovered_targets"] = sorted(missing)
    report["harness_panel_size"] = len(shared)

    out = p.interim / "target_coverage.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    panel = p.interim / "harness_panel.csv"
    pd.DataFrame({"target_gene": sorted(shared)}).to_csv(panel, index=False)
    print(f"\nwrote {out.name} and {panel.name} to {p.interim}")


if __name__ == "__main__":
    main()
