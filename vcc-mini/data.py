"""Mini dataset in memory (on the GPU), fold construction and batches.

A sample is a pair (target t, query line q). Its inputs are what the final phase provides:
the control profile of q, and the effects of t already measured in *other* cell lines
(public sources). Its label is the effect of t measured in q.

Regimes on the held-out line H of a fold (targets are split by `fold` in targets.csv):
    CT  target never trained on, its source effects given as input   <- the final-phase case
    J   target never trained on, no source effects (gene descriptors only)
    C   target trained on in other lines, H new
Leakage rules (docs/GENERALIZZAZIONE.md of the team repo): the held-out line's perturbed
profiles never enter training, normalisation or descriptors; held-out targets' effects never
enter training or descriptors (readout SVD) in any line. tests/test_leakage.py checks them.

Sources are cell-line *groups*, not experiments (P3): the two K562 experiments enter as one
source, their effects averaged with weights on cells, so K562 is never counted twice and the
number of sources a query sees is at most (number of groups - 1).

Control features use basal_common.npy when present (P4): log1p(cpm) with the library summed
over the common genes only, so that the experiments' different gene panels do not shift the
controls of one line against another. The effects keep the full-library normalisation.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch


@dataclass
class Fold:
    held_group: str
    target_fold: int


class Mini:
    def __init__(self, root: Path, device: str = "cuda"):
        root = Path(root)
        self.device = device
        self.genes = pd.read_csv(root / "genes.csv").gene.to_numpy()
        self.lines = pd.read_csv(root / "lines.csv")
        self.keys = list(self.lines.line)
        self.group = dict(zip(self.lines.line, self.lines.group))
        self.groups = sorted(set(self.group.values()))
        self.lines_of = {g: [i for i, k in enumerate(self.keys) if self.group[k] == g] for g in self.groups}
        self.s_max = len(self.groups) - 1
        self.targets = pd.read_csv(root / "targets.csv")
        self.fold_of = dict(zip(self.targets.target, self.targets.fold))
        self.gidx = {g: i for i, g in enumerate(self.genes)}
        self.G = len(self.genes)
        common = root / "basal_common.npy"
        self.basal_file = common.name if common.exists() else "basal.npy"
        self.basal = torch.tensor(np.load(root / self.basal_file), device=device)      # [L, G]
        self.delta, self.row, self.meta = [], [], []
        for key in self.keys:
            z = np.load(root / f"effects_{key}.npz")
            self.delta.append(torch.tensor(z["delta"], device=device))
            self.row.append({t: i for i, t in enumerate(z["targets"])})
            n = np.nan_to_num(z["n_cells"], nan=100.0)
            kd = np.nan_to_num(z["kd"], nan=0.0)
            self.meta.append(dict(n=n, kd=kd))
        # Global similarity of control profiles, a transferable scalar per (source, query).
        b = self.basal - self.basal.mean(1, keepdim=True)
        b = b / b.norm(dim=1, keepdim=True)
        self.basal_sim = (b @ b.T).cpu().numpy()

    # ----------------------------------------------------------------- fold bookkeeping
    def split(self, fold: Fold, val_share: float = 0.1, seed: int = 0):
        """Training pairs, inner-validation pairs and held-out evaluation sets."""
        rng = np.random.default_rng(seed)
        train_lines = [i for i, k in enumerate(self.keys) if self.group[k] != fold.held_group]
        held_lines = [i for i, k in enumerate(self.keys) if self.group[k] == fold.held_group]
        test_t = {t for t, f in self.fold_of.items() if f == fold.target_fold}
        pool = sorted({t for li in train_lines for t in self.row[li]} - test_t)
        val_t = set(rng.choice(pool, size=int(len(pool) * val_share), replace=False))
        train_t = set(pool) - val_t
        pairs = lambda ts, lines: [(t, q) for q in lines for t in self.row[q] if t in ts]
        return dict(
            train_lines=train_lines, held_lines=held_lines,
            train=pairs(train_t, train_lines), val=pairs(val_t, train_lines),
            test_t=test_t, train_t=train_t, val_t=val_t,
        )

    def sources(self, t: str, q: int, allowed: list[int]) -> list[list[int]]:
        """Source groups for (t, q): per group of another line than q, the allowed lines that measured t."""
        gq = self.group[self.keys[q]]
        out = []
        for g in self.groups:
            if g == gq:
                continue
            ls = [s for s in self.lines_of[g] if s in allowed and t in self.row[s]]
            if ls:
                out.append(ls)
        return out

    def source_effect(self, t: str, ls: list[int]) -> torch.Tensor:
        """Cells-weighted mean effect of t over the experiments of one group."""
        n = np.array([self.meta[s]["n"][self.row[s][t]] for s in ls])
        d = torch.stack([self.delta[s][self.row[s][t]] for s in ls])
        w = torch.tensor(n / n.sum(), device=self.device, dtype=d.dtype)
        return (w[:, None] * d).sum(0)

    # ----------------------------------------------------------------- descriptors
    def readout_svd(self, train_lines: list[int], train_t: set, k: int = 64):
        """Gene descriptors from how each gene moves as a *readout* across training knockdowns.

        Rows: training targets in training lines only. The entry of a target's own gene in its
        own row (the on-target knockdown) is zeroed, so a gene's descriptor never contains its
        own perturbation: held-out targets and training targets are described the same way.
        Returns gene loadings [G, k] (V * S, scaled) and the basis V [G, k].
        """
        blocks = []
        for li in train_lines:
            rows = [(i, t) for t, i in self.row[li].items() if t in train_t]
            if not rows:
                continue
            M = self.delta[li][[i for i, _ in rows]].clone()
            for r, (_, t) in enumerate(rows):
                if t in self.gidx:
                    M[r, self.gidx[t]] = 0.0
            blocks.append(M)
        M = torch.cat(blocks)
        M = M - M.mean(0, keepdim=True)
        U, S, V = torch.svd_lowrank(M, q=k, niter=4)
        load = V * S / S[0]
        return load, V

    # ----------------------------------------------------------------- batches
    def batch(self, pairs, allowed_sources, gene_load, train=False, rng=None,
              p_nosrc=0.25, p_subset=0.3, src_override=None, max_src=None, line_centre=None):
        """Tensors for a list of (target, query-line) pairs.

        src_override='none' forces the J regime; max_src keeps a random subset of that many
        source groups (a sensitivity check, drawn with rng). line_centre {line: mean effect} adds
        "sc", the same slots filled with the cells-weighted centre of their lines (gamma = 1).
        """
        B, G, dev, S = len(pairs), self.G, self.device, self.s_max
        sd = torch.zeros(B, S, G, device=dev)
        sb = torch.zeros(B, S, G, device=dev)
        sm = torch.zeros(B, S, 3, device=dev)
        sc = torch.zeros(B, S, G, device=dev) if line_centre is not None else None
        mask = torch.zeros(B, S, dtype=torch.bool, device=dev)
        qb = torch.empty(B, G, device=dev)
        tf = torch.zeros(B, gene_load.shape[1] + 3, device=dev)
        y = torch.empty(B, G, device=dev)
        w = torch.empty(B, device=dev)
        gmask = torch.ones(B, G, dtype=torch.bool, device=dev)
        for b, (t, q) in enumerate(pairs):
            src = [] if src_override == "none" else self.sources(t, q, allowed_sources)
            if train and src:
                u = rng.random()
                if u < p_nosrc:
                    src = []
                elif u < p_nosrc + p_subset and len(src) > 1:
                    keep = rng.choice(len(src), size=rng.integers(1, len(src)), replace=False)
                    src = [src[i] for i in keep]
            if max_src is not None and len(src) > max_src:
                keep = rng.choice(len(src), size=max_src, replace=False)
                src = [src[i] for i in sorted(keep)]
            for j, ls in enumerate(src):
                n = np.array([self.meta[s]["n"][self.row[s][t]] for s in ls])
                kd = np.array([self.meta[s]["kd"][self.row[s][t]] for s in ls])
                sd[b, j] = self.source_effect(t, ls)
                sb[b, j] = self.basal[ls].mean(0)
                sm[b, j] = torch.tensor([np.log1p(n.sum()) / 7.0, float((kd * n).sum() / n.sum()),
                                         float(np.mean([self.basal_sim[s, q] for s in ls]))])
                mask[b, j] = True
                if sc is not None:
                    wn = n / n.sum()
                    sc[b, j] = sum(float(x) * line_centre[s] for x, s in zip(wn, ls))
            qb[b] = self.basal[q]
            y[b] = self.delta[q][self.row[q][t]]
            nq = float(self.meta[q]["n"][self.row[q][t]])
            w[b] = nq / (nq + 50.0)
            if t in self.gidx:
                g = self.gidx[t]
                gmask[b, g] = False                       # the scorer drops the own target gene
                tf[b, : gene_load.shape[1]] = gene_load[g]
                tf[b, -3] = 1.0
                tf[b, -2] = self.basal[q, g]
                tf[b, -1] = self.basal[allowed_sources, g].mean()
        out = dict(sd=sd, sb=sb, sm=sm, mask=mask, qb=qb, tf=tf, y=y, w=w, gmask=gmask)
        if sc is not None:
            out["sc"] = sc
        return out
