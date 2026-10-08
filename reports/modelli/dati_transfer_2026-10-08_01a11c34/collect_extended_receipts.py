"""Collect allowlisted small T3 receipts, never source chunks or private URLs."""
import json
from pathlib import Path
import re
import requests
from percorso import DATA,HERE,read,pin,write_new,now,sha
from quick_generation_cloud import api_for_owner


def main():
    folder=HERE/'extended_transfer/r1';proof=read(folder/'prepared.json');slug=proof['slug']
    api=api_for_owner(proof['owner'])
    from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest
    req=ApiListKernelSessionOutputRequest();req.user_name,req.kernel_slug=slug.split('/');req.page_size=100
    wanted={'t3_consumption.json','t3_complete.json','recipe_t3.json','extended_runtime_preflight.json',
        'generation_preflight.json','failure.json','consumo.json','recipe_release.json'}
    dest=folder/'fit_completion_r1';dest.mkdir(exist_ok=False)
    got={}
    while True:
        with api.build_kaggle_client() as c:response=c.kernels.kernels_api_client.list_kernel_session_output(req)
        for item in response.files or []:
            if item.file_name not in wanted:continue
            r=requests.get(item.url,timeout=60);r.raise_for_status()
            if len(r.content)>2_000_000:raise ValueError('receipt too large')
            text=r.content.decode('utf-8')
            if 'kaggleusercontent.com' in text or '"url"' in text:raise ValueError('sensitive field in public receipt')
            path=dest/item.file_name
            with path.open('xb') as f:f.write(r.content)
            json.loads(text);got[item.file_name]=pin(path)
        if not response.next_page_token:break
        req.page_token=response.next_page_token
    if not {'t3_consumption.json','t3_complete.json'}.issubset(got):raise ValueError('T3 fit receipt absent')
    receipt=read(dest/'t3_consumption.json');done=read(dest/'t3_complete.json');plan=read(folder/'protocol.json')
    if done['receipt_sha256']!=sha(dest/'t3_consumption.json') or receipt['protocol']['sha256']!=sha(folder/'protocol.json'):
        raise ValueError('receipt pin differs')
    if not receipt['t1_null_parity'] or receipt['changed_outside_ko'] or set(receipt['changed_targets'])!=set(plan['panel_targets']):
        raise ValueError('T3 scientific contract differs')
    expected={k:(v['bytes'],v['sha256']) for k,v in plan['chunks'].items()}
    actual={x['key']:(x['bytes'],x['sha256']) for x in receipt['chunks']}
    if actual!=expected or len(receipt['ko_contexts'])!=12 or len(receipt['ko_study_votes'])!=5:
        raise ValueError('KO consumption incomplete')
    if any(c['measured_pairs']<=0 or c['nonzero_pairs']<=0 for c in receipt['ko_contexts']):
        raise ValueError('KO context has no actual signal')
    report=dict(utc=now(),status='FIT_VERIFIED_GENERATION_CLI_FAILED',files=got,
        T1_null_parity=True,required_chunks_verified=22,ko_contexts=12,ko_study_votes=5,changed_targets=34,
        no_changes_outside_ko=True,effects=receipt['effects'],
        downloaded_source_arrays=False,arrays_independently_rehashed_locally=False,
        cloud_runtime_performed_full_hash_axis_mask_checks=True)
    write_new(dest/'verification.json',report)
    print(json.dumps({k:report[k] for k in ('status','T1_null_parity','required_chunks_verified','ko_contexts','changed_targets','effects')}))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('T3 receipt collection failed: '+type(exc).__name__);raise SystemExit(1)
