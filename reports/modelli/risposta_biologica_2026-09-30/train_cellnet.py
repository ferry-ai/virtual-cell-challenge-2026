"""Train and evaluate the R-LAB cell network on contract shards (see cellnet.py for the model).

    python train_cellnet.py --shards <dir or glob> [...] --axis gene_names.csv --descriptors <dir> \
        --holdout-context <context> --holdout-target-frac 0.1 --target-code descriptors --out <new dir> \
        [--steps 20000] [--batch 256] [--max-minutes 480] [--device cuda]

Splits, fixed before any count is read and written to splits.json:
- C: one context invisible in training (its cells and its controls); at evaluation its controls feed only the
  context encoder;
- T: a fraction of the perturbation labels, drawn with --target-split-seed among the labels perturbed in at least one
  training context, invisible in every context (new targets, known contexts);
- J: the T targets inside the C context.
The run ends with a leakage check: no cell drawn into a batch may carry a held-out context or target.

Written to a NEW --out: config.json (arguments, code and descriptor hashes, corpus summary), splits.json, qc.json
(per study and context: quantiles of counts, genes detected and mitochondrial fraction on the measured genes; no
cell is filtered except cells without counts on the model genes), coverage.json (per study and context: cells offered,
distinct cells drawn, draws), train_log.jsonl, model.pt, eval.json (C, T and J), done.json last. A first run on part of
the corpus is a technical check, not a result (owner, 30/09).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cellnet as CN  # noqa: E402

QC_KEEP = 20000


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def shard_paths(patterns):
    out = []
    for p in patterns:
        pth = Path(p)
        out += sorted(str(q) for q in pth.rglob("*.h5ad")) if pth.is_dir() else sorted(glob.glob(p, recursive=True))
    return [p for p in dict.fromkeys(out) if not p.endswith(".partial.h5ad")]


class Loaded:
    """One shard in memory: counts on the model genes (CSR), measured mask, per-cell labels as indices."""

    def __init__(self, info, corpus, cidx, tidx, midx, sidx, holdout_ctx, holdout_targets):
        self.info = info
        self.x, self.mask = CN.read_counts(info, corpus.gene_of_axis, len(corpus.genes))
        self.lib = np.asarray(self.x.sum(axis=1)).ravel()
        self.ctx = np.array([cidx[c] for c in info.contexts])
        self.control = info.control.copy()
        self.target = np.array([tidx.get(t, -1) for t in info.targets])
        self.mod = np.array([midx[m] for m in info.modality])
        self.study = sidx[info.study]
        usable = (self.lib > 0) & (self.control | (self.target >= 0))
        hid_t = np.isin(self.target, list(holdout_targets)) & ~self.control
        in_c = info.contexts == holdout_ctx
        self.train_rows = np.flatnonzero(usable & ~in_c & ~hid_t)
        self.c_rows = np.flatnonzero(usable & in_c & ~hid_t)          # C: held-out context, seen targets (+ controls)
        self.t_rows = np.flatnonzero(usable & ~in_c & hid_t)          # T: new targets in training contexts
        self.j_rows = np.flatnonzero(usable & in_c & hid_t)           # J: new targets in the held-out context


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shards", nargs="+", required=True)
    ap.add_argument("--axis", required=True)
    ap.add_argument("--descriptors", type=Path, help="folder with descriptors.npy, genes.txt, manifest.json")
    ap.add_argument("--target-code", choices=["descriptors", "identity", "both"], default="descriptors")
    ap.add_argument("--holdout-context", required=True)
    ap.add_argument("--holdout-target-frac", type=float, default=0.1)
    ap.add_argument("--target-split-seed", type=int, default=20260930)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--ctrl-k", type=int, default=64)
    ap.add_argument("--reservoir", type=int, default=1024)
    ap.add_argument("--buffer-shards", type=int, default=8)
    ap.add_argument("--refresh-every", type=int, default=400)
    ap.add_argument("--control-frac", type=float, default=0.25)
    ap.add_argument("--input-genes", type=int, default=2048)
    ap.add_argument("--dim", type=int, default=128)
    ap.add_argument("--rank", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--max-minutes", type=float, default=480)
    ap.add_argument("--eval-min-cells", type=int, default=20)
    ap.add_argument("--eval-max-targets", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default=None)
    a = ap.parse_args()
    import torch
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    a.out.mkdir(parents=True)
    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    t0 = time.time()
    logf = open(a.out / "train_log.jsonl", "a", encoding="utf-8")

    def log(msg, **kw):
        line = {"t": round(time.time() - t0, 1), "msg": msg, **kw}
        print(json.dumps(line, default=str), flush=True)
        logf.write(json.dumps(line, default=str) + "\n"); logf.flush()

    axis = [l.strip().split(",")[0] for l in open(a.axis, encoding="utf-8") if l.strip()]
    if axis and axis[0].lower() in ("gene", "gene_name", "genes", "x"):
        axis = axis[1:]
    paths = shard_paths(a.shards)
    corpus = CN.Corpus.build(paths, axis, log=log)
    if a.holdout_context not in corpus.contexts:
        sys.exit(f"holdout context {a.holdout_context} is not in the corpus: {corpus.contexts}")
    cidx = {c: i for i, c in enumerate(corpus.contexts)}
    hc_eval = cidx[a.holdout_context] if a.holdout_context in cidx else -1
    tidx = {t: i for i, t in enumerate(corpus.targets)}
    midx = {m: i for i, m in enumerate(corpus.modalities)}
    sidx = {s: i for i, s in enumerate(corpus.studies)}
    G = len(corpus.genes)

    # ---- splits, from labels only
    perturbed_where = defaultdict(set)
    for i in corpus.shards:
        for c, t in zip(i.contexts[~i.control], i.targets[~i.control]):
            if t in tidx:
                perturbed_where[t].add(c)
    trainable = sorted(t for t, cs in perturbed_where.items() if cs - {a.holdout_context})
    rng = random.Random(a.target_split_seed)
    holdout_labels = sorted(rng.sample(trainable, int(round(a.holdout_target_frac * len(trainable)))))
    holdout_targets = {tidx[t] for t in holdout_labels}
    in_holdout_ctx = {t for t, cs in perturbed_where.items() if a.holdout_context in cs}
    eval_relevant = {tidx[t] for t in in_holdout_ctx} | holdout_targets    # the only labels whose sums are kept
    splits = {"seed": a.target_split_seed, "holdout_context": a.holdout_context,
              "holdout_targets": holdout_labels, "n_trainable_labels": len(trainable),
              "rule": "C: the context is invisible (cells and controls); T: these labels are invisible in every context; "
                      "J: T labels inside the C context"}
    (a.out / "splits.json").write_text(json.dumps(splits, indent=1), encoding="utf-8")

    # ---- descriptors of each target's gene (symbol before any '|' or '_' combination separator)
    desc, desc_info = None, None
    if a.descriptors:
        D = np.load(a.descriptors / "descriptors.npy")
        dgenes = (a.descriptors / "genes.txt").read_text(encoding="utf-8").split()
        drow = {g: k for k, g in enumerate(dgenes)}
        desc = np.zeros((len(corpus.targets) + 1, D.shape[1]), np.float32)
        found = 0
        for t, k in tidx.items():
            r = drow.get(t) if t in drow else drow.get(t.split("|")[0])
            if r is not None:
                desc[k] = D[r]; found += 1
        desc_info = {"sha256": sha(a.descriptors / "descriptors.npy"), "dims": int(D.shape[1]),
                     "targets_with_descriptors": found, "targets": len(corpus.targets)}
    target_gene = np.array([corpus.target_symbol_axis.get(t, -1) for t in corpus.targets] + [-1], dtype=np.int64)
    config = {"args": {k: str(v) for k, v in vars(a).items()}, "device": dev, "started_utc": now(),
              "code": {p.name: sha(p) for p in (HERE / "cellnet.py", Path(__file__))}, "descriptors": desc_info,
              "shards": len(paths), "corpus": corpus.summary(a.holdout_context)}
    (a.out / "config.json").write_text(json.dumps(config, indent=1, default=str), encoding="utf-8")
    log("corpus", genes=G, contexts=len(corpus.contexts), targets=len(corpus.targets),
        holdout_targets=len(holdout_targets), descriptors=desc_info)

    train_shards = [i for i in corpus.shards if (i.contexts != a.holdout_context).any()]
    hold_shards = [i for i in corpus.shards if (i.contexts == a.holdout_context).any()]
    L_args = (corpus, cidx, tidx, midx, sidx, a.holdout_context, holdout_targets)

    # ---- encoder input genes: most expressed over training controls of a sample of shards
    tot = np.zeros(G)
    for info in random.sample(train_shards, min(len(train_shards), 12)):
        L = Loaded(info, *L_args)
        rows = L.train_rows[L.control[L.train_rows]]
        if rows.size:
            tot += np.asarray(L.x[rows].multiply(1.0 / np.maximum(L.lib[rows], 1)[:, None]).sum(axis=0)).ravel()
    input_genes = np.argsort(-tot)[:a.input_genes]
    model = CN.build_model(G, len(corpus.targets), len(corpus.modalities), len(corpus.studies), input_genes,
                           dim=a.dim, rank=a.rank, target_desc=desc, target_code=a.target_code).to(dev)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=1e-4)
    log("model", parameters=sum(p.numel() for p in model.parameters() if p.requires_grad), input_genes=len(input_genes),
        target_code=a.target_code)

    mt = np.array([g.startswith("MT-") for g in corpus.genes])
    reservoir = {}
    offered = Counter()
    drawn = {}                              # shard path -> bool per row
    draws = Counter()
    visited_labels = Counter()
    qc = defaultdict(lambda: {"lib": [], "genes": [], "mito": []})
    sums = defaultdict(lambda: np.zeros(G, np.float32))   # pseudobulk sums: evaluation baselines only
    nsum = Counter()
    pert_sum = defaultdict(lambda: np.zeros(G, np.float32))   # every perturbed cell of a context, pooled
    pert_n = Counter()
    first_seen = set()
    t_cells = defaultdict(list)             # (context, target) -> [(shard path, row)] for the T evaluation

    def feed_reservoir(L):
        for c in np.unique(L.ctx[L.train_rows]):
            rows = L.train_rows[(L.ctx[L.train_rows] == c) & L.control[L.train_rows]]
            if rows.size == 0:
                continue
            take = rows if rows.size <= a.reservoir else np.random.choice(rows, a.reservoir, replace=False)
            dense = L.x[take].toarray().astype(np.float16)
            if c not in reservoir:
                reservoir[c] = [dense, L.mask.copy()]
            else:
                both = np.concatenate([reservoir[c][0], dense])
                keep = np.random.choice(len(both), min(len(both), a.reservoir), replace=False)
                reservoir[c][0] = both[keep]
                reservoir[c][1] |= L.mask

    def first_pass(L):
        """Once per shard: offered cells, QC values, pseudobulk sums for the transfer baseline (evaluation only),
        and where the T cells are."""
        info = L.info
        drawn[str(info.path)] = np.zeros(info.n_cells, bool)
        for c, n in zip(*np.unique(L.ctx[L.train_rows], return_counts=True)):
            offered[(info.study, corpus.contexts[c])] += int(n)
        rows = np.flatnonzero(L.lib > 0)
        genes_det = np.diff(L.x.indptr)[rows]
        mito = np.asarray(L.x[rows][:, np.flatnonzero(mt & L.mask)].sum(axis=1)).ravel() / np.maximum(L.lib[rows], 1)
        for c in np.unique(L.ctx[rows]):
            sel = L.ctx[rows] == c
            q = qc[(info.study, corpus.contexts[c])]
            for key, vals in (("lib", L.lib[rows][sel]), ("genes", genes_det[sel]), ("mito", mito[sel])):
                if len(q[key]) < QC_KEEP:
                    q[key].extend(np.random.permutation(vals)[:QC_KEEP - len(q[key])].tolist())
        tr = L.train_rows
        prop = L.x[tr].multiply(1.0 / np.maximum(L.lib[tr], 1)[:, None]).tocsr()
        keys = np.where(L.control[tr], -1, L.target[tr])
        for c in np.unique(L.ctx[tr]):
            selp = (~L.control[tr]) & (L.ctx[tr] == c)
            if selp.any():
                pert_sum[int(c)] += np.asarray(prop[selp].sum(axis=0)).ravel()
                pert_n[int(c)] += int(selp.sum())
        for k in np.unique(keys):
            if k != -1 and int(k) not in eval_relevant:
                continue
            sel = keys == k
            ctxs = L.ctx[tr][sel]
            for c in np.unique(ctxs):
                s2 = sel.copy(); s2[sel] = ctxs == c
                sums[(int(c), int(k))] += np.asarray(prop[s2].sum(axis=0)).ravel()
                nsum[(int(c), int(k))] += int(s2.sum())
        for r in L.t_rows:
            t_cells[(int(L.ctx[r]), int(L.target[r]))].append((str(info.path), int(r)))

    order = []

    def next_shard():
        nonlocal order
        if not order:
            order = random.sample(train_shards, len(train_shards))
        info = order.pop()
        L = Loaded(info, *L_args)
        feed_reservoir(L)
        if str(info.path) not in first_seen:
            first_seen.add(str(info.path))
            first_pass(L)
        return L

    buffer = [next_shard() for _ in range(min(a.buffer_shards, len(train_shards)))]
    target_gene_t = torch.as_tensor(target_gene, device=dev)

    def tensors(cells):
        xs = np.zeros((len(cells), G), np.float32)
        groups = defaultdict(list)
        for k, (L, r) in enumerate(cells):
            groups[id(L)].append((k, r, L))
        for items in groups.values():
            L = items[0][2]
            xs[[k for k, _, _ in items]] = L.x[[r for _, r, _ in items]].toarray()
        T = lambda v, dt=torch.float32: torch.as_tensor(np.asarray(v), dtype=dt, device=dev)
        return (T(xs), T(np.vstack([L.mask for L, _ in cells]), torch.bool),
                T([L.lib[r] for L, r in cells]), np.array([L.ctx[r] for L, r in cells]),
                T([L.control[r] for L, r in cells], torch.bool),
                T([L.target[r] if not L.control[r] else len(corpus.targets) for L, r in cells], torch.long),
                T([L.mod[r] for L, r in cells], torch.long), T([L.study for L, _ in cells], torch.long))

    def context_codes(ctx_ids, source=None):
        uniq = sorted(set(int(c) for c in ctx_ids))
        xs, ms = [], []
        for c in uniq:
            res, m = (source or reservoir)[c]
            take = np.random.choice(len(res), min(a.ctrl_k, len(res)), replace=len(res) < a.ctrl_k)
            xs.append(res[take].astype(np.float32)); ms.append(m)
        k = min(len(x) for x in xs)
        z, beta = model.context(torch.as_tensor(np.stack([x[:k] for x in xs]), device=dev),
                                torch.as_tensor(np.stack(ms), device=dev))
        return z, beta, {c: i for i, c in enumerate(uniq)}

    def loglik(cells, ctx_source=None, unknown_target=False):
        x, mask, lib, ctx, is_ctrl, tgt, mod, stu = tensors(cells)
        if unknown_target:                    # the same network told nothing about the target: a generic perturbation
            tgt = torch.full_like(tgt, len(corpus.targets))
        z_u, beta_u, pos = context_codes(ctx, ctx_source)
        sel = torch.as_tensor([pos[int(c)] for c in ctx], device=dev)
        z, beta = z_u[sel], beta_u[sel]
        theta = torch.exp(model.log_theta[stu]).clamp(1e-3, 1e4)
        ll0 = CN.cell_loglik(x, lib, beta, mask, theta)
        delta, pi = model(z, beta, tgt, target_gene_t[tgt], mod)
        ll1 = CN.cell_loglik(x, lib, beta + delta, mask, theta)
        mix = torch.logsumexp(torch.stack([torch.log(pi.clamp_min(1e-6)) + ll1,
                                           torch.log((1 - pi).clamp_min(1e-6)) + ll0]), 0)
        return x, mask, lib, beta, delta, pi, ll0, mix, is_ctrl

    def draw_batch():
        by = defaultdict(list)
        for L in buffer:
            for c in np.unique(L.ctx[L.train_rows]):
                if int(c) in reservoir:
                    by[(L.study, int(c))].append(L)
        keys = list(by)
        studies = sorted({k[0] for k in keys})
        cells = []
        for _ in range(a.batch):
            st = random.choice(studies)
            s, c = random.choice([k for k in keys if k[0] == st])
            L = random.choice(by[(s, c)])
            rows = L.train_rows[L.ctx[L.train_rows] == c]
            pool = rows[L.control[rows] == (random.random() < a.control_frac)]
            r = int(np.random.choice(pool if pool.size else rows))
            cells.append((L, r))
            drawn[str(L.info.path)][r] = True
            draws[(L.info.study, corpus.contexts[c])] += 1
            visited_labels[(corpus.contexts[c], "NTC" if L.control[r] else corpus.targets[L.target[r]])] += 1
        return cells

    step, t_train = 0, time.time()
    while step < a.steps and (time.time() - t0) / 60 < a.max_minutes:
        if step and step % a.refresh_every == 0:
            buffer.pop(0)
            buffer.append(next_shard())
        x, mask, lib, beta, delta, pi, ll0, mix, is_ctrl = loglik(draw_batch())
        genes_per_cell = mask.sum(-1).clamp_min(1)
        loss = -(torch.where(is_ctrl, ll0, mix) / genes_per_cell).mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        step += 1
        if step % 100 == 0 or step == 1:
            with torch.no_grad():
                log("step", step=step, loss=round(float(loss), 5),
                    pert_gain=float(((mix - ll0) / genes_per_cell)[~is_ctrl].mean()) if (~is_ctrl).any() else None,
                    pi_mean=float(pi[~is_ctrl].mean()) if (~is_ctrl).any() else None,
                    steps_per_s=round(step / (time.time() - t_train), 2), shards_seen=len(first_seen),
                    of_shards=len(train_shards))
    torch.save({"state": model.state_dict(), "genes": corpus.genes, "targets": corpus.targets,
                "contexts": corpus.contexts, "modalities": corpus.modalities, "studies": corpus.studies,
                "input_genes": input_genes.tolist(), "target_code": a.target_code}, a.out / "model.pt")

    # ---- leakage check, coverage, QC
    leaks = [(c, t) for (c, t) in visited_labels if c == a.holdout_context or (t != "NTC" and tidx[t] in holdout_targets)]
    cov = {"steps": step, "batch": a.batch, "draws": int(sum(draws.values())),
           "shards_seen": len(first_seen), "train_shards": len(train_shards),
           "by_study_context": [{"study": s, "context": c, "offered": int(offered[(s, c)]),
                                 "distinct_drawn": int(sum(int(drawn[str(i.path)][
                                     np.flatnonzero(i.contexts == c)].sum()) for i in train_shards
                                     if i.study == s and str(i.path) in drawn)),
                                 "draws": int(draws[(s, c)])} for (s, c) in sorted(offered)],
           "labels_drawn": len({t for _, t in visited_labels if t != "NTC"}),
           "leakage_check": {"passed": not leaks, "violations": leaks[:20]}}
    (a.out / "coverage.json").write_text(json.dumps(cov, indent=1), encoding="utf-8")
    qc_out = {}
    for (s, c), q in qc.items():
        qc_out[f"{s}|{c}"] = {k: {p: float(np.quantile(v, p / 100)) for p in (1, 5, 25, 50, 75, 95, 99)}
                              for k, v in q.items() if v}
    (a.out / "qc.json").write_text(json.dumps({"policy": "measured, no cell filtered (only cells without counts on the "
                                                          "model genes are skipped)", "by_study_context": qc_out},
                                              indent=1), encoding="utf-8")
    log("trained", steps=step, minutes=round((time.time() - t0) / 60, 1), leakage_passed=not leaks)
    if leaks:
        sys.exit(f"leakage: held-out cells were drawn: {leaks[:5]}")

    # ---- evaluation
    model.eval()

    def cos(u, v):
        nu, nv = np.linalg.norm(u), np.linalg.norm(v)
        return float(u @ v / (nu * nv)) if nu > 0 and nv > 0 else 0.0

    def evaluate(groups, ctx_source, base_props):
        """groups: {(context index, target index): [(Loaded or path, row)]}; ctx_source: control reservoirs to use."""
        out = []
        for (c, t), cells in groups.items():
            if len(cells) < a.eval_min_cells:
                continue
            if c not in ctx_source:          # a context without control cells cannot condition the model
                out.append({"context": corpus.contexts[c], "target": corpus.targets[t], "cells": len(cells),
                            "skipped": "no control cells for this context"})
                continue
            cells = cells[:2000]
            with torch.no_grad():
                torch.manual_seed(1234)          # the same control cells for both calls
                np.random.seed(1234)
                x, mask, lib, beta, delta, pi, ll0, mix, _ = loglik(cells, ctx_source)
                np.random.seed(1234)
                _, _, _, _, _, pi_u, _, mix_u, _ = loglik(cells, ctx_source, unknown_target=True)
                per_gene = mask.sum(-1).clamp_min(1)
                gain = float(((mix - ll0) / per_gene).mean())
                gain_specific = float(((mix - mix_u) / per_gene).mean())
                m0 = mask[0]
                p0 = torch.softmax(beta[0].masked_fill(~m0, float("-inf")), -1)
                p1 = torch.softmax((beta[0] + delta[0]).masked_fill(~m0, float("-inf")), -1)
                pred = (torch.log((pi[0] * p1 + (1 - pi[0]) * p0).clamp_min(1e-12)) - torch.log(p0.clamp_min(1e-12))).cpu().numpy()
            obs_prop = (x / lib[:, None].clamp_min(1)).mean(0).cpu().numpy()
            base = base_props[c]
            valid = m0.cpu().numpy() & (base > 0) & (obs_prop > 0)
            obs = np.where(valid, np.log(np.maximum(obs_prop, 1e-12)) - np.log(np.maximum(base, 1e-12)), 0)
            trans, nctx = np.zeros(G), 0
            for (cc, tt), n in nsum.items():
                if tt == t and cc != c and n >= 10 and nsum.get((cc, -1), 0) >= 10:
                    pt, pc = sums[(cc, t)] / n, sums[(cc, -1)] / nsum[(cc, -1)]
                    ok = (pt > 0) & (pc > 0)
                    trans[ok] += np.log(pt[ok]) - np.log(pc[ok]); nctx += 1
            trans /= max(nctx, 1)
            gen, ngen = np.zeros(G), 0            # the average perturbation, whatever the target
            for cc in ([c] if c in pert_n and c != hc_eval else [k for k in pert_n if k != hc_eval]):
                if pert_n[cc] >= 10 and nsum.get((cc, -1), 0) >= 10:
                    pg, pc = pert_sum[cc] / pert_n[cc], sums[(cc, -1)] / nsum[(cc, -1)]
                    ok = (pg > 0) & (pc > 0)
                    gen[ok] += np.log(pg[ok]) - np.log(pc[ok]); ngen += 1
            gen /= max(ngen, 1)
            top = np.argsort(-np.abs(obs * valid))[:200]
            out.append({"context": corpus.contexts[c], "target": corpus.targets[t], "cells": len(cells),
                        "ll_gain_per_gene": gain, "ll_gain_specific_per_gene": gain_specific, "pi": float(pi[0]),
                        "cos_model_top200": cos(pred[top], obs[top]),
                        "cos_transfer_top200": cos(trans[top], obs[top]) if nctx else None,
                        "cos_generic_top200": cos(gen[top], obs[top]) if ngen else None,
                        "transfer_contexts": nctx})
        return out

    def summarize(rows, name):
        skipped = sum("skipped" in r for r in rows)
        rows = [r for r in rows if "skipped" not in r]
        if not rows:
            return {"regime": name, "groups": 0, "skipped_groups": skipped}
        tr = [r for r in rows if r["cos_transfer_top200"] is not None]
        return {"regime": name, "groups": len(rows), "skipped_groups": skipped,
                "mean_ll_gain_per_gene": float(np.mean([r["ll_gain_per_gene"] for r in rows])),
                "share_groups_gain_positive": float(np.mean([r["ll_gain_per_gene"] > 0 for r in rows])),
                "mean_ll_gain_specific_per_gene": float(np.mean([r["ll_gain_specific_per_gene"] for r in rows])),
                "share_groups_specific_gain_positive": float(np.mean([r["ll_gain_specific_per_gene"] > 0 for r in rows])),
                "mean_cos_model_top200": float(np.mean([r["cos_model_top200"] for r in rows])),
                "groups_with_transfer": len(tr),
                "mean_cos_model_top200_where_transfer": float(np.mean([r["cos_model_top200"] for r in tr])) if tr else None,
                "mean_cos_transfer_top200": float(np.mean([r["cos_transfer_top200"] for r in tr])) if tr else None,
                "mean_cos_generic_top200": float(np.mean([r["cos_generic_top200"] for r in rows
                                                          if r.get("cos_generic_top200") is not None]))
                if any(r.get("cos_generic_top200") is not None for r in rows) else None}

    # held-out context: its own controls, drawn at random, feed the encoder
    hc = cidx[a.holdout_context]
    hold = [Loaded(i, *L_args) for i in hold_shards]
    ctrl_rows = [(L, L.c_rows[L.control[L.c_rows]]) for L in hold]
    n_ctrl = sum(len(r) for _, r in ctrl_rows)
    frac = min(1.0, 4000 / max(n_ctrl, 1))
    ctrl = np.vstack([L.x[np.sort(np.random.choice(r, max(1, int(round(len(r) * frac))), replace=False))].toarray()
                      for L, r in ctrl_rows if len(r)]).astype(np.float32)
    hmask = np.any(np.vstack([L.mask for L in hold]), axis=0)
    hold_res = {hc: [ctrl.astype(np.float16), hmask]}
    base_props = {hc: ctrl.sum(0) / max(ctrl.sum(), 1)}
    for c, (res, _) in reservoir.items():
        base_props[c] = res.astype(np.float32).sum(0) / max(float(res.astype(np.float32).sum()), 1.0)
    groups_c, groups_j = defaultdict(list), defaultdict(list)
    for L in hold:
        for r in L.c_rows[~L.control[L.c_rows]]:
            groups_c[(hc, int(L.target[r]))].append((L, int(r)))
        for r in L.j_rows:
            groups_j[(hc, int(L.target[r]))].append((L, int(r)))
    groups_c = dict(sorted(groups_c.items(), key=lambda kv: -len(kv[1]))[:a.eval_max_targets])
    res_c = evaluate(groups_c, hold_res, base_props)
    res_j = evaluate(dict(groups_j), hold_res, base_props)
    # new targets in training contexts: reload their shards
    by_path = defaultdict(list)
    for key, cells in t_cells.items():
        for p, r in cells:
            by_path[p].append((key, r))
    groups_t = defaultdict(list)
    info_of = {str(i.path): i for i in train_shards}
    for p, items in by_path.items():
        L = Loaded(info_of[p], *L_args)
        for key, r in items:
            groups_t[key].append((L, r))
    groups_t = dict(sorted(groups_t.items(), key=lambda kv: -len(kv[1]))[:a.eval_max_targets])
    res_t = evaluate(groups_t, reservoir, base_props)
    summary = {"C": summarize(res_c, "C"), "T": summarize(res_t, "T"), "J": summarize(res_j, "J"),
               "note": "technical check: log-likelihood gain over the no-effect model with the same learned baseline; "
                       "cosines are an auxiliary pseudobulk diagnostic against observed shifts, with the transfer baseline "
                       "computed from training cells only; not a VCC score"}
    (a.out / "eval.json").write_text(json.dumps({"summary": summary, "C": res_c, "T": res_t, "J": res_j}, indent=1),
                                     encoding="utf-8")
    log("eval", **{k: v for k, v in summary.items() if k != "note"})
    (a.out / "done.json").write_text(json.dumps({"finished_utc": now(), "steps": step}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
