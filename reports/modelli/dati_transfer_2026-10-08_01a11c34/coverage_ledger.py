"""Join catalogue, bank and actual receipts without promoting historical claims."""
import argparse
from collections import Counter
from pathlib import Path
from percorso import HERE, now, pin, read, sha, write_new


def main(out):
    audit_path = HERE / 'audit_r1.json'; audit = read(audit_path)
    inventory_path = HERE / 'alltargets/01a11c34-r3/inventory.json'
    inventory = read(inventory_path)['units']
    training_path = HERE / 'training_release_production_r1.json'
    training = read(training_path); view = read(training['view']['path'])
    if sha(training['view']['path']) != training['view']['sha256']:
        raise ValueError('training contract changed')
    derived = {'production': {}, 'T': {}}
    for regime, revisions in [('production', ['01a11c34-r3', '01a11c34-r4private']),
                               ('T', ['01a11c34-tj1', '01a11c34-tj2private'])]:
        for revision in revisions:
            for path in (HERE / 'alltargets' / revision).glob('*/completion_*/verification.json'):
                verification = read(path); receipt_path = path.with_name('effect_release.json')
                if sha(receipt_path) != verification['receipt']['sha256']:
                    raise ValueError('changed producer receipt')
                receipt = read(receipt_path); unit = receipt['unit']
                if unit in derived[regime]: raise ValueError('duplicate unit receipt')
                derived[regime][unit] = dict(receipt=pin(receipt_path), verification=pin(path),
                    bank_cells=receipt['bank_cells'], target_cells_contributing=receipt['target_cells_contributing'],
                    contexts=len(receipt['contexts']), target_context_rows=sum(len(c['targets_derived']) for c in receipt['contexts']))
    rows = Counter()
    for chunk in view['chunks']:
        rows[chunk['context_id'].split(':', 1)[0]] += len(chunk['targets'])
    pooled = {'h1_train': 'h1', 'h1_val': 'h1', 'k562_gwps_a': 'k562_gwps', 'k562_gwps_b': 'k562_gwps'}
    units = {}
    for unit, old in audit['units'].items():
        producer = pooled.get(unit, unit)
        units[unit] = dict(bank_metadata_verified=old['parts'], bank_cells=old['bank_cells'],
            cells_by_role=old['cells_by_role'], biological_strata=old['strata'],
            current_derivation={r: derived[r].get(unit) for r in derived},
            derivation_gap=inventory[unit] if unit not in derived['production'] else None,
            training_contract=dict(producer_unit=producer, admitted_rows=rows[producer],
                shared_joint_contribution=unit in pooled, model_fit=False,
                exclusions=[x for x in view['excluded'] if x['unit'] == producer]),
            historical_source_links=old['historical_sources'],
            raw_acquisition='historical bank provenance; raw files not independently reread in this session',
            raw_cells_read_by_this_session=0)
    catalogue = []
    for record in audit['catalogue']:
        if set(record['units']) - set(units): raise ValueError('unknown bank alias')
        catalogue.append(dict(record, historical_decision_only=True,
            linked_bank_units=record['units'],
            all_linked_units_derived=bool(record['units']) and all(u in derived['production'] for u in record['units']),
            unresolved_catalogue_reverification=not bool(record['units'])))
    write_new(out, dict(utc=now(), inputs=dict(audit=pin(audit_path), inventory=pin(inventory_path), training_release=pin(training_path)),
        catalogue_records=catalogue, units=units,
        counts=dict(catalogue_records=len(catalogue), bank_units=len(units),
            catalogue_records_without_bank_link=sum(not r['units'] for r in catalogue),
            production_verified=len(derived['production']), T_verified=len(derived['T']),
            training_context_rows=sum(rows.values())),
        counting_policy='Catalogue aliases, split outputs and joint contributions are not additive populations. Bank-cell sums are not unique physical cells. The training contract has no fit receipt.',
        admission_scope='CRISPRi contract only; KO/CRISPRa derived but require their separate mechanism consumer',
        T1_consumption=pin(HERE/'fit/dt1-01a11c34-r1/consumo.json'),
        T1_attribution='Source-table consumption only; do not attribute all newly derived bank cells to this earlier fit.',
        T2_consumption=[pin(p) for p in (HERE/'final_t2/r1/fit').glob('completion_*/t2_consumption.json')],
        claims_complete_corpus=False))
    print(len(catalogue), 'catalogue records;', len(units), 'bank units;',
          len(derived['production']), 'production and', len(derived['T']), 'T receipts')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('out', type=Path)
    main(parser.parse_args().out)
