"""Acceptance tests of the version-2 data rules (cell_data.py), one per correction of the lead audit of 1/10
(reports/analisi/lead_audit_2026-10-01/NOTA_TRAINING.md, P1), each with a known answer:
- folds: the same function and salt as the R-LEAD bench; adding sources or symbols never moves a target;
- line groups: every context of a line in one group, a context of no rule its own group;
- loss weights: over every epoch each line group carries 1/G of the loss coefficients whatever the shard partition,
  the order or the batch size; the version-1 normalisation (sum of weights in the batch) does not;
- reservoir: min(n, k) per library, uniform inclusion, the same cells whatever the shard order;
- control draws: own library, resampled in it, or the key's pool, never another key.

    python -m unittest test_v2_units -v          (from this folder, with the project venv)
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cell_data as CD  # noqa: E402

RLEAD_SPLITS = HERE.parent / "risposta_contesto_2026-10-02" / "splits.py"


class Folds(unittest.TestCase):
    def test_same_fold_as_the_bench(self):
        spec = importlib.util.spec_from_file_location("rlead_splits", RLEAD_SPLITS)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod                  # dataclasses look the module up while it executes
        spec.loader.exec_module(mod)
        keys = [f"ENSG{i:011d}" for i in range(0, 5000, 7)] + ["SYM:FOO", "SYM:BAR"]
        self.assertEqual([CD.target_fold(k, 5) for k in keys], [mod.target_fold(k, 5) for k in keys])
        self.assertEqual(CD.FOLD_SALT, mod.SALT)

    def test_hidden_set_is_stable_when_the_corpus_grows(self):
        keys = {f"S{i}": f"ENSG{i:011d}" for i in range(400)}
        small = CD.hidden_by_fold([f"S{i}" for i in range(200)], keys, 2, 5)
        large = CD.hidden_by_fold([f"S{i}" for i in range(400)], keys, 2, 5)
        self.assertEqual(small, {s for s in large if int(s[1:]) < 200})
        self.assertGreater(len(small), 20)
        self.assertEqual(CD.hidden_by_fold(["S1"], keys, None, 5), set())

    def test_unmapped_symbol_has_its_own_key(self):
        self.assertEqual(CD.target_key("ZZZ", {}), "SYM:ZZZ")
        self.assertEqual(CD.target_key("A", {"A": "ENSG1"}), "ENSG1")


class Groups(unittest.TestCase):
    def test_rules(self):
        rules = {"contexts": {"KOLF2.1J iPSC": "iPSC", "iPSC-induced neuron": "Neuron"},
                 "study_prefixes": {"hipsci_": "iPSC"}}
        self.assertEqual(CD.group_of("kolf_strong", "KOLF2.1J iPSC", rules), "iPSC")
        self.assertEqual(CD.group_of("hipsci_targeted_19", "oikd_5", rules), "iPSC")
        self.assertEqual(CD.group_of("tian2021_crispri", "iPSC-induced neuron", rules), "Neuron")
        self.assertEqual(CD.group_of("replogle_rpe1", "RPE1", rules), "RPE1")

    def test_classes_after_qc(self):
        # G2 counterexample (audit 2.6): perturbed only in a kept key that QC removes, so never trained
        trained = {"G1"}
        self.assertEqual(CD.classify_held(True, "G1", False, set(), trained), "C")
        self.assertEqual(CD.classify_held(True, "G2", False, set(), trained), "J")
        self.assertEqual(CD.classify_held(True, "G1", False, {"G1"}, trained), "J")
        self.assertEqual(CD.classify_held(False, "G1", False, {"G1"}, trained), "T")
        self.assertEqual(CD.classify_held(True, "NTC", True, set(), trained), "control_holdout")
        self.assertEqual(CD.classify_combined_held(True, ("G1", "G2"), set(), trained), "combined:J")
        self.assertEqual(CD.classify_combined_held(True, ("G1",), set(), trained), "combined:C")


def replay(shard_rows, unit_of_shard, weights, W, batch, epochs, seed, version):
    """Loss coefficients by unit along a run of the batch machinery of train_cellnet.py (roles, role batches,
    EpochSampler), version 1 (divided by the batch's own sum of weights) or 2 (divided by the nominal batch); and the
    cells drawn by unit."""
    sys.path.insert(0, str(HERE))
    import train_cellnet as TC
    shards = [{"train_rows": np.asarray(r)} for r in shard_rows]
    parts = TC.roles_of(shards, W)
    rb, rc = TC.role_batches(shards, parts, batch)
    samplers = [CD.EpochSampler([(sid, shards[sid]["train_rows"]) for sid in parts[r]], 2, seed=seed * 1000 + r)
                for r in range(W)]
    steps = int(max((-(-epochs * rc[r] // rb[r]) - 1) * W + r + 1 for r in range(W) if rc[r]))
    coef, drawn = Counter(), Counter()
    for g in range(steps):
        r = g % W
        cells = samplers[r].batch(rb[r])
        w = np.array([weights[unit_of_shard[s]] for s, _ in cells])
        den = w.sum() if version == 1 else batch
        for (s, _), wi in zip(cells, w):
            coef[unit_of_shard[s]] += wi / den
            drawn[unit_of_shard[s]] += 1
    tot = sum(coef.values())
    return {u: v / tot for u, v in coef.items()}, drawn


def by_group(shares):
    out = Counter()
    for u, v in shares.items():
        out[u.split("::")[0]] += v
    return out


class Weights(unittest.TestCase):
    def setUp(self):
        # three line groups; group A has two studies (one huge), B one, C one small
        sizes = {"A::big": [4000, 3000, 3000], "A::small": [300], "B::one": [800, 700], "C::tiny": [150]}
        self.rows, self.unit = [], []
        for u, ss in sizes.items():
            for n in ss:
                self.rows.append(np.arange(n))
                self.unit.append(u)
        cells = Counter()
        for u, r in zip(self.unit, self.rows):
            cells[u] += len(r)
        self.w = CD.hierarchical_weights(cells, {u: u.split("::")[0] for u in cells})
        self.cells = cells

    def test_mean_weight_one_and_equal_groups(self):
        n = sum(self.cells.values())
        self.assertAlmostEqual(sum(self.w[u] * c for u, c in self.cells.items()) / n, 1.0, places=12)
        share = Counter()
        for u, c in self.cells.items():
            share[u.split("::")[0]] += self.w[u] * c / n
        for g in "ABC":
            self.assertAlmostEqual(share[g], 1 / 3, places=12)
        self.assertAlmostEqual(self.w["A::big"] * self.cells["A::big"], self.w["A::small"] * self.cells["A::small"])

    def test_inactive_units_get_no_weight(self):
        w = CD.hierarchical_weights({"A::x": 10, "B::y": 0}, {"A::x": "A", "B::y": "B"})
        self.assertEqual(set(w), {"A::x"})
        self.assertAlmostEqual(w["A::x"], 1.0)

    def test_whole_epochs_give_the_declared_shares_exactly(self):
        # 18,950 cells, batches of 50: two epochs are 758 steps and draw every cell exactly twice
        shares, drawn = replay(self.rows, self.unit, self.w, 1, 50, 2, 0, version=2)
        self.assertEqual(dict(drawn), {u: 2 * c for u, c in self.cells.items()})
        for g, v in by_group(shares).items():
            self.assertAlmostEqual(v, 1 / 3, places=9)

    def test_the_batch_composition_never_changes_the_objective(self):
        # version 2: each unit's share is its weight times its draws, whatever the partition, order and batch size;
        # the only departure from 1/G comes from the partial epoch at the end of the roles (limit set here: 0.02)
        for W, batch, seed in ((1, 64, 0), (2, 64, 1), (3, 100, 2)):
            shares, drawn = replay(self.rows, self.unit, self.w, W, batch, 2, seed, version=2)
            tot = sum(self.w[u] * n for u, n in drawn.items())
            for u in shares:
                self.assertAlmostEqual(shares[u], self.w[u] * drawn[u] / tot, places=12)
            for g, v in by_group(shares).items():
                self.assertAlmostEqual(v, 1 / 3, delta=0.02, msg=(W, batch, seed))

    def test_version_one_normalisation_misses_them(self):
        shares, _ = replay(self.rows, self.unit, self.w, 1, 50, 2, 0, version=1)
        self.assertGreater(by_group(shares)["A"], 0.5)   # batches of one shard cancel the weights: cells win
        self.assertEqual(CD.loss_shares({"A::big": 10}, {"A::big": 2.0}, {"A::big": "A"})["by_group"], {"A": 1.0})


class Reservoir(unittest.TestCase):
    def test_quotas(self):
        n = {0: 500, 1: 70, 2: 20, 3: 64}
        q = CD.pool_quotas(n, pool_size=256, k=64)
        self.assertTrue(all(min(v, 64) <= q[l] <= v for l, v in n.items()))
        self.assertEqual(q, {0: 107, 1: 65, 2: 20, 3: 64})   # 212 guaranteed, 44 shared by largest remainders
        self.assertEqual(sum(q.values()), 256)
        self.assertEqual(CD.pool_quotas({0: 10, 1: 30}, 256, 64), {0: 10, 1: 30})
        many = {l: 100 for l in range(56)}            # HepG2-like: 56 libraries
        qm = CD.pool_quotas(many, 2048, 64)
        self.assertTrue(all(v >= 64 for v in qm.values()))   # version 1 kept none at 64 after its cap

    def test_bottom_k_is_independent_of_the_order(self):
        keys = np.array([f"s|L|{i}" for i in range(3000)])
        u = CD.pool_hash(keys, 7)
        whole = set(keys[CD.bottom_k(u, 200)])
        rng = np.random.default_rng(0)
        for _ in range(3):
            perm = rng.permutation(keys.size)
            chunks = np.array_split(perm, 7)
            kept_k, kept_u = np.array([], dtype=keys.dtype), np.array([], np.uint64)
            for c in chunks:                          # shard by shard, keep the bottom-k of the union so far
                pick = CD.bottom_k(u[c], 200)
                kept_k = np.concatenate([kept_k, keys[c][pick]])
                kept_u = np.concatenate([kept_u, u[c][pick]])
                sel = CD.bottom_k(kept_u, 200)
                kept_k, kept_u = kept_k[sel], kept_u[sel]
            self.assertEqual(set(kept_k), whole)

    def test_inclusion_is_uniform(self):
        n, q, seeds = 100, 20, 400
        keys = np.array([f"s|L|{i}" for i in range(n)])
        hits = np.zeros(n)
        for seed in range(seeds):
            hits[CD.bottom_k(CD.pool_hash(keys, seed), q)] += 1
        p = hits / seeds
        self.assertAlmostEqual(p.mean(), q / n, places=12)
        sd = np.sqrt(q / n * (1 - q / n) / seeds)
        self.assertLess(np.abs(p - q / n).max(), 5 * sd)

    def test_draws_stay_in_library_or_key(self):
        pools = {"k": {0: np.arange(0, 100), 1: np.arange(100, 110), 2: np.arange(110, 113)}}
        rng = np.random.default_rng(0)
        rows, how = CD.draw_controls_lib(pools, "k", 0, 64, rng)
        self.assertEqual(how, 0)
        self.assertTrue(set(rows) <= set(range(100)) and len(set(rows)) == 64)
        rows, how = CD.draw_controls_lib(pools, "k", 1, 64, rng)
        self.assertEqual(how, 1)
        self.assertTrue(set(rows) <= set(range(100, 110)))
        rows, how = CD.draw_controls_lib(pools, "k", 2, 64, rng)
        self.assertEqual((how, CD.FALLBACK[how]), (2, "key_pool"))
        self.assertTrue(set(rows) <= set(range(113)))
        rows, how = CD.draw_controls_lib(pools, "k", 9, 64, rng)   # a library without pooled controls
        self.assertEqual(how, 2)


if __name__ == "__main__":
    unittest.main()
