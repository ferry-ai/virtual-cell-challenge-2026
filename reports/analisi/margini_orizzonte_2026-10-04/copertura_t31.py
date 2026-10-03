"""Which sources actually cover the 300 targets of the official panel in the t31 export?

Counts only: no target name is written (pert_counts.csv is private). Reads the 25 training keys the
t31 export used (rete-sorgenti-r1-train, consegna/chiavi) and the official target list.
Usage: python copertura_t31.py <chiavi dir> <pert_counts.csv>
"""
import collections
import csv
import json
import sys
from pathlib import Path

import numpy as np

keys_dir, targets_csv = Path(sys.argv[1]), Path(sys.argv[2])
rows = list(csv.reader(targets_csv.open(encoding="utf-8")))
panel = {r[0] for r in rows[1:] if r[0] != "non-targeting"}
by_group, out = collections.defaultdict(set), {"panel_targets": len(panel), "keys": []}
for f in sorted(keys_dir.glob("*.npz")):
    z = np.load(f, allow_pickle=False)
    t = set(map(str, z["targets"])) & panel
    by_group[str(z["group"])] |= t
    out["keys"].append({"key": str(z["key"]), "group": str(z["group"]), "targets_total": int(z["targets"].size),
                        "targets_in_panel": len(t), "genes_measured": int(np.asarray(z["measured"]).sum())})
covered = set().union(*by_group.values())
out["covered"] = len(covered)
out["groups"] = {g: {"in_panel": len(s), "only_this_group": len(s - set().union(*(v for k, v in by_group.items() if k != g)))}
                 for g, s in by_group.items()}
out["covered_by_one_group_only"] = sum(1 for t in covered if sum(t in s for s in by_group.values()) == 1)
print(json.dumps(out, indent=2))
