"""Read status/file inventories for the two authorized kernels; optionally fetch small reports."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

KERNELS = {'seed0':'davidmaisterx/vcc-lead-neural-sources-r1',
           'seed1':'davidmaisterx/vcc-lead-neural-seed1-r1'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--retrieve-small', action='store_true')
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    args.out.mkdir(parents=True)
    result = {'observed_utc':datetime.now(timezone.utc).isoformat(),'kernels':{},
              'no_push_restart_or_compute':True,'retrieval_requested':args.retrieve_small}
    for seed,kernel in KERNELS.items():
        record = {'kernel':kernel,'status':api.kernels_status(kernel).to_dict(ignore_defaults=False), 'files':[]}
        token = None
        while True:
            response = api.kernels_list_files(kernel, page_token=token, page_size=200)
            for item in response.files or []:
                record['files'].append({'name':item.name, 'bytes':item.size})
            token = getattr(response,'next_page_token',None) or getattr(response,'nextPageToken',None)
            if not token:
                break
        if args.retrieve_small and record['files']:
            selected = []
            for entry in record['files']:
                name = entry['name']
                path = PurePosixPath(name.replace('\\','/'))
                if path.is_absolute() or '..' in path.parts or ':' in name:
                    raise ValueError('Unsafe remote output path')
                if path.suffix.lower() in {'.json','.csv','.log','.txt'} and entry['bytes'] <= 10_000_000:
                    selected.append(entry)
            if sum(entry['bytes'] for entry in selected)>100_000_000:
                raise ValueError('Small-report retrieval exceeds its 100 MB bound')
            if selected:
                destination = args.out/seed
                pattern = '^(?:'+'|'.join(re.escape(entry['name']) for entry in selected)+')$'
                api.kernels_output(kernel,str(destination),file_pattern=pattern,force=False,quiet=True,page_size=200)
                record['retrieved'] = [{'name':str(p.relative_to(destination)),'bytes':p.stat().st_size,
                                        'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                                       for p in sorted(destination.rglob('*')) if p.is_file()]
        result['kernels'][seed] = record
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    with (args.out/'snapshot.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,default=str)
        f.write('\n')
    print(json.dumps({seed:{'status':entry['status'],'files':len(entry['files']),
                            'retrieved':len(entry.get('retrieved',[]))} for seed,entry in result['kernels'].items()}))


if __name__=='__main__':
    main()
