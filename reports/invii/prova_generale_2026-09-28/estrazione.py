"""Step 1 of the dress rehearsal: draw the 300 fake targets and the D/E/F permutation of A/B/C.

As registered in RISULTATI.md (fixed at 20:00 on 28/09, before running): seed 20261022,
`np.random.default_rng`; every pool sorted alphabetically; `rng.choice` without replacement, in
this fixed order of strata:

    P3    today's panel                                   30
    P1-4  on the axis, not in the panel, in all 4 sources 120
    P1-3  ... in 3 sources                                50
    P1-2  ... in 2 sources                                40
    P1-1  ... in 1 source                                 30
    P0    on the axis, in no t22 source                   30

then `rng.permutation(["A", "B", "C"])` maps onto D, E, F in that order. Sources are the t22
ones as the protocol chose them (K562 of 26/09; CD4 and Orion `_me1`); the 26/09 universes are
read too, only to check that they list the same targets. A source "covers" a target when its
universe index gives the target a chunk (effects exist).

Writes into ``--out`` (default: this folder), refusing to overwrite:
- ``bersagli.csv``: target, stratum, draw order, sources, number of sources, in today's panel,
  has TSS coordinates, and membership in other universes (information only);
- ``pert_counts.csv``: ``target_gene`` only, alphabetical, LF, like the official file;
- ``pert_counts_n40.csv``: the same with ``n_cells`` = 40, for stage 48 at the reduced shape;
- ``estrazione.json``: seed, pool sizes against the ones registered, the mapping, the universes'
  index hashes, the u26-vs-me1 check.

    scripts/py.cmd reports/invii/prova_generale_2026-09-28/estrazione.py
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from comune import (  # noqa: E402
    HERE, SOURCES_ME1, SOURCES_U26, data_root, read_targets, sha256_file, universe_targets, write_new_json,
    write_new_text,
)

SEED = 20261022
STRATA = [("P3", 30), ("P1-4", 120), ("P1-3", 50), ("P1-2", 40), ("P1-1", 30), ("P0", 30)]
# Pool sizes written in the plan (map of 28/09, from the 26/09 universes), checked, not imposed.
PLANNED_POOLS = {"P3": 300, "P1-4": 7131, "P1-3": 4015, "P1-2": 5390, "P1-1": 723, "P0": 974}
INFO_UNIVERSES = ["universe_k562ess_2026-09-26", "universe_rpe1_2026-09-26", "universe_a549_2026-09-27_me1",
                  "universe_kolf_2026-09-27_me1", "universe_southard_hs27_2026-09-27_p2",
                  "universe_viperturb_2026-09-27_p1"]
N_REDUCED = 40


def pools(axis: list[str], panel: list[str], covered: dict[str, set[str]]) -> dict[str, list[str]]:
    """Stratum -> sorted pool. P1-k and P0 exclude the panel; all are on the axis."""
    pset = set(panel)
    n_src = {g: sum(g in s for s in covered.values()) for g in axis}
    out = {"P3": sorted(pset)}
    for k in (4, 3, 2, 1):
        out[f"P1-{k}"] = sorted(g for g in axis if g not in pset and n_src[g] == k)
    out["P0"] = sorted(g for g in axis if g not in pset and n_src[g] == 0)
    return out


def draw(pool_map: dict[str, list[str]], seed: int = SEED) -> tuple[list[tuple[str, str]], dict[str, str]]:
    """[(target, stratum)] in draw order, and {D, E, F} -> {A, B, C}."""
    rng = np.random.default_rng(seed)
    drawn = []
    for stratum, n in STRATA:
        pool = np.array(pool_map[stratum], dtype=object)
        if len(pool) < n:
            raise SystemExit(f"pool {stratum} holds {len(pool)} targets, {n} are to be drawn")
        for t in rng.choice(pool, size=n, replace=False):
            drawn.append((str(t), stratum))
    perm = rng.permutation(["A", "B", "C"])
    mapping = {new: str(old) for new, old in zip(("D", "E", "F"), perm)}
    if len({t for t, _ in drawn}) != sum(n for _, n in STRATA):
        raise SystemExit("a target was drawn twice: the strata overlap")
    return drawn, mapping


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=HERE)
    ap.add_argument("--seed", type=int, default=SEED, help="the registered seed; change it only in a test")
    args = ap.parse_args()
    root = data_root()
    controls = root / "raw" / "controls"
    axis = pd.read_csv(controls / "gene_names.csv").iloc[:, 0].astype(str).tolist()
    panel = read_targets(controls / "pert_counts.csv")
    for name in ("bersagli.csv", "pert_counts.csv", "pert_counts_n40.csv", "estrazione.json"):
        if (args.out / name).exists():
            raise SystemExit(f"{args.out / name} exists; the draw is done once")

    covered = {name: universe_targets(root / "processed" / d) for name, d in SOURCES_ME1.items()}
    u26 = {}
    for name, d in SOURCES_U26.items():
        if d == SOURCES_ME1[name]:
            continue
        other = universe_targets(root / "processed" / d)
        u26[name] = {"universe_u26": d, "targets_me1": len(covered[name]), "targets_u26": len(other),
                     "only_me1": sorted(covered[name] - other)[:20], "only_u26": sorted(other - covered[name])[:20],
                     "same_targets": other == covered[name]}
    pool_map = pools(axis, panel, covered)
    drawn, mapping = draw(pool_map, args.seed)

    coords_path = root / "external" / "annotation" / "gene_coordinates_gencode_v50.tsv"
    coords = set()
    if coords_path.exists():
        coords = set(pd.read_csv(coords_path, sep="\t", usecols=["symbol"])["symbol"].astype(str))
    info = {}
    for d in INFO_UNIVERSES:
        if (root / "processed" / d / "index.csv").exists():
            info[d] = universe_targets(root / "processed" / d)

    pset = set(panel)
    rows = []
    for order, (t, stratum) in enumerate(drawn):
        srcs = [n for n in SOURCES_ME1 if t in covered[n]]
        row = {"target_gene": t, "stratum": stratum, "draw_order": order, "sources": ";".join(srcs),
               "n_sources": len(srcs), "in_current_panel": t in pset, "has_coordinates": t in coords}
        for d, s in info.items():
            row[f"in_{d.removeprefix('universe_')}"] = t in s
        rows.append(row)
    table = pd.DataFrame(rows).sort_values("target_gene").reset_index(drop=True)
    targets = table["target_gene"].tolist()

    args.out.mkdir(parents=True, exist_ok=True)
    write_new_text(args.out / "bersagli.csv", table.to_csv(index=False, lineterminator="\n"))
    write_new_text(args.out / "pert_counts.csv", "target_gene\n" + "".join(f"{t}\n" for t in targets))
    write_new_text(args.out / "pert_counts_n40.csv",
                   "target_gene,n_cells\n" + "".join(f"{t},{N_REDUCED}\n" for t in targets))
    sizes = {k: len(v) for k, v in pool_map.items()}
    summary = {
        "script": "reports/invii/prova_generale_2026-09-28/estrazione.py",
        "written_utc": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "strata": [{"stratum": s, "drawn": n, "pool": sizes[s], "pool_planned": PLANNED_POOLS[s]} for s, n in STRATA],
        "pools_as_planned": sizes == PLANNED_POOLS,
        "mapping_new_to_old": mapping,
        "sources": {n: {"universe": d, "targets_with_effects": len(covered[n]),
                        "index_sha256": sha256_file(root / "processed" / d / "index.csv")}
                    for n, d in SOURCES_ME1.items()},
        "u26_vs_me1": u26,
        "coordinates": {"path": str(coords_path), "found": bool(coords)},
        "info_universes": {d: len(s) for d, s in info.items()},
        "drawn_by_n_sources": table["n_sources"].value_counts().sort_index().to_dict(),
        "drawn_with_coordinates": int(table["has_coordinates"].sum()),
        "pert_counts_sha256": sha256_file(args.out / "pert_counts.csv"),
        "pert_counts_n40_sha256": sha256_file(args.out / "pert_counts_n40.csv"),
    }
    write_new_json(args.out / "estrazione.json", summary)
    print(f"drew {len(targets)} targets; pools {sizes} (as planned: {summary['pools_as_planned']})")
    print(f"mapping new -> old: {mapping}")
    print(f"u26 vs me1 same targets: { {k: v['same_targets'] for k, v in u26.items()} }")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
