"""Issue private temporary download locators, outside Git, for one owner's runtime.

Each producer is queried with its own configured account. No ACL, source
visibility, dataset or collaborator is changed. Never print bearer URLs.
"""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import subprocess
import sys
from percorso import DATA, HERE, ROOT, now, pin, read, sha, write_new


def issue(owner, producer, required, out):
    from cloud_campaign import CONFIG
    for key in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):
        os.environ.pop(key, None)
    os.environ['KAGGLE_CONFIG_DIR'] = str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi, ApiListKernelSessionOutputRequest
    api = KaggleApi(); api.authenticate(); token = None; found = {}
    with api.build_kaggle_client() as client:
        while True:
            request = ApiListKernelSessionOutputRequest()
            request.user_name, request.kernel_slug = producer.split('/')
            api._set_paging(request, 100, token)
            response = client.kernels.kernels_api_client.list_kernel_session_output(request)
            for item in response.files or []:
                if item.file_name in required:
                    found[item.file_name] = dict(required[item.file_name], url=item.url)
            token = response.next_page_token
            if not token: break
    if set(found) != set(required): raise ValueError('producer output file set differs')
    write_new(out, dict(utc=now(), login_owner=owner, producer=producer, files=found,
        credentials='temporary bearer locators; keep this file private and outside Git'))
    print(json.dumps(dict(producer=producer, files=len(found), bytes=sum(x['bytes'] for x in found.values()))), flush=True)


def prepare(release_path, runtime_owner, revision, resume=False):
    release = read(release_path); view_path = Path(release['view']['path'])
    if sha(view_path) != release['view']['sha256']: raise ValueError('view changed')
    view = read(view_path); provenance = {p['producer']: p for p in view['provenance']}
    grouped = defaultdict(dict)
    for chunk in view['chunks']:
        grouped[chunk['producer']][chunk['producer_file']] = {k:chunk[k] for k in ('sha256','bytes')}
    stage = DATA/'processed/dati_transfer_2026-10-08_01a11c34/runtime_access'/revision
    stage.mkdir(parents=True, exist_ok=resume)
    if (stage/'runtime_inputs.json').exists(): raise ValueError('completed access release is immutable')
    sources = {}; locators = {}; mounts = []
    for producer, files in sorted(grouped.items()):
        owner = producer.split('/')[0]
        verification = read(provenance[producer]['verification']['path'])
        proof = verification.get('remote_identity')
        if proof is None:
            identity_path = stage/(producer.replace('/','__')+'.identity.json')
            if identity_path.exists(): proof = read(identity_path)
            else:
                result = subprocess.run([sys.executable,str(HERE/'remote_identity.py'),owner,producer],
                    capture_output=True,text=True,encoding='utf-8',check=True)
                proof = json.loads(result.stdout);write_new(identity_path,proof)
        route = 'native_mount' if owner == runtime_owner or not proof['is_private'] else 'authenticated_output_download'
        sources[producer] = dict(owner=owner, private=proof['is_private'], version=proof['version'], route=route,
            chunks=len(files), bytes=sum(x['bytes'] for x in files.values()),
            identity_evidence=provenance[producer]['verification'])
        if route == 'native_mount': mounts.append(producer); continue
        request_path = stage/(producer.replace('/','__')+'.request.json')
        output_path = stage/(producer.replace('/','__')+'.private.json')
        if request_path.exists():
            if not resume or read(request_path)!=files: raise ValueError('resumed request differs')
        else: write_new(request_path, files)
        if not output_path.exists():
            subprocess.run([sys.executable, str(Path(__file__)), 'issue', owner, producer, str(request_path), str(output_path)], check=True)
        issued = read(output_path)
        if issued['producer']!=producer or issued['login_owner']!=owner or set(issued['files'])!=set(files):
            raise ValueError('issued producer identity differs')
        if any(any(issued['files'][n][k]!=v for k,v in expected.items()) for n,expected in files.items()):
            raise ValueError('issued chunk pins differ')
        locators.update({producer+'/'+name: record for name,record in issued['files'].items()})
    locator_path = stage/'private_locators.json'
    write_new(locator_path, dict(utc=now(), runtime_owner=runtime_owner, release=pin(release_path),
        view=release['view'], files=locators, private=True, never_log_or_commit=True))
    write_new(stage/'runtime_inputs.json', dict(utc=now(), release=pin(release_path), view=release['view'],
        kernel_sources=mounts, private_locators=pin(locator_path), sources=sources))
    write_new(HERE/('runtime_access_'+revision+'.json'), dict(utc=now(), runtime_owner=runtime_owner,
        release=pin(release_path), view=release['view'], sources=sources,
        private_locators=dict(path=locator_path.as_posix(), files=len(locators), bytes=sum(x['bytes'] for x in locators.values())),
        kernel_sources=mounts, locators_are_not_data_access_verification=True,
        source_visibility_changed=False, runtime_chunk_hashes_verified=False))
    print(json.dumps(dict(runtime_owner=runtime_owner, mounts=len(mounts), authenticated_chunks=len(locators),
        authenticated_bytes=sum(x['bytes'] for x in locators.values()), stage=str(stage))))


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('prepare'); a.add_argument('release',type=Path); a.add_argument('runtime_owner'); a.add_argument('revision'); a.add_argument('--resume',action='store_true')
    a = sub.add_parser('issue'); a.add_argument('owner'); a.add_argument('producer'); a.add_argument('required',type=Path); a.add_argument('out',type=Path)
    a = p.parse_args()
    try:
        if a.command == 'prepare': prepare(a.release,a.runtime_owner,a.revision,a.resume)
        else: issue(a.owner,a.producer,read(a.required),a.out)
    except Exception as exc:
        # Provider exceptions can contain signed URLs; never echo their messages.
        print('Runtime access preparation failed: '+type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
