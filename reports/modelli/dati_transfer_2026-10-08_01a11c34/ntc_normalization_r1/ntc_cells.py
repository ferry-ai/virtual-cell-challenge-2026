"""Cloud NTC extraction: native depth, per-cell masks, stratified bottom hashes.

No target response is used for selection or normalization. Run one pinned bank
part at a time; merge storage parts by the same priority before fitting. Real
data execution belongs on cloud CPU. No network, credentials, or model fitting.
"""
from collections import Counter, defaultdict
import csv
import hashlib
import heapq
import json
from pathlib import Path

import h5py
import numpy as np
import scipy.sparse as sp

BIO = ('study', 'context', 'donor_or_clone', 'condition', 'modality', 'chemistry')
STRATA = ('library', 'batch', 'guides')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as src:
        for block in iter(lambda: src.read(8 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def checked(path, spec):
    path = Path(path)
    if (spec.get('bytes') is not None and path.stat().st_size != spec['bytes']) or sha(path) != spec['sha256']:
        raise ValueError('pinned input changed: ' + path.name)
    return path


def column(group, name, n=None):
    if name not in group:
        if name in ('batch', 'chemistry') and n is not None:
            return np.full(n, 'MISSING', dtype=object)
        raise ValueError('missing source column: ' + name)
    return column_value(group[name])


def column_value(value):
    """Decode AnnData arrays, categoricals and nullable arrays, failing closed."""
    if isinstance(value, h5py.Group):
        if set(value.keys()) == {'values', 'mask'}:
            values = column_value(value['values'])
            mask = value['mask'][:]
            if mask.dtype.kind != 'b' or mask.shape != values.shape:
                raise ValueError('invalid nullable mask: ' + value.name)
            if mask.any():
                if values.dtype.kind not in 'OUS':
                    raise ValueError('missing numeric source value: ' + value.name)
                values = values.astype(object)
                values[mask] = 'MISSING'
            return values
        if set(value.keys()) == {'categories', 'codes'}:
            cats = column_value(value['categories'])
            codes = value['codes'][:]
            if codes.ndim != 1 or codes.dtype.kind not in 'iu' or np.any((codes < -1) | (codes >= len(cats))):
                raise ValueError('categorical code out of bounds')
            return np.asarray([cats[c] if c >= 0 else 'MISSING' for c in codes])
        raise ValueError('unsupported source column: ' + value.name + ' keys=' + repr(sorted(value.keys())))
    if value.ndim != 1:
        raise ValueError('source column must be one-dimensional: ' + value.name)
    return value.asstr()[:] if value.dtype.kind in 'OS' else value[:]


def gene_mapping(h5, genes):
    var = h5['var']
    indices = column(var, 'official_index').astype(int)
    measured = column(var, 'measured')
    if measured.dtype.kind not in 'biu' or not np.isin(measured, [0, 1]).all():
        raise ValueError('measurement mask must be boolean')
    ok = ((indices >= 0) & (indices < len(genes)) & measured.astype(bool)
          & (column(var, 'mapping').astype(str) == 'unique'))
    counts = np.bincount(indices[ok], minlength=len(genes))
    ok &= counts[np.clip(indices, 0, len(genes)-1)] == 1
    symbols = column(var, 'symbol').astype(str)
    if np.any(symbols[ok] != np.asarray(genes)[indices[ok]]):
        raise ValueError('native mapping differs from frozen axis')
    mapped = np.where(ok, indices, -1)
    mask = np.bincount(mapped[ok], minlength=len(genes)).astype(bool)
    return mapped, mask


def selection(plan, locations, rows_path):
    """Metadata pass only. 64 per biological stratum, not old level-64 total."""
    checked(rows_path, plan['rows'])
    with Path(rows_path).open(encoding='utf-8', newline='') as src:
        bank_rows = list(csv.DictReader(src))
    allowed = {}
    for record in plan['controls']:
        row = bank_rows[record['bank_row']]
        if row['target'] != 'NTC':
            raise ValueError('control plan contains perturbed bank row')
        key = tuple(row[name] for name in BIO)
        if key in allowed and allowed[key]['context_id'] != record['context_id']:
            raise ValueError('ambiguous context assignment')
        allowed[key] = {**record, 'identity': dict(zip(BIO, key))}
    cap = plan['cells_per_stratum']
    if not isinstance(cap, int) or cap < 1:
        raise ValueError('invalid stratum cap')
    heaps, population, seen = defaultdict(list), Counter(), set()
    for source in plan['sources']:
        path = checked(locations[source['sha256']], source)
        with h5py.File(path, 'r') as h5:
            n = int(h5['X'].attrs['shape'][0])
            if n != source['cells']:
                raise ValueError('source cell count differs')
            columns = {name: column(h5['obs'], name, n).astype(str)
                       for name in (*BIO, *STRATA, 'cell_key', 'control_kind')}
            if any(len(v) != n for v in columns.values()):
                raise ValueError('metadata length differs')
            for i in np.flatnonzero(columns['control_kind'] == 'NTC'):
                identity = tuple(columns[name][i] for name in BIO)
                record = allowed.get(identity)
                if record is None:
                    continue
                stratum = tuple(columns[name][i] for name in STRATA)
                group = (record['context_id'], identity, stratum)
                cell_key = columns['cell_key'][i]
                unique = (group, cell_key)
                if unique in seen:
                    raise ValueError('duplicate NTC identity; source deduplication required')
                seen.add(unique)
                priority = hashlib.sha256(json.dumps(
                    [plan['seed'], group, cell_key], ensure_ascii=False,
                    separators=(',', ':')).encode()).hexdigest()
                item = (-int(priority, 16), cell_key, source['sha256'], int(i))
                heap = heaps[group]
                population[group] += 1
                if len(heap) < cap:
                    heapq.heappush(heap, item)
                elif item > heap[0]:
                    heapq.heapreplace(heap, item)
    actual = Counter()
    for group, count in population.items():
        actual[group[1]] += count
    for identity, record in allowed.items():
        if actual[identity] != record['expected_cells']:
            raise ValueError('NTC population differs from pinned bank: ' + record['context_id'])
    output = []
    for group in sorted(heaps):
        for neg_priority, cell_key, digest, row in sorted(heaps[group], reverse=True):
            output.append(dict(context_id=group[0], identity=dict(zip(BIO, group[1])),
                stratum=list(group[2]), cell_key=cell_key, source_sha256=digest,
                source_row=row, priority=f'{-neg_priority:064x}',
                stratum_population=population[group], selected_in_stratum=len(heaps[group]),
                inclusion_probability=len(heaps[group])/population[group]))
    if not output:
        raise ValueError('no selected NTC cells')
    return output


def extract(plan, locations, selected):
    """Read only selected NTC RNA rows and normalize on ingestion native depth."""
    genes = plan['genes']
    counts, depths, mask_values, mask_indices = [], [], [], []
    grouped = defaultdict(list)
    for index, record in enumerate(selected):
        grouped[record['source_sha256']].append((index, record))
    order = []
    specs = {s['sha256']: s for s in plan['sources']}
    for digest, records in sorted(grouped.items()):
        path = checked(locations[digest], specs[digest])
        with h5py.File(path, 'r') as h5:
            mapping, mask = gene_mapping(h5, genes)
            mask_index = len(mask_values)
            mask_values.append(mask)
            # This field is retained by ingestion before official-axis mapping.
            native_depth = column(h5['obs'], 'depth_native').astype(float)
            kind = column(h5['obs'], 'control_kind').astype(str)
            keys = column(h5['obs'], 'cell_key').astype(str)
            x = h5['X']
            if int(x.attrs['shape'][1]) != len(mapping):
                raise ValueError('native count axis differs')
            for index, record in records:
                row = record['source_row']
                if kind[row] != 'NTC' or keys[row] != record['cell_key']:
                    raise ValueError('selection resolves to a different or perturbed cell')
                lo, hi = map(int, x['indptr'][row:row+2])
                values = x['data'][lo:hi].astype(float)
                cols = x['indices'][lo:hi].astype(int)
                if (not np.isfinite(values).all() or (values < 0).any()
                        or not np.equal(values, np.floor(values)).all()):
                    raise ValueError('invalid raw NTC counts')
                if (cols < 0).any() or (cols >= len(mapping)).any():
                    raise ValueError('raw sparse index out of bounds')
                depth = native_depth[row]
                if not np.isfinite(depth) or depth <= 0 or depth + .5 < values.sum():
                    raise ValueError('native depth invalid or below full source row sum')
                good = mapping[cols] >= 0
                counts.append(sp.csr_matrix((values[good], (np.zeros(good.sum(), int), mapping[cols[good]])),
                                            shape=(1, len(genes))))
                depths.append(depth)
                mask_indices.append(mask_index)
                order.append(index)
    inverse = np.argsort(order)
    return dict(counts=sp.vstack(counts, format='csr')[inverse],
                native_depth=np.asarray(depths)[inverse], masks=np.asarray(mask_values),
                mask_index=np.asarray(mask_indices)[inverse], metadata=selected,
                quantity='raw UMI on official axis; denominator is ingestion obs/depth_native',
                perturbed_RNA_rows_read=0)


def normalized_batch(bundle, indices):
    counts = bundle['counts'][indices].toarray().astype(np.float32)
    mask = bundle['masks'][bundle['mask_index'][indices]]
    depth = bundle['native_depth'][indices]
    value = np.log1p(counts * (10000. / depth[:, None])).astype(np.float32)
    value[~mask] = 0.
    return value, mask


def merge_candidates(records, cap=64):
    """Merge disjoint storage-part reservoirs with identical priority rules."""
    groups = defaultdict(list)
    seen = set()
    for r in records:
        group = (r['context_id'], tuple(r['identity'][name] for name in BIO), tuple(r['stratum']))
        key = (group, r['cell_key'])
        if key in seen:
            raise ValueError('duplicate candidates; H1 must use the pinned canonical train control source')
        seen.add(key)
        groups[group].append(r)
    merged = []
    for group, values in sorted(groups.items()):
        # Each local population is repeated on each selected record. Part identity
        # is assigned by the orchestrating runner, not inferred from a source shard.
        populations = {}
        for r in values:
            key = r['part_id']
            if populations.setdefault(key, r['stratum_population']) != r['stratum_population']:
                raise ValueError('inconsistent part population')
        total = sum(populations.values())
        chosen = sorted(values, key=lambda r:(r['priority'], r['cell_key']))[:cap]
        merged.extend({**r, 'stratum_population':total, 'selected_in_stratum':len(chosen),
                       'inclusion_probability':len(chosen)/total} for r in chosen)
    return merged
