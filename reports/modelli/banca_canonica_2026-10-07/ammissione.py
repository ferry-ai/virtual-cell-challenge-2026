"""Apply the registered admission rule to the verified derivation receipts and fetch the tables.

    ammissione.py <out.json> <tables_dir>

The rule is PROTOCOLLO.md, written before any receipt was read: it is applied here as code and
is not tuned. Tables (small npz) are fetched once to the data root and matched to the sha256
their own runtime receipt declares; a table that does not match is refused.
"""
import json
import sys
from pathlib import Path

import percorso as P

HIPSCI = P.REUSE / 'hipsci_adapter_r3/completion_r1'
HIPSCI_QC = P.REUSE / 'hipsci_qc_r1/completion_r1'


def latest(name):
    """The one verified completion of a source; two verified revisions would be ambiguous."""
    done = sorted((P.HERE / 'derivazioni' / name).glob('*/completion/verification.json'))
    if len(done) != 1:
        raise ValueError('expected one verified completion for %s, found %d' % (name, len(done)))
    return done[0].parent


def knockdown(contexts):
    values = [o['raw'] for c in contexts for o in c['own_gene'] if o['state'] == 'measured']
    values.sort()
    n = len(values)
    median = None if not n else (values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2)
    return dict(measured=n, median_own_raw=median,
                fraction_negative=None if not n else sum(v < 0 for v in values) / n)


def fetch(job, pattern, out):
    owner = job.split('/')[0]
    out.mkdir(parents=True, exist_ok=True)
    rc, answer = P.call(owner, ['kernels', 'output', job, '-p', str(out), '--file-pattern', pattern])
    if rc:
        raise ValueError('table retrieval failed: ' + job)


def main():
    out, tables = Path(sys.argv[1]), Path(sys.argv[2])
    document = P.specs()
    sources = {}
    for name, spec in document['sources'].items():
        folder = latest(name)
        verification = json.loads((folder / 'verification.json').read_text(encoding='utf-8'))
        receipt = json.loads((folder / 'fit_receipt.json').read_text(encoding='utf-8'))
        kd = knockdown(receipt['contexts'])
        table = name + '.npz'
        target = tables / name
        fetch(verification['job'], r'\.npz$', target)
        files = {}
        for filename, pin in receipt['outputs'].items():
            path = target / filename
            if P.pin(path) != pin:
                raise ValueError('fetched table differs from its runtime receipt: ' + filename)
            files[filename] = dict(pin, path=path.as_posix())
        record = dict(arm=spec['arm'], study=spec['study'], modality=spec['modality'], units=spec['units'],
                      job=verification['job'], version=verification['version'],
                      receipt=dict(P.pin(folder / 'fit_receipt.json'), path=(folder / 'fit_receipt.json').relative_to(P.REPO).as_posix()),
                      table=dict(files[table], name=table), context_tables=sorted(set(files) - {table}),
                      targets=receipt['targets'], target_cells=int(sum(receipt['n_cells'])),
                      control_cells=int(sum(c['control_cells'] for c in receipt['contexts'])),
                      contexts=[c['context'] for c in receipt['contexts']], aggregation=receipt['aggregation'],
                      knockdown=kd, cells_by_role={i['unit']: i['cells_by_role'] for i in receipt['inventory']},
                      comparison={k: v for k, v in (receipt.get('comparison') or {}).items() if k != 'per_target'} or None,
                      caveat=spec.get('caveat'))
        if spec['arm'] == 'crispri':
            passed = bool(receipt['targets']) and kd['median_own_raw'] is not None and kd['median_own_raw'] < 0
            record.update(vote=passed, decision='admitted to the same-target vote' if passed
                          else 'derived, not admitted: knockdown direction rule not met')
        else:
            record.update(vote=False, decision={
                'ko': 'derived and kept as a separate KO arm; not in the CRISPRi vote of this release',
                'crispra': 'derived and kept as a separate activation arm; never in a knockdown vote',
                'crispri_same_study_as_k562_bulk': 'derived for the equivalence reading only; the historical K562 table keeps the one vote of this experiment',
            }[spec['arm']])
        sources[name] = record
    # HIPSCI targeted: derived by the earlier verified consumer, QC by the concluded diagnostic.
    candidate = json.loads((HIPSCI / 'source_candidate.json').read_text(encoding='utf-8'))
    qc = json.loads((HIPSCI_QC / 'qc_receipt.json').read_text(encoding='utf-8'))
    qc_ok = json.loads((HIPSCI_QC / 'verification.json').read_text(encoding='utf-8'))['verified']
    medians = [c['panel_median_raw'] for c in qc['contexts']]
    fetch(candidate['cloud']['job'], r'hipsci_targeted_19\.npz$', tables / 'hipsci_targeted_19')
    path = tables / 'hipsci_targeted_19' / 'hipsci_targeted_19.npz'
    if P.pin(path) != dict(bytes=candidate['output']['bytes'], sha256=candidate['output']['sha256']):
        raise ValueError('HIPSCI table differs from its frozen candidate')
    ordered = sorted(medians)
    passed = qc_ok and len(medians) == 19 and ordered[9] < 0
    sources['hipsci_targeted_19'] = dict(
        arm='crispri', study='hipsci_targeted_19', modality='CRISPRi', units=['hipsci_targeted_19'],
        job=candidate['cloud']['job'], version=candidate['cloud']['version'],
        receipt=dict(candidate['receipt'], path='reports/modelli/percorso_riusabile_2026-10-05/' + candidate['receipt']['path']),
        table=dict(candidate['output'], name='hipsci_targeted_19.npz', path=path.as_posix()), context_tables=[],
        targets=candidate['targets'], target_cells=candidate['target_cells'],
        control_cells=candidate['roles_cells']['control'], contexts=[c['context'] for c in candidate['contexts']],
        aggregation='19 clones pooled as donors before shrink',
        knockdown=dict(reading='per-clone median own-transcript raw log ratio of the five panel targets',
                       clones=len(medians), median_of_clone_medians=ordered[9], weakest_clone=ordered[-1],
                       clones_with_negative_median=sum(m < 0 for m in medians),
                       qc_receipt=P.pin(HIPSCI_QC / 'qc_receipt.json')),
        cells_by_role={'hipsci_targeted_19': candidate['roles_cells']}, comparison=None,
        caveat='chemistry unreported, namespaced to the study; weak clones stay in the pool with their cell weight',
        vote=passed, decision='admitted to the same-target vote' if passed
        else 'derived, not admitted: knockdown direction rule not met')
    P.write_new(out, dict(utc=P.now(), rule='reports/modelli/banca_canonica_2026-10-07/PROTOCOLLO.md',
                          rule_sha256=P.sha(P.HERE / 'PROTOCOLLO.md'), tables_root=tables.as_posix(),
                          sources=sources, not_launched=document['not_launched'],
                          scope='production derivations; no held-out validation and no score'))
    for name, r in sources.items():
        print(name, r['arm'], 'VOTE' if r['vote'] else 'no-vote', len(r['targets']), r['knockdown'].get('median_own_raw', r['knockdown'].get('median_of_clone_medians')))


if __name__ == '__main__':
    main()
