"""Canonical source registry: one identity, one provenance and one destination per source.

    registro.py <out.json> <out.md> [fit_revision]

Built only from verified evidence: the frozen coverage (expected r3), the catalogue r4, the
verified rows of every bank unit, the admission record, the frozen release and, when a fit
revision is given, its consumption receipt. A catalogue record with no bank keeps the reason the
catalogue itself states; this script does not re-audit those remote files.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import percorso as P

CATALOGUE = P.REPO / 'reports/sorgenti/corpus_cellulare_2026-09-30/catalogo_r4/catalogo.json'
TOTALS = P.REUSE / 'data_totals_r2.json'
REV = P.os.environ.get('VCC_BANCA_REV', 'r1')  # revision of admission and release
RELEASE = P.HERE / ('fit/release_%s.json' % REV)
ADMISSION = P.HERE / ('ammissione_%s.json' % REV)
PLAN = P.HERE / 'piano_r1.json'
SPECIAL = {'NTC', 'UNASSIGNED', 'NO_METADATA'}
UNSET = {'', 'MISSING', 'UNASSIGNED'}

# Catalogue record -> bank units. Explicit, exact ids; nothing is matched by a similar name.
CD4 = {'remote/cd4_D%d_%s' % (d, s): ['D%d_%s' % (d, s)] for d in (1, 2, 3, 4) for s in ('Rest', 'Stim8hr', 'Stim48hr')}
PRIMARY = dict(CD4, **{
    'remote/h1_train': ['h1_train'], 'remote/h1_val': ['h1_val'],
    'remote/kolf_KOLF_Chromatin_Modifiers_QC_Filtered': ['kolf_chromatin'],
    'remote/kolf_KOLF_Metabolic_Enzymes_QC_Filtered': ['kolf_metabolic'],
    'remote/kolf_KOLF_Pan_Genome_QC_Filtered': ['kolf_pan_genome'],
    'remote/kolf_KOLF_Strong_Perturbations': ['kolf_strong'],
    'remote/a549_GSE345058_SC_raw_normalized_counts': ['a549_ko'],
    'remote/scp_DatlingerBock2017': ['datlinger2017'], 'remote/scp_DatlingerBock2021': ['datlinger2021'],
    'remote/scp_DixitRegev2016_K562_TFs_13_days': ['dixit2016_d13'],
    'remote/scp_DixitRegev2016_K562_TFs_7_days': ['dixit2016_d7'],
    'remote/scp_DixitRegev2016_K562_TFs_High_MOI': ['dixit2016_high_moi'],
    'remote/scp_FrangiehIzar2021_RNA': ['frangieh2021'], 'remote/scp_NormanWeissman2019_filtered': ['norman2019'],
    'remote/scp_PapalexiSatija2021_eccite_arrayed_RNA': ['papalexi2021_arrayed'],
    'remote/scp_ShifrutMarson2018': ['shifrut2018'], 'remote/scp_SunshineHein2023': ['sunshine2023'],
    'remote/scp_TianKampmann2019_day7neuron': ['tian2019_neuron'], 'remote/scp_TianKampmann2019_iPSC': ['tian2019_ipsc'],
    'remote/scp_TianKampmann2021_CRISPRa': ['tian2021_crispra'], 'remote/scp_TianKampmann2021_CRISPRi': ['tian2021_crispri'],
    'remote/scp_XuCao2023': ['xu2023'],
    'ingested/hepg2_nadig': ['hepg2_nadig'], 'ingested/jurkat_nadig': ['jurkat_nadig'],
    'ingested/hipsci_targeted_19': ['hipsci_targeted_19'], 'ingested/hipsci_gw_fitness': ['hipsci_gw_fitness'],
    'ingested/hipsci_gw_nonfitness': ['hipsci_gw_nonfitness'],
    'ingested/replogle_k562_gwps': ['k562_gwps_a', 'k562_gwps_b'],
    'ingested/replogle_k562_essential': ['k562_essential'], 'ingested/replogle_rpe1': ['rpe1'],
})
# Second catalogue rows of an experiment that already has its primary row above.
ALIAS = {
    'ingested/h1_vcc2025_trainval': ['h1_train', 'h1_val'], 'ingested/a549_ko': ['a549_ko'],
    'ingested/tian_norman': ['norman2019', 'tian2019_ipsc', 'tian2019_neuron', 'tian2021_crispra', 'tian2021_crispri'],
    'ingested/kolf_small': ['kolf_chromatin', 'kolf_metabolic'], 'ingested/kolf_strong': ['kolf_strong'],
    'ingested/scp_ko_frangieh_sunshine_papalexi': ['frangieh2021', 'sunshine2023', 'papalexi2021_arrayed'],
    'ingested/scp_tcells_shifrut_datlinger': ['shifrut2018', 'datlinger2017', 'datlinger2021'],
    'ingested/scp_k562_hek_dixit_xu': ['dixit2016_d7', 'dixit2016_d13', 'dixit2016_high_moi', 'xu2023'],
    'remote/scp_NadigOConner2024_hepg2': ['hepg2_nadig'], 'remote/scp_NadigOConner2024_jurkat': ['jurkat_nadig'],
    'remote/scp_ReplogleWeissman2022_K562_essential': ['k562_essential'],
    'remote/scp_ReplogleWeissman2022_K562_gwps': ['k562_gwps_a', 'k562_gwps_b'],
    'remote/scp_ReplogleWeissman2022_rpe1': ['rpe1'],
}
RAW_ONLY = {'ingested/jurkat_gse249595': 'davidmaisterx/rlab-jurkat-gse249595'}
# Unit -> the one operational source it feeds. Sources of the t36 release keep their names.
T36_SOURCE = dict({u: 'cd4_mix' for units in CD4.values() for u in units}, **{
    'h1_train': 'h1', 'h1_val': 'h1', 'hepg2_nadig': 'hepg2_nadig', 'jurkat_nadig': 'jurkat_nadig',
    'rpe1': 'rpe1', 'k562_essential': 'k562_essential', 'kolf_chromatin': 'kolf_chromatin',
    'kolf_metabolic': 'kolf_metabolic', 'kolf_pan_genome': 'kolf_pan_genome', 'kolf_strong': 'kolf_strong',
    'orion_hct116': 'orion_hct116', 'orion_hek293t': 'orion_hek293t'})


def gb(n):
    return round(n / 1e9, 3)


def unit_rows(unit):
    rows = []
    for _, part in P.rows_of(unit):
        rows.extend(part)
    return rows


def describe(unit, record, targets):
    rows = unit_rows(unit)
    panel = set(targets)
    cells = Counter()
    for r in rows:
        t, n = r['target'], int(float(r['n']))
        cells['all'] += n
        cells['control' if t == 'NTC' else 'unassigned' if t == 'UNASSIGNED' else 'no_metadata'
              if t == 'NO_METADATA' else 'panel_target' if t in panel else 'other_target'] += n
    labels = {r['target'] for r in rows} - SPECIAL
    banks = [record['bank']] if 'bank' in record else [p['bank'] for p in record['verified_parts'].values()]
    samples = [record['samples']] if 'samples' in record else [p['samples'] for p in record.get('verified_parts', {}).values()]
    raw = record.get('raw') or {}
    one = lambda column: sorted({r[column] for r in rows})
    return dict(
        study=one('study')[0], line_group=one('line_group'), modality=one('modality'), chemistry=one('chemistry'),
        contexts=sorted({(r['context'], r['condition']) for r in rows if r['context'] not in UNSET}),
        donors_or_clones=sorted({r['donor_or_clone'] for r in rows} - UNSET),
        donor_identity='reported' if {r['donor_or_clone'] for r in rows} - UNSET else 'not reported in the bank rows',
        bank_rows=len(rows), cells=dict(cells), native_targets=len(labels), panel_targets=len(labels & panel),
        raw=dict(dataset=raw.get('dataset'), version=raw.get('version'), receipt=(raw.get('receipt') or raw.get('files_receipt') or '').replace('\\', '/'),
                 kernel_sources=raw.get('kernel_sources')),
        bank=[dict(kernel=b['kernel'], version=b['saved_version']['version'], receipt_sha256=b['receipt_sha256'],
                   count_sum_sha256=b['files']['count_sum.npz']['sha256'], rows_sha256=b['files']['rows.csv']['sha256'],
                   mountable_copy=(b.get('mountable_copy') or {}).get('dataset')) for b in banks],
        bank_bytes=sum(f['bytes'] for b in banks for f in b['files'].values()),
        samples_bytes=sum(int(s.get('bytes') or 0) for s in samples),
        samples_levels=[s.get('levels') for s in samples][0] if len(samples) == 1 else 'partitioned: see expected r3',
        axis_sha256=P.AXIS_SHA)


def main():
    out_json, out_md = Path(sys.argv[1]), Path(sys.argv[2])
    revision = sys.argv[3] if len(sys.argv) > 3 else None
    units = P.expected_units()
    _, targets = P.panel()
    catalogue = json.loads(CATALOGUE.read_text(encoding='utf-8'))
    release = json.loads(RELEASE.read_text(encoding='utf-8'))
    admission = json.loads(ADMISSION.read_text(encoding='utf-8'))
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    totals = json.loads(TOTALS.read_text(encoding='utf-8'))
    catalog_r11 = json.loads((P.REUSE / 'cloud_catalog_r11/manifest.json').read_text(encoding='utf-8'))
    consumo = None
    if revision:
        folder = P.HERE / 'fit' / revision / 'completion'
        assert json.loads((folder / 'verification.json').read_text(encoding='utf-8'))['verified']
        consumo = json.loads((folder / 'consumo.json').read_text(encoding='utf-8'))
    read = set(consumo['sources_read_by_stage100']) if consumo else set()

    # Operational sources: every derived table, with the units behind it and its one role.
    sources = {}
    for name, v in release['voted'].items():
        sources[name] = dict(role='voto', kind=v['kind'], table_sha256=v['sha256'], table_bytes=v['bytes'],
                             in_t36=v['in_reference'], units=[])
    for name, v in release['derived_not_voted'].items():
        sources[name] = dict(role={'ko': 'braccio KO, non votato', 'crispra': 'braccio CRISPRa, non votato',
                                   'crispri_same_study_as_k562_bulk': 'stesso esperimento di k562 BULK: equivalenza, mai secondo voto'}[v['arm']],
                             kind='fragment', table_sha256=v['sha256'], table_bytes=v['bytes'], in_t36=False, units=list(v['units']))
    for name, v in release['derived_not_admitted'].items():
        sources[name] = dict(role='derivata, non ammessa al voto (regola del verso)', kind='fragment',
                             table_sha256=v['sha256'], table_bytes=v['bytes'], in_t36=False, units=list(v['units']))
    for name, v in admission['sources'].items():
        if v['vote']:
            sources[name]['units'] = list(v['units'])
    for unit, name in T36_SOURCE.items():
        sources[name]['units'].append(unit)
    sources['k562']['units'] = []
    sources['k562']['note'] = ('tabella storica BULK della ricetta t25 (pseudobulk Replogle GWPS), non derivata dalla banca '
                               'cellulare; la banca k562_gwps_a/b e lo stesso esperimento a singola cellula')
    for name, s in sources.items():
        s['consumed_by_fit'] = name in read if consumo else None
        if consumo and name in consumo['sources']:
            s['panel_targets_voted'] = consumo['sources'][name]['panel_targets_voted']
    unit_source = {u: n for n, s in sources.items() for u in s['units']}

    registry_units, by_study = {}, defaultdict(list)
    for unit, record in units.items():
        d = describe(unit, record, targets)
        raw_archive = next((a for a in catalog_r11['raw_archives'].values() if unit in a['units']), None)
        d['raw']['bytes'] = raw_archive['units'][unit]['bytes'] if raw_archive else None
        d['raw']['cells'] = raw_archive['units'][unit]['cells'] if raw_archive else (record.get('raw') or {}).get('cells') \
            or ((record.get('raw') or {}).get('spec') or {}).get('cells')
        d['catalogue_records'] = sorted(k for k, v in PRIMARY.items() if unit in v)
        d['historical_aliases'] = sorted(k for k, v in ALIAS.items() if unit in v)
        source = unit_source.get(unit)
        if source:
            d['destination'] = dict(source=source, role=sources[source]['role'],
                                    consumed_by_fit=sources[source]['consumed_by_fit'])
        else:
            blocked = plan['not_launched'][unit]
            d['destination'] = dict(source=None, role='in banca, non derivata: ' + blocked['declared_reason'],
                                    consumed_by_fit=False if consumo else None,
                                    evidence=[dict(context=c['context'], control_cells=c['control_cells'],
                                                   panel_targets_min_cells=c['panel_targets_min_cells'],
                                                   donors_without_controls=len(c['donors_without_controls']))
                                              for c in blocked['contexts']][:6])
        registry_units[unit] = d
        by_study[d['study']].append(unit)

    records = []
    for section, items in catalogue.items():
        for item in items:
            rid = section + '/' + (item['id'] if isinstance(item, dict) else item[0])
            stated = item.get('state') if isinstance(item, dict) else ' ; '.join(item[1:])
            if rid in PRIMARY:
                kind, where = 'in banca', PRIMARY[rid]
            elif rid in ALIAS:
                kind, where = 'alias dello stesso esperimento: nessun secondo peso', ALIAS[rid]
            elif rid in RAW_ONLY:
                kind, where = 'solo archivio grezzo (%s): nessuna banca' % RAW_ONLY[rid], []
            else:
                kind, where = 'non in banca', []
            records.append(dict(record_id=rid, destination=kind, units=where, catalogue_state=stated,
                                modality=item.get('modality') if isinstance(item, dict) else None,
                                cells=item.get('cells') if isinstance(item, dict) else None))
    outside = sorted(set(units) - {u for r in records for u in r['units']})

    voted = [n for n, s in sources.items() if s['role'] == 'voto']
    voted_units = sorted(u for n in voted for u in sources[n]['units'])
    h1_shared = min(registry_units['h1_train']['cells'].get('control', 0), registry_units['h1_val']['cells'].get('control', 0))
    def lines(us):
        return sorted({g for u in us for g in registry_units[u]['line_group']})
    donors_distinct, contexts_distinct = set(), set()
    for unit, d in registry_units.items():
        hipsci = d['study'].startswith('hipsci')
        family = 'hipsci' if hipsci else d['study']
        donors_distinct.update((family, x) for x in d['donors_or_clones'])
        contexts_distinct.update((d['study'], 'clone' if hipsci else c, k) for c, k in d['contexts'])
    def read_cells(us):
        return sum(registry_units[u]['cells'].get('control', 0) + registry_units[u]['cells'].get('panel_target', 0) for u in us)
    summary = dict(
        raw_unique_gb=gb(totals['raw_total_bytes']), raw_cell_rows=totals['raw_cell_rows'],
        raw_note='17 archivi precedenti (%s GB, incluso Jurkat GSE249595 senza banca) piu CD4, KOLF pan, HCT116, HEK293T (%s GB)'
                 % (gb(totals['raw_existing_unique_bytes']), gb(totals['raw_new_bytes'])),
        derived_bank_gb=gb(sum(u['bank_bytes'] for u in registry_units.values())),
        derived_samples_gb=gb(sum(u['samples_bytes'] for u in registry_units.values())),
        derived_tables_gb=gb(sum(s['table_bytes'] for s in sources.values())),
        bank_units=len(registry_units), studies=len(by_study),
        bank_cells=sum(u['cells']['all'] for u in registry_units.values()),
        bank_cells_note='h1_train e h1_val ripetono gli stessi %d controlli: il totale li conta due volte' % h1_shared,
        line_groups=lines(registry_units), line_groups_n=len(lines(registry_units)),
        bank_rows_contexts=sum(len(u['contexts']) for u in registry_units.values()),
        contexts_distinct=len(contexts_distinct), donors_or_clones_distinct=len(donors_distinct),
        contexts_note='contesto = (studio, contesto, condizione) distinto; nelle tre unita HIPSCI il contesto di banca e il clone, '
                      'contato qui come donatore e non come contesto. Un gruppo di linea non e una linea: iPSC riunisce KOLF2.1J, '
                      'i cloni HIPSCI e le iPSC di Tian',
        donors_note='donatori CD4 e Shifrut e cloni HIPSCI distinti; i cloni HIPSCI comuni alle tre unita sono contati una volta',
        catalogue_records=len(records), catalogue_in_bank=sum(r['destination'] == 'in banca' for r in records),
        catalogue_alias=sum(r['destination'].startswith('alias') for r in records),
        catalogue_not_in_bank=sum(r['destination'] == 'non in banca' for r in records),
        units_outside_catalogue=outside,
        sources_voted=len(voted), sources_voted_with_panel_targets=None, sources_voted_names=sorted(voted),
        units_behind_voted_sources=len(voted_units), line_groups_voted=lines(voted_units),
        cells_in_bank_rows_read_by_voted_sources=read_cells(voted_units) - h1_shared,
        cells_read_note='controlli piu bersagli del pannello nelle righe di banca dietro le fonti votate; la tabella k562 BULK '
                        'storica non viene dalla banca e non e contata; i controlli H1 condivisi sono contati una volta',
        sources_other_arms=sorted(n for n, s in sources.items() if s['role'] != 'voto'),
        units_not_derived=sorted(u for u, d in registry_units.items() if d['destination']['source'] is None),
        fit=None)
    if consumo:
        summary['sources_voted_with_panel_targets'] = sum(1 for n in voted if sources[n].get('panel_targets_voted'))
        summary['fit'] = dict(revision=revision, release_sha256=consumo['release_sha256'],
                              sources_read=len(read), vote_count_histogram=consumo['vote_count_histogram'],
                              targets_with_added_votes=consumo['targets_with_added_votes'],
                              targets_changed_outside_added_votes=consumo['targets_changed_outside_added_votes'])
    document = dict(schema=1, utc=P.now(), claims_complete_corpus=False,
                    inputs=dict(expected=P.EXPECTED_SHA, catalogue=P.sha(CATALOGUE), rows=P.sha(P.ROWS / 'state.json'),
                                admission=P.sha(ADMISSION), release=P.sha(RELEASE), plan=P.sha(PLAN),
                                fit_consumo=None if not consumo else P.sha(P.HERE / 'fit' / revision / 'completion/consumo.json')),
                    summary=summary, sources=sources, studies={k: sorted(v) for k, v in sorted(by_study.items())},
                    units=registry_units, catalogue=records)
    P.write_new(out_json, document)

    lines_md = ['# Registro canonico delle fonti', '',
                'Generato da `registro.py` (%s). Non si modifica a mano: si rigenera in un file nuovo.' % document['utc'][:16],
                'Una riga per unita di banca; i record del catalogo e gli alias stanno nel JSON accanto.', '',
                '## Fonti operative (un solo ingresso per tabella)', '',
                '| Fonte | Ruolo | Unita di banca | Bersagli del pannello votati | Letta dal fit | sha256 tabella |', '|---|---|---|---:|---|---|']
    for name, s in sorted(sources.items(), key=lambda kv: (kv[1]['role'] != 'voto', kv[0])):
        lines_md.append('| `%s` | %s%s | %s | %s | %s | `%s` |' % (
            name, s['role'], '' if s['in_t36'] or s['role'] != 'voto' else ' (**nuova**)',
            ', '.join(s['units']) or 'nessuna: tabella storica', s.get('panel_targets_voted', ''),
            {True: 'si', False: 'no', None: 'fit non letto'}[s['consumed_by_fit']], s['table_sha256'][:12]))
    lines_md += ['', '## Unita di banca', '',
                 '| Unita | Studio | Linea | Modalita | Chimica | Contesti | Donatori/cloni | Cellule | Controlli | Bersagli (pannello) | Grezzo GB | Banca+campioni GB | Destinazione |',
                 '|---|---|---|---|---|---:|---:|---:|---:|---|---:|---:|---|']
    for unit, d in registry_units.items():
        dest = d['destination']
        lines_md.append('| `%s` | %s | %s | %s | %s | %d | %s | %d | %d | %d (%d) | %s | %s | %s |' % (
            unit, d['study'], '/'.join(d['line_group']), '/'.join(d['modality']), '/'.join(d['chemistry']),
            len(d['contexts']), len(d['donors_or_clones']) or 'n.r.', d['cells']['all'], d['cells'].get('control', 0),
            d['native_targets'], d['panel_targets'], '' if d['raw']['bytes'] is None else gb(d['raw']['bytes']),
            gb(d['bank_bytes'] + d['samples_bytes']),
            ('`%s`: %s' % (dest['source'], dest['role'])) if dest['source'] else dest['role']))
    lines_md += ['', '## Record del catalogo r4 senza banca', '', '| Record | Stato dichiarato dal catalogo |', '|---|---|']
    for r in records:
        if not r['units']:
            lines_md.append('| `%s` | %s: %s |' % (r['record_id'], r['destination'], (r['catalogue_state'] or '').replace('|', '/')))
    Path(out_md).write_text('\n'.join(lines_md) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in summary.items() if not isinstance(v, (list, dict))}, ensure_ascii=False))


if __name__ == '__main__':
    main()
