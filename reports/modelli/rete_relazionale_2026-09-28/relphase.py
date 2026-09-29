"""RelPhase: pool.Phase plus the relational inputs of the relational network (DISEGNO.md §2), every one derived
from the phase's visible rows alone. numpy and torch; imported by relnet.py, train_rel.py and selftest_rel.py.

The r1 files (reports/modelli/rete_contesti_2026-09-27/net.py, pool.py, train.py) are imported by path and never
edited: RETE_CONTESTI_CODE, else this folder (a flat Kaggle copy), else ../rete_contesti_2026-09-27.

What a RelPhase adds to pool.Phase (with `rel` settings; without them it is pool.Phase unchanged):
* gene cards rho0 [G, K]: a weighted randomized SVD of the visible family profiles P, then a varimax rotation.
  - rows: the profiles of targets responsive in their family (the maximum over the family's visible rows of
    `row_strength`, genes with |Z| >= 3, reaches --rel-min-strength); weight PW, normalised so that each family
    sums to 1; the row enters as sqrt(weight) x profile;
  - every profile's own target gene and cis window (pool.exclusion_mask) and every gene outside R are set to 0,
    so a target's card never carries its own knockdown direction;
  - randomized range finder (fixed generator --rel-card-seed, K + 16 columns, --rel-svd-iters power iterations,
    blockwise, so X is never materialised), SVD of the small projected matrix, varimax on the top K right
    singular vectors; components ordered by explained weighted variance, signs so that the sum of cubed loadings
    is positive. Rotation keeps the span and the orthonormality (the soft modules);
  - --rel-card-null bins (ablation): the card rows permuted among the genes of R within ten bins of the
    training-average log CPM (fixed seed);
* omega_mod [G, K]: per module the top --rel-omega-top genes by |rho0|, weights |rho0| normalised to sum 1 (the
  basal module activity is the omega-weighted mean of the drank channel of the controls);
* the card of a target: rho0 of its gene, unit norm, when the gene is stored, in R and has a non-zero card
  (card_ok); else 0;
* the card-neighbour table: for each target with a card, the --rel-nb visible targets (seen in the phase, with a
  card) of highest card cosine, never itself nor a target whose TSS is within --cis-group-bp on its chromosome;
* Qc / QcW / qcf_row: pool.Phase._partners' code driven by that table instead of STRING (each neighbour's own gene
  left out; only neighbours with a profile in the family enter): a hidden target is never a neighbour, because
  only seen targets are candidates.
`batch` adds qc, qc_ok (own family excluded, masked like m and q), rho_t (the target's card), t_rel (card_ok) and
priors_u (the target's standardised priors). With `rel_target_map` set (the tperm arm) these relational inputs
come from another target; m and q stay the row's own.
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def network_dir() -> Path:
    env = os.environ.get("RETE_CONTESTI_CODE", "")
    for d in ([Path(env)] if env else []) + [HERE, HERE.parent / "rete_contesti_2026-09-27"]:
        if all((d / f).exists() for f in ("net.py", "pool.py", "train.py")):
            return d.resolve()
    raise SystemExit("net.py, pool.py and train.py (reports/modelli/rete_contesti_2026-09-27) not found: copy them "
                     "beside this file or set RETE_CONTESTI_CODE")


NET_DIR = network_dir()
for _d in (NET_DIR, HERE):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

import pool as P  # noqa: E402

BasePhase = P.Phase          # the original class, whatever pool.Phase is later routed to
SETTINGS = None              # RelSettings while relnet.install() is active
CREATED: list = []           # rel_info of every RelPhase built while installed (for rel_config.json)


@dataclass
class RelSettings:
    k: int = 32                      # card dimensions (modules)
    nb: int = 16                     # card neighbours per target (0: no qc)
    min_strength: float = 10.0       # responsive: max row strength in the family >= this
    card_null: str = "none"          # "bins": ablation, card rows permuted within expression bins
    omega_top: int = 200             # genes per module in the basal activity
    cis_bp: float = 10000.0          # a neighbour is never within this of the target's TSS
    card_seed: int = 0               # generator of the randomized SVD, the null permutation, the tperm derangement
    oversample: int = 16
    svd_iters: int = 4
    block: int = 2048

    def to_dict(self) -> dict:
        return asdict(self)


def varimax(phi: np.ndarray, gamma: float = 1.0, max_iter: int = 200, tol: float = 1e-8) -> np.ndarray:
    """The K x K orthogonal rotation R maximising the varimax criterion of phi @ R (phi [p, K], float64)."""
    p, k = phi.shape
    rot = np.eye(k)
    d = 0.0
    if k < 2 or p == 0:
        return rot
    for _ in range(max_iter):
        d_old = d
        lam = phi @ rot
        u, s, vh = np.linalg.svd(phi.T @ (lam ** 3 - (gamma / p) * lam @ np.diag(np.diag(lam.T @ lam))))
        rot = u @ vh
        d = float(s.sum())
        if d_old != 0.0 and d / d_old < 1.0 + tol:
            break
    return rot


def orth(x):
    import torch
    q, _ = torch.linalg.qr(x)
    return q


class RelPhase(BasePhase):
    """pool.Phase and the relational inputs (module docstring). `rel` defaults to the installed SETTINGS."""

    def __init__(self, pool, train_rows, opts=None, device="cpu", log=print, rel: RelSettings | None = None):
        self.rel = rel if rel is not None else SETTINGS
        self.rel_target_map = None
        super().__init__(pool, train_rows, opts, device, log)
        if self.rel is None:
            return
        t0 = time.time()
        self._cards()
        self._card_table()
        self._qcard()
        self._rel_to_device()
        info = self.rel_info
        info["seconds"] = round(time.time() - t0, 1)
        CREATED.append(info)
        log(f"relational phase: {info['card_profiles']} responsive profiles in the cards (of {self.P.shape[0]}), "
            f"K {info['k']}, top singular values {[round(v, 4) for v in info['singular_values'][:4]]}; "
            f"{info['targets_with_card']} targets with a card, {info['targets_with_neighbours']} with neighbours; "
            f"card-neighbour profiles {self.Qc.shape[0]}; {info['seconds']} s")

    # ---- cards
    def _profile_index(self):
        """(slot, target) of every row of P."""
        prof_s = np.full(self.P.shape[0], -1, dtype=np.int64)
        prof_t = np.full(self.P.shape[0], -1, dtype=np.int64)
        for fs in range(self.F):
            tg = np.flatnonzero(self.pf_row[fs] >= 0)
            prof_s[self.pf_row[fs, tg]] = fs
            prof_t[self.pf_row[fs, tg]] = tg
        return prof_s, prof_t

    def _card_rows(self):
        """The profile rows entering the cards and their weights (each family sums to 1)."""
        pool, s = self.pool, self.rel
        nT = len(pool.target_names)
        prof_s, prof_t = self._profile_index()
        strength = np.zeros((self.F, nT), dtype=np.float32)
        for c in self.contexts:
            fs = int(self.slot[pool.ctx_family[c]])
            r = self.visible_rows_of(c)
            np.maximum.at(strength[fs], pool.row_target[r], self.row_strength[r])
        responsive = (prof_s >= 0) & (strength[np.clip(prof_s, 0, None), np.clip(prof_t, 0, None)] >= s.min_strength)
        w = np.where(responsive, self.PW.astype(np.float64), 0.0)
        fam_weight = {}
        for fs in range(self.F):
            sel = prof_s == fs
            tot = float(w[sel].sum())
            if tot > 0:
                w[sel] /= tot
            fam_weight[self.pool.family_names[self.families[fs]]] = {"profiles": int((sel & (w > 0)).sum()),
                                                                     "of": int(sel.sum())}
        used = np.flatnonzero(w > 0)
        return used, w[used], prof_t[used], fam_weight

    def _cards(self) -> None:
        import torch
        pool, s, G = self.pool, self.rel, self.pool.G
        d = self.device
        used, w, tgt, fam_weight = self._card_rows()
        n = int(used.size)
        k = int(min(s.k, max(n, 1), int(self.R.sum())))
        if n < 2 or k < 1:
            raise ValueError(f"only {n} responsive profiles: no gene cards (lower --rel-min-strength)")
        # own gene and cis window of each profile's target, as (local row, column) pairs sorted by row
        rr, cc = [], []
        for a in range(0, n, 1024):
            m = pool.exclusion_mask(tgt[a:a + 1024])
            i, j = np.nonzero(m)
            rr.append(i + a)
            cc.append(j)
        rr, cc = np.concatenate(rr), np.concatenate(cc)
        ptr = np.searchsorted(rr, np.arange(n + 1), side="left")
        t_rows = torch.from_numpy(used).to(d)
        t_sqw = torch.from_numpy(np.sqrt(w).astype(np.float32)).to(d)
        t_rr, t_cc = torch.from_numpy(rr).to(d), torch.from_numpy(cc).to(d)
        keep_g = self.t_R.unsqueeze(0)
        blk = int(s.block)

        def xb(a: int, b: int):
            x = self.t_P[t_rows[a:b]].float()
            x = torch.where(torch.isfinite(x) & keep_g, x, torch.zeros_like(x))
            lo, hi = int(ptr[a]), int(ptr[b])
            if hi > lo:
                x[t_rr[lo:hi] - a, t_cc[lo:hi]] = 0.0
            return x * t_sqw[a:b].unsqueeze(1)

        def xa(A):                                   # X @ A
            return torch.cat([xb(a, min(a + blk, n)) @ A for a in range(0, n, blk)])

        def xtb(B):                                  # X^T @ B
            out = torch.zeros(G, B.shape[1], device=d)
            for a in range(0, n, blk):
                out += xb(a, min(a + blk, n)).T @ B[a:min(a + blk, n)]
            return out

        ell = int(min(k + s.oversample, n, G))
        gen = torch.Generator().manual_seed(int(s.card_seed))
        omega = torch.randn(G, ell, generator=gen).to(d)
        y = xa(omega)
        for _ in range(int(s.svd_iters)):
            y = xa(orth(xtb(orth(y))))
        q = orth(y)
        bt = xtb(q)                                  # X^T Q  [G, ell]; X ~ Q (X^T Q)^T
        _, sv, vh = torch.linalg.svd(bt.T, full_matrices=False)
        v = vh[:k].T.double().cpu().numpy()          # [G, k], orthonormal columns, rows outside R exactly 0
        sv = sv[:k].double().cpu().numpy()
        rows_r = np.flatnonzero(self.R)
        rot = varimax(v[rows_r])
        rho = v @ rot
        var = (xa(torch.from_numpy(rho.astype(np.float32)).to(d)) ** 2).sum(dim=0).double().cpu().numpy()
        order = np.argsort(-var, kind="stable")
        rho, var = rho[:, order], var[order]
        sign = np.sign((rho ** 3).sum(axis=0))
        rho = rho * np.where(sign == 0, 1.0, sign)[None, :]
        if s.card_null == "bins":
            expr = self.blind_row[pool.genes_axis, 0].astype(np.float64) * 5.0     # training-average log1p CPM
            edges = np.quantile(expr[rows_r], np.linspace(0, 1, 11)[1:-1])
            bins = np.digitize(expr[rows_r], edges)
            prng = np.random.default_rng([int(s.card_seed), 101])
            perm = np.arange(G)
            for b in np.unique(bins):
                g = rows_r[bins == b]
                perm[g] = prng.permutation(g)
            rho = rho[perm]
        elif s.card_null != "none":
            raise ValueError(f"card_null {s.card_null!r}")
        self.rho0 = rho.astype(np.float32)
        a = np.abs(self.rho0).astype(np.float64)
        a[~self.R] = 0.0
        om = np.zeros_like(a)
        for j in range(k):
            top = np.argsort(-a[:, j], kind="stable")[:int(s.omega_top)]
            top = top[a[top, j] > 0]
            if top.size:
                om[top, j] = a[top, j] / a[top, j].sum()
        self.omega_mod = om.astype(np.float32)
        tg = pool.tgt_gene
        ok = tg >= 0
        ok[ok] &= self.R[tg[ok]]
        rows = self.rho0[np.clip(tg, 0, None)].astype(np.float64)
        nrm = np.linalg.norm(rows, axis=1)
        ok &= nrm > 1e-12
        self.card = np.where(ok[:, None], rows / np.where(nrm > 1e-12, nrm, 1.0)[:, None], 0.0).astype(np.float32)
        self.card_ok = ok
        self.card_rows, self.card_row_weight = used, w
        tot_var = float(sum(float((xb(a_, min(a_ + blk, n)) ** 2).sum()) for a_ in range(0, n, blk)))
        self.rel_info = {"k": k, "card_profiles": n, "profiles": int(self.P.shape[0]), "families": fam_weight,
                         "singular_values": sv.tolist(), "explained_share": (var / max(tot_var, 1e-30)).tolist(),
                         "card_null": s.card_null, "settings": s.to_dict()}

    # ---- card-neighbour table
    def _card_table(self) -> None:
        pool, s = self.pool, self.rel
        nT = len(pool.target_names)
        lists = [[] for _ in range(nT)]
        if s.nb > 0:
            cand = np.flatnonzero(self.seen_target & self.card_ok)
            cc = self.card[cand]
            ok_tss = np.isfinite(pool.tgt_tss)
            chrom, tss = pool.tgt_chrom, pool.tgt_tss
            bp = float(s.cis_bp)

            def near(t: int, n: np.ndarray) -> np.ndarray:
                if not ok_tss[t]:
                    return np.zeros(n.size, dtype=bool)
                return ok_tss[n] & (chrom[n] == chrom[t]) & (np.abs(np.where(ok_tss[n], tss[n], 0.0) - tss[t]) <= bp)

            with_card = np.flatnonzero(self.card_ok)
            extra = int(min(cand.size, s.nb + 64))
            for a in range(0, with_card.size, 1024):
                blk = with_card[a:a + 1024]
                sims = self.card[blk] @ cc.T                                     # [b, n_cand] float32
                if extra < cand.size:
                    part = np.argpartition(-sims, extra - 1, axis=1)[:, :extra]
                else:
                    part = np.tile(np.arange(cand.size), (blk.size, 1))
                for i, t in enumerate(blk):
                    def pick(pos):
                        sv = sims[i, pos]
                        pos = pos[np.lexsort((cand[pos], -sv))]
                        nb = cand[pos]
                        nb = nb[(nb != t) & ~near(int(t), nb)]
                        return nb[:s.nb]
                    got = pick(part[i])
                    if got.size < s.nb and extra < cand.size:
                        got = pick(np.arange(cand.size))
                    lists[int(t)] = [int(x) for x in got]
        self.card_indptr, self.card_index = P.csr(lists, dtype=np.int64)
        n_with = sum(1 for x in lists if x)
        self.rel_info.update({"targets_with_card": int(self.card_ok.sum()), "targets_with_neighbours": int(n_with),
                              "neighbour_candidates": int((self.seen_target & self.card_ok).sum())})

    def _qcard(self) -> None:
        """pool.Phase._partners, driven by the card-neighbour table (its code, with the table as an argument)."""
        pool, G = self.pool, self.pool.G
        nT, K = len(pool.target_names), max(int(self.rel.nb), 0)
        ip, ix = self.card_indptr, self.card_index
        self.qcf_row = np.full((self.F, nT), -1, dtype=np.int64)
        per_family = []
        for fs in range(self.F):
            have = self.pf_row[fs] >= 0
            tlist, plist = [], []
            for t in range(nT):
                ps = [int(p) for p in ix[ip[t]:ip[t + 1]] if have[p] and p != t][:K]
                if ps:
                    tlist.append(t)
                    plist.append(ps)
            per_family.append((tlist, plist))
        total = int(sum(len(t) for t, _ in per_family))
        self.Qc = np.empty((total, G), dtype=np.float16)
        self.QcW = np.zeros(total, dtype=np.float32)
        start, blk = 0, 128
        for fs, (tlist, plist) in enumerate(per_family):
            for b in range(0, len(tlist), blk):
                ts, ps = tlist[b:b + blk], plist[b:b + blk]
                width = max(len(p) for p in ps)
                idx = np.full((len(ts), width), -1, dtype=np.int64)
                for i, p in enumerate(ps):
                    idx[i, :len(p)] = self.pf_row[fs, p]
                vals = self.P[np.clip(idx, 0, None)].astype(np.float32)          # [b, width, G]
                valid = np.isfinite(vals) & (idx >= 0)[:, :, None]
                own = np.full(idx.shape, -1, dtype=np.int64)
                for i, p in enumerate(ps):
                    own[i, :len(p)] = pool.tgt_gene[p]
                ii, kk = np.nonzero(own >= 0)
                valid[ii, kk, own[ii, kk]] = False
                cnt = valid.sum(axis=1)
                q = np.full((len(ts), G), np.nan, dtype=np.float32)
                np.divide(np.where(valid, vals, 0.0).sum(axis=1), cnt, out=q, where=cnt > 0)
                self.Qc[start:start + len(ts)] = q.astype(np.float16)
                w = np.where(idx >= 0, self.PW[np.clip(idx, 0, None)], 0.0)
                self.QcW[start:start + len(ts)] = w.sum(axis=1) / np.maximum((idx >= 0).sum(axis=1), 1)
                self.qcf_row[fs, ts] = start + np.arange(len(ts))
                start += len(ts)

    def _rel_to_device(self) -> None:
        import torch
        d = self.device
        self.t_Qc = torch.from_numpy(self.Qc).to(d)
        self.t_card = torch.from_numpy(self.card).to(d)
        self.t_card_ok = torch.from_numpy(self.card_ok.astype(np.float32)).to(d)
        self.t_rho0 = torch.from_numpy(self.rho0).to(d)
        self.t_omega_mod = torch.from_numpy(self.omega_mod).to(d)

    # ---- what a step reads
    def rel_targets(self, tgt: np.ndarray) -> np.ndarray:
        return tgt if self.rel_target_map is None else self.rel_target_map[tgt]

    def qc_of(self, spec, excl):
        """(qc, qc_ok) of the rows of `spec`: the card-neighbour profile mixed over the allowed families (never the
        row's own), masked on R and the row target's own gene and cis window, as m and q are."""
        import torch
        tr = self.rel_targets(spec.target)
        allowed = self._allowed(spec.family, False)
        idx = self.qcf_row[:, tr].T.copy()
        idx[~allowed] = -1
        w = np.where(idx >= 0, self.QcW[np.clip(idx, 0, None)] if self.QcW.size else 0.0, 0.0).astype(np.float32)
        qc, ok = self._mix(self.t_Qc, idx, w)
        ok = ok & self.t_R.unsqueeze(0) & ~excl
        return torch.where(ok, qc, torch.zeros_like(qc)), ok

    def batch(self, spec, **kw):
        out = super().batch(spec, **kw)
        if self.rel is None:
            return out
        import torch
        d = self.device
        tr = self.rel_targets(spec.target)
        out["qc"], out["qc_ok"] = self.qc_of(spec, out["excl"])
        ti = torch.from_numpy(np.asarray(tr, dtype=np.int64)).to(d)
        out["rho_t"] = self.t_card[ti]
        out["t_rel"] = self.t_card_ok[ti]
        out["priors_u"] = torch.from_numpy(self.prior_z[tr]).to(d)
        return out
