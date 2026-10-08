"""Upload the frozen t37 artifact once, preserving receipts and preventing sleep.

Adapted from the successful t30/t36 upload launchers. Run in a separate hidden
Windows process. No generation, endpoint override, limit bypass or auto-retry.
"""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PREDICTION = HERE.parent / 'prediction_t37_2026-10-08/prediction.json'
PREDICTION_SHA = '0b8a349839032b690c655e5284d0ab3b9d7b2bbf0ee616f7c814e9c4ef4ed940'
MODEL = 't37 - transfer T1 banca estesa'
DESCRIPTION = ('Exploratory transfer refit using the frozen T1 source release. '
               'Same transfer estimator and cell-generation settings as t36, '
               'with additional eligible source evidence affecting 16 targets. '
               'No neural component. Local comparisons were inconclusive; '
               'no improvement is claimed before official scoring.')


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(8 << 20), b''):
            result.update(block)
    return result.hexdigest()


def write_new(path, value):
    with path.open('x', encoding='utf-8') as target:
        json.dump(value, target, indent=2)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--attempt', default='r1')
    parser.add_argument('--resume-entry')
    args = parser.parse_args()
    require(not (HERE / 'NO_SUBMIT_T1_r1.json').exists(),
            'T1 submission superseded by the owner: require a complete-source refit')
    require(bool(re.fullmatch(r'r[1-9][0-9]*', args.attempt)), 'invalid attempt label')
    require(os.name == 'nt', 'this persistent launcher is for Windows')
    args.run_dir.mkdir(parents=True, exist_ok=False)
    write_new(args.run_dir / 'started.json', {'utc': utc(), 'pid': os.getpid(),
              'attempt': args.attempt, 'resume_entry': args.resume_entry})
    awake = ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    require(bool(awake), 'could not inhibit system sleep')
    try:
        require(sha(PREDICTION) == PREDICTION_SHA, 'registered prediction changed')
        prediction = json.loads(PREDICTION.read_text(encoding='utf-8'))
        manifest = json.loads((args.evidence / 'generation_manifest.json').read_text(encoding='utf-8'))
        package_path = args.evidence / 'packaging.json'
        package = json.loads(package_path.read_text(encoding='utf-8'))['package']
        require(manifest['status'] == 'VCC_READY', 'producer is not ready')
        require(manifest['prediction']['sha256'] == PREDICTION_SHA, 'producer used another prediction')
        require(manifest['packaging_sha256'] == sha(package_path), 'packaging receipt changed')
        for context in ('A', 'B', 'C'):
            require(manifest['effects'][context]['sha256'] ==
                    prediction['candidate']['effect_sha256_each_context'], 'wrong candidate effects')
        require(package['validation']['ok'] and not package['validation']['failures'],
                'package validation failed')
        require(package['n_obs'] == 360000 and package['n_vars'] == 18533,
                'package is not full size')
        require(package['archive_bytes'] == manifest['bytes'], 'package byte counts differ')
        require(args.product.is_file() and args.product.suffix == '.vcc', 'product missing')
        require(args.product.stat().st_size == manifest['bytes'], 'local product size differs')
        digest = sha(args.product)
        require(digest == manifest['sha256'], 'local product checksum differs')
        previous = list(HERE.glob('submit_t37_*_started.json'))
        require(not previous or args.resume_entry is not None,
                'previous upload attempt exists; inspect entry before resuming')
        # The official CLI also performs its own live allowance and in-flight checks.
        state_path = Path.home() / '.config/vcc/state.json'
        if state_path.exists():
            pending = json.loads(state_path.read_text(encoding='utf-8')).get('pending_uploads', {})
            require(not pending or args.resume_entry is not None,
                    'pending upload exists; inspect it before a new submission')
        started = {'utc': utc(), 'pid': os.getpid(), 'model_name': MODEL,
                   'attempt': args.attempt, 'resume_entry': args.resume_entry,
                   'product_bytes': manifest['bytes'], 'product_sha256': digest,
                   'prediction_sha256': PREDICTION_SHA, 'checksum_verified': True,
                   'system_sleep_inhibited': True}
        write_new(HERE / f'submit_t37_{args.attempt}_started.json', started)
        write_new(args.run_dir / 'verified_product.json', dict(started, path=str(args.product)))
        cli = Path(sys.executable).with_name('vcc.exe')
        require(cli.is_file(), 'use the project Python environment containing vcc.exe')
        command = [str(cli), 'submit', str(args.product), '-m', MODEL,
                   '-d', DESCRIPTION, '--json']
        if args.resume_entry:
            command += ['--resume', args.resume_entry]
        env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
        # Raw CLI output stays outside the public repository; the public receipt
        # keeps its hash and return code. No credentials or endpoint are changed.
        raw_path = args.run_dir / 'submit_raw.json'
        error_path = args.run_dir / 'submit_stderr.txt'
        with raw_path.open('x', encoding='utf-8') as stdout, error_path.open('x', encoding='utf-8') as stderr:
            result = subprocess.run(command, env=env, stdout=stdout, stderr=stderr)
        finished = {'utc': utc(), 'attempt': args.attempt, 'exit_code': result.returncode,
                    'product_sha256': digest, 'raw_sha256': sha(raw_path),
                    'stderr_sha256': sha(error_path), 'score_observed': False,
                    'automatic_retry': False}
        write_new(HERE / f'submit_t37_{args.attempt}_finished.json', finished)
        write_new(args.run_dir / 'finished.json', finished)
        return result.returncode
    except BaseException as exc:
        write_new(args.run_dir / 'failure.json', {'utc': utc(), 'error_type': type(exc).__name__})
        raise
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == '__main__':
    sys.exit(main())
