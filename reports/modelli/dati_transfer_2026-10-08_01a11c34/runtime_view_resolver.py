"""Resolve every frozen chunk by content, with private authenticated cache if needed.

No model fitting and no learned transformation. Locators stay outside receipts.
The downstream chunk consumer must also check axes, masks and biological identity.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.request


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()


def write_new(path, doc):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(doc,f,indent=1,allow_nan=False)


def resolve(view_path, view_sha256, roots, cache, out, private_locators=None):
    start=time.monotonic();view_path=Path(view_path);cache=Path(cache);out=Path(out)
    if out.exists() or out.with_suffix('.receipt.json').exists(): raise ValueError('immutable output exists')
    if sha(view_path)!=view_sha256: raise ValueError('frozen view identity differs')
    spec=json.loads(view_path.read_text(encoding='utf-8'))
    locators=json.loads(Path(private_locators).read_text(encoding='utf-8'))['files'] if private_locators else {}
    index=defaultdict(list)
    for root in roots:
        for path in Path(root).rglob('*.npz'):
            if path.is_file():index[(path.name,path.stat().st_size)].append(path)
    cache.mkdir(parents=True,exist_ok=True);seen={};resolved=[];downloaded=0;access=[]
    for item in spec['chunks']:
        key=item['producer']+'/'+item['producer_file'];digest=item['sha256'];size=item['bytes']
        path=None
        for candidate in index[(Path(item['producer_file']).name,size)]:
            actual=seen.setdefault(str(candidate),None)
            if actual is None:actual=seen[str(candidate)]=sha(candidate)
            if actual==digest:path=candidate;break
        route='native_mount'
        if path is None:
            route='authenticated_output_download';path=cache/(digest+'.npz')
            if path.exists():
                if path.stat().st_size!=size or sha(path)!=digest: raise ValueError('cached chunk identity differs')
            else:
                locator=locators.get(key)
                if not locator or locator['sha256']!=digest or locator['bytes']!=size:
                    raise ValueError('required chunk unavailable: '+key)
                if shutil.disk_usage(cache).free<size+1024**3: raise ValueError('insufficient download-cache disk margin')
                temp=path.with_suffix('.partial')
                if temp.exists(): raise ValueError('partial download requires explicit recovery')
                h=hashlib.sha256();count=0
                try:
                    with urllib.request.urlopen(locator['url'],timeout=120) as response,temp.open('xb') as target:
                        while True:
                            block=response.read(1<<20)
                            if not block:break
                            target.write(block);h.update(block);count+=len(block)
                except Exception as exc:
                    raise ValueError('authenticated download failed for '+key+' ('+type(exc).__name__+')') from None
                if count!=size or h.hexdigest()!=digest:raise ValueError('downloaded chunk identity differs: '+key)
                temp.rename(path);downloaded+=count
        item['path']=str(path.resolve());resolved.append(item)
        access.append(dict(producer=item['producer'],file=item['producer_file'],bytes=size,sha256=digest,route=route))
        if len(resolved)%100==0: print(json.dumps(dict(resolved_chunks=len(resolved),expected_chunks=len(spec['chunks']))),flush=True)
    spec['chunks']=resolved
    spec['runtime_resolution']=dict(source_view_sha256=view_sha256,chunk_hashes_verified=True,source_visibility_changed=False)
    write_new(out,spec)
    receipt=dict(utc=datetime.now(timezone.utc).isoformat(),source_view_sha256=view_sha256,
        resolved_view_sha256=sha(out),regime=spec['regime'],chunks=len(resolved),
        bytes_verified=sum(x['bytes'] for x in access),downloaded_bytes=downloaded,
        contexts=len(spec['expected_rows_by_context']),rows=sum(spec['expected_rows_by_context'].values()),
        seconds=time.monotonic()-start,inputs=access,learned_transformations=False,
        axes_and_masks_verification='required in downstream chunk consumer',model_fit=False)
    write_new(out.with_suffix('.receipt.json'),receipt)
    print(json.dumps({k:receipt[k] for k in ('regime','chunks','rows','contexts','bytes_verified','downloaded_bytes','seconds')}))
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--view',required=True);p.add_argument('--view-sha256',required=True)
    p.add_argument('--roots',nargs='+',required=True);p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    p.add_argument('--private-locators');a=p.parse_args()
    resolve(a.view,a.view_sha256,a.roots,a.cache,a.out,a.private_locators)
