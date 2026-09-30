"""Data side of the R-LAB cell network: labels, splits, admission QC, sampling and the shift estimator.

Kept apart from the model so each property can be checked on small synthetic cases (test_cell_data.py) before any
long training (review of 30/09, 23:00):
- controls and masks by study: every context is keyed by (study, context); two studies of the same cell line never
  share controls, baselines or masks; control cells also carry their library, so a cell can be conditioned on the
  controls of its own library when there are enough of them;
- labels: a perturbation label is normalised to a gene symbol of the official axis when it names one (directly, or as
  `SYMBOL_<guide>` / `SYMBOL|<...>`), otherwise it stays its own label; splits and the C/T/J classes use the
  normalised symbol, so a target hidden under one spelling cannot enter training under another;
- effective classes: for the held-out context, C is a symbol perturbed in some training context; J is a hidden
  symbol, or one never perturbed in any training context; T is a hidden symbol evaluated in a training context;
- admission QC: thresholds per (study, context) from its control cells only, set beyond the controls' 1st and 99th
  percentiles (half the q01 of counts and genes detected; mitochondrial fraction above max(2 x q99, q99 + 0.05)) so
  that they catch technical failures and not a knockdown phenotype; fixed before training, applied to every cell of
  the key, held-out ones included; each rejection is counted by rule, and the rejection rate per perturbation shows
  whether a rule removes one selectively;
- sampling without replacement: an epoch visits every admitted training cell exactly once; balance between studies
  comes from loss weights (each study weighs the same in expectation), not from resampling;
- one estimator for every shift in the evaluation: log of the mean per-cell proportion, perturbed against controls
  of the same (study, context), on genes measured there; the same function serves observed cells, baselines and the
  model's expected proportions.

Four rules added before any extended training (owner, 30/09 23:39, on the review of Codex; revised the same night on
a second note of Codex), each with its cases in test_cell_data.py and test_prepass.py:
- duplicates and collisions: identity rests on provenance, not on counts alone. Within one key (study|library|barcode)
  the same counts are one cell ingested twice (admitted once); other counts from the same source file are two cells
  sharing a key (both kept, flagged); other counts from another source file are another version of the same cell
  (admitted once). Across keys, equal counts are only reported: independent cells can have equal projected counts,
  and a reprocessed republication can have different ones, so a republication is excluded only when declared, for
  the whole dataset. Native features that land on one model gene are never summed: that gene is not measured there;
- combined perturbations: a label naming two or more axis genes is a combined perturbation with a canonical label
  (`A+B`), never its first gene; its class says whether a component is hidden, and in version 0 it is not drawn;
- phenotype conservation in QC: only an absolute floor of usability is never lifted (fewer than 10 counts or 5 genes
  on the model genes: no expression profile to learn from). Every threshold relative to the controls (counts far
  below or below them, genes detected, mitochondrial fraction) is a suspicion, not a verdict: it is lifted for a
  perturbation it rejects well above the rate of its key's controls, because a strong loss of RNA or a stressed
  state is that perturbation's phenotype, not a technical failure;
- control masks: every cell and every control row keep the gene mask of their own shard; a (study, context) key has
  the intersection of its shards' masks, used by QC and by the estimator; the union of masks is never used.
"""
from __future__ import annotations

import hashlib
import random
import re
from collections import Counter, defaultdict

import numpy as np

SEP = re.compile(r"[|_,;+\s]")
CONTROL, UNASSIGNED = "NTC", "UNASSIGNED"
COMBO = "+"


def parse_label(label: str, axis: set) -> tuple:
    """(kind, symbols) of a perturbation label: 'single' with its one axis gene, 'combined' with its distinct axis genes
    (sorted), or 'unresolved' with none. Guides of one gene (`TFAM_+_...|TFAM_-_...`, `LAT_2`, `CEBPE_ctrl`) are
    single; `CEBPA_CEBPB` or `CEBPB+CEBPA` are combined."""
    if label in axis:
        return "single", (label,)
    found = sorted({t for t in SEP.split(label) if t in axis})
    if not found:
        return "unresolved", ()
    return ("single" if len(found) == 1 else "combined"), tuple(found)


def normalise(label: str, axis: set) -> str:
    """A label as its gene symbol when it names one gene; as the canonical `A+B` when it names several; the label
    itself otherwise."""
    kind, found = parse_label(label, axis)
    if kind == "single":
        return found[0]
    if kind == "combined":
        return COMBO.join(found)
    return label


def classify_combined(context: str, parts, holdout_context: str, hidden: set, trained_symbols: set) -> str:
    """Class of a combined perturbation: in the held-out context 'combined:C' only when every component is trained,
    else 'combined:J'; elsewhere 'combined:T' when a component is hidden, else 'combined:train'. Version 0 of the
    network draws none of them: a hidden target inside a combination can never reach training."""
    if context == holdout_context:
        return "combined:C" if all(p in trained_symbols for p in parts) else "combined:J"
    return "combined:T" if any(p in hidden for p in parts) else "combined:train"


def key_of(study, context):
    return f"{study}|{context}"


def splits(labels_where: dict, holdout_context: str, frac: float, seed: int):
    """labels_where: symbol -> set of (study, context) where it is perturbed. Returns the hidden symbols (T) drawn among
    the symbols perturbed in at least one training context."""
    trainable = sorted(s for s, keys in labels_where.items() if any(c != holdout_context for _, c in keys))
    rng = random.Random(seed)
    return set(rng.sample(trainable, int(round(frac * len(trainable))))), trainable


def classify(context: str, symbol: str, is_control: bool, holdout_context: str, hidden: set,
             trained_symbols: set) -> str:
    """'train', 'C', 'T', 'J', or 'control_holdout' (controls of the held-out context: encoder input only)."""
    if context == holdout_context:
        if is_control:
            return "control_holdout"
        if symbol in hidden or symbol not in trained_symbols:
            return "J"
        return "C"
    if not is_control and symbol in hidden:
        return "T"
    return "train"


UNLABELLED = {UNASSIGNED, "MISSING", "NO_METADATA", ""}


def qc_values(x_csr, measured_mask, mt_mask):
    """Per cell, on the genes of `measured_mask` only: counts, genes detected (non-zero), mitochondrial fraction (NaN
    when no mitochondrial gene is measured)."""
    cols = np.flatnonzero(measured_mask)
    x = x_csr[:, cols] if cols.size < x_csr.shape[1] else x_csr
    lib = np.asarray(x.sum(axis=1)).ravel().astype(float)
    genes = np.asarray((x > 0).sum(axis=1)).ravel().astype(float)
    mt_cols = np.flatnonzero(mt_mask[cols])
    if mt_cols.size:
        mito = np.asarray(x[:, mt_cols].sum(axis=1)).ravel() / np.maximum(lib, 1)
    else:
        mito = np.full(lib.shape, np.nan)
    return lib, genes, mito


ABSOLUTE = "no_usable_counts"
SOFT = ("counts_far_below_controls", "counts_below_floor", "genes_below_floor", "mito_above_ceiling")


def thresholds_from_controls(lib, genes, mito, slack=0.5, far=0.2, abs_counts=10.0, abs_genes=5.0):
    """Admission thresholds of a key. Relative to its controls, all liftable by phenotype_guard: counts far below
    them (`far` x their q01), counts or genes detected below `slack` x their q01, a mitochondrial fraction above
    max(q99 / slack, q99 + 0.05). A knockdown can lower counts and raise the mitochondrial fraction (an essential gene
    silenced): these rules flag outliers, not technical failures. Absolute, never lifted: fewer than `abs_counts`
    counts or `abs_genes` genes on the model genes, a cell with no usable expression profile."""
    q_lib, q_genes = float(np.quantile(lib, 0.01)), float(np.quantile(genes, 0.01))
    t = {"lib_abs": float(abs_counts), "genes_abs": float(abs_genes), "lib_far": max(1.0, far * q_lib),
         "lib_min": max(1.0, slack * q_lib), "genes_min": max(1.0, slack * q_genes)}
    if np.isfinite(mito).any():
        q99 = float(np.nanquantile(mito, 0.99))
        t["mito_max"] = min(1.0, max(q99 / slack, q99 + 0.05))
    else:
        t["mito_max"] = None
    return t


def admit(lib, genes, mito, t):
    """Admission mask and the rule each rejected cell failed first: the absolute floor, then the relative rules."""
    reason = np.full(lib.shape, "", dtype=object)
    reason[(lib < t.get("lib_abs", 0)) | (genes < t.get("genes_abs", 0))] = ABSOLUTE
    reason[(reason == "") & (lib < t.get("lib_far", 0))] = "counts_far_below_controls"
    reason[(reason == "") & (lib < t["lib_min"])] = "counts_below_floor"
    reason[(reason == "") & (genes < t["genes_min"])] = "genes_below_floor"
    if t["mito_max"] is not None:
        reason[(reason == "") & np.isfinite(mito) & (mito > t["mito_max"])] = "mito_above_ceiling"
    return reason == "", reason


def phenotype_guard(reason, groups, is_control, keys, guarded=None, n_min=5, alpha=1e-3, min_excess=0.02,
                    floor_rate=0.005):
    """Lift the relative thresholds for perturbations they reject selectively.

    reason: the rule each cell failed ('' when admitted); groups: the perturbation of each cell; keys: its (study,
    context); guarded: the cells whose groups are guarded (default: every non-control cell; unlabelled cells are left
    out by the caller). For each key, the controls' relative-rejection rate p_c among controls above the absolute
    floor; for each guarded group of that key with at least n_min cells above the absolute floor, its relative
    rejections k of n are selective when k/n >= p0 + min_excess and P(X >= k | n, p0) < alpha, p0 = max(p_c,
    floor_rate). Relative rejections of a selective group are admitted with reason 'phenotype_guard'; the absolute
    floor stays. Returns (ok, new reasons, report rows)."""
    import pandas as pd
    from scipy.stats import binom
    reason = np.asarray(reason, dtype=object).copy()
    is_control = np.asarray(is_control, bool)
    guarded = ~is_control if guarded is None else (np.asarray(guarded, bool) & ~is_control)
    frame = pd.DataFrame({"key": np.asarray(keys, dtype=object), "group": np.asarray(groups, dtype=object),
                          "soft": np.isin(reason, SOFT), "reason": reason})
    above = reason != ABSOLUTE
    ctrl = frame[is_control & above].groupby("key")["soft"].mean()
    pert = frame[guarded & above]
    stats = pert.groupby(["key", "group"], sort=True)["soft"].agg(["size", "sum"])
    rows, lift = [], set()
    for (k, g), (n, kk) in stats.iterrows():
        n, kk = int(n), int(kk)
        if n < n_min or kk == 0:
            continue
        p_c = float(ctrl.get(k, np.nan))
        p0 = max(p_c if np.isfinite(p_c) else 0.0, floor_rate)
        p_value = float(binom.sf(kk - 1, n, p0))
        selective = kk / n >= p0 + min_excess and p_value < alpha
        if selective:
            lift.add((k, g))
        rows.append({"key": str(k), "group": str(g), "cells_above_hard_floor": n, "soft_rejections": kk,
                     "rate": kk / n, "controls_rate": p_c, "p_value": p_value, "selective": selective,
                     "readmitted": kk if selective else 0})
    if lift:
        pairs = pd.MultiIndex.from_arrays([frame["key"], frame["group"]])
        hit = pairs.isin(list(lift)) & frame["soft"].to_numpy() & guarded
        rule = Counter()
        for (k, g, r) in zip(frame["key"][hit], frame["group"][hit], frame["reason"][hit]):
            rule[(k, g, r)] += 1
        for row in rows:
            if row["selective"]:
                row["lifted_rules"] = {r: n for (k, g, r), n in rule.items() if k == row["key"] and g == row["group"]}
        reason[hit] = "phenotype_guard"
    ok = (reason == "") | (reason == "phenotype_guard")
    return ok, reason, rows


def hash64(texts) -> np.ndarray:
    """A stable 64-bit hash per string (cell keys), so millions of keys fit in one array."""
    return np.array([int.from_bytes(hashlib.blake2b(str(t).encode(), digest_size=8).digest(), "little")
                     for t in texts], dtype=np.uint64)


def fingerprints(x_csr) -> np.ndarray:
    """Per cell, a 64-bit hash of its counts on the model genes (sorted column indices and values)."""
    x_csr.sort_indices()
    ind, dat, ptr = x_csr.indices.astype(np.int32), x_csr.data.astype(np.float32), x_csr.indptr
    out = np.empty(x_csr.shape[0], dtype=np.uint64)
    for i in range(x_csr.shape[0]):
        h = hashlib.blake2b(digest_size=8)
        h.update(ind[ptr[i]:ptr[i + 1]].tobytes())
        h.update(dat[ptr[i]:ptr[i + 1]].tobytes())
        out[i] = int.from_bytes(h.digest(), "little")
    return out


def identity(key_hash, fingerprint, source) -> np.ndarray:
    """Status of every cell of the corpus, in reading order (the first sighting of a key wins), from its key
    (study|library|barcode), the fingerprint of its counts and the source file it was read from:
    'new'; 'duplicate' (a key already seen with the same counts: one cell ingested twice, admitted once);
    'collision' (a key already seen with other counts from the same source file: two cells sharing a key in that
    source, both kept); 'version' (a key already seen with other counts from another source file: another version of
    the same cell, admitted once). Counts alone never join two keys: see content_matches."""
    key_hash, fingerprint = np.asarray(key_hash, np.uint64), np.asarray(fingerprint, np.uint64)
    source = np.asarray(source)
    n = key_hash.size
    status = np.full(n, "new", dtype=object)
    _, first_pair = np.unique(np.rec.fromarrays([key_hash, fingerprint]), return_index=True)
    dup = np.ones(n, bool)
    dup[first_pair] = False
    status[dup] = "duplicate"
    _, first_key, inv = np.unique(key_hash, return_index=True, return_inverse=True)
    later = np.ones(n, bool)
    later[first_key] = False
    other = later & ~dup
    same_source = source == source[first_key[inv]]
    status[other & same_source] = "collision"
    status[other & ~same_source] = "version"
    return status


def content_matches(key_hash, fingerprint, rich, study) -> list:
    """Cells whose counts equal those of an earlier cell under another key, by pair of studies, among cells with enough
    counts (`rich`). A report for review, never a reason to drop a cell: independent cells can share projected counts
    (a small panel, a few counts) and a reprocessed republication can differ; a republication is excluded only when
    declared, for its whole dataset."""
    key_hash, fingerprint = np.asarray(key_hash, np.uint64), np.asarray(fingerprint, np.uint64)
    study = np.asarray(study, dtype=object)
    idx = np.flatnonzero(np.asarray(rich, bool))
    if idx.size == 0:
        return []
    order = np.lexsort((idx, fingerprint[idx]))
    s_idx, s_fp = idx[order], fingerprint[idx][order]
    start = np.r_[True, s_fp[1:] != s_fp[:-1]]
    first = s_idx[np.maximum.accumulate(np.where(start, np.arange(s_idx.size), 0))]
    later = ~start & (key_hash[s_idx] != key_hash[first])
    pairs = Counter(zip(study[first[later]].tolist(), study[s_idx[later]].tolist()))
    return [{"studies": [a, b], "cells": int(n)} for (a, b), n in pairs.most_common()]


def feature_columns(official_index, measured, gene_of_axis, n_genes: int):
    """Model-gene column of each native feature and the shard's gene mask. Features off the axis or not measured get
    -1. When two or more measured features land on one model gene, none is used and the gene is not measured in the
    shard: counts of different features are never summed without a declared rule (plan §4.4). Returns (cols, mask,
    collided model genes)."""
    official_index = np.asarray(official_index, np.int64)
    col = np.where(official_index >= 0, gene_of_axis[np.clip(official_index, 0, None)], -1)
    col = np.where(np.asarray(measured, bool), col, -1)
    genes, counts = np.unique(col[col >= 0], return_counts=True)
    collided = genes[counts > 1]
    if collided.size:
        col = np.where(np.isin(col, collided), -1, col)
    mask = np.zeros(n_genes, bool)
    mask[col[col >= 0]] = True
    return col, mask, collided


def key_masks(shard_masks, shard_keys) -> dict:
    """Mask of a (study, context) key: the genes measured by every shard holding cells of that key (intersection)."""
    out = {}
    for mask, keys in zip(shard_masks, shard_keys):
        for k in set(keys):
            out[k] = mask.copy() if k not in out else (out[k] & mask)
    return out


class EpochSampler:
    """Every admitted training cell once per epoch, shard by shard through a buffer; returns (shard id, row) pairs.

    shards: list of (shard id, array of admitted training rows). The buffer holds `buffer` shards; each keeps a
    shuffled queue; a batch takes cells from the non-empty queues in proportion to what they have left, so an epoch
    ends exactly when every queue is empty."""

    def __init__(self, shards, buffer: int, seed: int = 0):
        self.shards = [(sid, np.asarray(rows)) for sid, rows in shards if len(rows)]
        self.buffer, self.rng, self.epoch = buffer, np.random.default_rng(seed), 0
        self._start_epoch()

    def _start_epoch(self):
        self.order = list(self.rng.permutation(len(self.shards)))
        self.active = {}
        self.epoch += 1
        self._fill()

    def _fill(self):
        while len(self.active) < self.buffer and self.order:
            k = self.order.pop()
            sid, rows = self.shards[k]
            self.active[sid] = list(self.rng.permutation(rows))

    def loaded(self):
        return list(self.active)

    def batch(self, n):
        """n cells; the count taken from each loaded shard is multinomial in what the shards have left, so an epoch
        still ends exactly when every queue is empty. Deterministic given the seed: a resumed run replays the batches
        it already consumed without reading any count."""
        out = []
        while len(out) < n:
            if not self.active:
                if not self.order:
                    self._start_epoch()
                else:
                    self._fill()
                continue
            sids = list(self.active)
            left = np.array([len(self.active[s]) for s in sids], np.int64)
            take = np.minimum(self.rng.multinomial(min(n - len(out), int(left.sum())), left / left.sum()), left)
            for s, t in zip(sids, take):
                if t:
                    q = self.active[s]
                    out.extend((s, int(r)) for r in q[-t:])
                    del q[-t:]
                    if not q:
                        del self.active[s]
            self._fill()
        return out


def control_rows_by_key(studies, contexts, is_control, libraries):
    """{(study|context): {library: rows}} of control cells: the pools the context encoder and the baselines draw from;
    two studies of the same cell line never share one."""
    out = defaultdict(lambda: defaultdict(list))
    for r in np.flatnonzero(is_control):
        out[key_of(studies[r], contexts[r])][libraries[r]].append(int(r))
    return {k: {lib: np.asarray(v) for lib, v in libs.items()} for k, libs in out.items()}


def draw_controls(pools: dict, key: str, library: str, k: int, rng) -> np.ndarray:
    """k control rows for a cell of `key` in `library`: from its own library when it holds at least k controls,
    otherwise from every library of the same (study, context), with replacement when the key has fewer than k.
    Never from another key."""
    libs = pools[key]
    own = libs.get(library)
    source = own if own is not None and len(own) >= k else np.concatenate(list(libs.values()))
    return rng.choice(source, size=k, replace=len(source) < k)


def study_weights(admitted_by_study: dict) -> dict:
    """Loss weight per study so that each study weighs the same in expectation: N / (S * n_study)."""
    total, n = sum(admitted_by_study.values()), len(admitted_by_study)
    return {s: total / (n * v) for s, v in admitted_by_study.items() if v}


def mean_prop(x_csr_or_dense, lib, measured):
    """Mean per-cell proportion on the measured genes (dense vector over all model genes; 0 off the mask)."""
    import scipy.sparse as sp
    L = np.maximum(np.asarray(lib, float), 1.0)
    if sp.issparse(x_csr_or_dense):
        m = np.asarray(x_csr_or_dense.multiply(1.0 / L[:, None]).mean(axis=0)).ravel()
    else:
        m = (np.asarray(x_csr_or_dense) / L[:, None]).mean(axis=0)
    return np.where(measured, m, 0.0)


def shift(prop_pert, prop_ctrl, measured, eps=1e-9):
    """The one shift estimator: log mean proportion perturbed minus control, on measured genes where both are > 0."""
    ok = measured & (prop_pert > 0) & (prop_ctrl > 0)
    out = np.zeros(prop_pert.shape)
    out[ok] = np.log(prop_pert[ok] + eps) - np.log(prop_ctrl[ok] + eps)
    return out, ok


def library(x, mask) -> np.ndarray:
    """Counts of each cell on the genes of `mask`."""
    import scipy.sparse as sp
    if sp.issparse(x):
        return np.asarray(x[:, np.flatnonzero(mask)].sum(axis=1)).ravel().astype(float)
    return (np.asarray(x, float) * np.asarray(mask, bool)).sum(axis=1)


def observed_shift(x_pert, mask_pert, x_ctrl, mask_ctrl):
    """Observed shift of perturbed cells against controls on the genes both measure, every library taken on those
    genes. Returns (shift, genes where it is defined, the common mask)."""
    common = np.asarray(mask_pert, bool) & np.asarray(mask_ctrl, bool)
    s, ok = shift(mean_prop(x_pert, library(x_pert, common), common),
                  mean_prop(x_ctrl, library(x_ctrl, common), common), common)
    return s, ok, common
