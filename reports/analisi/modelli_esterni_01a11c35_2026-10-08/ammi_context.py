"""Original low-rank ESM2-by-control-state correction; frozen anchor, explicit masks.

Control normalization and split-safe anchors belong to the caller's pinned contract.
This module never estimates an anchor, interprets a cell-line ID, or rescales effects.
"""
import torch
from torch import nn


class ContextCorrection(nn.Module):
    def __init__(self, control_genes, response_genes, reference_mean, rank=16,
                 hidden=64, context_mode='cells'):
        super().__init__()
        if context_mode not in ('cells', 'mean', 'none'):
            raise ValueError('unknown context ablation')
        mean = torch.as_tensor(reference_mean).detach().clone()
        if mean.ndim != 1 or not torch.isfinite(mean).all():
            raise ValueError('finite training-only reference mean required')
        self.register_buffer('reference_mean', mean)
        self.context_mode = context_mode
        self.control_genes = control_genes
        self.target_projection = nn.Linear(len(mean), rank, bias=False)
        self.cell_encoder = nn.Sequential(nn.Linear(2 * control_genes, hidden),
                                          nn.GELU(), nn.Linear(hidden, rank))
        self.decoder = nn.Linear(rank, response_genes, bias=False)
        nn.init.zeros_(self.decoder.weight)

    def encode_controls(self, cells, observed, valid):
        if cells.ndim != 3 or cells.shape[-1] != self.control_genes:
            raise ValueError('controls must have batch, cell, gene axes')
        if observed.shape != cells.shape or valid.shape != cells.shape[:2]:
            raise ValueError('control mask axes differ')
        if observed.dtype != torch.bool or valid.dtype != torch.bool:
            raise ValueError('boolean masks required')
        usable = observed & valid.unsqueeze(-1)
        if not torch.isfinite(cells[usable]).all() or not usable.any(-1)[valid].all():
            raise ValueError('observed control values must be finite and nonempty')
        count = valid.sum(1, keepdim=True)
        if (count == 0).any():
            raise ValueError('context without controls needs explicit fallback')
        x = torch.cat((torch.where(usable, cells, 0), usable.to(cells.dtype)), -1)
        weight = valid.unsqueeze(-1).to(cells.dtype)
        if self.context_mode == 'none':
            return cells.new_ones((len(cells), self.decoder.in_features))
        if self.context_mode == 'mean':
            return self.cell_encoder((x * weight).sum(1) / count)
        return (self.cell_encoder(x) * weight).sum(1) / count

    def forward(self, target_features, available, cells, observed, valid, anchor):
        if (target_features.ndim != 2 or target_features.shape[1] != len(self.reference_mean)
                or available.shape != target_features.shape[:1] or available.dtype != torch.bool):
            raise ValueError('target feature axes or availability differ')
        if (len(cells) != len(target_features) or anchor.shape != (len(cells), self.decoder.out_features)
                or not torch.isfinite(anchor).all() or not torch.isfinite(target_features[available]).all()):
            raise ValueError('finite observed features and pinned finite anchor required')
        safe = torch.where(available[:, None], target_features, self.reference_mean)
        target = self.target_projection(safe - self.reference_mean)
        context = self.encode_controls(cells, observed, valid)
        residual = self.decoder(target * context)
        residual = torch.where(available[:, None], residual, 0)
        return anchor.detach() + residual, residual


def weighted_masked_loss(prediction, response, observed, row_weights):
    if prediction.shape != response.shape or observed.shape != response.shape:
        raise ValueError('response axes differ')
    if observed.dtype != torch.bool or row_weights.shape != response.shape[:1]:
        raise ValueError('mask or weights differ')
    if (not torch.isfinite(prediction).all() or not torch.isfinite(response[observed]).all()
            or not torch.isfinite(row_weights).all() or (row_weights < 0).any()):
        raise ValueError('invalid observed value or row weight')
    weight = row_weights[:, None] * observed
    if weight.sum() <= 0:
        raise ValueError('empty supervised support')
    error = prediction - torch.where(observed, response, prediction.detach())
    return (weight * error.square()).sum() / weight.sum()


def export_guard(anchor, residual, observed, contexts, max_ratio=0.5, max_common=0.5):
    """Fail closed per context; same guard must run in validation and export.

    This is a structural/amplitude guard, not the independent PDS acceptance rule.
    Common fraction is calculated per gene over its available query targets.
    """
    if anchor.shape != residual.shape or observed.shape != anchor.shape or observed.dtype != torch.bool:
        raise ValueError('export axes differ')
    if len(contexts) != len(anchor) or not torch.isfinite(anchor[observed]).all() or not torch.isfinite(residual[observed]).all():
        raise ValueError('invalid export values')
    reports = []
    for context in sorted(set(contexts)):
        ix = torch.tensor([i for i,c in enumerate(contexts) if c == context], device=anchor.device)
        a, r, mask = anchor[ix], residual[ix], observed[ix]
        support = mask.sum(0)
        if len(ix) < 2 or not (support >= 2).any():
            raise ValueError('insufficient target support for export guard')
        a = torch.where(mask, a, 0); r = torch.where(mask, r, 0)
        energy = r.square().sum(); baseline = a.square().sum()
        ratio = torch.sqrt(energy / baseline) if baseline > 0 else (energy * 0 if energy == 0 else energy.new_tensor(float('inf')))
        enough = support >= 2
        mean = r.sum(0)[enough] / support[enough]
        second = r.square().sum(0)[enough] / support[enough]
        common = mean.square().sum() / second.sum() if second.sum() > 0 else energy * 0
        report = dict(context=context, targets=len(ix), common_genes=int(enough.sum()),
                      rms_ratio=float(ratio.detach()), common_share=float(common.detach()))
        report['pass'] = report['rms_ratio'] <= max_ratio and report['common_share'] <= max_common
        reports.append(report)
    if not reports or not all(r['pass'] for r in reports):
        raise ValueError('export guard failed; no automatic rescaling or centering')
    return reports
