"""Biology-conditioned source attention with bounded changes to frozen transfer.

Research-only code. Reuses the immutable r2 Pool format, never its pre-pooled Phase.
Arrays remain memory maps; a batch reads only its rows and requested gene columns.
No output from an invisible row may construct features, centres or source profiles.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
LEGACY = REPO / "reports/modelli/rete_contesti_2026-09-27"
sys.path.insert(0, str(LEGACY))
import pool as P


def finite_mean(x, axis=0):
    ok = np.isfinite(x)
    return np.divide(np.where(ok, x, 0).sum(axis=axis), ok.sum(axis=axis),
                     out=np.zeros(np.asarray(x).sum(axis=axis).shape), where=ok.sum(axis=axis) > 0)


def cis_hidden(pool, targets):
    """Target outcomes in each selected target's 5 kb region leave every source."""
    hidden = set(int(t) for t in targets)
    for t in list(hidden):
        if np.isfinite(pool.tgt_tss[t]) and pool.tgt_chrom[t]:
            near = (pool.tgt_chrom == pool.tgt_chrom[t]) & (np.abs(pool.tgt_tss - pool.tgt_tss[t]) <= 5000)
            hidden.update(np.flatnonzero(near).tolist())
    return np.array(sorted(hidden), dtype=int)


class SourceView:
    """Leakage-isolated context tokens; no family or context is pooled in advance."""

    def __init__(self, pool, visible, *, centres_cache=None, max_partners=8):
        self.pool = pool
        self.visible = np.zeros(pool.n_rows, bool)
        self.visible[np.asarray(visible, int)] = True
        if not self.visible.any():
            raise ValueError("No visible rows")
        self.rows = np.flatnonzero(self.visible)
        self.contexts = np.unique(pool.row_context[self.rows])
        self.max_partners = max_partners
        self.lookup = np.full((len(pool.context_names), len(pool.target_names)), -1, np.int64)
        self.lookup[pool.row_context[self.rows], pool.row_target[self.rows]] = self.rows
        self.mu = {"raw": {}, "shrunk": {}}
        self.cover = {}
        cache = {} if centres_cache is None else centres_cache
        for c in self.contexts:
            rows = self.rows[pool.row_context[self.rows] == c]
            key = (int(c), hashlib.sha256(rows.tobytes()).hexdigest())
            if key not in cache:
                sums = {k: np.zeros(pool.G) for k in self.mu}
                counts = {k: np.zeros(pool.G) for k in self.mu}
                for start in range(0, len(rows), 256):
                    r = rows[start:start + 256]
                    se = self.read("se", r, np.arange(pool.G))
                    for k in sums:
                        x = self.read(k, r, np.arange(pool.G))
                        ok = np.isfinite(x) & np.isfinite(se) & (se > 0)
                        sums[k] += np.where(ok, x, 0).sum(0, dtype=np.float64)
                        counts[k] += ok.sum(0)
                cache[key] = ({k: np.divide(sums[k], counts[k], out=np.zeros(pool.G), where=counts[k] > 0).astype(np.float32)
                               for k in sums}, counts["raw"] / len(rows))
            centre, coverage = cache[key]
            for k in self.mu:
                self.mu[k][int(c)] = centre[k]
            self.cover[int(c)] = coverage
        families = np.unique(pool.ctx_family[self.contexts])
        support = np.array([np.max([self.cover[int(c)] for c in self.contexts if pool.ctx_family[c] == f], axis=0)
                            for f in families])
        self.gene_keep = (support >= 0.5).sum(0) >= min(2, len(families))
        # Controls alone are allowed at held-out contexts; closure fixes incomparable CPM totals.
        basal = np.asarray(pool.basal, np.float64)
        self.basal_missing = ~np.isfinite(basal)
        closed = np.nan_to_num(basal, nan=0).clip(0)
        closed *= np.divide(1e6, closed.sum(1), out=np.ones(len(closed)), where=closed.sum(1) > 0)[:, None]
        self.log_basal = np.log1p(closed).astype(np.float32) / 8
        self.rank = P.quantile_ranks_np(self.log_basal).astype(np.float32)
        base_rows = np.unique(pool.ctx_basal[self.contexts])
        self.blind_log = self.log_basal[base_rows].mean(0)
        self.blind_rank = self.rank[base_rows].mean(0)
        self.blind_missing = self.basal_missing[base_rows].mean(0)
        priors = np.asarray(pool.prior_raw, float)
        seen_targets = np.unique(pool.row_target[self.rows])
        mean = finite_mean(priors[seen_targets])
        known = np.isfinite(priors)
        filled = np.where(known, priors, mean)
        sd = filled[seen_targets].std(0)
        self.priors = np.c_[np.clip((filled - mean) / np.maximum(sd, 1e-4), -5, 5), ~known].astype(np.float32)
        self.n_priors = self.priors.shape[1]
        # Family totals are fixed from visible contexts, then availability renormalizes per target.
        self.context_weight = np.maximum(pool.ctx_weight[self.contexts], 0).astype(float)
        for f in families:
            sel = pool.ctx_family[self.contexts] == f
            self.context_weight[sel] /= max(self.context_weight[sel].sum(), 1e-12)

    def read(self, key, rows, genes):
        rows = np.asarray(rows, int)
        if not self.visible[rows].all():
            raise P.LeakageError("Invisible outcomes requested as source/training feature")
        return np.asarray(self.pool.arrays[key][np.ix_(rows, genes)], np.float32)

    def _exclusion(self, target, genes):
        p = self.pool
        ex = genes == p.tgt_gene[target]
        cis = p.cis_index[p.cis_indptr[target]:p.cis_indptr[target + 1]]
        return ex | np.isin(genes, cis)

    def _profile(self, context, target, genes):
        """Direct profile or a source-local STRING fallback; never invisible partners."""
        p = self.pool
        row = self.lookup[context, target]
        fallback = row < 0
        if not fallback:
            rows, edge = np.array([row]), np.ones(1)
        else:
            a, b = p.partner_indptr[target:target + 2]
            partners = p.partner_index[a:b]
            scores = p.partner_score[a:b]
            keep = (partners != target) & (self.lookup[context, partners] >= 0)
            if np.isfinite(p.tgt_tss[target]):
                keep &= ~((p.tgt_chrom[partners] == p.tgt_chrom[target]) &
                          (np.abs(p.tgt_tss[partners] - p.tgt_tss[target]) <= 5000))
            partners, scores = partners[keep], scores[keep]
            order = np.lexsort((partners, -scores))[:self.max_partners]
            partners, edge = partners[order], scores[order]
            rows = self.lookup[context, partners]
        n_genes = len(genes)
        if len(rows) == 0:
            return np.zeros(n_genes), np.zeros(n_genes, bool), np.ones(n_genes), 0., 0., False, fallback
        sh, se = (self.read(k, rows, genes) for k in ("shrunk", "se"))
        mask = np.isfinite(sh) & np.isfinite(se) & (se > 0)
        for i, r in enumerate(rows):
            mask[i] &= ~self._exclusion(p.row_target[r], genes)
        values = sh - self.mu["shrunk"][int(context)][genes]
        cell_rel = p.row_ncells[rows] / (p.row_ncells[rows] + 100)
        cell_rel = np.nan_to_num(cell_rel, nan=0).clip(0, 1)
        weight = mask * (edge * cell_rel)[:, None]
        den = weight.sum(0)
        w = np.divide(weight, den, out=np.zeros_like(weight), where=den > 0)
        x = (w * np.where(mask, values, 0)).sum(0)
        variance = (w ** 2 * np.where(mask, se ** 2, 0)).sum(0) * p.ctx_se_factor[context]
        if fallback:
            x *= .1
            variance *= .01
        own = p.row_own[rows, 0]
        good_depth = np.isfinite(own)
        depth = np.average(-own[good_depth], weights=(edge * cell_rel)[good_depth]) if good_depth.any() and (edge * cell_rel)[good_depth].sum() > 0 else 0
        return x, den > 0, np.sqrt(variance), float(np.average(cell_rel, weights=edge)), float(depth), bool(good_depth.any()), fallback

    def batch(self, targets, basal_rows, families, genes, *, device="cpu", blind=False, swap_basal=None, prior_permutation=None):
        p = self.pool
        targets, genes = np.asarray(targets, int), np.asarray(genes, int)
        basal_rows, families = np.asarray(basal_rows, int), np.asarray(families, int)
        B, S, G = len(targets), len(self.contexts), len(genes)
        value, mask, reliability = np.zeros((B, S, G), np.float32), np.zeros((B, S, G), bool), np.zeros((B, S, G), np.float32)
        features = np.zeros((B, S, G, 20), np.float32)
        axis = p.genes_axis[genes]
        for i, t in enumerate(targets):
            b = int(basal_rows[i] if swap_basal is None else swap_basal)
            dl = self.blind_log if blind else self.log_basal[b]
            dr = self.blind_rank if blind else self.rank[b]
            dm = self.blind_missing if blind else self.basal_missing[b]
            ta = p.tgt_axis[t]
            for j, c in enumerate(self.contexts):
                if families[i] >= 0 and p.ctx_family[c] == families[i]:
                    continue
                x, ok, se, rel, depth, depth_ok, fallback = self._profile(int(c), int(t), genes)
                ok &= self.gene_keep[genes] & ~self._exclusion(t, genes)
                sb = p.ctx_basal[c]
                sl, sr, sm = self.log_basal[sb], self.rank[sb], self.basal_missing[sb]
                partner_ids = p.partner_index[p.partner_indptr[t]:p.partner_indptr[t + 1]]
                partner_axis = p.tgt_axis[partner_ids]
                partner_axis = partner_axis[partner_axis >= 0]
                pathway_distance = float(np.mean((dr[partner_axis] - sr[partner_axis]) ** 2)) if len(partner_axis) else 0.
                f = [dl[axis], sl[axis], dr[axis], sr[axis], dr[axis] - sr[axis],
                     dm[axis], sm[axis], np.tanh(x), np.log1p(se), np.full(G, rel),
                     np.full(G, np.mean((dr - sr) ** 2)), np.full(G, dl[ta] if ta >= 0 else 0),
                     np.full(G, sl[ta] if ta >= 0 else 0), np.full(G, dr[ta] - sr[ta] if ta >= 0 else 0),
                     np.full(G, ta >= 0), np.full(G, np.clip(depth, -1, 6) / 3),
                     np.full(G, depth_ok), np.full(G, fallback), np.full(G, self.context_weight[j]), np.full(G, pathway_distance)]
                features[i, j] = np.stack(f, -1)
                value[i, j], mask[i, j] = np.where(ok, x, 0), ok
                reliability[i, j] = ok * rel * self.context_weight[j]
        # Each represented family receives equal total cell-reliability mass, without erasing tokens.
        for f in np.unique(p.ctx_family[self.contexts]):
            group = p.ctx_family[self.contexts] == f
            den = reliability[:, group].sum(1, keepdims=True)
            family_rel = np.max(features[..., 9][:, group] * mask[:, group], axis=1, keepdims=True)
            reliability[:, group] = np.divide(reliability[:, group], den, out=np.zeros_like(reliability[:, group]), where=den > 0) * family_rel
        pri = self.priors[targets if prior_permutation is None else np.asarray(prior_permutation)[targets]]
        return {"value": torch.as_tensor(value, device=device), "mask": torch.as_tensor(mask, device=device),
                "reliability": torch.as_tensor(reliability, device=device), "features": torch.as_tensor(features, device=device),
                "priors": torch.as_tensor(pri, device=device)}

    def labels(self, rows, genes, *, truth=False, centres=None):
        p = self.pool
        rows = np.asarray(rows, int)
        if truth:
            if self.visible[rows].any():
                raise P.LeakageError("Visible rows passed as held-out truth")
            raw, se = (np.asarray(p.arrays[k][np.ix_(rows, genes)], np.float32) for k in ("raw", "se"))
        else:
            raw, se = (self.read(k, rows, genes) for k in ("raw", "se"))
        mu = self.mu["raw"] if centres is None else centres
        raw -= np.stack([mu[int(c)][genes] for c in p.row_context[rows]])
        keep = np.isfinite(raw) & np.isfinite(se) & (se > 0) & self.gene_keep[genes]
        for i, t in enumerate(p.row_target[rows]):
            keep[i] &= ~self._exclusion(t, genes)
        return np.where(keep, raw, 0), keep, se


class SourceAttention(nn.Module):
    """Shared biology-conditioned attention, exact baseline at zero initialization."""
    def __init__(self, n_priors):
        super().__init__()
        self.prior = nn.Sequential(nn.Linear(n_priors, 32), nn.GELU(), nn.Linear(32, 16))
        self.token = nn.Sequential(nn.Linear(20 + 16, 32), nn.GELU(), nn.Linear(32, 32), nn.GELU(), nn.Linear(32, 2))
        nn.init.zeros_(self.token[-1].weight)
        nn.init.zeros_(self.token[-1].bias)

    def forward(self, batch, *, frozen=False):
        x, rel, mask = batch["value"], batch["reliability"], batch["mask"]
        baseline_w = rel / rel.sum(1, keepdim=True).clamp_min(1e-12)
        baseline = (baseline_w * x).sum(1)
        if frozen:
            return {"prediction": baseline, "baseline": baseline, "support": mask.any(1), "weights": baseline_w}
        prior = self.prior(batch["priors"])[:, None, None].expand(*x.shape, 16)
        logits, gate = self.token(torch.cat([batch["features"], prior], -1)).unbind(-1)
        weights = rel * torch.exp(2 * torch.tanh(logits))
        weights = weights / weights.sum(1, keepdim=True).clamp_min(1e-12)
        learned = (weights * x * (1 + .25 * torch.tanh(gate))).sum(1)
        return {"prediction": .5 * baseline + .5 * learned, "baseline": baseline,
                "support": mask.any(1), "weights": weights}


def directional_loss(out, y, keep):
    """Same-context contrastive learning; no trainable amplitude can win by collapsing."""
    # Outcome availability and prediction coverage are distinct. A missing source predicts
    # zero; it cannot erase a gene measured in every truth. All pairs share the label mask.
    keep = keep.all(0, keepdim=True).expand_as(keep)
    pred = out["prediction"] * keep
    truth = y * keep
    base = out["baseline"] * keep
    valid = (keep.sum(1) >= 10) & (truth.norm(dim=1) > 1e-6) & (base.norm(dim=1) > 1e-6)
    if not valid.any():
        return None, 0
    pred, truth, base = pred[valid], truth[valid], base[valid]
    pn, yn = F.normalize(pred, dim=1, eps=1e-8), F.normalize(truth, dim=1, eps=1e-8)
    cosine = 1 - (pn * yn).sum(1).mean()
    contrastive = F.cross_entropy(pn @ yn.T / .2, torch.arange(len(pn), device=pn.device))
    anchor = ((pred - base).square().sum(1) / base.square().sum(1).clamp_min(1e-8)).mean()
    return cosine + .25 * contrastive + .01 * anchor, int(valid.sum())
