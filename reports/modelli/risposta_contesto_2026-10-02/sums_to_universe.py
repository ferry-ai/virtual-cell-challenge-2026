"""Effect universes from the count sums written by the Kaggle kernel `kaggle_sums/kaggle_sums.py`.

Same estimator as every other universe of the bench (`vcc2026.multisource.effects_from_pseudobulk`, quasi-Poisson
SE, z-shrinkage, ``min_expected`` 1), one pool of all cells against all controls as for HepG2, on the official-axis
genes the study measures (the others stay NaN, unmeasured). Writes, per study, ``universe_<study>`` (all cells),
``universe_<study>_halfa`` and ``_halfb`` (independent halves of cells and controls), and ``basal_<study>.csv``
(control CPM on the axis genes the study measures).

    py.cmd sums_to_universe.py --sums <downloaded kernel output> --out <data root>/processed/generalizzazione_contesti_2026-10-02/newlines_r1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import Timer, log, now_utc, sha256, write_json
from hepg2_universe import write_universe

from vcc2026.genes import official_axis
from vcc2026.multisource import effects_from_pseudobulk

CONTROL = 'non-targeting'


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--sums', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--min-cells', type=float, default=10.0)
    p.add_argument('--min-expected', type=float, default=1.0)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    timer = Timer()
    axis = np.array(official_axis().symbols)
    kernel_manifest = json.loads((a.sums / 'sums_manifest.json').read_text(encoding='utf-8'))
    a.out.mkdir(parents=True)
    report = {}
    for f in sorted(a.sums.glob('*_sums.npz')):
        study = f.name[:-len('_sums.npz')]
        z = np.load(f, allow_pickle=False)
        targets = list(z['targets'].astype(str))
        measured = z['measured'].astype(bool)
        genes = axis[measured]
        pos = np.flatnonzero(measured)
        basal = {}
        uni = {}
        for name, key, ckey, nkey, cidx in (('', 'sums', 'ctrl', 'n', 0), ('_halfa', 'sums_a', 'ctrl_a', 'n_a', 1),
                                            ('_halfb', 'sums_b', 'ctrl_b', 'n_b', 2)):
            rows = np.vstack([z[ckey][None, measured], z[key][:, measured]]).astype(np.float64)
            ncell = np.concatenate([[z['ctrl_n'][cidx]], z[nkey]]).astype(float)
            keep = ncell > 0
            obs = pd.DataFrame({'target': [CONTROL] + targets, 'donor': 'pool0', 'condition': 'all', 'n_cells': ncell})
            kept_targets = [t for t, k in zip(targets, keep[1:]) if k]
            eff = effects_from_pseudobulk(rows[keep], obs[keep], genes, targets=kept_targets,
                                          min_cells=a.min_cells, min_expected=a.min_expected)
            meta = dict(eff.meta, source=f'kaggle davidmaisterx/rlab-lead-sums-r1: {f.name}', source_sha256=sha256(f),
                        estimator='vcc2026.multisource.effects_from_pseudobulk, one pool of all cells (sums_to_universe.py)',
                        min_cells=a.min_cells, half={'': None, '_halfa': 'A', '_halfb': 'B'}[name])
            stem = f'{study}{name}'
            uni[stem] = write_universe(a.out / f'universe_{stem}', stem, eff, pos_map(pos, len(genes)), len(axis), meta)
            ctrl = z[ckey].astype(float)
            cpm = np.full(len(axis), np.nan)
            cpm[pos] = ctrl[measured] / max(ctrl[measured].sum(), 1.0) * 1e6
            basal[stem] = cpm
            log(f'{stem}: {len(eff.targets)} targets with >= {a.min_cells:g} cells, controls {int(ncell[0])}')
        pd.DataFrame({'gene_name': axis, **basal}).to_csv(a.out / f'basal_{study}.csv', index=False)
        report[study] = dict(universes=uni, kernel=kernel_manifest.get(study, {}),
                             basal=dict(file=f'basal_{study}.csv', sha256=sha256(a.out / f'basal_{study}.csv'),
                                        unit='CPM of the control sums over the axis genes the study measures'))
    write_json(a.out / 'manifest.json', dict(written_utc=now_utc(), script='reports/modelli/risposta_contesto_2026-10-02/sums_to_universe.py',
                                             sums=str(a.sums), parameters=vars(a) | {'sums': str(a.sums), 'out': str(a.out)},
                                             studies=report, seconds=timer()))
    log(f'done in {timer()} s')


def pos_map(pos: np.ndarray, n: int) -> np.ndarray:
    """write_universe maps native gene i to axis column pos[i]; here the native genes ARE the measured axis genes."""
    if len(pos) != n:
        raise ValueError('measured genes and positions disagree')
    return pos


if __name__ == '__main__':
    main()
