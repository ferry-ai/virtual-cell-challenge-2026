"""Pinned identities for r4. r10 is the storage index, not a fit manifest."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
STORAGE_INDEX = REPO / 'reports/modelli/percorso_riusabile_2026-10-05/cloud_catalog_r10/README.md'
STORAGE_MANIFEST = REPO / 'reports/modelli/percorso_riusabile_2026-10-05/cloud_catalog_r10/manifest.json'
STORAGE_SHA256 = '7134c13c741e04b1bb90b15f42afd2a50e653454aca17e49005edcad6f2e7fdf'
SUPERSEDED_STORAGE = {
    'r8': '272fced871671d7ab6295c0e67b29bec94a5275c20fdd67fc2ab3754897b6fb4',
    'r9': '4a866f404a337baf1ad1b3e9dfa18b609541fbeabd2e790cd6622b4fb4018a1a',
}
HIPSCI_R5 = REPO / 'reports/modelli/percorso_riusabile_2026-10-05/hipsci_verified_r5/state.json'
CATALOGUE = REPO / 'reports/sorgenti/corpus_cellulare_2026-09-30/catalogo_r4/catalogo.json'
UNION_STATE = 'remote_complete_union_checked'
FORBIDDEN_DATASET = 'rlead-bench-cube-r2'
OPEN_PARENT_KERNEL = 'davideferrante11/vcc-derivatives-rlab-k562-gwps-r3'
ORIGINAL_SOURCES = ('k562', 'cd4_mix', 'orion_hct116', 'orion_hek293t')
CD4_SOURCE = 'cd4_mix'
AMPLITUDE = 1.576
GAMMA = 1.0
RELIABILITY_SCALE = 100.0
SOURCE_WEIGHT = 1.0
ESTIMATOR = {
    'min_expected': 1.0,
    'pseudo': 0.5,
    'pseudo_scale': 'constant',
    'min_cells': 10.0,
    'min_control_frac': 1e-6,
    'phi': 0.2,
    'outcome_dependent_mask': False,
    'matrix': 'count_sum',
}
CONTROL_LABELS = {'NTC': 'non-targeting'}
BIO = ('study', 'context', 'donor_or_clone', 'condition', 'modality', 'chemistry')
GROUP = ('study', 'context', 'condition', 'modality', 'chemistry')
EMISSION = {
    'effects_scale': 1.5,
    'gene_dispersion': True,
    'gene_dispersion_scale': 1.0,
    'cells_per_target': 400,
    'generator_seed': 20260912,
    'seed_indices': [0, 1, 2, 3, 4],
    'trial': 'trial-ext-profile',
}
SPLIT = {'module': 'reports/modelli/risposta_contesto_2026-10-02/splits.py',
         'salt': 'r-lead-2026-10-02', 'n_folds': 5, 'regimes': ['C', 'J']}
AXIS_SHA256 = '25bfa66715e186bebabce7ac788bbcea47e2bf59ca70be1f8f3a06f2f0e47201'
AXIS_GENES = 18533
AXIS_FILE = Path(r'C:\Users\ferra\vcc2026-data\processed\ingestione_completa_2026-10-03'
                 r'\kaggle_code_cd4_r1\gene_names.csv')
AXIS_DATASET = {
    'davideferrante11': 'davideferrante11/vcc-ingest-code-cd4-r1',
    'davidmaisterx': 'davidmaisterx/vcc-ingest-code-cd4-r1',
}
RAM_BUDGET_BYTES = 6 * 1024 ** 3
OUTPUT_BUDGET_BYTES = 10 * 1024 ** 3
CONFIG = {'davideferrante11': '.kaggle-davideferrante11', 'davidmaisterx': '.kaggle',
          'davideferante': '.kaggle-codex'}
SECRET_ENV = ('KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN', 'KAGGLE_CONFIG_DIR')
CIS_RECIPE_PAIRS = 'reports/cis_2026-09-17/k562_neighbour_pairs.csv'
CIS_PAIRS = REPO / 'reports/trasferimento/cis_2026-09-17/k562_neighbour_pairs.csv'
CIS_MAX_DISTANCE_BP = 5000
CIS_SCALE = 2.0
# Transcribed from TRANSFER_IDENTICO_r1.md / CP-0052. Not remeasured in this session.
REFERENCE_T28_SCORE = 0.14484520500645978
