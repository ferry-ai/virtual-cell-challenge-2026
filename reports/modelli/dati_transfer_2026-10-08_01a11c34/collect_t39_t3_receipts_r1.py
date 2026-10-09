"""Collect only small completed T39 evidence, never download the prediction matrix."""
import hashlib
import json
import requests
from percorso import HERE,read,write_new,pin,now
from prepare_t39_t3_runtime_r2 import FOLDER,TRIAL
from quick_generation_cloud import api_for_owner


def main():
    proof=read(FOLDER/'prepared.json');api=api_for_owner('davideferrante11')
    status=str(api.kernels_status(proof['slug']).status).split('.')[-1]
    if status!='COMPLETE':print(json.dumps(dict(status=status)));return 2
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest,ApiListKernelSessionOutputRequest
    req=ApiGetKernelRequest();req.user_name,req.kernel_slug=proof['slug'].split('/')
    with api.build_kaggle_client() as client:saved=client.kernels.kernels_api_client.get_kernel(req)
    digest=hashlib.sha256(saved.blob.source.replace('\r\n','\n').encode()).hexdigest()
    if digest!=proof['code']['sha256'] or not saved.metadata.is_private or saved.metadata.current_version_number!=1:
        raise ValueError('producer identity differs')
    wanted={'upload_receipt.json','generation_manifest.json','packaging.json',
        'manifest_48_package_prediction.json','compact_diagnostics.json','generation_preflight.json',
        'generation_stage45_manifest.json','resource_preflight.json'}
    found={};token=None;seen=set()
    while True:
        req=ApiListKernelSessionOutputRequest();req.user_name,req.kernel_slug=proof['slug'].split('/')
        api._set_paging(req,100,token)
        with api.build_kaggle_client() as client:response=client.kernels.kernels_api_client.list_kernel_session_output(req)
        for item in response.files or []:
            name=item.file_name
            if name.startswith(req.kernel_slug+'/'):name=name[len(req.kernel_slug)+1:]
            if name in wanted:
                if name in found:raise ValueError('duplicate receipt name')
                found[name]=item.url
        token=response.next_page_token
        if not token:break
        if token in seen:raise ValueError('pagination repeated')
        seen.add(token)
    if set(found)!=wanted:raise ValueError('required receipts unavailable')
    dest=FOLDER/'completion_r1';dest.mkdir(exist_ok=False)
    for name,url in found.items():
        with requests.get(url,stream=True,timeout=60) as response:
            response.raise_for_status();body=bytearray()
            for chunk in response.iter_content(65536):
                body.extend(chunk)
                if len(body)>2_000_000:raise ValueError('oversized metadata')
        if b'kaggleusercontent.com' in body or b'"upload_url"' in body:raise ValueError('sensitive receipt')
        json.loads(body)
        with (dest/name).open('xb') as f:f.write(body)
    generation=read(dest/'generation_manifest.json');upload=read(dest/'upload_receipt.json')
    pre=read(dest/'generation_preflight.json');package=read(dest/'packaging.json');diag=read(dest/'compact_diagnostics.json')
    if any(pre['effects'][c]['sha256']!=proof['candidate']['sha256'] for c in 'ABC'):
        raise ValueError('candidate differs')
    if pre['prediction']!=proof['prediction'] or pre['amplitude_or_cis_reapplied'] or pre['emitter_scale_applied_once']!=1.5:
        raise ValueError('prediction or scale differs')
    shape=diag['shape']
    if (shape['n_cells'],shape['n_perturbations'],shape['cells_per_pert'],shape['contexts'])!=(360000,300,400,['A','B','C']):
        raise ValueError('generation shape differs')
    if diag['is_pilot'] or not diag['context_provenance_ok'] or diag['seed']!=20260912:
        raise ValueError('emission contract differs')
    v=package['verification']
    if (package['exit_code']!=0 or v['official_container_validator']!='passed'
        or not v['payload_vs_input']['matches_input'] or not v['payload_vs_input']['x_arrays_bit_identical']
        or v['archive_sha256']!=generation['sha256'] or v['archive_bytes']!=generation['bytes']
        or upload['sha256']!=generation['sha256'] or upload['bytes_uploaded']!=generation['bytes']
        or upload['entry_id']!=proof['entry_id'] or not upload['md5_verified']
        or upload['md5_local']!=upload['md5_remote']):
        raise ValueError('package or upload receipt differs')
    for name in wanted:
        with (TRIAL/('t39_t3_cloud_'+name)).open('xb') as f:f.write((dest/name).read_bytes())
    result=dict(utc=now(),status='GENERATION_PACKAGE_UPLOAD_RECEIPTS_VERIFIED',
        entry_id=proof['entry_id'],job=proof['slug'],source_sha256=digest,
        candidate=proof['candidate'],product_sha256=generation['sha256'],product_bytes=generation['bytes'],
        receipts={name:pin(dest/name) for name in sorted(wanted)},
        product_downloaded_locally=False,no_new_fit=True,scientific_promotion=False)
    write_new(dest/'verification.json',result)
    print(json.dumps({k:result[k] for k in ('status','entry_id','product_bytes','product_sha256')}));return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print('T39 receipt collection stopped: '+type(exc).__name__);raise SystemExit(1)
