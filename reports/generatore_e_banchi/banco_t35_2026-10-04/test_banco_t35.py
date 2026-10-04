"""Smoke test of the t35 bench's phase 3 on synthetic counts (no shards): Bench, ControlModel, the move, the rule.

    python test_banco_t35.py   (needs cell_eval2 and numba; writes to a temporary folder)
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "trasferimento" / "strada_c_banco_2026-10-03"))
sys.path.insert(0, str(HERE.parents[1] / "modelli" / "rete_l1_2026-10-04"))
sys.path.insert(0, str(HERE.parents[2] / "src"))
import banco_t35 as b  # noqa: E402


def main() -> None:
    from vcc2026.bench import Bench
    from vcc2026.generator import ControlModel

    rng = np.random.default_rng(0)
    G, targets = 400, [f"G{i}" for i in range(24)]
    genes = np.array([f"G{i}" for i in range(G)])
    p = rng.gamma(0.6, 1.0, G)
    p /= p.sum()
    eff = {t: np.where(rng.random(G) < 0.08, rng.normal(0, 0.8, G), 0.0) for t in targets}
    rows, labels = [], []
    for t in targets + ["__NTC__"]:
        n = 600 if t == "__NTC__" else 80
        q = p * np.exp(eff[t]) if t in eff else p
        q = q / q.sum()
        L = rng.lognormal(np.log(4000), 0.45, n)
        rows.append(sp.csr_matrix(rng.poisson(L[:, None] * q[None, :]).astype(np.float32)))
        labels += [t] * n
    x = sp.vstack(rows).tocsr()
    labels = np.array(labels)
    out = Path(tempfile.mkdtemp())
    bench = Bench(x, {t: np.flatnonzero(labels == t) for t in targets}, np.flatnonzero(labels == "__NTC__"), genes,
                  out / "bench_h1", seed=2026)
    b.bt.anchors_with_baseline_per(bench)
    model = ControlModel(state="kde", seed=2026).fit(bench.ctrl, log=print)
    c = bench.ctrl.tocsr().astype(np.float64)
    Lc = np.asarray(c.sum(axis=1)).ravel()
    ref = np.asarray((sp.diags(1e6 / Lc) @ c).mean(axis=0)).ravel()
    order = np.random.default_rng(0).permutation(G).astype(np.int64)
    ach = []
    for arm in ("null", "k562_a2", "k562_a2_slide"):
        r = np.random.default_rng(7)
        blocks, labs = [], []
        for t in bench.targets:
            n = bench.n_pred(t)
            if arm == "null":
                blk = model.sample(n, r)
            else:
                v = 2.0 * eff[t]
                blk = model.sample(n, r, fold_change=np.exp(np.clip(v, -3, 3)))
                if arm == "k562_a2_slide":
                    m = np.sign(v) * 0.15
                    active = (ref >= 5) & (v != 0)
                    blk, st = b.slide_block(sp.csr_matrix(blk), ref, m, active, order)
                    ach.append(st["achieved_share"])
            blocks.append(sp.csr_matrix(blk))
            labs.append(np.full(n, t))
        bench.score(arm, sp.vstack(blocks).tocsr(), np.concatenate(labs))
    bench.finish({"stage": "test", "line": "h1", "panel": bench.targets})
    rule = b.read_rule(out, {"h1": {"line": "h1", "readable": True}})
    print(json.dumps(rule["lines"]["h1"]["slide_vs_t34"]), "achieved median", float(np.median(ach)))
    print("raw", json.dumps(rule["lines"]["h1"]["raw"], default=str)[:600])
    print("OK")


if __name__ == "__main__":
    main()
