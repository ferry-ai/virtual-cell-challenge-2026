"""Check same-account preservation receipt against independent old producer pins."""
from percorso import HERE,read,pin,write_new,now
import argparse
from pathlib import Path
p=argparse.ArgumentParser(__doc__)
p.add_argument('--source-report',type=Path,default=HERE/'ntc_mx_partial_verified_r1.json')
p.add_argument('--destination-report',type=Path,default=HERE/'ntc_mx_r6a_verified_r1.json')
p.add_argument('--metadata',type=Path,default=HERE/'neural_launches/terminal_metadata/davidmaisterx/dt-ntc-inputs-01a11c34-r6a_r10')
p.add_argument('--out',type=Path,default=HERE/'ntc_mx_restored_verified_r1.json');a=p.parse_args()
old=read(a.source_report);new=read(a.destination_report);root=a.metadata
receipt=read(root/'restored_complete.json');expected={}
for part,record in old['parts'].items():
    for name,spec in record['files'].items():expected['ntc/'+part+'/'+name]={k:spec[k] for k in ('bytes','sha256')}
    spec=record['completion'];expected['ntc/'+part+'/complete.json']={k:spec[k] for k in ('bytes','sha256')}
    if pin(root/'ntc'/part/'complete.json')['sha256']!=spec['sha256']:raise ValueError('copied producer receipt changed')
actual={x['file']:{k:x[k] for k in ('bytes','sha256')} for x in receipt['files']}
if actual!=expected or len(receipt['files'])!=len(expected):raise ValueError('preserved file set differs')
if receipt['status']!='COMPLETE' or receipt['source_job']!=old['slug'] or not receipt['same_account'] or not receipt['numeric_files_rehashed']:
    raise ValueError('invalid restoration status')
schema=read(root/'schema_preflight.json')
write_new(a.out,dict(utc=now(),status='PASS',source=pin(a.source_report),
    destination=pin(a.destination_report),receipt=pin(root/'restored_complete.json'),
    files=actual,parts=list(old['parts']),schema_preflight=schema,
    full_file_hashes_rechecked_in_destination=True,NTC_recomputed=False,raw_RNA_downloaded=False,
    independently_rehashed_local_arrays=False))
print(f'PASS: {len(old["parts"])} preserved parts, {len(actual)} file pins, {sum(x["bytes"] for x in actual.values())} bytes')
