"""Bounded-memory all-target common effects; no panel-mean fallback."""
import hashlib
import heapq
import json
from pathlib import Path
import numpy as np


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(1<<20),b''):digest.update(block)
    return digest.hexdigest()


def hidden(target,split):
    return target in split['hidden_targets'] or (split['regime'] in {'T','J'} and
        int(hashlib.sha256(target.encode()).hexdigest(),16)%5==0)


def rows(chunks,genes,split,*,filter_hidden=False):
    """Yield sorted target rows, verifying a chunk before it contributes."""
    previous=None
    for entry in chunks:
        path=Path(entry['path'])
        if path.stat().st_size!=entry['bytes'] or sha(path)!=entry['sha256']:raise ValueError('chunk identity changed')
        with np.load(path,allow_pickle=False) as z:
            targets=z['targets'].astype(str).tolist()
            if 'genes' in z.files and z['genes'].astype(str).tolist()!=list(genes):raise ValueError('gene axis changed')
            values=z['shrunk'];cells=z['n_cells'];mask=z['mask'] if 'mask' in z.files else np.isfinite(values)
        if values.shape!=(len(targets),len(genes)) or mask.dtype!=bool or mask.shape!=values.shape or not np.array_equal(mask,np.isfinite(values)):
            raise ValueError('effect/mask contract changed')
        if len(cells)!=len(targets) or not np.isfinite(cells).all() or (cells<=0).any():raise ValueError('invalid reliability population')
        for i,target in enumerate(targets):
            if previous is not None and target<=previous:raise ValueError('targets are not strictly ordered')
            previous=target
            if hidden(target,split):
                if filter_hidden:continue
                raise ValueError('hidden target reached mean')
            yield target,values[i],mask[i],float(cells[i])


def mixed_common(streams,width,reliability_scale=100.):
    """Mix conditions per target/gene, then take an equal-target masked mean.

    The heap retains one target from each condition. A producer chunk contains
    at most 128 targets, so the full target-by-gene matrix is never allocated.
    """
    if reliability_scale<=0:raise ValueError('positive reliability scale required')
    streams=[iter(s) for s in streams];heap=[]
    def advance(index):
        item=next(streams[index],None)
        if item is not None:heapq.heappush(heap,(item[0],index,item))
    for i in range(len(streams)):advance(i)
    sums=np.zeros(width,np.float64);support=np.zeros(width,np.int64);targets=0;cells_by_stream=np.zeros(len(streams),np.int64)
    while heap:
        target=heap[0][0];num=np.zeros(width,np.float64);den=np.zeros(width,np.float64)
        while heap and heap[0][0]==target:
            _,index,(_,value,mask,n)=heapq.heappop(heap)
            if value.shape!=(width,) or mask.shape!=(width,):raise ValueError('row width mismatch')
            weight=n/(n+reliability_scale);num[mask]+=weight*value[mask].astype(np.float64);den[mask]+=weight
            cells_by_stream[index]+=int(n);advance(index)
        valid=den>0;sums+=np.divide(num,den,out=np.zeros(width),where=valid);support+=valid;targets+=1
    if targets==0:raise ValueError('no eligible target for common')
    mean=np.divide(sums,support,out=np.zeros(width),where=support>0)
    return dict(common=mean,mask=support>0,contributing_targets=support),dict(
        targets=targets,cells_by_condition=cells_by_stream.tolist(),
        policy='condition reliability n/(n+100) per target/gene, then equal target mean',
        width=width,common_supported_genes=int((support>0).sum()),full_matrix_allocated=False)


def single_common(stream,width):
    total=np.zeros(width,np.float64);support=np.zeros(width,np.int64);targets=0;cells=0
    for _,value,mask,n in stream:
        total+=np.where(mask,value,0).astype(np.float64);support+=mask;targets+=1;cells+=int(n)
    if targets==0:raise ValueError('no eligible target for common')
    return dict(common=np.divide(total,support,out=np.zeros(width),where=support>0),mask=support>0,
        contributing_targets=support),dict(targets=targets,target_cells=cells,policy='equal target mean')
