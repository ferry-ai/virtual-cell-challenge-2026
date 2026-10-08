"""Verify actual frozen T2 effects independently of the cloud receipt."""
import json
import numpy as np
from percorso import DATA,HERE,now,pin,read,sha,write_new


def main():
    proof=HERE/'final_t2/r1/fit/completion_r1/verification.json'
    receipt_path=proof.with_name('t2_consumption.json');receipt=read(receipt_path)
    if sha(receipt_path)!=read(proof)['receipt']['sha256'] or not receipt['t1_null_parity']:
        raise ValueError('unverified cloud receipt')
    folder=DATA/'processed/dati_transfer_2026-10-08_01a11c34/t2_r1'
    if sha(folder/'t2_consumption.json')!=sha(receipt_path):raise ValueError('downloaded receipt differs')
    outputs={};diagnostics={}
    for context in ('A','B','C'):
        path=folder/'effects'/('effects_'+context+'.npz');expected=receipt['effects'][context]
        if path.stat().st_size!=expected['bytes'] or sha(path)!=expected['sha256']:
            raise ValueError('actual effect file differs: '+context)
        old=DATA/'processed/dati_transfer_2026-10-08_01a11c34/t1_r1/effects'/path.name
        with np.load(path,allow_pickle=False) as z,np.load(old,allow_pickle=False) as t1:
            value=z['lfc'];mask=z['observed']
            if value.shape!=(300,18533) or value.dtype!=np.float32 or mask.shape!=value.shape or mask.dtype!=bool:
                raise ValueError('effect contract differs')
            for key in ('genes','targets','observed'):
                if not np.array_equal(z[key],t1[key]):raise ValueError('T2 changed axis or coverage')
            if not np.isfinite(value).all() or (value[~mask]!=0).any():raise ValueError('invalid effect missingness')
            delta=value.astype(np.float64)-t1['lfc']
            norm=float(np.linalg.norm(delta));maximum=float(np.abs(delta).max())
            if not np.isclose(norm,receipt['deltas_vs_T1'][context]['l2'],rtol=1e-12,atol=1e-12):
                raise ValueError('difference receipt differs')
            diagnostics[context]=dict(shape=list(value.shape),observed=int(mask.sum()),missing=int((~mask).sum()),
                l2_vs_T1=norm,max_abs_vs_T1=maximum,rms=float(np.sqrt(np.mean(value.astype(np.float64)**2))))
        outputs[context]=pin(path)
    write_new(HERE/'candidate_t2_r1.json',dict(utc=now(),name='dati-transfer-t2-01a11c34-r1',
        status='frozen effect candidate; independent comparative validation pending',
        effects=outputs,diagnostics=diagnostics,receipt=pin(receipt_path),cloud_verification=pin(proof),
        parent_release=pin(HERE/'release_t1_r1.json'),common_release=pin(HERE/'common_release_production_r1.json'),
        fold_common_release=pin(HERE/'common_release_T_r1.json'),
        units='natural-log fold change',amplitude_applied=1.576,cis_applied=True,emitter_applied=False,
        context_dependence='A/B/C effects are identical; this transfer does not learn a context-specific response',
        actual_output_arrays_independently_rehashed=True,t1_null_parity=True,claims_predictive_improvement=False,
        claims_complete_corpus=False,cellular_training=False,cell_generation=False,VCC_submission=False))
    print(json.dumps(dict(outputs=outputs,diagnostics=diagnostics)))


if __name__=='__main__':main()
