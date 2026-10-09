"""One-shot dependency continuation for exactly two already-authorized AMMI fits.

Waits only for DATI's local verified sentinels; never polls or re-extracts NTC.
No refit, bank transfer, bank launch, production fit or submission is possible.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def now():return datetime.now(timezone.utc).isoformat()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)


def check_pins(config):
    for path,digest in config['code_pins'].items():
        if sha(path)!=digest:raise ValueError('pinned workflow dependency changed')


def validate_jobs(jobs):
    expected={'davidmaisterx/ammi-c-k562-cells-17-01a11c35-r5','davidmaisterx/ammi-c-ipsc-cells-17-01a11c35-r5'}
    if len(jobs)!=2 or {j['slug'] for j in jobs}!=expected:
        raise ValueError('exactly the two authorized cells jobs required')
    if any(j['mode']!='cells' or j['seed']!=17 or j['private'] is not True for j in jobs):
        raise ValueError('authorized fit identity differs')


class Continuation:
    def __init__(self,config_path):
        self.config_path=Path(config_path);self.config=read(config_path)
        check_pins(self.config)
        self.here=Path(self.config['own']);self.dati=Path(self.config['dati'])
        self.work=Path(self.config['state_directory'])
        self.work.mkdir(parents=True,exist_ok=False)
        write_new(self.work/'claim.json',dict(pid=os.getpid(),utc=now(),config_sha256=sha(config_path)))
        self.status='STARTED'
        write_new(self.here/'ammi_cells_continuation_started_r1.json',dict(utc=now(),pid=os.getpid(),
            config_path=str(config_path),config_sha256=sha(config_path),state_directory=str(self.work),
            scope='one continuation, two initial cells fits only; no NTC polling or extra transfer scopes'))
        self.event('STARTED')

    def event(self,status,**fields):
        self.status=status
        value=dict(utc=now(),pid=os.getpid(),status=status,**fields)
        with (self.work/'events.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(value)+'\n')
        self.heartbeat()

    def heartbeat(self):
        # Mutable runtime heartbeat, outside Git; evidence and final receipts are append-only.
        (self.work/'heartbeat.json').write_text(json.dumps(dict(utc=now(),pid=os.getpid(),status=self.status)),encoding='utf-8')

    def pause(self):
        if (self.work/'STOP').exists():raise InterruptedError('local stop marker')
        time.sleep(60);self.heartbeat()

    def call(self,script,*args):
        check_pins(self.config)
        if (self.work/'STOP').exists():raise InterruptedError('local stop marker')
        result=subprocess.run([sys.executable,str(script),*map(str,args)],cwd=self.config['repo'],
            capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=900)
        # stdout/stderr are deliberately not persisted: no signed URLs or source logs.
        if result.returncode:
            self.event('COMMAND_FAILED',script=Path(script).name,returncode=result.returncode)
            raise RuntimeError('workflow command failed; inspect its immutable receipt')

    def wait_inputs(self):
        self.event('WAITING_DATI_VERIFIED_MANIFESTS')
        while not all((self.dati/name).is_file() for name in
            ('ntc_df11_terminal_verified_r1.json','ntc_ready_manifest_r2.json')):
            end=self.dati/'df11_ntc_watch_result_r1.json'
            if end.exists():
                result=read(end)
                if result.get('status')!='TERMINAL_COLLECTED' or result.get('producer_state')!='COMPLETE':
                    raise ValueError('DATI producer or collector requires diagnosis')
            self.pause()
        self.call(self.here/'prepare_ammi_cells_v1.py','--out',self.here/'ammi_cells_auto_readiness_r1.json')
        state=read(self.here/'ammi_cells_auto_readiness_r1.json')['status']
        if state not in ('READY_FOR_AUTHORIZED_LOCATOR_EXTENSION','READY_FOR_PACKAGE_PREPARATION'):
            raise ValueError('verified input gate did not open')

    def prepare(self):
        self.event('PREPARING_AUTHORIZED_CELLS_INPUTS')
        receipt=self.dati/'ammi_private_access_with_ntc_r1.json'
        if not receipt.exists():self.call(self.dati/'extend_ammi_access_ntc.py')
        self.call(self.here/'prepare_ammi_cells_v1.py','--prepare','--out',self.here/'ammi_cells_auto_packaging_r1.json')
        jobs=read(self.here/'ammi_cells_prepared_r1.json')['jobs'];validate_jobs(jobs)
        return jobs

    def dispatch(self,jobs):
        for index,job in enumerate(jobs,1):
            self.event('PREFLIGHT',fold=job['fold'])
            access=self.here/('ammi_cells_auto_access_r%d.json'%index)
            quota=self.here/('ammi_cells_auto_quota_r%d.json'%index)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(self.call,self.dati/'preflight_neural_inputs.py',
                    '--prepared',self.here/'ammi_cells_prepared_r1.json','--out',access),
                    pool.submit(self.call,self.here/'preflight_ammi_quota_v4.py','--out',quota)]
                for future in futures:future.result()
            prepared=self.here/('ammi_'+job['fold'].lower()+'_cells_prepared_r2.json')
            launch=self.here/('ammi_'+job['fold'].lower()+'_cells_auto_launch_r1.json')
            self.call(self.here/'launch_ammi_cloud_v4.py','--prepared',prepared,
                '--access-preflight',access,'--quota-preflight',quota,'--out',launch)
            result=read(launch)
            if result.get('accepted') is not True:
                raise ValueError('unaccepted or unknown push outcome; no retry')
            self.event('LAUNCH_ACCEPTED',slug=job['slug'],provider_state=result.get('state'))

    def collect(self,jobs):
        pending={j['fold']:j for j in jobs};revision=0
        while pending:
            revision+=1
            for fold,job in list(pending.items()):
                prepared=self.here/('ammi_'+fold.lower()+'_cells_prepared_r2.json')
                status=self.here/('ammi_'+fold.lower()+'_cells_auto_status_r%d.json'%revision)
                self.call(self.here/'check_ammi_remote_v1.py','--prepared',prepared,'--out',status)
                remote=read(status)
                if not remote.get('listed_exact_match'):raise ValueError('accepted job absent; no retry')
                self.event('REMOTE_STATE',slug=job['slug'],provider_state=remote['state'],
                    remote_code_matches=remote.get('remote_code_matches'),machine_shape=remote.get('machine_shape'))
                if remote['state'] not in ('COMPLETE','ERROR','CANCELLED'):continue
                if remote['state']=='CANCELLED':raise ValueError('cancelled job; no relaunch')
                receipt=self.here/('ammi_'+fold.lower()+'_cells_auto_retrieval_r1.json')
                self.call(self.here/'collect_ammi_evidence_v1.py','--prepared',prepared,
                    '--out',Path(self.config['evidence_root'])/('ammi_'+fold+'_cells_evidence_r1'),'--receipt',receipt)
                if read(receipt)['status']!='METADATA_PASS_BINARY_HASH_AND_READOUT_PENDING':
                    raise ValueError('cells fit or metadata failed; no refit')
                self.call(self.here/'summarize_ammi_metadata_v1.py','--receipt',receipt,'--remote',status,
                    '--out',self.here/('ammi_'+fold.lower()+'_cells_auto_metadata_verified_r1.json'))
                del pending[fold]
            if pending:self.pause()
        self.event('CELLS_METADATA_COMPLETE_BANK_AND_BINARY_VERIFICATION_PENDING')

    def run(self):
        try:
            self.wait_inputs();jobs=self.prepare();self.dispatch(jobs);self.collect(jobs)
            result=dict(status=self.status,utc=now(),new_bank_transfer_performed=False,refit_performed=False)
        except Exception as error:
            self.event('STOPPED_LOCAL' if isinstance(error,InterruptedError) else 'NEEDS_ATTENTION',error_type=type(error).__name__)
            result=dict(status=self.status,utc=now(),error_type=type(error).__name__,automatic_retry=False,
                remote_jobs_not_cancelled=True,details='read events and existing immutable step receipts; no private error text persisted')
        write_new(self.here/'ammi_cells_continuation_result_r1.json',result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--config',required=True)
    args=parser.parse_args();Continuation(args.config).run()
