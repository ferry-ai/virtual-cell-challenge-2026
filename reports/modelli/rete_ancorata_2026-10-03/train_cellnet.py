"""Train and evaluate the R-LAB cell network on contract shards, in two stages (model: cellnet.py; data rules:
cell_data.py).

    python train_cellnet.py prepass --shards <dir or glob> [...] --axis gene_names.csv --holdout-context <context> \
        --out <new dir> [--holdout-target-frac 0.1] [--republications <json: study -> preferred study>]
    python train_cellnet.py train --prepass <prepass dir> --out <new dir> [--descriptors <dir>] \
        [--target-code descriptors] [--epochs 2] [--budget-minutes 240] [--checkpoint-minutes 15] \
        [--workers 3] [--device cuda:0] [--resume <earlier run dir>]

prepass (CPU only: every read of the corpus happens here, not on the GPU):
0. index, from obs and var: labels parsed against the official axis (single gene, combined perturbation, unresolved
   label, control, unlabelled); each shard's gene mask, colliding native features masked, never summed; each
   (study, context) key's mask, the intersection of its shards' masks;
1. first read: QC values on the key's mask, a fingerprint of the counts, the key and the source file of each cell;
   identity by provenance (cell_data.identity), equal counts across keys only reported (cell_data.content_matches);
   hidden symbols (T) and the effective class of every cell; admission: absolute floor, relative thresholds lifted
   for perturbations they reject selectively (cell_data.phenotype_guard), declared republications left out;
2. second read: control pools per key (input genes only, each row with its shard and its library), the mean control
   profile of every key, pseudobulk sums of admitted training cells for the evaluation baselines; evaluation groups.
Writes prepass.pkl (the state the training reads), splits.json, qc.json and prepass_done.json with its sha256.

train (GPU):
- checks the state's sha256 and that every shard is present with its size;
- batches are assembled by loader processes (--workers), each owning a disjoint set of shards balanced by cells, so
  the GPU does not wait on decompression; batch k is always the same cells whatever the interruptions: samplers are
  seeded per worker role and control draws per global step;
- measures throughput on the first batches and the cost of the evaluation, then plans the end: training stops at the
  budget minus the evaluation and export reserves (plan.json);
- checkpoints every --checkpoint-minutes and when training stops: model, optimizer, step, the bitmap of the cells
  actually consumed, draws per key and class, RNG states; --resume continues the last checkpoint of an earlier run
  into a NEW --out with the same state and training arguments;
- evaluation per effective class, one read of each shard: log-likelihood gain over the no-effect model and over the
  same network told nothing about the target, with the same learned baseline; one shift estimator on the genes
  perturbed cells and controls both measure, for observed cells, the model, the transfer baseline (the same symbol
  in other training keys) and the generic-perturbation baseline;
- leakage check: no drawn cell may have a class other than train.
Outputs: config.json, plan.json, train_log.jsonl, checkpoints/, model.pt, coverage.json, eval.json, done.json.
A first run on part of the corpus is a technical check, not a result (owner, 30/09).

Version 2 (3/10, reports/modelli/rete_cellulare_2026-10-03), the corrections of the lead audit of 1/10
(reports/analisi/lead_audit_2026-10-01/NOTA_TRAINING.md and AGGIORNAMENTO_R3.md), each with its test:
- the held-out unit is a whole line group (--line-groups, --holdout-group: every study, state, donor and clone of a
  line), hidden targets are the hash fold of their reconciled key (--hidden-fold, the R-LEAD bench's function), and
  the classes C/J are computed after QC from the cells actually admitted for training;
- the loss divides the weighted log-likelihood by the nominal batch, not by the batch's own sum of weights, with
  hierarchical weights (every line group the same, every study within a group the same) on active units only;
- the control reservoir keeps, per library, the cells with the smallest hash of (seed, cell key): uniform, independent
  of the shard order, at least min(n, ctrl_k) per library; each draw records whether it left the cell's library;
- the responder gate enters the mixture through log-sigmoids of its logit (no clamp without gradient);
- arms 'generic' (no target information, trained) and context mode 'mean' (the pooled profile of the same control
  cells, no information on how cells differ) train on the same batches;
- the evaluation covers every held-out group with enough cells and exports each arm's predicted shifts
  (eval_shifts.npz) for the bench; T groups are a stratified diagnostic, not the 400 largest.

Version 3 (3/10, reports/modelli/rete_ancorata_2026-10-03/PROTOCOLLO.md): train --anchors <dir of anchors.py> starts every
perturbed cell's shift from the bench's transfer of its target, computed without the cell's own line group and without
the held-out one (cellnet.build_model, anchor_rank). The anchors are checked before training: their sha256 against
their manifest, their genes against the state's, their held-out group, and no row whose sources include its own group
or the held-out one, or whose target is hidden. The evaluation also exports 'ancora_sola', the anchor alone (g = 1,
delta = 0) through the first arm's baseline and the same estimator.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import pickle
import random
import sys
import time
from collections import Counter, OrderedDict, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cell_data as CD  # noqa: E402
import cellnet as CN  # noqa: E402

try:
    import torch
    from torch.utils.data import IterableDataset as _Iterable
except ImportError:                      # the prepass needs no torch
    torch, _Iterable = None, object

QC_KEEP = 20000
DRAWN = "train"
STATE = "prepass.pkl"
CLASSES = ["train", "C", "T", "J", "control_holdout", "combined:train", "combined:T", "combined:C", "combined:J",
           "unlabelled"]
SAME_ON_RESUME = ("arms", "epochs", "batch", "ctrl_k", "buffer_shards", "input_dim", "dim", "rank", "lr", "seed",
                  "roles", "descriptors_sha256", "pi_floor", "min_own", "delta_bound", "gate_warmup", "gate_mode",
                  "anchors_sha256")
VERSION = 3
ANCHOR_SOURCES = 6                      # source groups at most (the seven cell groups but the held-out one)
ANCHOR_ARM = "ancora_sola"


def load_anchors(folder: Path, st) -> dict:
    """The anchors of anchors.py for this prepass state, checked (module docstring, version 3), as tables:
    rows [R + 1, G] float16 with 0 where a source measures nothing and a last row of zeros (no anchor); info [R + 1, 2]
    (support / 6, presence); arow [groups, symbols + 1] the row of each (line group, target), R where none (the last
    column is the unknown target of controls); gidx [keys] the group of each key."""
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    for name, f in (("anchors_npz", "anchors.npz"), ("anchors_json", "anchors.json")):
        if sha(folder / f) != manifest["outputs"][name]:
            sys.exit(f"anchors: {f} does not hash as its manifest says")
    if manifest["held_group"] != st["holdout_group"]:
        sys.exit(f"anchors of {manifest['held_group']}, prepass of {st['holdout_group']}")
    index = json.loads((folder / "anchors.json").read_text(encoding="utf-8"))
    with np.load(folder / "anchors.npz", allow_pickle=False) as z:
        rows, U, genes = z["rows"], z["U"].astype(np.float32), [str(g) for g in z["genes"]]
    if genes != [str(g) for g in st["genes"]] or rows.shape != (len(index), len(genes)):
        sys.exit("anchors: genes or rows differ from the prepass state")
    held, hidden = st["holdout_group"], set(st.get("hidden", ()))
    bad = [r for r in index if r["group"] in r["sources"] or held in r["sources"] or r["symbol"] in hidden
           or (r["role"] == "eval") != (r["group"] == held)]
    if bad:
        sys.exit(f"anchors: {len(bad)} rows break the leakage rule, e.g. {bad[0]}")
    groups = sorted(set(st["key_group"].values()))
    gpos = {g: i for i, g in enumerate(groups)}
    spos = {s: i for i, s in enumerate(st["symbols"])}
    R = len(index)
    arow = np.full((len(groups), len(st["symbols"]) + 1), R, np.int64)
    unmatched = Counter()
    for i, r in enumerate(index):
        if r["group"] not in gpos or r["symbol"] not in spos:
            unmatched["group" if r["group"] not in gpos else "symbol"] += 1
            continue
        arow[gpos[r["group"]], spos[r["symbol"]]] = i
    table = np.zeros((R + 1, len(genes)), np.float16)
    table[:R] = np.nan_to_num(rows, nan=0.0)
    info = np.zeros((R + 1, 2), np.float32)
    info[:R, 0] = [r["support"] / ANCHOR_SOURCES for r in index]
    info[:R, 1] = 1.0
    gidx = np.array([gpos[st["key_group"][k]] for k in st["key_names"]], np.int64)
    roles = Counter(r["role"] for r in index)
    return {"rows": table, "info": info, "arow": arow, "gidx": gidx, "U": U, "sha256": manifest["outputs"]["anchors_npz"],
            "summary": {"rows": R, "rank": int(U.shape[1]), "by_role": dict(roles), "unmatched": dict(unmatched),
                        "manifest_checks": manifest.get("checks"), "rows_by_group": manifest.get("rows_by_group")}}


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


def top(counter, n=20):
    return [{"value": str(k), "cells": int(v)} for k, v in counter.most_common(n)]


def read_axis(path):
    axis = [l.strip().split(",")[0] for l in open(path, encoding="utf-8") if l.strip()]
    if axis and axis[0].lower() in ("gene", "gene_name", "genes", "x"):
        axis = axis[1:]
    return axis


def codes_of(values, table: dict) -> np.ndarray:
    """Integer codes of values, extending table (value -> code)."""
    uniq, inv = np.unique(np.asarray(values, dtype=object).astype(str), return_inverse=True)
    for u in uniq:
        table.setdefault(u, len(table))
    return np.array([table[u] for u in uniq], dtype=np.int32)[inv]


def logger(out: Path):
    t0 = time.time()
    fh = open(out / "train_log.jsonl", "a", encoding="utf-8")

    def log(msg, **kw):
        line = {"t": round(time.time() - t0, 1), "utc": now(), "msg": msg, **kw}
        print(json.dumps(line, default=str), flush=True)
        fh.write(json.dumps(line, default=str) + "\n")
        fh.flush()
    return log


# ============================================================================================== prepass

def pool_map(fn, tasks, workers):
    """fn over tasks, results in the order of the tasks; in `workers` processes when more than one. Every draw inside
    fn is seeded by its task, so the results do not depend on the number of processes."""
    if workers <= 1:
        for t in tasks:
            yield fn(t)
        return
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=workers) as ex:
        yield from ex.map(fn, tasks, chunksize=1)


def first_read(t):
    """One shard, first read: QC values on the mask of each cell's key, the fingerprint of the counts, the hash of the
    key, the control cells' QC values per key, the file's sha256 and the barcodes per context."""
    x, _ = CN.read_csr(t["path"], t["official_index"], t["measured"], t["gene_of_axis"], t["G"])
    keys, n = t["keys"], len(t["keys"])
    lib, genes, mito = np.zeros(n), np.zeros(n), np.full(n, np.nan)
    ctrl_qc, ctrl_prop = {}, {}
    for k, km in t["key_masks"].items():
        rows = np.flatnonzero(keys == k)
        l_, g_, m_ = CD.qc_values(x[rows], km, t["mt"])
        lib[rows], genes[rows], mito[rows] = l_, g_, m_
        sel = t["control"][rows] & (l_ > 0)
        if sel.any():
            ctrl_qc[k] = np.stack([l_[sel], g_[sel], m_[sel]])
            # version 2: the mean control proportions of each key, before admission, choose the input genes before
            # the second read, so the reservoir keeps only the input genes of its cells
            xs = x[rows[sel]].multiply(1.0 / l_[sel][:, None]).tocsr()
            ctrl_prop[k] = (np.asarray(xs.sum(axis=0)).ravel() * km, int(sel.sum()))
    with h5py.File(t["path"], "r") as f:
        bc = CN.h5_column(f["obs"], "barcode")
    bcs = {}
    if bc is not None:
        for c in np.unique(t["contexts"]):
            bcs[str(c)] = {str(b).split("-")[0] for b in bc[t["contexts"] == c]}
    return {"lib": lib, "genes": genes, "mito": mito, "fp": CD.fingerprints(x), "kh": CD.hash64(t["cell_keys"]),
            "ctrl_qc": ctrl_qc, "ctrl_prop": ctrl_prop, "sha256": sha(t["path"]), "bytes": Path(t["path"]).stat().st_size,
            "barcodes": bcs}


def second_read(t):
    """One shard, second read, admitted cells only: the sum and number of control proportions per key; per (key,
    library), the quota of control rows with the smallest hash of (seed, cell key) (cell_data.pool_hash, bottom_k:
    the global reservoir is the bottom-k of the union, whatever the shard order), their counts on the input genes; the
    training rows, and the proportion sums of training cells per key (all perturbed) and per (key, evaluated symbol)."""
    x, _ = CN.read_csr(t["path"], t["official_index"], t["measured"], t["gene_of_axis"], t["G"])
    keys, ok, lib_key = t["keys"], t["admitted"], t["lib_key"]
    out = {"ctrl_sum": {}, "ctrl_n": {}, "pool": {}, "pert_sum": {}, "pert_n": {}, "sums": {}, "nsum": {}}
    inp = t["input_genes"]
    for k in np.unique(keys):
        rows = np.flatnonzero(ok & t["control"] & (keys == k))
        if rows.size == 0:
            continue
        prop = x[rows].multiply(1.0 / np.maximum(lib_key[rows], 1)[:, None]).tocsr()
        out["ctrl_sum"][k] = np.asarray(prop.sum(axis=0)).ravel()
        out["ctrl_n"][k] = int(rows.size)
        u_all = CD.pool_hash(t["cell_keys"][rows], t["seed"])
        for lc in np.unique(t["libc"][rows]):
            sel = np.flatnonzero(t["libc"][rows] == lc)
            q = int(t["quota"].get((k, int(lc)), 0))
            if q <= 0:
                continue
            pick = sel[CD.bottom_k(u_all[sel], q)]
            take = rows[pick]
            xt = x[take]
            out["pool"][(k, int(lc))] = {
                "x": np.minimum(xt[:, inp].toarray(), 65504).astype(np.float16),
                "lib": np.asarray(xt.sum(axis=1)).ravel().astype(np.float32),
                "sid": np.full(take.size, t["sid"], np.int32), "libc": np.full(take.size, int(lc), np.int32),
                "u": u_all[pick], "control": t["control"][take]}
    tr = np.flatnonzero(ok & (t["cls"] == DRAWN))
    out["train_rows"] = tr
    pert_tr = tr[~t["control"][tr]]
    if pert_tr.size:
        prop = x[pert_tr].multiply(1.0 / np.maximum(lib_key[pert_tr], 1)[:, None]).tocsr()
        sym = t["symbols"][pert_tr]
        for k in np.unique(keys[pert_tr]):
            selk = keys[pert_tr] == k
            out["pert_sum"][k] = np.asarray(prop[selk].sum(axis=0)).ravel()
            out["pert_n"][k] = int(selk.sum())
            for s in np.unique(sym[selk]):
                if s in t["eval_symbols"]:
                    ss = selk & (sym == s)
                    out["sums"][(k, s)] = np.asarray(prop[ss].sum(axis=0)).ravel().astype(np.float32)
                    out["nsum"][(k, s)] = int(ss.sum())
    return out


def prepass(a):
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    a.out.mkdir(parents=True)
    log = logger(a.out)
    rng = np.random.default_rng(a.seed)
    axis = read_axis(a.axis)
    axis_set = set(axis)
    paths = shard_paths(a.shards)
    corpus = CN.Corpus.build(paths, axis, log=log)
    G = len(corpus.genes)
    mt = np.array([g.startswith("MT-") for g in corpus.genes])
    shards = corpus.shards
    if (a.holdout_group is None) == (a.holdout_context is None):
        sys.exit("give one of --holdout-group (a line group of --line-groups) and --holdout-context")
    rules = json.loads(Path(a.line_groups).read_text(encoding="utf-8")) if a.line_groups else {}
    holdout_group = a.holdout_group or a.holdout_context
    target_keys = json.loads(Path(a.target_keys).read_text(encoding="utf-8")) if a.target_keys else {}
    republications = json.loads(Path(a.republications).read_text(encoding="utf-8")) if a.republications else {}
    merged = {}                               # --same-experiment: files of one experiment become one study
    for spec in a.same_experiment or []:
        name, members = spec.split("=", 1)
        merged.update({m: name for m in members.split(",")})
    for info in shards:
        if info.study in merged:
            info.study_published = info.study
            info.study = merged[info.study]
            info.cell_keys = np.array([f"{info.study}|{k.split('|', 1)[1]}" for k in info.cell_keys], dtype=object)
    corpus.studies = sorted({i.study for i in shards})

    # ---- 0. labels, feature columns and masks, from obs and var
    parsed, combo_parts = {}, {}
    kinds_by_study, combined_by_study, unresolved_by_study = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    raw_per_symbol = defaultdict(set)
    feature_report = []
    for i, info in enumerate(shards):
        info.sid = i
        info.cols, info.mask, collided = CD.feature_columns(info.official_index, info.measured, corpus.gene_of_axis, G)
        if collided.size:
            feature_report.append({"shard": str(info.path), "study": info.study, "collided_model_genes": int(collided.size),
                                   "examples": [corpus.genes[c] for c in collided[:10]]})
        uniq, inv = np.unique(info.targets.astype(str), return_inverse=True)
        ukind, usym = [], []
        for t in uniq:
            if t in CD.UNLABELLED or t == CN.MISSING:
                ukind.append("unlabelled"); usym.append(t)
                continue
            if t not in parsed:
                parsed[t] = CD.parse_label(t, axis_set)
            kind, found = parsed[t]
            ukind.append(kind)
            if kind == "single":
                usym.append(found[0])
            elif kind == "combined":
                usym.append(CD.COMBO.join(found)); combo_parts[CD.COMBO.join(found)] = found
            else:
                usym.append(t)
        info.kind = np.array(ukind, dtype=object)[inv]
        info.symbols = np.array(usym, dtype=object)[inv]
        info.kind[info.control] = "control"
        info.symbols[info.control] = CD.CONTROL
        info.keys = np.array([CD.key_of(info.study, c) for c in info.contexts], dtype=object)
        kinds_by_study[info.study].update(info.kind.tolist())
        nc = ~info.control
        for (t, kind, s), n in Counter(zip(info.targets[nc].astype(str), info.kind[nc], info.symbols[nc])).items():
            if kind == "combined":
                combined_by_study[info.study][s] += n
            elif kind == "unresolved":
                unresolved_by_study[info.study][t] += n
            elif kind == "single":
                raw_per_symbol[(info.study, s)].add(t)
    key_mask = CD.key_masks([i.mask for i in shards], [set(np.unique(i.keys)) for i in shards])
    # version 2: the held-out unit is a whole line group (every study, state, donor and clone of the line)
    key_group = {}
    for info in shards:
        for k in np.unique(info.keys):
            key_group[k] = CD.group_of(info.study, k.split("|", 1)[1], rules)
    held_keys = sorted(k for k, g in key_group.items() if g == holdout_group)
    if not held_keys:
        sys.exit(f"holdout group {holdout_group} has no key in the corpus: groups {sorted(set(key_group.values()))}")
    held_set = set(held_keys)
    log("line groups", holdout_group=holdout_group, held_keys=held_keys,
        groups={g: sorted(k for k, gg in key_group.items() if gg == g) for g in sorted(set(key_group.values()))})
    union = defaultdict(lambda: np.zeros(G, bool))
    for info in shards:
        for k in np.unique(info.keys):
            union[k] |= info.mask
    mask_report = {k: {"genes_in_every_shard": int(m.sum()), "genes_in_some_shard_only": int((union[k] & ~m).sum())}
                   for k, m in key_mask.items()}
    many_labels = sorted(((st, s, sorted(v)) for (st, s), v in raw_per_symbol.items() if len(v) > 1),
                         key=lambda r: -len(r[2]))
    labels_report = {
        "rule": "cell_data.parse_label: one axis gene = single; two or more distinct axis genes = combined (canonical "
                "A+B, never its first gene); none = unresolved (kept as its own label); controls and unlabelled apart",
        "cells_by_kind_and_study": {st: dict(c) for st, c in kinds_by_study.items()},
        "combined_labels": {st: top(c, 30) for st, c in combined_by_study.items()},
        "unresolved_labels": {st: top(c, 30) for st, c in unresolved_by_study.items()},
        "symbols_with_several_raw_labels": {"count": len(many_labels),
                                            "examples": [{"study": st, "symbol": s, "labels": v[:6]}
                                                         for st, s, v in many_labels[:30]]}}

    # ---- 1a. first read (in --workers processes): QC values on the key's mask, fingerprints, keys, file hashes
    per = {}
    ctrl_qc = defaultdict(list)
    prop_sum, prop_n = defaultdict(lambda: np.zeros(G)), Counter()
    n_controls = Counter()
    barcodes = defaultdict(set)
    source_codes = {}
    key_order = {k: i for i, k in enumerate(sorted(key_mask))}
    tasks = [{"path": str(i.path), "official_index": i.official_index, "measured": i.measured,
              "gene_of_axis": corpus.gene_of_axis, "G": G, "keys": i.keys, "control": i.control, "mt": mt,
              "key_masks": {k: key_mask[k] for k in np.unique(i.keys)}, "cell_keys": i.cell_keys,
              "contexts": i.contexts} for i in shards]
    for info, res in zip(shards, pool_map(first_read, tasks, a.workers)):
        per[info.sid] = {"lib": res["lib"], "genes": res["genes"], "mito": res["mito"], "fp": res["fp"],
                         "kh": res["kh"],
                         "src": np.full(info.n_cells, source_codes.setdefault(info.source, len(source_codes)), np.int32)}
        info.sha256, info.bytes = res["sha256"], res["bytes"]
        for k, v in res["ctrl_qc"].items():
            ctrl_qc[k].append(v)
            n_controls[k] += int(v.shape[1])
        for k, (v, n_) in res["ctrl_prop"].items():
            prop_sum[k] += v
            prop_n[k] += n_
        for c, bcs in res["barcodes"].items():
            barcodes[(info.study, c)].update(bcs)
        log("first read", shard=info.path.name, study=info.study, cells=info.n_cells)
    qc_vals = {}
    for k, parts in ctrl_qc.items():                  # at most QC_KEEP controls per key, drawn per key: any --workers
        v = np.concatenate(parts, axis=1)
        if v.shape[1] > QC_KEEP:
            v = v[:, np.sort(np.random.default_rng([a.seed, 11, key_order[k]]).permutation(v.shape[1])[:QC_KEEP])]
        qc_vals[k] = {"lib": v[0], "genes": v[1], "mito": v[2]}
    # a key needs enough control cells to set its thresholds and to describe its context; fewer is not a context
    thresholds = {k: CD.thresholds_from_controls(np.array(v["lib"]), np.array(v["genes"]), np.array(v["mito"]))
                  for k, v in qc_vals.items() if n_controls[k] >= a.min_controls_per_key}

    # ---- 1b. identity by provenance; equal counts across keys only reported
    order = [info.sid for info in shards]
    offsets = np.cumsum([0] + [shards[s].n_cells for s in order])
    cat = lambda f: np.concatenate([f(shards[s]) for s in order])            # noqa: E731
    kh_all = np.concatenate([per[s]["kh"] for s in order])
    fp_all = np.concatenate([per[s]["fp"] for s in order])
    lib_all = np.concatenate([per[s]["lib"] for s in order])
    study_all = cat(lambda i: np.full(i.n_cells, i.study, dtype=object))
    status_all = CD.identity(kh_all, fp_all, np.concatenate([per[s]["src"] for s in order]))
    matches = CD.content_matches(kh_all, fp_all, lib_all >= a.identity_min_counts, study_all)
    identity_report = defaultdict(Counter)
    for st, s_ in zip(study_all, status_all):
        identity_report[st][s_] += 1
    overlap = []
    by_context = defaultdict(list)
    for (st, c), bcs in barcodes.items():
        by_context[c].append((st, bcs))
    for c, items in by_context.items():
        for x_ in range(len(items)):
            for y_ in range(x_ + 1, len(items)):
                (s1, b1), (s2, b2) = items[x_], items[y_]
                inter = len(b1 & b2)
                overlap.append({"context": c, "studies": [s1, s2], "shared_barcodes": inter,
                                "fraction_of_smaller": inter / max(1, min(len(b1), len(b2)))})

    # ---- 1c. hidden targets, from labels only (the classes come after admission, 1d')
    where = defaultdict(set)
    for info in shards:
        pert = np.isin(info.kind, ["single", "unresolved"])
        for c, s in zip(info.contexts[pert], info.symbols[pert]):
            where[s].add((info.study, c))
    trainable = sorted(s for s, ks in where.items() if any(CD.key_of(st, c) not in held_set for st, c in ks))
    if a.hidden_fold is not None:           # version 2: the R-LEAD hash fold of the reconciled key, in every context
        hidden = CD.hidden_by_fold(where, target_keys, a.hidden_fold, a.n_folds)
    else:                                   # version 1, kept for comparison: a seeded sample of the trainable symbols
        hidden = set(random.Random(a.target_split_seed).sample(trainable, int(round(a.holdout_target_frac
                                                                                    * len(trainable)))))
    symbols = sorted(where)
    sidx = {s: k for k, s in enumerate(symbols)}              # target index of the network: the normalised symbol

    # ---- 1d. admission: absolute floor, relative thresholds, phenotype guard, identity, declared republications
    reason_all = np.empty(offsets[-1], dtype=object)
    for j, s in enumerate(order):
        info, p = shards[s], per[s]
        reason = np.full(info.n_cells, "", dtype=object)
        for k in np.unique(info.keys):
            rows = info.keys == k
            if k not in thresholds:
                reason[rows] = "no_controls_in_key" if n_controls[k] == 0 else "too_few_controls_in_key"
                continue
            _, why = CD.admit(p["lib"][rows], p["genes"][rows], p["mito"][rows], thresholds[k])
            reason[rows] = why
        reason_all[offsets[j]:offsets[j + 1]] = reason
    keys_all, groups_all = cat(lambda i: i.keys), cat(lambda i: i.symbols)
    ctrl_all, kind_all = cat(lambda i: i.control), cat(lambda i: i.kind)
    declared = {st: pref for st, pref in republications.items()
                if st in corpus.studies and pref in corpus.studies and st != pref}
    in_declared = np.isin(study_all, list(declared)) if declared else np.zeros(offsets[-1], bool)
    unique_cell = np.isin(status_all, ["new", "collision"]) & ~in_declared
    _, r_u, guard_rows = CD.phenotype_guard(reason_all[unique_cell], groups_all[unique_cell], ctrl_all[unique_cell],
                                            keys_all[unique_cell],
                                            guarded=np.isin(kind_all[unique_cell], ["single", "unresolved", "combined"]))
    reason_all[unique_cell] = r_u
    reason_all[status_all == "duplicate"] = "duplicate_cell"
    reason_all[status_all == "version"] = "other_version_of_cell"
    for st, pref in declared.items():
        reason_all[study_all == st] = f"republication_of:{pref}"
    admitted_all = (reason_all == "") | (reason_all == "phenotype_guard")
    with_controls = set(keys_all[admitted_all & ctrl_all])        # a key needs admitted controls for its context
    lost = admitted_all & ~np.isin(keys_all, list(with_controls))
    reason_all[lost] = "no_admitted_controls_in_key"
    admitted_all &= ~lost
    for j, s in enumerate(order):
        shards[s].admitted = admitted_all[offsets[j]:offsets[j + 1]]
    rejected = Counter(zip(keys_all[~admitted_all], reason_all[~admitted_all]))
    lifted = Counter(keys_all[reason_all == "phenotype_guard"])
    per_symbol = defaultdict(lambda: [0, 0])
    pert_all = np.isin(kind_all, ["single", "unresolved", "combined"])
    for s_, ok_ in zip(groups_all[pert_all & unique_cell], admitted_all[pert_all & unique_cell]):
        per_symbol[s_][0 if ok_ else 1] += 1

    # ---- 1d'. effective classes after QC (audit 2.6): a held-out target is C only when cells of it were admitted for
    # training in a kept context; the hidden list is preserved
    trained_symbols = set()
    trained_pre_qc = set(trainable) - hidden
    for info in shards:
        kept = ~np.isin(info.keys, held_keys)
        sel = info.admitted & kept & ~info.control & np.isin(info.kind, ["single", "unresolved"])
        trained_symbols.update(s for s in np.unique(info.symbols[sel]) if s not in hidden)
    cls_cache = {}

    def cls_of(k, s, kind, trained):
        key = (k, s, kind, id(trained))
        if key not in cls_cache:
            held = k in held_set
            if kind == "control":
                cls_cache[key] = CD.classify_held(held, s, True, hidden, trained)
            elif kind in ("single", "unresolved"):
                cls_cache[key] = CD.classify_held(held, s, False, hidden, trained)
            elif kind == "combined":
                cls_cache[key] = CD.classify_combined_held(held, combo_parts[s], hidden, trained)
            else:
                cls_cache[key] = "unlabelled"
        return cls_cache[key]
    changed = Counter()
    for info in shards:
        info.cls = np.array([cls_of(k, s, kd, trained_symbols) for k, s, kd in zip(info.keys, info.symbols, info.kind)],
                            dtype=object)
        pre = np.array([cls_of(k, s, kd, trained_pre_qc) for k, s, kd in zip(info.keys, info.symbols, info.kind)],
                       dtype=object)
        for a_, b_ in zip(pre[pre != info.cls], info.cls[pre != info.cls]):
            changed[f"{a_}->{b_}"] += 1
    roles_after_qc = {"rule": "trained symbols = symbols of single-target cells admitted for training in a kept context, "
                              "hidden symbols excluded; held-out cells are C only for those",
                      "trained_symbols_before_qc": len(trained_pre_qc), "trained_symbols_after_qc": len(trained_symbols),
                      "cells_whose_class_changed": dict(changed)}

    # ---- 1e. evaluation groups (version 2): every held-out group (C, J) with --eval-min-cells admitted cells, T as a
    # diagnostic stratified by key and chosen by hash, not by size (audit P2: the 400 largest were 79% one screen);
    # each group capped at --eval-max-cells cells
    groups = defaultdict(list)
    for info in shards:
        for r in np.flatnonzero(info.admitted & np.isin(info.cls, ["C", "T", "J"])):
            groups[(info.cls[r], info.keys[r], info.symbols[r])].append((info.sid, int(r)))
    eval_groups = []
    for cl in ("C", "J", "T"):
        cand = sorted((k, v) for k, v in groups.items() if k[0] == cl and len(v) >= a.eval_min_cells)
        cap = a.eval_max_groups_t if cl == "T" else a.eval_max_groups
        if cap and len(cand) > cap:
            by_key = defaultdict(list)
            for kv in cand:
                by_key[kv[0][1]].append(kv)
            share = max(1, cap // len(by_key))
            cand = sorted(kv for items in by_key.values()
                          for kv in sorted(items, key=lambda kv: CD.unit_hash(f"{kv[0][1]}|{kv[0][2]}",
                                                                              "eval-groups"))[:share])
        for (c_, k_, s_), v in cand:
            if len(v) > a.eval_max_cells:
                pick = np.sort(rng.choice(len(v), a.eval_max_cells, replace=False))
                v = [v[i] for i in pick]
            eval_groups.append({"class": c_, "key": k_, "symbol": s_, "cells": v, "admitted_cells": len(groups[(c_, k_, s_)])})
    eval_symbols = {g["symbol"] for g in eval_groups}

    # ---- 2. second read (in --workers processes): control pools, mean control profiles, baseline sums, training rows
    key_names = sorted(key_mask)
    kidx = {k: i for i, k in enumerate(key_names)}
    lib_table, mod_table = {}, {m: i for i, m in enumerate(corpus.modalities)}
    for info in shards:
        info.libc = codes_of(info.library, lib_table)
    # version 2: input genes from the mean control proportions of the kept keys (each key weighs the same), before
    # the second read; the reservoir quota of each (key, library) from its admitted controls (cell_data.pool_quotas)
    tot = np.zeros(G)
    for k, v in prop_sum.items():
        if k not in held_set and prop_n[k]:
            tot += v / prop_n[k]
    input_genes = np.sort(np.argsort(-tot)[:a.input_genes])
    n_kl = defaultdict(Counter)
    for info in shards:
        sel = info.admitted & info.control
        for k, lc in zip(info.keys[sel], info.libc[sel]):
            n_kl[k][int(lc)] += 1
    quota = {(k, lc): q for k, libs in n_kl.items() for lc, q in CD.pool_quotas(libs, a.pool_size, a.ctrl_k).items()}
    pools = {}
    ctrl_sum, ctrl_n = defaultdict(lambda: np.zeros(G)), Counter()
    sums, nsum = {}, Counter()
    pert_sum, pert_n = defaultdict(lambda: np.zeros(G)), Counter()
    offered = Counter()
    quota_by_key = defaultdict(dict)        # built once: the pilot's prepasses (commit ad5ddd8) recomputed np.unique of
    for kl, q in quota.items():             # the shard's keys for every quota item of every shard (slow, same quotas)
        quota_by_key[kl[0]][kl] = q
    tasks = [{"path": str(i.path), "official_index": i.official_index, "measured": i.measured,
              "gene_of_axis": corpus.gene_of_axis, "G": G, "keys": i.keys, "admitted": i.admitted,
              "control": i.control, "cls": i.cls, "symbols": i.symbols, "lib_key": per[i.sid]["lib"],
              "libc": i.libc, "eval_symbols": eval_symbols, "seed": a.seed, "sid": i.sid,
              "cell_keys": i.cell_keys, "input_genes": input_genes,
              "quota": {kl: q for k in np.unique(i.keys) for kl, q in quota_by_key.get(k, {}).items()}}
             for i in shards]
    for info, res in zip(shards, pool_map(second_read, tasks, a.workers)):
        for k, v in res["ctrl_sum"].items():
            ctrl_sum[k] += v
            ctrl_n[k] += res["ctrl_n"][k]
        for kl, new in res["pool"].items():              # bottom-k of the union: any shard order, any --workers
            if kl in pools:
                both = {f: np.concatenate([pools[kl][f], new[f]]) for f in new}
                keep = CD.bottom_k(both["u"], quota[kl])
                pools[kl] = {f: v[keep] for f, v in both.items()}
            else:
                pools[kl] = new
        tr = res["train_rows"]
        info.train_rows = tr
        for k, n in Counter(info.keys[tr]).items():
            offered[k] += n
        for k, v in res["pert_sum"].items():
            pert_sum[k] += v
            pert_n[k] += res["pert_n"][k]
        for ks, v in res["sums"].items():
            sums.setdefault(ks, np.zeros(G))
            sums[ks] += v
            nsum[ks] += res["nsum"][ks]
        log("second read", shard=info.path.name, training_cells=int(tr.size))
    # the reservoir as flat arrays, key by key and library by library (a key with many libraries no longer pads the
    # others): pool_x [rows, input genes], pool_key, pool_libc, pool_sid, pool_lib
    order_kl = sorted(pools, key=lambda kl: (kidx[kl[0]], kl[1]))
    if order_kl and not all(bool(pools[kl]["control"].all()) for kl in order_kl):
        sys.exit("a perturbed cell reached the control reservoir")
    pool_x = np.concatenate([pools[kl]["x"] for kl in order_kl]) if order_kl else np.zeros((0, input_genes.size), np.float16)
    pool_lib = np.concatenate([pools[kl]["lib"] for kl in order_kl]).astype(np.float32)
    pool_sid = np.concatenate([pools[kl]["sid"] for kl in order_kl]).astype(np.int32)
    pool_libc = np.concatenate([pools[kl]["libc"] for kl in order_kl]).astype(np.int32)
    pool_key = np.concatenate([np.full(len(pools[kl]["u"]), kidx[kl[0]], np.int32) for kl in order_kl])
    # what the reservoir keeps, per key: libraries, controls, and how the cells of each library will draw
    reservoir = {}
    pert_kl = defaultdict(Counter)
    for info in shards:
        sel = info.admitted & ~info.control
        for k, lc in zip(info.keys[sel], info.libc[sel]):
            pert_kl[k][int(lc)] += 1
    for k in key_names:
        libs = n_kl.get(k, Counter())
        if not libs:
            continue
        kept = {lc: len(pools[(k, lc)]["u"]) for lc in libs if (k, lc) in pools}
        cells_by_lib = pert_kl.get(k, Counter())
        n_cells = sum(cells_by_lib.values())
        how = Counter()
        for lc, n in cells_by_lib.items():
            m = kept.get(lc, 0)
            how[CD.FALLBACK[0] if m >= a.ctrl_k else CD.FALLBACK[1] if m >= a.min_own else CD.FALLBACK[2]] += n
        reservoir[k] = {"libraries": len(libs), "controls": int(sum(libs.values())),
                        "libraries_with_ctrl_k": int(sum(v >= a.ctrl_k for v in libs.values())),
                        "kept": int(sum(kept.values())),
                        "libraries_with_ctrl_k_kept": int(sum(v >= a.ctrl_k for v in kept.values())),
                        "perturbed_cells_by_draw": {h: round(n / max(n_cells, 1), 5) for h, n in how.items()}}
    # loss weights (audit 2.2): every line group the same, every study within its group the same, active units only
    unit_of_key = {k: f"{key_group[k]}::{k.split('|', 1)[0]}" for k in key_names}
    cells_by_unit = Counter()
    for info in shards:
        for k, n in Counter(info.keys[info.train_rows]).items():
            cells_by_unit[unit_of_key[k]] += int(n)
    unit_weights = CD.hierarchical_weights(cells_by_unit, {u: u.split("::", 1)[0] for u in cells_by_unit})
    key_weights = np.array([unit_weights.get(unit_of_key[k], 0.0) for k in key_names], np.float32)
    cls_code = {c: i for i, c in enumerate(CLASSES)}
    records = []
    for info in shards:
        tgt = np.array([sidx[s] if k in ("single", "unresolved") else -1 for s, k in zip(info.symbols, info.kind)],
                       dtype=np.int32)
        records.append({"path": str(info.path), "name": info.path.name, "bytes": info.bytes, "sha256": info.sha256,
                        "study": info.study, "n": info.n_cells, "source": info.source,
                        "official_index": info.official_index, "measured": info.measured, "mask": info.mask,
                        "key": np.array([kidx[k] for k in info.keys], np.int32), "libc": info.libc,
                        "control": info.control, "mod": np.array([mod_table[m] for m in info.modality], np.int32),
                        "tgt": tgt, "cls": np.array([cls_code[c] for c in info.cls], np.int8),
                        "admitted": info.admitted, "train_rows": info.train_rows})
    train_keys = sorted(k for k in pert_n if k not in held_set)
    state = {"version": 3, "code_version": VERSION, "created_utc": now(), "args": {k: str(v) for k, v in vars(a).items()},
             "axis_sha256": sha(a.axis), "genes": corpus.genes, "gene_of_axis": corpus.gene_of_axis, "G": G,
             "contexts": corpus.contexts, "modalities": corpus.modalities, "studies": corpus.studies,
             "holdout_group": holdout_group, "held_keys": held_keys, "key_group": key_group,
             "holdout_context": holdout_group, "symbols": symbols, "hidden": sorted(hidden),
             "trainable": len(trainable), "classes": CLASSES, "key_names": key_names,
             "key_mask": np.stack([key_mask[k] for k in key_names]),
             "library_names": sorted(lib_table, key=lib_table.get), "input_genes": input_genes,
             "pool_x": pool_x, "pool_lib": pool_lib, "pool_sid": pool_sid, "pool_libc": pool_libc, "pool_key": pool_key,
             "ctrl_mean": {k: (ctrl_sum[k] / ctrl_n[k]).astype(np.float32) for k in key_names if ctrl_n[k]},
             "sums": {kv: (v / nsum[kv]).astype(np.float32) for kv, v in sums.items() if nsum[kv] >= 10},
             "pert_mean": {k: (pert_sum[k] / pert_n[k]).astype(np.float32) for k in pert_n if pert_n[k] >= 10},
             "train_keys": train_keys, "key_weights": key_weights, "unit_of_key": unit_of_key,
             "unit_weights": unit_weights, "eval_groups": eval_groups,
             "shards": records, "corpus_summary": corpus.summary(held_set)}
    with open(a.out / STATE, "wb") as fh:
        pickle.dump(state, fh, protocol=4)

    (a.out / "splits.json").write_text(json.dumps({
        "seed": a.target_split_seed, "holdout_group": holdout_group, "held_keys": held_keys,
        "line_groups": {g: sorted(k for k, gg in key_group.items() if gg == g) for g in sorted(set(key_group.values()))},
        "hidden_rule": (f"R-LEAD hash fold {a.hidden_fold} of {a.n_folds} on the reconciled key (salt {CD.FOLD_SALT})"
                        if a.hidden_fold is not None else
                        f"version 1: a sample of {a.holdout_target_frac} of the trainable symbols, seed {a.target_split_seed}"),
        "hidden_symbols": sorted(hidden), "trainable_symbols": len(trainable), "roles_after_qc": roles_after_qc,
        "loss_weights": {"rule": "cell_data.hierarchical_weights: every line group the same, every study within a group "
                                 "the same; the loss divides by the nominal batch", "by_unit": unit_weights,
                         "training_cells_by_unit": dict(cells_by_unit)},
        "rule": "classes of cell_data.classify_held on normalised single-target labels, after QC; combined perturbations "
                "by cell_data.classify_combined_held (a hidden or untrained component makes the combination T or J); "
                "only 'train' is drawn",
        "cells_by_class": dict(Counter(c for info in shards for c in info.cls)),
        "admitted_cells_by_class": dict(Counter(c for info in shards for c in info.cls[info.admitted])),
        "evaluation_groups": dict(Counter(g["class"] for g in eval_groups)),
        "labels": labels_report}, indent=1), encoding="utf-8")
    (a.out / "qc.json").write_text(json.dumps({
        "policy": "per (study, context) from its control cells (cell_data.thresholds_from_controls): an absolute floor of "
                  "usability (fewer than 10 counts or 5 genes on the model genes), never lifted; relative rules, all "
                  "lifted for a perturbation they reject selectively against its key's controls (cell_data."
                  "phenotype_guard: at least 5 cells, excess >= 0.02 and binomial p < 0.001): counts below 0.2 x and "
                  "0.5 x the controls' q01, genes detected below 0.5 x their q01, a mitochondrial fraction above "
                  "max(2 q99, q99 + 0.05); QC values on the key's mask (intersection of its shards' masks); a key "
                  "without control cells is not admitted; identity by provenance (cell_data.identity): duplicates and "
                  "other versions of a cell admitted once, collisions of keys kept; declared republications left out",
        "thresholds": thresholds,
        "controls_per_key": dict(sorted(n_controls.items())), "min_controls_per_key": a.min_controls_per_key,
        "rejected": {f"{k}|{r}": n for (k, r), n in sorted(rejected.items())},
        "phenotype_guard": {"readmitted_by_key": dict(lifted),
                            "selective_groups": [r for r in guard_rows if r["selective"]][:300],
                            "highest_non_selective_rates": sorted((r for r in guard_rows if not r["selective"]),
                                                                  key=lambda r: -r["rate"])[:30]},
        "highest_rejection_rate_by_perturbation": sorted(
            ({"symbol": s_, "admitted": n_ok, "rejected": n_no, "rate": n_no / (n_ok + n_no)}
             for s_, (n_ok, n_no) in per_symbol.items() if n_ok + n_no >= 20), key=lambda d: -d["rate"])[:30],
        "overall_perturbed_rejection_rate": (sum(v_[1] for v_ in per_symbol.values())
                                             / max(1, sum(v_[0] + v_[1] for v_ in per_symbol.values()))),
        "identity": {"rule": "cell_data.identity on (key hash, fingerprint of the counts on the model genes, source file); "
                             "equal counts under different keys are reported, never used to drop a cell "
                             f"(cells with at least {a.identity_min_counts:g} counts)",
                     "by_study": {st: dict(c) for st, c in identity_report.items()},
                     "sources": sorted(source_codes, key=source_codes.get),
                     "content_matches_across_keys": matches,
                     "declared_republications": declared, "same_experiment": merged,
                     "barcode_overlap_between_studies_of_a_context": sorted(overlap, key=lambda r: -r["fraction_of_smaller"])},
        "features": {"rule": "cell_data.feature_columns: native features colliding on one model gene are dropped and "
                             "the gene masked in that shard", "shards_with_collisions": feature_report},
        "masks": {"rule": "each cell's likelihood on its own shard's genes; control rows carry their shard's mask; a key's "
                          "QC and shift estimator on the intersection of its shards' masks", "by_key": mask_report},
        "control_quantiles": {k: {n: {p: float(np.nanquantile(np.array(v[n], float), p / 100)) for p in (1, 5, 50, 95, 99)}
                                  for n in ("lib", "genes", "mito") if np.isfinite(np.array(v[n], float)).any()}
                              for k, v in qc_vals.items() if len(v["lib"])},
        "reservoir": {"rule": "cell_data.pool_quotas and pool_hash: per (key, library) the admitted controls with the "
                              f"smallest hash of (seed, cell key); each library keeps min(n, {a.ctrl_k}), the rest of "
                              f"{a.pool_size} per key in proportion; a cell draws in its own library when it holds "
                              f"{a.ctrl_k}, with replacement in it when it holds {a.min_own}, else in the key's pool",
                      "rows": int(pool_key.size), "by_key": reservoir},
        "input_genes": {"rule": "the --input-genes genes with the largest sum over kept keys of their mean control "
                                "proportion (all controls with counts, before admission)", "n": int(input_genes.size)}},
        indent=1, default=str), encoding="utf-8")
    done = {"state": STATE, "sha256": sha(a.out / STATE), "bytes": (a.out / STATE).stat().st_size, "utc": now(),
            "shards": len(shards), "cells": int(offsets[-1]),
            "admitted_training_cells": int(sum(int(i.train_rows.size) for i in shards)),
            "evaluation_groups": len(eval_groups), "holdout_group": holdout_group, "pool_rows": int(pool_key.size)}
    (a.out / "prepass_done.json").write_text(json.dumps(done, indent=1), encoding="utf-8")
    log("prepass done", **done)


# ============================================================================================== batches

def roles_of(shards, W):
    """Shards with training rows split into W roles, greedily balanced by training cells (deterministic)."""
    parts, load = [[] for _ in range(W)], np.zeros(W)
    for sid in sorted((i for i, s in enumerate(shards) if len(s["train_rows"])), key=lambda i: (-len(shards[i]["train_rows"]), i)):
        r = int(np.argmin(load))
        parts[r].append(sid)
        load[r] += len(shards[sid]["train_rows"])
    return parts


def local_start(S, r, W):
    """Batches of role r (global steps r, r + W, ...) already consumed when the next global step is S."""
    return max(0, -(-(S - r) // W))


def role_batches(shards, parts, batch):
    """Batch size of each role, proportional to its training cells, so that every role ends its epochs together and
    the batches average `batch`."""
    n = np.array([sum(len(shards[s]["train_rows"]) for s in p) for p in parts], float)
    return [max(1, int(round(batch * len(parts) * v / max(n.sum(), 1)))) for v in n], n


def assemble(cells, xs, shards, lib_rows, ctrl_k, n_unknown, seed, step, unknown=False, min_own=8):
    """One batch as tensors: counts of the cells (CSR), their shard, codes and target; the control rows of each
    (key, library) pair, drawn with a generator seeded by (seed, step) by cell_data.draw_controls_lib (rows of the
    flat reservoir), with the way each pair was drawn (pair_fb: index into cell_data.FALLBACK)."""
    rng = np.random.default_rng([seed, 99, step])
    sid = np.array([s for s, _ in cells], np.int64)
    row = np.array([r for _, r in cells], np.int64)
    x = xs.rows(sid, row)
    key = np.array([shards[s]["key"][r] for s, r in cells], np.int64)
    libc = np.array([shards[s]["libc"][r] for s, r in cells], np.int64)
    ctrl = np.array([shards[s]["control"][r] for s, r in cells], bool)
    tgt = np.array([shards[s]["tgt"][r] for s, r in cells], np.int64)
    tgt = np.where(ctrl | unknown, n_unknown, tgt)
    pairs = sorted(set(zip(key.tolist(), libc.tolist())))
    pos = {p: i for i, p in enumerate(pairs)}
    drawn = [CD.draw_controls_lib(lib_rows, k, lc, ctrl_k, rng, min_own) for k, lc in pairs]
    pair_rows = np.stack([d[0] for d in drawn])
    return {"step": torch.tensor(step), "sid": torch.from_numpy(sid), "row": torch.from_numpy(row),
            "pair_fb": torch.tensor([d[1] for d in drawn], dtype=torch.int64),
            "crow": torch.from_numpy(x.indptr.astype(np.int64)), "col": torch.from_numpy(x.indices.astype(np.int64)),
            "val": torch.from_numpy(x.data.astype(np.float32)), "is_ctrl": torch.from_numpy(ctrl),
            "tgt": torch.from_numpy(tgt), "key": torch.from_numpy(key),
            "mod": torch.from_numpy(np.array([shards[s]["mod"][r] for s, r in cells], np.int64)),
            "stu": torch.from_numpy(np.array([shards[s]["stu"] for s in sid], np.int64)),
            "cls": torch.from_numpy(np.array([shards[s]["cls"][r] for s, r in cells], np.int64)),
            "pair_key": torch.tensor([p[0] for p in pairs], dtype=torch.int64),
            "pair_rows": torch.from_numpy(pair_rows.astype(np.int64)),
            "sel": torch.tensor([pos[p] for p in zip(key.tolist(), libc.tolist())], dtype=torch.int64)}


CHUNK_FACTOR = 6        # a row read alone decompresses about six times its own bytes (1/10: chunks of ~27.7k values,
#                         rows of ~5.6k in HIPSCI targeted); the price of a partial read, see read_bytes


def read_bytes(s, keep, partial):
    """The compressed bytes a read of rows `keep` of shard s decompresses, as priced: the whole file, or each row's
    share times CHUNK_FACTOR when the rows are read alone (at most `partial` of the shard's cells)."""
    if keep.size <= partial * s["n"]:
        return min(s["bytes"], CHUNK_FACTOR * keep.size * s["bytes"] / max(s["n"], 1)), True
    return s["bytes"], False


class ShardCache:
    """Counts of the rows a stream needs, one shard read at a time, the last `size` kept: the training rows by default,
    or the rows of `rows_by_sid`. A shard whose needed rows are at most `partial` of its cells is read row by row
    (cellnet.read_csr_rows), the others whole."""

    def __init__(self, shards, gene_of_axis, G, size, rows_of=lambda s: s["train_rows"], rows_by_sid=None,
                 partial=0.0):
        self.shards, self.gene_of_axis, self.G, self.size, self.rows_of = shards, gene_of_axis, G, size, rows_of
        self.rows_by_sid, self.partial = rows_by_sid, partial
        self.cache = OrderedDict()
        self.reads, self.read_seconds, self.partial_reads, self.priced_bytes = 0, 0.0, 0, 0.0

    def get(self, sid):
        if sid in self.cache:
            self.cache.move_to_end(sid)
            return self.cache[sid]
        s = self.shards[sid]
        t0 = time.time()
        keep = np.asarray(self.rows_by_sid[sid] if self.rows_by_sid is not None else self.rows_of(s))
        nbytes, alone = read_bytes(s, keep, self.partial)
        if alone:
            xk, _ = CN.read_csr_rows(s["path"], keep, s["official_index"], s["measured"], self.gene_of_axis, self.G)
            self.partial_reads += 1
        else:
            x, _ = CN.read_csr(s["path"], s["official_index"], s["measured"], self.gene_of_axis, self.G)
            xk = x[keep]
        self.cache[sid] = (keep, xk)
        self.reads += 1
        self.read_seconds += time.time() - t0
        self.priced_bytes += nbytes
        while len(self.cache) > self.size:
            self.cache.popitem(last=False)
        return self.cache[sid]

    def rows(self, sid, row):
        import scipy.sparse as sp
        parts, order = [], []
        for s in dict.fromkeys(sid.tolist()):
            keep, x = self.get(s)
            sel = np.flatnonzero(sid == s)
            pos = np.searchsorted(keep, row[sel])
            if (pos >= keep.size).any() or (keep[np.minimum(pos, keep.size - 1)] != row[sel]).any():
                raise KeyError(f"row not among the cached rows of shard {s}")
            parts.append(x[pos])
            order.append(sel)
        stacked = sp.vstack(parts).tocsr()
        inv = np.empty(sid.size, np.int64)
        inv[np.concatenate(order)] = np.arange(sid.size)
        return stacked[inv]


class BatchStream(_Iterable):
    """Batches of admitted training cells from global step `start` on. Role r (of W) owns a disjoint set of shards and
    produces global steps r, r + W, r + 2W, ...; its sampler is seeded by (seed, r) and each step's control draws by
    (seed, step). With W loader processes each plays one role, in the order the loader returns them; with none, one
    process plays every role in turn. Either way batch k is the same cells."""

    def __init__(self, shards, gene_of_axis, G, lib_rows, n_unknown, batch, buffer, ctrl_k, seed, W, start, min_own=8):
        self.shards, self.gene_of_axis, self.G, self.lib_rows = shards, gene_of_axis, G, lib_rows
        self.n_unknown, self.batch, self.buffer, self.ctrl_k, self.seed, self.W, self.start = \
            n_unknown, batch, buffer, ctrl_k, seed, W, start
        self.min_own = min_own
        self.parts = roles_of(shards, W)
        self.batches, _ = role_batches(shards, self.parts, batch)

    def role(self, r):
        sampler = CD.EpochSampler([(sid, self.shards[sid]["train_rows"]) for sid in self.parts[r]], self.buffer,
                                  seed=self.seed * 1000 + r)
        j = local_start(self.start, r, self.W)
        for _ in range(j):
            sampler.batch(self.batches[r])
        cache = ShardCache(self.shards, self.gene_of_axis, self.G, self.buffer + 2)
        while True:
            cells = sampler.batch(self.batches[r])
            yield assemble(cells, cache, self.shards, self.lib_rows, self.ctrl_k, self.n_unknown, self.seed, j * self.W + r,
                           min_own=self.min_own)
            j += 1

    def __iter__(self):
        info = torch.utils.data.get_worker_info()
        if info is None:
            streams = {r: self.role(r) for r in range(self.W)}
            g = self.start
            while True:
                yield next(streams[g % self.W])
                g += 1
        if info.num_workers != self.W:
            raise ValueError(f"{info.num_workers} loader processes for {self.W} roles")
        yield from self.role((info.id + self.start) % self.W)


# ============================================================================================== train

def latest_checkpoint(run_dir: Path):
    found = sorted((run_dir / "checkpoints").glob("ckpt_*.pt")) if (run_dir / "checkpoints").is_dir() else []
    if not found:
        sys.exit(f"no checkpoint in {run_dir / 'checkpoints'}")
    return found[-1]


def resolve_shards(shards, roots):
    """The shards of the prepass state on this runtime: each found by file name under `roots`, with the size the
    prepass recorded. The state is not changed: the caller uses the returned paths. Refuses a shard absent or found
    twice."""
    by_name = defaultdict(list)
    for root in roots:
        for p in Path(root).rglob("*.h5ad"):
            by_name[p.name].append(p)
    out, problems = [], []
    for s in shards:
        hits = [p for p in by_name.get(s["name"], []) if p.stat().st_size == s["bytes"]]
        if len(hits) != 1:
            problems.append(f"{s['name']}: {len(hits)} files of {s['bytes']} bytes")
        else:
            out.append(str(hits[0]))
    if problems:
        sys.exit(f"{len(problems)} shards not resolved, e.g. {problems[:3]}")
    return out


class HashCheck:
    """The sha256 of every shard against the prepass state, in a background thread: the training starts at once and
    stops if a shard differs; the evaluation waits for the check to end."""

    def __init__(self, shards, out: Path):
        import threading
        self.shards, self.out, self.bad, self.done, self.t0 = shards, out, [], False, time.time()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        for s in self.shards:
            if sha(s["path"]) != s["sha256"]:
                self.bad.append(s["path"])
        self.done = True
        (self.out / "verify.json").write_text(json.dumps({
            "shards": len(self.shards), "bytes": int(sum(s["bytes"] for s in self.shards)), "differ": self.bad,
            "seconds": round(time.time() - self.t0, 1), "rule": "sha256 of each shard against the prepass state"},
            indent=1), encoding="utf-8")

    def wait(self):
        self.thread.join()
        return not self.bad


def memory(devs=None) -> dict:
    """Peak resident memory of this process and of its live loader processes, the memory still available on the
    machine (Linux), in MB; for each CUDA device of `devs` (one device or a list) its peak allocation and reservation:
    at the top for one device, by device for several."""
    out = {}
    try:
        import resource
        out["rss_peak_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    except ImportError:
        pass
    try:
        import psutil
        me = psutil.Process()
        out["rss_mb"] = round(me.memory_info().rss / 2**20, 1)
        out["children_rss_mb"] = round(sum(c.memory_info().rss for c in me.children(recursive=True)) / 2**20, 1)
        out["system_available_mb"] = round(psutil.virtual_memory().available / 2**20, 1)
    except Exception:                    # noqa: BLE001 - memory figures are a report, never a reason to stop
        pass
    devs = [devs] if devs is not None and not isinstance(devs, (list, tuple)) else list(devs or [])
    cuda = [d for d in devs if d.type == "cuda"]
    gpu = {str(d): {"gpu_peak_mb": round(torch.cuda.max_memory_allocated(d) / 2**20, 1),
                    "gpu_reserved_mb": round(torch.cuda.memory_reserved(d) / 2**20, 1)} for d in cuda}
    if len(gpu) == 1:
        out.update(next(iter(gpu.values())))
    elif gpu:
        out["gpu"] = gpu
    return out


def parse_arms(a):
    """The arms trained on the one batch stream: --arm NAME=TARGET_CODE[/CONTEXT][@DEVICE], repeatable; each arm has
    its own model and optimizer and every arm gets the same batches (1/10, incident E-20261001-001: two arms in two
    processes read every shard twice and filled the memory). TARGET_CODE: descriptors, identity, both or generic;
    CONTEXT: cells (default) or mean (cellnet.build_model). Without --arm, one arm 'main' with --target-code on
    --device, whose files stay at the top of --out."""
    if not a.arm:
        return [("main", a.target_code, "cells", a.device)]
    arms = []
    for spec in a.arm:
        name, sep, rest = spec.partition("=")
        code_ctx, _, dev = rest.partition("@")
        code, _, ctx = code_ctx.partition("/")
        ctx = ctx or "cells"
        if not sep or not name or code not in CN.TARGET_CODES or ctx not in CN.CONTEXT_MODES:
            sys.exit(f"--arm {spec}: give NAME={'|'.join(CN.TARGET_CODES)}[/{'|'.join(CN.CONTEXT_MODES)}][@DEVICE]")
        arms.append((name, code, ctx, dev or a.device))
    if len({n for n, _, _, _ in arms}) != len(arms):
        sys.exit("two arms with one name")
    return arms


class Arm:
    """One model on the shared batch stream: its target code, context mode, device, tables, optimizer and folder."""

    def __init__(self, name, code, ctx, dev, out):
        self.name, self.code, self.ctx, self.dev, self.out = name, code, ctx, dev, out
        self.model = self.opt = self.T = self.last = None


class EvalStream(_Iterable):
    """The evaluation cells shard by shard in chunks, each chunk with the evaluation group of every cell. With loader
    processes each reads its own shards (shard k of the sorted list goes to process k mod n); the sums the evaluation
    accumulates do not depend on the order."""

    def __init__(self, by_shard, shards, gene_of_axis, G, lib_rows, ctrl_k, n_unknown, seed, chunk, partial=0.0,
                 min_own=8):
        self.by_shard, self.shards, self.gene_of_axis, self.G = by_shard, shards, gene_of_axis, G
        self.lib_rows, self.ctrl_k, self.n_unknown, self.seed, self.chunk = lib_rows, ctrl_k, n_unknown, seed, chunk
        self.needed = {s: np.unique([r for _, r in items]) for s, items in by_shard.items()}
        self.partial, self.cache, self.min_own = partial, None, min_own

    def priced_bytes(self):
        """The compressed bytes the whole evaluation decompresses, as ShardCache prices its reads."""
        return float(sum(read_bytes(self.shards[s], rows, self.partial)[0] for s, rows in self.needed.items()))

    def __iter__(self):
        info = torch.utils.data.get_worker_info()
        k, n = (info.id, info.num_workers) if info is not None else (0, 1)
        self.cache = ShardCache(self.shards, self.gene_of_axis, self.G, 1, rows_by_sid=self.needed,
                                partial=self.partial)
        for i, s in enumerate(sorted(self.by_shard)):
            if i % n != k:
                continue
            items = self.by_shard[s]
            for c0 in range(0, len(items), self.chunk):
                chunk = items[c0:c0 + self.chunk]
                b = assemble([(s, r) for _, r in chunk], self.cache, self.shards, self.lib_rows, self.ctrl_k,
                             self.n_unknown, self.seed, 10**9 + s * 10**5 + c0, min_own=self.min_own)
                b["gi"] = torch.tensor([gi for gi, _ in chunk], dtype=torch.int64)
                yield b


def train(a):
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    a.out.mkdir(parents=True)
    (a.out / "checkpoints").mkdir()
    log = logger(a.out)
    t_start = time.time()
    done_pre = json.loads((a.prepass / "prepass_done.json").read_text(encoding="utf-8"))
    state_sha = sha(a.prepass / STATE)
    if state_sha != done_pre["sha256"]:
        sys.exit(f"the prepass state hashes {state_sha}, prepass_done.json says {done_pre['sha256']}")
    with open(a.prepass / STATE, "rb") as fh:
        st = pickle.load(fh)
    shards = st["shards"]
    recorded = [s["path"] for s in shards]
    if a.shard_roots:                       # another runtime: find each shard by name and size, the state unchanged
        for s, p in zip(shards, resolve_shards(shards, a.shard_roots)):
            s["path"] = p
    bad = [s["path"] for s in shards if not Path(s["path"]).is_file() or Path(s["path"]).stat().st_size != s["bytes"]]
    if bad:
        sys.exit(f"{len(bad)} shards absent or of another size, e.g. {bad[:3]}")
    (a.out / "shards_resolved.json").write_text(json.dumps(
        [{"name": s["name"], "prepass_path": r, "path": s["path"], "bytes": s["bytes"], "sha256": s["sha256"]}
         for s, r in zip(shards, recorded)], indent=1), encoding="utf-8")
    hashes = HashCheck(shards, a.out) if not a.no_verify else None
    stix = {s: i for i, s in enumerate(st["studies"])}
    for s in shards:
        s["stu"] = stix[s["study"]]
    a.roles = max(1, a.workers) if a.roles is None else a.roles
    if a.workers not in (0, a.roles):
        sys.exit("--workers must be 0 or equal to --roles")
    specs = parse_arms(a)
    a.arms = ";".join(f"{n}={c}/{x}" for n, c, x, _ in specs)
    default_dev = "cuda" if torch.cuda.is_available() else "cpu"
    arms = [Arm(n, c, x, torch.device(d or default_dev), a.out / n if a.arm else a.out) for n, c, x, d in specs]
    for arm in arms:
        arm.out.mkdir(exist_ok=True)
    devs = list(dict.fromkeys(arm.dev for arm in arms))
    cuda_devs = [d for d in devs if d.type == "cuda"]
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    G, symbols = st["G"], st["symbols"]
    n_sym = len(symbols)
    input_genes = st["input_genes"]
    a.input_dim = int(input_genes.size)
    gene_pos = {g: i for i, g in enumerate(st["genes"])}
    desc, desc_info = None, None
    a.descriptors_sha256 = None
    if a.descriptors:
        Dm = np.load(a.descriptors / "descriptors.npy")
        drow = {g: k for k, g in enumerate((a.descriptors / "genes.txt").read_text(encoding="utf-8").split())}
        desc = np.zeros((n_sym + 1, Dm.shape[1]), np.float32)
        found = 0
        for k, s in enumerate(symbols):
            if s in drow:
                desc[k] = Dm[drow[s]]
                found += 1
        a.descriptors_sha256 = sha(a.descriptors / "descriptors.npy")
        desc_info = {"sha256": a.descriptors_sha256, "dims": int(Dm.shape[1]), "symbols_with_descriptors": found,
                     "symbols": n_sym}
    anchor = load_anchors(a.anchors, st) if a.anchors else None      # version 3
    a.anchors_sha256 = anchor["sha256"] if anchor else None
    a.anchor_rank = int(anchor["U"].shape[1]) if anchor else 0
    if anchor:
        log("anchors", **anchor["summary"])

    # tables on the device of every arm: target genes, masks per shard and per key, the flat control reservoir on the
    # input genes, loss weights per key (version 2: hierarchical, cell_data.hierarchical_weights)
    tg = np.array([gene_pos.get(s, -1) for s in symbols] + [-1], dtype=np.int64)
    masks_np = np.stack([s["mask"] for s in shards])
    w_np = np.asarray(st["key_weights"], dtype=np.float32)
    tables = {}
    for d in devs:
        T = {"target_gene": torch.as_tensor(tg, device=d), "shard_masks": torch.as_tensor(masks_np, device=d),
             "pool_x": torch.as_tensor(st["pool_x"], device=d), "pool_lib": torch.as_tensor(st["pool_lib"], device=d),
             "pool_sid": torch.as_tensor(st["pool_sid"].astype(np.int64), device=d),
             "w_k": torch.as_tensor(w_np, device=d), "key_mask": torch.as_tensor(st["key_mask"], device=d)}
        T["masks_in"] = T["shard_masks"][:, torch.as_tensor(input_genes, device=d, dtype=torch.int64)]
        if anchor:
            T.update({"anchor": torch.as_tensor(anchor["rows"], device=d),
                      "anchor_info": torch.as_tensor(anchor["info"], device=d),
                      "arow": torch.as_tensor(anchor["arow"], device=d), "gidx": torch.as_tensor(anchor["gidx"], device=d)})
        tables[d] = T
    for arm in arms:
        torch.manual_seed(a.seed)            # every arm starts from the weights of the seed, whatever the other arms
        arm.model = CN.build_model(G, n_sym, len(st["modalities"]), len(st["studies"]), input_genes, dim=a.dim,
                                   rank=a.rank, target_desc=desc, target_code=arm.code,
                                   pi_floor=a.pi_floor, context_mode=arm.ctx,
                                   delta_bound=a.delta_bound, anchor_rank=a.anchor_rank,
                                   anchor_U=anchor["U"] if anchor else None).to(arm.dev)
        arm.opt = torch.optim.AdamW([p for p in arm.model.parameters() if p.requires_grad], lr=a.lr,
                                    weight_decay=1e-4)
        arm.T = tables[arm.dev]
    same = {k: str(getattr(a, k)) for k in SAME_ON_RESUME}
    pool_key, pool_libc = np.asarray(st["pool_key"]), np.asarray(st["pool_libc"])
    lib_rows = {}
    for k in np.unique(pool_key):
        rows_k = np.flatnonzero(pool_key == k)
        lib_rows[int(k)] = {int(l): rows_k[pool_libc[rows_k] == l] for l in np.unique(pool_libc[rows_k])}
    unit_of_key, unit_weights = st["unit_of_key"], st["unit_weights"]

    def forward(b, arm, unknown=False, warm=False):
        """Per cell: counts, mask, library, baseline, shift, pi, the no-effect and the mixture log-likelihoods, the
        gate's logit and the responder component's log-likelihood (for the gate's diagnostics), and the anchor
        (version 3; zeros for controls, unknown targets and targets without one; None without anchors)."""
        dev, T, model = arm.dev, arm.T, arm.model
        B = b["sid"].shape[0]
        crow = b["crow"].to(dev)
        rows_idx = torch.repeat_interleave(torch.arange(B, device=dev), crow[1:] - crow[:-1])
        x = torch.zeros(B, G, device=dev)
        x[rows_idx, b["col"].to(dev)] = b["val"].to(dev)
        mask = T["shard_masks"][b["sid"].to(dev)]
        lib = (x * mask).sum(-1)
        pr = b["pair_rows"].to(dev)                      # rows of the flat reservoir
        z_u, beta_u = model.context(T["pool_x"][pr].float(), T["masks_in"][T["pool_sid"][pr]], T["pool_lib"][pr])
        sel = b["sel"].to(dev)
        z, beta = z_u[sel], beta_u[sel]
        is_ctrl = b["is_ctrl"].to(dev)
        tgt = torch.full_like(b["tgt"].to(dev), n_sym) if unknown else b["tgt"].to(dev)
        stu = b["stu"].to(dev)
        theta = torch.exp(model.log_theta[stu]).clamp(1e-3, 1e4)
        ll0 = CN.cell_loglik(x, lib, beta, mask, theta)
        anc = ainfo = None
        if "anchor" in T:
            ar = T["arow"][T["gidx"][b["key"].to(dev)], tgt]
            anc, ainfo = T["anchor"][ar].float(), T["anchor_info"][ar]
        delta, gate = model(z, beta, tgt, T["target_gene"][tgt], b["mod"].to(dev), anc, ainfo)
        ll1 = CN.cell_loglik(x, lib, beta + delta, mask, theta)
        if a.gate_mode == "off":    # version 2.2: no mixture, every perturbed cell carries the shift (pi = 1), so the
            mix = ll1               # shift always gets the full gradient (2.1's smoke run: the mixture let it die)
            pi = torch.ones_like(gate)
        elif warm:                  # version 2.1: during the gate warm-up pi is fixed at 1/2 and the gate learns nothing
            mix = torch.logaddexp(ll1, ll0) - math.log(2.0)
            pi = torch.full_like(gate, 0.5)
        else:
            mix = CN.mixture_loglik(gate, ll1, ll0, model.pi_floor)     # log-sigmoid weights, no clamp (audit, r3)
            pi = model.pi_of(gate)
        return x, mask, lib, beta, delta, pi, ll0, mix, is_ctrl, stu, gate, ll1, anc

    def synchronize():
        for d in cuda_devs:
            torch.cuda.synchronize(d)

    # coverage of the cells actually consumed, restored on resume
    offsets = np.cumsum([0] + [s["n"] for s in shards])
    seen = np.zeros(int(offsets[-1]), bool)
    draws, classes_drawn = Counter(), Counter()
    ctrl_draws = Counter()                   # cells by (key, how its controls were drawn: cell_data.FALLBACK)
    step, n_drawn, train_seconds, resumed_from = 0, 0, 0.0, None
    chain = hashlib.sha256(b"rlab batches").hexdigest()   # a hash chain over the cells consumed, step by step
    if a.resume:
        path = latest_checkpoint(a.resume)
        # everything to the CPU first: model and optimizer states move to their device when loaded; RNG states must
        # stay on the CPU (torch.set_rng_state and torch.cuda.set_rng_state take CPU byte tensors)
        ck = torch.load(path, map_location="cpu", weights_only=False)
        if ck["prepass_sha256"] != state_sha:
            sys.exit("the checkpoint belongs to another prepass state")
        before = {"pi_floor": "0.0", "min_own": "8", "delta_bound": "0.0", "gate_warmup": "0",
                  "gate_mode": "mixture", "anchors_sha256": "None"}                         # options added later
        diff = {k: (ck["same"].get(k, before.get(k)), v) for k, v in same.items()
                if ck["same"].get(k, before.get(k)) != v}
        if diff:
            sys.exit(f"resume with other training arguments: {diff}")
        for arm in arms:
            arm.model.load_state_dict(ck["models"][arm.name])
            arm.opt.load_state_dict(ck["opts"][arm.name])
        step, n_drawn, train_seconds = ck["step"], ck["n_drawn"], ck["train_seconds"]
        seen = np.unpackbits(ck["seen"])[:seen.size].astype(bool)
        draws, classes_drawn = Counter(ck["draws"]), Counter(ck["classes_drawn"])
        ctrl_draws = Counter({tuple(k.split("\t")): v for k, v in ck.get("ctrl_draws", {}).items()})
        chain = ck["batch_chain"]
        torch.set_rng_state(ck["rng"]["torch"].cpu())
        for d in cuda_devs:
            state = (ck["rng"].get("cuda") or {}).get(str(d))
            if state is not None:
                torch.cuda.set_rng_state(state.cpu(), device=d)
        np.random.set_state(ck["rng"]["numpy"])
        random.setstate(ck["rng"]["python"])
        resumed_from = {"checkpoint": str(path), "sha256": sha(path), "step": step, "batch_chain": chain}
        log("resumed", **resumed_from)
    total_train = int(sum(len(s["train_rows"]) for s in shards))
    if total_train == 0:
        sys.exit("no admitted training cell in the prepass state")
    rbatch, rcells = role_batches(shards, roles_of(shards, a.roles), a.batch)

    def epochs_at(S):
        """Epochs completed by the slowest role when the next global step is S."""
        return min(local_start(S, r, a.roles) * rbatch[r] / rcells[r] for r in range(a.roles) if rcells[r])

    def steps_for_epochs():
        """The first global step at which every role has drawn --epochs times its cells."""
        return max((-(-a.epochs * rcells[r] // rbatch[r]) - 1) * a.roles + r + 1 for r in range(a.roles) if rcells[r])
    step_goal = int(steps_for_epochs())
    params = {arm.name: sum(p.numel() for p in arm.model.parameters() if p.requires_grad) for arm in arms}
    config = {"args": {k: str(v) for k, v in vars(a).items()}, "same_on_resume": same,
              "devices": [str(d) for d in devs],
              "arms": [{"name": arm.name, "target_code": arm.code, "context": arm.ctx, "device": str(arm.dev),
                        "out": str(arm.out)} for arm in arms],
              "started_utc": now(), "prepass_sha256": state_sha, "resumed_from": resumed_from, "code_version": VERSION,
              "code": {p.name: sha(p) for p in (HERE / "cellnet.py", HERE / "cell_data.py", Path(__file__))},
              "descriptors": desc_info, "anchors": anchor["summary"] if anchor else None,
              "admitted_training_cells": total_train,
              "loss": {"rule": "-(sum over the batch of w * loglik per gene) / --batch, w the hierarchical weight of the "
                               "cell's unit (line group, study)", "unit_weights": unit_weights},
              "holdout_group": st.get("holdout_group"), "held_keys": st.get("held_keys"),
              "parameters": params[arms[0].name], "parameters_by_arm": params}
    (a.out / "config.json").write_text(json.dumps(config, indent=1, default=str), encoding="utf-8")
    for arm in arms:
        log("model", arm=arm.name, parameters=params[arm.name], target_code=arm.code, symbols=n_sym,
            descriptors=desc_info, device=str(arm.dev), roles=a.roles, workers=a.workers)

    def save_checkpoint(reason):
        path = a.out / "checkpoints" / f"ckpt_{step:07d}.pt"
        tmp = path.with_suffix(".partial")
        torch.save({"models": {arm.name: arm.model.state_dict() for arm in arms},
                    "opts": {arm.name: arm.opt.state_dict() for arm in arms}, "step": step, "n_drawn": n_drawn,
                    "train_seconds": train_seconds, "seen": np.packbits(seen), "draws": dict(draws),
                    "classes_drawn": dict(classes_drawn), "prepass_sha256": state_sha, "same": same,
                    "batch_chain": chain, "ctrl_draws": {f"{k}\t{c}": v for (k, c), v in ctrl_draws.items()},
                    "rng": {"torch": torch.get_rng_state(),
                            "cuda": {str(d): torch.cuda.get_rng_state(d) for d in cuda_devs},
                            "numpy": np.random.get_state(), "python": random.getstate()},
                    "memory": memory(devs), "utc": now(), "reason": reason}, tmp)
        os.replace(tmp, path)
        kept = sorted((a.out / "checkpoints").glob("ckpt_*.pt"))
        for old in kept[:-a.keep_checkpoints]:
            old.unlink()
        log("checkpoint", step=step, path=path.name, reason=reason, seen=int(seen.sum()),
            batch_chain=chain[:16])

    # ---- evaluation, streaming by shard (also used before training to price the evaluation)
    groups = st["eval_groups"]
    by_shard = defaultdict(list)
    for gi, g in enumerate(groups):
        for s, r in g["cells"]:
            by_shard[s].append((gi, r))

    def evaluate(limit_cells=None, deadline=None, workers=0):
        """Every arm on the same evaluation chunks. In this process (workers 0: the probe, whose reads are timed)
        or through loader processes that read the shards in parallel."""
        for arm in arms:
            arm.model.eval()
        # version 2: float32 sums, the observed proportions once for all arms (every group of the held-out line is
        # evaluated now, not the 400 largest)
        obs_acc = {gi: np.zeros(G, np.float32) for gi in range(len(groups))}
        acc = {arm.name: {gi: {"n": 0, "gain0": 0.0, "gainu": 0.0, "pi": 0.0, "obs": obs_acc[gi],
                               "pm": np.zeros(G, np.float32), "pb": np.zeros(G, np.float32)}
                          for gi in range(len(groups))} for arm in arms}
        if anchor:                           # version 3: the anchor alone through the first arm's baseline
            acc[ANCHOR_ARM] = {gi: {"n": 0, "pm": np.zeros(G, np.float32)} for gi in range(len(groups))}
        stream = EvalStream(by_shard, shards, st["gene_of_axis"], G, lib_rows, a.ctrl_k, n_sym, a.seed, a.eval_chunk,
                            partial=a.eval_partial, min_own=a.min_own)
        source = iter(stream) if workers == 0 else iter(torch.utils.data.DataLoader(
            stream, batch_size=None, num_workers=workers, prefetch_factor=2, pin_memory=bool(cuda_devs)))
        done_cells, t0, complete, compute = 0, time.time(), True, []
        while limit_cells is None or done_cells < limit_cells:
            b = next(source, None)
            if b is None:
                break
            if deadline and time.time() > deadline:
                complete = False
                break
            gis = b["gi"].numpy()
            t_c = time.time()
            with torch.no_grad():
                for ai, arm in enumerate(arms):
                    out = forward(b, arm)
                    x, mask, lib, beta, delta, pi, ll0, mix = out[:8]
                    mix_u = forward(b, arm, unknown=True)[7]
                    per_gene = mask.sum(-1).clamp_min(1)
                    common = arm.T["key_mask"][b["key"].to(arm.dev)]
                    p0 = torch.softmax(beta.masked_fill(~common, float("-inf")), -1)
                    p1 = torch.softmax((beta + delta).masked_fill(~common, float("-inf")), -1)
                    pm = pi[:, None] * p1 + (1 - pi[:, None]) * p0
                    if ai == 0 and anchor:
                        pa = torch.softmax((beta + out[12]).masked_fill(~common, float("-inf")), -1).cpu().numpy()
                        for j, gi in enumerate(gis):
                            acc[ANCHOR_ARM][int(gi)]["n"] += 1
                            acc[ANCHOR_ARM][int(gi)]["pm"] += pa[j]
                    g0 = ((mix - ll0) / per_gene).cpu().numpy()
                    gu = ((mix - mix_u) / per_gene).cpu().numpy()
                    pin, pmn, p0n = pi.cpu().numpy(), pm.cpu().numpy(), p0.cpu().numpy()
                    if ai == 0:
                        obn = (x * common / (x * common).sum(-1, keepdim=True).clamp_min(1)).cpu().numpy()
                        for j, gi in enumerate(gis):
                            obs_acc[int(gi)] += obn[j]
                    ac_arm = acc[arm.name]
                    for j, gi in enumerate(gis):
                        ac = ac_arm[int(gi)]
                        ac["n"] += 1; ac["gain0"] += g0[j]; ac["gainu"] += gu[j]; ac["pi"] += pin[j]
                        ac["pm"] += pmn[j]; ac["pb"] += p0n[j]
            done_cells += len(gis)
            compute.append((len(gis), time.time() - t_c))
        else:
            complete = False                 # stopped by limit_cells
        c = stream.cache if workers == 0 else None
        info = {"reads": c.reads if c else 0, "partial_reads": c.partial_reads if c else 0,
                "read_seconds": c.read_seconds if c else 0.0, "priced_bytes": c.priced_bytes if c else 0.0,
                "compute": compute, "all_priced_bytes": stream.priced_bytes()}
        del source
        for arm in arms:
            arm.model.train()
        return acc, done_cells, time.time() - t0, complete, info

    eval_cells = sum(len(g["cells"]) for g in groups)
    eval_shards = len(by_shard)
    eval_workers = a.eval_workers if a.eval_workers is not None else a.workers
    probe_cells = min(eval_cells, 3 * a.eval_chunk)
    if eval_cells:
        _, n_probe, t_probe, _, probe = evaluate(limit_cells=probe_cells)
    else:
        n_probe, t_probe, probe = 0, 0.0, {"reads": 0, "partial_reads": 0, "read_seconds": 0.0, "priced_bytes": 0.0,
                                           "compute": [], "all_priced_bytes": 0.0}
    # reads and compute priced apart (1/10, rlab-cellnet-r1: 1.5 x the probe's seconds per cell, a whole shard read
    # for few cells and the first passes on the device included, gave a reserve of 3,914 s for 1,621 s spent):
    # reads at the probe's rate over the bytes the whole evaluation decompresses, with a speed-up of 1 + 0.25 per extra
    # loader process (rlab-loader-profile-r1: 3 processes read about 1.4-1.6 times as fast as one); compute at the
    # probe's seconds per cell after its first chunk
    rate = probe["priced_bytes"] / probe["read_seconds"] if probe["read_seconds"] > 0 else None
    read_seconds = probe["all_priced_bytes"] / rate if rate else 0.0
    speedup = 1.0 + 0.25 * max(0, eval_workers - 1)
    later = probe["compute"][1:] or probe["compute"]
    per_cell = sum(t for _, t in later) / max(1, sum(n for n, _ in later))
    eval_reserve = 1.25 * (read_seconds / speedup + per_cell * eval_cells) + a.eval_reserve_seconds
    export_reserve = 60.0 * a.reserve_export_minutes
    train_deadline = t_start + 60.0 * a.budget_minutes - eval_reserve - export_reserve
    log("evaluation priced", cells=eval_cells, shards=eval_shards, probe_cells=n_probe, probe_seconds=round(t_probe, 1),
        probe_reads=probe["reads"], probe_partial_reads=probe["partial_reads"],
        probe_read_seconds=round(probe["read_seconds"], 1), probe_mb_per_s=round(rate / 2**20, 1) if rate else None,
        evaluation_priced_mb=round(probe["all_priced_bytes"] / 2**20, 1), compute_ms_per_cell=round(1e3 * per_cell, 3),
        eval_workers=eval_workers, reserve_seconds=round(eval_reserve, 1))

    # ---- training
    stream = BatchStream(shards, st["gene_of_axis"], G, lib_rows, n_sym, a.batch, a.buffer_shards, a.ctrl_k, a.seed,
                         a.roles, step, min_own=a.min_own)
    loader = torch.utils.data.DataLoader(stream, batch_size=None, num_workers=a.workers,
                                         prefetch_factor=a.prefetch if a.workers else None,
                                         pin_memory=bool(cuda_devs))
    it = iter(loader)
    if a.measure_from is None:
        per_shard = total_train / max(1, sum(1 for s in shards if len(s["train_rows"])))
        a.measure_from = int(math.ceil(3 * a.buffer_shards * per_shard / a.batch * a.roles))
    t_train0, wait, last_ckpt = time.time(), 0.0, time.time()
    measure = {"from": None, "wait": 0.0}
    plan, stop_reason = None, None
    start_step, start_n = step, n_drawn
    health_hist, health = deque(maxlen=50), None     # version 2.2: the short run inside every training
    while True:
        if step >= step_goal:
            stop_reason = "epochs done"
            break
        if time.time() >= train_deadline:
            stop_reason = "time budget"
            break
        if a.stop_after_steps is not None and step >= a.stop_after_steps:
            stop_reason = "stop-after-steps"
            break
        t_w = time.time()
        b = next(it)
        dt_wait = time.time() - t_w
        wait += dt_wait
        if int(b["step"]) != step:
            sys.exit(f"the loader returned step {int(b['step'])} where {step} was due")
        for arm in arms:
            x, mask, lib, beta, delta, pi, ll0, mix, is_ctrl, stu, gate, ll1, anc = forward(b, arm,
                                                                                          warm=step < a.gate_warmup)
            per_gene = mask.sum(-1).clamp_min(1)
            ll = torch.where(is_ctrl, ll0, mix) / per_gene
            w = arm.T["w_k"][b["key"].to(arm.dev)]
            loss = -(ll * w).sum() / a.batch            # a fixed denominator: the weights do not cancel (audit 2.2)
            arm.opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(arm.model.parameters(), 1.0)
            arm.opt.step()
            arm.last = (loss, mix, ll0, ll1, per_gene, is_ctrl, pi, delta, anc)
        sid, row = b["sid"].numpy(), b["row"].numpy()
        seen[offsets[sid] + row] = True
        chain = hashlib.sha256(bytes.fromhex(chain) + np.int64(step).tobytes() + sid.astype(np.int64).tobytes()
                               + row.astype(np.int64).tobytes()).hexdigest()
        if hashes is not None and hashes.bad:
            hashes.wait()
            sys.exit(f"shards differ from the prepass state: {hashes.bad[:3]}")
        key_np = b["key"].numpy()
        draws.update(np.array(st["key_names"], dtype=object)[key_np].tolist())
        classes_drawn.update(np.array(CLASSES, dtype=object)[b["cls"].numpy()].tolist())
        fb_cell = b["pair_fb"].numpy()[b["sel"].numpy()]
        ctrl_draws.update(zip(np.array(st["key_names"], dtype=object)[key_np].tolist(),
                              np.array(CD.FALLBACK, dtype=object)[fb_cell].tolist()))
        step += 1
        n_drawn += int(sid.size)
        if step - start_step == a.measure_from:
            synchronize()
            measure = {"from": time.time(), "wait": wait, "step": step}
        if plan is None and measure["from"] is not None and step - measure["step"] >= a.measure_steps:
            synchronize()
            span = time.time() - measure["from"]
            steps_per_s = (step - measure["step"]) / span
            remaining = train_deadline - time.time()
            need = max(0, step_goal - step)
            fit = int(max(0.0, remaining) * steps_per_s)
            plan = {"measured_steps": step - measure["step"], "measured_from_step": measure["step"],
                    "seconds": round(span, 2),
                    "steps_per_second": round(steps_per_s, 3), "cells_per_second": round(steps_per_s * a.batch, 1),
                    "data_wait_fraction": round((wait - measure["wait"]) / span, 3),
                    "budget_minutes": a.budget_minutes, "evaluation_reserve_seconds": round(eval_reserve, 1),
                    "export_reserve_seconds": export_reserve,
                    "train_until_utc": datetime.fromtimestamp(train_deadline, timezone.utc).isoformat(),
                    "steps_needed_for_epochs": need, "steps_that_fit": fit, "planned_steps": min(need, fit),
                    "epochs_expected": round(epochs_at(step + min(need, fit)), 3),
                    "admitted_training_cells": total_train, "step_at_plan": step, "memory": memory(devs),
                    "roles": {"batches": rbatch, "training_cells": rcells.astype(int).tolist()},
                    "arms": [arm.name for arm in arms]}
            (a.out / "plan.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
            log("plan", **plan)
        train_seconds += time.time() - t_w
        if step % a.log_every == 0 or step == start_step + 1:
            with torch.no_grad():
                per_arm = {}
                for arm in arms:
                    loss, mix, ll0, ll1, per_gene, is_ctrl, pi, delta, anc = arm.last
                    pert = ~is_ctrl
                    row = {"loss": round(float(loss), 5),
                           "pert_gain": float(((mix - ll0) / per_gene)[pert].mean()) if pert.any() else None,
                           "pi_mean": float(pi[pert].mean()) if pert.any() else None}
                    if pert.any():
                        # the gate's state, registered before the training (audit of r3): quantiles of pi, the
                        # posterior responsibility of the response component, the size of the shift
                        q = torch.quantile(pi[pert].float(), torch.tensor([0.1, 0.5, 0.9], device=pi.device))
                        resp = torch.exp(torch.log(pi[pert].clamp_min(1e-30)) + ll1[pert] - mix[pert])
                        row.update({"pi_q10": float(q[0]), "pi_q50": float(q[1]), "pi_q90": float(q[2]),
                                    "pi_below_1e-3": float((pi[pert] < 1e-3).float().mean()),
                                    "responsibility_mean": float(resp.mean()),
                                    "delta_rms": float(delta[pert].pow(2).mean().sqrt())})
                        if anc is not None:      # version 3: how many perturbed cells carry an anchor, and how far
                            has = anc[pert].abs().sum(-1) > 0      # the shift has moved from it
                            row.update({"anchored_share": float(has.float().mean()),
                                        "anchor_rms": float(anc[pert][has].pow(2).mean().sqrt()) if has.any() else None,
                                        "shift_minus_anchor_rms": float((delta - anc)[pert][has].pow(2).mean().sqrt())
                                        if has.any() else None})
                    per_arm[arm.name] = row
            elapsed = max(time.time() - t_train0, 1e-6)
            log("step", step=step, epoch=round(epochs_at(step), 3), **per_arm[arms[0].name],
                **({"arms": per_arm} if len(arms) > 1 else {}),
                cells_per_s=round((n_drawn - start_n) / elapsed, 1), data_wait_fraction=round(wait / elapsed, 3),
                **memory(devs))
            health_hist.append({nm: v.get("pert_gain") for nm, v in per_arm.items()})
            if a.health_check_step and health is None and step >= a.health_check_step:
                win = list(health_hist)[-a.health_window:]
                gains = {}
                for nm in per_arm:
                    vals = [h[nm] for h in win if h.get(nm) is not None]
                    gains[nm] = float(np.mean(vals)) if vals else None
                ok = all(g is not None and g > 0 for g in gains.values())
                health = {"step": step, "window_logs": len(win), "mean_pert_gain": gains, "passed": ok,
                          "rule": "PROTOCOLLO §9: at --health-check-step, every arm's mean gain of log-likelihood per gene "
                                  "over no effect, on the perturbed cells of the last --health-window logged batches, "
                                  "must be > 0; otherwise the training stops without evaluation"}
                (a.out / "health.json").write_text(json.dumps(health, indent=1), encoding="utf-8")
                log("health", **health)
                if not ok:
                    stop_reason = "unhealthy"
                    break
        if time.time() - last_ckpt >= 60.0 * a.checkpoint_minutes:
            save_checkpoint("periodic")
            last_ckpt = time.time()
    del it, loader
    if plan is None:
        plan = {"measured_steps": 0, "note": "training ended before the measurement window (--measure-from, "
                "--measure-steps)", "steps": step - start_step, "seconds": round(time.time() - t_train0, 2),
                "data_wait_fraction": round(wait / max(time.time() - t_train0, 1e-6), 3),
                "evaluation_reserve_seconds": round(eval_reserve, 1), "budget_minutes": a.budget_minutes}
        (a.out / "plan.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
    save_checkpoint(stop_reason)
    leaks = {c: n for c, n in classes_drawn.items() if c != DRAWN}
    by_key = defaultdict(lambda: [0, 0])
    for s, sh in enumerate(shards):
        tr = sh["train_rows"]
        if tr.size:
            ks = sh["key"][tr]
            hit = seen[offsets[s] + tr]
            for k in np.unique(ks):
                by_key[k][0] += int((ks == k).sum())
                by_key[k][1] += int(hit[ks == k].sum())
    elapsed = max(time.time() - t_train0, 1e-6)
    cov = {"steps": step, "batch": a.batch, "role_batches": rbatch, "epochs_done": round(epochs_at(step), 3),
           "stop": stop_reason, "arms": [arm.name for arm in arms],
           "admitted_training_cells": total_train, "draws": n_drawn, "distinct_cells_seen": int(seen.sum()),
           "resumed_from": resumed_from,
           "throughput": {"cells_per_second": round((n_drawn - start_n) / elapsed, 1),
                          "data_wait_fraction": round(wait / elapsed, 3), "seconds": round(elapsed, 1)},
           "by_key": [{"key": st["key_names"][k], "admitted_offered": v[0], "distinct_drawn": v[1],
                       "draws": int(draws.get(st["key_names"][k], 0))} for k, v in sorted(by_key.items())],
           "leakage_check": {"passed": not leaks, "non_train_classes_drawn": leaks},
           "batch_chain": chain, "memory": memory(devs)}
    # version 2: the loss coefficients the drawn cells actually carried, by line group and unit (audit 2.2), and how
    # the control cells of each key were drawn (audit 2.3)
    draws_by_unit = Counter()
    for k, n in draws.items():
        draws_by_unit[unit_of_key[k]] += n
    cov["loss_shares"] = CD.loss_shares(draws_by_unit, unit_weights, {u: u.split("::", 1)[0] for u in unit_weights})
    by_key_draw = defaultdict(dict)
    for (k, c), n in sorted(ctrl_draws.items()):
        by_key_draw[k][c] = int(n)
    cov["control_draws"] = {"rule": "cell_data.draw_controls_lib: own library without replacement, own library with "
                                    "replacement, or the key's pool; counts of training cells", "by_key": by_key_draw}
    (a.out / "coverage.json").write_text(json.dumps(cov, indent=1), encoding="utf-8")
    for arm in arms:
        torch.save({"state": arm.model.state_dict(), "genes": st["genes"], "symbols": symbols, "studies": st["studies"],
                    "modalities": st["modalities"], "input_genes": input_genes.tolist(), "target_code": arm.code,
                    "context_mode": arm.ctx, "pi_floor": a.pi_floor, "code_version": VERSION,
                    "delta_bound": a.delta_bound, "gate_warmup": a.gate_warmup, "gate_mode": a.gate_mode,
                    "dim": a.dim, "rank": a.rank, "descriptors_sha256": a.descriptors_sha256,
                    "anchor_rank": a.anchor_rank, "anchors_sha256": a.anchors_sha256,
                    "prepass_sha256": state_sha}, arm.out / "model.pt")
    log("trained", steps=step, epochs=cov["epochs_done"], stop=stop_reason, leakage_passed=not leaks)
    if leaks:
        sys.exit(f"leakage: {leaks}")
    if stop_reason in ("stop-after-steps", "unhealthy"):
        (a.out / "done.json").write_text(json.dumps({"finished_utc": now(), "steps": step, "evaluation": "skipped: "
                                                     f"stopped ({stop_reason})"}, indent=1), encoding="utf-8")
        if stop_reason == "unhealthy":
            sys.exit(f"unhealthy at step {step}: see health.json")
        return

    # ---- evaluation by effective class
    if hashes is not None and not hashes.wait():
        sys.exit(f"shards differ from the prepass state: {hashes.bad[:3]}")
    hard_deadline = t_start + 60.0 * a.budget_minutes - export_reserve
    try:
        acc_by_arm, n_eval, t_eval, complete, _ = evaluate(deadline=hard_deadline, workers=eval_workers)
    except Exception as e:               # noqa: BLE001 - a loader process lost must not cost the evaluation
        if eval_workers == 0:
            raise
        log("evaluation by loader processes failed: again in this process, within the budget", error=repr(e)[:500])
        eval_workers = 0
        acc_by_arm, n_eval, t_eval, complete, _ = evaluate(deadline=hard_deadline, workers=0)
    key_mask = st["key_mask"]

    def cos(u, v):
        nu, nv = np.linalg.norm(u), np.linalg.norm(v)
        return float(u @ v / (nu * nv)) if nu > 0 and nv > 0 else 0.0

    kidx = {k: i for i, k in enumerate(st["key_names"])}
    # the baselines depend on the group only, not on the arm
    base = {}
    for gi, g in enumerate(groups):
        if g["key"] not in st["ctrl_mean"]:
            continue
        common = key_mask[kidx[g["key"]]]
        trans, nt = np.zeros(G), 0
        for k2 in st["train_keys"]:
            if k2 != g["key"] and (k2, g["symbol"]) in st["sums"] and k2 in st["ctrl_mean"]:
                s2, _ = CD.shift(st["sums"][(k2, g["symbol"])], st["ctrl_mean"][k2], key_mask[kidx[k2]] & common)
                trans += s2
                nt += 1
        trans /= max(nt, 1)
        gen, ng = np.zeros(G), 0
        for k2 in ([g["key"]] if g["key"] in st["train_keys"] else st["train_keys"]):
            if k2 in st["pert_mean"] and k2 in st["ctrl_mean"]:
                s2, _ = CD.shift(st["pert_mean"][k2], st["ctrl_mean"][k2], key_mask[kidx[k2]] & common)
                gen += s2
                ng += 1
        gen /= max(ng, 1)
        base[gi] = (common, trans, nt, gen, ng)

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

    # version 2: the shifts of every evaluated group, for the bench (one estimator, cell_data.shift; NaN where it is
    # not defined): observed and the two baselines from training cells once, each arm's prediction in its folder
    nan16 = lambda v, ok: np.where(ok, v, np.nan).astype(np.float16)          # noqa: E731
    first = acc_by_arm[arms[0].name]
    obs_m, tra_m, gen_m = (np.full((len(groups), G), np.nan, np.float16) for _ in range(3))
    for gi, g in enumerate(groups):
        if first[gi]["n"] and gi in base:
            common, trans, nt, gen, ng = base[gi]
            o, ok = CD.shift(first[gi]["obs"] / first[gi]["n"], st["ctrl_mean"][g["key"]], common)
            obs_m[gi] = nan16(o, ok)
            if nt:
                tra_m[gi] = nan16(trans, common)
            if ng:
                gen_m[gi] = nan16(gen, common)
    np.savez_compressed(a.out / "eval_observed.npz", observed=obs_m, transfer_from_training_cells=tra_m,
                        generic_from_training_cells=gen_m, genes=np.array(st["genes"], dtype=object).astype(str),
                        n_cells=np.array([first[gi]["n"] for gi in range(len(groups))], np.int32))
    (a.out / "eval_groups.json").write_text(json.dumps(
        [{"class": g["class"], "key": g["key"], "symbol": g["symbol"], "admitted_cells": g["admitted_cells"],
          "evaluated_cells": int(first[gi]["n"])} for gi, g in enumerate(groups)], indent=0), encoding="utf-8")
    for arm in arms:
        acc = acc_by_arm[arm.name]
        results = {"C": [], "T": [], "J": []}
        pred_m = np.full((len(groups), G), np.nan, np.float16)
        for gi, g in enumerate(groups):
            ac = acc[gi]
            if ac["n"] == 0:
                results[g["class"]].append({"key": g["key"], "symbol": g["symbol"], "skipped": "not reached"})
                continue
            if gi not in base:
                results[g["class"]].append({"key": g["key"], "symbol": g["symbol"], "skipped": "no admitted controls"})
                continue
            common, trans, nt, gen, ng = base[gi]
            n = ac["n"]
            obs, ok = CD.shift(ac["obs"] / n, st["ctrl_mean"][g["key"]], common)
            pred, ok_p = CD.shift(ac["pm"] / n, ac["pb"] / n, common)
            pred_m[gi] = nan16(pred, ok_p)
            top_genes = np.argsort(-np.abs(obs * ok))[:200]
            results[g["class"]].append({"key": g["key"], "symbol": g["symbol"], "cells": n,
                                        "admitted_cells": g["admitted_cells"], "pi_mean": ac["pi"] / n,
                                        "ll_gain_vs_no_effect": ac["gain0"] / n,
                                        "ll_gain_vs_unknown_target": ac["gainu"] / n,
                                        "genes_compared": int(ok.sum()), "cos_model": cos(pred[top_genes], obs[top_genes]),
                                        "cos_transfer": cos(trans[top_genes], obs[top_genes]) if nt else None,
                                        "transfer_keys": nt,
                                        "cos_generic": cos(gen[top_genes], obs[top_genes]) if ng else None})
        np.savez_compressed(arm.out / "eval_shifts.npz", predicted=pred_m,
                            pi_mean=np.array([acc[gi]["pi"] / max(acc[gi]["n"], 1) for gi in range(len(groups))],
                                             np.float32))
        summary = {k: summarize(v, k) for k, v in results.items()}
        summary["evaluation"] = {"cells": n_eval, "seconds": round(t_eval, 1), "complete": complete,
                                 "reserve_seconds": round(eval_reserve, 1), "workers": eval_workers}
        summary["arm"] = {"name": arm.name, "target_code": arm.code, "context": arm.ctx, "device": str(arm.dev)}
        summary["note"] = ("technical check: log-likelihood gains with the same learned baseline; cosines of shifts "
                           "computed with one estimator (cell_data.shift on the key's genes, measured by perturbed cells "
                           "and controls alike) against observed cells, on the 200 genes with the largest observed "
                           "shift; baselines from admitted training cells only; not a VCC score")
        (arm.out / "eval.json").write_text(json.dumps({"summary": summary, **results}, indent=1, default=float),
                                           encoding="utf-8")
        log("eval", arm=arm.name, **{k: v for k, v in summary.items() if k not in ("note", "arm")})
    if anchor:          # version 3: the anchor alone (g = 1, delta = 0), the first arm's baseline, the same estimator
        out_a = a.out / ANCHOR_ARM
        out_a.mkdir(exist_ok=True)
        pa_m = np.full((len(groups), G), np.nan, np.float16)
        acc_a, acc0 = acc_by_arm[ANCHOR_ARM], acc_by_arm[arms[0].name]
        for gi in range(len(groups)):
            if acc_a[gi]["n"] and gi in base:
                pred, ok_p = CD.shift(acc_a[gi]["pm"] / acc_a[gi]["n"], acc0[gi]["pb"] / acc0[gi]["n"], base[gi][0])
                pa_m[gi] = nan16(pred, ok_p)
        np.savez_compressed(out_a / "eval_shifts.npz", predicted=pa_m)
        (out_a / "eval.json").write_text(json.dumps({"summary": {
            "evaluation": {"cells": n_eval, "complete": complete}, "baseline_arm": arms[0].name,
            "note": "the anchor alone through the first arm's baseline and estimator; evaluation only, no training"}},
            indent=1), encoding="utf-8")
    (a.out / "done.json").write_text(json.dumps({"finished_utc": now(), "steps": step,
                                                 "wall_seconds": round(time.time() - t_start, 1),
                                                 "budget_seconds": 60.0 * a.budget_minutes,
                                                 "arms": [arm.name for arm in arms],
                                                 "memory": memory(devs)}, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepass")
    p.add_argument("--shards", nargs="+", required=True)
    p.add_argument("--axis", required=True)
    p.add_argument("--holdout-group", help="the line group held out whole (version 2; groups from --line-groups)")
    p.add_argument("--line-groups", help="JSON {'contexts': {context: group}, 'study_prefixes': {prefix: group}}; a "
                                         "context of no rule is a group of its own (cell_data.group_of)")
    p.add_argument("--holdout-context", help="version 1: one context held out (a group of its own)")
    p.add_argument("--hidden-fold", type=int, help="version 2: the targets of this R-LEAD hash fold are hidden "
                                                    "everywhere (regime J); without it, version 1's seeded sample")
    p.add_argument("--n-folds", type=int, default=5)
    p.add_argument("--target-keys", help="JSON {symbol: reconciled key} for the hash folds (else SYM:<symbol>)")
    p.add_argument("--holdout-target-frac", type=float, default=0.1, help="version 1 only")
    p.add_argument("--target-split-seed", type=int, default=20260930, help="version 1 only")
    p.add_argument("--ctrl-k", type=int, default=64, help="controls each library keeps in the reservoir if it has them "
                                                          "(the training's --ctrl-k)")
    p.add_argument("--min-own", type=int, default=8, help="reported only: below this a library's cells draw from the key")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--republications", help="JSON {study: preferred study}: the first is left out when both are present")
    p.add_argument("--same-experiment", nargs="+", metavar="NAME=STUDY,STUDY",
                   help="files of one experiment read as one study NAME (their shared cells are then duplicates)")
    p.add_argument("--min-controls-per-key", type=int, default=30,
                   help="a (study, context) with fewer usable control cells is not admitted")
    p.add_argument("--workers", type=int, default=1, help="processes reading shards (results do not depend on it)")
    p.add_argument("--pool-size", type=int, default=2048,
                   help="control cells kept per (study, context) beyond min(n, --ctrl-k) per library")
    p.add_argument("--input-genes", type=int, default=2048)
    p.add_argument("--eval-min-cells", type=int, default=20)
    p.add_argument("--eval-max-groups", type=int, default=0, help="C and J groups (0: all, version 2)")
    p.add_argument("--eval-max-groups-t", type=int, default=300, help="T groups, stratified by key, chosen by hash")
    p.add_argument("--eval-max-cells", type=int, default=500)
    p.add_argument("--identity-min-counts", type=float, default=200,
                   help="cells with fewer counts are not reported as content matches (too few to be told apart)")
    p.add_argument("--seed", type=int, default=0)
    t = sub.add_parser("train")
    t.add_argument("--prepass", required=True, type=Path)
    t.add_argument("--out", required=True, type=Path)
    t.add_argument("--descriptors", type=Path)
    t.add_argument("--anchors", type=Path, help="version 3: the output folder of anchors.py for this prepass state")
    t.add_argument("--target-code", choices=["descriptors", "identity", "both"], default="descriptors")
    t.add_argument("--arm", action="append", default=[], metavar="NAME=TARGET_CODE[@DEVICE]",
                   help="an arm trained on the shared batches (repeatable; its files go to --out/NAME); without it, "
                        "one arm with --target-code on --device, its files at the top of --out")
    t.add_argument("--eval-workers", type=int, default=None,
                   help="loader processes that read the evaluation shards (default: --workers)")
    t.add_argument("--eval-partial", type=float, default=0.08,
                   help="a shard whose evaluation cells are at most this share of its cells is read row by row "
                        "(cellnet.read_csr_rows), the others whole")
    t.add_argument("--epochs", type=float, default=2.0)
    t.add_argument("--batch", type=int, default=256)
    t.add_argument("--ctrl-k", type=int, default=64)
    t.add_argument("--min-own", type=int, default=8,
                   help="a library with fewer pooled controls than --ctrl-k but at least this many is resampled with "
                        "replacement; below it, the cell draws from the key's pool (cell_data.draw_controls_lib)")
    t.add_argument("--buffer-shards", type=int, default=4)
    t.add_argument("--dim", type=int, default=128)
    t.add_argument("--rank", type=int, default=128)
    t.add_argument("--lr", type=float, default=1e-3)
    t.add_argument("--delta-bound", type=float, default=0.0,
                   help="version 2.1: shifts bounded smoothly, B tanh(raw / B) (0: unbounded, the pilot r1)")
    t.add_argument("--gate-mode", choices=["mixture", "off"], default="mixture",
                   help="version 2.2: 'off' drops the responder mixture, every perturbed cell carries the shift")
    t.add_argument("--health-check-step", type=int, default=0,
                   help="version 2.2: at this step every arm must gain log-likelihood over no effect, else stop (0: none)")
    t.add_argument("--health-window", type=int, default=5, help="logged batches averaged by the health check")
    t.add_argument("--gate-warmup", type=int, default=0,
                   help="version 2.1: steps with pi fixed at 1/2 before the gate learns (0: none, the pilot r1)")
    t.add_argument("--pi-floor", type=float, default=0.0,
                   help="floor on the responder probability, pi in [floor, 1 - floor] (0: none, the model until 1/10)")
    t.add_argument("--seed", type=int, default=0)
    t.add_argument("--workers", type=int, default=0, help="loader processes (0: the main process assembles batches)")
    t.add_argument("--roles", type=int, default=None, help="shard partitions (default: max(1, workers))")
    t.add_argument("--prefetch", type=int, default=8, help="batches prepared ahead by each loader process")
    t.add_argument("--budget-minutes", type=float, default=240)
    t.add_argument("--reserve-export-minutes", type=float, default=5)
    t.add_argument("--checkpoint-minutes", type=float, default=15)
    t.add_argument("--keep-checkpoints", type=int, default=3)
    t.add_argument("--measure-from", type=int, default=None,
                   help="steps of warm-up before the throughput is measured (default: until every role has read its "
                        "initial buffer of shards three times over, so the plan sees the steady state; 1/10, "
                        "rlab-cellnet-r1 measured 3,763 cells/s on the initial buffer and trained at about 600)")
    t.add_argument("--measure-steps", type=int, default=300)
    t.add_argument("--eval-chunk", type=int, default=512)
    t.add_argument("--eval-reserve-seconds", type=float, default=60,
                   help="added to the priced evaluation: 1.5 x the probe's seconds per cell x the evaluation cells")
    t.add_argument("--log-every", type=int, default=100)
    t.add_argument("--resume", type=Path, help="an earlier run directory: continue from its last checkpoint")
    t.add_argument("--shard-roots", nargs="+", help="find the shards of the prepass state by name and size under these "
                                                    "folders (another runtime); the state is not changed")
    t.add_argument("--no-verify", action="store_true", help="skip the background sha256 check of the shards (tests)")
    t.add_argument("--stop-after-steps", type=int, help="stop at this global step after a checkpoint, without "
                                                          "evaluation (simulates an interruption; tests)")
    t.add_argument("--device", default=None)
    a = ap.parse_args()
    prepass(a) if a.cmd == "prepass" else train(a)


if __name__ == "__main__":
    main()
