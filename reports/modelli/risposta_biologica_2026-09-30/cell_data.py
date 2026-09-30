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
- admission QC: thresholds per (study, context) from its control cells only (counts on the model genes >= q01,
  genes detected >= q01, mitochondrial fraction <= q99 where MT genes are measured), fixed before training and applied
  to every cell of the key, held-out ones included; each rejection is counted by rule;
- sampling without replacement: an epoch visits every admitted training cell exactly once; balance between studies
  comes from loss weights (each study weighs the same in expectation), not from resampling;
- one estimator for every shift in the evaluation: log of the mean per-cell proportion, perturbed against controls
  of the same (study, context), on genes measured there; the same function serves observed cells, baselines and the
  model's expected proportions.
"""
from __future__ import annotations

import random
import re
from collections import Counter, defaultdict

import numpy as np

SEP = re.compile(r"[|_,;+\s]")
CONTROL, UNASSIGNED = "NTC", "UNASSIGNED"


def normalise(label: str, axis: set) -> str:
    """A label as a gene symbol when it names one; the label itself otherwise."""
    if label in axis:
        return label
    head = SEP.split(label, maxsplit=1)[0]
    return head if head in axis else label


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


def qc_values(x_csr, measured_mask, mt_mask):
    """Per cell: counts on the measured model genes, genes detected, mitochondrial fraction (NaN if no MT measured)."""
    lib = np.asarray(x_csr.sum(axis=1)).ravel()
    genes = np.diff(x_csr.indptr)
    mt_cols = np.flatnonzero(mt_mask & measured_mask)
    if mt_cols.size:
        mito = np.asarray(x_csr[:, mt_cols].sum(axis=1)).ravel() / np.maximum(lib, 1)
    else:
        mito = np.full(lib.shape, np.nan)
    return lib, genes, mito


def thresholds_from_controls(lib, genes, mito):
    t = {"lib_min": float(np.quantile(lib, 0.01)), "genes_min": float(np.quantile(genes, 0.01))}
    t["mito_max"] = float(np.nanquantile(mito, 0.99)) if np.isfinite(mito).any() else None
    t["lib_min"] = max(t["lib_min"], 1.0)
    return t


def admit(lib, genes, mito, t):
    """Admission mask and the rule each rejected cell failed first."""
    reason = np.full(lib.shape, "", dtype=object)
    reason[lib < t["lib_min"]] = "counts_below_q01_of_controls"
    reason[(reason == "") & (genes < t["genes_min"])] = "genes_below_q01_of_controls"
    if t["mito_max"] is not None:
        reason[(reason == "") & np.isfinite(mito) & (mito > t["mito_max"])] = "mito_above_q99_of_controls"
    return reason == "", reason


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
        out = []
        while len(out) < n:
            if not self.active:
                if not self.order:
                    self._start_epoch()
                else:
                    self._fill()
                continue
            sids = list(self.active)
            left = np.array([len(self.active[s]) for s in sids], float)
            s = sids[self.rng.choice(len(sids), p=left / left.sum())]
            out.append((s, int(self.active[s].pop())))
            if not self.active[s]:
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
    otherwise from every library of the same (study, context). Never from another key."""
    libs = pools[key]
    own = libs.get(library)
    source = own if own is not None and len(own) >= k else np.concatenate(list(libs.values()))
    return rng.choice(source, size=min(k, len(source)), replace=len(source) < k)


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
