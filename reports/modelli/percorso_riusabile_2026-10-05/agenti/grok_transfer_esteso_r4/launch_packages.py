"""Write CPU derivation packages. This module does not call Kaggle and does not push."""
from __future__ import annotations

import ast
import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from cloud_job import POLICY_NAME, code_hashes
from linear_transfer import preparation_allowed
from pins import (AMPLITUDE, AXIS_DATASET, AXIS_FILE, AXIS_GENES, AXIS_SHA256, CATALOGUE,
                  CIS_MAX_DISTANCE_BP, CIS_PAIRS, CIS_RECIPE_PAIRS, CIS_SCALE, CONFIG, EMISSION,
                  ESTIMATOR, FORBIDDEN_DATASET, GAMMA, HERE, OPEN_PARENT_KERNEL, ORIGINAL_SOURCES,
                  OUTPUT_BUDGET_BYTES, RAM_BUDGET_BYTES, REFERENCE_T28_SCORE, RELIABILITY_SCALE,
                  REPO, SOURCE_WEIGHT, STORAGE_MANIFEST, STORAGE_SHA256, SUPERSEDED_STORAGE)
from roles import classify
from split_rule import LINE_GROUPS, N_FOLDS, PROVENANCE, REGIMES, SALT, frozen_splits

POLICY = {
    'name': POLICY_NAME,
    'evidence': (
        'rows.csv has no target_components. h5rows_cd4 writes target as the official symbol when '
        'the Ensembl id maps onto gene_names.csv, and writes the ENSG id when it does not. '
        'orion_job writes gene_target, with NTC for controls. A token is one gene only when it is '
        'an exact symbol on the bound axis. ENSG ids, UNASSIGNED, the label control, and any token '
        'containing + , ; | / or a space are excluded before statistics and are not split.'
    ),
}

# Closed CRISPRi banks with an owner that can mount the bound axis.
# training_vote false means the unit is a subcontext: collapse gives the source one weight.
# Validation lines stay in the launch and leave only the split that holds their line.
def _unit(source, line, *, vote, role='transfer', admitted=True, anchor=False, replaces=False):
    return {'transfer_source_id': source, 'line_group': line, 'modality': 'CRISPRi',
            'training_vote': vote, 'role': role, 'admitted_model': admitted,
            'exclude_only_when_held': True, 'distinct_study_pending_anchor': anchor,
            'replaces_k562': replaces}


WAVE = {
    **{f'D{donor}_{state}': _unit('cd4_mix', 'CD4T', vote=False)
       for donor in (1, 2, 3, 4) for state in ('Rest', 'Stim8hr', 'Stim48hr')},
    'orion_hct116': _unit('orion_hct116', 'HCT116', vote=True),
    'orion_hek293t': _unit('orion_hek293t', 'HEK293T', vote=True),
    'k562_essential': _unit('k562_essential', 'K562', vote=True, replaces=False),
    'hepg2_nadig': _unit('hepg2_nadig', 'HepG2', vote=True, role='validation'),
    'jurkat_nadig': _unit('jurkat_nadig', 'Jurkat', vote=True),
    'rpe1': _unit('rpe1', 'RPE1', vote=True),
    'h1_train': _unit('h1', 'H1', vote=False),
    'h1_val': _unit('h1', 'H1', vote=False),
    'kolf_pan_genome': _unit('kolf_pan_genome', 'iPSC', vote=True, anchor=True),
    'kolf_chromatin': _unit('kolf_chromatin', 'iPSC', vote=True, anchor=True),
    'kolf_metabolic': _unit('kolf_metabolic', 'iPSC', vote=True, anchor=True),
    'kolf_strong': _unit('kolf_strong', 'iPSC', vote=True, anchor=True),
}
PRIORITY = (
    'orion_hct116', 'orion_hek293t', 'D1_Rest', 'rpe1', 'jurkat_nadig',
    'k562_essential', 'D4_Rest', 'D4_Stim8hr', 'D4_Stim48hr',
)


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def split_spec():
    return {'module': 'reports/modelli/risposta_contesto_2026-10-02/splits.py', 'salt': SALT,
            'n_folds': N_FOLDS, 'regimes': list(REGIMES), 'line_groups': list(LINE_GROUPS),
            'provenance': PROVENANCE, 'n_splits': len(frozen_splits())}


def classify_gap(unit):
    name = unit.get('unit', '')
    kernel = unit.get('kernel') or ''
    state = unit.get('bank_state')
    if name in WAVE:
        return None
    if 'gwps' in kernel or 'gwps' in name:
        return ('open_parent_job', 'K562 GWPS is the only parent job still open. This package does not create ' + OPEN_PARENT_KERNEL)
    if name == 'norman2019':
        return ('compound_without_map',
                'Access reader davidmaisterx/vcc-reuse-runtime-norman-ipsc-r1 is COMPLETE and is not rerun. '
                'Norman public v1 has no component map. Compounds are not split. No statistic is launched.')
    if name.startswith('tian2019'):
        return ('qc_open',
                'The same reader verified iPSC public v3 bytes. Tian2019 QC is still open and is not invented. Not a fit.')
    if name == 'hipsci_targeted_19':
        return ('unresolved_controls',
                'Storage is complete on davideferante/vcc-derivatives-hipsci-targeted19-r1. Controls are unresolved and are not invented. '
                'That account has no gene_names.csv dataset in the axis binding. Do not relaunch the bank job.')
    if name.startswith('hipsci_gw'):
        return ('scarce_controls',
                'Owner states the genome-wide unions are storage-complete. This extract has no hash pin. '
                'Unassigned is not a control and the scarce NTC map is not invented. No statistic in this release.')
    if name in {'datlinger2017', 'datlinger2021', 'shifrut2018', 'dixit2016_d13', 'dixit2016_d7',
                'dixit2016_high_moi', 'xu2023', 'frangieh2021', 'papalexi2021_arrayed', 'sunshine2023'}:
        return ('modality_not_partitioned',
                'Closed scPerturb bank. Modality or guide labels are not partitioned onto the bound axis in this dispatch, so no statistic is launched.')
    if name in {'tian2021_crispri', 'tian2021_crispra'}:
        return ('control_label_unmapped',
                'Closed Tian2021 bank. The published control label is control, which this wave does not treat as non-targeting unless a unit map says so. No statistic is launched.')
    if name == 'a549_ko':
        return ('other_modality', 'A549 KO is closed and is not a CRISPRi supervision source. It stays in the inventory.')
    if not kernel or state != 'remote_complete_manifest_checked':
        return ('bank_not_closed', 'bank state is ' + str(state) + '; kernel is ' + (kernel or 'absent'))
    owner = kernel.split('/')[0]
    if owner not in AXIS_DATASET:
        return ('axis_account_unbound',
                'Owner ' + owner + ' has no gene_names.csv dataset in axis_binding_r1.json. Cross-account mount is not assumed.')
    return ('no_source_map',
            'Closed bank without a target-token map in this dispatch. It is not removed from the corpus.')


def recipe_pin():
    """Frozen t25/t28 identity. The cis file is located; the recipe path itself is absent."""
    if not CIS_PAIRS.is_file():
        raise RuntimeError('t25 cis pairs file is absent: ' + str(CIS_PAIRS))
    return {
        'model': 't25_effects_t28_emission', 'hybrid': False,
        'recipe_path': 'configs/recipes/t25.json', 'effect': 'shrunk',
        'amplitude': AMPLITUDE, 'gamma': GAMMA, 'reliability_scale': RELIABILITY_SCALE,
        'source_weight': SOURCE_WEIGHT,
        'new_source_weight_policy': 'frozen t25 weight 1.0 for every admitted source; no tuning on results',
        'estimator': ESTIMATOR,
        'control_pool': 'every donor with non-targeting controls in the biological group, including donors without the target',
        'original_sources': list(ORIGINAL_SOURCES),
        'k562_essential_replaces_k562': False,
        'reference_submission': 't28',
        'reference_official_score': REFERENCE_T28_SCORE,
        'reference_score_is_not_a_local_baseline': True,
        'cache_named_by_recipe': 'processed/multisource_2026-09-27_r9',
        'emission': EMISSION,
        'cis': {
            'recipe_pairs': CIS_RECIPE_PAIRS,
            'recipe_pairs_present': (REPO / CIS_RECIPE_PAIRS).is_file(),
            'located_pairs': 'reports/trasferimento/cis_2026-09-17/k562_neighbour_pairs.csv',
            'located_pairs_sha256': _sha256_file(CIS_PAIRS),
            'located_pairs_bytes': CIS_PAIRS.stat().st_size,
            'max_distance_bp': CIS_MAX_DISTANCE_BP, 'scale': CIS_SCALE,
        },
    }


def build_jobs(observed, axis_bytes):
    if observed.get('storage_manifest_sha256') != STORAGE_SHA256 or not observed.get('matches_r10_pin'):
        raise RuntimeError('r10 manifest hash does not match the pin')
    if observed.get('axis_sha256') != AXIS_SHA256:
        raise RuntimeError('local gene_names.csv hash does not match axis_binding_r1.json')
    by_name = {unit['unit']: unit for unit in observed['units']}
    jobs, gaps = [], []
    for unit in observed['units']:
        gap = classify_gap(unit)
        if gap:
            gaps.append({'unit': unit['unit'], 'reason_code': gap[0], 'evidence': gap[1],
                         'bank_state': unit.get('bank_state'), 'kernel': unit.get('kernel')})
    recipe = recipe_pin()
    for name, identity in WAVE.items():
        bank = by_name.get(name)
        if not bank or not bank.get('parsed'):
            gaps.append({'unit': name, 'reason_code': 'missing_from_r10', 'evidence': 'named wave unit is absent from r10'})
            continue
        if bank.get('bank_state') != 'remote_complete_manifest_checked':
            gaps.append({'unit': name, 'reason_code': 'bank_not_closed', 'evidence': str(bank.get('bank_state'))})
            continue
        owner = bank.get('account') or (bank.get('kernel') or '').split('/')[0]
        if bank.get('account') and bank['account'] != bank['kernel'].split('/')[0]:
            gaps.append({'unit': name, 'reason_code': 'owner_mismatch',
                         'evidence': 'account ' + bank['account'] + ' != kernel owner'})
            continue
        if owner not in AXIS_DATASET:
            gaps.append({'unit': name, 'reason_code': 'axis_account_unbound',
                         'evidence': 'no bound axis dataset for ' + owner})
            continue
        line = bank.get('spec_line_group') or identity['line_group']
        if bank.get('spec_line_group') and bank['spec_line_group'] != identity['line_group']:
            gaps.append({'unit': name, 'reason_code': 'line_group_conflict',
                         'evidence': bank['spec_line_group'] + ' != ' + identity['line_group']})
            continue
        dataset = AXIS_DATASET[owner]
        unit = {
            'unit': name, 'kernel': bank['kernel'], 'owner': owner,
            'relative_path': bank['relative_path'], 'version': bank['version'],
            'version_number': bank.get('version_number'),
            'count_sum_sha256': bank['count_sum_sha256'], 'count_sum_bytes': bank['count_sum_bytes'],
            'rows_sha256': bank['rows_sha256'], 'rows_bytes': bank['rows_bytes'],
            'mask_sha256': bank['mask_sha256'], 'mask_bytes': bank['mask_bytes'],
            'receipt_sha256': bank.get('receipt_sha256'), 'rows': bank.get('rows'),
            'transfer_source_id': identity['transfer_source_id'], 'line_group': line,
            'modality': identity['modality'], 'training_vote': identity['training_vote'],
            'replaces_k562': identity.get('replaces_k562', False),
            'role': identity.get('role', 'transfer'),
            'admitted_model': identity.get('admitted_model', True),
            'exclude_only_when_held': identity.get('exclude_only_when_held', True),
            'distinct_study_pending_anchor': identity.get('distinct_study_pending_anchor', False),
            'component_policy': POLICY, 'control_labels': {'NTC': 'non-targeting'},
        }
        if not unit['version'] or not unit['count_sum_sha256']:
            gaps.append({'unit': name, 'reason_code': 'pin_incomplete', 'evidence': 'version or count_sum hash absent'})
            continue
        params = {
            'kind': 'technical_preparation', 'claims_complete_training': False,
            'claims_complete_corpus': False, 'fit_admitted': False,
            'matrix': 'count_sum', 'ram_budget_bytes': RAM_BUDGET_BYTES,
            'output_budget_bytes': OUTPUT_BUDGET_BYTES, 'storage_sha256': STORAGE_SHA256,
            'global_hidden_targets': [], 'splits': split_spec(), 'units': [unit],
            'code_sha256': code_hashes(), 'recipe': recipe,
            'axis': {'dataset': dataset, 'relative_path': dataset.split('/')[-1],
                     'sha256': AXIS_SHA256, 'genes': AXIS_GENES, 'bytes': axis_bytes,
                     'ordering': 'gene_name CSV row order, zero based official_index'},
        }
        preparation_allowed(params)
        slug = 'vcc-effects-' + name.lower().replace('_', '-') + '-r4'
        jobs.append({'slug': slug, 'owner': owner, 'kernel': bank['kernel'], 'params': params,
                     'enable_gpu': False, 'dataset': dataset})
    return jobs, gaps


def _embed(params):
    sources = {
        'estimator_core.py': (HERE / 'estimator_core.py').read_bytes(),
        'cloud_job.py': (HERE / 'cloud_job.py').read_bytes(),
        'split_rule.py': (HERE / 'split_rule.py').read_bytes(),
        'params.json': json.dumps(params).encode(),
    }
    payload = {filename: {'base64': base64.b64encode(body).decode(), 'sha256': hashlib.sha256(body).hexdigest()}
               for filename, body in sources.items()}
    code = 'import base64,hashlib,json,os,runpy,sys\nfrom pathlib import Path\n'
    code += 'os.chdir("/kaggle/working"); sys.path.insert(0,"/kaggle/working")\n'
    code += 'P=' + repr(payload) + '\n'
    code += 'for name,item in P.items():\n'
    code += ' b=base64.b64decode(item["base64"]);\n'
    code += ' assert hashlib.sha256(b).hexdigest()==item["sha256"]; Path(name).write_bytes(b)\n'
    code += 'runpy.run_path("cloud_job.py",run_name="__main__")\n'
    compile(code, 'run.py', 'exec')
    return code


def write_packages(jobs, destination):
    """Write one private CPU kernel directory per job. Does not push."""
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    written = []
    for job in jobs:
        if job.get('enable_gpu') or FORBIDDEN_DATASET in json.dumps(job):
            raise RuntimeError('refusing gpu or the forbidden dataset')
        if OPEN_PARENT_KERNEL in json.dumps(job):
            raise RuntimeError('refusing the open K562 GWPS kernel')
        stage = root / job['slug']
        if stage.exists():
            raise RuntimeError('package already exists: ' + job['slug'])
        stage.mkdir()
        (stage / 'run.py').write_text(_embed(job['params']), encoding='utf-8')
        (stage / 'params.json').write_text(json.dumps(job['params']), encoding='utf-8')
        meta = {'id': job['owner'] + '/' + job['slug'], 'title': job['slug'], 'code_file': 'run.py',
                'language': 'python', 'kernel_type': 'script', 'is_private': True, 'enable_gpu': False,
                'enable_tpu': False, 'enable_internet': False, 'dataset_sources': [job['dataset']],
                'kernel_sources': [job['kernel']], 'competition_sources': []}
        (stage / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
        written.append({'slug': job['slug'], 'dir': str(stage), 'metadata': meta})
    return written


def parent_push_command(owner, stage):
    config = CONFIG[owner]
    return (
        "Remove-Item Env:KAGGLE_USERNAME,Env:KAGGLE_KEY,Env:KAGGLE_API_TOKEN,Env:KAGGLE_CONFIG_DIR "
        "-ErrorAction SilentlyContinue; "
        f"$env:KAGGLE_CONFIG_DIR = Join-Path $HOME '{config}'; "
        "$py = & .\\scripts\\py.cmd -c \"import sys; print(sys.executable)\"; "
        "$kaggle = Join-Path (Split-Path $py) 'kaggle.exe'; "
        f"& $kaggle kernels push -p '{stage}'"
    )


def dispatch_document(jobs, gaps, written):
    by_slug = {item['slug']: item for item in written}
    packages = []
    for job in jobs:
        unit = job['params']['units'][0]
        stage = by_slug[job['slug']]['dir']
        packages.append({
            'slug': job['slug'], 'owner': job['owner'], 'kernel': job['kernel'],
            'version': unit['version'], 'relative_path': unit['relative_path'],
            'transfer_source_id': unit['transfer_source_id'], 'line_group': unit['line_group'],
            'training_vote': unit['training_vote'], 'replaces_k562': unit['replaces_k562'],
            'role': unit['role'], 'admitted_model': unit['admitted_model'],
            'exclude_only_when_held': unit['exclude_only_when_held'],
            'distinct_study_pending_anchor': unit['distinct_study_pending_anchor'],
            'push_now': True, 'phase': 1,
            'count_sum_sha256': unit['count_sum_sha256'], 'count_sum_bytes': unit['count_sum_bytes'],
            'rows_sha256': unit['rows_sha256'], 'rows_bytes': unit['rows_bytes'],
            'mask_sha256': unit['mask_sha256'], 'mask_bytes': unit['mask_bytes'],
            'receipt_sha256': unit['receipt_sha256'], 'pinned_rows': unit['rows'],
            'axis_sha256': job['params']['axis']['sha256'], 'axis_genes': job['params']['axis']['genes'],
            'axis_dataset': job['dataset'], 'splits': job['params']['splits'],
            'global_hidden_targets': [], 'ram_budget_bytes': RAM_BUDGET_BYTES,
            'output_budget_bytes': OUTPUT_BUDGET_BYTES,
            'output_guard': 'stop before writing a pack whose uncompressed float32 projection exceeds the remaining budget; partial output is not a fit',
            'memory_guard': 'assert n_rows * n_genes * 8 <= 6 GiB before loading count_sum',
            'parent_push_command': parent_push_command(job['owner'], stage),
            'worker_pushed': False,
        })
    return {
        'kind': 'ready_dispatch', 'worker_pushed': False, 'fit_admitted': False,
        'claims_complete_training': False,
        'storage': {'manifest': 'reports/modelli/percorso_riusabile_2026-10-05/cloud_catalog_r10/manifest.json',
                    'sha256': STORAGE_SHA256, 'superseded_for_new_launches': SUPERSEDED_STORAGE,
                    'training_ready': False, 'meaning': 'r10 is a storage index, not a fit manifest'},
        'axis': {'sha256': AXIS_SHA256, 'genes': AXIS_GENES, 'file': str(AXIS_FILE),
                 'datasets': AXIS_DATASET},
        'preflight_command': (
            '.\\scripts\\py.cmd reports/modelli/percorso_riusabile_2026-10-05/agenti/'
            'grok_transfer_esteso_r4/preflight_slots.py '
            'reports/modelli/percorso_riusabile_2026-10-05/agenti/grok_transfer_esteso_r4/preflight.json 20'
        ),
        'push_rule': (
            'Parent only. Fresh preflight first. Cap 5 active kernels per account, counting jobs already RUNNING or QUEUED. '
            'A nonzero status return blocks that source. '
            'Do not push ' + OPEN_PARENT_KERNEL + '. '
            'Do not relaunch davidmaisterx/vcc-reuse-runtime-norman-ipsc-r1 (COMPLETE access reader, not training). '
            'Do not relaunch davideferante/vcc-derivatives-hipsci-targeted19-r1. '
            'Separate sessions do not add RAM. This worker did not push.'
        ),
        'recommended_order': _recommended(jobs),
        'phase2': {
            'push_now': False,
            'script': 'reports/modelli/percorso_riusabile_2026-10-05/agenti/grok_transfer_esteso_r4/release_fit.py',
            'prerequisite': 'phase-1 kernel outputs listed in packages; each output contains source_model.json and statistics/*.npz',
            'action': 'After the phase-1 kernels finish, download or mount those outputs and run release_fit.py on that directory. Do not push a mixer kernel before those outputs exist.',
            'does_not_block_phase_1': True,
        },
        'model': jobs[0]['params']['recipe'] if jobs else None,
        'is_final_d053_catalogue': False,
        'claims_complete_corpus': False,
        'access_reader': {
            'kernel': 'davidmaisterx/vcc-reuse-runtime-norman-ipsc-r1',
            'state': 'COMPLETE',
            'receipt_sha256': 'b779ab8a5518674114c4c780a757666b412a2777a539b72b7b90af2a6d1e43fa',
            'meaning': 'Norman public v1 and iPSC public v3 bytes were read. This is not a fit and is not relaunched.',
        },
        'do_not_relaunch': [
            OPEN_PARENT_KERNEL,
            'davidmaisterx/vcc-reuse-runtime-norman-ipsc-r1',
            'davideferante/vcc-derivatives-hipsci-targeted19-r1',
        ],
        'packages': packages,
        'not_in_this_dispatch': gaps,
        'not_in_r10': [
            {'unit': 'k562_gwps', 'reason_code': 'open_parent_job',
             'evidence': 'Parent kernel ' + OPEN_PARENT_KERNEL + ' stays RUNNING. It is not duplicated and is not replaced by k562_essential.'},
            {'unit': 'GSE249595', 'reason_code': 'guides_absent',
             'evidence': 'ingested/jurkat_gse249595 has no guide calls. It is not an r10 unit. The calls are not invented.'},
        ],
        'n_packages': len(packages),
        'n_splits_per_package': len(frozen_splits()),
        'inventory': 'inventory.json',
    }


def _recommended(jobs):
    rank = {name: index for index, name in enumerate(PRIORITY)}
    ordered = sorted(jobs, key=lambda job: (rank.get(job['params']['units'][0]['unit'], 100), job['slug']))
    return [job['slug'] for job in ordered]


def catalogue_rows():
    """Every catalogo_r4 record keeps the existing role and its evidence."""
    catalogue = json.loads(CATALOGUE.read_text(encoding='utf-8'))
    rows = []
    for section, entries in catalogue.items():
        if not isinstance(entries, list):
            continue
        for item in entries:
            source_id = item['id'] if isinstance(item, dict) else item[0]
            rows.append(classify(section + '/' + source_id))
    return rows


def module_does_not_push(path=HERE / 'launch_packages.py'):
    """The parent command is text. This module must not import or call a push."""
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(alias.name == 'subprocess' for alias in node.names):
            return False
        if isinstance(node, ast.ImportFrom) and node.module == 'subprocess':
            return False
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'push_job', 'kaggle'}:
            return False
    return True


def main():
    observed = json.loads((HERE / 'observed_units.json').read_text(encoding='utf-8'))
    axis_bytes = AXIS_FILE.stat().st_size
    if _sha256_file(AXIS_FILE) != AXIS_SHA256:
        raise SystemExit('local axis hash mismatch')
    jobs, gaps = build_jobs(observed, axis_bytes)
    written = write_packages(jobs, HERE / 'packages')
    document = dispatch_document(jobs, gaps, written)
    document['utc'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    (HERE / 'ready_dispatch.json').write_text(json.dumps(document, indent=1), encoding='utf-8')
    rows = catalogue_rows()
    inventory = {
        'kind': 'first_extended_release_inventory', 'utc': document['utc'],
        'is_final_d053_catalogue': False, 'fit_admitted': False, 'training_ready': False,
        'training_ready_meaning': 'The r10 flag stays false. This file is the first extended release, not the finished D-053 catalogue.',
        'catalogue_n': len(rows), 'catalogue_records': rows,
        'storage_additions_absent_from_catalogo_r4': ['orion_hct116', 'orion_hek293t'],
        'r10_in_this_launch': [job['params']['units'][0]['unit'] for job in jobs],
        'r10_not_in_this_launch': gaps, 'not_in_r10': document['not_in_r10'],
    }
    (HERE / 'inventory.json').write_text(json.dumps(inventory, indent=1), encoding='utf-8')
    protocol = {
        'kind': 'preregistration', 'registered_before_results': True, 'observed_result': None,
        'observed_score': None, 'not_started': True, 'does_not_block_phase_1': True,
        'model': 't25 effects and t28 emission. The only intended variable is the admitted bank.',
        'reference_official_t28': REFERENCE_T28_SCORE,
        'reference_is_not_the_local_baseline': True,
        'emission': EMISSION,
        'decision_rule': {
            'resolved': 'abs(mean of paired deltas) > 2 * sd / sqrt(5)',
            'favorable': 'six-member delta resolved positive, the same without Jaccard resolved positive, PDS not resolved negative, and expanded-arm local score >= 0.100',
            'loss_is_not_a_decision_metric': True,
            'early_stop_stops_comparison_only': True,
        },
    }
    (HERE / 'comparison_protocol.json').write_text(json.dumps(protocol, indent=1), encoding='utf-8')
    print(json.dumps({'packages': len(written), 'gaps': len(gaps), 'catalogue': len(rows),
                      'utc': document['utc']}))


if __name__ == '__main__':
    main()
