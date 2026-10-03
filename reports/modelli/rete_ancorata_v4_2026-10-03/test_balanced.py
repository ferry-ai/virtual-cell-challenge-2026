"""The balanced sampler (balanced.py), in process and without counts.

- the quota clock: every step sums to the batch, each unit stays within one cell of its exact cumulative share, and a
  replay from step 0 gives the same quotas;
- the role partition: disjoint, complete, near-equal subsets of every unit, independent of the shard order;
- the sampler: every window holds each line group's declared share exactly up to rounding, every unit is drawn from
  the first step, cells within a unit are drawn uniformly, and a resumed sampler continues with the same cells;
- the defect it replaces, simulated on the layout of the H1 training (the admitted cells of its 31 keys, from the
  receipt, cut into shards of about the corpus' size): version 3's epoch sampler stopped at 0.714 epochs leaves line
  groups out of the ±0.02 rule for most seeds, the balanced sampler for none. A simulation of the mechanism, not a
  reconstruction of the H1 run's exact shards.

    python -m unittest test_balanced -v           (from this folder, with the project venv; under a minute)
"""
from __future__ import annotations

import json
import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import balanced as BL  # noqa: E402
import cell_data as CD  # noqa: E402

RECEIPTS = HERE.parent.parent / "analisi" / "candidato_ibrido_2026-10-03" / "training_receipts.json"
GROUP_OF_STUDY = {"a549": "A549", "hepg2": "HepG2", "hipsci": "iPSC", "jurkat": "Jurkat", "kolf": "iPSC",
                  "norman2019": "K562", "replogle_k562": "K562", "replogle_rpe1": "RPE1", "tian2021": "Neuron",
                  "h1_vcc2025": "H1"}


def group_of_key(key):
    study = key.split("|", 1)[0]
    return next(g for p, g in GROUP_OF_STUDY.items() if study.startswith(p))


class Clock(unittest.TestCase):
    def test_quotas(self):
        rng = np.random.default_rng(0)
        for trial in range(5):
            U = int(rng.integers(3, 20))
            s = rng.dirichlet(np.ones(U))
            shares = {f"u{i}": float(v) for i, v in enumerate(s)}
            units = sorted(shares)
            clock = BL.QuotaClock(units, shares, 256)
            cum = np.zeros(U)
            for step in range(3000):
                q = clock.quotas(step)
                self.assertEqual(int(q.sum()), 256)
                cum += q
                exact = (step + 1) * 256 * np.array([shares[u] for u in units])
                self.assertLess(np.abs(cum - exact).max(), 1.0 + 1e-9)
            replay = BL.QuotaClock(units, shares, 256)
            np.testing.assert_array_equal(replay.quotas(1234), clock.quotas(1234))


class Partition(unittest.TestCase):
    def test_disjoint_complete_balanced(self):
        rows = {"A::a": [(0, np.arange(0, 5000)), (3, np.arange(10, 4000, 3))], "B::b": [(1, np.arange(700))]}
        parts = BL.partition(rows, 3, seed=11)
        for u, items in rows.items():
            got = sorted((sid, int(r)) for p in parts for sid, rr in p[u] for r in rr)
            want = sorted((sid, int(r)) for sid, rr in items for r in rr)
            self.assertEqual(got, want)                                   # every cell once, in exactly one role
            sizes = [sum(rr.size for _, rr in p[u]) for p in parts]
            self.assertLessEqual(max(sizes) - min(sizes), 1)
        again = BL.partition({u: list(reversed(v)) for u, v in rows.items()}, 3, seed=11)
        for p, q in zip(parts, again):                                     # the shard order changes nothing
            for u in rows:
                self.assertEqual(sorted((s, tuple(r)) for s, r in p[u]), sorted((s, tuple(r)) for s, r in q[u]))


def layout(sizes: dict, per_shard: int):
    """Shards of at most per_shard cells, one study's cells in consecutive shards: [(sid, key, rows)]."""
    out, sid = [], 0
    for key, n in sizes.items():
        for lo in range(0, n, per_shard):
            out.append((sid, key, np.arange(lo, min(n, lo + per_shard))))
            sid += 1
    return out


class Sampler(unittest.TestCase):
    def setUp(self):
        sizes = {"big|K": 40000, "big2|K": 3000, "mid|M": 9000, "tiny|T": 700}
        self.shards = layout(sizes, 2500)
        self.unit_of_key = {k: f"{k.split('|')[1]}::{k.split('|')[0]}" for k in sizes}
        rows = defaultdict(list)
        for sid, key, rr in self.shards:
            rows[self.unit_of_key[key]].append((sid, rr))
        self.rows = dict(rows)
        cells = {u: sum(r.size for _, r in v) for u, v in self.rows.items()}
        self.shares = BL.unit_shares(cells, {u: u.split("::")[0] for u in cells})
        self.cells = cells

    def test_shares(self):
        self.assertAlmostEqual(self.shares["K::big"], 1 / 6)
        self.assertAlmostEqual(self.shares["K::big2"], 1 / 6)
        self.assertAlmostEqual(self.shares["T::tiny"], 1 / 3)
        self.assertAlmostEqual(sum(self.shares.values()), 1.0)

    def test_windows_and_uniformity_and_resume(self):
        W, B = 2, 64
        units = sorted(self.shares)
        parts = BL.partition(self.rows, W, seed=3)
        samplers = [BL.BalancedSampler(parts[r], BL.QuotaClock(units, self.shares, B), 2, 3, r) for r in range(W)]
        draws = Counter()
        per_group_window = []
        win = Counter()
        for g in range(2000):
            cells, us = samplers[g % W].batch(g)
            self.assertEqual(len(cells), B)
            for (sid, r), u in zip(cells, us):
                draws[(sid, r)] += 1
                win[u.split("::")[0]] += 1
            if (g + 1) % 50 == 0:
                tot = sum(win.values())
                per_group_window.append({k: v / tot for k, v in win.items()})
                win = Counter()
        for w in per_group_window:                                          # every window: 1/3 each, to rounding
            self.assertEqual(set(w), {"K", "M", "T"})
            for v in w.values():
                self.assertLess(abs(v - 1 / 3), 0.01)
        tiny = [n for (sid, r), n in draws.items() if self.shards[sid][1] == "tiny|T"]
        self.assertEqual(len(tiny), 700)                                    # every tiny cell drawn, about equally
        self.assertLessEqual(max(tiny) - min(tiny), 2)
        # resume: a fresh sampler that replays the consumed steps continues with the same cells
        fresh = BL.BalancedSampler(parts[0], BL.QuotaClock(units, self.shares, B), 2, 3, 0)
        for g in range(0, 2000, W):
            fresh.batch(g)
        self.assertEqual(fresh.batch(2000)[0], samplers[0].batch(2000)[0])

    def test_too_many_roles_refused(self):
        rows = {"A::a": [(0, np.arange(1))], "B::b": [(1, np.arange(50))]}
        parts = BL.partition(rows, 4, seed=0)
        shares = {"A::a": 0.5, "B::b": 0.5}
        empty = next(r for r in range(4) if "A::a" not in parts[r])
        with self.assertRaises(ValueError):
            BL.BalancedSampler(parts[empty], BL.QuotaClock(["A::a", "B::b"], shares, 8), 1, 0, empty)


@unittest.skipUnless(RECEIPTS.is_file(), "the receipts of the v3 trainings are not in this checkout")
class H1Layout(unittest.TestCase):
    """The mechanism of the H1 defect, simulated: the admitted cells of the H1 run's keys, shards of 11,700 cells
    (the corpus' mean), three roles, a buffer of four shards, a stop at 0.714 epochs; loss shares with the run's
    hierarchical weights for version 3, cell counts for the balanced sampler. Cells, shard sizes and batch are divided
    by 20 (same number of shards, same proportions), so the simulation takes seconds."""

    SCALE = 20

    @classmethod
    def setUpClass(cls):
        r = json.loads(RECEIPTS.read_text(encoding="utf-8"))["runs"]["rcell-anchored-train-h1-r1"]["receipts"]
        cov = r["train/coverage.json"]["content"]
        cls.sizes = {e["key"]: max(1, e["admitted_offered"] // cls.SCALE) for e in cov["by_key"]}
        units = {k: f"{group_of_key(k)}::{k.split('|')[0]}" for k in cls.sizes}
        cells = Counter()
        for k, n in cls.sizes.items():
            cells[units[k]] += n
        cls.weights = CD.hierarchical_weights(cells, {u: u.split("::")[0] for u in cells})
        cls.units, cls.cells = units, cells
        cls.shards = layout(cls.sizes, 11700 // cls.SCALE)

    def v3_shares(self, seed, stop_fraction=0.714, W=3, buffer=4, batch=256 // 20):
        shards = [{"train_rows": rr} for _, _, rr in self.shards]
        parts = [[] for _ in range(W)]
        load = np.zeros(W)
        for sid in sorted(range(len(shards)), key=lambda i: (-shards[i]["train_rows"].size, i)):
            w = int(np.argmin(load))
            parts[w].append(sid)
            load[w] += shards[sid]["train_rows"].size
        total = sum(self.sizes.values())
        steps = int(stop_fraction * total / batch)
        coef = Counter()
        for w in range(W):
            sampler = CD.EpochSampler([(sid, shards[sid]["train_rows"]) for sid in parts[w]], buffer,
                                      seed=seed * 1000 + w)
            for _ in range(steps // W):
                for sid, _ in sampler.batch(batch):
                    u = self.units[self.shards[sid][1]]
                    coef[u.split("::")[0]] += self.weights[u]
        tot = sum(coef.values())
        return {g: coef.get(g, 0.0) / tot for g in {u.split("::")[0] for u in self.cells}}

    def test_epoch_sampler_breaks_the_rule_balanced_does_not(self):
        bad = 0
        for seed in range(20):
            shares = self.v3_shares(seed)
            if max(abs(v - 1 / 7) for v in shares.values()) > 0.02:
                bad += 1
        self.assertGreater(bad, 10, "the epoch sampler should usually miss the rule at 0.714 epochs")
        rows = defaultdict(list)
        for sid, key, rr in self.shards:
            rows[self.units[key]].append((sid, rr))
        shares = BL.unit_shares(dict(self.cells), {u: u.split("::")[0] for u in self.cells})
        parts = BL.partition(dict(rows), 3, seed=0)
        units = sorted(shares)
        samplers = [BL.BalancedSampler(parts[r], BL.QuotaClock(units, shares, 256), 2, 0, r) for r in range(3)]
        coef = Counter()
        for g in range(300):
            for _, u in zip(*samplers[g % 3].batch(g)):
                coef[u.split("::")[0]] += 1
        tot = sum(coef.values())
        self.assertLess(max(abs(v / tot - 1 / 7) for v in coef.values()), 0.002)
        self.assertEqual(len(coef), 7)


if __name__ == "__main__":
    unittest.main()
