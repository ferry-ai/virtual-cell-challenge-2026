"""The multi-context perturbation-response network (PyTorch only; no project imports).

For a row i = (context c, target t) and a stored response gene g:

    yhat[i, g] = s_i h[i, g] m[i, g]  +  s^q_i h[i, g] q[i, g]  +  r[i, g]

* m[i, :] is the transferred profile: the reliability-weighted mean of t's centred effects in the families
  other than c's (built by `pool.Phase`). It enters directly, never through a bottleneck: projecting transferred
  responses on shared programs lost discrimination at every rank tried (reports/atlante_2026-09-26/RISULTATI.md).
* q[i, :] is the same mean over t's STRING partners, each partner's own gene left out: the only prior with a
  measured gain for targets no source measured (reports/bersagli_nuovi_2026-09-26/RISULTATI.md).
* s_i, s^q_i = exp(log A + b tanh(.)) are amplitudes per (target, context) around learned global amplitudes.
* h = 2 sigmoid(gate logit), in (0, 2), is a gene gate per (row, gene): a per-(context, gene) bias, a low-rank
  row x (context, gene) coupling, and a slope on how much more the gene ranks in the context than where m came
  from. It generalises the gates of reports/modello_contesto_2026-09-27/gated.py.
* r = alpha_i . beta[c, g] is a low-rank target x gene correction whose gene side is modulated by the context.

At initialisation h = 1 and r = 0: the network starts as the plain transfer A m + A_q q.

The context enters only through features of its control expression, computed without parameters by
`context_features`: per gene its level (log1p CPM / 5), within-context quantile rank, on/off at 1 and 10 CPM,
rank minus the training-context average, and an imputation flag; per context, the drank-weighted mean of the
gene embeddings (the global encoding). Everything learned is shared by all contexts: there is no learned vector
per context, which failed with two training contexts (docs/checkpoints CP-0013, CP-0026). `blind` mode gives a
row the features of the training-average control profile, `swap` mode another context's (`pool.Phase.batch`).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import torch
import torch.nn.functional as F
from torch import nn

LOG1P_1 = math.log1p(1.0)
LOG1P_5 = math.log1p(5.0)
LOG1P_10 = math.log1p(10.0)
CHANNELS = ("level", "rank", "on1", "on10", "drank", "imputed")   # per (context, gene)
N_CG = len(CHANNELS)
N_TC = 8        # per row, the target's own gene in the context
N_SUM = 4       # per row, summaries of m; the same four for q
N_DEPTH = 2     # per row, knockdown depth (optional nuisance input) and whether it is known


@dataclass
class NetConfig:
    n_genes: int                     # stored response genes (output columns)
    n_priors: int                    # target prior columns, indicators included
    n_targets: int = 0               # needed only with target_embedding
    d_gene: int = 32
    d_target: int = 32
    d_context: int = 8
    d_hidden: int = 128
    k_gate: int = 16
    k_inter: int = 32
    dropout: float = 0.1
    amp_bound: float = 2.0           # |log s - log A| <= amp_bound
    use_gate: bool = True
    use_inter: bool = True
    use_global_context: bool = True
    use_partners: bool = True
    use_depth: bool = False
    target_embedding: bool = False   # ablation: a free residual embedding per seen target

    def to_dict(self) -> dict:
        return asdict(self)


def quantile_ranks(x: torch.Tensor) -> torch.Tensor:
    """Tie-aware quantile ranks in [0, 1] along the last axis; tied values share their mean position."""
    n = x.shape[-1]
    xs = x.contiguous()
    s = torch.sort(xs, dim=-1).values.contiguous()
    lo = torch.searchsorted(s, xs, right=False)
    hi = torch.searchsorted(s, xs, right=True)
    return (lo.to(x.dtype) + (hi - lo - 1).to(x.dtype) / 2.0) / max(n - 1, 1)


def platform_jitter(logcpm: torch.Tensor, sd: float, generator: torch.Generator | None = None) -> torch.Tensor:
    """log1p(CPM x exp(eps)), eps ~ N(0, sd^2) per (context, gene): an unknown per-gene platform bias.

    Multiplicative on CPM, so a gene at 0 CPM stays at 0. Training-only augmentation (evidence 6 in DISEGNO.md)."""
    if sd <= 0:
        return logcpm
    eps = torch.randn(logcpm.shape, generator=generator, device=logcpm.device, dtype=logcpm.dtype) * sd
    return torch.log1p(torch.expm1(logcpm) * torch.exp(eps))


def context_features(logcpm: torch.Tensor, imputed: torch.Tensor, ref_rank: torch.Tensor) -> torch.Tensor:
    """[n, A] finite log1p CPM, [n, A] imputation flags, [A] reference rank -> [n, A, 6] features (`CHANNELS`)."""
    if not bool(torch.isfinite(logcpm).all()):
        raise ValueError("basal log1p CPM must be finite: impute before computing features")
    rank = quantile_ranks(logcpm)
    one = logcpm.dtype
    return torch.stack([logcpm / 5.0, rank, (logcpm >= LOG1P_1).to(one), (logcpm >= LOG1P_10).to(one),
                        rank - ref_rank.unsqueeze(0), imputed.to(one)], dim=-1)


def row_inputs(feat: torch.Tensor, genes_axis: torch.Tensor, row_feat: torch.Tensor, tgt_axis: torch.Tensor,
               omega: torch.Tensor, rbar: torch.Tensor, ref_rank: torch.Tensor):
    """From full-axis context features to the model's context inputs for one batch.

    feat [n_feat, A, 6]; genes_axis [G] axis columns of the stored genes; row_feat [B] feature row of each batch
    row; tgt_axis [B] axis column of the target's own gene (-1: not on the axis); omega [B, F] family weights of
    the row's transferred profile (each row sums to 1, or to 0 when it has none); rbar [F, A] family mean ranks;
    ref_rank [A] the training-context average rank.
    Returns ctx_gene [n_feat, G, 6]; tctx [B, 8] (level, rank, on1, on10, drank, softplus(log1p 5 - level),
    rank minus its rank where m came from, on-axis flag; all 0 off the axis); gref [B, G] (the gene's rank in the
    context minus its rank where m came from, or minus the training average without m).
    """
    ctx_gene = feat[:, genes_axis, :]
    has_w = omega.sum(dim=1, keepdim=True)
    ref_g = omega @ rbar[:, genes_axis] + (1.0 - has_w) * ref_rank[genes_axis].unsqueeze(0)
    gref = ctx_gene[row_feat, :, 1] - ref_g
    a = tgt_axis.clamp(min=0)
    on_axis = (tgt_axis >= 0).to(feat.dtype)
    ft = feat[row_feat, a, :]
    ref_t = (omega * rbar[:, a].T).sum(dim=1) + (1.0 - has_w[:, 0]) * ref_rank[a]
    soft = F.softplus(LOG1P_5 - 5.0 * ft[:, 0])
    tctx = torch.stack([ft[:, 0], ft[:, 1], ft[:, 2], ft[:, 3], ft[:, 4], soft, ft[:, 1] - ref_t,
                        torch.ones_like(soft)], dim=1)
    return ctx_gene, tctx * on_axis.unsqueeze(1), gref


class PerturbNet(nn.Module):
    """See the module docstring. `forward(batch, feat, consts)`; `pool.Phase` builds the three arguments."""

    def __init__(self, cfg: NetConfig, gene_init: torch.Tensor | None = None):
        super().__init__()
        if cfg.target_embedding and cfg.n_targets <= 0:
            raise ValueError("target_embedding needs n_targets > 0")
        self.cfg = cfg
        G, dg = cfg.n_genes, cfg.d_gene
        init = torch.randn(G, dg) * 0.1 if gene_init is None else torch.as_tensor(gene_init, dtype=torch.float32)
        if tuple(init.shape) != (G, dg):
            raise ValueError(f"gene_init must be ({G}, {dg}), got {tuple(init.shape)}")
        self.gene_emb = nn.Parameter(init.clone())
        self.missing_gene = nn.Parameter(torch.zeros(dg))
        self.cg_mlp = nn.Sequential(nn.Linear(N_CG + dg, 64), nn.GELU(), nn.Linear(64, cfg.k_gate + 1 + cfg.k_inter))
        with torch.no_grad():               # the gate's per-(context, gene) bias starts at 0, so h = 1
            self.cg_mlp[-1].weight[cfg.k_gate].zero_()
            self.cg_mlp[-1].bias[cfg.k_gate].zero_()
        self.u_mlp = nn.Sequential(nn.Linear(dg, 32), nn.GELU(), nn.Linear(32, cfg.d_context), nn.Tanh())
        self.target_mlp = nn.Sequential(nn.Linear(cfg.n_priors + dg + 1, 64), nn.GELU(), nn.Linear(64, cfg.d_target))
        self.target_emb = nn.Embedding(cfg.n_targets, cfg.d_target) if cfg.target_embedding else None
        if self.target_emb is not None:
            nn.init.zeros_(self.target_emb.weight)
        d_in = cfg.d_target + N_TC + cfg.d_context + 2 * (dg + N_SUM) + N_DEPTH
        self.trunk = nn.Sequential(nn.LayerNorm(d_in), nn.Linear(d_in, cfg.d_hidden), nn.GELU(), nn.Dropout(cfg.dropout),
                                   nn.Linear(cfg.d_hidden, cfg.d_hidden), nn.GELU(), nn.Dropout(cfg.dropout))
        self.head = nn.Linear(cfg.d_hidden, 3 + cfg.k_gate + cfg.k_inter)   # ds, ds_q, kappa, psi, alpha
        nn.init.zeros_(self.head.weight)
        nn.init.zeros_(self.head.bias)
        self.log_amp = nn.Parameter(torch.zeros(()))
        self.log_amp_q = nn.Parameter(torch.tensor(math.log(0.1)))

    def set_amplitude(self, a: float, a_q: float) -> None:
        """Start the direct paths at the least-squares amplitudes of the training rows (train.calibrate)."""
        with torch.no_grad():
            self.log_amp.fill_(math.log(max(float(a), 1e-4)))
            self.log_amp_q.fill_(math.log(max(float(a_q), 1e-5)))

    def forward(self, b: dict, feat: torch.Tensor, consts: dict) -> dict:
        cfg = self.cfg
        E = self.gene_emb
        G, dg = E.shape
        m, q = b["m"], b["q"]
        B = m.shape[0]
        ctx_gene, tctx, gref = row_inputs(feat, consts["genes_axis"], b["row_feat"], b["tgt_axis"], b["omega"],
                                          consts["rbar"], consts["ref_rank"])
        used, inv = torch.unique(b["row_feat"], return_inverse=True)
        cg_in = ctx_gene[used]
        cg = self.cg_mlp(torch.cat([cg_in, E.unsqueeze(0).expand(used.shape[0], G, dg)], dim=-1))
        gvec, gbias, beta = torch.split(cg, [cfg.k_gate, 1, cfg.k_inter], dim=-1)
        if cfg.use_global_context:
            u_used = self.u_mlp(torch.einsum("cg,gd->cd", cg_in[..., 4], E) / G)
        else:
            u_used = m.new_zeros(used.shape[0], cfg.d_context)

        tg = b["tgt_gene"]
        known = tg >= 0
        e_t = torch.where(known.unsqueeze(1), E[tg.clamp(min=0)], self.missing_gene.unsqueeze(0).expand(B, dg))
        z = self.target_mlp(torch.cat([b["priors"], e_t, known.to(E.dtype).unsqueeze(1)], dim=1))
        if self.target_emb is not None:
            ti = b["tgt_emb"]
            z = z + self.target_emb(ti.clamp(min=0)) * (ti >= 0).to(z.dtype).unsqueeze(1)
        m_proj = (m @ E) / (m.norm(dim=1, keepdim=True) + 1e-3)
        if cfg.use_partners:
            q_proj = (q @ E) / (q.norm(dim=1, keepdim=True) + 1e-3)
            qsum = b["qsum"]
        else:
            q_proj = m.new_zeros(B, dg)
            qsum = torch.zeros_like(b["qsum"])
        depth = b["depth"] if cfg.use_depth else torch.zeros_like(b["depth"])
        a = torch.cat([z, tctx, u_used[inv], m_proj, b["msum"], q_proj, qsum, depth], dim=1)
        out = self.head(self.trunk(a))
        ds = cfg.amp_bound * torch.tanh(out[:, 0])
        ds_q = cfg.amp_bound * torch.tanh(out[:, 1])
        kappa = out[:, 2]
        psi = out[:, 3:3 + cfg.k_gate]
        alpha = out[:, 3 + cfg.k_gate:]

        # rows grouped by their feature row: [n_j, k] @ [k, G] per group, reassembled in the batch order
        logit_parts, r_parts, order = [], [], []
        for j in range(used.shape[0]):
            idx = torch.nonzero(inv == j, as_tuple=True)[0]
            order.append(idx)
            logit_parts.append(gbias[j, :, 0].unsqueeze(0) + psi[idx] @ gvec[j].T)
            r_parts.append(alpha[idx] @ beta[j].T)
        order_t = torch.cat(order)
        perm = torch.empty_like(order_t)
        perm[order_t] = torch.arange(B, device=order_t.device)
        if cfg.use_gate:
            logit = torch.cat(logit_parts)[perm] + kappa.unsqueeze(1) * gref
            h = 2.0 * torch.sigmoid(logit)
        else:
            logit = m.new_zeros(B, G)
            h = torch.ones_like(m)
        r = torch.cat(r_parts)[perm] if cfg.use_inter else m.new_zeros(B, G)
        yhat = torch.exp(self.log_amp + ds).unsqueeze(1) * h * m + r
        if cfg.use_partners:
            yhat = yhat + torch.exp(self.log_amp_q + ds_q).unsqueeze(1) * h * q
        return {"yhat": yhat, "ds": ds, "logit": logit, "r": r, "h": h}


def count_parameters(model: nn.Module) -> dict:
    """Trainable parameters, total and by top-level block."""
    blocks = {}
    for name, p in model.named_parameters():
        if p.requires_grad:
            key = name.split(".")[0]
            blocks[key] = blocks.get(key, 0) + p.numel()
    return {"total": int(sum(blocks.values())), "by_block": blocks}
