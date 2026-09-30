"""Validate a declared job contract; never install, queue, infer, score or submit.

python preflight.py validate --manifest job.json --site runtime --receipt new.json
Run inside the same Python environment that will execute the scientific job.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import socket
import sys
import tempfile
import time
import zipfile


class InvalidJob(ValueError):
    pass


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def physical(item, site):
    value = item.get('paths', {}).get(site)
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        raise InvalidJob(f"Missing absolute {site} path: {item.get('id', 'environment')}")
    return Path(value)


def check_file(item, site):
    path = physical(item, site)
    expected = item.get('sha256')
    size = item.get('bytes')
    if not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected):
        raise InvalidJob('Missing/invalid SHA256: ' + item['id'])
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise InvalidJob('Missing/invalid byte size: ' + item['id'])
    if not path.is_file():
        raise InvalidJob('Missing input: ' + str(path))
    before = path.stat()
    if before.st_size != size:
        raise InvalidJob('Input size differs: ' + item['id'])
    actual = digest(path)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise InvalidJob('Input changed during hashing: ' + item['id'])
    if actual != expected:
        raise InvalidJob('Input SHA256 differs: ' + item['id'])
    return {'id': item['id'], 'path': str(path), 'bytes': size, 'sha256': actual}


def check_targets(check, inputs, site):
    import numpy as np
    item = inputs.get(check.get('input_id'))
    if item is None:
        raise InvalidJob('Target check names an undeclared input')
    path = physical(item, site)
    key = check.get('npz_key', 'targets')
    required = check.get('required')
    if not isinstance(key, str) or not isinstance(required, list) or not required or not all(isinstance(t, str) and t for t in required):
        raise InvalidJob('Target check needs a nonempty explicit string target list')
    if len(set(required)) != len(required):
        raise InvalidJob('Duplicate required targets')
    # Inspect one metadata array only; never materialize effects/count matrices.
    with zipfile.ZipFile(path) as archive:
        members = [m for m in archive.infolist() if m.filename == key + '.npy']
        if len(members) != 1 or members[0].file_size > 16 * 1024**2:
            raise InvalidJob('Missing/ambiguous/oversized NPZ target metadata')
    with np.load(path, allow_pickle=False) as archive:
        values = archive[key]
        if values.ndim != 1 or values.dtype.kind not in ('U', 'S'):
            raise InvalidJob('Target metadata must be a one-dimensional non-object string array')
        actual = values.astype(str).tolist()
    if len(set(actual)) != len(actual):
        raise InvalidJob('Duplicate targets in source metadata')
    missing = sorted(set(required) - set(actual))
    if missing:
        raise InvalidJob('Source metadata lacks required targets: ' + ', '.join(missing))
    return {'input_id': item['id'], 'npz_key': key, 'required_count': len(required), 'available_count': len(actual)}


def environment_probe(spec, site):
    if not isinstance(spec, dict) or 'probes' not in spec or 'imports' not in spec or 'packages' not in spec:
        raise InvalidJob('Declare environment packages, imports and probes explicitly (empty lists allowed)')
    expected_python = spec.get('python')
    if expected_python and os.path.normcase(os.path.abspath(physical(expected_python, site))) != os.path.normcase(os.path.abspath(sys.executable)):
        raise InvalidJob('Preflight is not running in the declared job Python')
    versions = {}
    for name, wanted in spec['packages'].items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as e:
            raise InvalidJob('Missing environment package: ' + name) from e
        if wanted is not None and actual != wanted:
            raise InvalidJob(f'Environment version differs: {name} {actual} != {wanted}')
        versions[name] = actual
    for name in spec['imports']:
        if not re.fullmatch('[A-Za-z_][A-Za-z_0-9.]*', name):
            raise InvalidJob('Invalid import name')
        importlib.import_module(name)
    done = []
    for probe in spec['probes']:
        if probe != 'h5ad_nullable_roundtrip':
            raise InvalidJob('Unknown environment probe: ' + str(probe))
        import anndata as ad
        import numpy as np
        import pandas as pd
        import scipy.sparse as sp
        if spec.get('allow_write_nullable_strings') is True:
            if not hasattr(ad.settings, 'allow_write_nullable_strings'):
                raise InvalidJob('Requested nullable-string option is unavailable')
            ad.settings.allow_write_nullable_strings = True
        with tempfile.TemporaryDirectory(prefix='vcc_preflight_') as directory:
            path = Path(directory) / 'roundtrip.h5ad'
            x = sp.csr_matrix(np.array([[1, 0], [3, 2]], dtype=np.float32))
            obj = ad.AnnData(x, obs=pd.DataFrame({'gene': pd.array(['NTC', 'NTC'], dtype='string')}, index=['0', '1']),
                            var=pd.DataFrame(index=pd.Index(['A', 'B'], dtype='string')))
            obj.write_h5ad(path)
            restored = ad.read_h5ad(path)
            if list(restored.var_names) != ['A', 'B'] or list(restored.obs.gene) != ['NTC', 'NTC']:
                raise InvalidJob('H5AD string roundtrip differs')
            np.testing.assert_array_equal(restored.X.toarray(), x.toarray())
        done.append(probe)
    return {'executable': sys.executable, 'python': platform.python_version(), 'packages': versions,
            'imports_passed': spec['imports'], 'probes_passed': done,
            'configuration_scope': 'This process only; a later producer must apply the same options in its own wrapper'}


def validate(manifest, site):
    if manifest.get('schema_version') != 1 or not manifest.get('job_id'):
        raise InvalidJob('Unsupported job manifest or absent job_id')
    listed = manifest.get('inputs')
    outputs = manifest.get('outputs')
    if not isinstance(listed, list) or not listed or not isinstance(outputs, list) or not outputs:
        raise InvalidJob('Declare every input and at least one new output')
    ids = [x.get('id') for x in listed + outputs]
    if not all(isinstance(i, str) and i for i in ids) or len(set(ids)) != len(ids):
        raise InvalidJob('Missing or duplicate input/output IDs')
    input_paths = {physical(item, site).resolve() for item in listed}
    output_paths = []
    for item in outputs:
        path = physical(item, site)
        if item.get('must_be_absent') is not True:
            raise InvalidJob('Output must explicitly require a new path')
        if path.exists() or path.resolve() in input_paths:
            raise InvalidJob('Output already exists or aliases input: ' + str(path))
        resolved = path.resolve()
        for previous in output_paths:
            other = Path(previous).resolve()
            if resolved == other or resolved in other.parents or other in resolved.parents:
                raise InvalidJob('Output paths overlap or are duplicated')
        output_paths.append(str(path))
    # Exhaustively check files; no early successful marker substitutes for another input.
    for item in listed:
        path = physical(item, site)
        if not path.is_file():
            raise InvalidJob('Missing input: ' + str(path))
        if path.stat().st_size != item.get('bytes'):
            raise InvalidJob('Input size differs: ' + item['id'])
    verified = [check_file(item, site) for item in listed]
    checks = [check_targets(check, {i['id']: i for i in listed}, site) for check in manifest.get('target_checks', [])]
    env = environment_probe(manifest.get('environment'), site)
    return {'status': 'PASS', 'site': site, 'job_id': manifest['job_id'], 'host': socket.gethostname(),
            'checked_utc': datetime.now(timezone.utc).isoformat(), 'inputs': verified, 'new_outputs': output_paths,
            'target_checks': checks, 'environment': env,
            'scope': 'Only declared contract checked on this host; no scientific success or authorization implied'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['validate'])
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--site', choices=['local', 'runtime'], required=True)
    p.add_argument('--receipt', type=Path, required=True)
    p.add_argument('--attempts', type=int, default=1)
    p.add_argument('--interval-seconds', type=float, default=20)
    a = p.parse_args()
    if a.receipt.exists():
        raise FileExistsError(a.receipt)
    if not 1 <= a.attempts <= 180 or not 0 <= a.interval_seconds <= 60:
        p.error('Attempts1..180; interval0..60 seconds')
    raw_manifest = a.manifest.read_bytes()
    manifest = json.loads(raw_manifest.decode('utf-8'))
    # A receipt must not create the job's supposedly new output directory.
    for output in manifest.get('outputs', []):
        root = physical(output, a.site).resolve()
        if a.receipt.resolve() == root or root in a.receipt.resolve().parents:
            p.error('Receipt must be outside every declared job output')
    result = None
    for attempt in range(1, a.attempts + 1):
        try:
            result = validate(manifest, a.site)
            break
        except (OSError, ValueError, ImportError, AssertionError, KeyError, TypeError) as e:
            result = {'status': 'FAIL', 'site': a.site, 'job_id': manifest.get('job_id'),
                      'checked_utc': datetime.now(timezone.utc).isoformat(), 'error': f'{type(e).__name__}: {e}'}
            print(f'preflight {attempt}/{a.attempts}: {result["error"]}', file=sys.stderr, flush=True)
            if attempt < a.attempts:
                time.sleep(a.interval_seconds)
    try:
        if a.manifest.read_bytes() != raw_manifest:
            result |= {'status': 'FAIL', 'error': 'Manifest changed during preflight; create a new reviewed attempt'}
    except OSError as error:
        result |= {'status': 'FAIL', 'error': f'Manifest unavailable after preflight: {error}'}
    result |= {'manifest_sha256': hashlib.sha256(raw_manifest).hexdigest(), 'validator_sha256': digest(__file__), 'attempts_used': attempt}
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    with a.receipt.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False); stream.write('\n')
    print(json.dumps({'status': result['status'], 'receipt': str(a.receipt)}))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
