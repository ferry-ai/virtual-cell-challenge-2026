"""One-shot read-only terminal collector for the already running df11 extraction.

No launch, cancellation, sharing, link issuance, publication, or messaging.
Stops after terminal metadata verification; a failed producer needs diagnosis.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from cloud_campaign import call
from percorso import HERE,DATA,now,write_new,pin,read

slug='davideferrante11/dt-ntc-inputs-01a11c34-r5';revision='df11_watch_r1'
work=DATA/'processed/dati_transfer_2026-10-08_01a11c34'/revision
work.mkdir(parents=True,exist_ok=False)
write_new(HERE/'df11_ntc_watch_started_r1.json',dict(utc=now(),pid=os.getpid(),slug=slug,
    heartbeat=str(work/'heartbeat.json'),stop_marker=str(work/'STOP'),
    final_result=str(HERE/'df11_ntc_watch_result_r1.json'),poll_seconds=60,
    scope='status and terminal metadata, producer verification and consolidation only; no relaunch or transfer'))
def run(script,*args):
    result=subprocess.run([sys.executable,str(HERE/script),*map(str,args)],capture_output=True,text=True,timeout=600)
    if result.returncode:raise RuntimeError(script+' failed; '+result.stderr[-1200:])
    return result.stdout
previous=None
try:
    while True:
        if (work/'STOP').exists():
            write_new(HERE/'df11_ntc_watch_result_r1.json',dict(utc=now(),status='WATCH_STOPPED_NO_REMOTE_CHANGE'));break
        rc,answer=call('davideferrante11',['kernels','status',slug])
        state=next((s for s in ('COMPLETE','ERROR','CANCELLED','RUNNING','QUEUED') if s in answer),'UNKNOWN') if rc==0 else 'UNKNOWN'
        (work/'heartbeat.json').write_text(json.dumps(dict(utc=now(),pid=os.getpid(),state=state,returncode=rc)))
        if state!=previous:print(json.dumps(dict(utc=now(),state=state)),flush=True);previous=state
        if state in ('COMPLETE','ERROR','CANCELLED'):
            print(run('observe_neural_inputs.py','--out',revision,'--slug',slug,'--metadata'),flush=True)
            metadata=HERE/'neural_launches/terminal_metadata/davideferrante11'/('dt-ntc-inputs-01a11c34-r5_'+revision)
            verified=HERE/'ntc_df11_terminal_verified_r1.json'
            if state=='COMPLETE' or (metadata/'progress.json').is_file():
                arguments=['--prepared',HERE/'neural_inputs_cloud_prepared_r5.json','--slug',slug,
                    '--metadata',metadata,'--out',verified]
                if state!='COMPLETE':arguments.append('--allow-partial')
                print(run('verify_ntc_completion.py',*arguments),flush=True)
                print(run('consolidate_ntc_ready.py','--df11-report',verified.name,'--out','ntc_ready_manifest_r2.json'),flush=True)
            write_new(HERE/'df11_ntc_watch_result_r1.json',dict(utc=now(),status='TERMINAL_COLLECTED',producer_state=state,
                verification=pin(verified) if verified.exists() else None,
                ready_manifest=pin(HERE/'ntc_ready_manifest_r2.json') if (HERE/'ntc_ready_manifest_r2.json').exists() else None,
                transfer_performed=False,relaunch_performed=False,needs_diagnosis=state!='COMPLETE'))
            break
        time.sleep(60)
except Exception as exc:
    write_new(HERE/'df11_ntc_watch_result_r1.json',dict(utc=now(),status='WATCH_ERROR',error_type=type(exc).__name__,message=str(exc),remote_changed=False))
    raise
