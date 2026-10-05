"""Read full-population supervision and matched controls from persistent bank units.

Arrays are opened only after metadata-based fold filtering. No pseudocount, learned
transform, gene renaming or pooling of biological contexts is performed here.
Use on cloud for real banks; each unit decompresses its mean/mask arrays once.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sample_reader import BIO, sha


class PopulationReader:
    def __init__(self, root, receipt_sha256, *, held_groups=(), hidden_targets=()):
        self.root = Path(root).resolve()
        self.held = set(held_groups)
        self.hidden = set(hidden_targets)
        self.receipt_sha256 = receipt_sha256
        if sha(self.root/'complete.json') != receipt_sha256:
            raise ValueError('bank receipt changed')
        self.receipt = json.loads((self.root/'complete.json').read_text())
        if not self.receipt['complete']:
            raise ValueError('incomplete bank')
        self.verified = set()
        self.verify('rows.csv')
        self.rows = pd.read_csv(self.root/'rows.csv',keep_default_na=False)
        if len(self.rows)!=self.receipt['rows'] or int(self.rows.n.sum())!=self.receipt['cells_used']:
            raise ValueError('bank row/cell coverage changed')
        required = {*BIO,'line_group','target','n'}
        if not required.issubset(self.rows.columns):
            raise ValueError('missing bank identity')
        keys = [tuple(str(r[c]) for c in BIO) for _,r in self.rows.iterrows()]
        if self.rows.duplicated([*BIO,'target']).any():
            raise ValueError('duplicate context/target')
        control = {keys[i]:i for i,r in self.rows.iterrows() if r.target=='NTC'}
        allowed = ~self.rows.line_group.isin(self.held) & ~self.rows.target.isin(self.hidden|{'NTC'})
        self.target_rows = self.rows.index[allowed].to_numpy()
        self.control_rows = []
        for i in self.target_rows:
            if keys[i] not in control:
                raise ValueError('context has no matched controls: '+str(keys[i]))
            ci=control[keys[i]]
            if self.rows.iloc[i].n<=0 or self.rows.iloc[ci].n<=0:
                raise ValueError('zero admitted population: resolve QC before training')
            self.control_rows.append(ci)
        self.control_rows = np.array(self.control_rows,dtype=int)
        self.mean = self.mask = self.sampled_controls = None

    def verify(self,name):
        if name in self.verified:
            return
        p=(self.root/name).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError('unsafe bank path')
        expected=self.receipt['files'][name]
        if p.stat().st_size!=expected['bytes'] or sha(p)!=expected['sha256']:
            raise ValueError('bank artifact changed: '+name)
        self.verified.add(name)

    def batches(self,batch_size=64):
        if batch_size<=0:
            raise ValueError('invalid batch size')
        if not len(self.target_rows):
            return
        if self.mean is None:
            for name in ('mean_proportion.npz','mask.npz','sampled_controls.npz'):
                self.verify(name)
            with np.load(self.root/'mean_proportion.npz',allow_pickle=False) as z:
                self.mean=z['value']
            with np.load(self.root/'mask.npz',allow_pickle=False) as z:
                self.mask=z['value']
            with np.load(self.root/'sampled_controls.npz',allow_pickle=False) as z:
                self.sampled_controls={k:z[k] for k in z.files}
            if self.mean.shape!=self.mask.shape or self.mean.shape[0]!=len(self.rows) or self.mask.dtype!=bool:
                raise ValueError('population/mask axis mismatch')
        for start in range(0,len(self.target_rows),batch_size):
            ti=self.target_rows[start:start+batch_size];ci=self.control_rows[start:start+batch_size]
            mask=self.mask[ti]
            if not np.array_equal(mask,self.mask[ci]):
                raise ValueError('target/control measurement axes differ')
            y=self.mean[ti];b=self.mean[ci]
            if (not np.isfinite(y).all() or not np.isfinite(b).all() or (y<0).any() or (b<0).any()
                or not np.allclose(y.sum(1),1,atol=1e-5) or not np.allclose(b.sum(1),1,atol=1e-5)
                or (y[~mask]!=0).any() or (b[~mask]!=0).any()):
                raise ValueError('invalid full-population proportions')
            sampled=np.stack([self.sampled_controls[str(i)] for i in ci])
            if sampled.shape!=b.shape or not np.isfinite(sampled).all() or (sampled<0).any():
                raise ValueError('invalid sampled control mean')
            yield {'bank_rows':ti,'control_rows':ci,'metadata':self.rows.iloc[ti].reset_index(drop=True),
                   'truth_mean':y,'control_mean':b,'sampled_control_mean_64':sampled,
                   'mask':mask,'cells_target':self.rows.iloc[ti].n.to_numpy(),
                   'cells_control':self.rows.iloc[ci].n.to_numpy(),
                   'positive_truth_outside_control_support':((y>0)&(b==0)&mask).sum(1),
                   'bank_receipt_sha256':self.receipt_sha256}

    def require_sample_link(self, sample_reader):
        if self.held!=sample_reader.held or self.hidden!=sample_reader.hidden:
            raise ValueError('population/sample validation splits differ')
        if sample_reader.receipt['bank_receipt_sha256']!=self.receipt_sha256:
            raise ValueError('sample cells come from a different population bank')
        if sample_reader.receipt['files']['mask.npz']['sha256']!=self.receipt['files']['mask.npz']['sha256']:
            raise ValueError('population/sample masks differ')
        if not sample_reader.rows.equals(self.rows):
            raise ValueError('sample bank-row identities differ')
