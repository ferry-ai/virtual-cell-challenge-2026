"""R-LAB cell network, version 0: a response model trained on the raw counts of single cells (P5, technical check).

Supervision is the original count vector of every cell, never a mean, an LFC or a shrunk value. Each cell is read from
the contract shards (reports/sorgenti/corpus_cellulare_2026-09-30/contracts.py) with h5py alone, so the code runs on a
Kaggle GPU session without internet or anndata.

Model, per cell i of context c with perturbation t and modality m:
- context state z_c: a set encoder over K control cells of c (log1p CP10k on the input genes, measured mask as input);
- baseline logits beta_c = B(z_c) over the model genes; control cells are supervised with them, so the baseline is
  learned from control cells, not taken from a precomputed average;
- target code e_t: an embedding of t (learned across every context where t was perturbed) plus features available
  for any context: the target gene's own baseline expression in c (a knockdown can only act on an expressed gene);
- shift delta_ct = D(z_c, e_t, m) over the model genes (low rank plus a gene bias), and responder logit pi_ct;
- likelihood of the counts x_i given the library L_i (the cell's counts on the genes its source measures):
  controls NB(x | L softmax(beta_c)); perturbed cells a two-component mixture, pi NB(x | L softmax(beta_c + delta_ct))
  + (1 - pi) NB(x | L softmax(beta_c)), so a cell the guide did not silence is explained, not averaged in. The softmax
  runs over the genes the cell's source measures; the others are masked, never zero (D-009). Dispersion per gene and
  study.

Data: every shard of the given datasets is indexed from its obs and var; an epoch streams shards in a shuffled order
through a buffer of --buffer-shards shards, and batches are drawn from the buffer, so every cell can be visited and
the visited cells are counted per study, context and target (the coverage the plan asks for). A --holdout context is
invisible in training (its cells and its controls); at evaluation only its control cells feed z_c and beta_c.

Evaluation of the held-out context (technical, not a VCC score): per perturbation, the mean over its cells of the
log-likelihood gain over the no-effect model; and, as an auxiliary pseudobulk diagnostic, the cosine between the
predicted and observed mean shifts of log1p CP10k over the top observed genes, against two baselines computed from
training cells only: no effect, and transfer (the mean shift of the same target in the training contexts).
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import h5py
import numpy as np

MISSING = "MISSING"


# ------------------------------------------------------------------------------------------ reading contract shards

def _text(values):
    return np.asarray([v.decode() if isinstance(v, bytes) else str(v) for v in values], dtype=object)


def h5_column(group, name):
    if name not in group:
        return None
    node = group[name]
    if isinstance(node, h5py.Group) and "categories" in node:
        cats = _text(node["categories"][:])
        codes = node["codes"][:].astype(np.int64)
        return np.where(codes >= 0, cats[np.clip(codes, 0, None)], MISSING).astype(object)
    if isinstance(node, h5py.Group) and "values" in node:
        return _text(node["values"][:])
    return node[:] if node.dtype.kind in "iufb" else _text(node[:])


@dataclass
class ShardInfo:
    path: Path
    study: str
    n_cells: int
    contexts: np.ndarray            # per cell
    targets: np.ndarray             # per cell (NTC, UNASSIGNED or a label)
    control: np.ndarray             # per cell bool
    modality: np.ndarray            # per cell
    library: np.ndarray             # per cell
    official_index: np.ndarray      # per native feature, -1 when not on the axis
    measured: np.ndarray            # per native feature
    cell_keys: np.ndarray = None    # per cell: study|library|barcode, unique in the corpus
    source: str = "MISSING"         # the source file the shard was read from (uns/source: locator and release)


def h5_scalar(group, *path):
    node = group
    for p in path:
        if not isinstance(node, h5py.Group) or p not in node:
            return None
        node = node[p]
    v = node[()]
    return v.decode() if isinstance(v, bytes) else str(v)


def index_shard(path: Path) -> ShardInfo:
    with h5py.File(path, "r") as f:
        obs, var = f["obs"], f["var"]
        study = h5_column(obs, "study")
        control_kind = h5_column(obs, "control_kind")
        source = "|".join(str(h5_scalar(f, "uns", "source", k)) for k in ("locator", "release"))
        return ShardInfo(path=path, study=str(study[0]), n_cells=int(len(study)),
                         contexts=h5_column(obs, "context").astype(str),
                         targets=h5_column(obs, "target").astype(str),
                         control=(control_kind.astype(str) == "NTC"),
                         modality=h5_column(obs, "modality").astype(str),
                         library=h5_column(obs, "library").astype(str),
                         official_index=np.asarray(h5_column(var, "official_index"), dtype=np.int64),
                         measured=np.asarray(h5_column(var, "measured")).astype(bool),
                         cell_keys=h5_column(obs, "cell_key").astype(str), source=source)


def read_csr(path, official_index, measured, gene_of_axis: np.ndarray, n_model_genes: int):
    """A shard's counts as CSR on the model genes and the mask of model genes the shard measures. Features off the
    model are dropped; features that collide on one model gene are dropped and that gene is masked
    (cell_data.feature_columns), so no count is ever summed across features. Returns (csr, mask).

    The stored CSR is filtered in place: columns remapped, entries off the model dropped, the row pointer rebuilt
    from a running count of the kept entries; no COO, no sum, no sort (1/10, incident E-20261001-001: the loader of
    the first GPU training kept the GPU waiting). Within a row the columns keep the shard's native order: the matrix
    is the one the COO path built, but its indices may be unsorted, and whoever needs them sorted sorts them
    (cell_data.fingerprints does)."""
    import scipy.sparse as sp
    import cell_data as CD
    with h5py.File(path, "r") as f:
        g = f["X"]
        shape = tuple(int(v) for v in g.attrs["shape"])
        data, indices, indptr = g["data"][:], g["indices"][:], g["indptr"][:].astype(np.int64)
    col, mask, _ = CD.feature_columns(official_index, measured, gene_of_axis, n_model_genes)
    new_col = col[indices]
    ok = new_col >= 0
    kept = np.concatenate([[0], np.cumsum(ok, dtype=np.int64)])
    m = sp.csr_matrix((data[ok].astype(np.float32, copy=False), new_col[ok].astype(np.int32), kept[indptr]),
                      shape=(shape[0], n_model_genes))
    return m, mask


def read_csr_rows(path, rows, official_index, measured, gene_of_axis: np.ndarray, n_model_genes: int):
    """Some rows of a shard, in the given order (repeats allowed), as CSR on the model genes, with the shard's mask:
    the same matrix as read_csr(...)[0][rows]. Each run of consecutive rows is read as one slice, so only the
    compressed chunks that hold those rows are decompressed (1/10: the evaluation read whole shards for a few hundred
    cells of the hidden targets)."""
    import scipy.sparse as sp
    import cell_data as CD
    rows = np.asarray(rows, dtype=np.int64)
    col, mask, _ = CD.feature_columns(official_index, measured, gene_of_axis, n_model_genes)
    srt = np.unique(rows)
    if srt.size == 0:
        return sp.csr_matrix((0, n_model_genes), dtype=np.float32), mask
    with h5py.File(path, "r") as f:
        g = f["X"]
        indptr = g["indptr"][:].astype(np.int64)
        data_parts, ind_parts = [], []
        for run in np.split(srt, np.flatnonzero(np.diff(srt) != 1) + 1):
            lo, hi = indptr[run[0]], indptr[run[-1] + 1]
            data_parts.append(g["data"][lo:hi])
            ind_parts.append(g["indices"][lo:hi])
    data, indices = np.concatenate(data_parts), np.concatenate(ind_parts)
    sub_ptr = np.concatenate([[0], np.cumsum(indptr[srt + 1] - indptr[srt])])
    new_col = col[indices]
    ok = new_col >= 0
    kept = np.concatenate([[0], np.cumsum(ok, dtype=np.int64)])
    m = sp.csr_matrix((data[ok].astype(np.float32, copy=False), new_col[ok].astype(np.int32), kept[sub_ptr]),
                      shape=(srt.size, n_model_genes))
    return m[np.searchsorted(srt, rows)], mask


def read_counts(info: ShardInfo, gene_of_axis: np.ndarray, n_model_genes: int):
    return read_csr(info.path, info.official_index, info.measured, gene_of_axis, n_model_genes)


# ------------------------------------------------------------------------------------------ corpus

@dataclass
class Corpus:
    shards: list
    genes: list                      # model genes (symbols of the official axis)
    gene_of_axis: np.ndarray         # official axis index -> model gene index or -1
    contexts: list
    targets: list                    # perturbation labels seen anywhere (not NTC/UNASSIGNED)
    modalities: list
    studies: list
    target_symbol_axis: dict = field(default_factory=dict)   # label -> model gene index of the target gene, if any

    @classmethod
    def build(cls, shard_paths, axis_symbols, holdout=None, log=print):
        infos = []
        t0 = time.time()
        for p in shard_paths:
            infos.append(index_shard(Path(p)))
        log(f"indexed {len(infos)} shards, {sum(i.n_cells for i in infos)} cells in {time.time() - t0:.0f}s")
        used = np.zeros(len(axis_symbols), bool)
        for i in infos:
            on = i.official_index[(i.official_index >= 0) & i.measured]
            used[on] = True
        gene_axis = np.flatnonzero(used)
        gene_of_axis = np.full(len(axis_symbols), -1, np.int64)
        gene_of_axis[gene_axis] = np.arange(gene_axis.size)
        genes = [axis_symbols[g] for g in gene_axis]
        contexts = sorted({c for i in infos for c in np.unique(i.contexts)})
        targets = sorted({t for i in infos for t in np.unique(i.targets[~i.control]) if t not in ("NTC", "UNASSIGNED", MISSING)})
        modalities = sorted({m for i in infos for m in np.unique(i.modality)})
        studies = sorted({i.study for i in infos})
        where = {s: k for k, s in enumerate(genes)}
        tsa = {t: where.get(t.split("|")[0], -1) for t in targets}
        return cls(infos, genes, gene_of_axis, contexts, targets, modalities, studies, tsa)

    def summary(self, holdout=None) -> dict:
        rows = []
        for i in self.shards:
            for ctx in np.unique(i.contexts):
                sel = i.contexts == ctx
                rows.append({"study": i.study, "context": str(ctx), "cells": int(sel.sum()),
                             "controls": int((sel & i.control).sum()),
                             "perturbed": int((sel & ~i.control & ~np.isin(i.targets, ["UNASSIGNED", MISSING])).sum()),
                             "unassigned": int((sel & np.isin(i.targets, ["UNASSIGNED", MISSING])).sum()),
                             "targets": int(np.unique(i.targets[sel & ~i.control]).size),
                             "holdout": str(ctx) == holdout})
        agg = defaultdict(lambda: Counter())
        for r in rows:
            key = (r["study"], r["context"], r["holdout"])
            agg[key].update({k: v for k, v in r.items() if isinstance(v, int) and not isinstance(v, bool)})
        return {"genes": len(self.genes), "contexts": self.contexts, "targets": len(self.targets),
                "modalities": self.modalities,
                "by_study_context": [{"study": s, "context": c, "holdout": h, **dict(v)} for (s, c, h), v in sorted(agg.items())]}


# ------------------------------------------------------------------------------------------ model

def build_model(n_genes, n_targets, n_modalities, n_studies, input_genes, dim=128, rank=128,
                target_desc=None, target_code="descriptors", pi_floor=0.0):
    """target_desc: [n_targets + 1, D] biological descriptors of each target's gene (last row: none), or None.
    target_code: 'descriptors' (transferable to targets never perturbed), 'identity' (a free embedding per target,
    the comparison arm) or 'both'."""
    import torch
    from torch import nn

    class CellNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.input_genes = torch.as_tensor(input_genes, dtype=torch.long)
            k = len(input_genes)
            self.cell_enc = nn.Sequential(nn.Linear(2 * k, 512), nn.GELU(), nn.Linear(512, dim))
            self.ctx_proj = nn.Sequential(nn.Linear(dim, dim), nn.GELU(), nn.Linear(dim, dim))
            self.base = nn.Linear(dim, n_genes)                 # beta_c = W z_c + b
            self.target_code = target_code
            self.target_emb = nn.Embedding(n_targets + 1, dim)   # last row: unknown target
            if target_code == "descriptors":
                nn.init.zeros_(self.target_emb.weight)
                self.target_emb.weight.requires_grad_(False)     # identity path off: the code comes from biology
            if target_desc is not None:
                self.register_buffer("desc", torch.as_tensor(target_desc, dtype=torch.float32))
                self.desc_enc = nn.Sequential(nn.Linear(target_desc.shape[1], 256), nn.GELU(), nn.Linear(256, dim))
            else:
                self.desc = None
            if target_code == "identity" and target_desc is not None:
                self.desc_enc.requires_grad_(False)
            self.target_feat = nn.Sequential(nn.Linear(2, dim), nn.GELU(), nn.Linear(dim, dim))
            self.mod_emb = nn.Embedding(n_modalities, dim)
            self.trunk = nn.Sequential(nn.Linear(3 * dim, 512), nn.GELU(), nn.Linear(512, 512), nn.GELU())
            self.delta_low = nn.Linear(512, rank)
            self.delta_out = nn.Linear(rank, n_genes)
            self.pi_head = nn.Linear(512, 1)
            self.log_theta = nn.Parameter(torch.zeros(n_studies, n_genes) + math.log(5.0))
            nn.init.zeros_(self.delta_out.weight)
            nn.init.zeros_(self.delta_out.bias)

        def context(self, x_in, m_in, lib):
            """Control cells of each context, on the input genes only: x_in [n_ctx, K, n_input] counts; m_in the same
            shape, the input genes each control row's own shard measures; lib [n_ctx, K], each row's counts on the
            genes its shard measures. The input genes are fixed before training (self.input_genes)."""
            m = m_in.float()
            norm = torch.log1p(x_in * m / lib.clamp_min(1.0)[..., None] * 1e4)
            h = self.cell_enc(torch.cat([norm * m, m], -1)).mean(1)
            z = self.ctx_proj(h)
            beta = self.base(z)
            return z, beta

        def forward(self, z, beta, target_idx, target_gene, modality_idx):
            """Per cell: z [B, dim], beta [B, G], target_idx [B], target_gene [B] (-1 none), modality [B]."""
            import torch
            e = self.target_emb(target_idx)
            tg = target_gene.clamp_min(0)
            own = torch.gather(torch.log_softmax(beta, -1), 1, tg[:, None]).squeeze(1)
            feats = torch.stack([torch.where(target_gene >= 0, own, torch.zeros_like(own)),
                                 (target_gene >= 0).float()], -1)
            e = e + self.target_feat(feats)
            if self.desc is not None and self.target_code in ("descriptors", "both"):
                e = e + self.desc_enc(self.desc[target_idx])
            h = self.trunk(torch.cat([z, e, self.mod_emb(modality_idx)], -1))
            delta = self.delta_out(self.delta_low(h))
            # pi in [pi_floor, 1 - pi_floor]: with a floor the shift keeps a gradient even when the mixture prefers
            # no effect (1/10: without it the identity arm of rlab-cellnet-r3 went to pi = 1e-10 and stopped learning)
            pi = pi_floor + (1.0 - 2.0 * pi_floor) * torch.sigmoid(self.pi_head(h)).squeeze(-1)
            return delta, pi

    return CellNet()


def nb_logpmf(x, mu, theta):
    import torch
    # log NB(x | mu, theta), theta = inverse dispersion
    t = theta
    return (torch.lgamma(x + t) - torch.lgamma(t) - torch.lgamma(x + 1)
            + t * (torch.log(t) - torch.log(t + mu)) + x * (torch.log(mu.clamp_min(1e-12)) - torch.log(t + mu)))


def cell_loglik(x, lib, logits, mask, theta):
    """Sum over measured genes of log NB(x | lib softmax(logits over measured genes), theta)."""
    import torch
    masked = logits.masked_fill(~mask, float("-inf"))
    mu = lib[:, None] * torch.softmax(masked, -1)
    ll = nb_logpmf(x, mu.clamp_min(1e-12), theta)
    return (ll * mask).sum(-1)
