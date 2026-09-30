"""Query committed bytes with the installed CLI's resumable-upload status probe."""
import json
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from vcc import auth, config, upload

entry = 'ZvrYZ4UazadAyuq4AsDB'
expected = Path('C:/Users/ferra/vcc2026-data/artifacts/t28_local_upload_r1/prediction.vcc')
item = auth.get_pending_upload(config.resolve_profile(), entry)
if item is None:
    print(json.dumps({'entry_id': entry, 'pending_record_present': False}))
else:
    if Path(item['local_path']).resolve() != expected.resolve():
        raise ValueError('Pending file differs')
    parsed = urlsplit(item['upload_url'])
    if parsed.scheme != 'https' or not (parsed.hostname == 'storage.googleapis.com' or parsed.hostname.endswith('.storage.googleapis.com')):
        raise ValueError('Unexpected upload host')
    try:
        with httpx.Client() as client:
            committed = upload._committed_offset(item['upload_url'], expected.stat().st_size, client)
        print(json.dumps({'entry_id': entry, 'committed_bytes': committed, 'total_bytes': expected.stat().st_size}))
    except Exception as exc:
        print(json.dumps({'entry_id': entry, 'probe_error_type': type(exc).__name__}))
