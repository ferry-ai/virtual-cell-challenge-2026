"""Split only unfinished parts and preserve verified parts on the same account."""
import json
import argparse
import os
from pathlib import Path
from build_ammi_runtime_contract import payload
from cloud_campaign import CONFIG
from prepare_neural_inputs_cloud import save_job
from percorso import HERE, read, pin, now, write_new


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--source',default='davidmaisterx/dt-ntc-inputs-01a11c34-r4')
    parser.add_argument('--source-prepared',default='neural_inputs_cloud_prepared_r4.json')
    parser.add_argument('--partial',default='ntc_mx_partial_verified_r1.json')
    parser.add_argument('--revision',default='r6');parser.add_argument('--bins',type=int,default=3)
    parser.add_argument('--tests',default='ntc_cells_tests_r6.txt');parser.add_argument('--authorization',default='r3')
    args=parser.parse_args()
    owner='davidmaisterx';source=args.source
    if not source.startswith(owner+'/') or not 1<=args.bins<=3:raise ValueError('same account, one to three jobs only')
    report=read(HERE/args.partial)
    if report['slug']!=source or report['status']!='PASS_METADATA_AND_CODE':
        raise ValueError('verified partial source required')
    old=next(j for j in read(HERE/args.source_prepared)['jobs'] if j['slug']==source)
    members=payload(old);config=json.loads(members['job.json'])
    plans={x['plan']:json.loads(members[x['plan']]) for x in config['parts']}
    pending=[x for x in config['parts'] if plans[x['plan']]['part_id'] in report['missing_parts']]
    if len(pending)!=len(report['missing_parts']) or not pending:raise ValueError('unfinished part set differs')
    for key in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(key,None)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
    api=KaggleApi();api.authenticate()
    if str(api.kernels_status(source).status).split('.')[-1]!='ERROR':raise ValueError('source no longer terminal ERROR')
    files={}
    for part,record in report['parts'].items():
        for name,spec in record['files'].items():
            path='ntc/'+part+'/'+name;files[path]=dict(file=path,bytes=spec['bytes'],sha256=spec['sha256'])
        path='ntc/'+part+'/complete.json';p=record['completion']
        files[path]=dict(file=path,bytes=p['bytes'],sha256=p['sha256'])
    token=None;seen=set()
    while True:
        request=ApiListKernelSessionOutputRequest();request.user_name=owner
        request.kernel_slug=source.split('/')[1];request.page_size=200
        if token:request.page_token=token
        with api.build_kaggle_client() as client:response=client.kernels.kernels_api_client.list_kernel_session_output(request)
        for item in response.files or []:
            name=item.file_name.removeprefix(request.kernel_slug+'/')
            if name in files:files[name]['url']=item.url
        token=response.next_page_token
        if not token:break
        if token in seen:raise ValueError('repeated output page')
        seen.add(token)
    if any('url' not in x for x in files.values()):raise ValueError('preserved output inaccessible')
    bins=[[] for _ in range(args.bins)];sizes=[0]*args.bins
    def size(item):return sum(s.get('bytes') or s['cells']*10000 for s in plans[item['plan']]['sources'])
    for item in sorted(pending,key=size,reverse=True):
        index=min(range(args.bins),key=lambda i:sizes[i]);bins[index].append(item);sizes[index]+=size(item)
    jobs=[]
    for index,items in enumerate(bins):
        revision=args.revision+chr(97+index);slug=owner+'/dt-ntc-inputs-01a11c34-'+revision
        selected={name:(HERE/name).read_bytes() for name in ('ntc_cells.py','ntc_campaign_worker.py','run_ntc_extraction.py')}
        selected['plans/genes.json']=members['plans/genes.json'];mounts=[]
        for item in items:
            selected[item['plan']]=members[item['plan']];selected[item['rows']]=members[item['rows']]
            mounts.extend(plans[item['plan']]['mount_hints'])
        selected['job.json']=json.dumps(dict(parts=items)).encode()
        entry='ntc_campaign_worker.py'
        if index==0:
            selected['restore_ntc_parts.py']=(HERE/'restore_ntc_parts.py').read_bytes()
            selected['restore_parts.json']=json.dumps(dict(source_job=source,files=list(files.values()))).encode()
            selected['entry.py']=b'from restore_ntc_parts import restore\nrestore()\nimport runpy\nrunpy.run_path("ntc_campaign_worker.py",run_name="__main__")\n'
            entry='entry.py'
        job=save_job(slug,selected,entry,mounts,args.revision)
        if index==0:
            meta=read(job['metadata']['path']);meta['enable_internet']=True
            Path(job['metadata']['path']).write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
            job['metadata']=pin(job['metadata']['path'])
        job.update(parts=len(items),part_ids=[plans[x['plan']]['part_id'] for x in items],
            estimated_source_bytes=sizes[index],preserved_parts=list(report['parts']) if index==0 else [])
        jobs.append(job)
    prepared=HERE/('neural_inputs_cloud_prepared_'+args.revision+'.json')
    write_new(prepared,dict(utc=now(),jobs=jobs,recovery_of=source,
        partial_verified=pin(HERE/args.partial),
        tests=pin(HERE/args.tests),unchanged_science='exact frozen plans and bank admission, 64/stratum, normalization and merge',
        only_reader_fix_and_schema_preflight=True,completed_parts_recomputed=0,
        signed_urls='private same-account bootstrap only, outside repository and logs',
        preserved_bytes=sum(x['bytes'] for x in files.values())))
    auth=read(HERE/'neural_inputs_launch_authorization_r2.json')
    auth.update(recorded_utc=now(),jobs=[j['slug'] for j in jobs],prepared=pin(prepared),
        request_text='Lead: correct reader, retain completed parts and relaunch only necessary private CPU work; do not interrupt df11',
        scope_note=f'{len(pending)} unfinished existing units in {args.bins} native-account jobs; {len(report["parts"])} completed units copied and rehashed within same account, not recomputed')
    write_new(HERE/('neural_inputs_launch_authorization_'+args.authorization+'.json'),auth)
    print(json.dumps(dict(jobs=[dict(slug=j['slug'],parts=j['parts']) for j in jobs],preserved_bytes=sum(x['bytes'] for x in files.values()))))


if __name__=='__main__':main()
