"""Partition frozen selections by raw shard, retaining global row/cell identities."""
from collections import Counter
import json
import os
from pathlib import Path
import shutil
import materialize_samples as original


def select(plans, part, parts):
    if type(part) is not int or type(parts) is not int or not 0 <= part < parts:
        raise ValueError('invalid partition')
    chosen = {fi: cells for fi, cells in plans.items() if fi % parts == part}
    totals = Counter(k for cells in chosen.values() for c in cells.values()
                     for k in c['probabilities'])
    return chosen, dict(totals)


def run(p, root, out):
    part, parts = p['part'], p['parts']
    select({}, part, parts)
    base = original.plan_rows
    identity = {}

    def partition(bank_root, receipt):
        rows, plans, totals = base(bank_root, receipt)
        chosen, local_totals = select(plans, part, parts)
        identity.update(part=part, parts=parts, partition_rule='source_index % parts',
                        source_indices=list(range(part, len(receipt['sources']), parts)),
                        total_sources=len(receipt['sources']), global_levels=totals,
                        complete_unit=False)
        return rows, chosen, local_totals

    original.plan_rows = partition
    try:
        original.run(p, root, out)
    finally:
        original.plan_rows = base
    receipt = out/'complete.json'
    done = json.loads(receipt.read_text())
    done.update(identity)
    receipt.write_text(json.dumps(done, indent=1))


def verify_union(receipts):
    """Reject omissions/duplicates before a consumer treats parts as one unit."""
    if not receipts:
        raise ValueError('no parts')
    first = receipts[0]
    if sorted(r['part'] for r in receipts) != list(range(first['parts'])):
        raise ValueError('missing or duplicate parts')
    keys = ('unit', 'parts', 'bank_receipt_sha256', 'source_verification',
            'genes', 'global_levels', 'total_sources', 'partition_rule')
    sources, totals = [], Counter()
    for r in receipts:
        if not r['complete'] or r['complete_unit'] or any(r[k] != first[k] for k in keys):
            raise ValueError('partition identity mismatch')
        expected = list(range(r['part'], r['total_sources'], r['parts']))
        if r['source_indices'] != expected:
            raise ValueError('partition source mismatch')
        sources.extend(r['source_indices'])
        totals.update(r['levels'])
    if sorted(sources) != list(range(first['total_sources'])) or dict(totals) != first['global_levels']:
        raise ValueError('partition coverage mismatch')
    return dict(totals)


if __name__ == '__main__':
    import psutil
    p = json.loads(Path('params.json').read_text())
    env = {'cpus': os.cpu_count(), 'ram_available': psutil.virtual_memory().available,
           'disk_free': shutil.disk_usage('.').free}
    Path('environment.json').write_text(json.dumps(env))
    print(json.dumps(env), flush=True)
    if env['ram_available'] < 8 << 30 or env['disk_free'] < 19 << 30:
        raise RuntimeError('insufficient resources')
    run(p, Path('/kaggle/input'), Path('/kaggle/working/samples')/p['unit'])
