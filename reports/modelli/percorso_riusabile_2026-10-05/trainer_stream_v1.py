"""Actual optimisation over locked bank populations and materialized cell samples.

The caller supplies fold-frozen, hash-checked transfer features and hierarchical
weights. No anchors are learned from the consumed labels here. This integration
does not declare the still unresolved global catalogue ready or launch a pilot.
"""
import json, hashlib
import numpy as np
import torch
from sample_reader import SampleReader, BIO, sha
from population_parts_v1 import PopulationParts
from release_lock import resolve
from training_contract import validate_manifest, validate_exposure


class StreamFit:
    def __init__(self, manifest, catalogue_ids, lock_path, lock_sha256, mounts,
                 *, held_groups=(), hidden_targets=(), level=64):
        self.contexts=validate_manifest(manifest,catalogue_ids)
        self.held=tuple(held_groups); self.hidden=tuple(hidden_targets)
        self.identity={'lock_sha256':lock_sha256,'held_groups':sorted(self.held),
                       'hidden_targets':sorted(self.hidden),'level':level,
                       'manifest_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
        self.exposure={}; self.units={}
        for unit,parts in mounts.items():
            bank_parts=[]; readers=[]
            for part in parts:
                root=resolve(lock_path,lock_sha256,part['lock_unit'],'bank',part['bank_root'])
                bank_sha=sha(root/'complete.json'); bank_parts.append((root,bank_sha))
                local=[]
                for s in part['samples']:
                    sr=resolve(lock_path,lock_sha256,s['lock_unit'],'samples',s['root'])
                    local.append(SampleReader(sr,sha(sr/'complete.json'),bank_sha,level=level,
                                              held_groups=self.held,hidden_targets=self.hidden))
                if not local: raise ValueError('population has no sample consumer')
                readers.append(local)
            population=PopulationParts(bank_parts,held_groups=self.held,hidden_targets=self.hidden)
            for pi,local in enumerate(readers):
                for reader in local: population.require_sample_link(pi,reader)
            self.units[unit]=(population,readers)
        planned={c['context_id'] for c in self.contexts if c['role']=='supervision' and c['group'] not in self.held}
        mounted={json.dumps([str(row[c]) for c in BIO],separators=(',',':'))
                 for population,_ in self.units.values() for r in population.parts
                 for _,row in r.rows.iloc[r.target_rows].iterrows()}
        if mounted!=planned: raise ValueError('mounted supervision contexts differ from complete manifest')

    def record(self,row, *, cell_key=None, stratum=None, control=False, weight=0):
        ctx=json.dumps([str(row[c]) for c in BIO],separators=(',',':'))
        e=self.exposure.setdefault(ctx,{'context_id':ctx,'target_ids':set(),'stratum_ids':set(),
                  'cells':set(),'controls':set(),'loss_weight_sum':0.,'reads':0})
        e['reads']+=1
        if control:
            if cell_key is not None: e['controls'].add(cell_key)
        else:
            e['target_ids'].add(str(row.target))
            if stratum is not None: e['stratum_ids'].add(json.dumps(stratum,separators=(',',':')))
            if cell_key is not None: e['cells'].add(cell_key)
            e['loss_weight_sum']+=float(weight)

    def fit_epoch(self, model, optimizer, features, row_weights, *, batch_size=32, cell_weight=1.):
        """Features verifies frozen fold/axis/anchor lineage before returning tensors.

        feature.verify(identity) MUST check its own pinned receipt/hash and disjoint
        fit source groups/hidden targets; callback failure aborts before any fit.
        Features(unit,part,bank_rows,metadata,basal,mask) -> anchor,target,context.
        Returned tensors use the exact bank gene order; no positional truncation.
        """
        features.verify(self.identity)
        device=next(model.parameters()).device
        tensor=lambda x:torch.as_tensor(np.asarray(x),dtype=torch.float32,device=device)
        def step(unit,pi,ix,meta,basal,truth,mask,weights):
            anchor,target,context=features(unit,pi,ix,meta,basal,mask)
            if np.shape(anchor)!=np.shape(basal): raise ValueError('anchor/bank gene axis differs')
            a,t,c=tensor(anchor),tensor(target),tensor(context)
            m=torch.as_tensor(mask,dtype=torch.bool,device=device)
            b,y=tensor(basal),tensor(truth); w=tensor(weights)
            if (w.shape!=y.shape[:1] or not torch.isfinite(w).all() or (w<=0).any()):
                raise ValueError('invalid actual hierarchical weights')
            if (not torch.isfinite(b).all() or not torch.isfinite(y).all() or (b<0).any()
                or (y<0).any() or (y.sum(-1)<=0).any() or (b.sum(-1)<=0).any()
                or ((b==0)&(y>0)&m).any()): raise ValueError('resolve baseline support/QC before fit')
            residual=model(a,t,c,m); effect=a+residual
            support=m&(b>0)
            logits=torch.where(support,torch.log(b.clamp_min(torch.finfo(b.dtype).tiny))+effect,-torch.inf)
            logp=torch.log_softmax(logits,-1)
            y=torch.where(m,y,0); y=y/y.sum(-1,keepdim=True)
            per=-(y*torch.where(support,logp,0)).sum(-1)
            loss=(w*per).mean()
            if not torch.isfinite(loss): raise FloatingPointError('nonfinite actual loss')
            optimizer.zero_grad(set_to_none=True); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),1.); optimizer.step()
        for unit,(population,readers) in self.units.items():
            for batch in population.batches(batch_size):
                meta=batch['metadata']; w=np.asarray(row_weights(meta),float)
                step(unit,batch['part'],batch['bank_rows'],meta,batch['control_mean'],
                     batch['truth_mean'],batch['mask'],w)
                for (_,row),weight in zip(meta.iterrows(),w): self.record(row,weight=weight)
            for pi,local in enumerate(readers):
                for reader in local:
                    for batch in reader.batches(batch_size):
                        meta=batch['metadata']; target=(meta.target!='NTC').to_numpy()
                        weights=np.zeros(len(meta))
                        if target.any():
                            y=batch['counts'][target].toarray().astype(np.float32)
                            mask=batch['mask'][target]
                            if (not np.isfinite(y).all() or (y<0).any() or (y[~mask]!=0).any()
                                or (y.sum(1)<=0).any()): raise ValueError('invalid consumed counts')
                            kept=meta.loc[target].reset_index(drop=True)
                            b=np.stack([population.control_cache[tuple(str(row[c]) for c in BIO)][0]
                                        for _,row in kept.iterrows()])
                            weights[target]=cell_weight*np.asarray(row_weights(kept))/(batch['inclusion_probability'][target]*kept.n.to_numpy())
                            step(unit,pi,batch['bank_rows'][target],kept,b,y,mask,weights[target])
                        reader.acknowledge(batch['batch_id'],weights)
                        for j,(_,row) in enumerate(meta.iterrows()):
                            # Exact source cell key, namespaced by unit; repeated epochs/resume do not inflate coverage.
                            self.record(row,cell_key=unit+'|'+str(batch['cell_keys'][j]),stratum=batch['strata'][j],
                                        control=not target[j],weight=weights[j])

    def checkpoint(self):
        return {'identity':self.identity,'exposure':{k:{n:sorted(v) if isinstance(v,set) else v for n,v in e.items()}
                for k,e in self.exposure.items()}}

    def restore(self,checkpoint):
        if checkpoint['identity']!=self.identity: raise ValueError('resume release/split differs')
        self.exposure={k:{n:set(v) if n in {'target_ids','stratum_ids','cells','controls'} else v for n,v in e.items()}
                       for k,e in checkpoint['exposure'].items()}

    def accept(self):
        actual=[{**e,'target_ids':sorted(e['target_ids']),'stratum_ids':sorted(e['stratum_ids']),
                 'cells_seen_unique':len(e['cells']),'control_cells_seen':len(e['controls'])}
                for e in self.exposure.values()]
        validate_exposure(self.contexts,actual,held_groups=self.held,hidden_targets=self.hidden)
        return self.checkpoint()
