"""Move completed CPU fit artifacts privately to the GPU owner, then launch authorized training."""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path
from launch import HERE, CONFIG, call, push

DATA=Path('C:/Users/ferra/vcc2026-data/processed/ibrido_esecuzione_2026-10-04')

def run(owner,args,timeout=1800):
    r=subprocess.run([str(Path(sys.executable).with_name('kaggle.exe')),*args],
        env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG[owner])},capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    rec={'utc':time.time(),'owner':owner,'args':args,'returncode':r.returncode,'answer':(r.stdout+r.stderr)[-2500:]}
    with (HERE/'transfers.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(rec)+'\n')
    if r.returncode:raise RuntimeError(rec)
    return r.stdout+r.stderr

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    for held in ['Jurkat']:
        source='davideferante/vcc-hybrid-prep-'+held.lower()+'-r2'
        while True:
            rc,status=call('davideferante',['kernels','status',source])
            if rc:raise RuntimeError(status)
            if 'ERROR' in status or 'CANCEL' in status:raise RuntimeError(status)
            if 'COMPLETE' in status:break
            time.sleep(45)
        dest=DATA/(held.lower()+'_input_r1');dest.mkdir(parents=True,exist_ok=False)
        print('Downloading completed CPU input '+source,flush=True)
        run('davideferante',['kernels','output',source,'-p',str(dest),'--file-pattern',r'^fit/'])
        fit=dest/'fit';receipt=json.loads((fit/'complete.json').read_text())
        if not receipt['complete'] or receipt['held']!=held or receipt['held_fit_reads']:raise ValueError('fit audit failed')
        files={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in fit.iterdir() if p.is_file()}
        (HERE/(held.lower()+'_input_manifest.json')).write_text(json.dumps({'source':source,'files':files,'receipt':receipt},indent=1))
        slug='vcc-hybrid-fit-'+held.lower()+'-r1'
        meta={'title':slug,'id':'davidmaisterx/'+slug,'licenses':[{'name':'other'}],'isPrivate':True}
        (fit/'dataset-metadata.json').write_text(json.dumps(meta))
        print('Publishing private GPU input '+slug,flush=True)
        print(run('davidmaisterx',['datasets','create','-p',str(fit),'--dir-mode','skip','--keep-tabular'])[-500:],flush=True)
        for attempt in range(40):
            rc,status=call('davidmaisterx',['datasets','status','davidmaisterx/'+slug])
            if rc==0 and ('ready' in status.lower()):break
            if 'error' in status.lower() and '403' not in status and '404' not in status:raise RuntimeError(status)
            time.sleep(15)
        else:raise RuntimeError('dataset not ready')
        p={**receipt['parameters'],'fit_dataset':slug,'seeds':[0,1,2]}
        # At most two of our GPU fits concurrently; other users' jobs are never stopped.
        if held=='Jurkat':
            while True:
                active=[call('davidmaisterx',['kernels','status','davidmaisterx/vcc-hybrid-train-'+h+'-r1'])[1] for h in ['h1','hepg2']]
                if not all('RUNNING' in s or 'QUEUED' in s for s in active):break
                time.sleep(45)
        push('davidmaisterx','vcc-hybrid-train-'+held.lower()+'-r1',p,datasets=['davidmaisterx/'+slug],mode='train',gpu=True)
        print('TRAINING LAUNCHED '+held,flush=True)

if __name__=='__main__':main()
