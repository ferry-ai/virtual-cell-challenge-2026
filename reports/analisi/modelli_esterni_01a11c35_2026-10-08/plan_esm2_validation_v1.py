"""Plan existing-fit ESM2 support audit and level B; no transfer or cloud launch."""
import json
from datetime import datetime, timezone
from pathlib import Path
from ammi_io_v4 import write
from ammi_inputs_v3 import checked
from pie_adapter import sha256

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
VALID=HERE.parent/'validazione_indipendente_8a8ca58a_2026-10-08'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    delivery=read(HERE/'esm2_closure_bank_prepared_r1.json')
    conversion=read(HERE/'esm2_closure_conversion_r1.json')
    verified=read(HERE/'esm2_closure_verified_r1.json')
    if read(checked(verified['evidence']['common_support.json'])) != {}:
        raise ValueError('support audit premise changed')
    consumed=read(checked(verified['evidence']['consumption.json']))
    folds={}; transfer=[]; checks=[]
    for line,fold in [('k562','C-K562'),('ipsc','C-iPSC')]:
        base=VALID/'banco'/('livello_b_'+line+'_r1')
        prepared=read(base/'prepared.json'); params=prepared['params']
        effects=read(base/'effetti.json')
        filename=fold+'_E2f.npz'; pin=delivery['files'][filename]
        if (conversion['folds'][fold]['integration']['sha256']!=pin['sha256']
                or conversion['folds'][fold]['integration']['t0_sha256']!=effects['files']['T0']['sha256']):
            raise ValueError('fallback or reference differs from frozen level B')
        bench=ROOT/'reports/generatore_e_banchi/banco_v2_2026-10-04/bench_v2.py'
        if sha256(bench)!=params['bench_sha256']:
            raise ValueError('original bench changed')
        request_meta=read(base/'package/kernel-metadata.json')
        request_meta['id']='davidmaisterx/esm2-fallback-b-'+line+'-01a11c35-r1'
        request_meta['dataset_sources'].append(delivery['dataset'])
        request_meta['access_probe_only']=True
        meta_path=HERE/('esm2_level_b_'+line+'_access_request_metadata_r1.json')
        write(meta_path,request_meta)
        checks.append(dict(slug=request_meta['id'],metadata=dict(path=str(meta_path))))
        transfer.append(dict(source=delivery['dataset'],source_kind='dataset',file=filename,
            destination_account='davidmaisterx',bytes=pin['bytes'],sha256=pin['sha256'],
            explicit_transfer_approval_required=True))
        folds[fold]=dict(proposed_job=request_meta['id'],runtime='private Kaggle CPU',
            real_kernel='davidmaisterx/'+params['real_kernel'],
            real_files={'real_cells.npz':params['real_sha256'],'targets.json':params['real_targets_sha256']},
            reference_dataset=effects['dataset'],reference_file='T0.npz',reference=effects['files']['T0'],
            fallback=transfer[-1],scorer_version=params['scorer_version'],
            bench_sha256=params['bench_sha256'],snapshot_sha256=params['snapshot_sha256'],
            n_pred=params['n_pred'],bench_seed=params['bench_seed'],shuffle_seed=params['shuffle_seed'],
            emission='t28',generator_seed_base=20260912,generator_seed_indices=[0,1,2,3,4],
            steps=[dict(name='control',arms=['T0','T0shuffle'],gen_seeds=1,rule='PDS must decrease after frozen row permutation'),
                dict(name='full',arms=['T0','E2f'],gen_seeds=5,pair='E2f:T0'),
                dict(name='changed',arms=['T0','E2f'],gen_seeds=5,pair='E2f:T0',
                    selection='targets whose predictions or observed masks differ before truth scoring, intersect frozen real targets; skip below four')],
            native_RNA_stays_on_owner=True,no_new_training=True)
    audit_meta=read(HERE/'closure_bank_v1/esm2closure-r1/package/kernel-metadata.json')
    audit_meta['id']='davideferrante11/esm2-fallback-support-01a11c35-r1'
    audit_meta['kernel_sources'].append(verified['slug'])
    audit_meta['access_probe_only']=True
    audit_path=HERE/'esm2_support_access_request_metadata_r1.json';write(audit_path,audit_meta)
    checks.append(dict(slug=audit_meta['id'],metadata=dict(path=str(audit_path))))
    write(HERE/'esm2_validation_access_request_r1.json',dict(jobs=checks,
        purpose='read-only native inputs and cross-account fallback access probe, no launch or transfer'))
    manifest=read(VALID/'manifest_fold_v2.json')
    audit_files=[]
    for fold in folds:
        for arm in manifest['arms']:
            rows=[r for r in consumed if r['label']==arm and r['context']==fold]
            if len(rows)!=1:raise ValueError('unique frozen effect receipt required')
            audit_files.append(dict(source=verified['slug'],file='effects/'+arm+'__'+fold+'.npz',
                sha256=rows[0]['effects_sha256'],transfer=False))
    plan=dict(utc=datetime.now(timezone.utc).isoformat(),status='READ_ONLY_PLAN_NO_TRANSFER_OR_LAUNCH',
        ammi_plan='ammi_bank_access_plan_r1.json',priority='AMMI cells starts when NTC verified; these CPU checks do not delay or consume its GPU quota',
        fallback_classification='INCONCLUDENTE: level B missing; no resolved disc95 regression in measured C pair',
        native_E2='resolved regression on C-K562; distinct candidate, diagnostic stop before B',
        protocol_unchanged=True,no_training=True,
        support_audit=dict(destination_account='davideferrante11',runtime='private Kaggle CPU',
            files=audit_files,fallback_dataset=delivery['dataset'],fallback_files=[r['file'] for r in transfer],
            native_inputs=audit_meta,private_cross_account_transfer_required=False,
            truth=['k562','kolf_pan_genome','kolf_strong'],original_manifest_arms=list(manifest['arms']),
            recipe='Reconstruct keep, valid_pairs and cols95 exactly from unchanged bench_core; do not rerank or alter scores',
            outputs=['counts and hashes of full panel, retained targets, frozen cols95 and truth-valid support',
                'fallback filled-mask pairs and numerically changed pairs, separately',
                'pairs admitted to disc95 versus excluded by target, gene or truth validity; mutually exclusive exclusion counts',
                'per-target changed pair counts on evaluated support and subset summary',
                'reproduce stored original T0 and E2f disc95 before interpreting diagnostic counts'],
            common_support_empty_reason='original driver fills it only for analysis_arms/common_support, not external ESM2 arms'),
        level_B=folds,proposed_private_transfer_files=transfer,
        proposed_private_transfer_bytes=sum(r['bytes'] for r in transfer),
        transport='temporary signed locators in private MX CPU job packages; cloud-only download of two prediction NPZ after approval; no RNA movement or ACL change',
        metrics=['PDS','MSE','NMAE','FID','REACH','JAC'],
        reporting='raw and scaled local values, denominators, six-member and five-without-JAC deltas, paired-seed uncertainty, per-fold and equal-fold macro; not VCC scores',
        decision_rule='PROTOCOLLO_v1 section8 with v2 disc95 amendment; no new positive-disc95 threshold',
        remaining=['native-access preflight','explicit approval for two fallback prediction files to MX',
            'prepare and verify CPU packages using original bench snapshot','fresh CPU resource/slot checks before launch'],
        cloud_jobs_launched=0,URLs_issued=0,transferred_bytes=0,
        evidence={str(p.relative_to(ROOT)):sha256(p) for p in [VALID/'PROTOCOLLO_v1.md',VALID/'PROTOCOLLO_v2.md',
            VALID/'LIVELLO_B.md',VALID/'banco/bench_core.py',VALID/'banco/logo_driver.py',HERE/'esm2_closure_conversion_r1.json']})
    write(HERE/'esm2_validation_access_plan_r1.json',plan)
    print(json.dumps(dict(status=plan['status'],transfer_files=len(transfer),transfer_bytes=plan['proposed_private_transfer_bytes'])))


if __name__=='__main__':main()
