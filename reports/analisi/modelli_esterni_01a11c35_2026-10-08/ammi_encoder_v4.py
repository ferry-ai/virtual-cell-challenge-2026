"""Memory-bounded context encoder with exact selected NTC population semantics."""
import numpy as np
import torch
from torch.utils.checkpoint import checkpoint


class ControlsNotConsumed:
    """Context/axis registry only: no cells, masks, counts or invented population."""
    def __init__(self, contexts, gene_count):
        self.contexts = frozenset(contexts)
        self.gene_count = int(gene_count)
        if not self.contexts or self.gene_count < 1:
            raise ValueError('declared contexts and gene axis required')

    def __contains__(self, context): return context in self.contexts
    def __iter__(self): return iter(self.contexts)
    def __getitem__(self, context):
        raise RuntimeError('controls_not_consumed: no NTC values exist in this registry')


def control_shape(control):
    return control.shape if hasattr(control,'batch') else control[0].shape


def batch(control,start,stop):
    return control.batch(start,stop) if hasattr(control,'batch') else (control[0][start:stop],control[1][start:stop])


def encode(model,control,device,block_size=256):
    """Recompute blocks during backward; checkpoint stores no dense RNA input.

    Blocks are an arithmetic implementation detail, not new cell sampling. Each
    cell participates once in the population mean. No changing a trained model
    or context after scoring; no dropout or RNG in this encoder.
    """
    if model.context_mode=='none':
        return torch.ones((1,model.decoder.in_features),device=device)
    n,g=control_shape(control)
    if n<1 or g!=model.control_genes: raise ValueError('control shape differs')
    def input_block(start,stop):
        values,mask=batch(control,start,stop)
        if (values.shape!=(stop-start,g) or mask.shape!=values.shape or mask.dtype!=bool
                or not mask.any(1).all() or not np.isfinite(values[mask]).all()):
            raise ValueError('invalid streamed control block')
        x=torch.as_tensor(values,dtype=torch.float32,device=device)
        m=torch.as_tensor(mask,dtype=torch.bool,device=device)
        return torch.cat((torch.where(m,x,0),m.to(x.dtype)),-1)
    if model.context_mode=='mean':
        # Input statistics have no learned parameters. Accumulate the same cells
        # and masks, keeping only one vector, before applying the encoder.
        total=torch.zeros(2*g,device=device,dtype=torch.float64)
        for start in range(0,n,block_size):
            total+=input_block(start,min(start+block_size,n)).double().sum(0)
        return model.cell_encoder((total/n).float()[None])
    def fragment(start,stop):
        return model.cell_encoder(input_block(start,stop)).sum(0,keepdim=True)/n
    state=torch.zeros((1,model.decoder.in_features),device=device)
    for start in range(0,n,block_size):
        stop=min(start+block_size,n)
        if torch.is_grad_enabled():
            piece=checkpoint(fragment,start,stop,use_reentrant=False,preserve_rng_state=False)
        else: piece=fragment(start,stop)
        state=state+piece
    return state


def forward_grouped(model,features,contexts,controls,anchor,device):
    residual=torch.zeros_like(anchor)
    for context in sorted(set(contexts)):
        if context not in controls: raise ValueError('undeclared context')
        indices=torch.tensor([i for i,c in enumerate(contexts) if c==context],device=device)
        state=encode(model,None if model.context_mode=='none' else controls[context],device)
        projected=model.target_projection(features[indices]-model.reference_mean)
        residual=residual.index_copy(0,indices,model.decoder(projected*state))
    return anchor.detach()+residual,residual
