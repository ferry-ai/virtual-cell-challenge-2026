"""Nested and production anchor contracts; shared pinned input primitives."""
from collections import Counter
import hashlib
import json
import numpy as np
from ammi_inputs_v3 import checked, read_json, module

def load_anchors(contract, completion_pin, locations, fold, genes, panel):
    """Check numeric consumption and exclusions against frozen nested requests."""
    receipt = read_json(completion_pin)
    production = fold.get('mode') == 'production'
    if receipt.get('status') != 'COMPLETE':
        raise ValueError('anchor completion absent')
    if not production and receipt.get('outer_only_reference_parity_verified') is not True:
        raise ValueError('anchor production parity absent')
    requested = {r['id']: r for r in contract['requests']}
    completed = {r['id']: r for r in receipt['requests']}
    if len(completed) != len(receipt['requests']):
        raise ValueError('duplicate anchor receipt')
    if production:
        pairs = contract.get('parity_pairs')
        if not pairs or receipt.get('production_parity_pairs_verified') != pairs:
            raise ValueError('production T0 parity receipt differs')
        for left, right in pairs:
            if completed[left]['effects_sha256'] != completed[right]['effects_sha256']:
                raise ValueError('production T0 parity hash differs')
    needed = {r['anchor_id'] for r in fold['contexts'].values()}
    held = {fold[k] for k in ('outer','inner') if fold.get(k) is not None}
    needed |= {fold['outer_query_anchor']}
    if fold.get('inner_query_anchor'): needed.add(fold['inner_query_anchor'])
    if not needed <= set(requested) or not needed <= set(completed):
        raise ValueError('missing nested anchors')
    result = {}
    for ident in sorted(needed):
        req, done = requested[ident], completed[ident]
        excluded = set(req['excluded_lineages'])
        expected_sources = {s for s, g in contract['source_lineages'].items() if g not in excluded}
        if (not held <= excluded
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
        expected = set(held)
        if info['role'] == 'training': expected.add(info['lineage'])
        if set(requested[info['anchor_id']]['excluded_lineages']) != expected:
            raise ValueError('training row lineage leaked into anchor')
    if fold.get('mode') == 'production':
        if held or set(requested[fold['outer_query_anchor']]['excluded_lineages']):
            raise ValueError('production query requires unchanged full T0')
    return result


def training_data(view, fold, anchors, panel, features, available, locations, input_digest, anchor_digest):
    """Stream panel rows from training-only chunks and select eligible targets by ID hash."""
    genes = view['genes']
    held = {fold[k] for k in ('outer','inner') if fold.get(k) is not None}
    production = fold.get('mode') == 'production'
    if view.get('schema') != 'external-ridge-chunks/1' or view['modality'] != 'CRISPRi':
        raise ValueError('frozen CRISPRi response view required')
    if production:
        if held or view['regime'] != 'production' or view['excluded_contexts'] or view['excluded_targets']:
            raise ValueError('production view must declare all admitted rows and no held fold')
    elif (view['regime'] != 'C' or fold['no_final_refit'] is not True
          or fold['outer'] not in view['excluded_contexts']):
        raise ValueError('frozen C response view required')
    panel_pos = {t: i for i, t in enumerate(panel)}
    rows, consumed = {}, []
    for chunk in view['chunks']:
        context = chunk['context_id']
        info = fold['contexts'][context]
        # No path lookup or array read is allowed for either held lineage.
        if info['lineage'] in held:
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
        if hasattr(locations, 'release'): locations.release(chunk['sha256'])
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
