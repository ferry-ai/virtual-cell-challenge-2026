"""Frozen C/J/T splits by whole line groups, stable when the corpus changes (R-LEAD P1).

Two defects of the earlier splits are designed out (lead audit 1/10, §2.1 and §2.6):

* a fold is a pure function of the reconciled target key and a salt (sha256), never a draw over
  the sorted list of the targets present: adding, removing or reordering tables cannot move a
  target that was already assigned;
* the regime of an evaluated (group, target) is computed after QC, against the training rows that
  actually remain: a target whose only other observation failed QC is J for that split, not C.

A held-out unit is a **group**: a line with every study, state, donor and clone of it (registry.py).
C removes every perturbed response of the group from training. J also removes, from every table,
the rows of the targets in the held-out fold. T (diagnostic) removes only those target rows.
Controls of the held-out group are inputs at prediction time, never training rows.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

SALT = 'r-lead-2026-10-02'


def unit_hash(key: str, salt: str = SALT) -> float:
    """Uniform number in [0, 1) from sha256(salt:key): stable across corpora and platforms."""
    h = hashlib.sha256(f'{salt}:{key}'.encode('utf-8')).hexdigest()
    return int(h[:15], 16) / 16**15


def target_fold(key: str, n_folds: int, salt: str = SALT) -> int:
    if n_folds < 2:
        raise ValueError('n_folds >= 2')
    return min(int(unit_hash(key, salt + ':fold') * n_folds), n_folds - 1)


@dataclass(frozen=True)
class Split:
    regime: str                    # 'C', 'J' or 'T'
    held_group: str
    fold: int | None               # None for C
    n_folds: int
    salt: str = SALT

    @property
    def name(self) -> str:
        return f'{self.regime}:{self.held_group}' + ('' if self.fold is None else f':f{self.fold}')

    def target_held(self, key: str) -> bool:
        if self.regime == 'C':
            return False
        return target_fold(key, self.n_folds, self.salt) == self.fold

    def row_allowed(self, group: str, key: str) -> bool:
        """May a perturbed row of (group, target key) enter any fit of this split?"""
        if self.regime in ('C', 'J') and group == self.held_group:
            return False
        if self.regime in ('J', 'T') and self.target_held(key):
            return False
        return True


def make_splits(groups, regimes=('C', 'J'), n_folds: int = 5, salt: str = SALT) -> list[Split]:
    out = []
    for g in sorted(groups):
        for r in regimes:
            if r == 'C':
                out.append(Split('C', g, None, n_folds, salt))
            else:
                out.extend(Split(r, g, f, n_folds, salt) for f in range(n_folds))
    return out


def training_mask(rows: pd.DataFrame, split: Split) -> np.ndarray:
    """Boolean mask over ``rows`` (columns ``group``, ``target_key``) of rows allowed in training."""
    return np.array([split.row_allowed(g, k) for g, k in zip(rows['group'], rows['target_key'])], dtype=bool)


def assert_no_leak(train_rows: pd.DataFrame, split: Split, arm: str) -> None:
    """Raise if a training row of ``arm`` breaks ``split``: called for every arm, transfer included."""
    bad = ~training_mask(train_rows, split)
    if bad.any():
        sample = train_rows.loc[bad, ['group', 'target_key']].head(5).to_dict('records')
        raise AssertionError(f'{arm} under {split.name}: {int(bad.sum())} forbidden training rows, e.g. {sample}')


@dataclass
class EvalSet:
    split: Split
    rows: pd.DataFrame                       # evaluated rows with their post-QC regime
    lost: pd.DataFrame = field(default_factory=pd.DataFrame)


def evaluation_rows(all_rows: pd.DataFrame, split: Split, *, min_cells: float = 10) -> EvalSet:
    """Rows of the held-out group to score, with the regime they have after QC.

    ``all_rows`` has one row per (table, target) with ``group``, ``table``, ``target_key``,
    ``n_cells`` and ``qc_ok`` (the table-level QC verdict). For C a target is evaluated only if a
    QC-passing training row of the same key exists in another group (``support`` = number of such
    groups); otherwise it is reported as lost (C without support is J in fact, and is scored in J).
    For J and T only targets in the held-out fold are evaluated. Lost rows are listed, never
    reassigned to another fold.
    """
    ok = pd.Series(all_rows['qc_ok'].to_numpy(bool) & (all_rows['n_cells'].to_numpy(float) >= min_cells),
                   index=all_rows.index)
    train = all_rows[ok.to_numpy() & training_mask(all_rows, split)]
    held = all_rows[all_rows['group'] == split.held_group]
    if split.regime in ('J', 'T'):
        held = held[[split.target_held(k) for k in held['target_key']]]
    support = train.groupby('target_key')['group'].nunique()
    held = held.assign(support=held['target_key'].map(support).fillna(0).astype(int),
                       held_qc=ok.loc[held.index].to_numpy(bool))
    if split.regime == 'C':
        keep = held['held_qc'] & (held['support'] > 0)
        reason = np.where(~held['held_qc'], 'qc_or_cells', 'no_training_support_after_qc')
    elif split.regime == 'J':
        if (held['support'] > 0).any():
            raise AssertionError(f'{split.name}: a held-out J target still has training rows')
        keep = held['held_qc']
        reason = np.where(~held['held_qc'], 'qc_or_cells', '')
    else:
        keep = held['held_qc']
        reason = np.where(~held['held_qc'], 'qc_or_cells', '')
    lost = held[~keep].assign(reason=np.asarray(reason)[~keep.to_numpy()])
    return EvalSet(split, held[keep].assign(regime=split.regime), lost)
