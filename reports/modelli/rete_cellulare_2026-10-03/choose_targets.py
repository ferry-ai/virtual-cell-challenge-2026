"""Lane B targets of one held-out line (PROTOCOLLO.md §5), fixed by rule before any cell is generated or scored.

The rule of the six-member bench of R-LEAD (six_member_hepg2.py), restricted to what the cell network can be judged on:
C groups of the held-out keys in the training's eval_groups.json, whose reconciled key is a usable row of the held
line's cube table with at least --min-cells cells and is a usable row of at least one other line group of the cell
corpus (so that the transfer has support); ordered by sha256 of the key (salt 'six-member', as the bench) and cut at
--targets. Reads only the cube's row tables (rows.csv), never an effect.

    python choose_targets.py --eval-groups <training>/eval_groups.json --cube <cube_r2> --target-keys target_keys.json
        --held-group HepG2 --targets 150 --out targets.json
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

CELL_GROUPS = ("H1", "HepG2", "RPE1", "K562", "iPSC", "Jurkat", "Neuron")
NOT_IN_CELL_CORPUS = ("k562_viperturb",)


def unit_hash(key: str, salt: str) -> float:
    h = hashlib.sha256(f"{salt}:{key}".encode("utf-8")).hexdigest()
    return int(h[:15], 16) / 16 ** 15


def usable_rows(cube: Path, table: str, min_cells: float) -> dict:
    out = {}
    with open(cube / table / "rows.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            dup = str(r["duplicate_of_key"]).strip().lower() not in ("", "0", "false", "nan", "none")
            n = float(r["n_cells"])
            if not dup and n >= min_cells:
                out[r["target_key"]] = n
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--eval-groups", type=Path, required=True)
    p.add_argument("--cube", type=Path, required=True)
    p.add_argument("--target-keys", type=Path, required=True)
    p.add_argument("--held-group", required=True)
    p.add_argument("--targets", type=int, default=150)
    p.add_argument("--min-cells", type=float, default=50)
    p.add_argument("--support-min-cells", type=float, default=10)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    manifest = json.loads((a.cube / "manifest.json").read_text(encoding="utf-8"))
    group = {t: v["group"] for t, v in manifest["tables"].items()}
    held_tables = [t for t, g in group.items() if g == a.held_group]
    held_rows = {t: usable_rows(a.cube, t, a.min_cells) for t in held_tables}
    support = set()
    for t, g in group.items():
        if g != a.held_group and g in CELL_GROUPS and t not in NOT_IN_CELL_CORPUS:
            support |= set(usable_rows(a.cube, t, a.support_min_cells))
    keys = json.loads(a.target_keys.read_text(encoding="utf-8"))
    groups = json.loads(a.eval_groups.read_text(encoding="utf-8"))
    cand = []
    for g in groups:
        if g["class"] != "C":
            continue
        k = keys.get(g["symbol"]) or f"SYM:{g['symbol']}"
        for t in held_tables:
            if k in held_rows[t] and k in support:
                cand.append({"key": g["key"], "symbol": g["symbol"], "target_key": k, "table": t,
                             "cube_cells": held_rows[t][k]})
                break
    cand = sorted({c["target_key"]: c for c in cand}.values(), key=lambda c: unit_hash(c["target_key"], "six-member"))
    chosen = cand[:a.targets]
    a.out.write_text(json.dumps(chosen, indent=1), encoding="utf-8")
    print(json.dumps({"candidates": len(cand), "chosen": len(chosen), "tables": sorted({c["table"] for c in chosen})}))


if __name__ == "__main__":
    main()
