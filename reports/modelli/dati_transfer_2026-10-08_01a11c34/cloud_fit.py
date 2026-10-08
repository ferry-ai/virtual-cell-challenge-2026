"""Explicit one-shot launch/status/collection for the prepared, authorized T1 job."""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import re
import shutil
import sys
import zipfile
from percorso import BANK, HERE, ROOT, now, pin, read, sha, write_new

sys.path.insert(0, str(ROOT / 'reports/modelli/percorso_riusabile_2026-10-05'))
from preflight_slots_fast_v1 import call


def launch(revision, preflight, public=False):
    folder = HERE / 'fit' / revision
    proof = read(folder / 'prepared.json')
    stage = ROOT / proof['stage']
    for key, name in [('code', 'run.py'), ('params', 'params.json'), ('release', 'release.json')]:
        if sha(stage / name) != proof[key]['sha256']:
            raise ValueError('package changed: ' + name)
    code = (stage / 'run.py').read_text(encoding='utf-8')
    match = re.search(r"b64decode\('([A-Za-z0-9+/=]+)'\)", code)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(match.group(1)))) as z:
        members = [{'path': i.filename, 'bytes': i.file_size} for i in z.infolist() if not i.is_dir()]
    pre = read(preflight)
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(pre['utc'])).total_seconds()
    owner = proof['slug'].split('/')[0]
    if age > 900 or pre['active'][owner] >= pre['slot_limit_per_account']:
        raise ValueError('fresh accessible slot required')
    rc, text = call(owner, ['kernels', 'list', '--mine', '--search', proof['slug'].split('/')[1], '--csv'])
    if rc or proof['slug'] in text:
        raise ValueError('duplicate job or dedup query failed')
    if public:
        new = folder / 'public_package'
        shutil.copytree(stage, new)
        meta = read(new / 'kernel-metadata.json')
        meta['is_private'] = False
        (new / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8')
        stage = new
    write_new(folder / 'launch_intent.json', dict(utc=now(), stage=str(stage), code=pin(stage / 'run.py'),
        metadata=pin(stage / 'kernel-metadata.json'), preflight=pin(preflight), slug=proof['slug'],
        public_requested=public, embedded_members=members,
        authorization='owner authorized this T1 CPU job in chat, preferring public; no dataset visibility changes'))
    rc, text = call(owner, ['kernels', 'push', '-p', str(stage)])
    write_new(folder / 'launch_result.json', dict(utc=now(), returncode=rc, answer=text,
        accepted=rc == 0 and 'successfully pushed' in text, slug=proof['slug']))
    print(text)
    if rc:
        raise SystemExit(rc)
    status(revision, folder / 'status_after_push.json')


def status(revision, out):
    proof = read(HERE / 'fit' / revision / 'prepared.json')
    rc, text = call(proof['slug'].split('/')[0], ['kernels', 'status', proof['slug']])
    write_new(out, dict(utc=now(), slug=proof['slug'], returncode=rc, answer=text))
    print(text)


def collect(revision, destination):
    """Retrieve our authorized job's outputs, then verify identity and consumption."""
    folder = HERE / 'fit' / revision
    proof = read(folder / 'prepared.json')
    owner, slug = proof['slug'].split('/')
    rc, text = call(owner, ['kernels', 'status', proof['slug']])
    if rc or 'COMPLETE' not in text:
        raise ValueError('job is not complete: ' + text)
    out = Path(destination).resolve()
    out.mkdir(parents=True, exist_ok=False)
    rc, text = call(owner, ['kernels', 'output', proof['slug'], '-p', str(out),
        '--file-pattern', 'consumo.json|status.json|manifest.json|recipe_release.json|effects_.*.npz'])
    write_new(folder / 'retrieval.json', dict(utc=now(), returncode=rc, answer=text, destination=str(out)))
    if rc:
        raise ValueError('retrieval failed; partial outputs preserved')
    verify_outputs(revision, out)


def verify_outputs(revision, destination):
    """Verify existing downloads independently of CLI log encoding or exit status."""
    folder = HERE / 'fit' / revision
    proof = read(folder / 'prepared.json')
    owner, slug = proof['slug'].split('/')
    out = Path(destination).resolve()
    sys.path.insert(0, str(BANK))
    # An already imported module with the same basename must not be mistaken for the historical entry.
    import importlib.util
    spec = importlib.util.spec_from_file_location('historical_bank_entry', BANK / 'percorso.py')
    historical = importlib.util.module_from_spec(spec); spec.loader.exec_module(historical)
    saved = historical.saved_kernel(owner, slug)
    stage = ROOT / proof['stage']
    if saved.blob.source.replace('\r\n','\n') != (stage / 'run.py').read_text(encoding='utf-8').replace('\r\n','\n'):
        raise ValueError('saved cloud code differs')
    consumption = read(out / 'consumo.json')
    release = read(stage / 'release.json')
    expected = sorted(release['voted'])
    checks = dict(saved_code_matches=True,
        release_sha_matches=consumption['release_sha256'] == sha(stage / 'release.json'),
        expected_verified_read_equal=expected == consumption['sources_expected'] == consumption['sources_verified'] == consumption['sources_read_by_stage100'],
        no_unexplained_targets=not consumption['targets_changed_outside_added_votes'],
        reference_recipe_matches=consumption['reference']['equals_recorded_t36_recipe'])
    files = {}
    for context in ('A','B','C'):
        path = out / 'effects' / ('effects_%s.npz' % context)
        files[context] = pin(path)
        checks['effect_' + context + '_sha_matches'] = sha(path) == consumption['contexts'][context]['release_sha256']
    write_new(folder / 'verification.json', dict(utc=now(), checks=checks, effects=files,
        consumption=pin(out / 'consumo.json'), release=pin(stage / 'release.json'),
        claims_predictive_improvement=False, claims_complete_corpus=False))
    if not all(checks.values()):
        raise ValueError('output verification failed')
    for filename in ('consumo.json','status.json','reference_manifest.json'):
        source = out / filename
        if source.is_file():
            with (folder / filename).open('xb') as f:
                f.write(source.read_bytes())
    print(json.dumps(dict(checks=checks, sources=len(expected), effects=files)))


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('launch')
    q.add_argument('revision'); q.add_argument('preflight', type=Path); q.add_argument('--public', action='store_true')
    q = sub.add_parser('status'); q.add_argument('revision'); q.add_argument('out', type=Path)
    q = sub.add_parser('collect'); q.add_argument('revision'); q.add_argument('destination', type=Path)
    q = sub.add_parser('verify'); q.add_argument('revision'); q.add_argument('destination', type=Path)
    args = p.parse_args()
    if args.command == 'launch':
        launch(args.revision, args.preflight, args.public)
    elif args.command == 'status':
        status(args.revision, args.out)
    elif args.command == 'collect':
        collect(args.revision, args.destination)
    else:
        verify_outputs(args.revision, args.destination)
