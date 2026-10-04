"""Small transfer-residual model and population-mean supervision, in natural-log effect units.

No source policy is learned here: anchors and descriptors must be prepared within each
fold. The same predict_effect function serves fit, bench and export. No GEARS dependency.
"""
import torch
from torch import nn


class Hybrid(nn.Module):
    def __init__(self, genes, target_dim, context_dim, width=64, rank=32,
                 with_context=True, residual_bound=0.5):
        super().__init__()
        if min(genes, target_dim, context_dim, width, rank) < 1 or residual_bound <= 0:
            raise ValueError('invalid model dimensions or residual bound')
        self.with_context = with_context
        self.bound = residual_bound
        self.anchor_encoder = nn.Linear(genes, rank, bias=False)
        self.trunk = nn.Sequential(nn.Linear(rank + target_dim + (context_dim if with_context else 0), width),
                                   nn.GELU(), nn.Linear(width, rank), nn.GELU())
        self.decoder = nn.Linear(rank, genes, bias=False)
        nn.init.zeros_(self.decoder.weight)

    def forward(self, anchor, target, context, mask):
        a = torch.where(mask, anchor, 0)
        if not torch.isfinite(a).all() or not torch.isfinite(target).all():
            raise ValueError('nonfinite measured anchor or target descriptor')
        if self.with_context and not torch.isfinite(context).all():
            raise ValueError('nonfinite context descriptor')
        inputs = [self.anchor_encoder(a), target]
        if self.with_context:
            inputs.append(context)
        raw = self.decoder(self.trunk(torch.cat(inputs, -1)))
        return torch.where(mask, self.bound * torch.tanh(raw / self.bound), 0)


def predict_effect(model, anchor, target, context, mask, weight=1.0):
    """One unscaled effect contract. Emission t28 is applied exactly once downstream."""
    if not 0 <= weight <= 1:
        raise ValueError('residual weight outside [0, 1]')
    if weight == 0:
        return anchor.clone()
    residual = model(anchor, target, context, mask)
    return torch.where(mask, anchor + weight * residual, anchor)


def mean_supervision(effect, basal, truth_mean, mask, row_weight, residual,
                     residual_l2=0.01):
    """KL of the FULL admitted population mean against predicted proportions.

    Each row is a context/target stratum. Normalise valid positive baseline and truth
    on the measured intersection, with no arbitrary pseudo-count. A zero baseline
    cannot acquire mass under a multiplicative effect and is rejected if truth is positive.
    Caller supplies hierarchical row weights; no normalisation by their batch sum.
    """
    if effect.ndim != 2 or effect.shape != basal.shape or effect.shape != truth_mean.shape:
        raise ValueError('incompatible population arrays')
    if mask.shape != effect.shape or residual.shape != effect.shape:
        raise ValueError('incompatible support or residual')
    if row_weight.shape != effect.shape[:1] or not torch.isfinite(row_weight).all() or (row_weight < 0).any():
        raise ValueError('invalid row weights')
    b, y = torch.where(mask, basal, 0), torch.where(mask, truth_mean, 0)
    e = torch.where(mask, effect, 0)
    if not torch.isfinite(b).all() or not torch.isfinite(y).all() or not torch.isfinite(e).all():
        raise ValueError('nonfinite population statistic')
    if (b < 0).any() or (y < 0).any() or (b.sum(-1) <= 0).any() or (y.sum(-1) <= 0).any():
        raise ValueError('invalid population proportions')
    if ((b == 0) & (y > 0)).any():
        raise ValueError('positive truth outside baseline support; resolve estimator upstream')
    y = y / y.sum(-1, keepdim=True)
    support = mask & (b > 0)
    logits = torch.where(support, torch.log(b.clamp_min(torch.finfo(b.dtype).tiny)) + e, -torch.inf)
    logp = torch.log_softmax(logits, -1)
    # Mask first, avoiding 0 * -inf and gradients through unmeasured NaNs.
    terms = y * (torch.log(y.clamp_min(torch.finfo(y.dtype).tiny)) - torch.where(support, logp, 0))
    penalty = torch.where(mask, residual, 0).square().sum(-1) / mask.sum(-1).clamp_min(1)
    return ((terms.sum(-1) + residual_l2 * penalty) * row_weight).sum() / len(effect)
