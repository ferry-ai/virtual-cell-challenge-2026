"""Train and evaluate the R-LAB cell network on contract shards (model: cellnet.py; data rules: cell_data.py).

    python train_cellnet.py --shards <dir or glob> [...] --axis gene_names.csv --descriptors <dir> \
        --holdout-context <context> --holdout-target-frac 0.1 --target-code descriptors --out <new dir> \
        [--epochs 2] [--batch 256] [--max-minutes 480] [--device cuda]

1. Pre-pass over every shard (before any training): labels normalised to axis symbols; hidden symbols (T) drawn
   from the symbols perturbed in training contexts; the effective class of every cell (train, C, T, J, held-out
   control); admission thresholds per (study, context) from its control cells and the admission of every cell, with
   the rule each rejection failed; control pools per (study, context) with their library, for the context encoder;
   pseudobulk sums of admitted training cells for the evaluation baselines only.
2. Training: epochs without replacement over the admitted training cells (cell_data.EpochSampler), loss weighted so
   each study weighs the same; each cell is conditioned on control cells of its own library when there are enough,
   otherwise of its own (study, context), never of another study.
3. Evaluation per effective class: log-likelihood gain over the no-effect model and over the same network told
   nothing about the target, with the same learned baseline; and one shift estimator (cell_data.shift) for observed
   cells, the model, the transfer baseline (same symbol in other training keys) and the generic-perturbation baseline.
4. Leakage check: no drawn cell may have a class other than train.

Outputs in a NEW --out: config.json, splits.json, qc.json, coverage.json, train_log.jsonl, model.pt, eval.json, done.json.
A first run on part of the corpus is a technical check, not a result (owner, 30/09).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import random
import sys
import time
from collections import Counter, OrderedDict, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cell_data as CD  # noqa: E402
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shards", nargs="+", required=True)
    ap.add_argument("--axis", required=True)
    ap.add_argument("--descriptors", type=Path)
    ap.add_argument("--target-code", choices=["descriptors", "identity", "both"], default="descriptors")
    ap.add_argument("--holdout-context", required=True)
    ap.add_argument("--holdout-target-frac", type=float, default=0.1)
    ap.add_argument("--target-split-seed", type=int, default=20260930)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--ctrl-k", type=int, default=64)
    ap.add_argument("--pool-size", type=int, default=2048, help="control cells kept per (study, context)")
    ap.add_argument("--buffer-shards", type=int, default=6)
    ap.add_argument("--input-genes", type=int, default=2048)
    ap.add_argument("--dim", type=int, default=128)
    ap.add_argument("--rank", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--max-minutes", type=float, default=480)
    ap.add_argument("--eval-min-cells", type=int, default=20)
    ap.add_argument("--eval-max-groups", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default=None)
    a = ap.parse_args()
    import torch
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    a.out.mkdir(parents=True)
    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)
    t0 = time.time()
    logf = open(a.out / "train_log.jsonl", "a", encoding="utf-8")

    def log(msg, **kw):
        line = {"t": round(time.time() - t0, 1), "msg": msg, **kw}
        print(json.dumps(line, default=str), flush=True)
        logf.write(json.dumps(line, default=str) + "\n"); logf.flush()

    axis = [l.strip().split(",")[0] for l in open(a.axis, encoding="utf-8") if l.strip()]
    if axis and axis[0].lower() in ("gene", "gene_name", "genes", "x"):
        axis = axis[1:]
    axis_set = set(axis)
    paths = shard_paths(a.shards)
    corpus = CN.Corpus.build(paths, axis, log=log)
    G = len(corpus.genes)
    gene_pos = {g: i for i, g in enumerate(corpus.genes)}
    mt = np.array([g.startswith("MT-") for g in corpus.genes])
    shards = corpus.shards
    for i, info in enumerate(shards):
        info.sid = i
        info.symbols = np.array([t if t in (CD.CONTROL, CD.UNASSIGNED, CN.MISSING) else CD.normalise(t, axis_set)
                                 for t in info.targets], dtype=object)
        info.keys = np.array([CD.key_of(info.study, c) for c in info.contexts], dtype=object)
    if a.holdout_context not in corpus.contexts:
        sys.exit(f"holdout context {a.holdout_context} is not in the corpus: {corpus.contexts}")

    # ---- 1a. splits and effective classes, from labels only
    where = defaultdict(set)
    for info in shards:
        pert = ~info.control & ~np.isin(info.symbols, [CD.UNASSIGNED, CN.MISSING])
        for c, s in zip(info.contexts[pert], info.symbols[pert]):
            where[s].add((info.study, c))
    hidden, trainable = CD.splits(where, a.holdout_context, a.holdout_target_frac, a.target_split_seed)
    trained_symbols = set(trainable) - hidden
    symbols = sorted(where)
    sidx = {s: k for k, s in enumerate(symbols)}              # target index of the network: the normalised symbol
    for info in shards:
        info.cls = np.array([CD.classify(c, s, bool(ct), a.holdout_context, hidden, trained_symbols)
                             if (s not in (CD.UNASSIGNED, CN.MISSING) or ct) else "unlabelled"
                             for c, s, ct in zip(info.contexts, info.symbols, info.control)], dtype=object)
    (a.out / "splits.json").write_text(json.dumps({
        "seed": a.target_split_seed, "holdout_context": a.holdout_context, "hidden_symbols": sorted(hidden),
        "trainable_symbols": len(trainable), "rule": "classes of cell_data.classify on normalised symbols",
        "cells_by_class": dict(Counter(c for info in shards for c in info.cls))}, indent=1), encoding="utf-8")

    # ---- 1b. pre-pass over the counts: admission QC, control pools, baseline sums
    qc_vals = defaultdict(lambda: {"lib": [], "genes": [], "mito": []})
    for info in shards:                                        # thresholds need the controls of every key first
        x, mask = CN.read_counts(info, corpus.gene_of_axis, G)
        lib, genes, mito = CD.qc_values(x, mask, mt)
        for k in np.unique(info.keys):
            sel = (info.keys == k) & info.control & (lib > 0)
            q = qc_vals[k]
            for name, v in (("lib", lib[sel]), ("genes", genes[sel]), ("mito", mito[sel])):
                if len(q[name]) < QC_KEEP:
                    q[name].extend(rng.permutation(v)[:QC_KEEP - len(q[name])].tolist())
    thresholds = {k: CD.thresholds_from_controls(np.array(v["lib"]), np.array(v["genes"]), np.array(v["mito"]))
                  for k, v in qc_vals.items() if v["lib"]}
    rejected = Counter()
    pools = {}                                                 # key -> dict(x float16 [n, G], lib per row, mask)
    sums = defaultdict(lambda: np.zeros(G))                    # (key, symbol index or -1) -> sum of proportions
    nsum = Counter()
    pert_sum, pert_n = defaultdict(lambda: np.zeros(G)), Counter()
    admitted_train = {}
    offered = Counter()
    seen_keys = set()
    per_symbol = defaultdict(lambda: [0, 0])                   # symbol -> [admitted, rejected]
    for info in shards:
        x, mask = CN.read_counts(info, corpus.gene_of_axis, G)
        info.mask = mask
        lib, genes, mito = CD.qc_values(x, mask, mt)
        ok = np.zeros(info.n_cells, bool)
        for k in np.unique(info.keys):
            sel = info.keys == k
            if k not in thresholds:
                rejected[(k, "no_controls_in_key")] += int(sel.sum())
                continue
            o, why = CD.admit(lib[sel], genes[sel], mito[sel], thresholds[k])
            ok[sel] = o
            for r, n in Counter(why[~o]).items():
                rejected[(k, r)] += n
        dup = np.array([ck in seen_keys for ck in info.cell_keys])     # the same cell in two shards counts once
        for k, n in Counter(info.keys[dup & ok]).items():
            rejected[(k, "duplicate_cell_key")] += n
        ok &= ~dup
        seen_keys.update(info.cell_keys.tolist())
        for sym, o in zip(info.symbols, ok):
            if sym not in (CD.CONTROL, CD.UNASSIGNED, CN.MISSING):
                per_symbol[sym][0 if o else 1] += 1
        info.admitted = ok
        tr = np.flatnonzero(ok & (info.cls == "train"))
        admitted_train[info.sid] = tr
        for k, n in Counter(info.keys[tr]).items():
            offered[k] += n
        for k in np.unique(info.keys):                         # control pools, every key (held-out ones for evaluation)
            rows = np.flatnonzero(ok & info.control & (info.keys == k))
            if rows.size == 0:
                continue
            take = rows if rows.size <= a.pool_size else rng.choice(rows, a.pool_size, replace=False)
            new = {"x": x[take].toarray().astype(np.float16), "lib": info.library[take], "mask": mask.copy()}
            if k in pools:
                both = np.concatenate([pools[k]["x"], new["x"]])
                libs = np.concatenate([pools[k]["lib"], new["lib"]])
                keep = rng.choice(len(both), min(len(both), a.pool_size), replace=False)
                pools[k] = {"x": both[keep], "lib": libs[keep], "mask": pools[k]["mask"] | mask}
            else:
                pools[k] = new
        if tr.size == 0:
            continue
        prop = x[tr].multiply(1.0 / np.maximum(lib[tr], 1)[:, None]).tocsr()
        for k in np.unique(info.keys[tr]):
            selk = info.keys[tr] == k
            ctrl = selk & info.control[tr]
            pert = selk & ~info.control[tr]
            if ctrl.any():
                sums[(k, -1)] += np.asarray(prop[ctrl].sum(axis=0)).ravel()
                nsum[(k, -1)] += int(ctrl.sum())
            if pert.any():
                pert_sum[k] += np.asarray(prop[pert].sum(axis=0)).ravel()
                pert_n[k] += int(pert.sum())
                for s in np.unique(info.symbols[tr][pert]):
                    ss = pert & (info.symbols[tr] == s)
                    sums[(k, sidx[s])] += np.asarray(prop[ss].sum(axis=0)).ravel()
                    nsum[(k, sidx[s])] += int(ss.sum())
    key_mask = {k: p["mask"] for k, p in pools.items()}
    lib_rows = {k: {lb: np.flatnonzero(p["lib"] == lb) for lb in np.unique(p["lib"])} for k, p in pools.items()}
    (a.out / "qc.json").write_text(json.dumps({
        "policy": "technical-failure thresholds per (study, context) from its control cells (cell_data."
                  "thresholds_from_controls: half the q01 of counts and genes, mitochondrial fraction above max(2 q99, "
                  "q99 + 0.05)); applied to every cell of the key; a key without control cells is not admitted; a cell "
                  "key seen in an earlier shard is not admitted again",
        "thresholds": thresholds, "rejected": {f"{k}|{r}": n for (k, r), n in sorted(rejected.items())},
        "highest_rejection_rate_by_perturbation": sorted(
            ({"symbol": s_, "admitted": n_ok, "rejected": n_no, "rate": n_no / (n_ok + n_no)}
             for s_, (n_ok, n_no) in per_symbol.items() if n_ok + n_no >= 20), key=lambda d: -d["rate"])[:30],
        "overall_perturbed_rejection_rate": (sum(v_[1] for v_ in per_symbol.values())
                                             / max(1, sum(v_[0] + v_[1] for v_ in per_symbol.values()))),
        "control_quantiles": {k: {n: {p: float(np.nanquantile(np.array(v[n], float), p / 100)) for p in (1, 5, 50, 95, 99)}
                                  for n in ("lib", "genes", "mito") if np.isfinite(np.array(v[n], float)).any()}
                              for k, v in qc_vals.items() if v["lib"]}}, indent=1, default=str), encoding="utf-8")
    log("prepass", keys=len(pools), admitted_train=int(sum(len(v) for v in admitted_train.values())),
        rejected=int(sum(rejected.values())), hidden=len(hidden))

    # ---- descriptors and model
    desc, desc_info = None, None
    if a.descriptors:
        Dm = np.load(a.descriptors / "descriptors.npy")
        drow = {g: k for k, g in enumerate((a.descriptors / "genes.txt").read_text(encoding="utf-8").split())}
        desc = np.zeros((len(symbols) + 1, Dm.shape[1]), np.float32)
        found = 0
        for s, k in sidx.items():
            if s in drow:
                desc[k] = Dm[drow[s]]
                found += 1
        desc_info = {"sha256": sha(a.descriptors / "descriptors.npy"), "dims": int(Dm.shape[1]),
                     "symbols_with_descriptors": found, "symbols": len(symbols)}
    target_gene = np.array([gene_pos.get(s, -1) for s in symbols] + [-1], dtype=np.int64)
    by_study = Counter()
    for info in shards:
        by_study[info.study] += len(admitted_train[info.sid])
    weights = CD.study_weights(by_study)
    tot = np.zeros(G)
    for k, p in pools.items():
        if k.split("|", 1)[1] != a.holdout_context:
            xx = p["x"].astype(np.float32)
            tot += (xx / np.maximum(xx.sum(1, keepdims=True), 1)).sum(0)
    input_genes = np.argsort(-tot)[:a.input_genes]
    midx = {m: i for i, m in enumerate(corpus.modalities)}
    stix = {s: i for i, s in enumerate(corpus.studies)}
    model = CN.build_model(G, len(symbols), len(corpus.modalities), len(corpus.studies), input_genes, dim=a.dim,
                           rank=a.rank, target_desc=desc, target_code=a.target_code).to(dev)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=1e-4)
    config = {"args": {k: str(v) for k, v in vars(a).items()}, "device": dev, "started_utc": now(),
              "code": {p.name: sha(p) for p in (HERE / "cellnet.py", HERE / "cell_data.py", Path(__file__))},
              "descriptors": desc_info, "study_weights": weights, "shards": len(paths),
              "corpus": corpus.summary(a.holdout_context)}
    (a.out / "config.json").write_text(json.dumps(config, indent=1, default=str), encoding="utf-8")
    log("model", parameters=sum(p.numel() for p in model.parameters() if p.requires_grad), target_code=a.target_code,
        symbols=len(symbols), descriptors=desc_info, study_weights=weights)

    # ---- 2. training
    cache = OrderedDict()

    def load(sid):
        if sid in cache:
            cache.move_to_end(sid)
            return cache[sid]
        x, _ = CN.read_counts(shards[sid], corpus.gene_of_axis, G)
        cache[sid] = x
        while len(cache) > a.buffer_shards + 2:
            cache.popitem(last=False)
        return x

    tgt_gene_t = torch.as_tensor(target_gene, device=dev)

    def encode(pairs, draw_rng):
        """Context codes per (key, library): controls of the same library when it has ctrl-k of them, else of the key."""
        order = sorted(set(pairs))
        rows = {g: CD.draw_controls({g[0]: lib_rows[g[0]]}, g[0], g[1], a.ctrl_k, draw_rng) for g in order}
        k = min(len(rows[g]) for g in order)
        X = np.stack([pools[g[0]]["x"][rows[g][:k]].astype(np.float32) for g in order])
        M = np.stack([key_mask[g[0]] for g in order])
        z, beta = model.context(torch.as_tensor(X, device=dev), torch.as_tensor(M, device=dev))
        return z, beta, {g: i for i, g in enumerate(order)}

    def forward(cells, unknown=False, draw_rng=None):
        """cells: list of (sid, row)."""
        xs = np.zeros((len(cells), G), np.float32)
        by = defaultdict(list)
        for j, (sid, r) in enumerate(cells):
            by[sid].append((j, r))
        for sid, items in by.items():
            x = load(sid)
            xs[[j for j, _ in items]] = x[[r for _, r in items]].toarray()
        infos = [shards[sid] for sid, _ in cells]
        rws = [r for _, r in cells]
        pairs = [(info.keys[r], info.library[r]) for info, r in zip(infos, rws)]
        z_u, beta_u, pos = encode(pairs, draw_rng or rng)
        sel = torch.as_tensor([pos[p] for p in pairs], device=dev)
        z, beta = z_u[sel], beta_u[sel]
        is_ctrl = torch.as_tensor([bool(info.control[r]) for info, r in zip(infos, rws)], device=dev)
        tgt = torch.as_tensor([len(symbols) if (info.control[r] or unknown) else sidx[info.symbols[r]]
                               for info, r in zip(infos, rws)], device=dev)
        mod = torch.as_tensor([midx[info.modality[r]] for info, r in zip(infos, rws)], device=dev)
        stu = torch.as_tensor([stix[info.study] for info in infos], device=dev)
        mask = torch.as_tensor(np.stack([key_mask[info.keys[r]] for info, r in zip(infos, rws)]), device=dev)
        x = torch.as_tensor(xs, device=dev)
        lib = (x * mask).sum(-1)
        theta = torch.exp(model.log_theta[stu]).clamp(1e-3, 1e4)
        ll0 = CN.cell_loglik(x, lib, beta, mask, theta)
        delta, pi = model(z, beta, tgt, tgt_gene_t[tgt], mod)
        ll1 = CN.cell_loglik(x, lib, beta + delta, mask, theta)
        mix = torch.logsumexp(torch.stack([torch.log(pi.clamp_min(1e-6)) + ll1,
                                           torch.log((1 - pi).clamp_min(1e-6)) + ll0]), 0)
        return x, mask, lib, beta, delta, pi, ll0, mix, is_ctrl, stu

    sampler = CD.EpochSampler([(sid, rows) for sid, rows in admitted_train.items()], a.buffer_shards, seed=a.seed)
    total_train = int(sum(len(v) for v in admitted_train.values()))
    drawn = {sid: np.zeros(shards[sid].n_cells, bool) for sid in admitted_train}
    draws, classes_drawn = Counter(), Counter()
    w_t = torch.as_tensor([weights.get(s, 0.0) for s in corpus.studies], device=dev, dtype=torch.float32)
    step, n_drawn, t_train = 0, 0, time.time()
    while total_train and n_drawn < a.epochs * total_train and (time.time() - t0) / 60 < a.max_minutes:
        cells = sampler.batch(a.batch)
        for sid, r in cells:
            drawn[sid][r] = True
            draws[shards[sid].keys[r]] += 1
            classes_drawn[shards[sid].cls[r]] += 1
        x, mask, lib, beta, delta, pi, ll0, mix, is_ctrl, stu = forward(cells)
        per_gene = mask.sum(-1).clamp_min(1)
        ll = torch.where(is_ctrl, ll0, mix) / per_gene
        loss = -(ll * w_t[stu]).sum() / w_t[stu].sum()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        step += 1
        n_drawn += len(cells)
        if step % 100 == 0 or step == 1:
            with torch.no_grad():
                log("step", step=step, epoch=round(n_drawn / total_train, 3), loss=round(float(loss), 5),
                    pert_gain=float(((mix - ll0) / per_gene)[~is_ctrl].mean()) if (~is_ctrl).any() else None,
                    pi_mean=float(pi[~is_ctrl].mean()) if (~is_ctrl).any() else None,
                    cells_per_s=round(n_drawn / (time.time() - t_train), 1))
    torch.save({"state": model.state_dict(), "genes": corpus.genes, "symbols": symbols, "studies": corpus.studies,
                "modalities": corpus.modalities, "input_genes": input_genes.tolist(), "target_code": a.target_code},
               a.out / "model.pt")
    leaks = {c: n for c, n in classes_drawn.items() if c != "train"}
    cov = {"steps": step, "batch": a.batch, "epochs_done": round(n_drawn / max(total_train, 1), 3),
           "admitted_training_cells": total_train, "draws": n_drawn,
           "by_key": [{"key": k, "admitted_offered": int(offered[k]),
                       "distinct_drawn": int(sum(int(drawn[i.sid][i.keys == k].sum()) for i in shards if i.sid in drawn)),
                       "draws": int(draws[k])} for k in sorted(offered)],
           "leakage_check": {"passed": not leaks, "non_train_classes_drawn": leaks}}
    (a.out / "coverage.json").write_text(json.dumps(cov, indent=1), encoding="utf-8")
    log("trained", steps=step, epochs=cov["epochs_done"], leakage_passed=not leaks)
    if leaks:
        sys.exit(f"leakage: {leaks}")

    # ---- 3. evaluation by effective class
    model.eval()

    def cos(u, v):
        nu, nv = np.linalg.norm(u), np.linalg.norm(v)
        return float(u @ v / (nu * nv)) if nu > 0 and nv > 0 else 0.0

    groups = defaultdict(list)
    for info in shards:
        for cl in ("C", "T", "J"):
            for r in np.flatnonzero(info.admitted & (info.cls == cl)):
                groups[(cl, info.keys[r], info.symbols[r])].append((info.sid, int(r)))
    results = {"C": [], "T": [], "J": []}
    train_keys = [k for k in pert_n if k.split("|", 1)[1] != a.holdout_context]
    for (cl, key, sym), cells in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(cells) < a.eval_min_cells or len(results[cl]) >= a.eval_max_groups:
            continue
        if key not in pools:
            results[cl].append({"key": key, "symbol": sym, "skipped": "no admitted controls"})
            continue
        cells = cells[:2000]
        with torch.no_grad():
            x, mask, lib, beta, delta, pi, ll0, mix, _, _ = forward(cells, draw_rng=np.random.default_rng(1234))
            _, _, _, _, _, _, _, mix_u, _, _ = forward(cells, unknown=True, draw_rng=np.random.default_rng(1234))
            per_gene = mask.sum(-1).clamp_min(1)
            m0 = mask[0]
            p0 = torch.softmax(beta[0].masked_fill(~m0, float("-inf")), -1)
            p1 = torch.softmax((beta[0] + delta[0]).masked_fill(~m0, float("-inf")), -1)
            p_model = (pi[0] * p1 + (1 - pi[0]) * p0).cpu().numpy()
        measured = key_mask[key]
        pc = pools[key]["x"].astype(np.float32)
        obs, ok = CD.shift(CD.mean_prop(x.cpu().numpy(), lib.cpu().numpy(), measured),
                           CD.mean_prop(pc, (pc * measured).sum(1), measured), measured)
        pred, _ = CD.shift(p_model, p0.cpu().numpy(), measured)
        trans, nt = np.zeros(G), 0
        if sym in sidx:
            for k2 in train_keys:
                if k2 != key and nsum.get((k2, sidx[sym]), 0) >= 10 and nsum.get((k2, -1), 0) >= 10:
                    s2, _ = CD.shift(sums[(k2, sidx[sym])] / nsum[(k2, sidx[sym])], sums[(k2, -1)] / nsum[(k2, -1)],
                                     key_mask[k2] & measured)
                    trans += s2
                    nt += 1
        trans /= max(nt, 1)
        gen, ng = np.zeros(G), 0
        for k2 in ([key] if key in train_keys else train_keys):
            if pert_n[k2] >= 10 and nsum.get((k2, -1), 0) >= 10:
                s2, _ = CD.shift(pert_sum[k2] / pert_n[k2], sums[(k2, -1)] / nsum[(k2, -1)], key_mask[k2] & measured)
                gen += s2
                ng += 1
        gen /= max(ng, 1)
        top = np.argsort(-np.abs(obs * ok))[:200]
        results[cl].append({"key": key, "symbol": sym, "cells": len(cells), "pi": float(pi[0]),
                            "ll_gain_vs_no_effect": float(((mix - ll0) / per_gene).mean()),
                            "ll_gain_vs_unknown_target": float(((mix - mix_u) / per_gene).mean()),
                            "cos_model": cos(pred[top], obs[top]),
                            "cos_transfer": cos(trans[top], obs[top]) if nt else None, "transfer_keys": nt,
                            "cos_generic": cos(gen[top], obs[top]) if ng else None})

    def summarize(rows, name):
        skipped = sum("skipped" in r for r in rows)
        rows = [r for r in rows if "skipped" not in r]
        out = {"class": name, "groups": len(rows), "skipped": skipped}
        if not rows:
            return out

        def mean(f):
            vals = [r[f] for r in rows if r.get(f) is not None]
            return float(np.mean(vals)) if vals else None
        tr = [r for r in rows if r["cos_transfer"] is not None]
        out.update({"ll_gain_vs_no_effect": mean("ll_gain_vs_no_effect"),
                    "ll_gain_vs_unknown_target": mean("ll_gain_vs_unknown_target"),
                    "share_target_specific_gain_positive": float(np.mean([r["ll_gain_vs_unknown_target"] > 0 for r in rows])),
                    "cos_model": mean("cos_model"), "cos_generic": mean("cos_generic"),
                    "groups_with_transfer": len(tr),
                    "cos_model_where_transfer": float(np.mean([r["cos_model"] for r in tr])) if tr else None,
                    "cos_transfer": float(np.mean([r["cos_transfer"] for r in tr])) if tr else None})
        return out
    summary = {k: summarize(v, k) for k, v in results.items()}
    summary["note"] = ("technical check: log-likelihood gains with the same learned baseline; cosines of shifts computed "
                       "with one estimator (cell_data.shift) against observed cells, on the 200 genes with the largest "
                       "observed shift; baselines from admitted training cells only; not a VCC score")
    (a.out / "eval.json").write_text(json.dumps({"summary": summary, **results}, indent=1), encoding="utf-8")
    log("eval", **{k: v for k, v in summary.items() if k != "note"})
    (a.out / "done.json").write_text(json.dumps({"finished_utc": now(), "steps": step}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
