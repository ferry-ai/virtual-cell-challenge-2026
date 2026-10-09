"""Expose native mounts and explicitly authorized cloud-staged exports to a frozen bank.

No symlink recursion assumptions, permission changes, scorer edits or local
biological downloads. Calling this module alone does nothing.
"""
import hashlib
from pathlib import Path
from urllib.parse import urlparse


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''):result.update(block)
    return result.hexdigest()


class CombinedInputs:
    """The exact rglob interface used by the pinned original logo driver."""
    def __init__(self,native,staged):
        self.roots=(Path(native).resolve(),Path(staged).resolve())
        if self.roots[0]==self.roots[1] or not all(p.is_dir() for p in self.roots):
            raise ValueError('two existing distinct input roots required')

    def rglob(self,pattern):
        for root in self.roots:
            yield from root.rglob(pattern)


def bind(driver,driver_path,expected_sha,native,staged):
    if digest(driver_path)!=expected_sha:
        raise ValueError('frozen driver hash differs')
    driver.INPUTS=CombinedInputs(native,staged)
    return driver.INPUTS


def payload_set(files):
    pins={}
    for item in files:
        key=item['sha256'];size=item['bytes']
        if (not isinstance(key,str) or len(key)!=64 or any(c not in '0123456789abcdef' for c in key)
                or not isinstance(size,int) or isinstance(size,bool) or size<=0):
            raise ValueError('invalid payload pin')
        if key in pins and pins[key]!=size:raise ValueError('conflicting payload size')
        pins[key]=size
    if not pins:raise ValueError('no payloads')
    return pins


def transport_gate(plan_sha,files,authorization,locators):
    pins=payload_set(files)
    if (authorization.get('status')!='authorized' or authorization.get('plan_sha256')!=plan_sha
            or payload_set(authorization.get('payloads',[]))!=pins
            or set(locators)!=set(pins)):
        raise ValueError('exact private export authorization required')
    for key,value in locators.items():
        uri=urlparse(value['url'])
        if value['bytes']!=pins[key] or uri.scheme!='https' or not uri.hostname or uri.username or uri.password:
            raise ValueError('invalid private locator')
    return pins


def fetch_blocks(url):
    import requests
    try:
        with requests.get(url,stream=True,timeout=(15,90)) as response:
            response.raise_for_status()
            yield from response.iter_content(1<<20)
    except requests.RequestException:
        # Never expose signed URLs through exceptions or logs.
        raise RuntimeError('private export transport failed') from None


def stage_exports(plan_sha,files,authorization,locators,out,fetch=fetch_blocks):
    pins=transport_gate(plan_sha,files,authorization,locators)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    receipt=[]
    for key,size in sorted(pins.items()):
        path=out/(key+'.npz');actual=0;h=hashlib.sha256()
        with path.open('xb') as stream:
            for block in fetch(locators[key]['url']):
                actual+=len(block)
                if actual>size:raise ValueError('private export size exceeds pin')
                stream.write(block);h.update(block)
        if actual!=size or h.hexdigest()!=key:
            raise ValueError('private export content differs')
        receipt.append(dict(path=str(path),bytes=size,sha256=key,verified=True))
    return receipt
