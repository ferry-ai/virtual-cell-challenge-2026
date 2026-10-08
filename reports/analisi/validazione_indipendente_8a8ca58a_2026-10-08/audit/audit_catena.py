"""Independent check of one full path per new source: bank -> derivation -> release -> fit -> fold bench.

For every source the canonical release added to the t36 reference, compare, hash by hash, what each step
says it read with what the previous step says it wrote:

    registry (bank unit)  count_sum / rows / receipt sha256
        == derivation receipt, input_hashes
    derivation receipt, output table sha256
        == release pin (voted) == T1 release pin
        == file stage 100 hashed in the T1 production fit (DATI-TRANSFER's consumo)
        == file stage 100 hashed in this validation's production-parity run and in every fold that keeps it
    and the table is absent from the folds that hold its lineage.

It also counts what actually reaches the model: cells in the bank unit, cells in the rows the derivation
selected, targets voted, and the share of each target's own effect that panel centring removes (1 / targets
of the table). Reads small committed metadata only.

    py audit_catena.py <out.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
BANK = REPO / 'reports/modelli/banca_canonica_2026-10-07'
REGISTRY = BANK / 'registro_fonti_r1.json'
RELEASE_R1 = BANK / 'fit/release_r1.json'
RELEASE_T1 = REPO / 'reports/modelli/dati_transfer_2026-10-08_01a11c34/release_t1_r1.json'
CONSUMO_T1 = REPO / 'reports/modelli/dati_transfer_2026-10-08_01a11c34/fit/dt1-01a11c34-r1/consumo.json'
MANIFEST_T1 = REPO / 'reports/modelli/dati_transfer_2026-10-08_01a11c34/fit/dt1-01a11c34-r1/reference_manifest.json'
BENCH = HERE.parent / 'banco/r1/completion/consumption.json'
FOLDS = HERE.parent / 'manifest_fold_v1.json'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> None:
    out = Path(sys.argv[1])
    registry, r1, t1 = read(REGISTRY), read(RELEASE_R1), read(RELEASE_T1)
    consumo_t1, bench, folds = read(CONSUMO_T1), read(BENCH), read(FOLDS)
    lineage_of = {t: name for name, lin in folds['lineages'].items() for t in lin['tables']}
    added = sorted(s for s, v in r1['voted'].items() if not v['in_reference'])
    sources = {}
    for name in added:
        entry = r1['voted'][name]
        receipt_path = REPO / entry['receipt']['path']
        receipt = read(receipt_path)
        checks = {'receipt_file_sha256': sha(receipt_path) == entry['receipt']['sha256']}
        # 1. bank -> derivation
        bank_ok = []
        for unit in entry['units']:
            bank = registry['units'][unit]['bank']
            hashes = receipt.get('input_hashes', {})
            # the HIPSCI receipt of 5 October is flat: one unit, its files at the top level
            pins = hashes.get(unit) or (hashes if 'count_sum.npz' in hashes and len(entry['units']) == 1 else None)
            if pins is None:
                bank_ok.append(None)        # a layout this check does not know: reported, not passed
                continue
            match = any(b['count_sum_sha256'] == pins['count_sum.npz']['sha256']
                        and b['rows_sha256'] == pins['rows.csv']['sha256']
                        and b['receipt_sha256'] == pins['complete.json']['sha256'] for b in bank)
            bank_ok.append(match)
        checks['bank_files_equal_derivation_inputs'] = (None if any(b is None for b in bank_ok) else all(bank_ok))
        # 2. derivation -> release
        outputs = receipt.get('outputs', {})
        table = outputs.get(entry['file'], {})
        if not table and receipt.get('output', {}).get('path') == entry['file']:
            table = receipt['output']
        checks['derivation_output_equals_release_pin'] = (table.get('sha256') == entry['sha256']) if table else None
        in_t1 = name in t1['voted']
        checks['t1_pin_equals_r1_pin'] = (t1['voted'][name]['sha256'] == entry['sha256']) if in_t1 else None
        # 3. release -> production fit of T1 (their receipt)
        read_t1 = consumo_t1['sources'].get(name, {})
        checks['read_by_the_T1_production_fit'] = (read_t1.get('sha256') == entry['sha256']) if in_t1 else None
        # 4. release -> this validation's runs
        runs = [c for c in bench if c['label'] in ('T1', 'R1')]
        hashed = {(c['label'], c['context']): c['files_read_by_stage100'].get(name + '.npz') for c in runs}
        kept = {k: v for k, v in hashed.items() if v is not None}
        checks['every_validation_read_has_the_release_sha256'] = bool(kept) and all(v == entry['sha256'] for v in kept.values())
        lineage = lineage_of[name]
        held = [f['id'] for f in folds['folds_C'] if f['lineage'] == lineage]
        checks['absent_from_the_folds_that_hold_its_lineage'] = all(
            hashed.get((label, fid)) is None for fid in held for label in ('T1', 'R1'))
        units = {u: registry['units'][u]['cells'] for u in entry['units']}
        inv = receipt.get('inventory') or []
        n_targets = len(entry['targets'])
        sources[name] = {
            'lineage': lineage, 'modality': entry['modality'], 'in_T1': in_t1, 'checks': checks,
            'bank_cells': sum(u['all'] for u in units.values()),
            'bank_cells_by_role': {k: sum(u.get(k, 0) for u in units.values())
                                   for k in ('panel_target', 'other_target', 'control', 'unassigned')},
            'derivation_inventory': inv, 'target_cells_voting': entry['target_cells'],
            'control_cells': entry['control_cells'], 'targets_voted': entry['targets'],
            'share_of_bank_cells_behind_the_vote': (entry['target_cells'] + entry['control_cells'])
            / max(sum(u['all'] for u in units.values()), 1),
            'panel_centring': {'targets_in_table': n_targets,
                               'share_of_own_effect_removed': 1.0 / n_targets,
                               'vote_is_identically_zero': n_targets == 1},
            'folds_holding_its_lineage': held,
            'validation_runs_that_read_it': sorted('%s/%s' % k for k in kept)}
    small = {}
    for name, entry in r1['voted'].items():
        n = entry['targets'] if isinstance(entry.get('targets'), int) else None
        if n is None and isinstance(entry.get('targets'), list):
            n = len(entry['targets'])
        if n is None:
            n = consumo_t1['sources'].get(name, {}).get('panel_targets_voted')
        if n is not None and 0 < n <= 20:
            small[name] = {'targets_in_table': n, 'share_of_own_effect_removed_by_panel_centring': round(1 / n, 4),
                           'in_T0': bool(entry['in_reference'])}
    summary = {
        'sources_added_by_r1': added,
        'all_hash_checks_pass': all(v is not False for s in sources.values() for v in s['checks'].values()),
        'checks_not_evaluable': {s: [k for k, v in d['checks'].items() if v is None] for s, d in sources.items()
                                 if any(v is None for v in d['checks'].values())},
        'tables_with_at_most_20_panel_targets': small,
        'tables_read_with_no_panel_target': sorted(s for s, v in consumo_t1['sources'].items()
                                                   if v['panel_targets_voted'] == 0),
        'T1_sources_read': len(consumo_t1['sources']),
        'T1_sources_with_at_least_one_vote': sum(1 for v in consumo_t1['sources'].values() if v['panel_targets_voted'] > 0),
    }
    doc = {'inputs': {p.relative_to(REPO).as_posix(): sha(p) for p in (REGISTRY, RELEASE_R1, RELEASE_T1, CONSUMO_T1,
                                                                        BENCH, FOLDS)},
           'summary': summary, 'sources': sources}
    with out.open('x', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1)
        fh.write('\n')
    print(json.dumps(summary, indent=1))
    for name, s in sources.items():
        print(name, s['checks'], 'bank cells', s['bank_cells'], 'behind vote %.3f' % s['share_of_bank_cells_behind_the_vote'])


if __name__ == '__main__':
    main()
