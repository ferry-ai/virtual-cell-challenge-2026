"""Bounded verified private transport, with diagnostics that never include URLs."""
import hashlib
import json
import time
import urllib.error
import urllib.request


def diagnostic(exc, attempt):
    reason = getattr(exc, 'reason', None)
    errno = getattr(reason, 'errno', None)
    code = getattr(exc, 'code', None)
    verify = getattr(reason, 'verify_code', None)
    return dict(stage='private_transport', attempt=attempt,
        exception_type=type(exc).__name__, reason_type=type(reason).__name__ if reason is not None else None,
        errno=errno if isinstance(errno, int) else None,
        http_status=code if isinstance(code, int) else None,
        tls_verify_code=verify if isinstance(verify, int) else None)


def retryable(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in (408, 429, 500, 502, 503, 504)
    return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError))


def download_verified(url, path, expected_bytes, expected_sha256, attempts=3):
    if attempts not in (1, 2, 3):
        raise ValueError('at most three transport attempts')
    partial = path.with_suffix('.partial')
    if path.exists() or partial.exists():
        raise FileExistsError('download destination or partial already exists')
    for attempt in range(1, attempts + 1):
        created = False
        count = 0
        digest = hashlib.sha256()
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                with partial.open('xb') as stream:
                    created = True
                    while True:
                        block = response.read(1 << 20)
                        if not block:
                            break
                        stream.write(block)
                        digest.update(block)
                        count += len(block)
            if count != expected_bytes or digest.hexdigest() != expected_sha256:
                raise ValueError('downloaded chunk identity differs')
            partial.rename(path)
            return count
        except Exception as exc:
            # Only a partial created by this exact invocation may be removed.
            if created and partial.exists():
                partial.unlink()
            print(json.dumps(diagnostic(exc, attempt)), flush=True)
            if not retryable(exc) or attempt == attempts:
                raise ValueError('private transport failed after bounded attempts') from None
            time.sleep(2 ** attempt)
