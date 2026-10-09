"""Inventory of what the bank offers to the evaluation, by unit and by lineage (contract v3, section 3).

Built from metadata already committed, without touching data and without redoing any ingestion:

    the canonical source registry of 7 October   (45 bank units: study, line group, modality, chemistry, contexts,
                                                  donors, cells, controls, targets, where the unit goes)
    the coverage ledger of T3                    (what the submitted t38 actually used of each unit)
    the frozen fold manifest v2                  (lineages with aliases, C folds and their truth tables)
    the two existing level-B extractions         (real cells of panel targets: which folds have them)
    esposizione.json                             (curated: what each lineage has already seen of the project)

"File acquired" and "usable truth" are kept apart: a unit is a usable truth for a role only if the rule of
that role holds on its own numbers; every gap is named. Donors, conditions and libraries of one line are
never counted as lineages.

    py inventario.py <out.json> <out.md>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
REGISTRY = REPO / 'reports/modelli/banca_canonica_2026-10-07/registro_fonti_r1.json'
COVERAGE = REPO / 'reports/modelli/dati_transfer_2026-10-08_01a11c34/coverage_t3_r1.json'
MANIFEST = REPO / 'reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/manifest_fold_v2.json'
RELEASE = REPO / 'reports/modelli/banca_canonica_2026-10-07/fit/release_r1.json'
BENCH = REPO / 'reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco'
LEVEL_B = {'C-K562': BENCH / 'celle_k562_r1/completion/real_cells.json', 'C-iPSC': BENCH / 'celle_ipsc_r1/completion/real_cells.json'}
MIN_PANEL_TARGETS_FOLD = 30         # a six-member fold on the panel needs enough targets for a rank and a bootstrap
MIN_PANEL_TARGETS_DESCRIPTIVE = 3   # below this the bench skips a truth table (bench_core.measure)
MIN_CELLS_PER_TARGET = 10           # min_cells of the original recipe
MIN_CONTROLS = 100
ROLE_TEXT = {'CRISPRi_core_direct_vote': 'voto CRISPRi', 'CRISPRi_table_read_without_panel_vote': 'tabella letta, nessun voto sul pannello',
             'KO_direct_vote_pooled_by_study_lineage': 'voto KO a peso 0,25', 'CRISPRa_separate_mechanism_not_in_LOF_transfer': 'CRISPRa, fuori dal transfer',
             'not_eligible_for_direct_panel_transfer': 'in banca, non derivata', 'prior_CRISPRi_admission_exclusion_retained': 'derivata, non ammessa al voto',
             'same_experiment_represented_by_legacy_K562_bulk': 'stesso esperimento della tabella K562 BULK: non vota due volte'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def n(x):
    return '—' if x is None else format(int(x), ',').replace(',', '.')


def build() -> dict:
    registry, coverage, manifest, release = read(REGISTRY), read(COVERAGE), read(MANIFEST), read(RELEASE)
    exposure = read(HERE / 'esposizione.json')
    for block in list(exposure['lineages'].values()):
        for src in block['sources']:
            if not (REPO / src).exists():
                raise SystemExit('exposure cites a missing file: ' + src)
    for src in exposure['checkpoint_sources']:
        if not (REPO / src).exists():
            raise SystemExit('exposure cites a missing file: ' + src)
    lineage_of_unit = {u: name for name, lin in manifest['lineages'].items() for u in lin['units']}
    folds = {f['lineage']: f for f in manifest['folds_C']}
    voted = release['voted']
    level_b = {}
    for fold, path in LEVEL_B.items():
        if path.is_file():
            side = read(path)
            level_b[fold] = {'key': side['key'], 'targets': len(side['targets']), 'controls': side['controls'], 'genes': side['genes']}
    units = {}
    for name, u in registry['units'].items():
        cells = u.get('cells') or {}
        modality = '/'.join(u['modality'])
        lineage = lineage_of_unit.get(name)
        if lineage is None:
            raise SystemExit('unit outside the frozen lineages: ' + name)
        panel_t, panel_c, controls = u.get('panel_targets') or 0, cells.get('panel_target'), cells.get('control') or 0
        per_target = (panel_c / panel_t) if panel_t and panel_c else None
        conditions = sorted({c[1] for c in u['contexts'] if len(c) > 1 and c[1] not in ('MISSING', None)})
        gaps = []
        if 'MISSING' in (u.get('chemistry') or ['MISSING']):
            gaps.append('chimica non riportata nel registro')
        if controls < MIN_CONTROLS:
            gaps.append('solo %d controlli non perturbati' % controls)
        if panel_t and per_target is not None and per_target < MIN_CELLS_PER_TARGET:
            gaps.append('%.0f cellule per bersaglio del pannello' % per_target)
        if any(len(c) > 1 and c[1] == 'MISSING' for c in u['contexts']) and len(u['contexts']) > 1:
            gaps.append('condizione o stimolo non riportati per i contesti')
        if (u.get('native_targets') or 0) > 20000:
            gaps.append('più etichette native che geni (%s): guide o combinazioni da riconciliare prima di usarle come bersagli'
                        % n(u['native_targets']))
        dest = u.get('destination') or {}
        if not dest.get('source'):
            gaps.append(str(dest.get('role')))
        cov = coverage['bank_units'].get(name) or {}
        # the role a unit can play in the evaluation, by rule on its own numbers
        role, why = 'nessuno oggi', None
        usable_cells = controls >= MIN_CONTROLS and (per_target or 0) >= MIN_CELLS_PER_TARGET
        if modality == 'CRISPRi' and panel_t >= MIN_PANEL_TARGETS_FOLD and usable_cells:
            role = 'fold del pannello a sei membri (livello B)'
        elif modality == 'CRISPRi' and panel_t >= MIN_PANEL_TARGETS_DESCRIPTIVE and dest.get('source'):
            role = 'lettura descrittiva sul pannello (pochi bersagli)'
        elif modality == 'CRISPRi' and panel_t < MIN_PANEL_TARGETS_DESCRIPTIVE and (u.get('native_targets') or 0) >= 100 and controls >= MIN_CONTROLS:
            role = 'ricerca su bersagli fuori pannello (T, J, C fuori pannello)'
        elif modality == 'KO' and panel_t >= MIN_PANEL_TARGETS_DESCRIPTIVE and usable_cells:
            role = 'lettura KO separata, descrittiva'
        elif modality == 'CRISPRa':
            role = 'solo ramo CRISPRa separato'
        if role == 'nessuno oggi':
            why = '; '.join(gaps) or 'meno di %d bersagli del pannello' % MIN_PANEL_TARGETS_DESCRIPTIVE
        units[name] = {
            'lineage': lineage, 'registry_line_group': u['line_group'], 'study': u['study'], 'modality': modality,
            'chemistry': u.get('chemistry'), 'contexts': len(u['contexts']), 'donors_or_clones': len(u.get('donors_or_clones') or []),
            'donor_identity': u.get('donor_identity'), 'conditions': conditions,
            'cells_all': cells.get('all'), 'cells_control': controls, 'cells_panel_target': panel_c,
            'cells_per_panel_target': per_target, 'native_targets': u.get('native_targets'), 'panel_targets': panel_t,
            'single_cells_in_bank': bool(u.get('samples_bytes')), 'samples_levels': u.get('samples_levels'),
            'table': dest.get('source'), 'table_in_release_r1': dest.get('source') in voted,
            'destination_role': dest.get('role'), 'role_in_t38': ROLE_TEXT.get(cov.get('role'), cov.get('role')),
            'possible_role': role, 'no_role_because': why, 'gaps': gaps}
    lineages = {}
    for name, lin in manifest['lineages'].items():
        mine = {k: v for k, v in units.items() if v['lineage'] == name}
        fold = folds.get(name)
        studies = sorted({v['study'] for v in mine.values()})
        b_ready = [k for k, v in mine.items() if v['possible_role'].startswith('fold del pannello')]
        lineages[name] = {
            'registry_groups': lin['registry_groups'], 'units': sorted(mine), 'studies': studies,
            'modalities': sorted({v['modality'] for v in mine.values()}),
            'donors_or_clones_max': max((v['donors_or_clones'] for v in mine.values()), default=0),
            'cells_all': sum(v['cells_all'] or 0 for v in mine.values()),
            'fold_level_A': None if fold is None else {'id': fold['id'], 'truth_tables': [t['table'] for t in fold['truth']]},
            'fold_level_B_today': level_b.get(fold['id']) if fold else None,
            'units_ready_for_level_B': b_ready,
            'descriptive_units': [k for k, v in mine.items() if v['possible_role'].startswith('lettura')],
            'off_panel_units': [k for k, v in mine.items() if v['possible_role'].startswith('ricerca')],
            'exposure': exposure['lineages'].get(name), 'status': 'sviluppo'}
    return {'schema': 'inventario-valutazione/1', 'contract': 'PROTOCOLLO_v3 section 3',
            'inputs': {p.relative_to(REPO).as_posix(): __import__('hashlib').sha256(p.read_bytes()).hexdigest()
                       for p in (REGISTRY, COVERAGE, MANIFEST, RELEASE, HERE / 'esposizione.json')},
            'rules': {'min_panel_targets_for_a_fold': MIN_PANEL_TARGETS_FOLD, 'min_panel_targets_descriptive': MIN_PANEL_TARGETS_DESCRIPTIVE,
                      'min_cells_per_panel_target': MIN_CELLS_PER_TARGET, 'min_controls': MIN_CONTROLS},
            'units': units, 'lineages': lineages, 'checkpoints': exposure['checkpoints'],
            'totals': {'units': len(units), 'lineages': len(lineages),
                       'lineages_with_level_A_fold': sum(1 for v in lineages.values() if v['fold_level_A']),
                       'lineages_with_level_B_today': sum(1 for v in lineages.values() if v['fold_level_B_today']),
                       'lineages_ready_for_level_B': sorted(k for k, v in lineages.items() if v['units_ready_for_level_B'])}}


def render(doc: dict) -> str:
    L, U = doc['lineages'], doc['units']
    out = ['# Inventario della banca per la valutazione', '',
           'Scritto da `inventario/inventario.py` dai metadati committati (registro canonico del 7/10, registro d\'uso di T3, '
           'manifest dei fold v2); nessun dato letto e nessuna ingestione rifatta. **«In banca» non vuol dire «verità '
           'utilizzabile»**: la colonna del ruolo applica una regola ai numeri dell\'unità, e ogni lacuna è nominata. '
           'Donatori, condizioni e librerie della stessa linea non sono lignaggi. Tutti i lignaggi sono **sviluppo**.', '',
           'Regole: fold a sei membri sul pannello con almeno %d bersagli del pannello, %d cellule per bersaglio e %d '
           'controlli; lettura descrittiva da %d bersagli; CRISPRi, KO e CRISPRa separati.'
           % (doc['rules']['min_panel_targets_for_a_fold'], doc['rules']['min_cells_per_panel_target'],
              doc['rules']['min_controls'], doc['rules']['min_panel_targets_descriptive']), '',
           '## 1. Per lignaggio', '',
           '| Lignaggio | Studi | Modalità | Cellule in banca | Verità oggi: spazio degli effetti | Verità oggi: sei membri | Pronto per i sei membri (cellule in banca) | Altre letture possibili | Da quando è fonte, e dove è già entrato |',
           '|---|---|---|---:|---|---|---|---|---|']
    for name, v in L.items():
        a = '—' if not v['fold_level_A'] else '%s (%s)' % (v['fold_level_A']['id'], ', '.join('`%s`' % t for t in v['fold_level_A']['truth_tables']))
        b = '—' if not v['fold_level_B_today'] else '%d bersagli, %s geni' % (v['fold_level_B_today']['targets'], n(v['fold_level_B_today']['genes']))
        ready = ', '.join('`%s` (%d bersagli)' % (k, U[k]['panel_targets']) for k in v['units_ready_for_level_B']) or '—'
        other = '; '.join(filter(None, [
            ('descrittive: ' + ', '.join('`%s` %s, %d' % (k, U[k]['modality'], U[k]['panel_targets']) for k in v['descriptive_units'])) if v['descriptive_units'] else '',
            ('fuori pannello: ' + ', '.join('`%s` (%s bersagli)' % (k, n(U[k]['native_targets'])) for k in v['off_panel_units'])) if v['off_panel_units'] else ''])) or '—'
        exp = v['exposure']
        seen = '—' if not exp else '%s. %s' % (exp['source_since'], '; '.join(exp['used_in']))
        out.append('| **%s** | %d | %s | %s | %s | %s | %s | %s | %s |' % (
            name, len(v['studies']), ', '.join(v['modalities']), n(v['cells_all']), a, b, ready, other, seen))
    t = doc['totals']
    out += ['', '%d unità in %d lignaggi. Con un fold nello spazio degli effetti: %d. Con un fold a sei membri oggi: %d. '
            'Con cellule in banca sufficienti per un fold a sei membri: %s.'
            % (t['units'], t['lineages'], t['lineages_with_level_A_fold'], t['lineages_with_level_B_today'],
               ', '.join(t['lineages_ready_for_level_B'])), '',
            '## 2. Per unità di banca', '',
            '| Unità | Lignaggio | Studio | Modalità | Chimica | Contesti; donatori o cloni; condizioni | Cellule: tutte / controlli / bersagli del pannello | Bersagli: nativi / pannello | Cellule per bersaglio del pannello | Tabella di effetti | Uso nel t38 | Ruolo possibile nella valutazione | Lacune |',
            '|---|---|---|---|---|---|---|---|---:|---|---|---|---|']
    for name, u in U.items():
        ctx = '%d; %d%s' % (u['contexts'], u['donors_or_clones'], ('; ' + ', '.join(u['conditions'])) if u['conditions'] else '')
        out.append('| `%s` | %s | %s | %s | %s | %s | %s / %s / %s | %s / %d | %s | %s | %s | %s | %s |' % (
            name, u['lineage'], u['study'], u['modality'], ', '.join(u['chemistry'] or ['—']), ctx,
            n(u['cells_all']), n(u['cells_control']), n(u['cells_panel_target']), n(u['native_targets']), u['panel_targets'],
            '—' if u['cells_per_panel_target'] is None else '%.0f' % u['cells_per_panel_target'],
            '`%s`' % u['table'] if u['table'] else '—', u['role_in_t38'] or '—', u['possible_role'],
            '; '.join(u['gaps']) or '—'))
    out += ['', 'Tutte le 45 unità hanno campioni di singole cellule in banca (livelli 32, 64, 128 per contesto e bersaglio); '
            'la tabella di effetti è l\'aggregato che il transfer legge. Le cellule «per bersaglio» sono la media delle '
            'cellule con un bersaglio del pannello divise per i bersagli del pannello dell\'unità.', '',
            '## 3. Quali checkpoint si possono leggere come contesto nuovo, e dove', '',
            '| Checkpoint o candidato | Si legge come regime C su | Nota |', '|---|---|---|']
    for c in doc['checkpoints']:
        out.append('| %s | %s | %s |' % (c['name'], c['regime_C_on'], c['note']))
    return '\n'.join(out) + '\n'


def main() -> None:
    out_json, out_md = Path(sys.argv[1]), Path(sys.argv[2])
    doc = build()
    with out_json.open('x', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    with out_md.open('x', encoding='utf-8', newline='\n') as fh:
        fh.write(render(doc))
    print(json.dumps(doc['totals'], ensure_ascii=False))


if __name__ == '__main__':
    main()
