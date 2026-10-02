"""Hand-curated registry of the perturbation effect tables R-LEAD can read on this machine.

One entry per effect table (a "study unit": one study, one line, one state). Every attribute that
is not read from the files themselves names its evidence in ``evidence``. Biological identity is
kept separate from the study: ``line`` is the cell line or primary cell type, ``group`` the unit
that a C/J split holds out whole (a line together with every derivative or clone of the same
donor), ``donor`` the individual where it matters. Identities of the competition contexts A/B/C
are never written here (root CLAUDE.md).

Assay values marked ``(da verificare)`` come from secondary notes, not from a primary metadata
file; they are strata, never filters.
"""
from __future__ import annotations

UNIVERSES = 'processed'          # relative to the data root

HIPSCI_LINES = ['eipl_1', 'eipl_3', 'fiaj_1', 'fiaj_3', 'iudw_1', 'iudw_4', 'jejf_2', 'jejf_3', 'kolf_2',
                'kolf_3', 'oikd_2', 'oikd_5', 'paab_3', 'paab_4', 'pipw_4', 'pipw_5', 'tolg_4', 'tolg_6',
                'zapk_3']

_EV_SRC = 'reports/sorgenti/corpus_cellulare_2026-09-30/sources.yaml'
_EV_CAT = 'reports/sorgenti/corpus_cellulare_2026-09-30/catalogo_r4/CATALOGO.md'
_EV_AUD = 'reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md'


def _t(id, universe, stem, line, group, study, assay, modality, cells, *, donor=None, state=None,
       evidence=(), role='bench', note=''):
    return dict(id=id, universe=universe, stem=stem, line=line, group=group, donor=donor, state=state,
                study=study, assay=assay, modality=modality, cells=cells, role=role, note=note,
                evidence=list(evidence) or [_EV_SRC])


TABLES = [
    _t('k562_gwps', 'universe_k562_2026-09-26', 'k562', 'K562', 'K562', 'replogle2022_gwps', "10x 3'", 'CRISPRi',
       'Drive (65,8 GB) e Kaggle rlab-k562-gwps-r3', evidence=[_EV_SRC, _EV_AUD, _EV_CAT]),
    _t('k562_essential', 'universe_k562ess_2026-09-26', 'k562ess', 'K562', 'K562', 'replogle2022_essential',
       "10x 3'", 'CRISPRi', 'Kaggle rlab-k562-essential-r2', evidence=[_EV_SRC, _EV_CAT]),
    _t('k562_viperturb', 'universe_viperturb_2026-09-27_p1', 'viperturb', 'K562', 'K562', 'viperturb_flex',
       '10x Flex', 'CRISPRi', 'remote (Zenodo RDS prefiltrato)', evidence=[_EV_SRC, _EV_AUD],
       note='halves halfa/halfb in universe_viperturb_2026-09-28_half{a,b}'),
    _t('rpe1', 'universe_rpe1_2026-09-26', 'rpe1', 'RPE1', 'RPE1', 'replogle2022_rpe1', "10x 3'", 'CRISPRi',
       'Kaggle rlab-rpe1-r2', evidence=[_EV_SRC, _EV_CAT]),
    _t('hepg2_nadig', 'generalizzazione_contesti_2026-10-02/universe_hepg2_nadig_me1', 'hepg2', 'HepG2', 'HepG2',
       'nadig2025_hepg2', "10x 3' (da verificare)", 'CRISPRi', 'local raw/nadig_hepg2 (0,85 GB)',
       evidence=[_EV_SRC, 'reports/analisi/lead_audit_2026-10-01/REVISIONE.md'],
       note='built in this study from local cells (hepg2_universe.py); development line'),
    _t('cd4_rest', 'universe_cd4_2026-09-27_me1', 'cd4_Rest', 'CD4 T', 'CD4T', 'marson2025', '10x Flex (GEMX_flex_v1)',
       'CRISPRi', 'remote S3 (1,7 TB)', state='Rest', donor='4 donors pooled',
       evidence=[_EV_SRC, _EV_AUD]),
    _t('cd4_stim8hr', 'universe_cd4_2026-09-27_me1', 'cd4_Stim8hr', 'CD4 T', 'CD4T', 'marson2025',
       '10x Flex (GEMX_flex_v1)', 'CRISPRi', 'remote S3 (1,7 TB)', state='Stim8hr', donor='4 donors pooled',
       evidence=[_EV_SRC, _EV_AUD]),
    _t('cd4_stim48hr', 'universe_cd4_2026-09-27_me1', 'cd4_Stim48hr', 'CD4 T', 'CD4T', 'marson2025',
       '10x Flex (GEMX_flex_v1)', 'CRISPRi', 'remote S3 (1,7 TB)', state='Stim48hr', donor='4 donors pooled',
       evidence=[_EV_SRC, _EV_AUD]),
    _t('hct116', 'universe_orion_hct116_2026-09-27_me1', 'orion_hct116', 'HCT116', 'HCT116', 'xaira_orion',
       "GEM-X 5' (schede, da verificare)", 'CRISPRi', 'remote Hugging Face', evidence=[_EV_SRC, _EV_AUD]),
    _t('hek293t', 'universe_orion_hek293t_2026-09-27_me1', 'orion_hek293t', 'HEK293T', 'HEK293T', 'xaira_orion',
       "GEM-X 5' (schede, da verificare)", 'CRISPRi', 'remote Hugging Face', evidence=[_EV_SRC, _EV_AUD]),
    _t('kolf21j', 'universe_kolf_2026-09-27_me1', 'kolf', 'KOLF2.1J (iPSC)', 'iPSC', 'nourreddine2026_kolf',
       'da verificare', 'CRISPRi', 'remote Figshare+ (189 GB)', donor='kolf',
       evidence=[_EV_SRC, 'reports/sorgenti/universo_kolf_2026-09-27/RISULTATI.md'],
       note='KOLF2.1J is a subclone of HIPSCI HPSI0114i-kolf_2: same donor as hipsci_kolf_2/3 (literature, iNDI)'),
] + [
    _t(f'hipsci_{l}', f'universe_hipsci_{l}_2026-09-28_p2', f'hipsci_{l}', f'HIPSCI {l} (iPSC)', 'iPSC',
       'hipsci_targeted19', 'da verificare', 'CRISPRi', 'Kaggle rlab-hipsci-targeted19', donor=l.split('_')[0],
       evidence=[_EV_SRC, 'reports/sorgenti/universo_hipsci_2026-09-27/RISULTATI.md'])
    for l in HIPSCI_LINES
] + [
    _t('hipsci_gwfit', 'universe_hipsci_gwfit_2026-09-27_me1', 'hipsci_gwfit', 'iPSC pool (HIPSCI)', 'iPSC',
       'hipsci_gw_fitness', 'da verificare', 'CRISPRi', 'Kaggle rlab-hipsci-gwfit', donor='pool',
       role='excluded: 36 NTC cells (me1); ua1 uses unassigned cells as controls',
       evidence=[_EV_SRC, _EV_CAT]),
    _t('hipsci_gwnonfit', 'universe_hipsci_gwnonfit_2026-09-27_me1', 'hipsci_gwnonfit', 'iPSC pool (HIPSCI)', 'iPSC',
       'hipsci_gw_nonfitness', 'da verificare', 'CRISPRi', 'Kaggle rlab-hipsci-gwnonfit', donor='pool',
       role='excluded: 12 NTC cells (me1); ua1 uses unassigned cells as controls',
       evidence=[_EV_SRC, _EV_CAT]),
    _t('a549_ko', 'universe_a549_2026-09-27_me1', 'a549', 'A549', 'A549', 'liu2026_a549', 'da verificare', 'KO',
       'Kaggle rlab-a549', role='other modality: recorded, not in the CRISPRi bench'),
    _t('hs27_crispra', 'universe_southard_hs27_2026-09-27_p2', 'southard_hs27', 'Hs27', 'Hs27', 'southard2025',
       'da verificare', 'CRISPRa', 'Zenodo / ingestion J09', role='other modality: recorded, not in the CRISPRi bench'),
]

# Sources the matrix must name although no effect table is on this machine (P0, file and step).
NOT_LOCAL = [
    dict(id='jurkat_nadig', line='Jurkat', group='Jurkat', modality='CRISPRi', study='nadig2025_jurkat',
         cells='Kaggle rlab-jurkat-nadig, Drive (job 103), 262.956 cells', missing='no local effect table or cells',
         reads='in r1-r3 training; 21 T groups read in the r2 diagnostics (lead_audit_2026-10-01/REVISIONE.md §3.1)'),
    dict(id='h1_vcc2025_trainval', line='H1 (hESC)', group='H1', modality='CRISPRi', study='vcc2025',
         cells='Kaggle rlab-h1-vcc2025-trainval, 320.200 cells', missing='no local effect table or cells',
         reads='in r1-r3 training (17 T groups in r2 diagnostics); the 2025 test split stays closed'),
    dict(id='jurkat_gse249595', line='Jurkat', group='Jurkat', modality='CRISPRi', study='gse249595',
         cells='local MTX channels', missing='no guide calls in the release: not supervisable',
         reads='none recorded'),
    dict(id='dld1_gse337988', line='DLD-1', group='DLD-1', modality='CRISPRi', study='gse337988',
         cells='to verify', missing='effects (LFC, SE) only on a targeted response panel; no control profile',
         reads='audit and ceiling 24/09'),
    dict(id='mixscale', line='six lines', group='mixscale', modality='CRISPRi', study='mixscale',
         cells='remote Seurat objects (about 20 GB)', missing='DE tables only; no separate basal profiles',
         reads='H6 and pattern 24/09'),
    dict(id='tian_norman', line='iPSC, iPSC neurons, K562', group='iPSC/neuron/K562', modality='CRISPRi/CRISPRa',
         study='tian2019_2021_norman2019', cells='Kaggle rlab-tian-norman, 623.436 cells',
         missing='no local effect table', reads='in r3 training only'),
    dict(id='scp_third_wave', line='melanoma, T cells, K562, HEK293', group='various', modality='KO/CRISPRi',
         study='frangieh, sunshine, papalexi, shifrut, datlinger, dixit, xu2023', cells='Kaggle rlab-scp-*',
         missing='no local effect table', reads='in no training'),
]

# Official contexts: controls only, identity never written.
COMPETITION_CONTROLS = ['A', 'B', 'C']
