"""Exact ranged private recovery; preserve diagnostics, never log bearer URLs."""
import hashlib
import json
import time
import requests


def download_verified(url,path,expected_bytes,expected_sha256,attempts=3):
    partial=path.with_suffix('.partial')
    if path.exists() or partial.exists():raise FileExistsError('fresh destination required')
    digest=hashlib.sha256();offset=0;last=0;range_size=64<<20
    with partial.open('xb') as stream:
        while offset<expected_bytes:
            end=min(expected_bytes-1,offset+range_size-1)
            for attempt in range(1,attempts+1):
                try:
                    # Buffer at most 64 MiB so a failed range never contaminates
                    # the committed prefix or its incremental hash.
                    with requests.get(url,headers={'Range':f'bytes={offset}-{end}'},stream=True,timeout=(15,90)) as r:
                        if r.status_code!=206 or r.headers.get('Content-Range')!=f'bytes {offset}-{end}/{expected_bytes}':
                            print(json.dumps(dict(stage='range_header_mismatch',status=r.status_code,
                                expected_total=expected_bytes,content_length=r.headers.get('Content-Length'))),flush=True)
                            raise ValueError('provider range identity differs')
                        body=bytearray()
                        for block in r.iter_content(1<<20):
                            body.extend(block)
                            if len(body)>end-offset+1:raise ValueError('oversized range')
                        if len(body)!=end-offset+1:raise IOError('short range')
                    stream.write(body);digest.update(body);offset=end+1
                    break
                except (requests.RequestException,IOError) as exc:
                    print(json.dumps(dict(stage='range_retry',offset=offset,attempt=attempt,error_type=type(exc).__name__)),flush=True)
                    if attempt==attempts:raise ValueError('range transport failed') from None
                    time.sleep(2**attempt)
            if time.monotonic()-last>=20 or offset==expected_bytes:
                stream.flush();print(json.dumps(dict(stage='recovery_download',bytes_verified_transport=offset,
                    total_bytes=expected_bytes)),flush=True);last=time.monotonic()
    actual=digest.hexdigest()
    print(json.dumps(dict(stage='recovery_full_hash',bytes=offset,actual_sha256=actual,
        expected_sha256=expected_sha256,matches=actual==expected_sha256)),flush=True)
    if offset!=expected_bytes or actual!=expected_sha256:
        raise ValueError('recovered file full hash differs; not admitted')
    partial.rename(path)
    return offset
