"""Verify native predictions before slow model retrieval; never claim reload parity."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import zipfile
import numpy as np
from pie_adapter import sha256
from verify_fit_outputs import blocks


def verify(root, prepared_path):
    complete=json.loads((root/'complete.json').read_text())
    receipt=json.loads((root/'fit/manifest.json').read_text())
    prepared=json.loads(prepared_path.read_text())
    if complete['status']!='COMPLETE': raise ValueError('complete receipt required')
    prediction=root/'fit/native_predictions.npz'
    digest=sha256(prediction)
    if digest!=complete['predictions_sha256'] or digest!=receipt['native_predictions_sha256']:
        raise ValueError('prediction hash mismatch')
    if sha256(root/'fit/manifest.json')!=complete['receipt_sha256']:
        raise ValueError('fit receipt hash mismatch')
    queries=receipt['manifest']['queries']; genes=receipt['store_receipt']['source_manifest']['genes']
    if len(queries)!=prepared['queries']: raise ValueError('query count differs')
    with np.load(prediction,allow_pickle=False) as z:
        if z['genes'].tolist()!=genes: raise ValueError('gene axis differs')
        for name,key in [('targets','target'),('context_ids','context_id'),('context_groups','context_group')]:
            if z[name].tolist()!=[q[key] for q in queries]: raise ValueError('query axis differs')
        available=z['esm2_observed']
        if available.dtype!=bool or available.shape!=(len(queries),): raise ValueError('feature availability differs')
    checked=0; support=None; generic=None
    with zipfile.ZipFile(prediction) as archive:
        iterators=[blocks(archive,n) for n in ('effects','observed','generic','generic_observed')]
        for parts in zip(*iterators,strict=True):
            start=parts[0][0]; effect,mask,baseline,bmask=[p[1] for p in parts]
            if any(p[0]!=start for p in parts) or effect.shape[1]!=len(genes): raise ValueError('block axes differ')
            if support is None: support=bmask[0].copy(); generic=baseline[0].copy()
            expected=available[start:start+len(effect),None]&support[None,:]
            if (mask.dtype!=bool or bmask.dtype!=bool or not np.array_equal(mask,expected)
                    or not np.array_equal(np.isfinite(effect),expected) or not np.isnan(effect[~expected]).all()
                    or not np.array_equal(bmask,np.broadcast_to(support,bmask.shape))
                    or not np.array_equal(baseline,np.broadcast_to(generic,baseline.shape))):
                raise ValueError('prediction or mask invariant failed')
            checked+=len(effect)
    if checked!=len(queries): raise ValueError('incomplete row verification')
    return dict(status='PREDICTIONS_PASS_MODEL_RELOAD_PENDING',utc=datetime.now(timezone.utc).isoformat(),
        job_id=prepared['job_id'],predictions_path=str(prediction),predictions_bytes=prediction.stat().st_size,
        predictions_sha256=digest,queries=checked,genes=len(genes),feature_missing_queries=int((~available).sum()),
        all_prediction_cells_verified=True,model_hash_verified=False,reload_parity_verified=False,
        source_receipt_sha256=complete['receipt_sha256'],training_RNA_read=False,scientific_benefit='not_scored')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job-root',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    result=verify(a.job_root,a.prepared)
    with a.out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
