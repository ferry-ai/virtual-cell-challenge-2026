"""Retrieve only previously unread HIPSCI row metadata, with the archived byte pin."""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = HERE.parent
REPO = S.parents[2]
STATE = S/'archive_completion_hipsci_targeted19_r1/state.json'
bank = json.loads(STATE.read_text())['units']['hipsci_targeted_19']['bank']
receipt_path = REPO/bank['receipt']
if hashlib.sha256(receipt_path.read_bytes()).hexdigest() != bank['receipt_sha256']:
    raise ValueError('archived receipt changed')
receipt = json.loads(receipt_path.read_text())
pin = receipt['files']['rows.csv']
out = HERE/'real_rows_r1'
out.mkdir(exist_ok=False)
for key in ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN'):
    os.environ.pop(key, None)
os.environ['KAGGLE_CONFIG_DIR'] = str(Path.home()/'.kaggle-codex')
from kaggle.api.kaggle_api_extended import KaggleApi, ApiListKernelSessionOutputRequest
import requests
import pandas as pd

api = KaggleApi()
api.authenticate()
token = None
found = None
while True:
    req = ApiListKernelSessionOutputRequest()
    req.user_name, req.kernel_slug = bank['kernel'].split('/')
    req.page_size = 100
    if token:
        req.page_token = token
    with api.build_kaggle_client() as client:
        response = client.kernels.kernels_api_client.list_kernel_session_output(req)
    for item in response.files or []:
        if item.file_name == 'bank/hipsci_targeted_19/rows.csv':
            if found is not None:
                raise ValueError('ambiguous row metadata')
            with requests.get(item.url, stream=True, timeout=(20, 60)) as r:
                r.raise_for_status()
                data = bytearray()
                for chunk in r.iter_content(65536):
                    data.extend(chunk)
                    if len(data) > pin['bytes']:
                        raise ValueError('row metadata exceeds pinned size')
            if len(data) != pin['bytes'] or hashlib.sha256(data).hexdigest() != pin['sha256']:
                raise ValueError('row metadata differs from archived producer')
            found = bytes(data)
    token = response.next_page_token
    if not token:
        break
if found is None:
    raise ValueError('row metadata not available')
(out/'rows.csv').write_bytes(found)
rows = pd.read_csv(out/'rows.csv', keep_default_na=False)
BIO = ['study', 'context', 'donor_or_clone', 'condition', 'modality', 'chemistry']
if len(rows) != receipt['rows'] or int(rows.n.sum()) != receipt['cells_used']:
    raise ValueError('row/cell coverage differs')
controls = rows[rows.target == 'NTC']
anchors = set(controls[BIO].itertuples(index=False, name=None))
contexts = []
for key, frame in rows.groupby(BIO, sort=True, dropna=False):
    contexts.append(dict(zip(BIO, key), rows=len(frame), cells=int(frame.n.sum()),
                         control_cells=int(frame.loc[frame.target == 'NTC', 'n'].sum()),
                         targets=int(frame.loc[frame.target != 'NTC', 'target'].nunique())))
summary = dict(scope='metadata only; counts/axis not opened, no fit admission',
               producer=bank['saved_version'], rows=len(rows), cells=int(rows.n.sum()),
               metadata_sha256=pin['sha256'], contexts=contexts,
               missing_control_contexts=[dict(zip(BIO, key)) for key in
                   rows[BIO].drop_duplicates().itertuples(index=False, name=None) if key not in anchors],
               unresolved_bio={c: sorted(set(rows[c]) & {'', 'MISSING', 'UNASSIGNED'}) for c in BIO},
               target_examples=sorted(rows.target.unique().tolist())[:25],
               targets=int(rows.loc[rows.target != 'NTC', 'target'].nunique()),
               matrix_hash_verified_in_consumer=False, training_used=False)
(out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k:summary[k] for k in ('rows','cells','targets','unresolved_bio','missing_control_contexts')}))
