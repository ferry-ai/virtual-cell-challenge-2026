"""Which training line groups (and modalities) really teach each target, after the exclusions and QC of one prepass.

From the prepass state of one held-out line (prepass.pkl): for every admitted training cell of a single-target label
(class 'train', not a control), counts by (symbol, line group, modality); and, for every evaluation group of the held-out
line, how many training line groups saw its symbol at all, with CRISPRi, with CRISPRa and with KO. Descriptive (the
question of Codex, 3/10): it tells whether the network is asked to learn responses from one or two lines despite seven
groups in total. Writes target_by_group.csv.gz and eval_support.csv next to --out.

    python target_matrix.py --prepass <prepass dir> --out <new dir>
"""
from __future__ import annotations

import argparse
import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prepass", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    with open(a.prepass / "prepass.pkl", "rb") as fh:
        st = pickle.load(fh)
    classes = st["classes"]
    train_code = classes.index("train")
    key_group = st["key_group"]
    groups_of_key = [key_group[k] for k in st["key_names"]]
    mods = st["modalities"]
    symbols = st["symbols"]
    counts = Counter()
    for s in st["shards"]:
        sel = (np.asarray(s["admitted"], bool) & ~np.asarray(s["control"], bool)
               & (np.asarray(s["cls"]) == train_code) & (np.asarray(s["tgt"]) >= 0))
        if not sel.any():
            continue
        trip = np.stack([np.asarray(s["tgt"])[sel], np.asarray(s["key"])[sel], np.asarray(s["mod"])[sel]], 1)
        u, n = np.unique(trip, axis=0, return_counts=True)
        for (t, k, m), c in zip(u.tolist(), n.tolist()):
            counts[(symbols[t], groups_of_key[k], mods[m])] += int(c)
    rows = [{"symbol": s, "group": g, "modality": m, "training_cells": c} for (s, g, m), c in sorted(counts.items())]
    tab = pd.DataFrame(rows)
    a.out.mkdir(parents=True)
    tab.to_csv(a.out / "target_by_group.csv.gz", index=False, compression="gzip")
    seen = defaultdict(lambda: defaultdict(set))
    for r in rows:
        seen[r["symbol"]][r["modality"]].add(r["group"])
        seen[r["symbol"]]["any"].add(r["group"])
    ev = []
    for g in st["eval_groups"]:
        s = g["symbol"]
        by = seen.get(s, {})
        ev.append({"class": g["class"], "key": g["key"], "symbol": s, "admitted_cells": g["admitted_cells"],
                   "training_groups_any": len(by.get("any", ())),
                   **{f"training_groups_{m}": len(by.get(m, ())) for m in mods},
                   "groups": ";".join(sorted(by.get("any", ())))})
    pd.DataFrame(ev).to_csv(a.out / "eval_support.csv", index=False)
    summary = {"holdout_group": st.get("holdout_group"), "modalities": mods,
               "symbols_trained": int(tab.symbol.nunique()) if len(tab) else 0,
               "symbols_by_number_of_training_groups": {str(k): int(v) for k, v in
                                                        tab.groupby("symbol").group.nunique().value_counts().sort_index().items()},
               "eval_groups_by_training_groups": {cl: {str(k): int(v) for k, v in
                                                       pd.DataFrame(ev).query("`class` == @cl").training_groups_any.value_counts().sort_index().items()}
                                                  for cl in ("C", "J", "T")}}
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
