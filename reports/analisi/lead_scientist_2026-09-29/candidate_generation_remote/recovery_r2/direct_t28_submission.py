"""Validate t28 in place on Drive; submit only with explicit --submit.

Never copies/decompresses the multi-GB container. The official CLI remains the
only upload implementation. Each attempt has a new small output directory.
"""
from __future__ import annotations
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
GENERATION_SHA = '123ce93f4d8d21c107215c96f726a6b7121545c1329948f431234eabce80f40e'
REGISTRATION_SHA = 'a2081b9cd615a1020a962def21eafa54d7116db79285887f56c775033d61e192'
TEXTS_SHA = '6a2881e819b4450780dc5922740cbf1dd68636fc649f319589466188a8c53947'
AUTHORIZATION_SHA = '2d57dd28f2349ec81b89b0dd2c9e3a9dfbf5ce7f66c99a76c49706296ab51f66'
MANIFEST_SHA = '18dc29195d818cbfc8cb4a5442850e4e9581b60d8cba585afad65daf85a99bae'
CONFIRMATION_SHA = '35471a773ae2e51759d946682c3223b5a2a72f53eb03c83559c7a9e463f9c41c'
ARCHIVE_SHA = 'f7324778e5d7225552734e2c7303353f46dee6c01e9d455703adce3b9b105860'
CLI_SOURCE_SHAS = {
    'submit.py': 'ab648c3c78fd5f8e09bccf259283810f169edb51b24944aeb8b6f0b5539af3b5',
    'upload.py': '4b52db387b366abfbf69a105b8010da55b3d05e932223a1f4410904f3f3a9b0e',
    'vccfile.py': '84a3c3e2468df53758e3054edc3b601b5fbb13f73d8748e0693c1caad4773a0b'}
METADATA = ('completion.json', 'transfer_verification.json', 'launch_review.json',
            'pack/packaging.json', 'pack/manifest_48_package_prediction.json',
            'gen/manifest_45_generate_prediction.json', 'gen/generation_diagnostics.json',
            'stage45_checkpoint/complete.json')
REQUIRED_CHECKS = ('var_names_unique', 'gene_order_matches_list', 'gene_dim_matches_expected',
    'has_cells', 'cell_dim_within_cap', 'pert_column_present', 'no_control_rows', 'contexts_complete',
    'targets_match_official_list', 'density_within_cap', 'column_indices_in_range', 'counts_finite',
    'counts_non_negative', 'counts_are_whole_numbers', 'max_counts_per_cell_within_cap',
    'no_all_zero_perturbation')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2); f.write('\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_metadata(source):
    raw = {}
    for name in METADATA:
        path = source/name
        require(path.stat().st_size <= 5*1024**2, 'Oversized metadata: '+name)
        raw[name] = path.read_bytes()
    return {name: json.loads(data) for name, data in raw.items()}, raw


def verify_metadata(documents):
    complete = documents['completion.json']
    transfer = documents['transfer_verification.json']
    pack = documents['pack/packaging.json']
    checkpoint = documents['stage45_checkpoint/complete.json']
    launch = documents['launch_review.json']
    gen = documents['gen/manifest_45_generate_prediction.json']
    verify = pack['verification']
    expected, size = verify['archive_sha256'], verify['archive_bytes']
    require(isinstance(expected, str) and re.fullmatch('[a-f0-9]{64}', expected), 'Invalid archive SHA')
    require(isinstance(size, int) and not isinstance(size, bool) and size > 0, 'Invalid archive size')
    require(complete.get('status') == 'complete' and complete.get('prediction_sha256') == GENERATION_SHA
            and complete.get('vcc_sha256') == expected, 'No complete frozen t28 result')
    require(checkpoint.get('sha256') == GENERATION_SHA and checkpoint.get('full_sha256_verified') is True
            and checkpoint.get('scientific_recipe_unchanged') is True, 'No verified stage45 checkpoint')
    require(transfer.get('sha256') == expected and transfer.get('bytes') == size
            and transfer.get('local_vs_drive_full_sha256') == 'identical', 'Missing complete Drive transfer')
    require(pack.get('exit_code') == 0 and pack['input']['sha256'] == GENERATION_SHA
            and pack['input']['bytes'] == checkpoint['bytes'], 'Package is not the frozen generation')
    require(verify.get('official_container_validator') == 'passed', 'Container validator did not pass')
    payload = verify['payload_vs_input']
    require(payload.get('matches_input') is True and payload.get('x_arrays_bit_identical') is True,
            'Payload equality is not verified')
    for obj in (payload, verify['meta_from_archive'], pack['package']):
        require(obj['n_obs'] == 360000 and obj['n_vars'] == 18533, 'Incorrect full-panel dimensions')
        require(obj['nnz'] == verify['nnz_from_archive'], 'NNZ metadata mismatch')
    validation = pack['package']['validation']
    require(validation.get('failures') == [] and validation.get('all_integer') is True
            and validation.get('n_nonfinite') == 0, 'Prediction validation failed')
    require(all(validation['checks'].get(k) is True for k in REQUIRED_CHECKS), 'Missing successful official checks')
    require(bool(validation.get('csr_checks')) and all(v is True for v in validation['csr_checks'].values()),
            'CSR structure was not verified')
    require(validation['cells_per_context'] == dict.fromkeys(('A', 'B', 'C'), 120000)
            and validation['n_targets_per_context'] == dict.fromkeys(('A', 'B', 'C'), 300)
            and validation['empty_perturbations'] == [], 'Incorrect context/target coverage')
    require(launch['registration_sha256'] == REGISTRATION_SHA and launch['manifest_sha256'] == MANIFEST_SHA
            and launch['confirmation_sha256'] == CONFIRMATION_SHA and launch['code_archive_sha256'] == ARCHIVE_SHA,
            'Generation lineage changed')
    config = gen['config']
    wanted = {'trial': 'trial-ext-profile', 'contexts': 'A,B,C', 'cells_per_pert': 400,
              'seed': 20260912, 'gene_dispersion': True, 'gene_dispersion_scale': 1.,
              'depth_bins': False, 'effects_scale': 1.5}
    require(all(config.get(k) == v for k, v in wanted.items()), 'Generation parameters changed')
    return expected, size, verify['nnz_from_archive']


def frozen_texts(repo):
    trial = repo/'reports/invii/trial_2026-09-29'
    registration = repo/'reports/invii/prediction_t28_2026-09-29/prediction.json'
    files = {registration: REGISTRATION_SHA, trial/'submission_texts.md': TEXTS_SHA,
             trial/'autorizzazione_lead_2026-09-29.md': AUTHORIZATION_SHA}
    for path, expected in files.items():
        require(digest(path) == expected, 'Frozen registration/text/authorization changed: '+str(path))
    text = (trial/'submission_texts.md').read_text(encoding='utf-8')
    section = text.split('## t28\n', 1)[1].split('\n## ', 1)[0]
    model = re.search(r'\*\*Model name:\*\* `([^`]+)`', section).group(1)
    description = section.split('**Description:**', 1)[1].strip()
    require(0 < len(description) <= 2000, 'Invalid description length')
    return model, description


def cli_contract():
    import vcc
    require(importlib.metadata.version('vcc-cli') == '0.2.0', 'Reviewed CLI version differs')
    folder = Path(vcc.__file__).parent
    for name, expected in CLI_SOURCE_SHAS.items():
        require(digest(folder/name) == expected, 'Installed CLI code changed: '+name)
    return CLI_SOURCE_SHAS


def full_hash_checked(path, size, expected, cache_volume, min_free_bytes):
    before = path.stat()
    require(before.st_size == size, 'Container is incomplete by size')
    h, read, lowest = hashlib.sha256(), 0, shutil.disk_usage(cache_volume).free
    require(lowest >= min_free_bytes, 'Insufficient cache-volume reserve before reading')
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8*1024**2), b''):
            h.update(block); read += len(block)
            free = shutil.disk_usage(cache_volume).free
            lowest = min(lowest, free)
            require(free >= min_free_bytes, 'Drive cache volume fell below reserve; no submission started')
            if read % (256*1024**2) == 0:
                print(json.dumps({'phase': 'sha256', 'bytes_read': read, 'total_bytes': size,
                                  'cache_volume_free_bytes': free}), flush=True)
    after = path.stat()
    require((before.st_size, before.st_mtime_ns, before.st_ino) ==
            (after.st_size, after.st_mtime_ns, after.st_ino), 'Container changed during hashing')
    require(read == size and h.hexdigest() == expected, 'Full container SHA256 mismatch')
    return {'sha256': h.hexdigest(), 'bytes': read, 'mtime_ns': after.st_mtime_ns,
            'lowest_cache_volume_free_bytes_during_sha': lowest,
            'cache_volume': str(cache_volume), 'reserve_bytes': min_free_bytes}


def validate(source, out, cache_volume, reserve_bytes):
    require(not out.exists(), 'Attempt output already exists')
    require(source.is_absolute() and out.is_absolute(), 'Use absolute source/output paths')
    require(source.resolve() != out.resolve() and source.resolve() not in out.resolve().parents,
            'Attempt output must be outside the immutable source')
    metadata, raw = load_metadata(source)
    expected, size, nnz = verify_metadata(metadata)
    model, description = frozen_texts(REPO)
    cli_contract()
    path = source/'prediction.vcc'
    file_info = full_hash_checked(path, size, expected, cache_volume, reserve_bytes)
    from vcc.vccfile import validate_vcc, nnz_from_vcc
    validate_vcc(path)
    require(nnz_from_vcc(path) == nnz, 'Actual container NNZ metadata differs')
    require(all((source/name).read_bytes() == data for name, data in raw.items()), 'Source metadata changed during validation')
    out.mkdir(parents=True)
    for name, data in raw.items():
        target = out/'metadata'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write(data)
    receipt = {'status': 'validated_in_place_not_submitted', 'utc': datetime.now(timezone.utc).isoformat(),
               'source': str(path), 'file': file_info, 'generation_sha256': GENERATION_SHA,
               'metadata_sha256': {n: hashlib.sha256(b).hexdigest() for n, b in raw.items()},
               'registration_sha256': REGISTRATION_SHA, 'submission_texts_sha256': TEXTS_SHA,
               'authorization_sha256': AUTHORIZATION_SHA, 'cli_source_shas': CLI_SOURCE_SHAS,
               'runner_sha256': digest(__file__), 'model_name': model, 'description': description,
               'container_copied': False, 'container_decompressed': False, 'uploaded': False}
    write(out/'validation.json', receipt)
    return receipt


def submit(receipt, out, resume_id=None):
    path = Path(receipt['source'])
    if resume_id:
        require(bool(re.fullmatch('[A-Za-z0-9_-]+', resume_id)), 'Invalid resume entry ID')
        from vcc import auth
        from vcc.config import resolve_profile
        pending = auth.get_pending_upload(resolve_profile(), resume_id)
        require(pending is not None and Path(pending['local_path']).resolve() == path.resolve(),
                'Resume entry points to a different container; no upload started')
    require(path.stat().st_size == receipt['file']['bytes'] and
            path.stat().st_mtime_ns == receipt['file']['mtime_ns'], 'Container changed after full SHA')
    command = [sys.executable, '-m', 'vcc', '--json', 'submit', str(path),
               '-m', receipt['model_name'], '-d', receipt['description']]
    if resume_id:
        command += ['--resume', resume_id]
    awake = None
    if os.name == 'nt':
        awake = ctypes.windll.kernel32.SetThreadExecutionState
        require(bool(awake(0x80000001)), 'Unable to inhibit system sleep; no upload started')
    try:
        write(out/'submission_started.json', {'utc': datetime.now(timezone.utc).isoformat(),
            'runner_pid': os.getpid(), 'command': command, 'resume_entry': resume_id,
            'validation_sha256': digest(out/'validation.json'), 'sleep_inhibition': awake is not None})
        with (out/'submit_raw.json').open('xb') as stdout, (out/'submit_stderr.txt').open('xb') as stderr:
            completed = subprocess.run(command, stdout=stdout, stderr=stderr, check=False)
        write(out/'submission_exit.json', {'utc': datetime.now(timezone.utc).isoformat(),
            'returncode': completed.returncode,
            'note': 'CLI exit is not proof of published score; inspect raw output and vcc status separately'})
        return completed.returncode
    finally:
        if awake is not None:
            awake(0x80000000)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--cache-volume', type=Path, default=Path('C:/'))
    p.add_argument('--reserve-mib', type=int, default=512)
    p.add_argument('--submit', action='store_true', help='Execute official CLI only after fresh complete validation')
    p.add_argument('--resume-entry')
    a = p.parse_args()
    require(a.reserve_mib >= 512, 'At least 512 MiB cache-volume reserve is required')
    require(not a.resume_entry or a.submit, '--resume-entry requires --submit')
    receipt = validate(a.source, a.out, a.cache_volume, a.reserve_mib*1024**2)
    if a.submit:
        raise SystemExit(submit(receipt, a.out, a.resume_entry))
    print(json.dumps({'status': receipt['status'], 'receipt': str(a.out/'validation.json'), 'uploaded': False}))


if __name__ == '__main__':
    main()
