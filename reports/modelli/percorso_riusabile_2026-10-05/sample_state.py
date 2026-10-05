"""Verify saved sample manifests without transferring matrices; isolate SDK accounts."""
import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from pipeline_state import CONFIG, REPO, command, sha

HERE = Path(__file__).resolve().parent


def fetch(job, out):
    import requests
    from kaggle.api.kaggle_api_extended import KaggleApi, ApiGetKernelRequest, ApiListKernelSessionOutputRequest
    owner, slug = job.split('/')
    api = KaggleApi(); api.authenticate()
    req = ApiGetKernelRequest(); req.user_name = owner; req.kernel_slug = slug
    with api.build_kaggle_client() as client:
        saved = client.kernels.kernels_api_client.get_kernel(req)
    version = saved.metadata.current_version_number
    if version <= 0 or not saved.metadata.is_private:
        raise ValueError('expected a saved private version')
    files, receipts, token = [], {}, None
    while True:
        listing = ApiListKernelSessionOutputRequest()
        listing.user_name = owner; listing.kernel_slug = slug; listing.page_size = 100
        if token:
            listing.page_token = token
        with api.build_kaggle_client() as client:
            page = client.kernels.kernels_api_client.list_kernel_session_output(listing)
        for item in page.files or []:
            name = item.file_name; files.append(name)
            if name.startswith('samples/') and name.endswith('/complete.json'):
                raw = bytearray()
                with requests.get(item.url, stream=True, timeout=(20,30)) as response:
                    response.raise_for_status()
                    for chunk in response.iter_content(65536):
                        raw.extend(chunk)
                        if len(raw) > 1 << 20:
                            raise ValueError('oversized completion metadata')
                value = json.loads(raw)
                if Path(name).parts != ('samples', value['unit'], 'complete.json'):
                    raise ValueError('invalid receipt path')
                path = out/'receipts'/owner/slug/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.open('xb').write(raw)
                receipts[value['unit']] = {'value':value,'path':path.relative_to(REPO).as_posix(), 'sha256':sha(path)}
        token = page.next_page_token
        if not token:
            break
    with api.build_kaggle_client() as client:
        after = client.kernels.kernels_api_client.get_kernel(req)
    if after.metadata.current_version_number != version or after.blob.source != saved.blob.source:
        raise ValueError('version changed during output inspection')
    return {'receipts':receipts,'files':files,'saved_version':{
        'version':version,'kernel_id':saved.metadata.id,'private':True,
        'version_ref':job+'/versions/'+str(version),
        'saved_source_sha256':hashlib.sha256(saved.blob.source.encode()).hexdigest(),
        'version_stable_during_output_read':True}}


def validate(record, remote, bank_info):
    unit = record['parameters']['unit']; bank = bank_info['bank']
    if remote['saved_version']['saved_source_sha256'] != record['code_sha256']:
        raise ValueError('saved source differs from accepted launch')
    received = remote['receipts'][unit]; sample = received['value']
    bank_path = REPO/bank['receipt']
    if sha(bank_path) != bank['receipt_sha256']:
        raise ValueError('bank manifest changed')
    original = json.loads(bank_path.read_text())
    if (not sample['complete'] or sample['unit'] != unit or sample['genes'] != 18533
        or sample['bank_receipt_sha256'] != bank['receipt_sha256']
        or sample['bank_receipt_sha256'] != record['parameters']['bank_receipt_sha256']
        or sample['source_verification'] != original['source_verification']):
        raise ValueError('sample lineage mismatch')
    levels = sample['levels']
    if set(levels) != {'32','64','128'} or not 0 < levels['32'] <= levels['64'] <= levels['128'] == original['samples128']:
        raise ValueError('sample population coverage mismatch')
    for name, parent in [('bank_rows.csv','rows.csv'),('mask.npz','mask.npz')]:
        if sample['files'][name] != original['files'][parent]:
            raise ValueError('sample rows/mask differs from bank')
    matrices = {n:v for n,v in sample['files'].items() if n.endswith('.npz') and n != 'mask.npz'}
    if sum(v['cells'] for v in matrices.values()) != levels['128']:
        raise ValueError('shard cell coverage mismatch')
    sources = {s['file'].replace('\\','/') for s in original['sources']}
    seen = set()
    for name, info in sample['files'].items():
        if Path(name).name != name or 'samples/'+unit+'/'+name not in remote['files']:
            raise ValueError('missing or invalid sample output')
        if name in matrices:
            source = info['source_file'].replace('\\','/')
            if source not in sources or source in seen:
                raise ValueError('unexpected or duplicate raw source')
            seen.add(source)
            partner = sample['files'][name[:-4]+'.jsonl.gz']
            if any(partner[k] != info[k] for k in ('source_file','source_sha256','cells')):
                raise ValueError('matrix/metadata lineage mismatch')
    return {'state':'remote_complete_manifest_checked','kernel':record['slug'],
            'receipt':received['path'],'receipt_sha256':received['sha256'],
            'saved_version':remote['saved_version'],'levels':levels,
            'bytes':sum(f['bytes'] for f in sample['files'].values()),
            'bank_receipt_sha256':bank['receipt_sha256'],
            'consumer_hashes_verified':False,'training_used':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    banks=json.loads(args.state.read_text())['units']
    launches=[r for r in map(json.loads,(HERE/'sample_launches.jsonl').read_text().splitlines()) if r['accepted']]
    if len({r['slug'] for r in launches}) != len(launches):
        raise ValueError('ambiguous accepted launches')
    statuses=list(concurrent.futures.ThreadPoolExecutor(6).map(lambda r:command(r['slug'],['status']),launches))
    units={}
    for record,status in zip(launches,statuses):
        unit=record['parameters']['unit'];entry={'status':status,'state':'not_complete','kernel':record['slug']}
        if status['returncode']==0 and 'KernelWorkerStatus.COMPLETE' in status['text']:
            owner=record['slug'].split('/')[0]
            run=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--fetch',record['slug'],str(out)],
                env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG[owner])},
                capture_output=True,encoding='utf-8',errors='replace',timeout=180)
            if run.returncode:
                raise RuntimeError('sample metadata retrieval failed: '+record['slug']+'; no matrices transferred')
            entry.update(validate(record,json.loads(run.stdout),banks[unit]))
        units[unit]=entry
    result={'utc':datetime.now(timezone.utc).isoformat(),'units':units,'extended_training_ready':False}
    (out/'state.json').write_text(json.dumps(result,indent=1))
    print(json.dumps({u:{k:v for k,v in info.items() if k in ('state','levels','bytes')} for u,info in units.items()}))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--fetch':
        print(json.dumps(fetch(sys.argv[2],Path(sys.argv[3]))))
    else:
        main()
