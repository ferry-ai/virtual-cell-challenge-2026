"""TransferNet: a gene-wise, source-set encoder for knockdown effects in an unseen cell line.

Prediction for target t in query line q, gene g:

    y_hat[g] = gain[g] * sum_s alpha[s, g] * delta_s[g]   +   U[g] . c
               '---------- transfer term ----------'       '- program term -'

- transfer term: a convex combination, per gene, of the effects of t already measured in the
  source lines. The attention weights alpha come from per-(source, gene) tokens built from
  transferable quantities only: the source effect, the gene's control expression in source and
  query, their difference, cells and on-target knockdown of the source measurement, and the
  global control similarity of source and query. With alpha uniform and gain constant this is a
  simple transfer (mean of the source effects times an amplitude). It is *not* the team's t22
  recipe, which also shrinks the effects, centres each source (gamma = 1), weights sources by
  reliability and adds a cis module.
- program term: a low-rank response whose coefficients c come from the target's descriptor and
  from the source effects projected on the programs. It is the only term left when no source
  measured t (regime J).

No parameter is indexed by gene or by cell line (P5). A gene is known to the model only through
its descriptor row in `gene_load` (how it moves as a readout across training knockdowns) and
through its control expression; the program loadings U are a function of the descriptor. The
parameter count does not depend on the number of genes, and the same weights run on any gene
axis for which the descriptors are computed the same way. `gene_res=True` adds back a learned
vector per gene, as an ablation only.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


def mlp(i, h, o, p=0.1):
    return nn.Sequential(nn.Linear(i, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, o))


class TransferNet(nn.Module):
    def __init__(self, gene_load: torch.Tensor, d: int = 64, k_prog: int = 32,
                 gain_init: float = 0.5, gene_res: bool = False):
        super().__init__()
        G, kr = gene_load.shape
        assert k_prog <= kr
        self.register_buffer("gene_load", gene_load)                  # fixed readout descriptors
        self.gene_proj = mlp(kr, d, d)
        self.gene_res = nn.Embedding(G, d) if gene_res else None      # ablation only
        if gene_res:
            nn.init.zeros_(self.gene_res.weight)
        self.tok = nn.Linear(4 + 3, d)                                # per (source, gene) scalars + source meta
        self.tok_out = mlp(d, d, d)
        self.target = mlp(kr + 3, 2 * d, d)                           # target descriptor -> context vector
        self.query = mlp(d + 1 + d, d, d)                             # gene, query basal, target vector
        self.k = nn.Linear(d, d, bias=False)
        self.gain = mlp(2 * d + 1 + d, d, 1)
        nn.init.zeros_(self.gain[-1].weight)
        nn.init.constant_(self.gain[-1].bias, float(torch.log(torch.expm1(torch.tensor(gain_init)))))
        # Program loadings from the descriptor: starts as the first k_prog readout components.
        self.prog = nn.Linear(kr, k_prog, bias=False)
        with torch.no_grad():
            self.prog.weight.zero_()
            self.prog.weight[:, :k_prog] = torch.eye(k_prog)
        self.prog_res = mlp(d, d, k_prog)
        nn.init.zeros_(self.prog_res[-1].weight)
        nn.init.zeros_(self.prog_res[-1].bias)
        self.coef = mlp(d + k_prog + 1, 2 * d, k_prog)
        nn.init.zeros_(self.coef[-1].weight)
        nn.init.zeros_(self.coef[-1].bias)

    def forward(self, sd, sb, sm, mask, qb, tf, **_):
        B, S, G = sd.shape
        e = self.gene_proj(self.gene_load)                              # [G, d]
        if self.gene_res is not None:
            e = e + self.gene_res.weight
        U = self.prog(self.gene_load) + self.prog_res(e)                # [G, K]
        ctx = self.target(tf)                                           # [B, d]
        has = mask.any(1, keepdim=True).float()                         # [B, 1]

        x = torch.stack([sd, sb, qb[:, None] - sb, qb[:, None].expand_as(sd)], -1)   # [B,S,G,4]
        x = torch.cat([x, sm[:, :, None, :].expand(B, S, G, 3)], -1)
        h = self.tok_out(F.gelu(self.tok(x) + e))                        # [B,S,G,d]
        q = self.query(torch.cat([e.expand(B, G, -1), qb[..., None], ctx[:, None].expand(B, G, -1)], -1))
        logit = (self.k(h) * q[:, None]).sum(-1) / h.shape[-1] ** 0.5    # [B,S,G]
        logit = logit.masked_fill(~mask[:, :, None], -1e4)
        alpha = torch.softmax(logit, 1) * mask[:, :, None]
        transfer = (alpha * sd).sum(1)                                   # [B,G]
        pooled = (alpha[..., None] * h).sum(1)                           # [B,G,d]
        gain = F.softplus(self.gain(torch.cat([e.expand(B, G, -1), pooled, qb[..., None],
                                               ctx[:, None].expand(B, G, -1)], -1))).squeeze(-1)

        n_src = mask.sum(1, keepdim=True).clamp(min=1).float()
        src_mean = (sd * mask[:, :, None]).sum(1) / n_src                # [B,G]
        z = src_mean @ U / G ** 0.5                                      # projection on the programs
        c = self.coef(torch.cat([ctx, z, has], -1))                      # [B,K]
        program = c @ U.T
        return gain * transfer * has + program


def loss_fn(pred, y, w, gmask, lam_cos: float = 0.5):
    """Reliability-weighted MSE on the genes the scorer keeps, plus 1 - cosine (the PDS axis).

    The MSE is divided by the batch's mean squared effect (detached), so both terms are O(1):
    predicting zero costs 1 on the first term, as the scorer's `mse` normalises by effect size.
    """
    m = gmask.float()
    mse = ((pred - y) ** 2 * m).sum(1) / m.sum(1)
    scale = ((y ** 2 * m).sum(1) / m.sum(1)).mean().detach().clamp(min=1e-8)
    cos = F.cosine_similarity(pred * m, y * m, dim=1, eps=1e-8)
    return ((mse / scale + lam_cos * (1 - cos)) * w).sum() / w.sum()
