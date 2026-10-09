"""Construct the four predeclared level-B arms without truth reads or refitting."""
import json
from pathlib import Path
import shutil
import numpy as np
from bank_input_bridge_v1 import digest,stage_exports


def arrays(base,native,generic,fallback,shuffled_rows,amplitude=1.576):
    for other in (native,generic,fallback):
        if any(not np.array_equal(base[k],other[k]) for k in ('targets','genes')):
            raise ValueError('four-arm axes differ')
    for item in (base,native,generic,fallback):
        if (item['lfc'].dtype!=np.float32 or item['observed'].dtype!=bool
                or not np.isfinite(item['lfc']).all() or np.any(item['lfc'][~item['observed']]!=0)):
            raise ValueError('invalid prediction values or mask')
    a,m=base['lfc'],base['observed'];b,n=native['lfc'],native['observed']
    fill=~m&n;expected=(b.astype(np.float64)*amplitude).astype(np.float32)
    f,fm=fallback['lfc'],fallback['observed']
    if (not np.array_equal(f[m],a[m]) or not np.array_equal(fm,m|fill)
            or (fill.any() and np.max(np.abs(f[fill]-expected[fill]))>1e-6)):
        raise ValueError('delivered fallback differs from frozen adapter')
    rows=np.flatnonzero(n.any(axis=1));donor=np.arange(len(a))
    donor[rows]=rows[shuffled_rows(rows.size)]
    if np.any(fill&~generic['observed']) or np.any(fill&~n[donor]):
        raise ValueError('matched-mask diagnostic has missing predictions')
    gf=(generic['lfc'].astype(np.float64)*amplitude).astype(np.float32)
    values={'T0':a,'E2f':f,'Generic':np.where(fill,gf,a),'Swapped':np.where(fill,expected[donor],a)}
    masks={name:m if name=='T0' else fm for name in values}
    changed=np.any((f!=a)|(fm!=m),axis=1)
    return values,masks,changed,donor


def materialize(native_effects,params,bundle,out):
    """Cloud only: verify approved transport, native T0, then derive two controls."""
    bundle=Path(bundle);out=Path(out);native_effects=Path(native_effects)
    files=params['private_exports'];authorization=json.loads((bundle/'transport_authorization.json').read_text())
    locators=json.loads((bundle/'private_locators.json').read_text())
    receipts=stage_exports(params['transport_plan_sha256'],files,authorization,locators,out.parent/'downloaded_exports')
    paths={r['sha256']:Path(r['path']) for r in receipts}
    base_path=native_effects/'T0.npz'
    if digest(base_path)!=params['reference_sha256']:raise ValueError('native T0 differs')
    def load(path):
        with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}
    by_label={item['label']:paths[item['sha256']] for item in files}
    base=load(base_path)
    import metrics
    values,masks,changed,donor=arrays(base,load(by_label['E2']),load(by_label['E2g']),load(by_label['E2f']),metrics.shuffled_rows)
    out.mkdir(exist_ok=False)
    shutil.copyfile(base_path,out/'T0.npz');shutil.copyfile(by_label['E2f'],out/'E2f.npz')
    for name in ('Generic','Swapped'):
        payload=dict(base,lfc=values[name],observed=masks[name]);np.savez_compressed(out/(name+'.npz'),**payload)
    pins={name:digest(out/(name+'.npz')) for name in values}
    receipt=dict(input_exports=receipts,reference_sha256=params['reference_sha256'],arms_sha256=pins,
        adapter_checked=True,mask_semantics='model-predicted pairs; no observed zeros manufactured',
        expected_filled_pairs=int((~base['observed']&masks['E2f']).sum()),
        changed_targets=[str(t) for t in base['targets'][changed]],donor_rows=donor.tolist(),
        truth_read=False,trained=False,amplitude=1.576,swap_seed=20261008)
    (out.parent/'four_arms_verified.json').write_text(json.dumps(receipt,indent=2))
    return pins,receipt['changed_targets']
