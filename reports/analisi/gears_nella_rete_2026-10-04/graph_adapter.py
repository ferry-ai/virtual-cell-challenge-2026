"""Research-only contextual graph adapter for the frozen-anchor CellNet v5 API.

Original implementation inspired by GEARS, not a GEARS port. Graphs and descriptors
must be built outside the held-out response data. This module never loads a graph,
chooses a split, samples cells, or launches training. No PyG dependency.
"""
from __future__ import annotations

import torch
from torch import nn


class ContextGraph(nn.Module):
    """Context-gated neighbor messages; own-gene features remain in the base model.

    edges[0] -> edges[1]. Nonnegative similarity weights are NOT causal signs.
    Node axis includes the base model's final unknown/control row, which must be
    isolated. Isolated genes return zero extra message and are never discarded.
    Normalization uses ungated incoming weight so a one-neighbor gate can act.
    """

    def __init__(self, descriptors, edges, weights, context_dim, dim):
        super().__init__()
        features = torch.as_tensor(descriptors, dtype=torch.float32).detach().clone()
        edge = torch.as_tensor(edges, dtype=torch.long).detach().clone()
        weight = torch.as_tensor(weights, dtype=torch.float32).detach().clone()
        if features.ndim != 2 or not torch.isfinite(features).all():
            raise ValueError('descriptors must be a finite node-by-feature matrix')
        if edge.ndim != 2 or edge.shape[0] != 2 or weight.shape != (edge.shape[1],):
            raise ValueError('expected edges [2,E] and weights [E]')
        if not torch.isfinite(weight).all() or (weight <= 0).any():
            raise ValueError('similarity weights must be finite and positive')
        if edge.numel() and ((edge < 0).any() or (edge >= len(features) - 1).any()):
            raise ValueError('edges must name valid genes, excluding the sentinel')
        if edge.numel() and (edge[0] == edge[1]).any():
            raise ValueError('self information already has a separate path')
        if edge.shape[1] != torch.unique(edge.T, dim=0).shape[0]:
            raise ValueError('duplicate directed edge')
        self.register_buffer('features', features)
        self.register_buffer('edges', edge)
        self.register_buffer('weights', weight)
        incoming = torch.zeros(len(features)).index_add_(0, edge[1], weight)
        self.register_buffer('incoming', incoming)
        self.message = nn.Linear(features.shape[1], dim, bias=False)
        self.edge_key = nn.Linear(2 * features.shape[1], dim, bias=False)
        self.context_key = nn.Linear(context_dim, dim, bias=False)
        self.message_out = nn.Linear(dim, dim, bias=False)
        nn.init.zeros_(self.message_out.weight)

    def forward(self, context, target_idx):
        if context.ndim != 2 or target_idx.shape != (len(context),):
            raise ValueError('one target index per context row required')
        if (target_idx < 0).any() or (target_idx >= len(self.features)).any():
            raise ValueError('target outside the declared node axis')
        # Loop over distinct requested targets; avoid materializing B x all genes x D.
        out = context.new_zeros((len(context), self.message.out_features))
        source, destination = self.edges
        for target in target_idx.unique():
            rows = torch.where(target_idx == target)[0]
            selected = destination == target
            if not selected.any():
                continue
            src = source[selected]
            dst = destination[selected]
            key = self.edge_key(torch.cat([self.features[src], self.features[dst]], -1))
            gate = torch.sigmoid(self.context_key(context[rows]) @ key.T / key.shape[1] ** 0.5)
            normalized = self.weights[selected] / self.incoming[target].clamp_min(1e-12)
            messages = self.message(self.features[src])
            out[rows] = self.message_out((gate * normalized[None, :]) @ messages)
        return out


class GraphCellNet(nn.Module):
    """Bridge to CellNet v5: insert graph messages in the target code, before trunk.

    Only descriptor mode and fixed anchor gain are supported. The base model,
    likelihood, common head, masks and generator are preserved. Trainer checkpoint
    and export reconstruction must be extended before a real run (see report).
    """

    def __init__(self, base, graph):
        super().__init__()
        if base.target_code != 'descriptors' or base.desc is None:
            raise ValueError('bridge requires the descriptor-only base model')
        if not base.anchor_rank or base.gain_mode != 'fixed':
            raise ValueError('bridge requires a frozen transfer anchor')
        if not torch.equal(base.desc.detach().cpu(), graph.features.detach().cpu()):
            raise ValueError('graph and model must have the exact same descriptor axis')
        if graph.message.out_features != base.mod_emb.embedding_dim:
            raise ValueError('graph embedding dimension must match the base model')
        self.base, self.graph = base, graph

    def context(self, *args, **kwargs):
        return self.base.context(*args, **kwargs)

    def common(self, *args, **kwargs):
        return self.base.common(*args, **kwargs)

    def forward(self, z, beta, target_idx, target_gene, modality_idx, anchor=None, anchor_info=None):
        if anchor is None or anchor_info is None:
            raise ValueError('the frozen anchor and its support are required')
        b = self.base
        own = torch.gather(torch.log_softmax(beta, -1), 1, target_gene.clamp_min(0)[:, None]).squeeze(1)
        feats = torch.stack([torch.where(target_gene >= 0, own, torch.zeros_like(own)),
                             (target_gene >= 0).float()], -1)
        e = b.target_emb(target_idx) + b.target_feat(feats)
        e = e + b.desc_enc(b.desc[target_idx]) + self.graph(z, target_idx)
        e = e + b.anchor_enc(torch.cat([anchor @ b.anchor_U, anchor_info], -1))
        h = b.trunk(torch.cat([z, e, b.mod_emb(modality_idx)], -1))
        delta = b.delta_out(b.delta_low(h))
        if b.delta_bound > 0:
            delta = b.delta_bound * torch.tanh(delta / b.delta_bound)
        return anchor + delta, b.pi_head(h).squeeze(-1)
