"""Read only the entry identity for the local t28 upload; omit credentials and URLs."""
import json
from pathlib import Path
from vcc import auth, config

expected = Path('C:/Users/ferra/vcc2026-data/artifacts/t28_local_upload_r1/prediction.vcc')
pending = auth.list_pending_uploads(config.resolve_profile())
print(json.dumps([
    {'entry_id': entry, 'local_file': expected.name}
    for entry, item in pending.items()
    if Path(item.get('local_path', '')).resolve() == expected.resolve()
]))
