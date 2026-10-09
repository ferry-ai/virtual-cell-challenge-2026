"""Verify remote code and frozen-bank provenance; summarize without rescore/tuning."""
import json
import hashlib
from pathlib import Path
from ammi_inputs_v3 import checked
from ammi_io_v4 import write
from esm2_closure_cloud_v1 import api
from pie_adapter import sha256

HERE=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text())

def main():
    retrieval=read(HERE/'esm2_closure_retrieval_r1.json')
    files=retrieval['files']
    for pin in files.values():checked(pin)
    data=Path(retrieval['output']);result=read(data/'results.json')
    bank=read(HERE/'closure_bank_v1/esm2closure-r1/prepared.json')
    params=read(HERE/'closure_bank_v1/esm2closure-r1/package/params.json')
    analysis=read(HERE/'closure_bank_v1/analisi_esm2closure-r1.json')
    source=data.parent/'esm2_closure_remote_source_r1'
    if not source.exists():
        source.mkdir(exist_ok=False)
        service=api();service.kernels_pull(bank['slug'],path=str(source),metadata=True,quiet=True)
    code=[p for p in source.iterdir() if p.suffix=='.py']
    if len(code)!=1:raise ValueError('remote code artifact differs')
    # Kaggle SDK writes CRLF on this Windows host. Only canonicalize those line
    # endings; do not strip or alter any source text or embedded payload.
    canonical=hashlib.sha256(code[0].read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    if canonical!=bank['code']['sha256']:raise ValueError('remote source content differs')
    metadata=read(source/'kernel-metadata.json')
    if metadata.get('is_private') not in (True,'true'):raise ValueError('remote privacy differs')
    status=read(data/'status.json')
    if not status.get('usable') or not all(status['parity'].values()):raise ValueError('bank not technically usable')
    if any(result[k]!=params[k] for k in ('manifest_sha256','release_sha256')):raise ValueError('frozen input identity differs')
    external=read(data/'external_arms.json')
    expected={a+'/'+f:pin for a,folds in analysis['external_arms'].items() for f,pin in folds.items()}
    if set(external)!=set(expected) or any(any(external[k][p]!=v[p] for p in ('bytes','sha256')) for k,v in expected.items()):
        raise ValueError('external prediction consumption differs')
    consumption=read(data/'consumption.json')
    if any(x.get('held_tables_read') or x.get('sources_matching_held_patterns') for x in consumption):
        raise ValueError('held response source consumed')
    anchors=read(HERE.parents[2]/'reports/modelli/dati_transfer_2026-10-08_01a11c34/ammi_anchors_verified_r1.json')
    for fold,ident in [('C-K562','parity_k562'),('C-iPSC','parity_ipsc')]:
        row=next(x for x in consumption if x['context']==fold and x['label']=='T0')
        if row['effects_sha256']!=anchors['anchors'][ident]['effects']['sha256']:
            raise ValueError('fallback anchor differs from frozen bank')
    summary={}
    for family,folds,names in [('C',result['folds'],['C-K562','C-iPSC']),('J',result['regime_J']['folds'],['J-iPSC'])]:
        for fold in names:
            summary[fold]={}
            for table,row in folds[fold]['truth'].items():
                summary[fold][table]=dict(role=row['role'],targets=row['targets'],genes_disc95=row['genes_for_rank_95'],
                    arms={a:dict(disc95=v['disc95'],predicted=v['targets_with_a_prediction']) for a,v in row['arms'].items()
                          if a in ('T0','E2','E2g','E2f','E2jip','E2jipg','E2T')},
                    contrasts={c:v['measures']['disc95']['all'] for c,v in row['contrasts'].items()
                          if c in ('C_integration','C_native','C_specific','c_shufflein_E2','J_native','J_specific','J_minus_T','c_shufflein_E2jip')})
    report=dict(status='TECHNICAL_PASS_NO_PROMOTION',slug=bank['slug'],remote_code_sha256=sha256(code[0]),
        remote_code_LF_sha256=canonical,local_code_sha256=bank['code']['sha256'],
        remote_source_difference='SDK Windows CRLF only; exact LF content equality verified',
        remote_private=True,evidence=files,executor='MODELLI-ESTERNI',independent_code_unchanged=True,
        independent_final_judgment_owner='VALIDAZIONE',bootstrap=result['bootstrap'],
        development_lineages_not_confirmation=True,not_vcc_scores=True,summary=summary,
        C_integration_macro=result['macro']['C_integration']['measures']['disc95'],
        verdict='Do not adopt target-only ESM2 as a replacement or demonstrated improvement; preserve component and embeddings for the already declared AMMI test.')
    write(HERE/'esm2_closure_verified_r1.json',report)
    print(json.dumps(dict(status=report['status'],summary=summary),allow_nan=False))

if __name__=='__main__':main()
