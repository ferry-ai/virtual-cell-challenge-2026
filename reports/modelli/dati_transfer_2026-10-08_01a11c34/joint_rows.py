"""Explicit biological pooling over lazy pinned count banks, before shrinkage."""
from collections import defaultdict
import numpy as np
import pandas as pd
from fold_bank import BIO

UNITS={
    'cd4':{f'D{d}_{c}' for d in range(1,5) for c in ('Rest','Stim8hr','Stim48hr')},
    'h1':{'h1_train','h1_val'},
    'k562_gwps':{'k562_gwps_a','k562_gwps_b'},
    'hipsci_targeted_19':{'hipsci_targeted_19'},
}
UNITS.update({f'cd4_{c}':{f'D{d}_{c}' for d in range(1,5)} for c in ('Rest','Stim8hr','Stim48hr')})


class PooledArray:
    """Only requested logical rows are materialized; no full-bank concatenate."""
    def __init__(self, banks, refs, field, genes):
        self.banks,self.refs,self.field=banks,refs,field
        self.shape=(len(refs),genes);self.ndim=2;self.dtype=np.dtype(bool if field=='masks' else 'float64')

    def __getitem__(self, indices):
        indices=np.asarray(indices,dtype=int).reshape(-1)
        result=np.empty((len(indices),self.shape[1]),dtype=self.dtype)
        for out,index in enumerate(indices):
            refs=self.refs[index]
            mask=np.ones(self.shape[1],bool)
            for unit,row in refs:mask &= self.banks[unit]['masks'][row]
            if self.field=='masks':result[out]=mask
            else:
                value=np.zeros(self.shape[1],dtype=np.float64)
                for unit,row in refs:value += self.banks[unit]['counts'][row]
                value[~mask]=0.;result[out]=value
        return result


def joint(policy,banks,genes):
    """Banks contain already fold-selected frames plus mmap counts and masks.

    No missing donor is invented. For H1 only, an identical shared control is
    retained once. K562's a/b are disjoint storage blocks and their counts add.
    CD4 and HIPSCI retain donor identity and pool donor effects in the estimator.
    """
    if policy not in UNITS or set(banks)!=UNITS[policy]:raise ValueError('explicit complete pooling units required')
    groups=defaultdict(list)
    for unit,b in banks.items():
        for row in b['frame'].to_dict('records'):
            item=dict(row)
            if policy.startswith('cd4'):item['context']='CD4T '+item['condition']
            elif policy=='hipsci_targeted_19':item['context']='HIPSCI iPSC '+item['condition']
            elif policy=='h1':
                item['study']='h1_vcc2025'
                for column in ('donor_or_clone','condition','chemistry'):
                    if str(item[column]).startswith('UNREPORTED@'):item[column]='UNREPORTED@h1_vcc2025'
            groups[tuple(item[k] for k in (*BIO,'target'))].append((unit,row,item))
    frames=[];refs=[];duplicates=0
    for key,items in groups.items():
        use=items
        if len(items)>1 and policy=='h1':
            if items[0][2]['target']!='non-targeting':raise ValueError('overlapping H1 perturbations')
            u0,r0,_=items[0]
            for unit,row,_ in items[1:]:
                if row['n']!=r0['n'] or not np.array_equal(banks[unit]['counts'][row['bank_row']],banks[u0]['counts'][r0['bank_row']]) or not np.array_equal(banks[unit]['masks'][row['bank_row']],banks[u0]['masks'][r0['bank_row']]):
                    raise ValueError('H1 controls are not identical')
            duplicates+=len(items)-1;use=items[:1]
        elif len(items)>1 and policy!='k562_gwps':raise ValueError('unexplained duplicate biological row')
        record=dict(use[0][2]);record.update(n=sum(r['n'] for _,r,_ in use),bank_row=len(refs),
            origin=[dict(unit=u,row=int(r['bank_row']),cells=int(r['n'])) for u,r,_ in use])
        frames.append(record);refs.append([(u,int(r['bank_row'])) for u,r,_ in use])
    frame=pd.DataFrame(frames)
    return frame,PooledArray(banks,refs,'counts',len(genes)),PooledArray(banks,refs,'masks',len(genes)),dict(
        policy=policy,units=sorted(banks),duplicate_control_rows_dropped=duplicates,
        pooling_before_shrink=True,full_bank_concatenated=False,
        selected_cells_before_dedup=sum(int(b['frame'].n.sum()) for b in banks.values()),
        admitted_cells_after_dedup=int(frame.n.sum()) if not frame.empty else 0)
