"""One private byte-identical controls input for the authorized generation."""
import hashlib,json,os,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
SRC=Path(r'C:\Users\ferra\vcc2026-data\raw\controls')
STAGE=REPO/'data/cloud_inputs/vcc-official-controls-r1'
OUT=HERE/'generation_controls_r1'
REF='davideferrante11/vcc-official-controls-r1'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    if sys.argv[1:]!=['--prepare-only']:
        raise SystemExit('Upload blocked by automatic approval review; this helper currently prepares local files only.')
    OUT.mkdir(exist_ok=False)
    STAGE.mkdir(parents=True,exist_ok=False)
    ready=json.loads((HERE/'agenti/grok_transfer_esteso_r8/ready_dispatch.json').read_text())
    files={}
    for name,pin in ready['identity']['controls'].items():
        src=SRC/name
        assert sha(src)==pin['sha256'] and src.stat().st_size==pin['bytes']
        dest=STAGE/name
        shutil.copy2(src,dest)
        assert sha(dest)==pin['sha256']
        files[name]=pin
    meta={'id':REF,'title':'VCC official controls r1','licenses':[{'name':'other'}],
          'description':'Private official competition controls, byte-identical pinned input for generation. No training source or prediction.'}
    (STAGE/'dataset-metadata.json').write_text(json.dumps(meta,indent=2))
    receipt={'utc':datetime.now(timezone.utc).isoformat(),'ref':REF,'files':files,
             'stage':str(STAGE),'private':True,'reason':'historical generator input returns 403 on consumer; copy only official controls, no bank recompute',
             'state':'prepared_not_uploaded','accepted':False,
             'upload_blocked':'automatic approval review requires specific authorization for these three files and this private Kaggle destination'}
    dest=OUT/'launch.json'
    dest.open('x').write(json.dumps(receipt,indent=2))
    print(json.dumps({'ref':REF,'state':receipt['state'],'files':len(files),'bytes':sum(f['bytes'] for f in files.values())}),flush=True)

if __name__=='__main__':main()
