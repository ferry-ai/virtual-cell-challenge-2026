"""Recover pinned completed parts inside the same private cloud account."""
import hashlib
import json
from pathlib import Path
import shutil
import requests


def restore(work=Path('/kaggle/working')):
    spec=json.loads((work/'restore_parts.json').read_text())
    total=sum(x['bytes'] for x in spec['files'])
    if shutil.disk_usage(work).free < total+(1<<30):
        raise ValueError('insufficient disk for preserved NTC parts')
    completed=[]
    for item in spec['files']:
        name=Path(item['file'])
        if name.is_absolute() or '..' in name.parts:raise ValueError('unsafe restore path')
        target=work/name;target.parent.mkdir(parents=True,exist_ok=True)
        digest=hashlib.sha256();size=0
        try:
            with requests.get(item['url'],stream=True,timeout=(20,90)) as response:
                response.raise_for_status()
                with target.with_suffix(target.suffix+'.partial').open('xb') as out:
                    for block in response.iter_content(1<<20):
                        if block:out.write(block);digest.update(block);size+=len(block)
        except Exception:
            raise RuntimeError('private NTC restoration failed: '+str(name)) from None
        if size!=item['bytes'] or digest.hexdigest()!=item['sha256']:
            raise ValueError('restored NTC pin differs: '+str(name))
        target.with_suffix(target.suffix+'.partial').rename(target)
        completed.append({k:v for k,v in item.items() if k!='url'})
    (work/'restored_complete.json').write_text(json.dumps(dict(status='COMPLETE',
        source_job=spec['source_job'],same_account=True,files=completed,
        numeric_files_rehashed=True,RNA_recomputed=False),indent=2))
    (work/'restore_parts.json').unlink()


if __name__=='__main__':restore()
