"""Audit cells readiness and, only when complete, prepare the two authorized packages.

No network requests, locator issuance or cloud launches. Each invocation writes
a fresh receipt. The DATI watcher remains the only NTC collector.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DATI=ROOT/'reports/modelli/dati_transfer_2026-10-08_01a11c34'
DATA=Path('C:/Users/ferra/vcc2026-data/external_models/01a11c35/ammi_cloud')
PRODUCER='davideferrante11/dt-ntc-inputs-01a11c34-r5'
REPORTS=['ntc_mx_partial_verified_r1.json','ntc_mx_r6a_verified_r1.json',
    'ntc_mx_r6b_verified_r1.json','ntc_mx_r6c_partial_verified_r1.json',
    'ntc_mx_r7a_verified_r1.json','ntc_mx_restored_verified_r1.json',
    'ntc_mx_r6c_restored_verified_r1.json','ntc_df11_terminal_verified_r1.json']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def gates(contract, known, terminal, ready, access):
    missing={fold:sorted(set(contract['folds'][fold]['ntc_expected_parts'])-set(known))
        for fold in ('C-K562','C-iPSC')}
    if terminal is None or ready is None:
        return 'WAITING_VERIFIED_NTC_MANIFESTS',missing
    if (terminal.get('status')!='PASS_METADATA_AND_CODE' or terminal.get('slug')!=PRODUCER
            or ready.get('pending_parts') or set(ready['parts'])!=set(contract['parts'])
            or any(missing.values())):
        raise ValueError('NTC gate incomplete or inconsistent')
    if access is None:
        return 'READY_FOR_AUTHORIZED_LOCATOR_EXTENSION',missing
    if (access.get('status')!='AUTHORIZED_INPUT_LOCATORS_COMPLETE_CONSUMER_HASHES_PENDING'
            or access.get('NTC_parts')!=12 or access.get('NTC_files')!=48):
        raise ValueError('private NTC access receipt differs')
    return 'READY_FOR_PACKAGE_PREPARATION',missing


def main(out, prepare=False):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    from ammi_inputs_v3 import checked
    from ammi_io_v4 import write
    from pie_adapter import sha256
    capsule=read(HERE/'ammi_code_package_r8/manifest.json')
    for pin in capsule['files'].values():checked(pin)
    ntc_path=DATI/'ammi_ntc_runtime_contract_r3.json';contract=read(ntc_path)
    known={}; reports=[]
    for name in REPORTS:
        path=DATI/name
        if not path.exists():continue
        report=read(path)
        if not report.get('status','').startswith('PASS'):raise ValueError('nonpassing NTC report')
        if isinstance(report.get('parts'),dict):
            for key,value in report['parts'].items():
                checked(value['completion'])
                if key in known and known[key]['completion']['sha256']!=value['completion']['sha256']:
                    raise ValueError('conflicting part receipt')
                known[key]=value
        reports.append(path)
    def optional(name):
        path=DATI/name
        return read(path) if path.exists() else None
    terminal=optional('ntc_df11_terminal_verified_r1.json')
    ready=optional('ntc_ready_manifest_r2.json')
    access=optional('ammi_private_access_with_ntc_r1.json')
    state,missing=gates(contract,known,terminal,ready,access)
    result=dict(utc=datetime.now(timezone.utc).isoformat(),status=state,missing_parts=missing,
        known_parts=len(known),code_capsule_sha256=sha256(HERE/'ammi_code_package_r8/manifest.json'),
        verified_runtime_code=True,readiness_only=not prepare,private=True,cloud_jobs_launched=0,
        locator_issuance_performed=False,NTC_collector='DATI PID912',execution_owner='MODELLI-ESTERNI',
        next_step='wait for both DATI manifests' if state.startswith('WAITING') else
            'run DATI extend_ammi_access_ntc.py once, within existing consent' if access is None else
            'prepare both cells packages, then fresh access/quota checks and individual guarded launches')
    if prepare and state=='READY_FOR_PACKAGE_PREPARATION':
        from build_ammi_runtime_v4 import build
        from package_ammi_cloud_v4 import package
        from compact_ammi_package_v1 import compact
        locator=checked(access['private_locators']);mount=checked(access['mount_plan'])
        checked(access['ntc_verification']);checked(access['ntc_ready_manifest'])
        jobs=[]
        for fold in ('C-K562','C-iPSC'):
            prefix='ammi_'+fold.lower()+'_cells'
            runtime=DATA/(fold+'-cells-r1')
            build(fold,'cells',runtime,ntc_path,reports,HERE/'autorizzazione_chiusura_r1.json')
            raw_receipt=HERE/(prefix+'_prepared_r1.json')
            final_receipt=HERE/(prefix+'_prepared_r2.json')
            package(runtime,locator,mount,DATA/(fold+'-cells-r1-deflate'),raw_receipt)
            compact(raw_receipt,DATA/(fold+'-cells-r1-package'),final_receipt)
            jobs.append(read(final_receipt))
        combined=HERE/'ammi_cells_prepared_r1.json'
        write(combined,dict(jobs=jobs,private=True,launch_pending=True))
        result.update(status='PACKAGES_PREPARED_NOT_LAUNCHED',prepared=str(combined),
            next_step='fresh native-access and GPU-quota preflights, then two guarded one-shot launches')
    write(out,result)
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--out',required=True)
    parser.add_argument('--prepare',action='store_true')
    args=parser.parse_args();main(args.out,args.prepare)
