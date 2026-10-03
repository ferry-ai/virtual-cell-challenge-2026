"""The reconciled key of every target symbol, for the hash folds of the cell network (version 2).

The R-LEAD bench assigns a target to a fold by sha256 of its reconciled key (reports/modelli/risposta_contesto_2026-10-02/
splits.py), the key being the Ensembl ID recorded by the source, else the GENCODE v50 axis table, else the GTF name,
else SYM:<symbol> (p0_inventory.py). The cell network normalises labels to symbols of the official axis, so here each
symbol gets: the key the P0 inventory recorded most often for that symbol (ties: the smallest key), else the axis table
(gene_coordinates_gencode_v50.tsv), else nothing (the network then uses SYM:<symbol>, cell_data.target_key). Both
benches then hide the same targets in the same fold.

    py.cmd target_keys.py --p0 <report>/p0_r2 --coords <data>/external/annotation/gene_coordinates_gencode_v50.tsv
        --axis gene_names.csv --out <new file>.json
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--p0", type=Path, required=True)
    p.add_argument("--coords", type=Path, required=True)
    p.add_argument("--axis", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    with gzip.open(a.p0 / "context_target_study.csv.gz", "rt", encoding="utf-8") as f:
        cts = pd.read_csv(f, usecols=["target", "target_key"], low_memory=False)
    seen = defaultdict(Counter)
    for s, k in zip(cts["target"].astype(str), cts["target_key"].astype(str)):
        seen[s][k] += 1
    coords = pd.read_csv(a.coords, sep="\t")
    axis_ids = {s: str(g).split(".")[0] for s, g in zip(coords["symbol"], coords["gene_id"]) if isinstance(g, str)}
    axis = [l.strip().split(",")[0] for l in a.axis.read_text(encoding="utf-8").splitlines() if l.strip()][1:]
    out, how = {}, Counter()
    for s in sorted(set(axis) | set(seen)):
        if s in seen:
            best = sorted(seen[s].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            out[s], h = best, "p0_inventory"
        elif s in axis_ids:
            out[s], h = axis_ids[s], "axis_gencode_v50"
        else:
            continue
        how[h] += 1
    text = json.dumps(out, indent=0, sort_keys=True)
    a.out.write_text(text, encoding="utf-8")
    meta = {"symbols": len(out), "by_source": dict(how),
            "inputs": {"p0": str(a.p0), "coords": str(a.coords), "axis": str(a.axis)},
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    a.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
