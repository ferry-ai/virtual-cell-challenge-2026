"""Freeze the six verified model/prediction handoffs; metadata only, no scoring."""
from datetime import datetime, timezone
import json
from pathlib import Path
from pie_adapter import sha256

HERE=Path(__file__).resolve().parent
DATI=HERE.parents[1]/'modelli/dati_transfer_2026-10-08_01a11c34'
JOBS=[('production','esm2-production-01a11c35-r4','resume_r4'),
      ('T','esm2-t-01a11c35-r3','terminal_collection_r1'),
      ('C-K562','esm2-c-k562-01a11c35-r1','resume_r4'),
      ('C-iPSC','esm2-c-ipsc-01a11c35-r3','resume_r4'),
      ('J-K562','esm2-j-k562-01a11c35-r1','terminal_collection_r1'),
      ('J-iPSC','esm2-j-ipsc-01a11c35-r1','resume_r4')]


def pin(path):
    return dict(path=path.as_posix(),bytes=path.stat().st_size,sha256=sha256(path))


if __name__=='__main__':
    result=dict(utc=datetime.now(timezone.utc).isoformat(),status='SIX_TECHNICAL_AND_CONSUMPTION_PASS',
                jobs=[],scientific_promotion=False,complete_D053=False,
                C_integration='T0 where transfer predicts; ESM2 fallback elsewhere, fixed before reading C')
    for fold,job,label in JOBS:
        vp=HERE/(job+'.verified_'+label+'.json')
        v=json.loads(vp.read_text())
        cp=DATI/('esm2_'+fold+'_consumption_verified_r1.json')
        c=json.loads(cp.read_text())
        if v['status']!='PASS' or c['status']!='PASS' or v['receipt_sha256']!=c['fit_receipt_sha256']:
            raise ValueError('technical/independent receipt mismatch')
        root=Path(v['job_root'])
        artifact={}
        for name,filename,key in [('model','ridge.npz','model_sha256'),
                                  ('predictions','native_predictions.npz','predictions_sha256')]:
            path=root/'fit'/filename
            artifact[name]=dict(path=path.as_posix(),bytes=path.stat().st_size,
                sha256=v[key],hash_source=vp.name)
        result['jobs'].append(dict(fold=fold,job_id=job,artifacts=artifact,
            technical_receipt=pin(vp),independent_consumption_receipt=pin(cp),
            rows=c['rows'],contexts=c['contexts'],queries=v['queries'],genes=v['genes'],
            feature_missing_queries=v['feature_missing_queries'],uses_context=v['uses_context'],
            scientific_benefit='independent scorer owns result'))
    out=HERE/'completed_fits_handoff_r1.json'
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(status=result['status'],jobs=len(result['jobs']),manifest=pin(out))))
