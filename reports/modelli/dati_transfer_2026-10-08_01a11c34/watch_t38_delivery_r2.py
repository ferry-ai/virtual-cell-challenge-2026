"""One authorized watcher: verify the single cloud upload and obtain server receipt.

No new entries, compute launches, cancellations or automatic scoring retries.
The VCC token stays in the local official credential store.
"""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from percorso import HERE,DATA,ROOT,read,pin,sha,write_new,now
from cloud_t38_delivery_r2 import FOLDER,verify_current_authorization,auth_context
from quick_generation_cloud import api_for_owner


def main():
    verify_current_authorization()
    stage=DATA/'processed/dati_transfer_2026-10-08_01a11c34/cloud_delivery/r2/watcher'
    stage.mkdir(parents=True,exist_ok=False)
    proof=read(FOLDER/'prepared.json');entry=proof['entry_id']
    if entry!='LJmnhqqh1WTrx1JcoRlr':raise ValueError('entry differs')
    write_new(stage/'started.json',dict(utc=now(),pid=os.getpid(),entry_id=entry,
        job=proof['slug'],prepared=pin(FOLDER/'prepared.json'),authorization=pin(HERE/'t38_resume_authorization_r1.json')))
    def state(phase,**values):
        (stage/'state.json').write_text(json.dumps(dict(utc=now(),pid=os.getpid(),phase=phase,
            entry_id=entry,job=proof['slug'],**values)),encoding='utf-8')
    awake=ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    if not awake:raise ValueError('sleep inhibition failed')
    try:
        api=api_for_owner(proof['owner']);errors=0
        while True:
            if (stage/'STOP').exists():state('STOPPED_NO_CLOUD_CANCELLATION');return 1
            try:
                remote=str(api.kernels_status(proof['slug']).status).split('.')[-1];errors=0
            except Exception as exc:
                errors+=1;state('STATUS_CONNECTION_ERROR',error_type=type(exc).__name__,errors=errors)
                if errors>=10:return 1
                time.sleep(60);continue
            state('AWAITING_CLOUD',remote_status=remote)
            if remote=='COMPLETE':break
            if remote in ('ERROR','FAILED','CANCELLED'):
                state('CLOUD_FAILED_ENTRY_PRESERVED',remote_status=remote)
                write_new(FOLDER/'watcher_result_r1.json',dict(utc=now(),status='CLOUD_FAILED_ENTRY_PRESERVED',
                    entry_id=entry,job=proof['slug'],remote_status=remote,new_entry_created=False))
                return 1
            time.sleep(60)
        state('VERIFYING_UPLOAD_AND_LAUNCHING_SAME_ENTRY')
        env=dict(os.environ,PYTHONUTF8='1')
        result=subprocess.run([sys.executable,str(HERE/'finalize_cloud_t38_r2.py')],
            cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
        (stage/'finalize_stdout.txt').open('x',encoding='utf-8').write(result.stdout)
        (stage/'finalize_stderr.txt').open('x',encoding='utf-8').write(result.stderr)
        if result.returncode:
            state('FINALIZATION_NEEDS_INSPECTION',returncode=result.returncode)
            write_new(FOLDER/'watcher_result_r1.json',dict(utc=now(),status='FINALIZATION_NEEDS_INSPECTION',
                entry_id=entry,returncode=result.returncode,no_automatic_scoring_retry=True))
            return result.returncode
        state('READING_SERVER_RECEIPT')
        from vcc import api as vcc_api
        auth,profile,endpoint,token=auth_context()
        current=vcc_api.get_submission(endpoint,token,entry)
        receipt=ROOT/'reports/invii/trial_2026-10-09'/('status_'+entry+'_after_launch.json')
        write_new(receipt,current)
        write_new(FOLDER/'watcher_result_r1.json',dict(utc=now(),status='SERVER_RECEIPT_OBTAINED',
            entry_id=entry,server_status=current.get('status'),receipt=pin(receipt),
            submission=pin(ROOT/'reports/invii/trial_2026-10-09/submit_t38_cloud_result.json'),
            new_entry_created=False,source_RNA_downloaded=False))
        state('SERVER_RECEIPT_OBTAINED',server_status=current.get('status'))
        return 0
    except Exception as exc:
        state('WATCH_ERROR',error_type=type(exc).__name__)
        return 1
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__=='__main__':
    raise SystemExit(main())
