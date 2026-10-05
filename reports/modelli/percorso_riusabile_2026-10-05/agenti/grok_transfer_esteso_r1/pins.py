"""Pinned identities for the extended linear transfer. No latest-name lookup."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
MANIFEST = REPO / 'reports/modelli/percorso_riusabile_2026-10-05/cloud_catalog_r7/manifest.json'
MANIFEST_SHA256 = '0c786da9155360e2cbe01604dba37ab5141e71022880be1ab20a4e4fb2f03678'
CATALOGUE = REPO / 'reports/sorgenti/corpus_cellulare_2026-09-30/catalogo_r4/catalogo.json'
FORBIDDEN_DATASET = 'rlead-bench-cube-r2'
ORIGINAL_SOURCES = ('k562', 'cd4_mix', 'orion_hct116', 'orion_hek293t')
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
HIPSCI_LEDGERS = (
    REPO / 'reports/modelli/percorso_riusabile_2026-10-05/hipsci_partition_r1/launches.jsonl',
    REPO / 'reports/modelli/percorso_riusabile_2026-10-05/hipsci_shared_r1/launches.jsonl',
)
HIPSCI_STATE = REPO / 'reports/modelli/percorso_riusabile_2026-10-05/hipsci_verified_r2/state.json'
