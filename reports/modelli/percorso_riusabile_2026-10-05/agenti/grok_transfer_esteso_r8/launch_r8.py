"""Write the r8 cloud generation package. Does not push, query Kaggle, or generate cells."""
from __future__ import annotations

import ast
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import generate_contract as contract

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent.parent
REPO = HERE.parents[4]
DATA = Path(r'C:\Users\ferra\vcc2026-data')
PACKAGE = HERE / 'packages' / contract.KERNEL_TITLE
CONTROLS = DATA / 'raw' / 'controls'
COORDS = DATA / 'external' / 'annotation' / 'gene_coordinates_gencode_v50.tsv'
AXIS_FILE = DATA / 'processed' / 'ingestione_completa_2026-10-03' / 'kaggle_code_cd4_r1' / 'gene_names.csv'
CIS_FILE = REPO / 'reports' / 'trasferimento' / 'cis_2026-09-17' / 'k562_neighbour_pairs.csv'
VCC_PACKAGE = DATA / '.venv' / 'Lib' / 'site-packages' / 'vcc'
FORBIDDEN_PACKAGE_TEXT = (
    'davideferrante11/vcc-derivatives-rlab-k562-gwps-r3',
    'rlead-bench-cube-r2',
    'vcc-effects-h1-train-r4',
    'vcc-effects-h1-val-r4',
    'vcc-effects-hek293t-j-a549-f4-r7',
)
REFUSED_KERNEL_SOURCES = (
    'davideferrante11/vcc-effects-cd4-stim8hr-joint-r5',
    'davideferrante11/vcc-effects-kolf-metabolic-r4',
    'davideferrante11/vcc-effects-kolf-strong-r4',
    'davidmaisterx/vcc-effects-kolf-pan-genome-r4',
    'davideferrante11/vcc-effects-mix-t25-bank-r1',
)


def module_does_not_push(path):
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(alias.name == 'subprocess' for alias in node.names):
            return False
        if isinstance(node, ast.ImportFrom) and node.module == 'subprocess':
            return False
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'push_job', 'kaggle'}:
            return False
    return True


def guard_job(metadata, params):
    blob = json.dumps({
        'slug': metadata['id'],
        'kernel_sources': metadata['kernel_sources'],
        'dataset': metadata['dataset_sources'],
        'params': params,
    })
    for token in FORBIDDEN_PACKAGE_TEXT:
        if token in blob:
            raise RuntimeError('forbidden token in the job description')
    for slug in REFUSED_KERNEL_SOURCES:
        if slug in metadata['kernel_sources']:
            raise RuntimeError('refused kernel source is a member')
    if metadata['kernel_sources'] != [contract.MOUNT_SLUG]:
        raise RuntimeError('generation mounts only the retry mix')
    if metadata['dataset_sources'] != [contract.AXIS_DATASET]:
        raise RuntimeError('only the existing axis dataset is attached')
    if metadata['enable_internet'] or metadata['enable_gpu'] or metadata['enable_tpu'] or not metadata['is_private']:
        raise RuntimeError('generation is a private CPU kernel with internet off')
    return blob


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _ignore(directory, names):
    return [name for name in names if name == '__pycache__' or name.endswith('.pyc')]


def _copy(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def _require_identity():
    from vcc2026.panel import panel_sha256, read_panel
    panel = read_panel(CONTROLS / 'pert_counts.csv')
    file_sha = _sha256(CONTROLS / 'pert_counts.csv')
    digest = panel_sha256(panel)
    if (len(panel), digest, file_sha) != (contract.PANEL_N, contract.PANEL_SHA256, contract.PANEL_FILE_SHA256):
        raise SystemExit('pert_counts.csv does not match the pinned panel')
    if 'non-targeting' in panel:
        raise SystemExit('the panel lists a control')
    axis_sha = _sha256(AXIS_FILE)
    raw_axis = _sha256(CONTROLS / 'gene_names.csv')
    if axis_sha != contract.AXIS_SHA256 or raw_axis != axis_sha:
        raise SystemExit('gene_names.csv does not match the axis pin')
    if AXIS_FILE.stat().st_size != contract.AXIS_BYTES:
        raise SystemExit('axis byte size does not match the pin')
    cis_sha = _sha256(CIS_FILE)
    if cis_sha != contract.CIS_SHA256:
        raise SystemExit('cis pairs do not match the original pin')
    controls = {}
    for name in ('context_A.h5ad', 'context_B.h5ad', 'context_C.h5ad'):
        path = CONTROLS / name
        controls[name] = {'sha256': _sha256(path), 'bytes': path.stat().st_size}
    return {
        'panel_n': len(panel),
        'panel_sha256': digest,
        'panel_file_sha256': file_sha,
        'axis_sha256': axis_sha,
        'cis_sha256': cis_sha,
        'coords_sha256': _sha256(COORDS),
        'coords_bytes': COORDS.stat().st_size,
        'controls': controls,
    }


def _write_tree():
    if PACKAGE.exists():
        raise RuntimeError('package already exists')
    PACKAGE.mkdir(parents=True)
    for path in sorted((REPO / 'src' / 'vcc2026').glob('*.py')):
        _copy(path, PACKAGE / 'repo' / 'src' / 'vcc2026' / path.name)
    for name in ('100_build_context_effects.py', '45_generate_prediction.py', '48_package_prediction.py'):
        _copy(REPO / 'scripts' / name, PACKAGE / 'repo' / 'scripts' / name)
    _copy(REPO / 'configs' / 'config.yaml', PACKAGE / 'repo' / 'configs' / 'config.yaml')
    _copy(REPO / 'configs' / 'trials.yaml', PACKAGE / 'repo' / 'configs' / 'trials.yaml')
    _copy(CIS_FILE, PACKAGE / 'repo' / 'reports' / 'trasferimento' / 'cis_2026-09-17' / 'k562_neighbour_pairs.csv')
    _copy(CONTROLS / 'gene_names.csv', PACKAGE / 'data' / 'raw' / 'controls' / 'gene_names.csv')
    _copy(CONTROLS / 'pert_counts.csv', PACKAGE / 'data' / 'raw' / 'controls' / 'pert_counts.csv')
    _copy(COORDS, PACKAGE / 'data' / 'external' / 'annotation' / 'gene_coordinates_gencode_v50.tsv')
    shutil.copytree(VCC_PACKAGE, PACKAGE / 'vendor' / 'vcc', ignore=_ignore)
    _copy(HERE / 'generate_contract.py', PACKAGE / 'generate_contract.py')
    _copy(HERE / 'driver.py', PACKAGE / 'driver.py')
    run = (
        'import os, runpy, sys\n'
        'from pathlib import Path\n'
        'os.chdir("/kaggle/working")\n'
        'sys.path.insert(0, "/kaggle/working")\n'
        'runpy.run_path("/kaggle/working/driver.py", run_name="__main__")\n'
    )
    compile(run, 'run.py', 'exec')
    (PACKAGE / 'run.py').write_text(run, encoding='utf-8')


def _embedded_hashes():
    found = {}
    for path in sorted(PACKAGE.rglob('*')):
        if not path.is_file():
            continue
        if path.name in {'params.json', 'kernel-metadata.json'}:
            continue
        found[path.relative_to(PACKAGE).as_posix()] = _sha256(path)
    return found


def _scan_package():
    for path in PACKAGE.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix in {'.py', '.json', '.yaml', '.yml', '.txt', '.md'}:
            text = path.read_text(encoding='utf-8', errors='ignore')
            for token in FORBIDDEN_PACKAGE_TEXT:
                if token in text:
                    raise RuntimeError('forbidden token in package file ' + path.name)


def parent_push_command(stage):
    return (
        "Remove-Item Env:KAGGLE_USERNAME,Env:KAGGLE_KEY,Env:KAGGLE_API_TOKEN,Env:KAGGLE_CONFIG_DIR "
        "-ErrorAction SilentlyContinue; "
        "$env:KAGGLE_CONFIG_DIR = Join-Path $HOME '.kaggle-davideferrante11'; "
        "$py = & .\\scripts\\py.cmd -c \"import sys; print(sys.executable)\"; "
        "$kaggle = Join-Path (Split-Path $py) 'kaggle.exe'; "
        "& $kaggle kernels push -p '" + str(stage) + "'"
    )


def _freeze():
    destination = HERE / 'ledger_snapshot'
    destination.mkdir(exist_ok=True)
    sources = [
        PARENT / 'extended_mix_launch_r2' / 'vcc-effects-mix-t25-bank-r1-retry1.json',
        PARENT / 'extended_mix_launch_r1' / 'vcc-effects-mix-t25-bank-r1.json',
        PARENT / 'sourcefits_status_r9' / 'verification.json',
        PARENT / 'cd4_joint_status_r3' / 'verification.json',
        PARENT / 'h1_joint_completion_r1' / 'status.json',
    ]
    frozen = []
    for path in sources:
        if not path.is_file():
            frozen.append({'source': path.as_posix(), 'copied': False})
            continue
        target = destination / (path.parent.name + '__' + path.name)
        shutil.copy2(path, target)
        frozen.append({'snapshot': target.name, 'sha256': _sha256(target), 'bytes': target.stat().st_size,
                       'copied': True})
    return frozen


def _inventory(identity):
    """Technical inventory. A missing adapter is a gap, not a scientific exclusion."""
    verification = json.loads((PARENT / 'sourcefits_status_r9' / 'verification.json').read_text(encoding='utf-8'))
    rows = []
    for job in verification['jobs']:
        for item in job.get('statuses') or []:
            rows.append({
                'job': job['job'],
                'unit': item.get('unit'),
                'transfer_source_id': item.get('transfer_source_id'),
                'status': item.get('status'),
                'version': job.get('version'),
                'saved_source_sha256': job.get('saved_source_sha256'),
                'output_bytes': item.get('output_bytes'),
                'ram_available': (job.get('resources') or {}).get('ram_available'),
                'disk_available': (job.get('resources') or {}).get('disk_available'),
                'cpu_count': (job.get('resources') or {}).get('cpu_count'),
                'verified': job.get('verified'),
                'in_this_generation': False,
                'technical_gap': 'derived statistic exists; this generation does not mount the producer, only the mix cache',
            })
    gaps = [
        {'source': 'HIPSCI', 'adapter': 'missing', 'technical_gap': 'anchors and partitions are registered; not relaunched and not a voted cache in this package', 'scientific_exclusion': False},
        {'source': 'Tian 2021', 'adapter': 'missing', 'technical_gap': 'the control token is not non-targeting without a verified map', 'scientific_exclusion': False},
        {'source': 'Tian 2019', 'adapter': 'missing', 'technical_gap': 'QC is not verified; no QC was invented', 'scientific_exclusion': False},
        {'source': 'SCP', 'adapter': 'missing', 'technical_gap': 'no statistic in this package', 'scientific_exclusion': False},
        {'source': 'KO', 'adapter': 'missing', 'technical_gap': 'no statistic in this package', 'scientific_exclusion': False},
        {'source': 'A549', 'adapter': 'missing', 'technical_gap': 'no statistic in this package', 'scientific_exclusion': False},
        {'source': 'Norman 2019', 'adapter': 'missing', 'technical_gap': 'compound tokens stay blocked; no map was invented', 'scientific_exclusion': False},
        {'source': 'GSE249595', 'adapter': 'missing', 'technical_gap': 'guides are absent; none were invented', 'scientific_exclusion': False},
        {'source': 'k562 GWPS', 'adapter': 'not in this generation', 'technical_gap': 'parent is still closing it; this recipe does not rename k562_essential', 'scientific_exclusion': False},
        {'source': 'davideferante axis', 'adapter': 'missing', 'technical_gap': 'that account has no axis dataset', 'scientific_exclusion': False},
    ]
    payload = {
        'kind': 'technical_inventory',
        'training_ready': False,
        'fit_ready': False,
        'same_linear_model': True,
        'redesign': False,
        'sourcefits_status': 'r9',
        'sourcefits_units': len(rows),
        'rows': rows,
        'gaps': gaps,
        'controls_identity': identity['controls'],
        'note': 'rows are saved derivations. gaps have no adapter here and are not excluded for size or target overlap',
    }
    (HERE / 'inventario_fonti.json').write_text(contract.dumps(payload) + '\n', encoding='utf-8')
    return payload


def main():
    if not module_does_not_push(__file__):
        raise SystemExit('launch_r8.py is not push-free')
    for path in (HERE / 'generate_contract.py', HERE / 'driver.py'):
        if not module_does_not_push(path):
            raise SystemExit('module is not push-free: ' + path.name)
    identity = _require_identity()
    _write_tree()
    if not module_does_not_push(PACKAGE / 'run.py') or not module_does_not_push(PACKAGE / 'driver.py'):
        raise SystemExit('package entry is not push-free')
    metadata = contract.kernel_metadata()
    params = {
        'kind': 't28_emission_on_extended_mix_cache',
        'mount_slug': contract.MOUNT_SLUG,
        'mount_directory': contract.MOUNT_DIR,
        'refuse_directory': contract.REFUSE_DIR,
        'expected_model_relative': 'model',
        'push_now': False,
        'worker_pushed': False,
        'kaggle_called': False,
        'training_ready': False,
        'fit_ready': False,
        'fit_admitted': False,
        'claims_complete_training': False,
        'all_compatible_admitted': False,
        'loss': None,
        'optimizer': None,
        'local_score': None,
        'comparison_started': False,
        'emission': contract.emission(),
        'reading_rule': contract.reading_rule(),
        'policy': {
            'effect': contract.EFFECT,
            'gamma': contract.GAMMA,
            'reliability_scale': contract.RELIABILITY_SCALE,
            'weight': contract.WEIGHT,
            'amplitude': contract.AMPLITUDE,
            'amplitude_applied_once_in': 'stage 100',
            'cis_pairs': contract.CIS_PAIRS,
            'cis_sha256': identity['cis_sha256'],
            'cis_max_distance_bp': contract.CIS_MAX_DISTANCE_BP,
            'cis_scale': contract.CIS_SCALE,
            'cis_applied_once_in': 'stage 100',
            'effects_scale_applied_once_in': 'stage 45',
            'allow_missing_targets': True,
            'k562_essential_replaces_k562': False,
        },
        'panel': {
            'n': identity['panel_n'],
            'panel_sha256': identity['panel_sha256'],
            'file_sha256': identity['panel_file_sha256'],
        },
        'axis': {'sha256': identity['axis_sha256'], 'genes': contract.AXIS_GENES, 'bytes': contract.AXIS_BYTES},
        'coords': {'sha256': identity['coords_sha256'], 'bytes': identity['coords_bytes']},
        'controls': {
            'sha256': {name: item['sha256'] for name, item in identity['controls'].items()},
            'bytes': {name: item['bytes'] for name, item in identity['controls'].items()},
            'note': 'No controls dataset slug is known. Parent attaches the official files before push. This worker does not upload them.',
        },
        'guards': {
            'ram_budget_bytes': contract.RAM_BUDGET_BYTES,
            'output_budget_bytes': contract.OUTPUT_BUDGET_BYTES,
            'stage45_reserve_gib': contract.STAGE45_RESERVE_GIB,
            'stage48_reserve_gib': contract.STAGE48_RESERVE_GIB,
            'full_run_free_disk_note_gib': 17,
        },
        'product': 'prediction.vcc',
        'embedded_sha256': _embedded_hashes(),
    }
    guard_job(metadata, params)
    (PACKAGE / 'params.json').write_text(contract.dumps(params) + '\n', encoding='utf-8')
    (PACKAGE / 'kernel-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    _scan_package()
    frozen = _freeze()
    inventory = _inventory(identity)
    utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    dispatch = {
        'kind': 'ready_dispatch',
        'wave': 'r8',
        'utc': utc,
        'worker_pushed': False,
        'kaggle_called': False,
        'fit_ready': False,
        'fit_admitted': False,
        'training_ready': False,
        'claims_complete_training': False,
        'all_compatible_admitted': False,
        'comparison_started': False,
        'local_score': None,
        'loss': None,
        'optimizer': None,
        'push_now': False,
        'product': 'prediction.vcc',
        'product_is_not': ['effects.npz', 'model', 'cache'],
        'packages': [{
            'slug': contract.KERNEL_SLUG,
            'owner': contract.OWNER,
            'dir': str(PACKAGE),
            'push_now': False,
            'kernel_sources': metadata['kernel_sources'],
            'dataset_sources': metadata['dataset_sources'],
            'parent_push_command': parent_push_command(PACKAGE),
            'push_when': (
                'Push only after the retry mix is COMPLETE and its cache is the mount, '
                'and after the official context h5ad files are attached and match controls.sha256. '
                'Do not mount the ERROR producer. Do not push from this worker.'
            ),
        }],
        'identity': {
            'panel_sha256': identity['panel_sha256'],
            'axis_sha256': identity['axis_sha256'],
            'cis_sha256': identity['cis_sha256'],
            'coords_sha256': identity['coords_sha256'],
            'controls': identity['controls'],
        },
        'ledger_snapshot': frozen,
        'inventory_units': inventory['sourcefits_units'],
        'inventory_gaps': len(inventory['gaps']),
    }
    (HERE / 'ready_dispatch.json').write_text(contract.dumps(dispatch) + '\n', encoding='utf-8')
    (HERE / 'prediction_contract.json').write_text(contract.dumps({
        'registered_before_generation': True,
        'utc': utc,
        'emission': contract.emission(),
        'reading_rule': contract.reading_rule(),
        'policy': params['policy'],
        'mount_slug': contract.MOUNT_SLUG,
        'product': 'prediction.vcc',
        'training_ready': False,
        'fit_ready': False,
        'loss': None,
        'optimizer': None,
    }) + '\n', encoding='utf-8')
    (HERE / 'status.json').write_text(contract.dumps({
        'utc': utc,
        'status': 'package_ready_parent_push_blocked',
        'push_now': False,
        'worker_pushed': False,
        'kaggle_called': False,
        'generation_started': False,
        'mix_mount': contract.MOUNT_SLUG,
        'mix_state_at_package': 'RUNNING at the r2 receipt; not polled again',
        'controls_dataset_slug': None,
        'training_ready': False,
        'fit_ready': False,
        'loss': None,
        'optimizer': None,
        'local_score': None,
        'comparison_started': False,
        'blockers': [
            'retry mix must be COMPLETE before it can be mounted',
            'official context_A/B/C.h5ad are not an existing kernel dataset; parent attaches them',
        ],
    }) + '\n', encoding='utf-8')
    print('package ' + contract.KERNEL_TITLE)
    print('identity controls ' + str({name: item['bytes'] for name, item in identity['controls'].items()}))
    print('inventory units ' + str(inventory['sourcefits_units']))


if __name__ == '__main__':
    main()
