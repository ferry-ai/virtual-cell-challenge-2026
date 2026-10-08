"""Observe T3 status and sanitized logs; never retrieve biological arrays."""
import argparse
import hashlib
import json
import re
from percorso import DATA,HERE,read,pin,write_new,now
from quick_generation_cloud import api_for_owner


def main(label,relative_folder):
    folder=HERE/relative_folder;proof=read(folder/'prepared.json');slug=proof['slug']
    api=api_for_owner(proof['owner'])
    status=api.kernels_status(slug)
    raw=api.kernels_logs(slug)
    private=DATA/'processed/dati_transfer_2026-10-08_01a11c34'/relative_folder/'observations'/label
    private.mkdir(parents=True,exist_ok=False)
    (private/'provider.log').write_text(raw,encoding='utf-8')
    lines=[]
    try:
        entries=json.loads(raw)
        for e in entries:lines.extend(str(e.get('data','')).splitlines())
    except (ValueError,TypeError):lines=raw.splitlines()
    safe=[]
    for line in lines:
        line=re.sub(r'https?://\S+','[URL REDACTED]',line)
        line=re.sub(r'[A-Za-z0-9+/=]{100,}','[ENCODED DATA OMITTED]',line)
        if len(line)>1000:line='[LONG LINE OMITTED]'
        safe.append(line)
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest
    req=ApiGetKernelRequest();req.user_name,req.kernel_slug=slug.split('/')
    with api.build_kaggle_client() as client:saved=client.kernels.kernels_api_client.get_kernel(req)
    source_sha=hashlib.sha256(saved.blob.source.replace('\r\n','\n').encode()).hexdigest()
    report=dict(utc=now(),job=slug,status=str(status.status),version=saved.metadata.current_version_number,
        private=saved.metadata.is_private,enable_internet=saved.metadata.enable_internet,
        source_sha256=source_sha,saved_code_matches=source_sha==proof['code']['sha256'],
        raw_log=pin(private/'provider.log'),sanitized_tail=safe[-24:],arrays_downloaded=False)
    write_new(folder/('observation_'+label+'.json'),report)
    print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--folder',default='extended_transfer/r1');a=p.parse_args()
    try:main(a.label,a.folder)
    except Exception as exc:
        print('T3 observation failed: '+type(exc).__name__);raise SystemExit(1)
