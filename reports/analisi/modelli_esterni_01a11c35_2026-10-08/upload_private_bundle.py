"""Upload only the pinned execution bundle to its explicitly private owner account."""
import argparse
import contextlib
from datetime import datetime,timezone
import io
import json
import os
from pathlib import Path

from pie_adapter import sha256
from source_access_preflight import CONFIG


def main(prepared_path,receipt):
    if receipt.exists():raise FileExistsError(receipt)
    prepared=json.loads(prepared_path.read_text());spec=prepared['bundle_dataset']
    owner=prepared['slug'].split('/')[0];folder=Path(spec['path']).parent
    if owner!='davideferante' or spec['slug']!='davideferante/esm2-j-ipsc-01a11c35-r4-private-bundle' or spec['private'] is not True:
        raise ValueError('only authorized J-iPSC private bundle accepted')
    if {p.name for p in folder.iterdir()}!={'bundle.bin','dataset-metadata.json'}:
        raise ValueError('unexpected upload file')
    if sha256(spec['path'])!=spec['sha256'] or sha256(folder/'dataset-metadata.json')!=spec['metadata_sha256']:
        raise ValueError('private bundle changed')
    lock=receipt.with_suffix('.lock')
    with lock.open('x') as f:json.dump(dict(slug=spec['slug'],prepared_sha256=sha256(prepared_path)),f)
    for key in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN'):os.environ.pop(key,None)
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG[owner])
    from kaggle.api.kaggle_api_extended import KaggleApi,ApiGetDatasetRequest
    api=KaggleApi();api.authenticate()
    try:
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            result=api.dataset_create_new(str(folder),public=False,quiet=True,convert_to_csv=False)
        if result.error:raise RuntimeError('private dataset creation rejected')
        request=ApiGetDatasetRequest();request.owner_slug,request.dataset_slug=spec['slug'].split('/')
        with api.build_kaggle_client() as client:
            saved=client.datasets.dataset_api_client.get_dataset(request)
        if saved.is_private is not True:raise RuntimeError('private visibility not confirmed')
        report=dict(status='PASS',utc=datetime.now(timezone.utc).isoformat(),dataset=spec['slug'],
            is_private=saved.is_private,version=saved.current_version_number,
            bundle_sha256=spec['sha256'],bytes=spec['bytes'],prepared_sha256=sha256(prepared_path),
            contents='authorized private execution bundle; no local RNA arrays')
    except Exception as exc:
        report=dict(status='needs_attention',exception_type=type(exc).__name__,dataset=spec['slug'])
    with receipt.open('x',encoding='utf-8') as f:json.dump(report,f,indent=1)
    print(json.dumps(report))
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True);a=p.parse_args();main(a.prepared,a.receipt)
