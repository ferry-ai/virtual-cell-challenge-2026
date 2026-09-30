"""Input-only Stack support/depth audit on the two prepared control populations.

Never reads perturbation outcomes or changes a model input, prediction, or gate.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp
import stack_pilot as pilot


def collisions(genes):
    groups=defaultdict(list)
    for g in genes:
        groups[str(g).upper()].append(str(g))
    return {k:v for k,v in groups.items() if len(v)>1}


def population(x, genes, other, model, exact, upper, name):
    x=sp.csr_matrix(x); genes=np.asarray(genes,dtype=str)
    keep=np.array([g in exact for g in genes]); folded=np.array([g.upper() in upper for g in genes])
    totals=np.asarray(x.sum(axis=1,dtype=np.float64)).ravel()
    if np.any(totals<=0):
        raise ValueError('Zero-library control cannot define a lost fraction')
    retained=np.asarray(x[:,keep].sum(axis=1,dtype=np.float64)).ravel()
    folded_retained=np.asarray(x[:,folded].sum(axis=1,dtype=np.float64)).ravel()
    loss=(totals-retained)/totals; upper_loss=(totals-folded_retained)/totals
    sums=np.asarray(x.sum(axis=0,dtype=np.float64)).ravel()
    detected=np.asarray((x>0).sum(axis=0)).ravel()
    order=np.flatnonzero(~keep)
    order=order[np.argsort(-sums[order],kind='stable')]
    excluded=[{'gene':str(genes[i]),'counts':int(sums[i]),'fraction_of_all_counts':float(sums[i]/totals.sum()),
               'control_cells_detected':int(detected[i]),'missing_model_exact':genes[i] not in model,
               'missing_other_axis_exact':genes[i] not in other,
               'recoverable_by_uppercase':bool(folded[i])} for i in order[:20]]
    quantiles=[0,.01,.05,.25,.5,.75,.95,.99,1]
    result={'cells':x.shape[0],'measured_genes':x.shape[1],'total_counts':int(totals.sum()),
        'retained_counts_exact':int(retained.sum()),'lost_fraction_aggregate_exact':float(1-retained.sum()/totals.sum()),
        'lost_fraction_aggregate_uppercase':float(1-folded_retained.sum()/totals.sum()),
        'recoverable_fraction_of_all_counts':float((folded_retained-retained).sum()/totals.sum()),
        'lost_fraction_per_cell_quantiles':dict(zip(map(str,quantiles),map(float,np.quantile(loss,quantiles)))),
        'upper_loss_per_cell_quantiles':dict(zip(map(str,quantiles),map(float,np.quantile(upper_loss,quantiles)))),
        'top20_excluded_genes':excluded,'uppercase_collisions':collisions(genes),
        'library_size_quantiles_before':dict(zip(map(str,quantiles),map(float,np.quantile(totals,quantiles)))),
        'library_size_quantiles_after_exact':dict(zip(map(str,quantiles),map(float,np.quantile(retained,quantiles))))}
    per_cell=pd.DataFrame({'population':name,'control_row':np.arange(len(totals)),
        'library_total':totals,'retained_counts_exact':retained,'lost_fraction_exact':loss,
        'retained_counts_uppercase':folded_retained,'lost_fraction_uppercase':upper_loss})
    return result,per_cell


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('bundle','genelist','inference-manifest','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    inference=json.loads(args.inference_manifest.read_text(encoding='utf-8'))
    if inference['genelist_sha256']!=pilot.GENELIST_SHA or inference['checkpoint_sha256']!=pilot.CHECKPOINT_SHA:
        raise ValueError('Derived gene list lacks pinned source provenance')
    with args.genelist.open('rb') as f:
        model_list=[str(g) for g in pilot.GeneListUnpickler(f).load()]
    model=set(model_list)
    if len(model_list)!=15012 or len(model)!=15012:
        raise ValueError('Unexpected Stack gene list')
    selected=['bundle.json','source_00.h5ad','destination_controls.h5ad']
    with tarfile.open(args.bundle,'r:gz') as archive, tempfile.TemporaryDirectory() as tmp:
        directory=Path(tmp)
        for name in selected:
            found=[m for m in archive.getmembers() if PurePosixPath(m.name).name==name]
            if len(found)!=1 or not found[0].isfile():
                raise ValueError(f'Ambiguous or absent control input: {name}')
            with archive.extractfile(found[0]) as source,(directory/name).open('xb') as dest:
                shutil.copyfileobj(source,dest)
        bundle=json.loads((directory/'bundle.json').read_text(encoding='utf-8'))
        hashes={name:pilot.sha(directory/name) for name in selected}
        for name in selected[1:]:
            if hashes[name]!=bundle['files'][name]:
                raise ValueError('Prepared controls differ from original bundle manifest')
        source=ad.read_h5ad(directory/'source_00.h5ad')
        dest=ad.read_h5ad(directory/'destination_controls.h5ad')
        for obj,n in ((source,512),(dest,2000)):
            if obj.n_obs!=n or set(obj.obs.gene.astype(str))!={pilot.CONTROL}:
                raise ValueError('Unexpected cells or perturbations in control-only diagnostic')
            if not obj.var_names.is_unique:
                raise ValueError('Prepared response axis is not unique')
        sg,dg=set(source.var_names),set(dest.var_names)
        exact=sg&dg&model
        upper={g.upper() for g in sg}&{g.upper() for g in dg}&{g.upper() for g in model}
        measurements={}; cells=[]
        for name,obj,other in [('K562_source',source,dg),('HepG2_destination',dest,sg)]:
            record,per_cell=population(obj.X,obj.var_names,other,model,exact,upper,name)
            measurements[name]=record; cells.append(per_cell)
        result={'created_utc':datetime.now(timezone.utc).isoformat(),
            'claim_type':'Measured input-only diagnostic, no outcomes or prediction changes',
            'targets_read':False,'exact_shared_genes':len(exact),'uppercase_shared_genes':len(upper),
            'uppercase_additional_symbols':sorted(upper-{g.upper() for g in exact}),
            'model_not_uppercase':[g for g in model_list if g!=g.upper()],
            'model_uppercase_collisions':collisions(model_list),'control_populations':measurements,
            'extracted_control_sha256':hashes,'original_inference_provenance':{
                k:inference[k] for k in ['bundle_sha256','adapter_sha256','checkpoint_sha256','genelist_sha256']},
            'inputs':{str(p):{'bytes':p.stat().st_size,'sha256':pilot.sha(p)} for p in
                      [args.bundle,args.genelist,args.inference_manifest]},'script_sha256':pilot.sha(__file__)}
    args.out.mkdir(parents=True)
    pilot.write_json(args.out/'analysis.json',result)
    pd.concat(cells,ignore_index=True).to_csv(args.out/'per_control_cell.csv',index=False)
    print(json.dumps({'out':str(args.out),'exact_shared':len(exact),'uppercase_shared':len(upper),
        'losses':{k:{key:v[key] for key in ['lost_fraction_aggregate_exact','lost_fraction_aggregate_uppercase',
                        'recoverable_fraction_of_all_counts']} for k,v in measurements.items()}},indent=2))


if __name__=='__main__':
    main()
