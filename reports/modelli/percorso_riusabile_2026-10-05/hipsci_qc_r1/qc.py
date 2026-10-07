"""Diagnostic own-transcript effects; never select donors or change model weights."""
import numpy as np
import pandas as pd
import estimator

def diagnose(counts, rows, genes, mask, panel):
    x=np.asarray(counts,dtype=np.float64)[:,mask]
    measured=np.asarray(genes)[mask]
    obs=pd.DataFrame(dict(target=rows.target.replace({'NTC':'non-targeting'}),
        donor=rows.donor_or_clone,condition=rows.condition,n_cells=rows.n))
    targets=sorted(set(rows.target)-{'NTC'})
    result=estimator.effects_from_pseudobulk(x,obs,measured,targets=targets,condition=None,**estimator.CALL)
    gene_index={g:i for i,g in enumerate(measured)}
    derived_index={g:i for i,g in enumerate(result['targets'])}
    records=[]
    for target in targets:
        record=dict(target=target,in_frozen_panel=target in panel,
                    cells=int(rows.loc[rows.target==target,'n'].sum()),state='below_min_cells')
        if target in derived_index:
            if target not in gene_index:
                record['state']='own_transcript_not_measured'
            else:
                i,j=derived_index[target],gene_index[target]
                if result['control_mean'][j]<1e-6:
                    record['state']='own_transcript_control_fraction_below_original_mask'
                elif not np.isfinite(result['raw'][i,j]):
                    record['state']='own_transcript_expected_count_below_original_guard'
                else:
                    record.update(state='measured',raw=float(result['raw'][i,j]),
                                  shrunk=float(result['shrunk'][i,j]),se=float(result['se'][i,j]))
        records.append(record)
    return records

def summarize(records):
    from collections import Counter
    observed=[r['raw'] for r in records if r['state']=='measured']
    panel=[r['raw'] for r in records if r['state']=='measured' and r['in_frozen_panel']]
    return dict(states=dict(Counter(r['state'] for r in records)),
        measured_own_gene=len(observed),median_own_raw=float(np.median(observed)) if observed else None,
        q25=float(np.quantile(observed,.25)) if observed else None,
        q75=float(np.quantile(observed,.75)) if observed else None,
        fraction_negative=float(np.mean(np.asarray(observed)<0)) if observed else None,
        panel_measured=len(panel),panel_median_raw=float(np.median(panel)) if panel else None,
        automatic_admission=False,automatic_context_exclusion=False)
