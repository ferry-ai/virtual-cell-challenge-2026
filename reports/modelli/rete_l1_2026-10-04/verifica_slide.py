"""Check of the count move on a few real blocks (PROTOCOLLO.md §1), before the full generation.

For sampled (context, target) blocks generated exactly as stage 45 does (t34 effects, x2, same seed stream is NOT
reproduced here: an independent rng), it measures, before and after the move:
  the mean per-cell CPM log2FC against the controls vs the Rete L1 target (on the active genes);
  Wilcoxon (Mann-Whitney on log1p CPM, against 4,000 control cells) BH calls at 0.05: Jaccard before/after, share changed;
  gene totals (must be identical) and stored entries.
Usage: python verifica_slide.py --targets <l1_obiettivi dir> --effects <effects_t34 dir> --controls <raw/controls>
       --out <json> [--blocks 6]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import scipy.sparse as sp
from scipy.stats import mannwhitneyu

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE))
from genera_l1 import Targets  # noqa: E402
from vcc2026.inference import predicted_profile, read_basal_profile  # noqa: E402
from vcc2026.sampling import resample_library_sizes, sample_counts  # noqa: E402


def controls_subset(path: Path, n: int, rng) -> sp.csr_matrix:
    with h5py.File(path, "r") as f:
        indptr = f["X/indptr"][:].astype(np.int64)
        n_cells, n_genes = len(indptr) - 1, int(f["X"].attrs["shape"][1])
        pick = np.sort(rng.choice(n_cells, n, replace=False))
        data, idx = f["X/data"], f["X/indices"]
        rows = [sp.csr_matrix((data[indptr[i]:indptr[i + 1]], idx[indptr[i]:indptr[i + 1]],
                               [0, indptr[i + 1] - indptr[i]]), shape=(1, n_genes)) for i in pick]
    return sp.vstack(rows).tocsr()


def bh(p: np.ndarray) -> np.ndarray:
    n = len(p)
    o = np.argsort(p)
    q = p[o] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.minimum(q, 1)
    return out


def calls(block: sp.csr_matrix, ctrl: sp.csr_matrix, genes: np.ndarray):
    def lcpm(m):
        L = np.asarray(m.sum(1)).ravel()
        return np.log1p(m[:, genes].toarray() / L[:, None] * 1e6)
    a, b = lcpm(block), lcpm(ctrl)
    p = mannwhitneyu(a, b, axis=0).pvalue
    p = np.where(np.isfinite(p), p, 1.0)
    return bh(p) < 0.05, np.sign(a.mean(0) - b.mean(0))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", type=Path, required=True)
    ap.add_argument("--effects", type=Path, required=True)
    ap.add_argument("--controls", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--blocks", type=int, default=6)
    a = ap.parse_args()
    rng = np.random.default_rng(7)
    tg = Targets(a.targets, 18533)
    res = []
    for ctx in "ABC":
        prof = read_basal_profile(a.controls / f"context_{ctx}.h5ad")
        ctrl = controls_subset(a.controls / f"context_{ctx}.h5ad", 4000, rng)
        z = np.load(a.effects / f"effects_{ctx}.npz", allow_pickle=False)
        rows, gidx, m, ref, own = tg.ctx[ctx]
        names = list(map(str, z["targets"]))
        for ti in rng.choice(len(names), a.blocks // 3 or 1, replace=False):
            t = names[ti]
            delta = 2.0 * z["lfc"][ti] / np.log(2.0)
            profile, _ = predicted_profile(prof.profile, delta, z["observed"][ti].astype(bool))
            libs = resample_library_sizes(prof.library_sizes, 400, rng)
            block = sample_counts(profile, libs, rng, max_stored_per_cell=13194, max_counts_per_cell=10**9)
            slid, st = tg.apply(block, ctx, t)
            act = gidx[gidx != own[rows[t]]]

            def mean_lfc(bl):
                L = np.asarray(bl.sum(1)).ravel()
                mc = np.asarray(sp.diags(1e6 / L) @ bl[:, act]).mean(0) if False else \
                    np.asarray((sp.diags(1e6 / L) @ bl[:, act]).mean(0)).ravel()
                return np.log2((mc + 1e-9) / (ref[act] + 1e-9))
            goal = m[rows[t]][np.searchsorted(gidx, act)]
            l0, l1 = mean_lfc(block), mean_lfc(slid)
            c0, s0 = calls(block, ctrl, act)
            c1, s1 = calls(slid, ctrl, act)
            union = (c0 | c1).sum()
            res.append({
                "context": ctx, "target_index": int(ti), **st,
                "gene_totals_equal": bool(np.array_equal(np.asarray(block.sum(0)).ravel(),
                                                         np.asarray(slid.sum(0)).ravel())),
                "nnz_equal": bool(block.nnz == slid.nnz),
                "mae_to_goal_before": float(np.mean(np.abs(l0 - goal))),
                "mae_to_goal_after": float(np.mean(np.abs(l1 - goal))),
                "sign_agree_goal_after": float(np.mean(np.sign(l1) == np.sign(goal))),
                "calls_before": int(c0.sum()), "calls_after": int(c1.sum()),
                "calls_jaccard": float((c0 & c1).sum() / union) if union else 1.0,
                "called_rank_direction_changed": int(((s0 != s1) & (c0 & c1)).sum())})
            print(json.dumps(res[-1]), flush=True)
    a.out.write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
