"""Fold-safe full-population moments and nested stratified samples for the simple hybrid.

Inputs are ADMITTED cells on a previously reconciled common measured axis. This module
does not perform QC, resolve aliases, certify the catalogue, or treat missing genes as zero.
The caller must supply the complete source manifest and canonical target/line identities.
"""
from collections import Counter, defaultdict
import hashlib
import heapq
import json

import numpy as np

BIO = ('study', 'context', 'donor_or_clone', 'condition', 'modality', 'chemistry')
STRATA = ('library', 'batch', 'guides')


def key(record, columns):
    return tuple(str(record.get(c, 'MISSING')) for c in columns)


def digest(value, seed):
    raw = json.dumps([seed, value], ensure_ascii=False, separators=(',', ':'))
    return int.from_bytes(hashlib.sha256(raw.encode()).digest(), 'big')


def admit_to_fit(record, held_groups, hidden_targets, protected_sources=()):
    """Reject every held-line response/control and globally hidden perturbation target.

    Controls of an outer held line are reserved for inference and are not fit inputs.
    A compound's canonical component list must already have been resolved upstream.
    """
    for name in ('line_group', 'target', 'study', 'cell_key'):
        if not record.get(name) or record[name] == 'MISSING':
            raise ValueError(f'missing canonical {name}')
    if record['line_group'] in set(held_groups) or record['study'] in set(protected_sources):
        return False
    parts = set(record.get('target_components', [record['target']]))
    return not bool(parts & set(hidden_targets))


class NestedSampler:
    """Bottom-hash reservoir per biological unit/target/library/batch/guide.

    Round-robin across strata, then take nested prefixes. If a level cannot represent
    all strata, raise its cap to their count and record the exception. Memory scales
    with retained candidates, not all cell metadata. Probabilities describe this
    stratified design; no inverse-probability weights are silently applied to loss.
    """
    def __init__(self, levels=(32, 64, 128), seed=20261004):
        self.levels = tuple(sorted(set(levels)))
        if not self.levels or any(not isinstance(n, int) or n < 1 for n in self.levels):
            raise ValueError('levels must be positive integers')
        self.seed = seed
        self.heaps = defaultdict(list)
        self.counts = Counter()
        self.retained_ids = defaultdict(set)

    def add(self, record, locator):
        if not record.get('cell_key'):
            raise ValueError('cell_key is required')
        unit = (*key(record, BIO), str(record['target']))
        stratum = key(record, STRATA)
        k = (unit, stratum)
        ident = str(record['cell_key'])
        if ident in self.retained_ids[k]:
            raise ValueError('duplicate retained identity; deduplicate inputs before sampling')
        priority = digest((unit, stratum, ident), self.seed)
        item = (-priority, ident, str(locator))
        self.counts[k] += 1
        h = self.heaps[k]
        if len(h) < self.levels[-1]:
            heapq.heappush(h, item)
            self.retained_ids[k].add(ident)
        elif item > h[0]:
            old = heapq.heapreplace(h, item)
            self.retained_ids[k].remove(old[1])
            self.retained_ids[k].add(ident)

    def finish(self):
        units = defaultdict(dict)
        for (unit, stratum), h in self.heaps.items():
            units[unit][stratum] = sorted(h, key=lambda x: (-x[0], x[1]))
        answer = []
        for unit in sorted(units):
            strata = sorted(units[unit], key=lambda s: (digest(s, self.seed), s))
            queues = units[unit]
            interleaved = [(s, item) for j in range(self.levels[-1]) for s in strata
                           for item in queues[s][j:j + 1]]
            n = sum(self.counts[(unit, s)] for s in strata)
            levels = {}
            for level in self.levels:
                chosen = interleaved[:max(level, len(strata))]
                ns = Counter(s for s, _ in chosen)
                levels[str(level)] = {
                    'requested': level, 'effective_cap': max(level, len(strata)),
                    'raised_to_preserve_strata': len(strata) > level,
                    'cells': [{'cell_key': item[1], 'locator': item[2], 'stratum': list(s),
                               'inclusion_probability': ns[s] / self.counts[(unit, s)]}
                              for s, item in chosen]}
                if not chosen or set(ns) != set(strata):
                    raise AssertionError('sampling lost a stratum')
            answer.append({'context': dict(zip(BIO, unit[:-1])), 'target': unit[-1],
                           'admitted': n, 'strata': len(strata), 'levels': levels})
        return answer


class Moments:
    """Mergeable moments of per-cell proportions, computed BEFORE sampling.

    Raw count sums, sums of proportions and means of logarithms are distinct.
    `mask` is the already reconciled intersection for this stratum. We normalise
    each cell on that mask; inputs with incompatible masks cannot be merged.
    """
    def __init__(self, mask):
        self.mask = np.asarray(mask, bool).copy()
        if self.mask.ndim != 1 or not self.mask.any():
            raise ValueError('empty or non-vector measured axis')
        self.n = 0
        self.count_sum = np.zeros(len(self.mask), np.float64)
        self.prop_sum = np.zeros(len(self.mask), np.float64)
        self.prop_sq_sum = np.zeros(len(self.mask), np.float64)
        self.detected = np.zeros(len(self.mask), np.int64)

    def update(self, counts):
        x = np.asarray(counts, np.float64)
        if x.ndim != 2 or x.shape[1] != len(self.mask):
            raise ValueError('counts/axis mismatch')
        # Unmeasured columns do not enter either validation or denominators.
        x = np.where(self.mask, x, 0)
        if not np.isfinite(x).all() or (x < 0).any():
            raise ValueError('invalid admitted counts')
        den = x.sum(1)
        if (den <= 0).any():
            raise ValueError('zero-depth row must be resolved by QC before aggregation')
        p = x / den[:, None]
        self.n += len(x)
        self.count_sum += x.sum(0)
        self.prop_sum += p.sum(0)
        self.prop_sq_sum += (p * p).sum(0)
        self.detected += (x > 0).sum(0)

    def merge(self, other):
        if not np.array_equal(self.mask, other.mask):
            raise ValueError('incompatible measured axes: reconcile before aggregating')
        self.n += other.n
        for name in ('count_sum', 'prop_sum', 'prop_sq_sum', 'detected'):
            getattr(self, name)[:] += getattr(other, name)
        return self

    def summary(self):
        if not self.n:
            raise ValueError('no admitted cells')
        mean = self.prop_sum / self.n
        var = (np.maximum(self.prop_sq_sum - self.n * mean ** 2, 0) / (self.n - 1)
               if self.n > 1 else np.full_like(mean, np.nan))
        return {'n': self.n, 'mask': self.mask.copy(),
                'count_sum': np.where(self.mask, self.count_sum, np.nan),
                'mean_proportion': np.where(self.mask, mean, np.nan),
                'variance_proportion': np.where(self.mask, var, np.nan),
                'zero_fraction': np.where(self.mask, 1 - self.detected / self.n, np.nan)}


def require_coverage(expected_contexts, observed_contexts, exclusions):
    """Require an explicit catalogue reconciliation; exclusions must have evidence."""
    missing = set(expected_contexts) - set(observed_contexts)
    unknown = set(observed_contexts) - set(expected_contexts)
    justified = {c for c, reason in exclusions.items() if reason.get('evidence') and
                 reason.get('kind') in {'validation', 'duplicate', 'quality', 'incompatible', 'access'}}
    if unknown or missing - justified:
        raise ValueError(f'coverage gap: missing={sorted(missing - justified)}, unknown={sorted(unknown)}')
    return {'expected': len(set(expected_contexts)), 'observed': len(set(observed_contexts)),
            'excluded': sorted(missing & justified), 'complete': True}


def hierarchical_weights(records):
    """Weights for UNIFORM row sampling with a fixed batch denominator.

    Equal mass to line families, studies within a family, biological contexts within
    a study, targets within a context and replicate/guide rows within a target.
    Population cell counts do not increase a context's training mass.
    """
    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    for i, r in enumerate(records):
        tree[r['line_group']][r['study']][key(r, BIO)][r['target']].append(i)
    if not records:
        raise ValueError('empty training rows')
    w = np.zeros(len(records), np.float64)
    for studies in tree.values():
        for contexts in studies.values():
            for targets in contexts.values():
                for ids in targets.values():
                    w[ids] = len(records) / (len(tree) * len(studies) * len(contexts) * len(targets) * len(ids))
    return w
