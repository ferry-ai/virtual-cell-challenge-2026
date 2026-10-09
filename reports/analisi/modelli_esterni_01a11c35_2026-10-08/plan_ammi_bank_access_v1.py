"""Plan df11 bank inputs from metadata only; never issue URLs or transfer data."""
from datetime import datetime, timezone
import json
from pathlib import Path
from ammi_inputs_v3 import checked
from ammi_io_v4 import write
from pie_adapter import sha256

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATI = ROOT/'reports/modelli/dati_transfer_2026-10-08_01a11c34'
PRIMARY = {'C-K562':'k562_gwps:48d8d89e89785608', 'C-iPSC':'kolf_pan_genome:1e7354e259028404'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    original = ROOT/'reports/modelli/banca_canonica_2026-10-07/fit/r1/package/kernel-metadata.json'
    meta = read(original)
    anchors = read(DATI/'ammi_anchors_verified_r1.json')
    contract = read(DATI/'panel_anchor_requests_r1.json')
    anchor_files = read(DATI/'ammi_anchors_retrieval_r1.json')['files']
    if anchors['status'] != 'PASS':
        raise ValueError('verified anchors required')
    existing = []; available = []; pending = []; aliases = []
    for fold in PRIMARY:
        report_path = HERE/('ammi_'+fold.lower()+'_none_retrieval_r2.json')
        report = read(report_path)
        if report['status'] != 'METADATA_PASS_BINARY_HASH_AND_READOUT_PENDING':
            raise ValueError('none metadata not verified')
        parity = read(checked(report['files']['zero_residual_parity.receipt.json']))
        anchor_id = contract['folds'][fold]['outer_query_anchor']
        anchor = anchors['anchors'][anchor_id]['effects']
        if anchor['sha256'] != parity['anchor_sha256'] or anchor['bytes'] != parity['bytes']:
            raise ValueError('nested anchor differs')
        paths = [r['file'] for r in anchor_files if r['sha256']==anchor['sha256'] and r['bytes']==anchor['bytes']]
        if not paths:
            raise ValueError('anchor producer file absent')
        existing.append(dict(fold=fold, arm='A0', source=anchors['slug'], file=paths[0],
            bytes=anchor['bytes'], sha256=anchor['sha256'], cross_account_transfer=False))
        unique = {}
        for entry in report['verification']['exports']:
            if entry['intervention'] != 'native':
                raise ValueError('unexpected none intervention')
            pin = (entry['bytes'], entry['sha256'])
            unique.setdefault(pin, entry)
            aliases.append(dict(fold=fold, mode='none', context_id=entry['context_id'],
                primary=entry['context_id']==PRIMARY[fold], sha256=entry['sha256']))
        for entry in unique.values():
            available.append(dict(fold=fold, mode='none', **{k:entry[k] for k in ('source','file','bytes','sha256')},
                payload_hash_verified_by_consumer=False))
        slug='ammi-'+fold.lower()+'-cells-17-01a11c35-r5'
        for entry in report['verification']['exports']:
            native=Path(entry['file']).name
            for intervention in ('native','swapped'):
                pending.append(dict(fold=fold, mode='cells', context_id=entry['context_id'],
                    primary=entry['context_id']==PRIMARY[fold], intervention=intervention,
                    expected_source='davidmaisterx/'+slug,
                    expected_file=slug+'/'+native.replace('_native.npz','_'+intervention+'.npz'),
                    source_identity='provisional until prepared receipt; job not launched',
                    bytes=None, sha256=None,
                    admission='only complete verified native export' if intervention=='native'
                    else 'only exported diagnostic passing guard; otherwise preserve failure metadata, no refit'))
    # The original scorer can resolve A0 by content directly from its owner's anchor job.
    meta.update(id='davideferrante11/vcc-validazione-logo-01a11c35-ammireadout-r1',
        title='AMMI readout access plan only', enable_gpu=False, is_private=True)
    meta['kernel_sources']=sorted(set(meta['kernel_sources']) | {anchors['slug']})
    meta['access_plan_only']=True
    meta_path=HERE/'ammi_bank_df11_native_sources_r1.json'; write(meta_path,meta)
    write(HERE/'ammi_bank_df11_access_request_r1.json',dict(jobs=[dict(slug=meta['id'],metadata=dict(path=str(meta_path)))],
        purpose='read-only native-input access check; no launch or transfer'))
    plan=dict(utc=datetime.now(timezone.utc).isoformat(), status='READ_ONLY_PLAN_NOT_TRANSFER_AUTHORIZATION',
        destination_account='davideferrante11', proposed_runtime='private Kaggle CPU',
        proposed_job=meta['id'], source_account='davidmaisterx',
        reason='reuse native bank inputs on df11; MX received HTTP403 for nine original private sources',
        native_dataset_sources=meta['dataset_sources'],native_kernel_sources=meta['kernel_sources'],
        native_anchors=existing, known_export_files=available, none_aliases=aliases,
        known_transfer_bytes=sum(e['bytes'] for e in available),
        pending_cells_exports=pending, maximum_files_before_cells_hash_dedup=len(available)+len(pending),
        primary_comparison_files_before_hash_dedup=6,
        minimum_policy='one file per distinct (bytes,SHA256) needed by frozen readout; retain all descriptive routes, no content-based selection',
        pending_total_bytes=True,
        proposed_transport='temporary signed locators from MX, inside one private df11 CPU package; download arrays only in cloud after separate transfer approval',
        input_adapter='stage authorized exports under /kaggle/temp, create input-root symlinks to original native mounts, bind unchanged driver INPUTS to combined root; adapter parity test required before launch',
        no_dataset_creation_required=True, no_ACL_change=True, no_publication=True,
        no_NTC_or_RNA_or_checkpoint_transfer=True, no_local_array_download=True,
        transfer_authorization='not covered by 105+NTC fit-input consent; explicit approval required before issuing new private export locators',
        remaining_gates=['df11 native access preflight','two cells fits complete and verified',
            'freeze exact distinct export hashes and bytes','approve exact private export transfer',
            'test input-root adapter with original driver unchanged','fresh CPU runtime preflight and full payload hashes'],
        evidence={str(p.relative_to(ROOT)):sha256(p) for p in (original,DATI/'ammi_anchors_verified_r1.json',
            HERE/'ammi_bank_base_access_preflight_r1.json',HERE/'prepare_ammi_readout_v1.py')},
        transferred_bytes=0, URLs_issued=0, cloud_jobs_launched=0)
    write(HERE/'ammi_bank_access_plan_r1.json',plan)
    print(json.dumps(dict(destination=plan['destination_account'],known_files=len(available),
        known_bytes=plan['known_transfer_bytes'],pending_exports=len(pending),native_anchors=len(existing))))


if __name__=='__main__':
    main()
