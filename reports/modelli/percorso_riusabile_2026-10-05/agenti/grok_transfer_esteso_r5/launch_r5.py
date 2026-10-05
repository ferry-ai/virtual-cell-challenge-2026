"""Write the r5 CD4 joint packages and the cloud mixer. Does not push."""
from __future__ import annotations

import ast
import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pins

HERE = Path(__file__).resolve().parent
R4 = HERE.parent / 'grok_transfer_esteso_r4'
SOURCEFITS = HERE.parent.parent / 'sourcefits_launch_r1'
COVERAGE = HERE.parent.parent / 'training_coverage_r1' / 'expected.json'
LAUNCHES = HERE.parent.parent / 'training_coverage_r1' / 'launches_frozen.json'
CONDITIONS = ('Rest', 'Stim8hr', 'Stim48hr')
DONORS = ('D1', 'D2', 'D3', 'D4')
FRAGMENT_SLUGS = (
    'vcc-effects-orion-hct116-r4',
    'vcc-effects-orion-hek293t-r4',
    'vcc-effects-rpe1-r4',
    'vcc-effects-jurkat-nadig-r4',
    'vcc-effects-k562-essential-r4',
)
JOINT_SLUG = {
    'Rest': 'vcc-effects-cd4-rest-joint-r5',
    'Stim8hr': 'vcc-effects-cd4-stim8hr-joint-r5',
    'Stim48hr': 'vcc-effects-cd4-stim48hr-joint-r5',
}
MIX_SLUG = 'vcc-effects-mix-t25-r5'
CALL = {key: pins.ESTIMATOR[key] for key in (
    'phi', 'min_control_frac', 'min_cells', 'pseudo', 'pseudo_scale', 'min_expected')}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def module_does_not_push(path=HERE / 'launch_r5.py'):
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


def _cd4_units(observed):
    by_name = {item['unit']: item for item in observed['units']}
    grouped = {}
    for condition in CONDITIONS:
        pins_for = []
        for donor in DONORS:
            name = donor + '_' + condition
            if name not in by_name:
                raise SystemExit('observed units have no ' + name)
            unit = by_name[name]
            pins_for.append({
                'unit': name,
                'kernel': unit['kernel'],
                'relative_path': unit['relative_path'],
                'version': unit['version'],
                'receipt_sha256': unit['receipt_sha256'],
                'rows': unit['rows'],
                'count_sum_sha256': unit['count_sum_sha256'],
                'count_sum_bytes': unit['count_sum_bytes'],
                'rows_sha256': unit['rows_sha256'],
                'rows_bytes': unit['rows_bytes'],
                'mask_sha256': unit['mask_sha256'],
                'mask_bytes': unit['mask_bytes'],
            })
        grouped[condition] = pins_for
    return grouped


def _fragments():
    found = []
    for slug in FRAGMENT_SLUGS:
        receipt_path = SOURCEFITS / (slug + '.json')
        params_path = SOURCEFITS / slug / 'params.json'
        if not receipt_path.is_file() or not params_path.is_file():
            raise SystemExit('missing sourcefit receipt or params for ' + slug)
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        params = json.loads(params_path.read_text(encoding='utf-8'))
        unit = params['units'][0]
        if receipt.get('accepted') is not True or receipt.get('returncode') != 0:
            raise SystemExit('sourcefit was not accepted: ' + slug)
        found.append({
            'slug': receipt['slug'],
            'owner': receipt['owner'],
            'unit': receipt['unit'],
            'transfer_source_id': unit['transfer_source_id'],
            'role': 'fragment',
            'remote_status': receipt.get('remote_status'),
            'receipt_utc': receipt.get('utc'),
            'full_training': receipt.get('full_training'),
            'producer': receipt.get('producer'),
            'producer_version_pin': receipt.get('producer_version_pin'),
        })
    return found


def _axis():
    if sha256_file(pins.AXIS_FILE) != pins.AXIS_SHA256:
        raise SystemExit('local axis hash mismatch')
    return {'dataset': pins.AXIS_DATASET['davideferrante11'],
            'relative_path': pins.AXIS_DATASET['davideferrante11'].split('/')[-1],
            'sha256': pins.AXIS_SHA256, 'genes': pins.AXIS_GENES,
            'bytes': pins.AXIS_FILE.stat().st_size,
            'ordering': 'gene_name CSV row order, zero based official_index'}


def _cis():
    recipe_path = pins.REPO / pins.CIS_RECIPE_PAIRS
    located = pins.CIS_PAIRS
    info = {'recipe_path': pins.CIS_RECIPE_PAIRS, 'recipe_path_present': recipe_path.is_file(),
            'located_path': str(located), 'located_present': located.is_file(),
            'max_distance_bp': pins.CIS_MAX_DISTANCE_BP, 'scale': pins.CIS_SCALE,
            'applied_in_effect_kernel': False}
    if located.is_file():
        info['sha256'] = sha256_file(located)
        info['bytes'] = located.stat().st_size
    return info


def _coverage():
    expected_sha = sha256_file(COVERAGE)
    frozen_sha = sha256_file(LAUNCHES)
    payload = json.loads(COVERAGE.read_text(encoding='utf-8'))
    recorded = payload.get('launches_frozen_sha256')
    return {'path': COVERAGE.relative_to(pins.REPO).as_posix(), 'sha256': expected_sha,
            'launches_frozen': LAUNCHES.relative_to(pins.REPO).as_posix(),
            'launches_frozen_sha256': frozen_sha,
            'launches_frozen_sha_recorded_in_expected': recorded,
            'launches_frozen_sha_matches': recorded == frozen_sha,
            'claims_complete_training': False, 'claims_complete_corpus': False,
            'meaning': 'The coverage contract keeps every storage unit. This dispatch does not certify admission.'}


def _named_blocks():
    return [
        {'name': 'k562_gwps', 'reason': 'open_parent_job',
         'evidence': 'Il kernel GWPS del parent resta aperto. k562_essential non lo sostituisce. Non è in questo mix.'},
        {'name': 'norman2019', 'reason': 'adapter_limit_component_map',
         'evidence': 'Molte perturbazioni sono singole. Alcune doppie non autorizzano a escludere la fonte. Serve la mappa source verificata; i composti non si inventano. Non è in questo primo mix.'},
        {'name': 'tian2021_control', 'reason': 'adapter_limit_control_token',
         'evidence': "Il token control va verificato nel producer o nei metadata. Non è un'esclusione scientifica definitiva."},
        {'name': 'tian2019_ipsc', 'reason': 'adapter_limit_qc',
         'evidence': 'QC non verificato in questo turno. Non è un\'esclusione scientifica definitiva.'},
        {'name': 'hipsci_gw_and_targeted19', 'reason': 'adapter_limit_controls',
         'evidence': 'Controlli e ancore già registrati. Non rilanciare. Cercare solo prove pertinenti.'},
        {'name': 'davideferante_axis', 'reason': 'technical_access',
         'evidence': "L'asse manca sul terzo account. Si risolve pubblicando l'input della pipeline, non escludendo la fonte."},
        {'name': 'scp_ko', 'reason': 'same_estimator_when_valid',
         'evidence': 'I KO idonei possono usare lo stesso stimatore dove è valido, senza inventare chimica o guide. Non entrano in questo primo mix.'},
        {'name': 'GSE249595', 'reason': 'guides_absent',
         'evidence': 'Le guide non ci sono e non si inventano.'},
        {'name': 'hepg2_h1_kolf_and_other_r4_packages', 'reason': 'not_in_this_first_mix',
         'evidence': 'Restano fonti nominata, non omissioni. I pacchetti r4 per donatore CD4 non vanno pushati: la stima CD4 è il joint r5.'},
    ]


def _final_mix():
    return {'gamma': pins.GAMMA, 'reliability_scale': pins.RELIABILITY_SCALE,
            'weight': pins.SOURCE_WEIGHT, 'amplitude': pins.AMPLITUDE,
            'amplitude_applied': False, 'effect': 'shrunk',
            'cd4_condition_gamma': 0.0,
            'cd4_condition_how': 'reliability-weighted mean; raw and shrunk mixed separately',
            'reference_t28_score_transcribed': pins.REFERENCE_T28_SCORE,
            'score_measured_here': False}


def _emission():
    return dict(pins.EMISSION)


def build_jobs(cd4, fragments, axis, cis, coverage):
    code = {
        'estimator_core.py': (HERE / 'estimator_core.py').read_bytes(),
        'cd4_joint.py': (HERE / 'cd4_joint.py').read_bytes(),
    }
    code_sha = {name: hashlib.sha256(body).hexdigest() for name, body in code.items()}
    jobs = []
    for condition in CONDITIONS:
        donors = cd4[condition]
        kernels = []
        for pin in donors:
            if pin['kernel'] not in kernels:
                kernels.append(pin['kernel'])
        params = {
            'kind': 'cd4_condition_joint', 'condition': condition, 'donors': donors,
            'claims_complete_training': False, 'claims_complete_corpus': False, 'fit_admitted': False,
            'matrix': 'count_sum', 'ram_budget_bytes': pins.RAM_BUDGET_BYTES,
            'output_budget_bytes': pins.OUTPUT_BUDGET_BYTES,
            'storage_sha256': pins.STORAGE_SHA256, 'global_hidden_targets': [],
            'control_labels': {'NTC': 'non-targeting'}, 'verified_control_map': {},
            'line_group_expected': 'CD4T', 'estimator': CALL, 'axis': axis,
            'code_sha256': code_sha, 'final_mix': _final_mix(), 'emission': _emission(),
            'cis': cis, 'coverage_contract': coverage,
        }
        jobs.append({'slug': JOINT_SLUG[condition], 'owner': 'davideferrante11', 'params': params,
                     'dataset': axis['dataset'], 'kernel_sources': kernels, 'entry': 'cd4_joint.py',
                     'files': code, 'phase': 'cd4_joint',
                     'push_now': False,
                     'push_when': 'uno slot davideferrante11 è libero; non pushare sopra GWPS e i quattro sourcefit df11'})
    mix_sources = {
        'mix_model.py': (HERE / 'mix_model.py').read_bytes(),
    }
    expected = []
    for condition in CONDITIONS:
        expected.append({'role': 'cd4_condition', 'slug': 'davideferrante11/' + JOINT_SLUG[condition],
                         'condition': condition, 'transfer_source_id': 'cd4_' + condition})
    mix_kernels = ['davideferrante11/' + JOINT_SLUG[condition] for condition in CONDITIONS]
    for item in fragments:
        expected.append({'role': 'fragment', 'slug': item['slug'], 'condition': None,
                         'transfer_source_id': item['transfer_source_id'], 'unit': item['unit']})
        mix_kernels.append(item['slug'])
    mix_params = {
        'kind': 'incremental_extended_release', 'expected': expected, 'final_mix': _final_mix(),
        'emission': _emission(), 'cis': cis, 'axis': axis, 'coverage_contract': coverage,
        'storage_sha256': pins.STORAGE_SHA256, 'not_in_this_mix': _named_blocks(),
        'claims_complete_training': False, 'claims_complete_corpus': False, 'fit_admitted': False,
        'code_sha256': {name: hashlib.sha256(body).hexdigest() for name, body in mix_sources.items()},
    }
    jobs.append({'slug': MIX_SLUG, 'owner': 'davideferrante11', 'params': mix_params,
                 'dataset': axis['dataset'], 'kernel_sources': mix_kernels, 'entry': 'mix_model.py',
                 'files': mix_sources, 'phase': 'mix', 'push_now': False,
                 'push_when': 'i tre joint e i cinque frammenti hanno un output montabile'})
    return jobs


def write_packages(jobs, destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    written = []
    for job in jobs:
        inspected = json.dumps({'slug': job['slug'], 'kernel_sources': job['kernel_sources'],
                                'dataset': job['dataset'], 'params': job['params']})
        if job.get('enable_gpu') or pins.FORBIDDEN_DATASET in inspected:
            raise RuntimeError('refusing gpu or the forbidden dataset')
        if pins.OPEN_PARENT_KERNEL in inspected:
            raise RuntimeError('refusing the open K562 GWPS kernel')
        if any(slug in job['slug'] for slug in FRAGMENT_SLUGS):
            raise RuntimeError('refusing to rebuild a running sourcefit')
        stage = root / job['slug']
        if stage.exists():
            raise RuntimeError('package already exists: ' + job['slug'])
        stage.mkdir()
        sources = dict(job['files'])
        sources['params.json'] = json.dumps(job['params']).encode()
        (stage / 'run.py').write_text(_embed(job['entry'], sources), encoding='utf-8')
        (stage / 'params.json').write_text(sources['params.json'].decode(), encoding='utf-8')
        meta = {'id': job['owner'] + '/' + job['slug'], 'title': job['slug'], 'code_file': 'run.py',
                'language': 'python', 'kernel_type': 'script', 'is_private': True, 'enable_gpu': False,
                'enable_tpu': False, 'enable_internet': False, 'dataset_sources': [job['dataset']],
                'kernel_sources': list(job['kernel_sources']), 'competition_sources': []}
        (stage / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
        written.append({'slug': job['slug'], 'dir': str(stage), 'metadata': meta})
    return written


def dispatch_document(jobs, written, fragments, coverage, cis, axis):
    by_slug = {item['slug']: item for item in written}
    packages = []
    for job in jobs:
        stage = by_slug[job['slug']]['dir']
        packages.append({
            'slug': job['slug'], 'owner': job['owner'], 'phase': job['phase'],
            'push_now': False, 'push_when': job['push_when'], 'worker_pushed': False,
            'kernel_sources': job['kernel_sources'], 'dataset_sources': [job['dataset']],
            'enable_gpu': False, 'enable_internet': False, 'is_private': True,
            'ram_budget_bytes': pins.RAM_BUDGET_BYTES, 'output_budget_bytes': pins.OUTPUT_BUDGET_BYTES,
            'parent_push_command': parent_push_command(job['owner'], stage),
            'cross_account': 'Se Kaggle rifiuta un kernel_source di davidmaisterx, il parent condivide quel kernel con davideferrante11 oppure copia la banca sul suo account. Non si scarta D4 e non si rifà l\'ingestion.',
        })
    return {
        'kind': 'ready_dispatch', 'wave': 'r5', 'worker_pushed': False, 'fit_admitted': False,
        'claims_complete_training': False, 'claims_complete_corpus': False,
        'is_final_d053_catalogue': False, 'training_ready': False,
        'loss': None, 'optimizer': None,
        'loss_note': 'Il modello lineare non ha optimizer né loss. Nessun beneficio si legge da una loss.',
        'storage': {'manifest': 'reports/modelli/percorso_riusabile_2026-10-05/cloud_catalog_r10/manifest.json',
                    'sha256': pins.STORAGE_SHA256, 'training_ready': False,
                    'meaning': 'r10 è un indice di storage, non un manifest di fit'},
        'axis': axis, 'cis': cis, 'coverage_contract': coverage,
        'model': _final_mix(), 'emission': _emission(),
        'consumed_fragments': fragments,
        'do_not_relaunch': [
            pins.OPEN_PARENT_KERNEL,
            'davidmaisterx/vcc-reuse-runtime-norman-ipsc-r1',
            'davideferante/vcc-derivatives-hipsci-targeted19-r1',
            *[item['slug'] for item in fragments],
        ],
        'push_rule': (
            'Solo il parent pusha. Questo worker non ha chiamato kaggle. '
            'I cinque frammenti sourcefits_launch_r1 sono già accettati: non duplicarli. '
            "L'ultima evidenza è il preflight del parent con un job df11 (K562 GWPS) e quattro ricevute df11 RUNNING "
            'più K562 essential su davidmaisterx. Non è un censimento nuovo. '
            'I tre joint aspettano uno slot libero su davideferrante11 (tetto 5). '
            'Il mixer si pusha quando i tre joint e i cinque frammenti hanno un output; il mount è cloud, senza trasferimento locale obbligatorio. '
            'Non rilanciare Norman/iPSC né HIPSCI targeted19. Non pushare i dodici fit CD4 per donatore di r4.'
        ),
        'packages': packages,
        'not_in_this_mix': _named_blocks(),
        'comparison': {'started': False, 'observed_result': None,
                       'blocks_phase_1': False,
                       'rule': 'six-member delta resolved positive, the same without Jaccard resolved positive, '
                               'PDS not resolved negative, and expanded-arm local score >= 0.100'},
        'n_packages': len(packages),
    }


def main():
    if not module_does_not_push():
        raise SystemExit('launch_r5.py is not push-free')
    observed = json.loads((R4 / 'observed_units.json').read_text(encoding='utf-8'))
    if observed.get('storage_manifest_sha256') != pins.STORAGE_SHA256 or observed.get('training_ready') is not False:
        raise SystemExit('r4 observed units are not the r10 pin')
    axis = _axis()
    cis = _cis()
    coverage = _coverage()
    fragments = _fragments()
    jobs = build_jobs(_cd4_units(observed), fragments, axis, cis, coverage)
    written = write_packages(jobs, HERE / 'packages')
    document = dispatch_document(jobs, written, fragments, coverage, cis, axis)
    document['utc'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    (HERE / 'ready_dispatch.json').write_text(json.dumps(document, indent=1), encoding='utf-8')
    print(document['utc'])
    print('packages', len(written))
    return document


if __name__ == '__main__':
    main()
