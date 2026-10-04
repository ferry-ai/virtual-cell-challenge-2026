"""t35 bench (PROTOCOLLO.md in this folder): the count move of t35, read with the real scorer on held-out lines.

Phases 1-2 are those of the route C bench (reports/trasferimento/strada_c_banco_2026-10-03/banco_tipo.py, imported
unchanged): every shard is read once and K562 effects are estimated with its formulas. Phase 3, per held-out line L
(h1, kolf, hepg2, jurkat), builds the same `vcc2026.bench.Bench` from L's own cells and scores three arms:
  null           the control model (no effect);
  k562_a2        the K562 effect x2 with the registered amplitude rule: the t34-like arm (t31/t34 are K562 x2);
  k562_a2_slide  the very same cells (same random stream), then the count move of t35
                 (reports/modelli/rete_l1_2026-10-04/genera_l1.py `slide`, depth cap 2%, two passes) toward the
                 rete_anti magnitude trained without L (obiettivi_linee.py), with the sign of the arm's own effect.
Phase 4 reads the registered rule with the route C paired bootstrap over targets.

    python banco_t35.py --inputs /kaggle/input --axis gene_names.csv --obiettivi <dir> --out out --code <src>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import banco_tipo as bt  # noqa: E402

LINES = ("h1", "kolf", "hepg2", "jurkat")
A_T34 = 2.0
DEPTH_CAP = 0.02
log = bt.log


def load_obiettivi(folder: Path, L: str) -> dict:
    """{key: {target: (gene_idx on the axis, |m|)}} for the keys of line L."""
    out = {}
    for p in sorted(folder.glob("obiettivi_*.npz")):
        z = np.load(p, allow_pickle=False)
        if str(z["group"]) != L:
            continue
        gidx = z["gene_idx"].astype(np.int64)
        out[str(z["key"])] = {t: (gidx, z["mag"][i].astype(np.float64)) for i, t in enumerate(map(str, z["targets"]))}
    return out


def slide_block(block: sp.csr_matrix, ref_cpm: np.ndarray, m: np.ndarray, active: np.ndarray, gene_order):
    from genera_l1 import slide
    n = block.shape[0]
    goal = n * ref_cpm * np.exp2(np.nan_to_num(m)) / 1e6
    csc = block.tocsc().astype(np.float64)
    csc.sort_indices()
    totals0 = np.asarray(block.sum(axis=1)).ravel().astype(np.float64)
    col0 = np.asarray(csc.sum(axis=0)).ravel()
    delta, cap = np.zeros(n), DEPTH_CAP * totals0
    need0 = None
    for p in range(2):
        L = np.asarray(csc.sum(axis=1)).ravel()
        resid, before = slide(csc.indptr.astype(np.int64), csc.indices.astype(np.int64), csc.data, L, goal,
                              active, delta, cap, gene_order)
        if p == 0:
            need0 = float(np.abs(before[active]).sum())
    out = csc.tocsr()
    if not np.array_equal(np.asarray(out.sum(axis=0)).ravel(), col0) or out.nnz != block.nnz:
        raise RuntimeError("the move changed gene totals or stored entries")
    return out, {"achieved_share": 1 - float(np.abs(resid[active]).sum()) / max(need0, 1e-12),
                 "active_genes": int(active.sum())}


def run_line(L, sums, lib, shard_paths, axis, out: Path, obj_dir: Path) -> dict:
    from vcc2026.bench import Bench
    from vcc2026.generator import ControlModel

    G = axis.size
    cand = [k for k in sums.where if bt.group_of(*k.split("|", 1)) == L]
    if not cand:
        return {"line": L, "readable": False, "why": "no key of this line in the corpus"}
    studies = {k.split("|", 1)[0] for k in cand}
    excluded = {k for k in lib.eff if k.split("|", 1)[0] in studies or lib.group[k] == L} | bt.SAME_LINE.get(L, set())
    allowed = {k for k in lib.eff if k not in excluded and lib.group[k] is not None}
    obj = load_obiettivi(obj_dir, L)

    def eligible(key):
        mine = obj.get(key, {})
        return sorted(t for t, n in sums.n[key].items()
                      if t != bt.NTC and n >= bt.PANEL_MIN_CELLS and lib.covers("k562", allowed, t) and t in mine)

    key = max(cand, key=lambda k: len(eligible(k)))
    el = eligible(key)
    info = {"line": L, "key": key, "eligible_targets": len(el), "obiettivi_keys": sorted(obj)}
    log(f"{L}: key {key}, {len(el)} eligible targets")
    if len(el) < 20:
        return info | {"readable": False, "why": f"panel of {len(el)} targets < 20"}
    rng = np.random.default_rng(bt.PANEL_SEED)
    panel = sorted(rng.choice(el, size=min(bt.PANEL_MAX, len(el)), replace=False).tolist())
    where = defaultdict(list)
    for sid, row, lab in sums.where[key]:
        where[lab].append((sid, row))
    picks, labels = [], []
    for t in panel + [bt.NTC]:
        cap = bt.CTRL_MAX if t == bt.NTC else bt.CELLS_MAX
        rows = where[t]
        take = rng.choice(len(rows), size=min(cap, len(rows)), replace=False)
        picks.extend(rows[i] for i in sorted(take))
        labels.extend([t] * take.size)
    labels = np.array(labels)
    x_all = bt.read_cells(sums, shard_paths, picks, G)
    genes_idx = np.flatnonzero(sums.mask[key])
    x = x_all[:, genes_idx]
    genes = axis[genes_idx]
    target_rows = {t: np.flatnonzero(labels == t) for t in panel}
    ctrl_rows = np.flatnonzero(labels == bt.NTC)
    bench = Bench(x, target_rows, ctrl_rows, genes, out / f"bench_{L}", seed=bt.PANEL_SEED)
    bt.anchors_with_baseline_per(bench)
    model = ControlModel(state="kde", seed=bt.PANEL_SEED).fit(bench.ctrl, log=log)
    c = bench.ctrl.tocsr().astype(np.float64)
    Lc = np.asarray(c.sum(axis=1)).ravel()
    ref_cpm = np.asarray((sp.diags(1e6 / np.maximum(Lc, 1.0)) @ c).mean(axis=0)).ravel()  # the scorer's reference mean
    expressed = ref_cpm >= 5.0
    targets = bench.targets
    pos = {t: i for i, t in enumerate(targets)}
    gene_pos = {g: i for i, g in enumerate(genes)}
    axis_to_bench = np.full(G, -1, np.int64)
    axis_to_bench[genes_idx] = np.arange(genes_idx.size)
    M, S, norms = bt.arm_matrix(lib, ["k562"], allowed, targets, genes_idx)
    s = bt.amplitude(M, norms)
    order = np.random.default_rng(0).permutation(genes_idx.size).astype(np.int64)
    src_key = {t: (key if t in obj.get(key, {}) else next(k for k in obj if t in obj[k])) for t in targets}

    slide_log = []
    for arm in ("null", "k562_a2", "k562_a2_slide"):
        rng_arm = np.random.default_rng(bt.PANEL_SEED + 1)  # the same stream for every arm: same cells before the move
        blocks, labs = [], []
        for t in targets:
            n = bench.n_pred(t)
            if arm == "null":
                blk = model.sample(n, rng_arm)
            else:
                v = A_T34 * s * M[pos[t]]
                blk = model.sample(n, rng_arm, fold_change=np.exp(np.clip(v, -3, 3)))
                if arm == "k562_a2_slide":
                    gidx, mag = obj[src_key[t]][t]
                    mb = np.full(genes_idx.size, np.nan)
                    ok = axis_to_bench[gidx] >= 0
                    mb[axis_to_bench[gidx[ok]]] = mag[ok]
                    m = np.sign(v) * mb
                    active = expressed & (v != 0) & np.isfinite(m) & (np.abs(np.nan_to_num(m)) > 0)
                    j = gene_pos.get(t)
                    if j is not None:
                        active[j] = False          # the knocked-down gene's own row is not scored
                    blk, st = slide_block(sp.csr_matrix(blk), ref_cpm, m, active, order)
                    slide_log.append({"target": t, **st})
            blocks.append(sp.csr_matrix(blk))
            labs.append(np.full(n, t))
        bench.score(arm, sp.vstack(blocks).tocsr(), np.concatenate(labs))
    ach = [d["achieved_share"] for d in slide_log]
    bench.finish({"stage": "banco_t35", "line": L, "key": key, "panel": targets, "amplitude_s": s, "a": A_T34,
                  "excluded_keys": sorted(excluded), "slide": {"achieved_share_median": float(np.median(ach)),
                                                               "per_target": slide_log}})
    return info | {"readable": True, "panel": len(targets), "amplitude_s": s,
                   "slide_achieved_median": float(np.median(ach))}


def read_rule(out: Path, lines: dict) -> dict:
    res = {"lines": {}}
    for L, info in lines.items():
        if not info.get("readable"):
            res["lines"][L] = info
            continue
        bdir = out / f"bench_{L}"
        bj = json.loads((bdir / "bench.json").read_text())
        targets = bj["panel"]
        g = bt.gate(bdir)
        raw = {a: bj["results"][a]["raw"] for a in ("k562_a2", "k562_a2_slide", "null") if a in bj["results"]}
        res["lines"][L] = info | {"gate": g, "readable": g["passes"], "raw": raw,
                                  "slide_vs_t34": bt.compare(bdir, targets, "k562_a2_slide", "k562_a2"),
                                  "t34_vs_null": bt.compare(bdir, targets, "k562_a2", "null")}
    ok = {L: v for L, v in res["lines"].items() if v.get("readable") and v.get("slide_vs_t34")}
    means = {L: v["slide_vs_t34"]["mean"] for L, v in ok.items()}
    macro = float(np.mean(list(means.values()))) if means else None
    h1 = means.get("h1")
    res["rule"] = {"per_line_mean": means, "macro": macro, "h1": h1,
                   "launch_t35": bool(macro is not None and h1 is not None and macro >= 0.005 and h1 >= 0.0
                                      and len(ok) >= 3),
                   "text": "launch t35 only if macro(slide - t34) >= +0.005 over >= 3 readable lines and H1 >= 0"}
    return res


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--axis", type=Path, required=True)
    p.add_argument("--obiettivi", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--code", type=Path, default=None)
    p.add_argument("--lines", nargs="+", default=list(LINES))
    a = p.parse_args()
    if a.code:
        sys.path.insert(0, str(a.code))
    a.out.mkdir(parents=True, exist_ok=True)
    if (a.out / "lettura.json").exists():
        raise SystemExit(f"{a.out} already holds a reading")
    axis = pd.read_csv(a.axis, header=None).iloc[:, 0].astype(str).to_numpy()
    if axis[0].lower() in ("gene", "gene_name", "genes", "symbol"):
        axis = axis[1:]
    G = axis.size
    shard_paths = sorted(a.inputs.rglob("*.h5ad"))
    log(f"axis {G} genes; {len(shard_paths)} shards")
    sums = bt.Sums(G)
    t0, report = time.time(), []
    for sid, path in enumerate(shard_paths):
        try:
            obs, oi, ok, x = bt.read_shard(path)
        except Exception as exc:
            report.append({"shard": str(path), "error": f"{type(exc).__name__}: {exc}"})
            log(f"SKIP {path.name}: {exc}")
            continue
        report.append({"shard": str(path), **sums.add(sid, obs, oi, ok, x, set(axis), set(a.lines))})
        if sid % 25 == 0:
            log(f"phase 1: {sid + 1}/{len(shard_paths)} shards, {time.time() - t0:.0f}s")
    effects = {}
    for key in sorted(sums.acc):
        g = bt.group_of(*key.split("|", 1))
        if g is None or sums.n[key].get(bt.NTC, 0) < bt.MIN_NTC_KEY:
            continue
        r = bt.key_effects(sums, key)
        if r is not None:
            effects[key] = r
    (a.out / "sorgenti.json").write_text(json.dumps({"keys_with_effects": sorted(effects), "shards": report}, indent=1))
    lib = bt.Library(effects)
    lines = {}
    for L in a.lines:
        try:
            lines[L] = run_line(L, sums, lib, shard_paths, axis, a.out, a.obiettivi)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            lines[L] = {"line": L, "readable": False, "why": f"{type(exc).__name__}: {exc}"}
        (a.out / "linee.json").write_text(json.dumps(lines, indent=1, default=str))
    lettura = read_rule(a.out, lines)
    (a.out / "lettura.json").write_text(json.dumps(lettura, indent=1, default=str))
    log(json.dumps(lettura["rule"], indent=1, default=str))
    log("done")


if __name__ == "__main__":
    main()
