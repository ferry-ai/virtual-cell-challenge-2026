"""The context encoder: a basal expression profile -> an embedding of a few dozen numbers (PyTorch; no project
imports). pretrain.py trains it; train_emb.py plugs its embeddings (or the encoder itself) into the network of
reports/modelli/rete_contesti_2026-09-27/.

Input: one profile's values on the model genes, as corpus.py prepares them -- log1p CPM over the genes the
profile measures (or within-profile ranks, the platform-robust option), minus the gene's training mean, over its
training SD -- with 0 where the gene is not measured or is hidden. Output: z, `d_emb` numbers. A decoder, given
z and the profile's platform, predicts every model gene.

Objective (pretrain.py):
1. masked-gene reconstruction: a share of the measured genes is hidden -- at random, and sometimes as another
   profile's platform hides them -- and predicted from z; the loss is the squared error on the hidden genes only;
2. consistency: a supervised contrastive term on z (L2-normalised) that pulls together two profiles of the same
   context (two cell subsets, pools, plates, or two augmented views of one profile) and pushes apart the other
   contexts of the batch.
Training inputs also get a random per-gene log bias (as net.platform_jitter); the reconstruction targets do not.

What it learns: the axes along which basal profiles co-vary across the corpus -- lineage, proliferation, stress,
interferon, p53 and the like, as far as the corpus varies along them -- summarised so that samples of one context
land together and different contexts apart. The decoder's platform input and the augmentations push platform
effects out of z; the consistency term pushes sampling noise out.

What it cannot learn:
* anything about perturbations: no response enters the objective. Whether z helps predict knockdown responses
  is a question for the network runs (DISEGNO.md §10); a better reconstruction of basal expression is not
  evidence of it;
* platform or study effects confounded with context: a context seen on one platform only cannot be told apart
  from its platform, and an effect shared by every context of a study looks like biology;
* states absent from the corpus: a held-out cell type gets an extrapolated z, with no guarantee of meaning;
* heterogeneity inside a context: a pseudobulk has no cell-level structure, and a context's embedding is the
  mean over its profiles;
* which basal differences matter: reconstruction weighs the dominant co-expression axes (cell size, ribosomal
  and mitochondrial load) whatever their relevance to responses.
Downstream, the network learns the map from z to its context vector from a handful of CRISPRi contexts (5-7 per
design today): a rich z can act as a context identifier (the failure of CP-0013). The blind, swap, emb_blind and
emb_swap controls of train_emb.py detect that; they do not prevent it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
import torch.nn.functional as F
from torch import nn
from torch.func import functional_call

CKPT_FORMAT = "context_encoder/1"


@dataclass
class EncoderConfig:
    n_genes: int
    d_emb: int = 32
    d_hidden: int = 512
    n_platforms: int = 0          # platforms the decoder knows (index 0: unknown); 0: no platform input
    d_platform: int = 8
    dropout: float = 0.1

    def to_dict(self) -> dict:
        return asdict(self)


class ContextEncoder(nn.Module):
    """forward(x) -> z; decode(z, platform) -> the reconstructed values of every model gene."""

    def __init__(self, cfg: EncoderConfig):
        super().__init__()
        self.cfg = cfg
        G, H, D = cfg.n_genes, cfg.d_hidden, cfg.d_emb
        self.encoder = nn.Sequential(nn.Linear(G, H), nn.LayerNorm(H), nn.GELU(), nn.Dropout(cfg.dropout),
                                     nn.Linear(H, H), nn.LayerNorm(H), nn.GELU(), nn.Linear(H, D))
        if cfg.n_platforms > 0:
            self.platform = nn.Embedding(cfg.n_platforms + 1, cfg.d_platform)
            with torch.no_grad():
                self.platform.weight[0].zero_()         # unknown platform: a neutral input, never trained
            d_in = D + cfg.d_platform
        else:
            self.platform = None
            d_in = D
        self.decoder = nn.Sequential(nn.Linear(d_in, H), nn.GELU(), nn.Linear(H, G))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """[B, G] standardised values, 0 where not visible -> [B, d_emb]."""
        return self.encoder(x)

    def decode(self, z: torch.Tensor, platform: torch.Tensor | None = None) -> torch.Tensor:
        if self.platform is not None:
            if platform is None:
                platform = torch.zeros(z.shape[0], dtype=torch.long, device=z.device)
            z = torch.cat([z, self.platform(platform.clamp(min=0, max=self.cfg.n_platforms))], dim=1)
        return self.decoder(z)


def masked_mse(xhat: torch.Tensor, target: torch.Tensor, scored: torch.Tensor) -> torch.Tensor:
    """Mean squared error over the scored entries (measured and hidden)."""
    m = scored.to(xhat.dtype)
    return ((xhat - target) ** 2 * m).sum() / m.sum().clamp(min=1.0)


def supcon(z: torch.Tensor, labels: torch.Tensor, temperature: float) -> torch.Tensor:
    """Supervised contrastive loss (Khosla et al. 2020) on L2-normalised z: for each row with at least one
    positive (same label, itself excluded), minus the mean log-probability of its positives among all the other
    rows of the batch. Rows without a positive do not count as anchors; they still serve as negatives."""
    n = z.shape[0]
    zn = F.normalize(z, dim=1)
    sim = zn @ zn.T / temperature
    eye = torch.eye(n, dtype=torch.bool, device=z.device)
    sim = sim.masked_fill(eye, float("-inf"))
    logprob = sim - torch.logsumexp(sim, dim=1, keepdim=True)
    pos = (labels.unsqueeze(0) == labels.unsqueeze(1)) & ~eye
    npos = pos.sum(dim=1)
    has = npos > 0
    if not bool(has.any()):
        return z.new_zeros(())
    per = -logprob.masked_fill(~pos, 0.0).sum(dim=1) / npos.clamp(min=1).to(z.dtype)
    return per[has].mean()


class DeltaEncoder(nn.Module):
    """A pre-trained encoder whose weights stay frozen, plus trainable offsets that start at zero: it computes
    with w0 + scale * delta. With Adam the offsets move at the learning rate of whatever trains them, so the
    encoder moves `scale` times slower; decoupled weight decay pulls delta, hence w, back towards w0. Only the
    encoder half is used (the decoder is not needed to embed)."""

    def __init__(self, base: ContextEncoder, scale: float):
        super().__init__()
        self.base = base
        self.scale = float(scale)
        for p in self.base.parameters():
            p.requires_grad_(False)
        self.deltas = nn.ParameterList([nn.Parameter(torch.zeros_like(p))
                                        for _, p in self.base.encoder.named_parameters()])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        params = {name: p + self.scale * d
                  for (name, p), d in zip(self.base.encoder.named_parameters(), self.deltas)}
        return functional_call(self.base.encoder, params, (x,))


def count_parameters(model: nn.Module) -> dict:
    """Trainable parameters, total and by top-level block."""
    blocks = {}
    for name, p in model.named_parameters():
        if p.requires_grad:
            key = name.split(".")[0]
            blocks[key] = blocks.get(key, 0) + p.numel()
    return {"total": int(sum(blocks.values())), "by_block": blocks}


def save_encoder(path, model: ContextEncoder, norm: dict, extra: dict | None = None) -> None:
    """encoder.pt, a new file: config, weights and the normalisation (tensors, strings and numbers only, so that
    torch.load(..., weights_only=True) reads it)."""
    payload = {"format": CKPT_FORMAT, "config": model.cfg.to_dict(),
               "state_dict": {k: v.detach().cpu() for k, v in model.state_dict().items()}, "norm": norm}
    payload.update(extra or {})
    with open(path, "xb") as fh:
        torch.save(payload, fh)


def load_checkpoint(path) -> dict:
    ck = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(ck, dict) or ck.get("format") != CKPT_FORMAT:
        raise ValueError(f"{path} is not a {CKPT_FORMAT} checkpoint")
    return ck


def build_encoder(ck: dict) -> ContextEncoder:
    model = ContextEncoder(EncoderConfig(**ck["config"]))
    model.load_state_dict(ck["state_dict"])
    return model
