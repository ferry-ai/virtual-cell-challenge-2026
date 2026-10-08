"""Frozen T3 KO pooling and combination; no I/O, tuning, or implicit centering."""
import numpy as np


def pool_contexts(contexts, shape, reliability_scale=100.0):
    """One study vote, retaining every context but never summing replicate weight."""
    numerator=np.zeros(shape,dtype=np.float64)
    denominator=np.zeros(shape,dtype=np.float64)
    reliability=np.zeros(shape,dtype=np.float64)
    for value,mask,n_cells in contexts:
        value=np.asarray(value);mask=np.asarray(mask);n_cells=np.asarray(n_cells)
        if value.shape!=shape or mask.shape!=shape or mask.dtype!=bool or n_cells.shape!=(shape[0],):
            raise ValueError('KO context dimensions or mask differ')
        if not np.isfinite(value[mask]).all() or not np.isfinite(n_cells).all() or np.any(n_cells<0):
            raise ValueError('invalid KO values or cell counts')
        rel=n_cells/(n_cells+reliability_scale)
        weight=np.where(mask,rel[:,None],0)
        numerator+=np.where(mask,value,0)*weight
        denominator+=weight
        reliability=np.maximum(reliability,weight)
    effect=np.divide(numerator,denominator,out=np.zeros(shape),where=denominator>0)
    return effect,reliability


def combine(core_effect,core_weight,groups,ko_weight=0.25):
    """Preserve the original CRISPRi values exactly outside observed KO pairs."""
    core_effect=np.asarray(core_effect,dtype=np.float64)
    core_weight=np.asarray(core_weight,dtype=np.float64)
    if core_effect.shape!=core_weight.shape or np.any(core_weight<0) or not np.isfinite(core_effect).all():
        raise ValueError('invalid CRISPRi core')
    ko_num=np.zeros_like(core_effect);ko_den=np.zeros_like(core_effect)
    for effect,reliability in groups:
        if effect.shape!=core_effect.shape or reliability.shape!=effect.shape:
            raise ValueError('KO group shape differs')
        if not np.isfinite(effect).all() or not np.isfinite(reliability).all() or np.any((reliability<0)|(reliability>1)):
            raise ValueError('invalid KO group')
        ko_num+=ko_weight*reliability*effect
        ko_den+=ko_weight*reliability
    supported=ko_den>0
    result=core_effect.copy()
    result[supported]=(core_effect[supported]*core_weight[supported]+ko_num[supported])/(core_weight[supported]+ko_den[supported])
    return result,core_weight+ko_den,ko_den
