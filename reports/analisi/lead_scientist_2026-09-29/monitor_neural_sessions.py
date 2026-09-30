"""Monitor authorized neural sessions; use static outputs only after terminal status."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

KERNELS={'seed0':'davidmaisterx/vcc-lead-neural-sources-r1',
         'seed1':'davidmaisterx/vcc-lead-neural-seed1-r1',
         'cluster0':'davidmaisterx/vcc-lead-neural-cluster0-r1'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seeds',nargs='+',choices=KERNELS,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--download-if-terminal',action='store_true')
    args=ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi();api.authenticate()
    args.out.mkdir(parents=True)
    result={'observed_utc':datetime.now(timezone.utc).isoformat(),'sessions':{}}
    for seed in args.seeds:
        kernel=KERNELS[seed]
        status=api.kernels_status(kernel).to_dict(ignore_defaults=False)
        record={'kernel':kernel,'status':status,'downloaded':False}
        if status['status'] in {'ERROR','COMPLETE','CANCEL_ACKNOWLEDGED'} and args.download_if_terminal:
            helper=Path(__file__).with_name('download_neural_reports.py')
            rc=subprocess.run([sys.executable,str(helper),'--kernel',kernel,'--out',str(args.out/seed)],check=False).returncode
            record.update({'download_returncode':rc,'downloaded':rc==0})
        result['sessions'][seed]=record
    result['finished_utc']=datetime.now(timezone.utc).isoformat()
    (args.out/'snapshot.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':
    main()
