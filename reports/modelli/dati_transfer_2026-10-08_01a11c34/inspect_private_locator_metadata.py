"""Inspect frozen locator metadata without network access or revealing URLs."""
from collections import Counter
from urllib.parse import urlsplit, parse_qs
from percorso import DATA, HERE, read, pin, sha, now, write_new


def main():
    path = DATA/'processed/dati_transfer_2026-10-08_01a11c34/runtime_access/J-iPSC_davideferante_r3/runtime_inputs.json'
    runtime = read(path)
    loc_path = runtime['private_locators']['path']
    if sha(loc_path) != runtime['private_locators']['sha256']:
        raise ValueError('locator file identity changed')
    doc = read(loc_path)
    view = read(runtime['view']['path'])
    expected = {c['producer']+'/'+c['producer_file']:c for c in view['chunks']}
    errors=[]; hosts=Counter(); schema=Counter(); expiry_keys=Counter(); query_keys=Counter()
    for key,item in doc['files'].items():
        schema[tuple(sorted(item))]+=1
        if key not in expected or any(item.get(k)!=expected[key][k] for k in ('sha256','bytes')):
            errors.append('pin:'+key)
        url=urlsplit(item.get('url',''))
        hosts[url.hostname]+=1
        if url.scheme!='https' or url.username or url.password or not url.hostname:
            errors.append('url_schema:'+key)
        query=parse_qs(url.query)
        query_keys.update(query.keys())
        expiry_keys.update(k for k in query if any(x in k.lower() for x in ('expir','date')))
    required={k for k,c in expected.items() if runtime['sources'][c['producer']]['route']=='authenticated_output_download'}
    first=view['chunks'][0]; key=first['producer']+'/'+first['producer_file']
    report=dict(utc=now(),runtime_inputs=pin(path),local_metadata_only=True,network_requests=0,
        local_rna_downloaded_bytes=0,locator_chunks=len(doc['files']),required_private_chunks=len(required),
        exact_private_inventory=set(doc['files'])==required,bytes=sum(v['bytes'] for v in doc['files'].values()),
        hosts=dict(hosts),entry_schemas=[dict(fields=list(k),count=v) for k,v in schema.items()],
        query_parameter_names=dict(query_keys),exposed_expiry_fields=dict(expiry_keys),
        first_chunk=dict(producer=first['producer'],file=first['producer_file'],bytes=first['bytes'],
                         has_locator=key in doc['files']),errors=errors,
        access_verified=False,expiry_verified=False)
    write_new(HERE/'private_locator_metadata_J_r1.json',report)
    print(__import__('json').dumps(report))


if __name__=='__main__': main()
