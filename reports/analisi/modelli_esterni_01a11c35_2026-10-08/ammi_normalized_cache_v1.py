"""Bounded CPU cache of immutable normalized inputs, never learned embeddings."""
from collections import OrderedDict
import time
import numpy as np


class NormalizedBlockCache:
    def __init__(self, max_bytes, max_entries=128):
        if max_bytes < 0 or max_entries < 1:
            raise ValueError('invalid normalization cache bounds')
        self.max_bytes, self.max_entries = int(max_bytes), int(max_entries)
        self.entries = OrderedDict()
        self.resident = self.peak = 0
        self.hits = self.misses = self.evictions = self.bypasses = 0
        self.loader_seconds = self.copy_seconds = 0.0

    def fetch(self, namespace, start, stop, loader):
        key = namespace, int(start), int(stop)
        if key in self.entries:
            self.hits += 1
            values, masks = self.entries.pop(key)
            self.entries[key] = values, masks
            begun = time.perf_counter()
            # Isolated writable outputs preserve the old caller contract. The
            # retained arrays remain read-only even if a caller mutates its copy.
            result = values.copy(), masks.copy()
            self.copy_seconds += time.perf_counter() - begun
            return result
        self.misses += 1
        begun = time.perf_counter()
        values, masks = loader(start, stop)
        self.loader_seconds += time.perf_counter() - begun
        if values.dtype != np.float32 or masks.dtype != bool or values.shape != masks.shape:
            raise ValueError('normalized input dtype or mask differs')
        size = values.nbytes + masks.nbytes
        if size > self.max_bytes or self.max_bytes == 0:
            self.bypasses += 1
            return values, masks
        while self.entries and (self.resident + size > self.max_bytes or len(self.entries) >= self.max_entries):
            _, (old_values, old_masks) = self.entries.popitem(last=False)
            self.resident -= old_values.nbytes + old_masks.nbytes
            self.evictions += 1
        begun = time.perf_counter()
        frozen_values, frozen_masks = values.copy(), masks.copy()
        frozen_values.flags.writeable = False
        frozen_masks.flags.writeable = False
        self.entries[key] = frozen_values, frozen_masks
        self.copy_seconds += time.perf_counter() - begun
        self.resident += size
        self.peak = max(self.peak, self.resident)
        return values, masks

    def stats(self):
        return dict(kind='CPU immutable normalized float32 values and boolean masks only',
            max_payload_bytes=self.max_bytes, max_entries=self.max_entries,
            resident_payload_bytes=self.resident, peak_payload_bytes=self.peak,
            entries=len(self.entries), hits=self.hits, misses=self.misses,
            evictions=self.evictions, bypasses=self.bypasses,
            loader_seconds=self.loader_seconds, copy_seconds=self.copy_seconds,
            learned_embeddings_cached=False, disk_cache=False, selection_changed=False)


class CachedControl:
    def __init__(self, control, cache):
        self.control, self.cache = control, cache
        self.shape = control.shape
        self.namespace = object()

    def __len__(self):
        return self.shape[0]

    def batch(self, start, stop):
        if not 0 <= start < stop <= self.shape[0]:
            raise ValueError('invalid NTC block')
        return self.cache.fetch(self.namespace, start, stop, self.control.batch)


class CachedControlMap(dict):
    def __init__(self, controls, cache):
        super().__init__((key, CachedControl(control, cache)) for key, control in controls.items())
        self.cache = cache


def stage_controls_cached(*args, **kwargs):
    from ammi_controls_v4 import stage_controls, available_memory
    controls, audit = stage_controls(*args, **kwargs)
    available = available_memory()
    budget = min(512 << 20, available // 8)
    cache = NormalizedBlockCache(budget)
    audit = dict(audit, normalization_cache_policy=dict(
        available_RAM_after_staging=available, payload_budget_bytes=budget,
        max_entries=cache.max_entries, fraction_of_available_RAM=0.125,
        maximum_payload_bytes=512 << 20, learned_embeddings_cached=False,
        same_reader=True, same_selected_cells=True, same_block_order=True))
    return CachedControlMap(controls, cache), audit
