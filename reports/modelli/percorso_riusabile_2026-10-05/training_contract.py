"""Fail-closed coverage and artifact contract for the next (not legacy) trainer.

The adopted corpus must resolve ALL catalogue records, but only eligible contexts
are supervised. Exclusions require evidence; missing adapters are open blockers.
Call validate_manifest before fitting and validate_exposure before acceptance.
"""
from pathlib import Path
from pipeline_state import sha

ROLES = {'supervision', 'anchor', 'descriptor', 'validation', 'duplicate', 'ineligible'}


def validate_manifest(manifest, catalogue_record_ids):
    records = manifest['catalogue_records']
    ids = [r['record_id'] for r in records]
    if len(ids) != len(set(ids)) or set(ids) != set(catalogue_record_ids):
        raise ValueError('catalogue coverage mismatch')
    contexts = manifest['contexts']
    context_ids = [c['context_id'] for c in contexts]
    if len(context_ids) != len(set(context_ids)):
        raise ValueError('duplicate biological context')
    mapped = set()
    for r in records:
        if r['role'] not in ROLES:
            raise ValueError('unresolved catalogue record: '+r['record_id'])
        if not r.get('evidence'):
            raise ValueError('role lacks evidence')
        if r['role'] in {'validation', 'duplicate', 'ineligible'}:
            if not r.get('reason') or not r.get('review_condition'):
                raise ValueError('unjustified exclusion')
        else:
            refs = r.get('context_ids', [])
            if not refs or not set(refs).issubset(context_ids):
                raise ValueError('eligible source has no complete context mapping')
            mapped.update(refs)
    if mapped != set(context_ids):
        raise ValueError('unmapped context in corpus')
    for c in contexts:
        if c['role'] not in {'supervision', 'anchor', 'descriptor'}:
            raise ValueError('invalid context role')
        if c.get('state') != 'ready' or not c.get('artifacts'):
            raise ValueError('context not ready: '+c['context_id'])
        if not c.get('gene_axis_sha256') or not c.get('source_receipt_sha256'):
            raise ValueError('missing gene/source lineage')
        if c['role'] == 'supervision':
            for field in ('cells_admitted', 'cells_sampled', 'target_count', 'stratum_count'):
                if c.get(field, 0) <= 0:
                    raise ValueError('missing supervision coverage: '+field)
            if c['cells_sampled'] > c['cells_admitted']:
                raise ValueError('sample exceeds admitted population')
    return contexts


def verify_artifacts(contexts, root):
    """Run on the consumer runtime. No downloading, decompression, or rebuild."""
    root = Path(root).resolve()
    checked = {}
    for c in contexts:
        for item in c['artifacts']:
            path = (root/item['path']).resolve()
            if not path.is_relative_to(root):
                raise ValueError('artifact outside mounted root')
            expected = (item['bytes'], item['sha256'])
            if str(path) in checked:
                if checked[str(path)] != expected:
                    raise ValueError('conflicting artifact identity')
                continue
            if path.stat().st_size != expected[0] or sha(path) != expected[1]:
                raise ValueError('mounted artifact changed: '+str(path))
            checked[str(path)] = expected
    return checked


def validate_exposure(contexts, exposure, held_groups=(), hidden_targets=()):
    """Receipt rows come from actual loader reads/loss, not from planned weights.

Targets and strata are exact IDs from the admitted split-specific manifest.
Caller must propagate held_groups/hidden_targets into every derived anchor too.
"""
    if len({e['context_id'] for e in exposure}) != len(exposure):
        raise ValueError('duplicate exposure context')
    expected = {c['context_id']: c for c in contexts if c['group'] not in held_groups}
    observed = {e['context_id']: e for e in exposure}
    if set(expected) != set(observed):
        raise ValueError('missing context or held context consumed')
    for key, c in expected.items():
        e = observed[key]
        targets = set(c['target_ids']) - set(hidden_targets)
        if set(e['target_ids']) != targets:
            raise ValueError('target coverage/leakage mismatch: '+key)
        if c['role'] == 'supervision':
            strata = {s for t, values in c['strata_by_target'].items() if t in targets for s in values}
            if set(e['stratum_ids']) != strata:
                raise ValueError('stratum coverage mismatch: '+key)
            if e['cells_seen_unique'] < c['split_cells_sampled'] or e['loss_weight_sum'] <= 0:
                raise ValueError('supervision not actually consumed: '+key)
            if e['control_cells_seen'] <= 0:
                raise ValueError('controls never consumed: '+key)
        elif e['reads'] <= 0:
            raise ValueError('declared auxiliary role never consumed: '+key)
    return True
