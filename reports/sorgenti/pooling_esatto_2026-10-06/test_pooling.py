"""Synthetic fixtures for pooling.py against the ORIGINAL stage-98 estimator.

    .\\scripts\\py.cmd reports/sorgenti/pooling_esatto_2026-10-06/test_pooling.py   (prints a JSON summary too)
"""
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pooling as P  # noqa: E402
from vcc2026.multisource import effects_from_pseudobulk, z_shrink  # noqa: E402

G, NT = 3000, 30
GENES = np.array([f"g{i}" for i in range(G)])
TARGETS = [f"t{i}" for i in range(NT)]
SUMMARY = {}


def make_rows(seed, donors, conditions, rows_per=2):
    """Summed-count rows: per donor x condition, controls and each target in `rows_per` row sets (GEM groups)."""
    rng = np.random.default_rng(seed)
    base = rng.lognormal(0, 2.2, G)
    base[rng.choice(G, 300, replace=False)] *= 1e-5           # very low genes: usable / min_expected edge cases
    base /= base.sum()
    fc = np.exp(rng.normal(0, 0.35, (NT, G)) * (rng.random((NT, G)) < 0.1))
    X, rows = [], []
    for d in donors:
        dshift = np.exp(rng.normal(0, 0.15, G))
        for c in conditions:
            for t in ["non-targeting"] + TARGETS:
                for r in range(rows_per):
                    n = int(rng.integers(400, 900)) if t == "non-targeting" else int(rng.integers(3, 40))
                    p = base * dshift * (fc[TARGETS.index(t)] if t != "non-targeting" else 1.0)
                    p = p / p.sum()
                    lib = n * rng.lognormal(np.log(4000), 0.3)
                    X.append(rng.poisson(lib * p))
                    rows.append({"target": t, "donor": d, "condition": c, "n_cells": n})
    return np.array(X, dtype=np.float64), pd.DataFrame(rows)


def by_donor(X, obs, donors):
    return [P.Unit(d, X[(obs["donor"] == d).to_numpy()], obs[obs["donor"] == d].reset_index(drop=True), GENES)
            for d in donors]


class Pooling(unittest.TestCase):
    def test_pool_units_identity_split_same_donor(self):
        """Units that split one donor (train/val) pooled by pool_units == the original on all rows."""
        X, obs = make_rows(1, ["D1", "D2"], ["c"], rows_per=2)
        ref = effects_from_pseudobulk(X, obs, GENES, targets=TARGETS, condition=None, min_expected=1.0, **P.CALL)
        half = np.arange(len(obs)) % 2 == 0                       # alternate row sets: "train" and "val"
        units = [P.Unit("train", X[half], obs[half].reset_index(drop=True), GENES),
                 P.Unit("val", X[~half], obs[~half].reset_index(drop=True), GENES)]
        new = P.pool_units(units, targets=TARGETS, condition=None, min_expected=1.0)
        rep = P.compare_tables(P.as_table(new), P.as_table(ref))
        SUMMARY["pool_units_train_val"] = rep["equal"]
        self.assertTrue(rep["equal"], rep)

    def _combine_case(self, min_expected):
        donors = ["D1", "D2", "D3"]
        X, obs = make_rows(2, donors, ["c"], rows_per=1)
        ref = effects_from_pseudobulk(X, obs, GENES, targets=TARGETS, condition="c", min_expected=min_expected,
                                      **P.CALL)
        parts = [P.donor_stats(X, obs, GENES, d, targets=TARGETS, condition="c", min_expected=min_expected)
                 for d in donors]
        new = P.combine_donors(parts, targets=TARGETS, min_expected=min_expected)
        return P.compare_tables(P.as_table((new, GENES)), P.as_table(ref)), X, obs, ref

    def test_combine_disjoint_donors_exact(self):
        for me in (0.0, 1.0):
            rep, *_ = self._combine_case(me)
            SUMMARY[f"combine_donors_min_expected_{me}"] = rep["equal"]
            self.assertTrue(rep["equal"], rep)

    def test_shrink_then_average_differs(self):
        """What r6 did: shrink each donor's table, then average. Measured against the original."""
        rep, X, obs, ref = self._combine_case(1.0)
        tabs = []
        for d in ["D1", "D2", "D3"]:
            m = (obs["donor"] == d).to_numpy()
            tabs.append(effects_from_pseudobulk(X[m], obs[m].reset_index(drop=True), GENES, targets=TARGETS,
                                                condition="c", min_expected=1.0, **P.CALL))
        num, den = np.zeros((NT, G)), np.zeros((NT, G))
        for s in tabs:
            idx = s.index()
            for i, t in enumerate(TARGETS):
                if t in idx:
                    v = s.shrunk[idx[t]].astype(np.float64)
                    ok = np.isfinite(v)
                    w = s.n_cells[idx[t]] / (s.n_cells[idx[t]] + 100.0)
                    num[i] += np.where(ok, w * v, 0)
                    den[i] += np.where(ok, w, 0)
        after = np.divide(num, den, out=np.full_like(num, np.nan), where=den > 0)
        ri = ref.index()
        a = np.array([after[TARGETS.index(t)] for t in ref.targets])
        b = ref.shrunk.astype(np.float64)
        fin = np.isfinite(a) & np.isfinite(b)
        diff = np.abs(a - b)[fin]
        big = np.abs(b[fin]) > 0.1
        SUMMARY["shrink_then_average"] = {"max_abs_diff": float(diff.max()),
                                          "median_rel_diff_on_|ref|>0.1": float(np.median(diff[big] / np.abs(b[fin][big]))),
                                          "corr": float(np.corrcoef(a[fin], b[fin])[0, 1])}
        self.assertGreater(diff.max(), 1e-3)
        _ = ri

    def test_combine_fails_when_a_donor_is_split(self):
        """The shortcut is NOT valid for a donor split across units: log of sums != mean of logs."""
        X, obs = make_rows(3, ["D1"], ["c"], rows_per=2)
        ref = effects_from_pseudobulk(X, obs, GENES, targets=TARGETS, condition=None, min_expected=0.0, **P.CALL)
        half = np.arange(len(obs)) % 2 == 0
        o1, o2 = obs[half].reset_index(drop=True).copy(), obs[~half].reset_index(drop=True).copy()
        o1["donor"], o2["donor"] = "D1_train", "D1_val"           # treated as two donors: the wrong shortcut
        parts = [P.donor_stats(X[half], o1, GENES, "D1_train", targets=TARGETS),
                 P.donor_stats(X[~half], o2, GENES, "D1_val", targets=TARGETS)]
        new = P.combine_donors(parts, targets=TARGETS)
        rep = P.compare_tables(P.as_table((new, GENES)), P.as_table(ref))
        SUMMARY["combine_on_split_donor_equal"] = rep["equal"]
        SUMMARY["combine_on_split_donor_max_diff_shrunk"] = rep["shrunk"]["max_abs_diff"]
        self.assertFalse(rep["equal"])

    def test_condition_none_pools_conditions_within_donor(self):
        """condition=None (extra sources) sums a donor's rows across conditions: per-condition shortcuts differ."""
        X, obs = make_rows(4, ["D1", "D2"], ["a", "b"], rows_per=1)
        ref = effects_from_pseudobulk(X, obs, GENES, targets=TARGETS, condition=None, **P.CALL)
        units = [P.Unit(f"{d}_{c}", X[((obs.donor == d) & (obs.condition == c)).to_numpy()],
                        obs[(obs.donor == d) & (obs.condition == c)].reset_index(drop=True), GENES)
                 for d in ["D1", "D2"] for c in ["a", "b"]]
        new = P.pool_units(units, targets=TARGETS, condition=None)
        rep = P.compare_tables(P.as_table(new), P.as_table(ref))
        SUMMARY["pool_units_conditions_none"] = rep["equal"]
        self.assertTrue(rep["equal"], rep)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    print(json.dumps(SUMMARY, indent=1))
    sys.exit(0 if r.wasSuccessful() else 1)
