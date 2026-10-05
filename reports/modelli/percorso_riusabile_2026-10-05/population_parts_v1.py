"""Read complete partition unions with controls resolved across BIO/target parts.

Keeps only one population matrix plus matched control vectors in memory. Bank
metadata are checked first; excluded groups never open population matrices.
"""
import json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from sample_reader import BIO, sha
from population_reader import PopulationReader


class PopulationParts:
    def __init__(self, parts, *, held_groups=(), hidden_targets=()):
        self.held=set(held_groups); self.hidden=set(hidden_targets)
        self.parts=[]; self.controls={}; self.control_cache={}
        for root, digest in parts:
            r=PopulationReader.__new__(PopulationReader)
            r.root=Path(root).resolve(); r.receipt_sha256=digest; r.verified=set()
            if sha(r.root/'complete.json')!=digest: raise ValueError('bank receipt changed')
            r.receipt=json.loads((r.root/'complete.json').read_text())
            if not r.receipt['complete']: raise ValueError('incomplete bank')
            r.verify('rows.csv'); r.rows=pd.read_csv(r.root/'rows.csv',keep_default_na=False)
            if not {*BIO,'target','line_group','n'}.issubset(r.rows.columns): raise ValueError('bank identity missing')
            if len(r.rows)!=r.receipt['rows'] or int(r.rows.n.sum())!=r.receipt['cells_used']:
                raise ValueError('bank population coverage differs')
            r.held=self.held; r.hidden=self.hidden
            self.parts.append(r)
        proofs=[r.receipt.get('partition') for r in self.parts]
        if any(proofs):
            if not all(proofs): raise ValueError('mixed partition/unpartitioned banks')
            n=proofs[0]['parts']
            if len(proofs)!=n or {p['part'] for p in proofs}!=set(range(n)):
                raise ValueError('incomplete partition union')
            for field in ('all_keys_sha256','global_rows','global_cells','parts','method'):
                if len({p[field] for p in proofs})!=1: raise ValueError('partition union identity differs')
            if (sum(r.receipt['rows'] for r in self.parts)!=proofs[0]['global_rows'] or
                sum(r.receipt['cells_in'] for r in self.parts)!=proofs[0]['global_cells']):
                raise ValueError('partition union coverage differs')
        elif len(self.parts)!=1: raise ValueError('unpartitioned unit must have one bank')
        if len({r.receipt['source_verification'] for r in self.parts})!=1:
            raise ValueError('bank source identity differs')
        keys=set()
        for pi,r in enumerate(self.parts):
            for i,row in r.rows.iterrows():
                key=tuple(str(row[c]) for c in BIO); identity=(*key,str(row.target))
                if identity in keys: raise ValueError('duplicate BIO/target across parts')
                keys.add(identity)
                if row.target=='NTC' and row.line_group not in self.held:
                    self.controls[key]=(pi,i)
            allowed=~r.rows.line_group.isin(self.held)&~r.rows.target.isin(self.hidden|{'NTC'})
            r.target_rows=r.rows.index[allowed].to_numpy()
        if any(proofs):
            digest=hashlib.sha256(json.dumps(sorted(keys),separators=(',',':')).encode()).hexdigest()
            if digest!=proofs[0]['all_keys_sha256']: raise ValueError('global BIO/target keys changed')
            for r in self.parts:
                p=r.receipt['partition']
                actual=[tuple(str(row[c]) for c in (*BIO,'target')) for _,row in r.rows.iterrows()]
                if actual!=sorted(keys)[p['part']::p['parts']]: raise ValueError('row partition differs')
        for r in self.parts:
            for i in r.target_rows:
                row=r.rows.iloc[i]; key=tuple(str(row[c]) for c in BIO)
                if key not in self.controls: raise ValueError('context lacks matched controls')
                pi,ci=self.controls[key]
                if row.n<=0 or self.parts[pi].rows.iloc[ci].n<=0:
                    raise ValueError('zero admitted population: resolve QC before fit')

    def arrays(self,r):
        r.verify('mean_proportion.npz'); r.verify('mask.npz')
        with np.load(r.root/'mean_proportion.npz',allow_pickle=False) as z: mean=z['value']
        with np.load(r.root/'mask.npz',allow_pickle=False) as z: mask=z['value']
        if mean.shape!=mask.shape or mean.shape[0]!=len(r.rows) or mask.dtype!=bool:
            raise ValueError('population/mask axes differ')
        return mean,mask

    def batches(self,batch_size=64):
        if batch_size<=0: raise ValueError('invalid batch size')
        needed={tuple(str(r.rows.iloc[i][c]) for c in BIO) for r in self.parts for i in r.target_rows}
        for pi,r in enumerate(self.parts):
            selected=[(key,ci) for key,(p,ci) in self.controls.items() if p==pi and key in needed]
            if not selected: continue
            mean,mask=self.arrays(r); r.verify('sampled_controls.npz')
            with np.load(r.root/'sampled_controls.npz',allow_pickle=False) as z:
                for key,ci in selected:
                    self.control_cache[key]=(mean[ci].copy(),mask[ci].copy(),z[str(ci)].copy(),int(r.rows.iloc[ci].n))
            del mean,mask
        for pi,r in enumerate(self.parts):
            if not len(r.target_rows): continue
            mean,mask=self.arrays(r)
            for at in range(0,len(r.target_rows),batch_size):
                ix=r.target_rows[at:at+batch_size]; meta=r.rows.iloc[ix].reset_index(drop=True)
                controls=[self.control_cache[tuple(str(row[c]) for c in BIO)] for _,row in meta.iterrows()]
                y=mean[ix]; b=np.stack([v[0] for v in controls]); m=mask[ix]
                if not np.array_equal(m,np.stack([v[1] for v in controls])): raise ValueError('target/control masks differ')
                if (not np.isfinite(y).all() or not np.isfinite(b).all() or (y<0).any() or (b<0).any()
                    or not np.allclose(y.sum(1),1,atol=1e-5) or not np.allclose(b.sum(1),1,atol=1e-5)
                    or (y[~m]!=0).any() or (b[~m]!=0).any()): raise ValueError('invalid population proportions')
                yield {'part':pi,'bank_rows':ix,'metadata':meta,'truth_mean':y,'control_mean':b,
                    'sampled_control_mean_64':np.stack([v[2] for v in controls]),'mask':m,
                    'cells_target':meta.n.to_numpy(),'cells_control':np.array([v[3] for v in controls]),
                    'bank_receipt_sha256':r.receipt_sha256}
            del mean,mask

    def require_sample_link(self,part,sample_reader):
        self.parts[part].require_sample_link(sample_reader)
