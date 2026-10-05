"""Vendored C/J split rule. Groups come from registry.py TABLES, not from one bank."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

SALT = 'r-lead-2026-10-02'
N_FOLDS = 5
REGIMES = ('C', 'J')
# Sorted unique `group` values of reports/modelli/risposta_contesto_2026-10-02/registry.py TABLES.
LINE_GROUPS = (
    'A549', 'CD4T', 'H1', 'HCT116', 'HEK293T', 'HepG2', 'Hs27', 'Jurkat', 'K562', 'Neuron', 'RPE1', 'iPSC',
)
PROVENANCE = (
    'reports/modelli/risposta_contesto_2026-10-02/splits.py unit_hash, target_fold, '
    'Split.row_allowed, make_splits; groups are the sorted unique group field of registry.py TABLES'
)


def unit_hash(key: str, salt: str = SALT) -> float:
    digest = hashlib.sha256(f'{salt}:{key}'.encode('utf-8')).hexdigest()
    return int(digest[:15], 16) / 16 ** 15


def target_fold(key: str, n_folds: int = N_FOLDS, salt: str = SALT) -> int:
    if n_folds < 2:
        raise ValueError('n_folds >= 2')
    return min(int(unit_hash(key, salt + ':fold') * n_folds), n_folds - 1)


@dataclass(frozen=True)
class Split:
    regime: str
    held_group: str
    fold: int | None
    n_folds: int = N_FOLDS
    salt: str = SALT

    @property
    def name(self) -> str:
        return f'{self.regime}:{self.held_group}' + ('' if self.fold is None else f':f{self.fold}')

    def target_held(self, key: str) -> bool:
        if self.regime == 'C':
            return False
        return target_fold(key, self.n_folds, self.salt) == self.fold

    def row_allowed(self, group: str, key: str) -> bool:
        if self.regime in ('C', 'J') and group == self.held_group:
            return False
        if self.regime in ('J', 'T') and self.target_held(key):
            return False
        return True


def make_splits(groups=LINE_GROUPS, regimes=REGIMES, n_folds: int = N_FOLDS, salt: str = SALT) -> list[Split]:
    out = []
    for group in sorted(groups):
        for regime in regimes:
            if regime == 'C':
                out.append(Split(regime, group, None, n_folds, salt))
            else:
                out.extend(Split(regime, group, fold, n_folds, salt) for fold in range(n_folds))
    return out


def frozen_splits() -> list[Split]:
    return make_splits()
