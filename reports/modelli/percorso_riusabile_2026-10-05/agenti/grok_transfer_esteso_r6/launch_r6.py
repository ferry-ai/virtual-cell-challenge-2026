"""Write the r6 production mixer package. Does not push and does not relaunch."""
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
SOURCEFITS = PARENT / 'sourcefits_launch_r1'
JOINTS = PARENT / 'cd4_joint_launch_r1'
R4_PACKAGES = HERE.parent / 'grok_transfer_esteso_r4' / 'packages'
COVERAGE = PARENT / 'training_coverage_r1' / 'expected.json'
LAUNCHES = PARENT / 'training_coverage_r1' / 'launches_frozen.json'
CONDITIONS = ('Rest', 'Stim8hr', 'Stim48hr')
MIX_SLUG = 'vcc-effects-mix-t25-r6'
GATE_UNITS = (
    'h1_train', 'h1_val', 'hepg2_nadig', 'jurkat_nadig', 'k562_essential', 'kolf_chromatin', 'rpe1',
    'orion_hct116',
)
MOUNT_WHEN_PRESENT = ('orion_hek293t',)
DEFERRED_UNTIL_EXACT = ('kolf_metabolic', 'kolf_strong', 'kolf_pan_genome')
PAN_BLOCKED_SLUG = 'davidmaisterx/vcc-effects-kolf-pan-genome-r4'
PAN_REPAIR_SLUG = 'davidmaisterx/vcc-effects-kolf-pan-genome-r4-access1'
JOINT_SLUG = {
    'Rest': 'vcc-effects-cd4-rest-joint-r5',
    'Stim8hr': 'vcc-effects-cd4-stim8hr-joint-r5-retry1',
    'Stim48hr': 'vcc-effects-cd4-stim48hr-joint-r5',
}
DO_NOT_RELAUNCH = (
    'davideferrante11/vcc-derivatives-rlab-k562-gwps-r3',
    'davidmaisterx/vcc-reuse-runtime-norman-ipsc-r1',
    'davideferante/vcc-derivatives-hipsci-targeted19-r1',
    'davideferrante11/vcc-effects-cd4-stim8hr-joint-r5',
)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


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
    payload = {}
    for filename, body in sources.items():
        payload[filename] = {'base64': base64.b64encode(body).decode(), 'sha256': hashlib.sha256(body).hexdigest()}
    code = 'import base64,hashlib,json,os,runpy,sys\nfrom pathlib import Path\n'
    code += 'os.chdir("/kaggle/working"); sys.path.insert(0,"/kaggle/working")\n'
    code += 'P=' + repr(payload) + '\n'
    code += 'for name,item in P.items():\n'
    code += ' b=base64.b64decode(item["base64"]);\n'
    code += ' assert hashlib.sha256(b).hexdigest()==item["sha256"]; Path(name).write_bytes(b)\n'
    code += 'runpy.run_path(' + repr(entry) + ',run_name="__main__")\n'
    compile(code, 'run.py', 'exec')
    return code


def _axis():
    if sha256_file(pins.AXIS_FILE) != pins.AXIS_SHA256:
        raise SystemExit('local axis hash mismatch')
    return {'dataset': pins.AXIS_DATASET['davideferrante11'],
            'sha256': pins.AXIS_SHA256, 'genes': pins.AXIS_GENES,
            'bytes': pins.AXIS_FILE.stat().st_size,
            'ordering': 'gene_name CSV row order, zero based official_index'}


def _cis():
    located = pins.CIS_PAIRS
    info = {'recipe_path': pins.CIS_RECIPE_PAIRS,
            'recipe_path_present': (pins.REPO / pins.CIS_RECIPE_PAIRS).is_file(),
            'located_present': located.is_file(), 'max_distance_bp': pins.CIS_MAX_DISTANCE_BP,
            'scale': pins.CIS_SCALE, 'applied_in_effect_kernel': False, 'applied_in_mixer': False}
    if located.is_file():
        info['sha256'] = sha256_file(located)
        info['bytes'] = located.stat().st_size
    return info


def _coverage():
    return {'expected_sha256': sha256_file(COVERAGE), 'launches_frozen_sha256': sha256_file(LAUNCHES),
            'claims_complete_training': False, 'claims_complete_corpus': False}


def load_fragments():
    found = []
    for path in sorted(SOURCEFITS.glob('vcc-effects-*.json')):
        if not (SOURCEFITS / path.stem / 'params.json').is_file():
            continue
        receipt = json.loads(path.read_text(encoding='utf-8'))
        params = json.loads((SOURCEFITS / path.stem / 'params.json').read_text(encoding='utf-8'))
        unit = params['units'][0]
        if receipt.get('accepted') is not True or receipt.get('returncode') != 0:
            raise SystemExit('sourcefit was not accepted: ' + path.name)
        name = unit['unit']
        admission = 'required' if name in GATE_UNITS else 'if_exact'
        found.append({
            'slug': receipt['slug'], 'owner': receipt['owner'], 'unit': name,
            'transfer_source_id': unit['transfer_source_id'], 'line_group': unit['line_group'],
            'training_vote': unit.get('training_vote'), 'role': 'fragment', 'admission': admission,
            'condition': None,
        })
    return found


def _catalogue_gaps():
    return [
        {'name': 'k562_gwps', 'reason': 'open_parent_job',
         'evidence': 'The parent GWPS kernel stays running. k562_essential does not replace it.'},
        {'name': 'kolf_metabolic', 'reason': 'accepted_output_not_mounted',
         'evidence': 'Receipt accepted and the snapshot still says RUNNING. Not relaunched. It votes only if a later mount is exact.'},
        {'name': 'kolf_strong', 'reason': 'accepted_output_not_observed',
         'evidence': 'Receipt accepted. The status snapshot has no provider status. Not relaunched.'},
        {'name': 'kolf_pan_genome', 'reason': 'technical_access_axis',
         'evidence': 'r4 completed blocked: gene_names.csv under the df11 axis found 0. '
                     'access1 is accepted and was RUNNING, with the mx axis embedded and mounted. '
                     'It is not duplicated. The blocked r4 output does not vote. access1 votes only if its production statistic is exact.'},
        {'name': 'norman2019_compounds', 'reason': 'compound_tokens_excluded',
         'evidence': 'Single-gene perturbations stay eligible. Compound tokens are excluded. No compound map is invented. Separator tokens are not split.'},
        {'name': 'tian2021_control', 'reason': 'control_token_unmapped',
         'evidence': 'The token control is not non-targeting without a verified map.'},
        {'name': 'tian2019_ipsc', 'reason': 'qc_unverified',
         'evidence': 'QC is not invented. The study is not excluded.'},
        {'name': 'hipsci_partitions', 'reason': 'controls_registered_not_relaunched',
         'evidence': 'Control anchors are registered. The bank kernels are not relaunched. Partition statistics are not in this mixer.'},
        {'name': 'scp_ko_a549', 'reason': 'adapter_not_in_this_package',
         'evidence': 'A compatible KO source is not a scientific exclusion. No statistic is launched in this package.'},
        {'name': 'GSE249595', 'reason': 'guides_absent',
         'evidence': 'Guides are absent and are not invented.'},
        {'name': 'davideferante_axis', 'reason': 'technical_access',
         'evidence': 'The third account has no axis dataset. The fix is a byte-identical gene_names.csv, not dropping the source.'},
    ]


def _final_mix():
    return {'gamma': pins.GAMMA, 'reliability_scale': pins.RELIABILITY_SCALE,
            'weight': pins.SOURCE_WEIGHT, 'amplitude': pins.AMPLITUDE,
            'amplitude_applied': False, 'cis_applied': False, 'effects_scale_applied': False,
            'effect': 'shrunk', 'cd4_condition_gamma': 0.0,
            'reference_t28_score_transcribed': pins.REFERENCE_T28_SCORE,
            'score_measured_here': False, 'selection_rule': 'split_identity'}


def build_job(fragments, axis, cis, coverage):
    expected = []
    kernels = []
    for condition in CONDITIONS:
        slug = 'davideferrante11/' + JOINT_SLUG[condition]
        expected.append({'role': 'cd4_condition', 'admission': 'required', 'slug': slug,
                         'condition': condition, 'transfer_source_id': 'cd4_' + condition,
                         'unit': 'cd4_' + condition, 'line_group': 'CD4T'})
        kernels.append(slug)
    deferred = []
    for item in fragments:
        if item['slug'] == PAN_BLOCKED_SLUG:
            continue
        record = {key: item[key] for key in (
            'role', 'admission', 'slug', 'condition', 'transfer_source_id', 'unit', 'line_group')}
        expected.append(record)
        mount_now = item['admission'] == 'required' or item['unit'] in MOUNT_WHEN_PRESENT
        if mount_now:
            kernels.append(item['slug'])
        elif item['unit'] in DEFERRED_UNTIL_EXACT:
            deferred.append(item['slug'])
        else:
            raise SystemExit('fragment has no mount rule: ' + item['unit'])
    sources = {'mix_model.py': (HERE / 'mix_model.py').read_bytes(),
               'split_rule.py': (HERE / 'split_rule.py').read_bytes()}
    params = {
        'kind': 'incremental_partial_extended_release', 'expected': expected,
        'split_manifest': mix_model.frozen_manifest(), 'final_mix': _final_mix(),
        'emission': dict(pins.EMISSION), 'cis': cis, 'axis': axis, 'coverage_contract': coverage,
        'storage_sha256': pins.STORAGE_SHA256, 'catalogue_gaps': _catalogue_gaps(),
        'claims_complete_training': False, 'claims_complete_corpus': False,
        'fit_admitted': False, 'fit_ready': False, 'all_compatible_admitted': False,
        'output_budget_bytes': pins.OUTPUT_BUDGET_BYTES, 'ram_budget_bytes': pins.RAM_BUDGET_BYTES,
        'code_sha256': {name: hashlib.sha256(body).hexdigest() for name, body in sources.items()},
        'k562_essential_replaces_k562': False,
    }
    return {'slug': MIX_SLUG, 'owner': 'davideferrante11', 'params': params, 'dataset': axis['dataset'],
            'kernel_sources': kernels, 'deferred_kernels': deferred, 'entry': 'mix_model.py',
            'files': sources, 'phase': 'mix', 'push_now': False,
            'push_when': 'the three CD4 joint outputs are COMPLETE. Stim8hr is the accepted retry1 kernel: the first stim8hr slug had no scientific output and is not mounted. HCT and the other required sourcefits are already in this kernel. HEK is mounted and votes only when shrunk, raw and se are present. Metabolic, strong and pan access1 stay deferred until their outputs exist.'}


def _metadata(owner, slug, dataset, kernels):
    return {'id': owner + '/' + slug, 'title': slug, 'code_file': 'run.py', 'language': 'python',
            'kernel_type': 'script', 'is_private': True, 'enable_gpu': False, 'enable_tpu': False,
            'enable_internet': False, 'dataset_sources': [dataset], 'kernel_sources': list(kernels),
            'competition_sources': []}


def _inspect_job(job):
    inspected = json.dumps({'slug': job['slug'], 'kernel_sources': job['kernel_sources'],
                            'dataset': job['dataset'], 'params': job['params']})
    if job.get('enable_gpu') or pins.FORBIDDEN_DATASET in inspected:
        raise RuntimeError('refusing gpu or the forbidden dataset')
    if pins.OPEN_PARENT_KERNEL in inspected:
        raise RuntimeError('refusing the open K562 GWPS kernel')
    if job['slug'] != MIX_SLUG:
        raise RuntimeError('r6 writes only the mixer')
    return inspected


def _fill_stage(job, stage):
    sources = dict(job['files'])
    sources['params.json'] = json.dumps(job['params']).encode()
    (stage / 'run.py').write_text(_embed(job['entry'], sources), encoding='utf-8')
    (stage / 'params.json').write_text(sources['params.json'].decode(), encoding='utf-8')
    meta = _metadata(job['owner'], job['slug'], job['dataset'], job['kernel_sources'])
    (stage / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    later_kernels = list(job['kernel_sources']) + list(job.get('deferred_kernels') or [])
    if PAN_BLOCKED_SLUG in later_kernels or PAN_REPAIR_SLUG not in later_kernels:
        raise RuntimeError('the later metadata must name pan access1 and not the blocked r4 output')
    if 'davideferrante11/vcc-effects-cd4-stim8hr-joint-r5-retry1' not in job['kernel_sources']:
        raise RuntimeError('Stim8hr must mount the accepted retry')
    if 'davideferrante11/vcc-effects-cd4-stim8hr-joint-r5' in job['kernel_sources']:
        raise RuntimeError('the failed stim8hr slug has no scientific output')
    later = _metadata(job['owner'], job['slug'], job['dataset'], later_kernels)
    (stage / 'kernel-metadata-when-remaining-kolf-exact.json').write_text(
        json.dumps(later, indent=1), encoding='utf-8')
    return {'slug': job['slug'], 'dir': str(stage), 'metadata': meta,
            'metadata_when_remaining_kolf_exact': later}


def write_packages(jobs, destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    written = []
    for job in jobs:
        _inspect_job(job)
        stage = root / job['slug']
        if stage.exists():
            raise RuntimeError('package already exists: ' + job['slug'])
        stage.mkdir()
        written.append(_fill_stage(job, stage))
    return written


def freeze_ledgers():
    """Copy the consumed ledgers. Later edits of the live files do not move this pin."""
    destination = HERE / 'ledger_snapshot'
    destination.mkdir(exist_ok=True)
    sources = [
        PARENT / 'sourcefits_status_r6' / 'verification.json',
        PARENT / 'sourcefits_status_r3' / 'verification.json',
        PARENT / 'public_cd4_fragments_r1' / 'consumer_verified.json',
        PARENT / 'preflight_public_joint_r1.json',
    ]
    sources.extend(sorted(SOURCEFITS.glob('vcc-effects-*.json')))
    sources.extend(sorted(p for p in JOINTS.glob('vcc-effects-*.json') if p.parent == JOINTS))
    frozen = []
    for path in sources:
        if not path.is_file():
            frozen.append({'source': path.as_posix(), 'present': False})
            continue
        if path.stat().st_size > 30_000_000:
            frozen.append({'source': path.as_posix(), 'present': True, 'copied': False,
                           'bytes': path.stat().st_size, 'reason': 'larger than the snapshot cap'})
            continue
        target = destination / (path.parent.name + '__' + path.name)
        shutil.copy2(path, target)
        frozen.append({'source': path.relative_to(pins.REPO).as_posix(), 'snapshot': target.name,
                       'sha256': sha256_file(target), 'bytes': target.stat().st_size, 'copied': True})
    return frozen


def dispatch_document(job, written, fragments, coverage, cis, axis, frozen):
    stage = written[0]['dir']
    return {
        'kind': 'ready_dispatch', 'wave': 'r6', 'worker_pushed': False, 'kaggle_called': False,
        'fit_admitted': False, 'fit_ready': False, 'all_compatible_admitted': False,
        'claims_complete_training': False, 'claims_complete_corpus': False,
        'is_final_d053_catalogue': False, 'training_ready': False,
        'loss': None, 'optimizer': None,
        'loss_note': 'The linear model has no optimizer and no loss. No benefit is read from a loss.',
        'storage_sha256': pins.STORAGE_SHA256, 'axis': axis, 'cis': cis, 'coverage_contract': coverage,
        'model': _final_mix(), 'emission': dict(pins.EMISSION),
        'selection_rule': 'split_identity',
        'frozen_ledgers': frozen,
        'packages': [{
            'slug': job['slug'], 'owner': job['owner'], 'phase': 'mix', 'push_now': False,
            'push_when': job['push_when'], 'worker_pushed': False,
            'kernel_sources': job['kernel_sources'],
            'kernel_sources_when_remaining_kolf_exact': written[0]['metadata_when_remaining_kolf_exact']['kernel_sources'],
            'dataset_sources': [job['dataset']], 'enable_gpu': False, 'enable_internet': False,
            'is_private': True, 'ram_budget_bytes': pins.RAM_BUDGET_BYTES,
            'output_budget_bytes': pins.OUTPUT_BUDGET_BYTES,
            'parent_push_command': parent_push_command(job['owner'], stage),
            'later_metadata': 'kernel-metadata-when-remaining-kolf-exact.json',
            'pan_repair_already_running': PAN_REPAIR_SLUG,
            'pan_blocked_not_mounted': PAN_BLOCKED_SLUG,
        }],
        'parent_can_push_new': [],
        'do_not_relaunch': list(DO_NOT_RELAUNCH) + [item['slug'] for item in fragments] + [
            'davideferrante11/' + slug for slug in JOINT_SLUG.values()],
        'consumed_fragments': fragments,
        'catalogue_gaps': _catalogue_gaps(),
        'comparison': {'started': False, 'observed_result': None, 'local_score': None,
                       'blocks_phase_1': False, 'cells_per_target': 400, 'seeds': 5,
                       'official_t28_score_is_not_the_local_baseline': pins.REFERENCE_T28_SCORE,
                       'rule': 'six-member delta resolved positive, the same without Jaccard resolved positive, '
                               'PDS not resolved negative, and expanded-arm local score >= 0.100'},
        'export_contract': {
            'mixer_writes': 'cache/<source>.npz in the stage-98 save_table layout, plus effects.npz of the gamma-1 mix',
            'stage100_reads_cache_not_effects_npz': True,
            'amplitude_1_576_and_cis_5000_scale_2_applied_in': 'scripts/100_build_context_effects.py',
            'effects_scale_1_5_applied_in': 'scripts/45_generate_prediction.py read_effects',
            'applied_in_mixer': False, 'double_application': False,
            'evaluation_started': False,
        },
        'n_packages': 1,
    }


def _publish(job, written, fragments, coverage, cis, axis, frozen):
    document = dispatch_document(job, written, fragments, coverage, cis, axis, frozen)
    document['utc'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    (HERE / 'ready_dispatch.json').write_text(json.dumps(document, indent=1), encoding='utf-8')
    (HERE / 'status.json').write_text(json.dumps({
        'utc': document['utc'], 'wave': 'r6', 'worker_pushed': False, 'kaggle_called': False,
        'package': MIX_SLUG, 'fit_admitted': False, 'fit_ready': False,
        'usable_export_of_the_saved_model': 'set by the kernel after a mixed_accepted_gate run; a package file is not fit_ready',
        'push_when': job['push_when'], 'comparison_started': False,
    }, indent=1), encoding='utf-8')
    print(document['utc'])
    print('kernel_sources', len(job['kernel_sources']))
    return document


def main():
    if not module_does_not_push():
        raise SystemExit('launch_r6.py is not push-free')
    axis = _axis()
    cis = _cis()
    coverage = _coverage()
    fragments = load_fragments()
    frozen = freeze_ledgers()
    job = build_job(fragments, axis, cis, coverage)
    written = write_packages([job], HERE / 'packages')
    return _publish(job, written, fragments, coverage, cis, axis, frozen)


def refresh_mixer():
    """Rewrite the mixer files in place. Does not delete the directory or relaunch a kernel."""
    if not module_does_not_push():
        raise SystemExit('launch_r6.py is not push-free')
    axis = _axis()
    cis = _cis()
    coverage = _coverage()
    fragments = load_fragments()
    previous = json.loads((HERE / 'ready_dispatch.json').read_text(encoding='utf-8'))
    job = build_job(fragments, axis, cis, coverage)
    _inspect_job(job)
    stage = HERE / 'packages' / MIX_SLUG
    if not stage.is_dir():
        raise SystemExit('mixer package is missing')
    written = [_fill_stage(job, stage)]
    return _publish(job, written, fragments, coverage, cis, axis, previous['frozen_ledgers'])


if __name__ == '__main__':
    if sys.argv[1:] == ['--refresh']:
        refresh_mixer()
    else:
        main()
