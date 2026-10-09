"""Prepare a frozen primary handoff as soon as one fold has completed."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from ammi_inputs_v3 import checked
from build_ammi_runtime_v4 import pin
from continue_ammi_cells_once_v1 import write_new
from plan_ammi_bank_access_v1 import PRIMARY

HERE=Path(__file__).resolve().parent


def prepare(fold,out):
    source=HERE/('ammi_'+fold.lower()+'_cells_auto_retrieval_r1.json')
    report=json.loads(source.read_text())
    if report['status']!='METADATA_PASS_BINARY_HASH_AND_READOUT_PENDING': raise ValueError('terminal metadata required')
    for item in report['files'].values(): checked(item)
    complete=json.loads(checked(report['files']['complete.json']).read_text())
    if (complete['status'],complete['fold'],complete['mode'],complete['seed'])!=('COMPLETE',fold,'cells',17):
        raise ValueError('wrong completed fit')
    none_path=HERE/('ammi_'+fold.lower()+'_none_retrieval_r2.json')
    none=json.loads(none_path.read_text())
    cells_anchor=json.loads(checked(report['files']['zero_residual_parity.receipt.json']).read_text())
    none_anchor=json.loads(checked(none['files']['zero_residual_parity.receipt.json']).read_text())
    if cells_anchor['anchor_sha256']!=none_anchor['anchor_sha256']: raise ValueError('cells/none anchor differs')
    exports=report['verification']['exports']
    chosen=[row for row in exports if row['context_id']==PRIMARY[fold]]
    if sum(row['intervention']=='native' for row in chosen)!=1: raise ValueError('primary native absent')
    unique={row['sha256']:row for row in chosen}
    result=dict(utc=datetime.now(timezone.utc).isoformat(),status='ONE_FOLD_METADATA_VERIFIED_READOUT_PENDING',
        fold=fold,primary_context=PRIMARY[fold],files=list(unique.values()),unique_files=len(unique),
        total_bytes=sum(row['bytes'] for row in unique.values()),all_routes_preserved=exports,
        diagnostic_failures=report['verification']['swapped_diagnostic_failures'],
        metadata_inputs=[pin(source),pin(none_path)],same_cells_and_none_anchor=True,
        anchor_sha256=cells_anchor['anchor_sha256'],primary_fixed_before_results=True,
        destination_account='davideferrante11',readout_owner='VALIDAZIONE',
        exact_private_destination_pending=True,output_transfer_authorized=False,
        consumer_payload_hashes_verified=False,benefit_verified=False,complete_D053=False,
        requested_contrasts=['cells - A0','cells - none','cells - swapped','cells - T0 (distinct anchor)'],
        no_array_download=True,no_URLs_issued=True,no_cloud_job_launched=True,preparer=pin(__file__))
    write_new(out,result)
    print(json.dumps(dict(fold=fold,files=len(unique),bytes=result['total_bytes'],same_anchor=True)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--fold',required=True,choices=list(PRIMARY))
    parser.add_argument('--out',required=True)
    args=parser.parse_args();prepare(args.fold,args.out)
