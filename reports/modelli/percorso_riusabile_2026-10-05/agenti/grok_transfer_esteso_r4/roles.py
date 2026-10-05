"""Scientific roles for catalogo_r4. Open is not an exclusion and not a completed fit."""
from __future__ import annotations

import json

from pins import CATALOGUE, CD4_SOURCE, SPLIT, STORAGE_SHA256, UNION_STATE

ROLES = {'supervision', 'anchor', 'descriptor', 'validation', 'duplicate', 'ineligible'}


def _row(record_id, role, evidence, **extra):
    if role not in ROLES and role != 'open':
        raise ValueError('bad role')
    item = {'record_id': record_id, 'role': role, 'evidence': evidence}
    item.update(extra)
    if role in {'validation', 'duplicate', 'ineligible'}:
        if not item.get('reason') or not item.get('review_condition'):
            raise ValueError('unjustified exclusion: ' + record_id)
    return item


def classify(record_id):
    """Exact ids only. An unlisted id stays open."""
    cd4 = {f'remote/cd4_D{donor}_{state}' for donor in (1, 2, 3, 4)
           for state in ('Rest', 'Stim8hr', 'Stim48hr')}
    if record_id in cd4:
        return _row(record_id, 'supervision',
                    'Marson 2025 CRISPRi Flex. Twelve donor x state units are subcontexts of CD4T, one source cd4_mix.',
                    transfer_source_id=CD4_SOURCE, line='CD4T', weight_policy='one biological source',
                    context_id=record_id.split('/', 1)[1])
    mouse = {
        'remote/scp_LaraAstiasoHuntly2023_exvivo', 'remote/scp_LaraAstiasoHuntly2023_invivo',
        'remote/scp_LaraAstiasoHuntly2023_leukemia', 'remote/scp_LiangWang2023',
        'remote/scp_SantinhaPlatt2023'}
    if record_id in mouse:
        return _row(record_id, 'ineligible', 'Mouse screen. The transfer axis is human.',
                    reason='human axis incompatible',
                    review_condition='reopen only on a mouse axis, not by adding it to this human transfer')
    enhancer = {
        'remote/scp_GasperiniShendure2019_atscale', 'remote/scp_GasperiniShendure2019_highMOI',
        'remote/scp_GasperiniShendure2019_lowMOI', 'remote/scp_XieHon2017',
        'remote/scp_SchraivogelSteinmetz2020_TAP_SCREEN__chromosome_11_screen',
        'remote/scp_SchraivogelSteinmetz2020_TAP_SCREEN__chromosome_8_screen'}
    if record_id in enhancer:
        return _row(record_id, 'ineligible', 'Enhancer screen: the named targets are not genes.',
                    reason='targets are not genes',
                    review_condition='reopen if a gene-target map is published for this screen')
    if record_id == 'remote/scp_WesselsSatija2023':
        return _row(record_id, 'ineligible', 'Cas13 guide pairs, no single gene target.',
                    reason='no single gene target',
                    review_condition='reopen if single-gene calls are released')
    no_counts = {
        'remote/scp_GehringPachter2019', 'remote/scp_JoungZhang2023_atlas',
        'remote/scp_JoungZhang2023_combinatorial', 'remote/scp_WeinrebKlein2020'}
    if record_id in no_counts:
        return _row(record_id, 'ineligible', 'No integer count layer. The missing adapter is a consequence, not the reason.',
                    reason='no integer count layer',
                    review_condition='reopen if an integer count layer is released')
    proteins = {
        'remote/scp_FrangiehIzar2021_protein', 'remote/scp_PapalexiSatija2021_eccite_arrayed_protein',
        'remote/scp_PapalexiSatija2021_eccite_protein'}
    if record_id in proteins:
        return _row(record_id, 'descriptor',
                    'Surface-protein ADT matrix, not an RNA count_sum. Auxiliary only.',
                    transfer_source_id='protein_adt', context_id=record_id)
    duplicates = {
        'remote/scp_NadigOConner2024_hepg2': 'ingested/hepg2_nadig',
        'remote/scp_NadigOConner2024_jurkat': 'ingested/jurkat_nadig',
        'remote/scp_ReplogleWeissman2022_K562_essential': 'ingested/replogle_k562_essential',
        'remote/scp_ReplogleWeissman2022_K562_gwps': 'ingested/replogle_k562_gwps',
        'remote/scp_ReplogleWeissman2022_rpe1': 'ingested/replogle_rpe1',
        'remote/southard_fibroblast_CRISPRa_mean_pop': 'aggregate_only/southard_*_mean_pop',
        'remote/southard_RPE1_CRISPRa_mean_pop': 'aggregate_only/southard_*_mean_pop',
        'ingested/a549_ko': 'remote/a549_GSE345058_SC_raw_normalized_counts',
        'ingested/kolf_small': 'remote/kolf_KOLF_Chromatin_Modifiers_QC_Filtered+remote/kolf_KOLF_Metabolic_Enzymes_QC_Filtered',
        'ingested/kolf_strong': 'remote/kolf_KOLF_Strong_Perturbations',
        'ingested/h1_vcc2025_trainval': 'remote/h1_train+remote/h1_val',
    }
    if record_id in duplicates:
        return _row(record_id, 'duplicate', 'Same experiment as ' + duplicates[record_id] + '. Not a second mix weight.',
                    reason='republication or ingested bundle of a primary record',
                    review_condition='do not merge by a similar name; reopen only if this card is a different experiment',
                    duplicate_of=duplicates[record_id])
    drugs = {
        'remote/scp_AissaBenevolenskaya2021', 'remote/scp_ChangYe2021', 'remote/scp_CuiHacohen2023',
        'remote/scp_LotfollahiTheis2023', 'remote/scp_McFarlandTsherniak2020',
        'remote/scp_SchiebingerLander2019_GSE106340', 'remote/scp_SchiebingerLander2019_GSE115943',
        'remote/scp_SrivatsanTrapnell2020_sciplex2', 'remote/scp_SrivatsanTrapnell2020_sciplex3',
        'remote/scp_SrivatsanTrapnell2020_sciplex4', 'remote/scp_ZhaoSims2021'}
    if record_id in drugs:
        return _row(record_id, 'open',
                    'Drug or cytokine, or a file that mixes them with CRISPR. A separate head is required. Not an exclusion.')
    if record_id == 'ingested/jurkat_gse249595':
        return _row(record_id, 'open', 'GSE249595 has no guide calls. Stays open until an assignment is proven.')
    if record_id in {'ingested/hipsci_gw_fitness', 'ingested/hipsci_gw_nonfitness'}:
        counts = '36' if record_id.endswith('fitness') else '12'
        return _row(record_id, 'open',
                    f'HIPSCI genome-wide NTC cells are {counts} in total. Unassigned cells are not controls. Not supervision.')
    if record_id in {'remote/scp_TianKampmann2019_iPSC', 'remote/scp_TianKampmann2019_day7neuron'}:
        return _row(record_id, 'open',
                    'Tian 2019 droplets are unfiltered. A QC rule has to be written before effects are read. Not a permanent exclusion.')
    if record_id == 'remote/scp_NormanWeissman2019_filtered':
        return _row(record_id, 'open',
                    'Norman is combinatorial CRISPRa. Original compound components are required before any statistic. The bank is kept.')
    if record_id == 'ingested/tian_norman':
        return _row(record_id, 'open',
                    'One ingested bundle mixes Tian 2019 QC, Tian 2021 CRISPRi, Tian 2021 CRISPRa and Norman compounds. It is not one role.')
    if record_id in {'remote/scp_AdamsonWeissman2016_GSM2406675_10X001',
                     'remote/scp_AdamsonWeissman2016_GSM2406677_10X005',
                     'remote/scp_AdamsonWeissman2016_GSM2406681_10X010'}:
        return _row(record_id, 'open', 'Adamson controls are plasmid names. A declared label map is required.')
    if record_id in {'remote/scp_DixitRegev2016_K562_TFs_13_days', 'remote/scp_DixitRegev2016_K562_TFs_7_days',
                     'remote/scp_DixitRegev2016_K562_TFs_High_MOI'}:
        return _row(record_id, 'open', 'Dixit modality is not confirmed and the controls are intergenic cuts.')
    if record_id == 'remote/scp_PapalexiSatija2021_eccite_RNA':
        return _row(record_id, 'open', 'ECCITE RNA labels are GENEg1 without a separator. A declared map is required.')
    if record_id in {'remote/southard_fibroblast_CRISPRa_final_pop', 'remote/southard_RPE1_CRISPRa_final_population',
                     'ingested/southard'}:
        return _row(record_id, 'open', 'Southard cell ingestion was still open in the catalogue. Not excluded for size.')
    if record_id == 'aggregate_only/dld1_gse337988':
        return _row(record_id, 'open', 'DLD-1 needs a channel-matrix adapter. The adapter is work, not an exclusion.')
    if record_id == 'aggregate_only/mixscale (parte DE)':
        return _row(record_id, 'open', 'Mixscale is RDS and is not converted. Six lines stay in the corpus as open work.')
    if record_id == 'aggregate_only/catalogo_accessioni':
        return _row(record_id, 'open', 'Accessions named by the catalogue are not reconciled one by one.')
    bundles = {
        'ingested/scp_ko_frangieh_sunshine_papalexi': 'Frangieh, Sunshine and Papalexi are separate remote records.',
        'ingested/scp_tcells_shifrut_datlinger': 'Shifrut and Datlinger stay on their own remote records.',
        'ingested/scp_k562_hek_dixit_xu': 'Dixit and Xu stay on their own remote records.',
    }
    if record_id in bundles:
        return _row(record_id, 'open', bundles[record_id] + ' The ingested bundle is not a second source.')
    if record_id == 'remote/kolf_KOLF_Pan_Genome_QC_Filtered':
        return _row(record_id, 'supervision',
                    'CRISPRi pan-genome bank kolf_pan_genome is closed. It is not the kolf21j anchor until that link is checked.',
                    transfer_source_id='kolf_pan', context_id='kolf_pan_genome',
                    review_condition='do not fold into kolf_small; anchor link unverified')
    if record_id == 'ingested/hepg2_nadig':
        return _row(record_id, 'validation',
                    'HepG2 was a pilot held-out in regimes C and J. This manifest does not invent a new HepG2 split.',
                    reason='already used as a held line in the frozen splits',
                    review_condition='supervision only in a fold that does not hold HepG2 out')
    if record_id == 'aggregate_only/depmap_24q4':
        return _row(record_id, 'descriptor', 'DepMap 24Q4 basal covariates. Never supervision.',
                    transfer_source_id='depmap_24q4', context_id='depmap_24q4')
    if record_id == 'aggregate_only/southard_*_mean_pop':
        return _row(record_id, 'descriptor', 'Population-mean tables, not cell count_sum.',
                    transfer_source_id='southard_mean_pop', context_id='southard_mean_pop')
    primary = {
        'ingested/replogle_k562_gwps': ('k562', 'CRISPRi', 'Original t25 source. The new GWPS bank is not in the r8 index; the t25 cache stays.'),
        'ingested/replogle_k562_essential': ('k562_essential', 'CRISPRi', 'Essential screen, a different source from GWPS. Bank closed in r8.'),
        'ingested/replogle_rpe1': ('rpe1', 'CRISPRi', 'Replogle RPE1 CRISPRi. Bank closed in r8.'),
        'ingested/hipsci_targeted_19': ('hipsci_targeted', 'CRISPRi', 'Nineteen lines, matched NTC. Unguided cells stay out of supervision.'),
        'ingested/jurkat_nadig': ('jurkat_nadig', 'CRISPRi', 'Nadig Jurkat CRISPRi, used in the pilot.'),
        'remote/h1_train': ('h1', 'CRISPRi', 'VCC 2025 train. The H1 test reserve is not this record and is not downloaded.'),
        'remote/h1_val': ('h1', 'CRISPRi', 'VCC 2025 validation file of the same experiment. The test reserve stays closed.'),
        'remote/kolf_KOLF_Chromatin_Modifiers_QC_Filtered': ('kolf_chromatin', 'CRISPRi', 'KOLF chromatin CRISPRi. Bank closed.'),
        'remote/kolf_KOLF_Metabolic_Enzymes_QC_Filtered': ('kolf_metabolic', 'CRISPRi', 'KOLF metabolic CRISPRi. Bank closed.'),
        'remote/kolf_KOLF_Strong_Perturbations': ('kolf_strong', 'CRISPRi', 'KOLF strong CRISPRi. Bank closed.'),
        'remote/a549_GSE345058_SC_raw_normalized_counts': ('a549_ko', 'KO', 'Cas9 knockout. A separate arm, not pooled with CRISPRi.'),
        'remote/scp_TianKampmann2021_CRISPRi': ('tian2021_crispri', 'CRISPRi', 'Tian 2021 neuron CRISPRi. Bank closed. Control label in the spec is control and must be mapped explicitly at derivation.'),
        'remote/scp_TianKampmann2021_CRISPRa': ('tian2021_crispra', 'CRISPRa', 'Tian 2021 CRISPRa. Not pooled with the CRISPRi arm.'),
        'remote/scp_XuCao2023': ('xu2023', 'CRISPRi', 'Xu HEK293 CRISPRi, distinct from Orion HEK293T.'),
        'remote/scp_FrangiehIzar2021_RNA': ('frangieh_rna', 'CRISPR', 'Frangieh RNA. Not the protein matrix and not pooled with CRISPRi until the modality is partitioned.'),
        'remote/scp_PapalexiSatija2021_eccite_arrayed_RNA': ('papalexi_arrayed', 'CRISPR', 'Arrayed RNA, distinct from the unmapped ECCITE labels.'),
        'remote/scp_SunshineHein2023': ('sunshine', 'CRISPR-cas9', 'Sunshine Cas9. Not pooled with CRISPRi.'),
        'remote/scp_DatlingerBock2017': ('datlinger2017', 'CRISPR', 'Datlinger 2017. Modality stays CRISPR, not CRISPRi.'),
        'remote/scp_DatlingerBock2021': ('datlinger2021', 'CRISPR', 'Datlinger 2021. Context is read from the bank, not renamed.'),
        'remote/scp_ShifrutMarson2018': ('shifrut', 'CRISPR', 'Shifrut is related to CD4T and leaves with it in a severe fold. It is not a second CD4 weight.'),
    }
    if record_id in primary:
        source, modality, evidence = primary[record_id]
        return _row(record_id, 'supervision', evidence, transfer_source_id=source, modality=modality,
                    context_id=source)
    return _row(record_id, 'open', 'No source-evidence rule matched this id. It is not dropped.')


def hipsci_unions(state):
    units = []
    for name, unit in (state.get('units') or {}).items():
        units.append({'unit': name, 'state': unit.get('state'),
                      'checked': unit.get('state') == UNION_STATE
                      and unit.get('verified_parts') == unit.get('expected_parts')})
    return units


def build_manifest(catalogue, storage, hipsci_state):
    records = []
    for section, entries in catalogue.items():
        for item in entries:
            source_id = item['id'] if isinstance(item, dict) else item[0]
            records.append(classify(section + '/' + source_id))
    extra = []
    for name, source, line in (('orion_hct116', 'orion_hct116', 'HCT116'),
                               ('orion_hek293t', 'orion_hek293t', 'HEK293T')):
        extra.append(_row('storage_only/' + name, 'supervision',
                          'Closed CRISPRi bank in cloud_catalog_r10. Absent from catalogo_r4, so the catalogue is not complete.',
                          transfer_source_id=source, line=line, context_id=name))
    open_ids = [row['record_id'] for row in records if row['role'] == 'open']
    contexts = []
    for row in records + extra:
        if row['role'] != 'supervision':
            continue
        contexts.append({'context_id': row.get('context_id', row['record_id']),
                         'transfer_source_id': row.get('transfer_source_id'),
                         'record_id': row['record_id'], 'state': 'not_ready',
                         'reason': 'bank may be closed; count_sum effects are not derived and the gene symbols are not in the bank files'})
    return {
        'kind': 'fit_manifest',
        'fit_admitted': False,
        'blockers': ['open records remain', 'supervision contexts are not ready',
                     'gene symbols are not stored in the pinned bank outputs',
                     'full fit waits for a frozen admitted corpus'],
        'storage_provenance': {
            'path': 'reports/modelli/percorso_riusabile_2026-10-05/cloud_catalog_r10/README.md',
            'manifest': 'reports/modelli/percorso_riusabile_2026-10-05/cloud_catalog_r10/manifest.json',
            'superseded_for_new_launches': ['r8', 'r9'],
            'sha256': storage['storage_manifest_sha256'],
            'named_pin': STORAGE_SHA256,
            'training_ready': storage['training_ready'],
            'training_ready_meaning': 'expected storage flag, not scientific ineligibility',
        },
        'hipsci_r5': {'sha256': storage['hipsci_r5']['sha256'], 'units': hipsci_unions(hipsci_state),
                      'verified_jobs': storage['hipsci_r5']['verified_jobs']},
        'catalogue': {'path': str(CATALOGUE), 'n': len(records), 'later_catalogue_folder': None},
        'records': records,
        'storage_additions': extra,
        'n_open': len(open_ids),
        'contexts': contexts,
        'folds': {'split': dict(SPLIT), 'cells_per_target': 400, 'seed_indices': [0, 1, 2, 3, 4],
                  'inputs': 'same pinned bank version and hash on every fold; the held line and its controls are dropped from the fit',
                  'axis': 'bound gene_names.csv sha256 25bfa66715e186bebabce7ac788bbcea47e2bf59ca70be1f8f3a06f2f0e47201 before any statistic',
                  'qc': ['Tian2019 unfiltered droplets stay out of effects',
                         'HIPSCI unassigned is not a control',
                         'GSE249595 has no guide calls',
                         'modalities are not pooled']},
        'source_policy': 'one weight per biological source; CD4 donors are cell-weighted inside a condition and the three conditions are equal-weighted',
    }


def write_protocol(path):
    payload = {
        'registered_before_results': True,
        'observed_result': None,
        'unchanged': {'sources': ['k562', 'cd4_mix', 'orion_hct116', 'orion_hek293t'],
                      'weight': 1.0, 'amplitude': 1.576, 'gamma': 1.0, 'reliability_scale': 100,
                      'emission_cells': 400, 'seed_indices': [0, 1, 2, 3, 4]},
        'reading': {
            'resolved': 'abs(mean of paired deltas) > 2 * sd / sqrt(5)',
            'favorable_line': 'six-member delta resolved positive, the same without Jaccard resolved positive, PDS not resolved negative, expanded local score >= 0.100',
            'early_stop': 'a resolved negative expanded_J - original_J stops the remaining comparison runs only',
            'catalogue_coverage_continues': True,
            'loss_is_not_a_decision_metric': True,
        },
    }
    path.write_text(json.dumps(payload, indent=1), encoding='utf-8')
    return payload
