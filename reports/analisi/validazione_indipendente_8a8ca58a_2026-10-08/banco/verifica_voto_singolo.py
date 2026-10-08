"""Check, on the fold effects of level A, what a single-target source does under panel centring.

With "common": "panel" and gamma 1, stage 100 subtracts from every source the mean of its own rows. A table
with one target (Tian 2019 neurons: RFK) is its own mean: its vote is exactly zero on every gene it measured,
with the full reliability weight n / (n + 100). R1 differs from T1 only by that table, so on RFK
R1 - T1 = -amplitude * mix_T1 * w / (W + w), with W the weight of the other sources on that gene: a pure
shrink toward zero, whatever the table contains. This reads the two files and counts.

    py verifica_voto_singolo.py <R1 effects npz> <T1 effects npz> <out.json>
"""
import json
import sys

import numpy as np

r1_path, t1_path, out = sys.argv[1:4]
with np.load(r1_path, allow_pickle=False) as a, np.load(t1_path, allow_pickle=False) as b:
    targets = a["targets"].astype(str)
    assert (targets == b["targets"].astype(str)).all() and (a["genes"] == b["genes"]).all()
    r1, t1, o1, o2 = a["lfc"].astype(np.float64), b["lfc"].astype(np.float64), a["observed"], b["observed"]
changed = np.flatnonzero(np.abs(r1 - t1).max(axis=1) > 0)
report = {"targets_changed_between_R1_and_T1": [str(targets[i]) for i in changed], "n_cells_single_source": 3190,
          "reliability_weight_single_source": 3190 / 3290}
i = int(np.flatnonzero(targets == "RFK")[0])
d = r1[i] - t1[i]
moved = d != 0
ratio = r1[i][moved] / t1[i][moved]
report["RFK"] = {
    "genes_observed": int(o2[i].sum()), "genes_moved": int(moved.sum()),
    "moved_genes_where_T1_is_zero": int((t1[i][moved] == 0).sum()),
    "share_of_moved_genes_pulled_toward_zero": float(np.mean(np.sign(d[moved]) == -np.sign(t1[i][moved]))),
    "ratio_R1_over_T1_quantiles_5_50_95": [float(q) for q in np.quantile(ratio[np.isfinite(ratio)], [0.05, 0.5, 0.95])],
    "share_of_ratios_in_0_1": float(np.mean((ratio > 0) & (ratio < 1))),
    "norm_T1": float(np.linalg.norm(t1[i])), "norm_R1": float(np.linalg.norm(r1[i])),
    "norm_difference": float(np.linalg.norm(d)), "cosine_R1_T1": float(r1[i] @ t1[i] / (np.linalg.norm(r1[i]) * np.linalg.norm(t1[i]))),
    "observed_masks_equal": bool((o1[i] == o2[i]).all()),
}
with open(out, "x", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1)
    fh.write("\n")
print(json.dumps(report, indent=1))
