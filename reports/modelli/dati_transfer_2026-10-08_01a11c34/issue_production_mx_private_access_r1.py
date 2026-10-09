"""Prepare MX production bearer locators ONLY after specific human consent.

Default is an offline gate check. --issue explicitly enables metadata requests.
No payload download, publication, ACL modification or compute launch is implemented.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit
from percorso import HERE, ROOT, DATA, read, pin, sha, write_new, now

PLAN = ROOT / 'reports/analisi/modelli_esterni_01a11c35_2026-10-08/ammi_production_mx_access_plan_r1.json'
PLAN_SHA = '2337ee0dfd807c25e68b78bd2ba2a0bcf2ce44bf41a2f4aadb0eeb3ff5c5535c'
OWNER = 'davidmaisterx'
JOB = 'davidmaisterx/ammi-production-cells-17-01a11c35-r1'
PURPOSE = 'AMMI production cells seed17'


def validate_authorization(auth, plan_sha, code_sha, job):
    if job != JOB:
        raise ValueError('exact private destination job required')
    expected = dict(granted=True, original_human_response_read_directly=True,
        production_inputs_authorized=True, destination_owner=OWNER,
        destination_job=job, purpose=PURPOSE, private_only=True,
        plan_sha256=plan_sha, emitter_sha256=code_sha,
        file_count=209, total_bytes=10100920946,
        temporary_bearer_urls_explicitly_authorized=True,
        all_209_payloads_including_119_pilot_hashes_authorized=True)
    if any(auth.get(k) != v for k, v in expected.items()):
        raise ValueError('specific production authorization absent or scope differs')
    for field in ['source_thread_id', 'source_user_message_id', 'original_answer']:
        if not isinstance(auth.get(field), str) or not auth[field].strip():
            raise ValueError('direct human authorization evidence missing')


def guard(auth_path, job):
    if sha(PLAN) != PLAN_SHA:
        raise ValueError('frozen payload plan hash differs')
    plan = read(PLAN)
    if sha(plan['source_inventory']['path']) != plan['source_inventory']['sha256']:
        raise ValueError('source inventory changed')
    rows = plan['files']
    if (plan['destination_account'] != OWNER or plan['destination_job'] != JOB or plan['private_only'] is not True
            or len(rows) != 209 or sum(r['bytes'] for r in rows) != 10100920946
            or len({r['sha256'] for r in rows}) != 209
            or len({(r['source'], r['file']) for r in rows}) != 209):
        raise ValueError('payload scope differs')
    validate_authorization(read(auth_path), PLAN_SHA, sha(__file__), job)
    return plan


def safe_stage(path):
    path = Path(path).resolve()
    if not path.is_relative_to(DATA.resolve()) or path.is_relative_to(ROOT.resolve()):
        raise ValueError('bearer files must stay under DATA outside repository')
    return path


def safe_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('invalid HTTPS locator')
    return url


def fetch_source(args):
    plan = guard(args.authorization, args.job)
    stage = safe_stage(args.stage)
    rows = [r for r in plan['files'] if r['source'] == args.source]
    if not rows:
        raise ValueError('source outside frozen plan')
    required = {r['file']: r for r in rows}
    # SDK account configuration must precede import, isolated in this subprocess.
    from issue_ammi_private_access import authenticate
    owner, slug = args.source.split('/')
    api = authenticate(owner)
    from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest
    if str(api.kernels_status(args.source).status).split('.')[-1] != 'COMPLETE':
        raise ValueError('source not COMPLETE')
    found = {}; token = None; seen = set()
    while True:
        request = ApiListKernelSessionOutputRequest()
        request.user_name = owner; request.kernel_slug = slug
        api._set_paging(request, 100, token)
        with api.build_kaggle_client() as client:
            response = client.kernels.kernels_api_client.list_kernel_session_output(request)
        for item in response.files or []:
            name = item.file_name
            if name.startswith(slug + '/'):
                name = name[len(slug) + 1:]
            if name in required:
                if name in found:
                    raise ValueError('duplicate remote filename')
                found[name] = dict(required[name], url=safe_url(item.url))
        token = response.next_page_token
        if not token:
            break
        if token in seen:
            raise ValueError('repeated pagination token')
        seen.add(token)
    if set(found) != set(required):
        raise ValueError('expected payload not found')
    write_new(stage / (args.source.replace('/', '__') + '.private.json'),
        dict(source=args.source, authorization=pin(args.authorization),
             destination_job=args.job, files=found, body_bytes_read=0))


def issue(args, plan):
    stage = safe_stage(args.stage)
    receipt = Path(args.receipt).resolve()
    if not receipt.is_relative_to(HERE.resolve()) or receipt.exists():
        raise ValueError('new public receipt must be inside own report folder')
    stage.mkdir(parents=True, exist_ok=False)
    auth_pin = pin(args.authorization)
    for source in sorted({r['source'] for r in plan['files']}):
        command = [sys.executable, str(Path(__file__).resolve()),
            '--authorization', str(Path(args.authorization).resolve()), '--job', args.job,
            '--stage', str(stage), '--source', source, '--issue']
        child = subprocess.run(command, capture_output=True, timeout=300,
                               env=dict(os.environ, PYTHONUTF8='1'))
        # Never forward SDK stdout/stderr, which might contain bearer references.
        if child.returncode:
            raise RuntimeError('isolated source locator request failed')
    guard(args.authorization, args.job)
    if pin(args.authorization) != auth_pin:
        raise ValueError('authorization changed during issuance')
    mapping = {}; origins = []
    for source in sorted({r['source'] for r in plan['files']}):
        expected = {r['file']: r for r in plan['files'] if r['source'] == source}
        part = read(stage / (source.replace('/', '__') + '.private.json'))
        if (part['authorization'] != auth_pin or part['destination_job'] != args.job
                or part['source'] != source or set(part['files']) != set(expected)):
            raise ValueError('issued source scope differs')
        for name, row in part['files'].items():
            if any(row.get(k) != v for k, v in expected[name].items()):
                raise ValueError('issued file pin differs')
            mapping[row['sha256']] = dict(sha256=row['sha256'], bytes=row['bytes'], url=safe_url(row['url']))
            origins.append(dict(source_kind='kernel', **expected[name]))
    if len(mapping) != 209 or sum(r['bytes'] for r in mapping.values()) != 10100920946:
        raise ValueError('combined payload scope differs')
    locator = stage / 'private_locators.json'
    write_new(locator, dict(status='authorized', utc=now(), owner=OWNER,
        destination_job=args.job, purpose=PURPOSE, private_only=True,
        authorization=auth_pin, authorized_plan=pin(PLAN), emitter=pin(__file__),
        files=mapping, origins=origins, temporary_bearer_urls=True,
        never_log_or_commit=True, runtime_full_size_and_sha256_verification_required=True,
        ready_for_training=False))
    write_new(receipt, dict(utc=now(), status='LOCATORS_ISSUED_CONSUMER_HASHES_PENDING',
        authorization=auth_pin, plan=pin(PLAN), emitter=pin(__file__),
        destination_job=args.job, private_locators=pin(locator),
        files=209, bytes=10100920946, body_bytes_read=0, cloud_jobs_launched=0,
        hashes_are_expected_pins_not_fresh_remote_content_hashes=True,
        source_visibility_changed=False, consumer_full_size_and_sha256_required=True,
        ready_for_training=False))
    print(json.dumps(dict(status='LOCATORS_ISSUED_CONSUMER_HASHES_PENDING', receipt=str(receipt))))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--authorization', required=True, type=Path)
    parser.add_argument('--job', required=True)
    parser.add_argument('--issue', action='store_true')
    parser.add_argument('--stage', type=Path)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--source', help=argparse.SUPPRESS)
    args = parser.parse_args()
    plan = guard(args.authorization, args.job)
    if not args.issue:
        print(json.dumps(dict(status='OFFLINE_CONSENT_GATE_PASS', files=209,
                             bytes=10100920946, network_calls=0)))
        return
    if not args.stage or (not args.source and not args.receipt):
        raise ValueError('issuance output paths required')
    if args.source:
        fetch_source(args)
    else:
        issue(args, plan)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Intentionally omit exception text and traceback; provider errors can contain URLs.
        print('Production access gate/issuance failed: ' + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
