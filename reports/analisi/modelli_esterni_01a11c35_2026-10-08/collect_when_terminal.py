"""One-shot collector for an explicit finite list of already launched private jobs.

No launches, retries, source retrieval, publications or scoring. Exits after all
named jobs have terminal receipts, or records an actionable collection failure.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

from collect_cloud_fit_v2 import main as collect
from verify_fit_outputs import verify

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'reports/modelli/dati_transfer_2026-10-08_01a11c34'))
from cloud_campaign import call


def write_new(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=1)


def run(prepared_paths,destination,esm2,label):
    lock=HERE/(label+'.lock')
    jobs={json.loads(p.read_text())['slug']:p for p in prepared_paths}
    write_new(lock,dict(utc=datetime.now(timezone.utc).isoformat(),jobs=list(jobs),
                       scope='one-time collection only; no job launch'))
    previous={};pending=dict(jobs);finished={}
    events=HERE/(label+'.jsonl')
    while pending:
        for slug,prepared_path in list(pending.items()):
            rc,body=call(slug.split('/')[0],['kernels','status',slug])
            state=next((s for s in ('COMPLETE','ERROR','RUNNING','QUEUED','CANCELLED')
                        if 'KernelWorkerStatus.'+s in body),'UNKNOWN')
            utc=datetime.now(timezone.utc).isoformat()
            if previous.get(slug)!=state:
                entry=dict(utc=utc,slug=slug,state=state,returncode=rc)
                with events.open('a',encoding='utf-8') as f:f.write(json.dumps(entry)+'\n')
                print(json.dumps(entry),flush=True);previous[slug]=state
            if rc or state not in ('COMPLETE','ERROR','CANCELLED'):continue
            job=slug.split('/')[1]
            try:
                if state=='CANCELLED':raise RuntimeError('cancelled job')
                out=destination/job
                retrieval=HERE/(job+'.retrieval_'+label+'.json')
                collect(prepared_path,out,retrieval)
                if state=='COMPLETE':
                    result=verify(out/job,prepared_path,esm2)
                    write_new(HERE/(job+'.verified_'+label+'.json'),result)
                finished[slug]=dict(provider_state=state,collection='finished',out=str(out/job),
                    scientific_benefit='not_scored',independent_validation='pending')
            except Exception as exc:
                # Do not persist arbitrary provider exception text or secret URLs.
                finished[slug]=dict(provider_state=state,collection='needs_attention',exception_type=type(exc).__name__)
            write_new(HERE/(job+'.terminal_'+label+'.json'),dict(utc=utc,**finished[slug]))
            del pending[slug]
        print(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),pending=list(pending),
                              terminal=list(finished))),flush=True)
        if pending:time.sleep(60)
    write_new(HERE/(label+'.complete.json'),dict(utc=datetime.now(timezone.utc).isoformat(),jobs=finished))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',nargs='+',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--esm2',type=Path,required=True)
    p.add_argument('--label',required=True)
    a=p.parse_args();run(a.prepared,a.destination,a.esm2,a.label)
