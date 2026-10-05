"""Recipe and mount rules for one t28-shaped prediction from the extended mix.

The mixer cache has no amplitude, no cis head and no effects scale. Stage 100
applies amplitude 1.576 and the original cis pairs once. Stage 45 applies
effects_scale 1.5 once. This module does not train and does not push.
"""
from __future__ import annotations

import json
from pathlib import Path

CONTEXTS = ('A', 'B', 'C')
AMPLITUDE = 1.576
GAMMA = 1.0
RELIABILITY_SCALE = 100.0
WEIGHT = 1.0
EFFECT = 'shrunk'
CIS_PAIRS = 'reports/cis_2026-09-17/k562_neighbour_pairs.csv'
CIS_SHA256 = 'd874c305f12e932d2d43eff629ea7d44c8536b7a198868c8fac10007d01dcf8f'
CIS_MAX_DISTANCE_BP = 5000
CIS_SCALE = 2.0
PANEL_N = 300
PANEL_SHA256 = 'c9c4c9a69f76afd4507e9a7619fe9925c19ff34e5878c7854493683b23bea5ca'
PANEL_FILE_SHA256 = 'f57edd7b912ebd718efc7ee9d0f334772513e7cc418d133ce525470e373b3276'
AXIS_SHA256 = '25bfa66715e186bebabce7ac788bbcea47e2bf59ca70be1f8f3a06f2f0e47201'
AXIS_GENES = 18533
AXIS_BYTES = 119295
REFERENCE_T28_SCORE = 0.14484520500645978
CELLS_PER_TARGET = 400
EFFECTS_SCALE = 1.5
GENE_DISPERSION_SCALE = 1.0
GENERATOR_SEED = 20260912
TRIAL = 'trial-ext-profile'
N_GENES = 18533
RAM_BUDGET_BYTES = 6 * 1024 ** 3
OUTPUT_BUDGET_BYTES = 10 * 1024 ** 3
STAGE45_RESERVE_GIB = 10.0
STAGE48_RESERVE_GIB = 6.0
MOUNT_SLUG = 'davideferrante11/vcc-effects-mix-t25-bank-r1-retry1'
MOUNT_DIR = 'vcc-effects-mix-t25-bank-r1-retry1'
REFUSE_DIR = 'vcc-effects-mix-t25-bank-r1'
KERNEL_SLUG = 'davideferrante11/vcc-generate-t28-extbank-r1'
KERNEL_TITLE = 'vcc-generate-t28-extbank-r1'
AXIS_DATASET = 'davideferrante11/vcc-ingest-code-cd4-r1'
OWNER = 'davideferrante11'
CD4_CONDITIONS = ('cd4_Rest', 'cd4_Stim8hr', 'cd4_Stim48hr')
TABLE_KEYS = ('targets', 'shrunk', 'raw', 'se', 'n_cells', 'meta')


def recipe_from_voted(voted):
    """Weight 1 on every source the mix actually votes. Conditions are not a second vote."""
    names = [str(name) for name in voted]
    if not names or len(names) != len(set(names)):
        raise ValueError('voted sources must be a non-empty set of unique names')
    if 'k562' in names:
        raise ValueError('k562 is absent until a true GWPS table is in the voted cache')
    if 'cd4_mix' in names and any(name in names for name in CD4_CONDITIONS):
        raise ValueError('cd4 conditions already vote once inside cd4_mix')
    extra_cd4 = [name for name in names if name.startswith('cd4_') and name != 'cd4_mix']
    if extra_cd4:
        raise ValueError('cd4 fragments are not extra votes: ' + ','.join(extra_cd4))
    if 'h1_train' in names or 'h1_val' in names:
        raise ValueError('H1 train and val share the one voted source h1')
    weights = {name: WEIGHT for name in sorted(names)}
    return {
        'name': 'extbank-r1',
        'effect': EFFECT,
        'gamma': GAMMA,
        'reliability_scale': RELIABILITY_SCALE,
        'allow_missing_targets': True,
        'allow_foreign_cache': False,
        'common': 'panel',
        'contexts': {
            ctx: {'amplitude': AMPLITUDE, 'weights': dict(weights)} for ctx in CONTEXTS
        },
        'cis': {
            'pairs': CIS_PAIRS,
            'max_distance_bp': CIS_MAX_DISTANCE_BP,
            'scale': CIS_SCALE,
        },
        'why': (
            't25 weight-1 policy on every source this extended mix votes. '
            'k562_essential stays under its own name. Amplitude and the original '
            'cis pairs are applied once downstream, not in the mixer.'
        ),
    }


def accept_source_model(document):
    """The mix receipt that stage 100 is allowed to read. A file is not a fit."""
    if not isinstance(document, dict):
        raise ValueError('source_model is not an object')
    if document.get('status') != 'mixed_accepted_gate':
        raise ValueError('mix status is ' + str(document.get('status')))
    if document.get('amplitude_applied') or document.get('cis_applied') or document.get('effects_scale_applied'):
        raise ValueError('the mix already applied amplitude, cis, or effects_scale')
    if document.get('k562_essential_replaces_k562') is True:
        raise ValueError('k562_essential must not be renamed to k562')
    if document.get('training_ready') is True or document.get('fit_ready') is True:
        raise ValueError('a written mix is not training_ready and not fit_ready')
    if document.get('loss') not in (None,):
        raise ValueError('the linear transfer has no loss')
    sources = document.get('sources')
    if not isinstance(sources, list):
        raise ValueError('source_model has no voted source list')
    return recipe_from_voted(sources)


def mix_dir_allowed(path):
    """True only for the retry mount. The ERROR producer directory is refused."""
    parts = Path(path).parts
    if REFUSE_DIR in parts:
        return False
    return MOUNT_DIR in parts


def require_table_arrays(name, keys, shrunk, raw, se, meta):
    """Refuse a shrunk-only downgrade. cd4_mix keeps a non-finite SE by construction."""
    missing = [key for key in TABLE_KEYS if key not in keys]
    if missing:
        raise ValueError(name + ' is missing ' + ','.join(missing))
    if getattr(shrunk, 'ndim', None) != 2 or getattr(shrunk, 'shape', None) != getattr(raw, 'shape', None):
        raise ValueError(name + ' shrunk and raw shapes differ')
    if getattr(se, 'shape', None) != getattr(shrunk, 'shape', None):
        raise ValueError(name + ' se shape differs from shrunk')
    if name == 'cd4_mix':
        origin = list((meta or {}).get('from') or [])
        if sorted(origin) != sorted(CD4_CONDITIONS):
            raise ValueError('cd4_mix meta.from is not the three condition tables')
        return
    finite = shrunk == shrunk
    if bool(finite.any()) and not bool((se == se)[finite].all()):
        raise ValueError(name + ' has a measured pair without a finite se')


def kernel_metadata():
    return {
        'id': KERNEL_SLUG,
        'title': KERNEL_TITLE,
        'code_file': 'run.py',
        'language': 'python',
        'kernel_type': 'script',
        'is_private': True,
        'enable_gpu': False,
        'enable_tpu': False,
        'enable_internet': False,
        'dataset_sources': [AXIS_DATASET],
        'kernel_sources': [MOUNT_SLUG],
        'competition_sources': [],
    }


def reading_rule():
    return {
        'registered_before_generation': True,
        'what_is_read': 'one official VCC score of the single submitted .vcc',
        'not_attributed_to_one_added_source': True,
        'not_compared_as_a_local_bench_to_the_t28_score': True,
        'reference_t28_official_score': REFERENCE_T28_SCORE,
        'reference_is_not_a_target_or_a_promise': True,
        'no_improvement_band': True,
        'five_seed_bench_before_submission': False,
        'comparison_started': False,
        'local_score': None,
        'loss': None,
        'optimizer': None,
    }


def emission():
    return {
        'effects_scale': EFFECTS_SCALE,
        'gene_dispersion': True,
        'gene_dispersion_scale': GENE_DISPERSION_SCALE,
        'cells_per_target': CELLS_PER_TARGET,
        'generator_seed': GENERATOR_SEED,
        'trial': TRIAL,
        'contexts': list(CONTEXTS),
        'n_perturbations': PANEL_N,
        'n_genes': N_GENES,
        'controls_included': False,
        'depth_bins': False,
        'five_seed_bench': False,
    }


def dumps(payload):
    return json.dumps(payload, indent=2, sort_keys=True)
