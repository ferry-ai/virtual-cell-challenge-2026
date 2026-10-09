"""Persistent exact-entry watcher: authenticated live evidence, then one finalization."""
import ctypes
import json
import os
import subprocess
import sys
import time
from percorso import HERE, ROOT, read, pin, write_new, now
from prepare_t39_t3_runtime_r2 import FOLDER, PRIVATE
from operate_t39_t3_r1 import consent
from finalize_t39_t3_live_r1 import extract
from quick_generation_cloud import api_for_owner


def main():
    consent();proof=read(FOLDER/'prepared.json');stage=PRIVATE/'watcher';stage.mkdir(exist_ok=False)
    write_new(stage/'started.json',dict(utc=now(),pid=os.getpid(),entry_id=proof['entry_id'],prepared=pin(FOLDER/'prepared.json')))
    def state(phase,**fields):
        (stage/'state.json').write_text(json.dumps(dict(utc=now(),pid=os.getpid(),phase=phase,
            entry_id=proof['entry_id'],job=proof['slug'],**fields)),encoding='utf-8')
    awake=ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    if not awake:raise ValueError('sleep inhibition unavailable')
    api=api_for_owner('davideferrante11');index=0;errors=0
    try:
        while True:
            if (stage/'STOP').exists():state('STOPPED');return 1
            if (FOLDER/'server_receipt_obtained.json').exists():state('SERVER_RECEIPT_OBTAINED');return 0
            index+=1;label='watch_'+str(index).zfill(3)
            try:status=str(api.kernels_status(proof['slug']).status).split('.')[-1];errors=0
            except Exception as exc:
                errors+=1;state('STATUS_READ_ERROR',error_type=type(exc).__name__,errors=errors)
                if errors>=10:return 1
                time.sleep(45);continue
            state('AWAITING_CLOUD',remote_status=status)
            command=[sys.executable,str(HERE/'read_t39_live_r2.py'),'r2',label]
            run=subprocess.run(command,cwd=ROOT,capture_output=True,env=dict(os.environ,PYTHONUTF8='1'),timeout=90)
            stream=FOLDER/('live_log_'+label+'.json')
            ready=False
            if stream.exists():
                snapshot=read(stream)
                state('AWAITING_CLOUD',remote_status=status,latest_stream=str(stream),
                      latest_events=snapshot.get('events',[])[-3:])
                try:extract(stream,proof);ready=True
                except (ValueError,KeyError):pass
            if ready:
                state('FINALIZING_SAME_ENTRY',stream=str(stream))
                result=subprocess.run([sys.executable,str(HERE/'finalize_t39_t3_live_r1.py'),str(stream)],
                    cwd=ROOT,capture_output=True,env=dict(os.environ,PYTHONUTF8='1'),timeout=180)
                (stage/'finalize_stdout.txt').write_bytes(result.stdout)
                (stage/'finalize_stderr.txt').write_bytes(result.stderr)
                if result.returncode:
                    state('FINALIZATION_NEEDS_INSPECTION',returncode=result.returncode)
                    return result.returncode
                state('SERVER_RECEIPT_OBTAINED');return 0
            if status in ('ERROR','FAILED','CANCELLED'):
                state('CLOUD_FAILED_ENTRY_PRESERVED',remote_status=status,latest_stream=str(stream));return 1
            time.sleep(45)
    except Exception as exc:
        state('WATCH_ERROR',error_type=type(exc).__name__);return 1
    finally:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__=='__main__':raise SystemExit(main())
