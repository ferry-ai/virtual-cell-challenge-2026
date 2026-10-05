"""Write the r7 H1 joint, the HEK split repair, and the production mixer. Does not push."""
from __future__ import annotations

import ast
import base64
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import mix_model
import pins

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent.parent
R4 = HERE.parent / 'grok_transfer_esteso_r4'
SOURCEFITS = PARENT / 'sourcefits_launch_r1'
JOINTS = PARENT / 'cd4_joint_launch_r1'
DATA = Path(r'C:\Users\ferra\vcc2026-data')
H1_TRAIN_INDEX = DATA / 'processed/generalizzazione_contesti_2026-10-02/newlines_r1/universe_h1_vcc2025_train/index.csv'
H1_VAL_INDEX = DATA / 'processed/generalizzazione_contesti_2026-10-02/newlines_r1/universe_h1_vcc2025_val/index.csv'
H1_SLUG = 'vcc-effects-h1-joint-r7'
HEK_SLUG = 'vcc-effects-hek293t-j-a549-f4-r7'
MIX_SLUG = 'vcc-effects-mix-t25-r7'
AXIS_RELATIVE = 'vcc-ingest-code-cd4-r1'
FAILED = (
    'davideferrante11/vcc-effects-cd4-stim8hr-joint-r5',
    'davideferrante11/vcc-effects-kolf-metabolic-r4',
    'davideferrante11/vcc-effects-kolf-strong-r4',
    'davidmaisterx/vcc-effects-kolf-pan-genome-r4',
)


def module_does_not_push(path=None):
    tree = ast.parse(Path(path or __file__).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(alias.name == 'subprocess' for alias in node.names):
            return False
        if isinstance(node, ast.ImportFrom) and node.module == 'subprocess':
            return False
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'push_job', 'kaggle'}:
            return False
    return True


def parent_push_command(owner, stage):
    config = pins.CONFIG[owner]
    return (
        "Remove-Item Env:KAGGLE_USERNAME,Env:KAGGLE_KEY,Env:KAGGLE_API_TOKEN,Env:KAGGLE_CONFIG_DIR "
        "-ErrorAction SilentlyContinue; "
        f"$env:KAGGLE_CONFIG_DIR = Join-Path $HOME '{config}'; "
        "$py = & .\\scripts\\py.cmd -c \"import sys; print(sys.executable)\"; "
        "$kaggle = Join-Path (Split-Path $py) 'kaggle.exe'; "
        f"& $kaggle kernels push -p '{stage}'"
    )


def _embed(entry, sources):
    payload = {name: {'base64': base64.b64encode(body).decode(), 'sha256': hashlib.sha256(body).hexdigest()}
               for name, body in sources.items()}
    code = 'import base64,hashlib,os,runpy,sys\nfrom pathlib import Path\n'
    code += 'os.chdir("/kaggle/working"); sys.path.insert(0,"/kaggle/working")\n'
    code += 'P=' + repr(payload) + '\n'
    code += 'for name,item in P.items():\n b=base64.b64decode(item["base64"]);\n'
    code += ' assert hashlib.sha256(b).hexdigest()==item["sha256"]; Path(name).write_bytes(b)\n'
    code += 'runpy.run_path(' + repr(entry) + ',run_name="__main__")\n'
    compile(code, 'run.py', 'exec')
    return code


def _read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _targets(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()[1:]
    return {line.split(',', 1)[0] for line in lines if line}


def bound_panel():
    """The t25 panel. Off-panel perturbation ids stay inventory and do not enter the mix."""
    from vcc2026.panel import panel_sha256, read_panel
    panel = read_panel(pins.PANEL_PATH)
    digest = panel_sha256(panel)
    file_sha = hashlib.sha256(pins.PANEL_PATH.read_bytes()).hexdigest()
    if (len(panel), digest, file_sha) != (pins.PANEL_N, pins.PANEL_SHA256, pins.PANEL_FILE_SHA256):
        raise SystemExit('panel pin does not match raw/controls/pert_counts.csv')
    return {'n': len(panel), 'targets': panel, 'panel_sha256': digest, 'file_sha256': file_sha,
            'path': 'raw/controls/pert_counts.csv'}


def h1_identity(panel):
    """Small local index counts. The joint itself reads the cloud count_sum banks."""
    if not H1_TRAIN_INDEX.is_file() or not H1_VAL_INDEX.is_file():
        return {'present': False}
    train, val = _targets(H1_TRAIN_INDEX), _targets(H1_VAL_INDEX)
    names = set(panel)
    return {'present': True, 'h1_train_targets': len(train), 'h1_val_targets': len(val),
            'shared_targets': len(train & val), 'h1_test_in_indexes': False,
            'local_index_on_panel': {'h1_train': len(train & names), 'h1_val': len(val & names),
                                     'note': 'local index.csv, not the cloud count_sum rows'},
            'same_transfer_source_id': 'h1', 'pooling': 'count_sum before z_shrink',
            'controls': 'identical non-targeting count rows are kept once',
            'off_panel_targets_stay_inventory': True}


def _receipts(folder):
    found = []
    for path in sorted(Path(folder).glob('vcc-effects-*.json')):
        stage = Path(folder) / path.stem / 'params.json'
        if not stage.is_file():
            continue
        receipt = _read_json(path)
        params = _read_json(stage)
        if 'units' not in params:
            condition = params['condition']
            found.append({'slug': receipt['slug'], 'owner': receipt.get('owner'),
                          'unit': 'cd4_' + condition, 'transfer_source_id': 'cd4_' + condition,
                          'line_group': 'CD4T', 'training_vote': None, 'kernel': None,
                          'relative_path': None, 'modality': 'CRISPRi', 'unit_pin': {'condition': condition},
                          'supersedes_failed': receipt.get('supersedes_failed'),
                          'accepted': receipt.get('accepted') is True})
            continue
        unit = params['units'][0]
        found.append({'slug': receipt['slug'], 'owner': receipt.get('owner') or unit.get('owner'),
                      'unit': unit['unit'], 'transfer_source_id': unit.get('transfer_source_id'),
                      'line_group': unit.get('line_group'), 'training_vote': unit.get('training_vote'),
                      'kernel': unit.get('kernel'), 'relative_path': unit.get('relative_path'),
                      'modality': unit.get('modality'), 'unit_pin': unit,
                      'supersedes_failed': receipt.get('supersedes_failed'),
                      'accepted': receipt.get('accepted') is True})
    return found


def alias_kept(receipts, superseded):
    return [item for item in receipts if item['slug'] not in superseded]


def logical_sources(source_rows, joint_rows):
    superseded = {item['supersedes_failed'] for item in source_rows + joint_rows if item.get('supersedes_failed')}
    missing = [slug for slug in FAILED if slug not in superseded]
    if missing:
        raise SystemExit('failed producer has no superseding alias: ' + ','.join(missing))
    kept_sources = alias_kept(source_rows, superseded)
    kept_joints = alias_kept(joint_rows, superseded)
    superseded = sorted(superseded)
    groups = {}
    for item in kept_sources:
        groups.setdefault(item['transfer_source_id'], []).append(item)
    multi = {key: [item['unit'] for item in value] for key, value in groups.items() if len(value) > 1}
    if set(multi) != {'h1'}:
        raise SystemExit('unexpected multi-table source ids: ' + json.dumps(multi, sort_keys=True))
    if sorted(item['unit'] for item in groups['h1']) != ['h1_train', 'h1_val']:
        raise SystemExit('H1 banks are not train and val')
    singles = [item for key, value in groups.items() if key != 'h1' for item in value]
    return {'sources': kept_sources, 'joints': kept_joints, 'singles': singles,
            'h1': groups['h1'], 'superseded': superseded, 'multi': multi}


def _axis():
    return {'dataset': pins.AXIS_DATASET['davideferrante11'], 'relative_path': AXIS_RELATIVE,
            'sha256': pins.AXIS_SHA256, 'genes': pins.AXIS_GENES, 'bytes': pins.AXIS_FILE.stat().st_size}


GAPS = (
    'k562_gwps running; not mounted',
    'kolf_pan_genome access1 running; blocked r4 not mounted',
    'norman2019 compound tokens; no invented map',
    'tian2021 control token is not non-targeting without a verified map',
    'tian2019 QC not verified',
    'hipsci anchors and partitions already registered; not relaunched here',
    'scp KO A549 and GSE249595 guides have no statistic in this package',
    'davideferante has no axis dataset; technical access, not a scientific exclusion',
)


def h1_job(resolved, axis, panel):
    banks = []
    for unit_name in ('h1_train', 'h1_val'):
        item = next(row for row in resolved['h1'] if row['unit'] == unit_name)
        banks.append({'unit': item['unit'], 'relative_path': item['relative_path'],
                      'kernel': item['kernel'], **{key: item['unit_pin'][key] for key in item['unit_pin']
                                                   if key.endswith('sha256') or key.endswith('bytes')}})
    kernels = sorted({item['kernel'] for item in banks})
    params = {'kind': 'pooled_before_shrink', 'banks': banks, 'axis': axis, 'axis_sha256': axis['sha256'],
              'panel': panel, 'min_expected': 1, 'pseudo': 0.5, 'pseudo_scale': 'constant', 'phi': 0.2,
              'min_cells': 10, 'h1_test_included': False, 'claims_complete_training': False,
              'fit_ready': False, 'global_hidden_targets': []}
    return {'slug': H1_SLUG, 'owner': 'davideferrante11', 'params': params, 'dataset': axis['dataset'],
            'kernel_sources': kernels, 'entry': 'h1_joint.py', 'push_now': True,
            'ready_for_parent': True,
            'files': {'h1_joint.py': (HERE / 'h1_joint.py').read_bytes(),
                      'pool_adapter.py': (HERE / 'pool_adapter.py').read_bytes(),
                      'split_rule.py': (HERE / 'split_rule.py').read_bytes()}}


def hek_job(resolved, axis):
    hek = next(item for item in resolved['singles'] if item['unit'] == 'orion_hek293t')
    params = {'kind': 'split_repair', 'only_split': 'J:A549:f4', 'unit': hek['unit_pin'], 'axis': axis,
              'ram_budget_bytes': pins.RAM_BUDGET_BYTES, 'output_budget_bytes': pins.OUTPUT_BUDGET_BYTES,
              'replaces_production': False, 'claims_complete_training': False, 'fit_ready': False}
    return {'slug': HEK_SLUG, 'owner': hek['owner'], 'params': params, 'dataset': axis['dataset'],
            'kernel_sources': [hek['kernel']], 'entry': 'hek_repair.py', 'push_now': True,
            'ready_for_parent': True,
            'files': {'hek_repair.py': (HERE / 'hek_repair.py').read_bytes(),
                      'cloud_job.py': (R4 / 'cloud_job.py').read_bytes(),
                      'estimator_core.py': (R4 / 'estimator_core.py').read_bytes(),
                      'split_rule.py': (HERE / 'split_rule.py').read_bytes()}}


def mix_job(resolved, axis, identity, panel):
    kernels = []
    expected = []
    for item in resolved['joints']:
        expected.append({'role': 'cd4_condition', 'admission': 'required', 'slug': item['slug'],
                         'condition': item['unit_pin'].get('condition') or item['unit'].split('_', 1)[1],
                         'transfer_source_id': item['transfer_source_id'], 'unit': item['unit'],
                         'line_group': 'CD4T'})
        kernels.append(item['slug'])
    deferred_units = {'kolf_pan_genome'}
    deferred = []
    for item in resolved['singles']:
        admission = 'if_exact' if item['unit'] in deferred_units or item['unit'] == 'orion_hek293t' else 'required'
        expected.append({'role': 'fragment', 'admission': admission, 'slug': item['slug'], 'condition': None,
                         'transfer_source_id': item['transfer_source_id'], 'unit': item['unit'],
                         'line_group': item['line_group'], 'training_vote': item['training_vote']})
        if item['unit'] in deferred_units:
            deferred.append(item['slug'])
        else:
            kernels.append(item['slug'])
    expected.append({'role': 'fragment', 'admission': 'required', 'slug': 'davideferrante11/' + H1_SLUG,
                     'condition': None, 'transfer_source_id': 'h1', 'unit': 'h1', 'line_group': 'H1',
                     'training_vote': False})
    kernels.append('davideferrante11/' + H1_SLUG)
    expected.append({'role': 'split_repair', 'admission': 'if_exact', 'slug': 'davideferrante11/' + HEK_SLUG,
                     'split': 'J:A549:f4', 'repairs_unit': 'orion_hek293t', 'condition': None,
                     'transfer_source_id': 'orion_hek293t', 'unit': 'orion_hek293t', 'line_group': 'HEK293T'})
    kernels.append('davideferrante11/' + HEK_SLUG)
    params = {'kind': 'incremental_partial_extended_release', 'expected': expected,
              'split_manifest': mix_model.frozen_manifest(), 'panel': panel,
              'final_mix': {'gamma': pins.GAMMA, 'reliability_scale': pins.RELIABILITY_SCALE,
                            'weight': pins.SOURCE_WEIGHT, 'amplitude': pins.AMPLITUDE,
                            'amplitude_applied': False, 'cis_applied': False, 'effects_scale_applied': False,
                            'effect': 'shrunk', 'targets': 'original pert_counts panel'},
              'emission': dict(pins.EMISSION), 'axis': axis, 'h1_identity': identity,
              'storage_sha256': pins.STORAGE_SHA256, 'claims_complete_training': False,
              'fit_admitted': False, 'fit_ready': False, 'all_compatible_admitted': False,
              'aggregated_after_shrink': False, 'k562_essential_replaces_k562': False,
              'catalogue_gaps': list(GAPS),
              'output_budget_bytes': pins.OUTPUT_BUDGET_BYTES, 'ram_budget_bytes': pins.RAM_BUDGET_BYTES}
    return {'slug': MIX_SLUG, 'owner': 'davideferrante11', 'params': params, 'dataset': axis['dataset'],
            'kernel_sources': kernels, 'deferred_kernels': deferred, 'entry': 'mix_model.py',
            'push_now': False, 'ready_for_parent': False,
            'push_when': 'after vcc-effects-h1-joint-r7 is COMPLETE with shrunk, raw and se. '
                         'Stim8hr, metabolic and strong retries are already derived. '
                         'The HEK repair does not replace HEK production.',
            'files': {'mix_model.py': (HERE / 'mix_model.py').read_bytes(),
                      'pool_adapter.py': (HERE / 'pool_adapter.py').read_bytes(),
                      'split_rule.py': (HERE / 'split_rule.py').read_bytes()}}


def _metadata(owner, slug, dataset, kernels):
    return {'id': owner + '/' + slug, 'title': slug, 'code_file': 'run.py', 'language': 'python',
            'kernel_type': 'script', 'is_private': True, 'enable_gpu': False, 'enable_tpu': False,
            'enable_internet': False, 'dataset_sources': [dataset], 'kernel_sources': list(kernels),
            'competition_sources': []}


def _guard(job):
    inspected = json.dumps({'slug': job['slug'], 'kernel_sources': job['kernel_sources'],
                            'dataset': job['dataset'], 'params': job['params']})
    if pins.OPEN_PARENT_KERNEL in inspected or pins.FORBIDDEN_DATASET in inspected:
        raise RuntimeError('refusing the open GWPS kernel or the forbidden dataset')
    for slug in FAILED:
        if slug in job['kernel_sources']:
            raise RuntimeError('failed producer in kernel_sources: ' + slug)
    if 'vcc-effects-h1-train-r4' in inspected or 'vcc-effects-h1-val-r4' in inspected:
        raise RuntimeError('the separate shrunk H1 fragments are not inputs')
    return inspected


def write_packages(jobs, destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    written = []
    for job in jobs:
        _guard(job)
        stage = root / job['slug']
        if stage.exists():
            raise RuntimeError('package already exists: ' + job['slug'])
        stage.mkdir()
        sources = dict(job['files'])
        sources['params.json'] = json.dumps(job['params']).encode()
        (stage / 'run.py').write_text(_embed(job['entry'], sources), encoding='utf-8')
        (stage / 'params.json').write_text(sources['params.json'].decode(), encoding='utf-8')
        meta = _metadata(job['owner'], job['slug'], job['dataset'], job['kernel_sources'])
        (stage / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
        written.append({'slug': job['slug'], 'dir': str(stage), 'owner': job['owner']})
    return written


def freeze_ledgers():
    destination = HERE / 'ledger_snapshot'
    destination.mkdir(exist_ok=True)
    sources = [
        PARENT / 'sourcefits_status_r7' / 'verification.json',
        PARENT / 'sourcefits_status_r8' / 'verification.json',
        PARENT / 'cd4_joint_status_r2' / 'verification.json',
        PARENT / 'cd4_joint_status_r3' / 'verification.json',
        PARENT / 'preflight_joint_progress_r4.json',
        PARENT / 'preflight_joint_progress_r5.json',
    ]
    sources.extend(sorted(SOURCEFITS.glob('vcc-effects-*.json')))
    sources.extend(sorted(path for path in JOINTS.glob('vcc-effects-*.json') if path.parent == JOINTS))
    frozen = []
    for path in sources:
        if not path.is_file() or path.stat().st_size > 30_000_000:
            frozen.append({'source': path.as_posix(), 'copied': False})
            continue
        target = destination / (path.parent.name + '__' + path.name)
        shutil.copy2(path, target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        frozen.append({'snapshot': target.name, 'sha256': digest, 'bytes': target.stat().st_size, 'copied': True})
    return frozen


def main():
    if not module_does_not_push():
        raise SystemExit('launch_r7.py is not push-free')
    resolved = logical_sources(_receipts(SOURCEFITS), _receipts(JOINTS))
    panel = bound_panel()
    identity = h1_identity(panel['targets'])
    axis = _axis()
    jobs = [h1_job(resolved, axis, panel), hek_job(resolved, axis), mix_job(resolved, axis, identity, panel)]
    written = write_packages(jobs, HERE / 'packages')
    frozen = freeze_ledgers()
    document = {
        'kind': 'ready_dispatch', 'wave': 'r7', 'utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'worker_pushed': False, 'kaggle_called': False, 'fit_ready': False, 'fit_admitted': False,
        'claims_complete_training': False, 'all_compatible_admitted': False,
        'push_order': [H1_SLUG, HEK_SLUG, MIX_SLUG],
        'packages': [{
            'slug': job['slug'], 'owner': job['owner'], 'push_now': job['push_now'],
            'ready_for_parent': job['ready_for_parent'], 'kernel_sources': job['kernel_sources'],
            'parent_push_command': parent_push_command(job['owner'], str(HERE / 'packages' / job['slug'])),
            'push_when': job.get('push_when', 'parent may push now; inputs are the existing banks'),
        } for job in jobs],
        'superseded_not_mounted': resolved['superseded'],
        'panel': {'n': panel['n'], 'panel_sha256': panel['panel_sha256'],
                  'file_sha256': panel['file_sha256'], 'path': panel['path']},
        'h1_identity': identity,
        'ledger_note': 'preflight_joint_progress_r4 predates the KOLF metabolic and strong retries. '
                       'sourcefits_status_r8, cd4_joint_status_r3 and preflight_joint_progress_r5 '
                       'are the later closures. In r5, pan access1 and the K562 GWPS kernel were still RUNNING.',
        'catalogue_gaps': list(GAPS),
        'logical_source_ids': sorted({item['transfer_source_id'] for item in resolved['singles']} | {'h1', 'cd4_mix'}),
        'multi_group_pooled_before_shrink': resolved['multi'],
        'reused_single_table_units': sorted(item['unit'] for item in resolved['singles']),
        'frozen_ledgers': frozen,
        'comparison_started': False, 'local_score': None,
        'official_t28_score_is_not_the_local_baseline': pins.REFERENCE_T28_SCORE,
        'n_packages_written': len(written),
    }
    (HERE / 'ready_dispatch.json').write_text(json.dumps(document, indent=1), encoding='utf-8')
    (HERE / 'status.json').write_text(json.dumps({
        'utc': document['utc'], 'wave': 'r7', 'worker_pushed': False, 'kaggle_called': False,
        'fit_ready': False, 'fit_admitted': False, 'claims_complete_training': False,
        'all_compatible_admitted': False, 'comparison_started': False, 'local_score': None,
        'loss': None, 'optimizer': None, 'packages': [job['slug'] for job in jobs],
        'push_now': [job['slug'] for job in jobs if job['push_now']],
        'panel_n': panel['n'], 'panel_sha256': panel['panel_sha256'],
        'h1_local_index_on_panel': identity.get('local_index_on_panel'),
        'tests': 'test_r7_pool.py 6 passed before this write',
    }, indent=1), encoding='utf-8')
    print(document['utc'])
    print('packages', len(written))
    return document


if __name__ == '__main__':
    main()
