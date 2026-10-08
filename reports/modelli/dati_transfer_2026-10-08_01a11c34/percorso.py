"""Versioned canonical-bank entry: audit, freeze, package and release consumers.

No command launches remote compute or changes a previous release.
collect-common retrieves outputs of already-authorised jobs; its caller must
have that retrieval authorisation. Other commands operate on local inputs.
Run with scripts/py.cmd. Heavy array work belongs to a verified cloud runtime.
"""
from __future__ import annotations

import argparse
import copy
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BANK = ROOT / 'reports/modelli/banca_canonica_2026-10-07'
DATA = Path(__import__('os').environ.get('VCC2026_DATA_ROOT', 'C:/Users/ferra/vcc2026-data'))
PARENT_SHA = '0650d1d610e05b5cb5fea3c3695dff67bec14443c9df2708121f84e8f8771c8c'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def pin(path):
    p = Path(path)
    return dict(path=p.as_posix(), bytes=p.stat().st_size, sha256=sha(p))


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(document, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def audit(out):
    """Verify small local metadata; do not claim live raw/cloud verification."""
    registry_path = BANK / 'registro_fonti_r1.json'
    registry, state = read(registry_path), read(BANK / 'rows_r1/state.json')
    consumption = read(BANK / 'fit/r1/completion/consumo.json')
    release_path = BANK / 'fit/release_r1.json'
    if sha(release_path) != PARENT_SHA or consumption['release_sha256'] != PARENT_SHA:
        raise ValueError('canonical parent release changed')
    by_unit = {}
    for item in state['units']:
        path = DATA / 'processed/banca_canonica_2026-10-07' / item['path']
        if not item['verified'] or sha(path) != item['sha256']:
            raise ValueError('rows identity changed: ' + item['unit'])
        with path.open(encoding='utf-8', newline='') as f:
            rows = list(csv.DictReader(f))
        counts = {}
        labels = set()
        strata = {}
        for row in rows:
            n, target = int(float(row['n'])), row['target']
            role = 'control' if target == 'NTC' else 'unresolved' if target in ('NO_METADATA', 'UNASSIGNED') else 'labelled'
            counts[role] = counts.get(role, 0) + n
            labels.add(target)
            # Preserve every available biological dimension, including guide if present.
            keys = ('study', 'line_group', 'context', 'donor_or_clone', 'condition', 'modality', 'chemistry', 'guide', 'time', 'state')
            key = json.dumps({k: row[k] for k in keys if k in row}, sort_keys=True)
            strata[key] = strata.get(key, 0) + n
        u = by_unit.setdefault(item['unit'], dict(parts=[], bank_cells=0, native_labels=set(), strata={}, cells_by_role={}))
        u['parts'].append(dict(path=item['path'], sha256=item['sha256'], rows=len(rows)))
        u['bank_cells'] += sum(counts.values())
        u['native_labels'].update(labels)
        for k, n in counts.items():
            u['cells_by_role'][k] = u['cells_by_role'].get(k, 0) + n
        for k, n in strata.items():
            u['strata'][k] = u['strata'].get(k, 0) + n
    for name, u in by_unit.items():
        original = registry['units'][name]
        if u['bank_cells'] != original['cells']['all']:
            raise ValueError('bank population mismatch: ' + name)
        sources = [s for s, info in registry['sources'].items() if name in info.get('units', [])]
        u['native_label_count'] = len(u.pop('native_labels'))
        u['strata'] = [dict(identity=json.loads(k), bank_cells=v) for k, v in sorted(u['strata'].items())]
        u['historical_destination'] = original['destination']
        u['historical_sources'] = sources
        u['samples_read_by_this_audit'] = 0
        u['cells_read_for_training_by_this_audit'] = 0
        u['historical_consumption'] = {s: dict(table_read=s in consumption['sources_read_by_stage100'],
            panel_targets_voted=consumption['sources'].get(s, {}).get('panel_targets_voted', 0)) for s in sources}
    if set(by_unit) != set(registry['units']):
        raise ValueError('unreconciled unit set')
    result = dict(schema=1, utc=now(), scope='verified rows metadata only; raw matrices and current cloud state not checked',
                  inputs={p.name: pin(p) for p in (registry_path, BANK / 'rows_r1/state.json', release_path)},
                  units=by_unit, catalogue=registry['catalogue'],
                  catalogue_reverification='historical decisions carried forward, not independently reverified',
                  claims_complete_corpus=False, bank_cells=sum(u['bank_cells'] for u in by_unit.values()),
                  known_duplicate_h1_controls=38176, physical_samples_read=0, learning_contributions=0)
    write_new(out, result)
    print(json.dumps(dict(units=len(by_unit), bank_cells=result['bank_cells'], output=str(out))))


def freeze(out):
    parent = BANK / 'fit/release_r1.json'
    if sha(parent) != PARENT_SHA:
        raise ValueError('canonical parent changed')
    result = copy.deepcopy(read(parent))
    excluded = result['voted'].pop('tian2019_neuron')
    result['name'] = 'dati-transfer-t1-01a11c34-r1'
    result['frozen_utc'] = now()
    result['why'] = 'Separate admission contrast: canonical r1 minus the doubtful RFK vote; t25 transfer unchanged.'
    result['parent'] = pin(parent)
    result['protocol'] = pin(HERE / 'PROTOCOLLO.md')
    result['candidate_exclusions'] = {'tian2019_neuron': dict(source=excluded,
        scope='same-target vote only; context retained for target/QC reconciliation',
        reason='own-transcript ln ratio -0.0014 on RFK is not persuasive knockdown evidence',
        decision='prospective T1 contrast from the user-requested lead plan; no rewrite of original r1 rule')}
    result['consumption_state'] = 'not_run_for_this_release'
    result['split'] = dict(regime='production', held_groups=[], hidden_targets=[], protected_units=['h1_test'],
                           warning='not a C/T/J validation release')
    result['claims_complete_corpus'] = False
    if len(result['voted']) != 16 or any(v.get('modality', 'CRISPRi') != 'CRISPRi' for v in result['voted'].values()):
        raise ValueError('unexpected T1 vote composition')
    write_new(out, result)
    print(json.dumps(dict(release=str(out), sha256=sha(out), sources=16, fitted=False)))


def package(release, revision):
    """Reuse the original package builder and driver byte-for-byte, in our output folder."""
    folder = HERE / 'fit'
    folder.mkdir(exist_ok=True)
    driver = folder / 'driver.py'
    source_driver = BANK / 'fit/driver.py'
    if driver.exists():
        if sha(driver) != sha(source_driver):
            raise ValueError('local driver differs from parent')
    else:
        shutil.copy2(source_driver, driver)
    spec = importlib.util.spec_from_file_location('canonical_fit_builder', BANK / 'fit/prepara_fit.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The original builder's destination is explicit. Source inputs stay at their pinned paths.
    module.HERE = folder
    module.package(str(Path(release).resolve()), revision)
    write_new(folder / revision / 'reuse_provenance.json', dict(utc=now(), builder=pin(BANK / 'fit/prepara_fit.py'),
        driver=pin(driver), source_driver=pin(source_driver), entry=pin(__file__),
        scope='package preparation only; no remote launch', commands=['fit_t1'], compute_started=False))


def main():
    parser = argparse.ArgumentParser(__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('audit', 'freeze', 'coverage'):
        sub.add_parser(name).add_argument('out', type=Path)
    p = sub.add_parser('package')
    p.add_argument('release', type=Path)
    p.add_argument('revision')
    for name, help_text in (
        ('training-release', 'Freeze a training contract from verified campaign receipts; no fit'),
        ('collect-common', 'Retrieve authorised small outputs and freeze a complete common-vector set'),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument('regime', choices=['production', 'T'])
        p.add_argument('revision', help='New immutable output name; existing releases are not overwritten')
    args = parser.parse_args()
    if args.command == 'package':
        package(args.release, args.revision)
    elif args.command == 'training-release':
        from build_training_release import main as build_release
        build_release(args.regime, args.revision)
    elif args.command == 'collect-common':
        from collect_common_set import main as collect_release
        collect_release(args.regime, args.revision)
    elif args.command == 'coverage':
        from coverage_ledger import main as build_coverage
        build_coverage(args.out)
    else:
        globals()[args.command](args.out)


if __name__ == '__main__':
    main()
