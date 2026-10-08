"""Private remote-only diagnostic: hash the first authorized private chunk, never print its URL."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

BUNDLE_SHA='5baf896a6552351fd9121317fa825c35461c15dbf0eadd9a07703529cb5bdfae'
VIEW_SHA='63624e9405cbf9b02f1072ccd63beddc5d5fbddbe3eac8499e2b5e815f231793'


def main():
    result=dict(scope='first private input only; no model fit',url_printed=False)
    try:
        matches=[p for p in Path('/kaggle/input').rglob('bundle.bin') if hashlib.sha256(p.read_bytes()).hexdigest()==BUNDLE_SHA]
        if len(matches)!=1:raise ValueError('bundle identity')
        with zipfile.ZipFile(matches[0]) as z:
            raw=z.read('view.json')
            if hashlib.sha256(raw).hexdigest()!=VIEW_SHA:raise ValueError('view identity')
            view=json.loads(raw);loc=json.loads(z.read('private_locators.json'))['files']
        chunk=next(c for c in view['chunks'] if c['producer']+'/'+c['producer_file'] in loc)
        item=loc[chunk['producer']+'/'+chunk['producer_file']]
        result.update(producer=chunk['producer'],file=chunk['producer_file'],expected_bytes=chunk['bytes'],expected_sha256=chunk['sha256'])
        count=0;digest=hashlib.sha256()
        with urllib.request.urlopen(item['url'],timeout=120) as response:
            result.update(http_status=response.status,content_type=response.headers.get('Content-Type'))
            for block in iter(lambda:response.read(1<<20),b''):
                count+=len(block);digest.update(block)
        result.update(actual_bytes=count,actual_sha256=digest.hexdigest(),
                      status='PASS' if count==chunk['bytes'] and digest.hexdigest()==chunk['sha256'] else 'CONTENT_MISMATCH')
    except Exception as exc:
        result.update(status='FAIL',exception_type=type(exc).__name__,http_status=getattr(exc,'code',None))
    Path('/kaggle/working/diagnostic.json').write_text(json.dumps(result,indent=1))
    print(json.dumps(result))


if __name__=='__main__':main()
