"""Reusable streaming reader for materialized CD4 samples; no fit or transformation.

Receipts distinguish physical decompression, yielded cells and explicit loss use.
An excluded line returns before opening matrices. Hidden targets are never yielded
or included in statistics; compressed source shards can contain excluded rows.
"""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import scipy.sparse as sp

BIO = ('study','context','donor_or_clone','condition','modality','chemistry')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):
            h.update(b)
    return h.hexdigest()


class SampleReader:
    def __init__(self, root, receipt_sha256, bank_receipt_sha256, *, level=64,
                 held_groups=(), hidden_targets=()):
        self.root = Path(root).resolve()
        if level not in (32,64,128):
            raise ValueError('unsupported nested level')
        self.level = str(level)
        self.held = set(held_groups)
        self.hidden = set(hidden_targets)
        self.verified = set()
        self.seen = set()
        self.loss_seen = set()
        self.yielded = Counter()
        self.loss_mass = Counter()
        self.storage_rows = 0
        self.target_seen = set()
        self.strata_seen = set()
        self.pending = {}
        self.next_batch = 0
        path = self.root/'complete.json'
        if sha(path) != receipt_sha256:
            raise ValueError('sample completion receipt changed')
        self.receipt = json.loads(path.read_text())
        if not self.receipt['complete'] or self.receipt['bank_receipt_sha256'] != bank_receipt_sha256:
            raise ValueError('sample/bank lineage mismatch')
        self.verify('bank_rows.csv')
        self.rows = pd.read_csv(self.root/'bank_rows.csv', keep_default_na=False)
        required = {*BIO,'line_group','target','n'}
        if not required.issubset(self.rows.columns):
            raise ValueError('missing biological identity columns')
        self.allowed = (~self.rows.line_group.isin(self.held) & ~self.rows.target.isin(self.hidden)).to_numpy()
        self.context_ids = [json.dumps([str(r[c]) for c in BIO],separators=(',',':')) for _,r in self.rows.iterrows()]
        self.expected_targets = {str(r.target) for _,r in self.rows[self.allowed].iterrows()}

    def verify(self, name):
        if name in self.verified:
            return
        path = (self.root/name).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('unsafe sample path')
        record = self.receipt['files'][name]
        if path.stat().st_size != record['bytes'] or sha(path) != record['sha256']:
            raise ValueError('sample artifact changed: '+name)
        self.verified.add(name)

    def batches(self, batch_size=64):
        if batch_size <= 0:
            raise ValueError('invalid batch size')
        if self.pending:
            raise ValueError('unacknowledged batches from previous iteration')
        if not self.allowed.any():
            return
        self.verify('mask.npz')
        with np.load(self.root/'mask.npz',allow_pickle=False) as z:
            masks = z['value']
        if masks.dtype != bool or masks.shape != (len(self.rows),self.receipt['genes']):
            raise ValueError('mask/gene-axis mismatch')
        for name in sorted(n for n in self.receipt['files'] if n.startswith('shard_') and n.endswith('.npz')):
            meta_name = name[:-4]+'.jsonl.gz'
            self.verify(meta_name)
            with gzip.open(self.root/meta_name,'rt',encoding='utf-8') as f:
                records = [json.loads(line) for line in f]
            if len(records) != self.receipt['files'][name]['cells']:
                raise ValueError('sample row count differs from manifest')
            selected = []
            for i,r in enumerate(records):
                row = r['bank_row']
                if not isinstance(row,int) or not 0 <= row < len(self.rows):
                    raise ValueError('sample points outside bank rows')
                if self.level in r['probabilities'] and self.allowed[row]:
                    if not 0 < r['probabilities'][self.level] <= 1:
                        raise ValueError('invalid inclusion probability')
                    selected.append(i)
            if not selected:
                continue
            self.verify(name)
            x = sp.load_npz(self.root/name)
            if x.shape != (len(records),self.receipt['genes']):
                raise ValueError('sample matrix shape mismatch')
            self.storage_rows += x.shape[0]
            for start in range(0,len(selected),batch_size):
                ix = selected[start:start+batch_size]
                rr = [records[i] for i in ix]
                bank_rows = np.array([r['bank_row'] for r in rr])
                cells = [(name,int(i)) for i in ix]
                context_ids = [self.context_ids[i] for i in bank_rows]
                targets = self.rows.iloc[bank_rows].target.astype(str).tolist()
                for cell,ctx,target,r in zip(cells,context_ids,targets,rr):
                    self.seen.add(cell)
                    self.yielded[ctx] += 1
                    self.target_seen.add(target)
                    self.strata_seen.add((ctx,target,tuple(r['stratum'])))
                batch_id = self.next_batch;self.next_batch += 1
                self.pending[batch_id] = (cells,context_ids,targets)
                yield {'batch_id':batch_id,'counts':x[ix], 'mask':masks[bank_rows],
                       'bank_rows':bank_rows,'metadata':self.rows.iloc[bank_rows].reset_index(drop=True),
                       'cell_keys':[r['cell_key'] for r in rr], 'strata':[r['stratum'] for r in rr],
                       'inclusion_probability':np.array([r['probabilities'][self.level] for r in rr])}
            del x,records

    def acknowledge(self, batch_id, loss_weights):
        """Call only AFTER actual loss consumption; None explicitly records no loss.

Controls can have zero loss weight while being consumed as context. The trainer
must also keep its separate receipt for control usage and context/target weights.
"""
        if batch_id not in self.pending:
            raise ValueError('unknown/already acknowledged batch')
        cells,contexts,targets = self.pending[batch_id]
        weights = np.zeros(len(cells)) if loss_weights is None else np.asarray(loss_weights,dtype=float)
        if weights.shape != (len(cells),) or not np.isfinite(weights).all() or (weights<0).any():
            raise ValueError('invalid actual loss weights')
        for cell,ctx,target,w in zip(cells,contexts,targets,weights):
            if w>0:
                self.loss_seen.add(cell)
                self.loss_mass[(ctx,target)] += float(w)
        del self.pending[batch_id]

    def exposure(self):
        return {'unit':self.receipt['unit'],'level':int(self.level),'held_groups':sorted(self.held),
                'hidden_targets':sorted(self.hidden),'physical_rows_decompressed':self.storage_rows,
                'unique_cells_yielded':len(self.seen),'unique_cells_with_loss':len(self.loss_seen),
                'targets_yielded':sorted(self.target_seen),'missing_targets':sorted(self.expected_targets-self.target_seen),
                'strata_yielded':len(self.strata_seen),'unacknowledged_batches':len(self.pending),
                'loss_mass':[{'context':c,'target':t,'weight':w} for (c,t),w in sorted(self.loss_mass.items())],
                'verified_files':sorted(self.verified),
                'complete_training_proven':False}
