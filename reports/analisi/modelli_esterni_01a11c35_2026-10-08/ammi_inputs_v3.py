"""Hash-pinned biological input boundary for the AMMI panel pilot.

No networking or job launch. Only mounted, explicitly pinned artifacts are read.
Real callers run in cloud; tests use small synthetic arrays. Outer and inner
response chunks are rejected before resolving paths or reading numeric arrays.
"""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import scipy.sparse as sp

from pie_adapter import sha256


def checked(spec):
    path = Path(spec['path'])
    digest = spec['sha256']
    if (len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)
            or path.stat().st_size != spec['bytes'] or sha256(path) != digest):
        raise ValueError('input pin differs: ' + path.name)
    return path


def read_json(spec):
    return json.loads(checked(spec).read_text(encoding='utf-8'))


def module(spec, name):
    path = checked(spec)
    definition = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(loaded)
    return loaded


def load_ntc(parts, genes, expected_contexts, reader_pin, expected_parts):
    """Validate DATI outputs, globally merge reservoirs, then normalize each cell."""
    reader = module(reader_pin, 'ammi_pinned_ntc_reader')
    candidates, bundles, used = [], {}, []
    for spec in parts:
        receipt = read_json(spec['completion'])
        root = Path(spec['completion']['path']).parent
        part = receipt['part_id']
        if (receipt.get('schema') != 'native-NTC-extraction-completion/1'
                or receipt.get('status') != 'COMPLETE' or part in bundles
                or expected_parts.get(part) != spec['plan_sha256']
                or receipt['plan_sha256'] != spec['plan_sha256']
                or receipt['perturbed_RNA_rows_read'] != 0
                or receipt['code']['ntc_cells.py'] != reader_pin['sha256']
                or receipt['normalized_scale'] != 'log1p(counts * 10000 / native_depth)'):
            raise ValueError('unverified NTC extraction')
        files = receipt['files']
        for name in ('counts.npz', 'axes_depth_mask.npz', 'cells.json'):
            checked(dict(files[name], path=str(root/name)))
        records = json.loads((root/'cells.json').read_text(encoding='utf-8'))
        counts = sp.load_npz(root/'counts.npz').tocsr()
        with np.load(root/'axes_depth_mask.npz', allow_pickle=False) as source:
            if source['genes'].tolist() != list(genes):
                raise ValueError('NTC gene axis differs')
            bundle = {k: source[k] for k in ('native_depth', 'masks', 'mask_index')}
        depth, masks, index = (bundle[k] for k in ('native_depth', 'masks', 'mask_index'))
        n = len(records)
        if (counts.shape != (n, len(genes)) or list(counts.shape) != receipt['arrays_shape']
                or depth.shape != (n,) or masks.ndim != 2 or masks.shape[1] != len(genes)
                or masks.dtype != bool or index.shape != (n,) or index.dtype.kind not in 'iu'
                or np.any(index < 0) or np.any(index >= len(masks))
                or not np.isfinite(depth).all() or np.any(depth <= 0)
                or not np.isfinite(counts.data).all() or np.any(counts.data < 0)
                or not np.equal(counts.data, np.floor(counts.data)).all()
                or np.any(np.asarray(counts.sum(1)).ravel() > depth + .5)):
            raise ValueError('invalid NTC counts, masks, or native depth')
        if dict(Counter(r['context_id'] for r in records)) != receipt['contexts']:
            raise ValueError('NTC metadata coverage differs')
        coo = counts.tocoo()
        if np.any(~masks[index[coo.row], coo.col] & (coo.data != 0)):
            raise ValueError('NTC values outside measured support')
        for i, record in enumerate(records):
            if record['part_id'] != part:
                raise ValueError('NTC storage part identity differs')
            candidates.append(dict(record, _row=i))
        bundles[part] = dict(bundle, counts=counts)
        used.append(spec['completion']['sha256'])
    if set(bundles) != set(expected_parts):
        raise ValueError('NTC storage part coverage differs')
    merged = reader.merge_candidates(candidates, cap=64)
    actual = set(r['context_id'] for r in merged)
    if actual != set(expected_contexts):
        raise ValueError('NTC coverage differs from frozen context set')
    controls, audit = {}, {}
    for context in sorted(actual):
        records = [r for r in merged if r['context_id'] == context]
        values, masks = [], []
        for part in sorted({r['part_id'] for r in records}):
            ids = [r['_row'] for r in records if r['part_id'] == part]
            value, mask = reader.normalized_batch(bundles[part], ids)
            if not mask.any(1).all() or not np.isfinite(value).all():
                raise ValueError('empty or nonfinite normalized NTC')
            values.append(value); masks.append(mask)
        controls[context] = (np.concatenate(values), np.concatenate(masks))
        audit[context] = dict(cells=len(records), cells_before_global_merge=sum(
            r['context_id'] == context for r in candidates),
            selection_sha256=hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest())
    return controls, dict(completions=used, contexts=audit, global_reservoir_cap=64,
                         normalized_scale='log1p(counts * 10000 / native_depth)', complete_D053=False)


def load_anchors(contract, completion_pin, locations, fold, genes, panel):
    """Check numeric consumption and exclusions against frozen nested requests."""
    receipt = read_json(completion_pin)
    if (receipt.get('status') != 'COMPLETE'
            or receipt.get('outer_only_reference_parity_verified') is not True):
        raise ValueError('anchor production parity absent')
    requested = {r['id']: r for r in contract['requests']}
    completed = {r['id']: r for r in receipt['requests']}
    if len(completed) != len(receipt['requests']):
        raise ValueError('duplicate anchor receipt')
    needed = {r['anchor_id'] for r in fold['contexts'].values()}
    needed |= {fold['inner_query_anchor'], fold['outer_query_anchor']}
    if not needed <= set(requested) or not needed <= set(completed):
        raise ValueError('missing nested anchors')
    result = {}
    for ident in sorted(needed):
        req, done = requested[ident], completed[ident]
        excluded = set(req['excluded_lineages'])
        expected_sources = {s for s, g in contract['source_lineages'].items() if g not in excluded}
        if (not {fold['outer'], fold['inner']} <= excluded
                or set(req['sources']) != expected_sources
                or set(done['excluded_lineages']) != excluded
                or done['consumed'] != req['expected_cache_sha256']
                or locations[ident]['sha256'] != done['effects_sha256']):
            raise ValueError('anchor source/exclusion consumption differs')
        with np.load(checked(locations[ident]), allow_pickle=False) as source:
            values = {k: source[k] for k in ('targets', 'genes', 'lfc', 'observed')}
        a, mask = values['lfc'], values['observed']
        if (values['targets'].tolist() != list(panel) or values['genes'].tolist() != list(genes)
                or a.shape != (len(panel), len(genes)) or mask.shape != a.shape
                or a.dtype != np.float32 or mask.dtype != bool or not np.isfinite(a).all()
                or np.any(a[~mask] != 0)):
            raise ValueError('anchor stage100 axes/support differ')
        result[ident] = values
    for info in fold['contexts'].values():
        expected = {fold['outer'], fold['inner']}
        if info['role'] == 'training': expected.add(info['lineage'])
        if set(requested[info['anchor_id']]['excluded_lineages']) != expected:
            raise ValueError('training row lineage leaked into anchor')
    return result


def training_data(view, fold, anchors, panel, features, available, locations, input_digest, anchor_digest):
    """Stream panel rows from training-only chunks and select eligible targets by ID hash."""
    genes = view['genes']
    if (view.get('schema') != 'external-ridge-chunks/1' or view['modality'] != 'CRISPRi'
            or view['regime'] != 'C' or fold['no_final_refit'] is not True
            or fold['outer'] not in view['excluded_contexts']):
        raise ValueError('frozen C response view required')
    panel_pos = {t: i for i, t in enumerate(panel)}
    rows, consumed = {}, []
    for chunk in view['chunks']:
        context = chunk['context_id']
        info = fold['contexts'][context]
        # No path lookup or array read is allowed for either held lineage.
        if info['lineage'] in {fold['outer'], fold['inner']}:
            if info['lineage'] == fold['outer']: raise ValueError('outer response in frozen view')
            continue
        if info['role'] != 'training' or chunk.get('protected', False):
            raise ValueError('invalid training role')
        selected = [(i, panel_pos[t]) for i, t in enumerate(chunk['targets'])
                    if t in panel_pos and available[panel_pos[t]]]
        if not selected: continue
        spec = dict(chunk, path=locations[chunk['sha256']])
        with np.load(checked(spec), allow_pickle=False) as source:
            if (source['genes'].tolist() != genes or source['targets'].tolist() != chunk['targets']
                    or json.loads(str(source['meta'].item())) != chunk['identity']):
                raise ValueError('response chunk axes/identity differ')
            y, mask = source[view['effect_field']], source['mask']
        if (y.dtype != np.float32 or mask.dtype != bool or y.shape != (len(chunk['targets']), len(genes))
                or mask.shape != y.shape or not np.isfinite(y[mask]).all() or not np.isnan(y[~mask]).all()):
            raise ValueError('response chunk support differs')
        consumed.append(chunk['sha256'])
        anchor = anchors[info['anchor_id']]
        for source_row, target_row in selected:
            support = mask[source_row] & anchor['observed'][target_row]
            if not support.any(): continue
            target = panel[target_row]
            key = (context, target)
            if key in rows: raise ValueError('duplicate response context/target')
            rows[key] = (target_row, y[source_row].copy(), support.copy())
    chosen, coverage = [], {}
    for context, info in sorted(fold['contexts'].items()):
        if info['role'] != 'training': continue
        eligible = sorted((t for c, t in rows if c == context), key=lambda t: (
            hashlib.sha256(json.dumps(['esm2-ammi-pilot-r1', context, t], separators=(',', ':')).encode()).hexdigest(), t))
        targets = eligible[:64]
        coverage[context] = dict(lineage=info['lineage'], eligible=len(eligible), selected=len(targets),
                                 gap=None if targets else 'no panel target with ESM2 and common response/anchor support')
        chosen.extend((context, t) for t in targets)
    if not chosen: raise ValueError('empty panel training set')
    ids = [rows[key][0] for key in chosen]
    data = dict(contexts=[c for c, t in chosen], lineages=[fold['contexts'][c]['lineage'] for c, t in chosen],
        row_ids=[json.dumps(key, separators=(',', ':')) for key in chosen], features=features[ids].astype(np.float32),
        response=np.stack([rows[key][1] for key in chosen]), observed=np.stack([rows[key][2] for key in chosen]),
        anchor=np.stack([anchors[fold['contexts'][c]['anchor_id']]['lfc'][i] for (c, t), i in zip(chosen, ids)]),
        input_receipt_sha256=input_digest, anchor_receipt_sha256=anchor_digest)
    return data, dict(contexts=coverage, consumed_chunks=consumed, outer_response_arrays_read=0,
                      inner_response_arrays_used_for_fit=0, complete_D053=False)
