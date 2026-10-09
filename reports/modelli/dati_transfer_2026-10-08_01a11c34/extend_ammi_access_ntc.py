"""Add exactly the 12 authorized df11 parts, only after their terminal verification."""
import json
from pathlib import Path
from percorso import HERE,DATA,read,pin,sha,write_new,now
from issue_ammi_private_access import AUTH,frozen_plan,authenticate,validate_url


def main():
    plan=frozen_plan();source='davideferrante11/dt-ntc-inputs-01a11c34-r5'
    verified_path=HERE/'ntc_df11_terminal_verified_r1.json'
    ready_path=HERE/'ntc_ready_manifest_r2.json'
    verified=read(verified_path);ready=read(ready_path)
    allowed=plan['pending_NTC_parts']
    if verified['status']!='PASS_METADATA_AND_CODE' or verified['slug']!=source:
        raise ValueError('producer verification missing')
    if set(verified['parts'])!=set(allowed) or ready['pending_parts']:
        raise ValueError('not all 12 authorized parts complete')
    requested={}
    for part,expected in allowed.items():
        record=ready['parts'][part]
        if record['producer_job']!=source or record['job']!=source or record['plan_sha256']!=expected['plan_sha256']:
            raise ValueError('producer or frozen plan differs')
        completion=record['completion'];path=Path(completion['path'])
        if pin(path)!=completion:raise ValueError('completion receipt changed')
        doc=read(path)
        if doc['status']!='COMPLETE' or doc['code']!=record['producer_code']:
            raise ValueError('completion or code mismatch')
        requested['ntc/'+part+'/complete.json']=dict(bytes=completion['bytes'],sha256=completion['sha256'],part_id=part)
        for name,spec in record['files'].items():
            if name not in ('counts.npz','cells.json','axes_depth_mask.npz'):
                raise ValueError('unexpected NTC file')
            if any(spec[k]!=doc['files'][name][k] for k in ('bytes','sha256')):
                raise ValueError('numeric file pin differs from producer receipt')
            requested['ntc/'+part+'/'+name]=dict(bytes=spec['bytes'],sha256=spec['sha256'],part_id=part)
    if len(requested)!=48:raise ValueError('authorized NTC file count differs')
    previous=read(HERE/'ammi_private_access_issued_r1.json')
    if pin(previous['private_locators']['path'])!=previous['private_locators']:
        raise ValueError('prior locator manifest changed')
    base=read(previous['private_locators']['path'])
    if base['authorization']!=pin(AUTH):raise ValueError('prior authorization changed')
    api=authenticate('davideferrante11')
    from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest,ApiGetKernelRequest
    if str(api.kernels_status(source).status).split('.')[-1]!='COMPLETE':
        raise ValueError('producer not COMPLETE')
    request=ApiGetKernelRequest();request.user_name,request.kernel_slug=source.split('/')
    with api.build_kaggle_client() as client:saved=client.kernels.kernels_api_client.get_kernel(request)
    import hashlib
    digest=hashlib.sha256(saved.blob.source.replace('\r\n','\n').encode()).hexdigest()
    if digest!=verified['remote_identity']['source_sha256'] or saved.metadata.current_version_number!=verified['remote_identity']['version']:
        raise ValueError('remote producer changed after verification')
    found={};token=None;seen=set()
    while True:
        request=ApiListKernelSessionOutputRequest();request.user_name,request.kernel_slug=source.split('/')
        api._set_paging(request,100,token)
        with api.build_kaggle_client() as client:response=client.kernels.kernels_api_client.list_kernel_session_output(request)
        for item in response.files or []:
            name=item.file_name
            if name.startswith(request.kernel_slug+'/'):name=name[len(request.kernel_slug)+1:]
            if name in requested:
                if name in found:raise ValueError('duplicate NTC output')
                found[name]=dict(requested[name],url=validate_url(item.url))
        token=response.next_page_token
        if not token:break
        if token in seen:raise ValueError('pagination repeated')
        seen.add(token)
    if set(found)!=set(requested):raise ValueError('verified NTC output missing')
    stage=DATA/'processed/dati_transfer_2026-10-08_01a11c34/ammi_private_access_r1/issued_with_ntc_r1'
    stage.mkdir(parents=True,exist_ok=False)
    for name,row in found.items():
        digest=row['sha256'];old=base['files'].get(digest)
        if old and old['bytes']!=row['bytes']:raise ValueError('conflicting hash size')
        base['files'].setdefault(digest,{k:row[k] for k in ('bytes','sha256','url')})
        base['origins'].append(dict(source_kind='kernel',source=source,file=name,bytes=row['bytes'],sha256=digest,
            role='NTC',part_id=row['part_id']))
    base.update(utc=now(),pending_NTC_parts=[],complete_training_inputs=True,
        ready_for_training=False,remaining_gate='consumer full file hashes and runtime preflight',
        NTC_verification=pin(verified_path),NTC_ready_manifest=pin(ready_path))
    locator=stage/'private_locators.json';write_new(locator,base)
    receipt=HERE/'ammi_private_access_with_ntc_r1.json'
    write_new(receipt,dict(utc=now(),status='AUTHORIZED_INPUT_LOCATORS_COMPLETE_CONSUMER_HASHES_PENDING',
        private_locators=pin(locator),mount_plan=previous['mount_plan'],authorization=pin(AUTH),
        ntc_verification=pin(verified_path),ntc_ready_manifest=pin(ready_path),NTC_parts=12,NTC_files=48,
        NTC_bytes=sum(r['bytes'] for r in requested.values()),unique_hashes=len(base['files']),
        body_bytes_read=0,full_numeric_hash_verification_by_consumer_required=True,
        ready_for_training=False,cloud_jobs_launched=0))
    print(json.dumps(dict(receipt=str(receipt),NTC_parts=12,NTC_files=48)))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('NTC locator extension not completed: '+type(exc).__name__)
        raise SystemExit(1)
