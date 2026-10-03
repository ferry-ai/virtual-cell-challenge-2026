"""Inventory before registration: targets and genes available to the context-propagation bench.

Reads only the source keys (truth effects aggregated per target, no cells) and writes counts plus the share of the
true-effect energy that falls on genes K562 gwps does not measure. It computes NO arm of the protocol.
Usage: python inventario.py <chiavi dir>
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np

keys = Path(sys.argv[1])
K = np.load(keys / "replogle_k562_gwps__K562.npz", allow_pickle=False)
k_meas, k_targets = np.asarray(K["measured"]), set(map(str, K["targets"]))


def line(files):
    n_pairs, num, den, per, targets = 0, 0.0, 0.0, [], set()
    for f in files:
        z = np.load(f, allow_pickle=False)
        m = np.asarray(z["measured"])
        t = list(map(str, z["targets"]))
        idx = [i for i, x in enumerate(t) if x in k_targets]
        targets |= {t[i] for i in idx}
        lfc = np.clip(np.nan_to_num(z["eff"].astype(np.float64))[idx][:, m], -10, 10)
        p = (np.expm1(z["basal"].astype(np.float64)) / 1e4)[m]
        d = np.log1p(5e4 * p * np.exp(lfc)) - np.log1p(5e4 * p)  # bulk-lognorm space at 50k
        u = (~k_meas)[m]
        tot, eu = (d ** 2).sum(1), (d[:, u] ** 2).sum(1)
        per += list(eu / np.maximum(tot, 1e-12))
        num, den, n_pairs = num + eu.sum(), den + tot.sum(), n_pairs + len(idx)
    z = np.load(files[0], allow_pickle=False)
    m = np.asarray(z["measured"])
    return {"keys": len(files), "targets_shared_with_k562": len(targets), "line_target_pairs": n_pairs,
            "genes_measured_both": int((m & k_meas).sum()), "genes_only_in_line_U": int((m & ~k_meas).sum()),
            "energy_share_on_U_pooled": num / den, "energy_share_on_U_median": float(np.median(per)),
            "median_cells_per_target": int(np.median(z["n_cells"]))}


out = {"k562_gwps_genes_measured": int(k_meas.sum()),
       "hipsci_pooled": line(sorted(glob.glob(str(keys / "hipsci_targeted_19__*.npz")))),
       "tian2021_neuron": line([str(keys / "tian2021_crispri__iPSC-induced neuron.npz")])}
print(json.dumps(out, indent=2))
