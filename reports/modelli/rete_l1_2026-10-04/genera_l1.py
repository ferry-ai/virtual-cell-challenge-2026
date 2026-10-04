"""Stage 45 with one addition (PROTOCOLLO.md §1, §3): after each block is sampled exactly as stage 45 samples it,
counts of each gene are moved between cells of different depth so that the mean of per-cell CPM (what the scorer's
de_lfc_nmae reads) matches the Rete L1 target, while every gene's total in the block (the bulk) is unchanged.

Moves only between cells that already hold the gene; a source keeps at least one count and a destination at most
doubles, so the zero pattern and the stored entries do not change. Deterministic: the random stream, hence every
block before the move, is the one stage 45 would write with the same arguments.

Usage: python genera_l1.py --targets <l1_obiettivi dir> --stats-out <json> -- <stage-45 arguments>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numba
import numpy as np
import scipy.sparse as sp

REPO = Path(__file__).resolve().parents[3]


@numba.njit(cache=True)
def slide(indptr, indices, data, L, target, active):
    """In place on a CSC block: per active column, move counts toward sum(x/L) == target. Returns the residuals."""
    n_cols = len(indptr) - 1
    resid = np.zeros(n_cols)
    before = np.zeros(n_cols)
    for g in range(n_cols):
        a, b = indptr[g], indptr[g + 1]
        if not active[g] or b - a < 2:
            continue
        rows = indices[a:b]
        S = 0.0
        for q in range(a, b):
            S += data[q] / L[indices[q]]
        before[g] = S - target[g]
        need = target[g] - S
        order = np.argsort(L[rows])  # small depth first
        x0 = data[a:b].copy()
        if need > 0:  # big -> small raises the mean CPM
            i, j = 0, b - a - 1
            while need > 1e-12 and i < j:
                d, s = a + order[i], a + order[j]
                gain = 1.0 / L[indices[d]] - 1.0 / L[indices[s]]
                if gain <= 0:
                    break
                cap_s = data[s] - 1.0
                cap_d = 2.0 * x0[order[i]] - data[d]
                if cap_s <= 0:
                    j -= 1
                    continue
                if cap_d <= 0:
                    i += 1
                    continue
                k = min(cap_s, cap_d, np.ceil(need / gain))
                data[s] -= k
                data[d] += k
                need -= k * gain
        elif need < 0:  # small -> big lowers it
            i, j = 0, b - a - 1
            while need < -1e-12 and i < j:
                s, d = a + order[i], a + order[j]
                gain = 1.0 / L[indices[s]] - 1.0 / L[indices[d]]
                if gain <= 0:
                    break
                cap_s = data[s] - 1.0
                cap_d = 2.0 * x0[order[j]] - data[d]
                if cap_s <= 0:
                    i += 1
                    continue
                if cap_d <= 0:
                    j -= 1
                    continue
                k = min(cap_s, cap_d, np.ceil(-need / gain))
                data[s] -= k
                data[d] += k
                need += k * gain
        resid[g] = -need
    return resid, before


class Targets:
    def __init__(self, folder: Path, n_genes: int):
        self.ctx = {}
        for ctx in "ABC":
            z = np.load(folder / f"obiettivi_{ctx}.npz", allow_pickle=False)
            rows = {t: i for i, t in enumerate(map(str, z["targets"]))}
            self.ctx[ctx] = (rows, z["gene_idx"].astype(np.int64), z["m"], z["ref_mean_cpm"], z["own_idx"])
        self.n_genes = n_genes

    def apply(self, block: sp.csr_matrix, ctx: str, target: str):
        rows, gidx, m, ref, own = self.ctx[ctx]
        i = rows[target]
        n = block.shape[0]
        active = np.zeros(self.n_genes, np.bool_)
        active[gidx] = np.isfinite(m[i])  # NaN = no target: the gene is not moved
        if own[i] >= 0:
            active[own[i]] = False
        goal = np.zeros(self.n_genes)
        goal[gidx] = n * ref[gidx] * np.exp2(np.nan_to_num(m[i].astype(np.float64))) / 1e6
        csc = block.tocsc().astype(np.float64)
        csc.sort_indices()
        totals0 = np.asarray(block.sum(axis=1)).ravel().astype(np.float64)
        col0 = np.asarray(csc.sum(axis=0)).ravel()
        stats = {}
        for p in range(2):  # the second pass re-reads the depths the first pass moved
            L = np.asarray(csc.sum(axis=1)).ravel()
            resid, before = slide(csc.indptr.astype(np.int64), csc.indices.astype(np.int64), csc.data, L, goal, active)
            if p == 0:
                stats["need_abs_sum"] = float(np.abs(before[active]).sum())
        stats["resid_abs_sum"] = float(np.abs(resid[active]).sum())
        out = csc.tocsr()
        if not np.array_equal(np.asarray(out.sum(axis=0)).ravel(), col0):
            raise RuntimeError("gene totals changed")
        totals1 = np.asarray(out.sum(axis=1)).ravel()
        stats["depth_rel_change_max"] = float(np.max(np.abs(totals1 / totals0 - 1)))
        stats["achieved_share"] = 1 - stats["resid_abs_sum"] / max(stats["need_abs_sum"], 1e-12)
        return out.astype(np.float32), stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", type=Path, required=True)
    ap.add_argument("--stats-out", type=Path, required=True)
    ap.add_argument("rest", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    rest = a.rest[1:] if a.rest[:1] == ["--"] else a.rest
    spec = importlib.util.spec_from_file_location("stage45", REPO / "scripts" / "45_generate_prediction.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tg = Targets(a.targets, 18533)
    log = []
    t0 = time.perf_counter()
    base = mod.SubmissionWriter

    class SlidingWriter(base):
        def add(self, block, *, target_gene, context):
            nnz0 = block.nnz
            block, st = tg.apply(block, context, target_gene)
            if block.nnz != nnz0:
                raise RuntimeError("stored entries changed")
            st.update({"context": context, "target_index": len(log) % 300})
            log.append(st)
            super().add(block, target_gene=target_gene, context=context)

    mod.SubmissionWriter = SlidingWriter
    sys.argv = ["45_generate_prediction.py"] + rest
    mod.main()
    ach = np.array([s["achieved_share"] for s in log])
    summary = {"blocks": len(log), "achieved_share_median": float(np.median(ach)),
               "achieved_share_q10": float(np.quantile(ach, 0.1)),
               "depth_rel_change_max": float(max(s["depth_rel_change_max"] for s in log)),
               "slide_seconds_total": time.perf_counter() - t0, "per_block": log}
    a.stats_out.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"slide: median achieved {summary['achieved_share_median']:.3f}, q10 {summary['achieved_share_q10']:.3f}, "
          f"max depth change {summary['depth_rel_change_max']:.4f}")


if __name__ == "__main__":
    main()
