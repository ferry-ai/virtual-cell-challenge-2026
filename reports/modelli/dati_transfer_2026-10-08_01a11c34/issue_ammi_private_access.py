"""Issue only the consented AMMI pilot locators; never download array bodies.

Private bearer URLs stay under DATA. Subprocesses isolate account credentials.
This command neither launches compute nor changes visibility or ACLs.
"""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit
from percorso import HERE, ROOT, DATA, read, pin, sha, write_new, now

AUTH = HERE/'ammi_private_access_authorization_r1.json'
SUMMARY = HERE/'ammi_private_access_plan_r1.json'
PLAN_SHA = '8d849d0e380f24ec8517346e11f73d97af940f261fb696811ad68c12addae41d'


def frozen_plan():
    summary = read(SUMMARY)
    path = Path(summary['plan']['path'])
    if sha(path) != PLAN_SHA or summary['plan']['sha256'] != PLAN_SHA:
        raise ValueError('authorized plan changed')
    plan = read(path)
    auth = read(AUTH)
    if (auth['source_user_message_id'] != '01a1217b-c586-7a12-b5bc-251b4e3a3bac'
            or not auth['original_human_response_read_directly']
            or auth['original_answer'] != 'Sì, autorizzo questi trasferimenti privati AMMI'):
        raise ValueError('authorization differs')
    if len(plan['files']) != 105 or sum(r['bytes'] for r in plan['files']) != 1639694217:
        raise ValueError('authorized file scope differs')
    return plan


def safe_destination(path):
    path = Path(path).resolve()
    if path.is_relative_to(ROOT.resolve()) or not path.is_relative_to(DATA.resolve()):
        raise ValueError('private destination must be outside repository under DATA')
    return path


def validate_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('invalid private HTTPS locator')
    return url


def authenticate(owner):
    from cloud_campaign import CONFIG
    for key in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):
        os.environ.pop(key, None)
    os.environ['KAGGLE_CONFIG_DIR'] = str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi(); api.authenticate()
    return api


def issue(source, out):
    out = safe_destination(out)
    rows = [r for r in frozen_plan()['files'] if r['source'] == source]
    if not rows or len({r['source_kind'] for r in rows}) != 1:
        raise ValueError('source not in exact authorized plan')
    kind = rows[0]['source_kind']; owner, slug = source.split('/')
    required = {r['file']: r for r in rows}; found = {}
    api = authenticate(owner)
    with api.build_kaggle_client() as client:
        if kind == 'kernel':
            from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
            if str(api.kernels_status(source).status).split('.')[-1] != 'COMPLETE':
                raise ValueError('producer not complete')
            token = None; seen = set()
            while True:
                request = ApiListKernelSessionOutputRequest()
                request.user_name = owner; request.kernel_slug = slug
                api._set_paging(request, 100, token)
                response = client.kernels.kernels_api_client.list_kernel_session_output(request)
                for item in response.files or []:
                    name = item.file_name
                    if name.startswith(slug+'/'): name = name[len(slug)+1:]
                    remote_name = name
                    # This historical truth manifest stores a cache suffix; its
                    # producer places those exact files under the model folder.
                    if source == 'davideferrante11/vcc-effects-mix-t25-bank-r1-retry1' and name.startswith('model/cache/'):
                        name = name[len('model/'):]
                    if name in required:
                        if name in found: raise ValueError('duplicate producer output')
                        found[name] = dict(required[name], url=validate_url(item.url),resolved_remote_file=remote_name)
                token = response.next_page_token
                if not token: break
                if token in seen: raise ValueError('repeated pagination token')
                seen.add(token)
        elif kind == 'dataset':
            from kagglesdk.datasets.types.dataset_api_service import ApiDownloadDatasetRequest
            for name, row in required.items():
                request = ApiDownloadDatasetRequest()
                request.owner_slug = owner; request.dataset_slug = slug
                request.file_name = name; request.raw = True
                response = client.datasets.dataset_api_client.download_dataset(request)
                try:
                    if response.status_code != 200: raise ValueError('dataset locator HTTP status')
                    length = response.headers.get('Content-Length')
                    if length is not None and int(length) != row['bytes']:
                        raise ValueError('dataset raw-file size differs')
                    # SDK uses stream=True: record the final redirect, never read its body.
                    found[name] = dict(row, url=validate_url(response.request.url))
                finally:
                    response.close()
        else:
            raise ValueError('unsupported source kind')
    if set(found) != set(required): raise ValueError('authorized output missing')
    write_new(out, dict(utc=now(),source=source,files=found,authorization=pin(AUTH),
                       body_bytes_read=0,temporary_bearer_urls=True))
    print(json.dumps(dict(source=source,files=len(found),body_bytes_read=0)),flush=True)


def mount_check(out):
    plan = frozen_plan()
    refs = set(plan['public_or_natively_accessible_sources_not_transferred'])
    ready = read(HERE/'ntc_ready_manifest_r1.json')
    refs.update(p['job'] for p in ready['parts'].values())
    api = authenticate('davidmaisterx')
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest
    def check(ref):
        request = ApiGetKernelRequest(); request.user_name, request.kernel_slug = ref.split('/')
        with api.build_kaggle_client() as client:
            meta = client.kernels.kernels_api_client.get_kernel(request).metadata
        state = str(api.kernels_status(ref).status).split('.')[-1]
        admissible = (meta.is_private is False or ref.split('/')[0] == 'davidmaisterx')
        return dict(ref=ref,private=meta.is_private,version=meta.current_version_number,
                    state=state,native_admissible=admissible and state=='COMPLETE')
    with ThreadPoolExecutor(max_workers=4) as pool: sources = list(pool.map(check,sorted(refs)))
    if not all(s['native_admissible'] for s in sources): raise ValueError('mount inadmissible')
    write_new(out,dict(utc=now(),owner='davidmaisterx',all_sources_verified_admissible=True,
        kernel_sources=sorted(refs),dataset_sources=[],sources=sources,
        ntc_ready_manifest=pin(HERE/'ntc_ready_manifest_r1.json'),
        pending_NTC_parts=sorted(plan['pending_NTC_parts']),
        contains_only_available_inputs=True,complete_training_inputs=False))
    print(json.dumps(dict(native_mounts=len(refs),all_sources_verified_admissible=True)),flush=True)


def combine(stage, receipt):
    stage = safe_destination(stage); plan = frozen_plan(); mapping = {}; origins = []
    for source in sorted({r['source'] for r in plan['files']}):
        doc = read(stage/(source.replace('/','__')+'.private.json'))
        expected = {r['file']: r for r in plan['files'] if r['source']==source}
        if doc['source'] != source or set(doc['files']) != set(expected):
            raise ValueError('issued file scope differs')
        if doc['authorization'] != pin(AUTH): raise ValueError('issued authorization differs')
        for name, row in doc['files'].items():
            if any(row[k] != value for k,value in expected[name].items()):
                raise ValueError('issued pin differs')
            digest = row['sha256']; item = dict(sha256=digest,bytes=row['bytes'],url=validate_url(row['url']))
            if digest in mapping and mapping[digest]['bytes'] != row['bytes']:
                raise ValueError('hash has conflicting sizes')
            mapping.setdefault(digest,item)
            origins.append({k:v for k,v in row.items() if k!='url'})
    locator = stage/'private_locators.json'
    write_new(locator,dict(status='authorized',utc=now(),authorization=pin(AUTH),
        authorized_plan=read(SUMMARY)['plan'],owner='davidmaisterx',private_only=True,
        files=mapping,origins=origins,pending_NTC_parts=sorted(plan['pending_NTC_parts']),
        complete_training_inputs=False,runtime_full_size_and_sha256_verification_required=True,
        temporary_bearer_urls=True,never_log_or_commit=True))
    mounts = stage/'mount_plan.json'
    if not read(mounts)['all_sources_verified_admissible']: raise ValueError('mount check missing')
    write_new(receipt,dict(utc=now(),status='AUTHORIZED_KNOWN_INPUT_LOCATORS_READY_NTC_PENDING',
        authorization=pin(AUTH),authorized_plan=read(SUMMARY)['plan'],private_locators=pin(locator),
        mount_plan=pin(mounts),source_files=len(origins),source_bytes=sum(r['bytes'] for r in origins),
        unique_sha256=len(mapping),unique_content_bytes=sum(r['bytes'] for r in mapping.values()),
        pending_NTC_parts=sorted(plan['pending_NTC_parts']),body_bytes_read=0,
        hashes_are_expected_pins_not_fresh_remote_content_hashes=True,
        runtime_full_hash_verification_required=True,complete_training_inputs=False,
        source_visibility_changed=False,cloud_jobs_launched=0,raw_RNA_on_laptop=False))
    print(json.dumps(dict(receipt=str(receipt),source_files=len(origins),unique_sha256=len(mapping),
        pending_NTC_parts=len(plan['pending_NTC_parts']))),flush=True)


def prepare(stage, receipt):
    stage = safe_destination(stage); plan = frozen_plan(); stage.mkdir(parents=True,exist_ok=False)
    tasks = [('issue',source,str(stage/(source.replace('/','__')+'.private.json')))
             for source in sorted({r['source'] for r in plan['files']})]
    tasks.append(('mounts',str(stage/'mount_plan.json')))
    def child(args):
        env = dict(os.environ,PYTHONUTF8='1')
        run = subprocess.run([sys.executable,__file__,*args],capture_output=True,text=True,env=env,timeout=300)
        # Never forward arbitrary provider stdout/stderr (could contain URLs).
        return dict(task=args[0],source=args[1] if args[0]=='issue' else 'mounts',returncode=run.returncode)
    with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(child,tasks))
    write_new(stage/'preparation_results.json',dict(utc=now(),tasks=results))
    for result in results: print(json.dumps(result),flush=True)
    if any(r['returncode'] for r in results): raise RuntimeError('one or more isolated preparations failed')
    combine(stage,receipt)


if __name__ == '__main__':
    p=argparse.ArgumentParser(__doc__); sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('issue');a.add_argument('source');a.add_argument('out',type=Path)
    a=sub.add_parser('mounts');a.add_argument('out',type=Path)
    for name in ('prepare','combine'):
        a=sub.add_parser(name);a.add_argument('stage',type=Path);a.add_argument('receipt',type=Path)
    a=p.parse_args()
    try:
        if a.command=='issue': issue(a.source,a.out)
        elif a.command=='mounts': mount_check(a.out)
        else: globals()[a.command](a.stage,a.receipt)
    except Exception as exc:
        print('Private AMMI preparation failed: '+type(exc).__name__,file=sys.stderr)
        raise SystemExit(1)
