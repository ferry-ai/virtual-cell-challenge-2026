"""Check authorized locator response headers, without reading response bodies."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, parse_qs
import requests
from percorso import read, pin, write_new, now


def verify(item):
    digest, record = item
    result = dict(sha256=digest,expected_bytes=record['bytes'],body_bytes_read=0)
    try:
        # Signed links may bind GET; a streaming GET validates that method. No
        # content/iter_content/raw.read access occurs; close cancels the body.
        with requests.get(record['url'],stream=True,timeout=(15,45)) as response:
            length = response.headers.get('Content-Length')
            result.update(http_status=response.status_code,
                          observed_bytes=int(length) if length is not None else None,
                          content_type=response.headers.get('Content-Type'))
            result['status'] = ('PASS_HEADERS' if response.status_code==200 and
                                length is not None and int(length)==record['bytes'] else 'FAIL_HEADERS')
        query = {k.lower():v[0] for k,v in parse_qs(urlsplit(record['url']).query).items()}
        expiry = None
        if 'expires' in query and query['expires'].isdigit():
            expiry = datetime.fromtimestamp(int(query['expires']),timezone.utc)
        elif 'x-goog-date' in query and 'x-goog-expires' in query:
            expiry = datetime.strptime(query['x-goog-date'],'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
            expiry += timedelta(seconds=int(query['x-goog-expires']))
        result['expires_utc_if_encoded'] = expiry.isoformat() if expiry else None
    except Exception as exc:
        result.update(status='FAIL_HEADERS',error_type=type(exc).__name__)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('locators');p.add_argument('out');a=p.parse_args()
    doc=read(a.locators)
    if doc['status']!='authorized' or not doc['authorization']: raise ValueError('authorization required')
    with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(verify,sorted(doc['files'].items())))
    passed=sum(r['status']=='PASS_HEADERS' for r in results)
    expiry=[r['expires_utc_if_encoded'] for r in results if r.get('expires_utc_if_encoded')]
    write_new(a.out,dict(utc=now(),status='PASS_HEADERS' if passed==len(results) else 'FAIL_HEADERS',
        locator_manifest=pin(a.locators),files=len(results),passed=passed,body_bytes_read=0,
        earliest_expiry_utc_if_encoded=min(expiry) if expiry else None,
        full_content_sha256_verified=False,results=results))
    print(__import__('json').dumps(dict(files=len(results),passed=passed,body_bytes_read=0,
        earliest_expiry_utc_if_encoded=min(expiry) if expiry else None)))
    raise SystemExit(0 if passed==len(results) else 1)
