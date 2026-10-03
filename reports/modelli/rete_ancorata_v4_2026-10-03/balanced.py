"""Balanced batches for the cell network, version 4 (PROTOCOLLO.md of this folder).

Why (diagnosi_r1/DIAGNOSI.md): versions 2-3 drew cells through cell_data.EpochSampler, one per loader role, reading
the role's shards in an order shuffled once per epoch, and balanced line groups through loss weights. The weights give
every group 1/G of the objective only over whole epochs: the H1 training stopped at 0.714 epochs and never read the
shards of tian2021_crispri (26,218 admitted cells), so the Neuron group carried 0.7% of the loss instead of 14.3%.

Here the batch itself carries the declared shares, at every step:
- unit_shares: a unit is a study within a line group (cell_data.hierarchical_weights' unit); every active line group
  weighs 1/G and every unit 1/(units of its group) of its group, the objective of versions 2-3;
- QuotaClock: integer quotas per global step that sum to the batch; the cumulative count of every unit stays within
  one cell of its exact share at every step (largest accumulated remainder, deterministic);
- partition: each unit's cells, ordered by a hash of (seed, shard, row), are dealt to the W loader roles in turn, so
  every role draws from every unit, its subset is a uniform sample of the unit, and the subsets differ by one cell;
- BalancedSampler: per role, one cell_data.EpochSampler per unit over the role's cells of that unit (its own shuffled
  epochs and a small buffer of shards), drawing that unit's quota of each of the role's steps.
Because the sampling realises the shares, every drawn cell has loss weight 1: the shares are not applied twice.
A cell of unit u is drawn on average B s_u / N_u times per step (B the batch, N_u the unit's training cells).
"""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np

from cell_data import EpochSampler

MASK64 = (1 << 64) - 1


def unit_shares(cells_by_unit: dict, group_of_unit: dict) -> dict:
    """Share of the batch of every active unit (with training cells): 1/G per line group, split equally among the
    group's active units. The same objective as cell_data.hierarchical_weights, as a share instead of a weight."""
    active = sorted(u for u, n in cells_by_unit.items() if n > 0)
    members = defaultdict(list)
    for u in active:
        members[group_of_unit[u]].append(u)
    G = len(members)
    return {u: 1.0 / (G * len(members[group_of_unit[u]])) for u in active}


class QuotaClock:
    """Quotas per global step for units of fixed shares: each step every unit gets floor(B s_u) cells, and the
    remaining cells of the batch go to the units with the largest accumulated fractional parts (ties by unit order).
    quotas(step) is a pure function of the step: the clock replays from 0 when asked for an earlier step."""

    def __init__(self, units: list, shares: dict, batch: int):
        self.units = list(units)
        s = np.array([shares[u] for u in self.units], np.float64)
        if abs(s.sum() - 1.0) > 1e-9:
            raise ValueError(f"shares sum to {s.sum()}")
        exact = batch * s
        self.base = np.floor(exact + 1e-12).astype(np.int64)
        self.frac = exact - self.base
        self.left = int(round(batch - self.base.sum()))
        self.batch = batch
        self._reset()

    def _reset(self):
        self.acc = np.zeros(len(self.units), np.float64)
        self.step = 0

    def _advance(self):
        self.acc += self.frac
        q = self.base.copy()
        if self.left:
            order = np.lexsort((np.arange(len(self.units)), -self.acc))
            pick = order[:self.left]
            q[pick] += 1
            self.acc[pick] -= 1.0
        self.step += 1
        return q

    def quotas(self, step: int) -> np.ndarray:
        if step < self.step:
            self._reset()
        q = None
        while self.step <= step:
            q = self._advance()
        return q


def splitmix64(x: np.ndarray) -> np.ndarray:
    """A 64-bit integer hash, vectorised (uint64 arithmetic wraps)."""
    z = (np.asarray(x, np.uint64) + np.uint64(0x9E3779B97F4A7C15))
    z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    return z ^ (z >> np.uint64(31))


def cell_hash(sid: int, rows: np.ndarray, seed: int) -> np.ndarray:
    """A stable 64-bit hash of each (shard, row), independent of the shard order and of the batch."""
    key = (np.uint64(seed & 0xFFFFFFFF) << np.uint64(32)) ^ np.uint64(sid & 0xFFFFFFFF)
    with np.errstate(over="ignore"):
        return splitmix64(splitmix64(np.full(rows.size, key, np.uint64)) ^ np.asarray(rows, np.uint64))


def unit_rows(shards: list, key_names: list, unit_of_key: dict) -> dict:
    """{unit: [(shard id, training rows of that unit in the shard)]} from the prepass records (train_rows, key)."""
    out = defaultdict(list)
    for sid, s in enumerate(shards):
        tr = np.asarray(s["train_rows"], np.int64)
        if tr.size == 0:
            continue
        units = np.array([unit_of_key[key_names[k]] for k in np.asarray(s["key"])[tr]], dtype=object)
        for u in np.unique(units):
            out[u].append((sid, tr[units == u]))
    return dict(out)


def partition(rows_by_unit: dict, W: int, seed: int) -> list:
    """Per role, {unit: [(shard id, rows)]}: each unit's cells, ordered by cell_hash, dealt to the roles in turn, so the
    roles' subsets of a unit differ by one cell at most (each role draws the same quotas: equal subsets keep the draws
    per cell equal across roles) and do not depend on the order of the shards."""
    parts = [defaultdict(list) for _ in range(W)]
    for u, items in rows_by_unit.items():
        sids = np.concatenate([np.full(rows.size, sid, np.int64) for sid, rows in items])
        rows = np.concatenate([np.asarray(r, np.int64) for _, r in items])
        h = np.concatenate([cell_hash(sid, np.asarray(r, np.int64), seed) for sid, r in items])
        order = np.lexsort((rows, sids, h))
        role = np.empty(order.size, np.int64)
        role[order] = np.arange(order.size) % W
        for w in range(W):
            sel = role == w
            for sid in np.unique(sids[sel]):
                parts[w][u].append((int(sid), np.sort(rows[sel & (sids == sid)])))
    return [dict(p) for p in parts]


class BalancedSampler:
    """The cells of one role: per unit an EpochSampler over the role's cells of that unit; batch(step) takes each unit's
    quota of that global step. Deterministic given (seed, role); a resumed run replays the batches it consumed by
    calling batch() for the earlier steps, which reads no count."""

    def __init__(self, role_units: dict, clock: QuotaClock, buffer: int, seed: int, role: int):
        self.clock = clock
        self.samplers = {}
        for i, u in enumerate(clock.units):
            items = role_units.get(u, [])
            if not items:
                raise ValueError(f"role {role} holds no cell of unit {u}: too many roles for this unit")
            self.samplers[u] = EpochSampler(items, buffer, seed=[seed, 7, role, i])
        self.drawn = Counter()

    def batch(self, step: int):
        q = self.clock.quotas(step)
        out, units = [], []
        for u, n in zip(self.clock.units, q):
            if n:
                cells = self.samplers[u].batch(int(n))
                out.extend(cells)
                units.extend([u] * len(cells))
                self.drawn[u] += len(cells)
        return out, units

    def epochs(self) -> dict:
        """Completed epochs of each unit's sampler (the number of times its cells were all drawn)."""
        return {u: s.epoch - 1 for u, s in self.samplers.items()}
