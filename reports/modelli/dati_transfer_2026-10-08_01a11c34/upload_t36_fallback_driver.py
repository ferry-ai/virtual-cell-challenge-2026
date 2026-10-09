"""Upload the unchanged, previously validated t36 archive to one VCC entry."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys
import time
from urllib.parse import urlparse
from private_download_v2 import download_verified

def mark(stage, **fields):
    print(json.dumps(dict(stage=stage, **fields)), flush=True)

def main():
    cfg=json.loads(Path('delivery.json').read_text())
    target=urlparse(cfg['upload_url'])
    if target.scheme!='https' or not (target.hostname=='storage.googleapis.com' or (target.hostname or '').endswith('.storage.googleapis.com')):
        raise ValueError('invalid upload capability')
    if shutil.disk_usage('/kaggle/working').free<cfg['bytes']+2*1024**3:
        raise ValueError('insufficient output disk')
    product=Path('/kaggle/working/prediction_t36_fallback.vcc')
    mark('fetch_validated_t36',bytes=cfg['bytes'])
    download_verified(cfg['source_url'], product, cfg['bytes'], cfg['sha256'])
    mark('package_verified',sha256=cfg['sha256'],bytes=cfg['bytes'],candidate='unchanged_t36')
    sys.path.insert(0,str(Path('vendor').resolve()))
    from vcc.upload import upload_file
    last=0
    def progress(done,total):
        nonlocal last
        if time.monotonic()-last>10 or done==total:
            mark('uploading',bytes_done=done,total_bytes=total);last=time.monotonic()
    result=upload_file(cfg['upload_url'],product,chunk_size=32*1024**2,progress=progress)
    if not result.verified or result.md5_local!=result.md5_remote or result.bytes_sent!=cfg['bytes']:
        raise ValueError('remote upload verification failed')
    receipt=dict(status='UPLOAD_VERIFIED',entry_id=cfg['entry_id'],utc_upload_verified=datetime.now(timezone.utc).isoformat(),
        sha256=cfg['sha256'],bytes_uploaded=result.bytes_sent,md5_verified=True,md5_local=result.md5_local,
        md5_remote=result.md5_remote,nnz=cfg['nnz'],candidate='unchanged_t36',new_fit=False)
    Path('upload_receipt.json').write_text(json.dumps(receipt,indent=2))
    mark('upload_verified',**receipt)

if __name__=='__main__':
    try:main()
    except BaseException as exc:
        mark('delivery_failed',error_type=type(exc).__name__)
        raise SystemExit(1)
