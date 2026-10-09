"""Move bulky immutable contract outside Git, retaining digest and small index."""
from percorso import HERE,DATA,read,pin,write_new,now
source=HERE/'official_ntc_contract_r1.json';before=pin(source);doc=read(source)
target=DATA/'processed/dati_transfer_2026-10-08_01a11c34/official_ntc_r1/official_ntc_contract_r1.json'
target.parent.mkdir(parents=True,exist_ok=True)
if target.exists():raise FileExistsError(target)
source.rename(target)
after=pin(target)
if before['sha256']!=after['sha256']:raise ValueError('relocation changed bytes')
write_new(HERE/'official_ntc_contract_manifest_r1.json',dict(utc=now(),contract=after,
    original_location=before['path'],relocated_without_content_change=True,
    ntc_expected_parts=doc['ntc_expected_parts'],axis=doc['axis'],
    plans=[{k:v for k,v in p.items() if k!='genes'} for p in doc['plans']],
    historical_prepared_contract_pin='old path in official_ntc_prepared_r1.json; identical bytes at contract.path',
    immutable_cloud_payload='unchanged; official_contract.json remains embedded in the already executed package'))
print('Immutable contract moved outside Git; digest unchanged')
