"""Recover local locator assembly after relative/absolute authorization mismatch.

No network calls, SDK imports, source requests or payload downloads. Existing
per-source files remain unchanged; every pin and scope is checked before assembly.
"""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
DATI=HERE.parents[2]/'reports/modelli/dati_transfer_2026-10-08_01a11c34'
sys.path.insert(0,str(DATI))
import issue_production_mx_private_access_r1 as emitter


def main():
    authorization=(HERE/'ammi_production_mx_authorized_r1.json').resolve()
    auth=emitter.read(authorization)
    if emitter.sha(emitter.__file__)!=auth['emitter_sha256']: raise ValueError('emitter code changed')
    plan=emitter.guard(authorization,emitter.JOB)
    stage=emitter.safe_stage('C:/Users/ferra/vcc2026-data/external_models/01a11c35/ammi_production_mx_access_r1')
    auth_pin=emitter.pin(authorization)
    relative_pin=emitter.pin(authorization.relative_to(HERE.parents[2]))
    mapping={};origins=[];source_pins=[];mismatch_reproduced=0
    for source in sorted({r['source'] for r in plan['files']}):
        expected={r['file']:r for r in plan['files'] if r['source']==source}
        path=stage/(source.replace('/','__')+'.private.json')
        part=emitter.read(path)
        source_pins.append(emitter.pin(path))
        if part['authorization']!=relative_pin: mismatch_reproduced+=1
        if (part['authorization']!=auth_pin or part['destination_job']!=emitter.JOB
                or part['source']!=source or set(part['files'])!=set(expected)
                or part['body_bytes_read']!=0): raise ValueError('source receipt differs')
        for name,row in part['files'].items():
            if any(row.get(k)!=v for k,v in expected[name].items()): raise ValueError('file scope differs')
            if row['sha256'] in mapping: raise ValueError('duplicate digest')
            mapping[row['sha256']]=dict(sha256=row['sha256'],bytes=row['bytes'],url=emitter.safe_url(row['url']))
            origins.append(dict(source_kind='kernel',**expected[name]))
    if mismatch_reproduced!=10 or len(mapping)!=209 or sum(r['bytes'] for r in mapping.values())!=10100920946:
        raise ValueError('recovery preconditions differ')
    emitter.guard(authorization,emitter.JOB)
    if emitter.pin(authorization)!=auth_pin: raise ValueError('authorization changed')
    locator=stage/'private_locators.json'
    receipt=DATI/'production_mx_private_access_issued_r1.json'
    if locator.exists() or receipt.exists(): raise FileExistsError('immutable recovery output exists')
    emitter.write_new(locator,dict(status='authorized',utc=emitter.now(),owner=emitter.OWNER,
        destination_job=emitter.JOB,purpose=emitter.PURPOSE,private_only=True,
        authorization=auth_pin,authorized_plan=emitter.pin(emitter.PLAN),emitter=emitter.pin(emitter.__file__),
        local_finalizer=emitter.pin(__file__),files=mapping,origins=origins,temporary_bearer_urls=True,
        never_log_or_commit=True,runtime_full_size_and_sha256_verification_required=True,ready_for_training=False))
    emitter.write_new(receipt,dict(utc=emitter.now(),status='LOCATORS_ISSUED_CONSUMER_HASHES_PENDING',
        authorization=auth_pin,plan=emitter.pin(emitter.PLAN),emitter=emitter.pin(emitter.__file__),
        local_finalizer=emitter.pin(__file__),destination_job=emitter.JOB,private_locators=emitter.pin(locator),
        files=209,bytes=10100920946,body_bytes_read=0,cloud_jobs_launched=0,
        hashes_are_expected_pins_not_fresh_remote_content_hashes=True,
        source_visibility_changed=False,consumer_full_size_and_sha256_required=True,ready_for_training=False))
    emitter.write_new(HERE/'ammi_production_mx_access_recovery_r1.json',dict(utc=emitter.now(),status='PASS',
        original_failure='main authorization pin relative; child authorization pin absolute; byte/hash identity unchanged',
        failure_reproduced_on_sources=mismatch_reproduced,source_private_receipts=source_pins,
        corrected_authorization=auth_pin,output_receipt=emitter.pin(receipt),finalizer=emitter.pin(__file__),
        new_network_calls=0,new_locators_issued=0,private_URLs_logged=False))
    print(json.dumps(dict(status='LOCAL_ASSEMBLY_RECOVERED',sources=10,files=209,new_network_calls=0)))


if __name__=='__main__': main()
