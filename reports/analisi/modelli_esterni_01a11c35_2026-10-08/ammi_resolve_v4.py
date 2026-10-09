"""Hash-addressed runtime inputs and one-at-a-time response chunk staging.

Private locators must be supplied in a separately authorized private package.
No URL or provider response body is logged. Mounted files are never deleted.
"""
import hashlib
import json
from pathlib import Path
import shutil
import requests
from ammi_inputs_v3 import checked

class Resolver:
    def __init__(self,roots,scratch,locators=None):
        self.roots=[Path(x) for x in roots];self.scratch=Path(scratch)
        self.scratch.mkdir(parents=True,exist_ok=False)
        self.locators=locators or {};self.by_size={};self.verified={};self.downloaded=set()
        for root in self.roots:
            for path in root.rglob('*'):
                if path.is_file():self.by_size.setdefault(path.stat().st_size,[]).append(path)

    def resolve(self,pin):
        digest=pin['sha256']
        if digest in self.verified:return self.verified[digest]
        for path in self.by_size.get(pin['bytes'],[]):
            try:checked(dict(pin,path=str(path)))
            except ValueError:continue
            self.verified[digest]=path;return path
        item=self.locators.get(digest)
        if not item or item['bytes']!=pin['bytes'] or item['sha256']!=digest:
            raise ValueError('pinned input unavailable: '+digest)
        if not item['url'].startswith('https://'):raise ValueError('HTTPS locator required')
        if shutil.disk_usage(self.scratch).free < pin['bytes']+(1<<30):
            raise RuntimeError('insufficient disk for next pinned input')
        path=self.scratch/digest;partial=path.with_suffix('.partial')
        try:
            with requests.get(item['url'],stream=True,timeout=(15,60)) as response:
                if response.status_code!=200:raise RuntimeError('input HTTP '+str(response.status_code))
                count=0;h=hashlib.sha256()
                with partial.open('xb') as stream:
                    for block in response.iter_content(1<<20):
                        count+=len(block)
                        if count>pin['bytes']:raise ValueError('input exceeds pinned size')
                        stream.write(block);h.update(block)
            if count!=pin['bytes'] or h.hexdigest()!=digest:raise ValueError('download pin differs')
        except requests.RequestException:
            raise RuntimeError('input transport failed; locator suppressed') from None
        partial.rename(path);self.downloaded.add(digest);self.verified[digest]=path
        return path

    def release(self,digest):
        # Only our disposable download cache; provider originals remain intact.
        if digest not in self.downloaded:return
        path=self.verified[digest]
        if path.parent.resolve()!=self.scratch.resolve() or path.name!=digest:
            raise ValueError('cache ownership differs')
        path.unlink();self.downloaded.remove(digest);self.verified.pop(digest)

    def pin(self,pin):return dict(pin,path=str(self.resolve(pin)))

    def stage_ntc(self,parts,out):
        out=Path(out);out.mkdir(parents=True,exist_ok=False);result=[]
        for i,spec in enumerate(parts):
            completion=self.pin(spec['completion']);receipt=json.loads(Path(completion['path']).read_text())
            dest=out/('part_%03d'%i);dest.mkdir()
            pins=dict(receipt['files'],**{'complete.json':spec['completion']})
            for name,pin in pins.items():
                if Path(name).name!=name:raise ValueError('non-flat NTC payload')
                (dest/name).symlink_to(self.resolve(pin))
            item=dict(spec,completion=dict(spec['completion'],path=str(dest/'complete.json')))
            if item.get('relocation_requires_receipt'):item['relocation_receipt']=self.pin(item['relocation_receipt'])
            result.append(item)
        return result

class ResponseLocations:
    """Resolve only the next explicitly permitted training response chunk."""
    def __init__(self,resolver,pins):self.resolver=resolver;self.pins=pins
    def __getitem__(self,digest):return str(self.resolver.resolve(self.pins[digest]))
    def release(self,digest):self.resolver.release(digest)
