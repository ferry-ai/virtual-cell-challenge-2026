"""R-LEAD P3, regime C: does a correction learned from the controls of a never-perturbed line beat transfer?

For every line group held out whole (all its studies, states and clones), every arm of `arms.py` is
fitted on the other groups only (`assert_no_leak` on the training rows of every arm; every table read is
logged with its purpose and the run fails if a fit read the held-out group) and scored on the held-out
tables with `metrics.score_table`, block by block (blocks of <= 300 targets, the PDS unit).
Fits and predictions are `fitting.fit_c` and `fitting.predict_c` (version 2: inner selection of M2 with
basis, transfers and PCA rebuilt without the validation group).

Arms: null, generic, transfer (t25 recipe, amplitude 1.576), tm0 (context-free gains), m1 (per-gene
gains from the held-out controls), m1_swap (another group's controls), m1_tperm (another target's
shared effect), m1_null<r> (fitted with controls permuted across training groups, the run's own null),
m2_0 / m2 / m2_swap / m2_null<r> (low-rank bilinear, hyperparameters chosen by inner leave-one-group-out).

    py.cmd p3_run.py --cube <data>/processed/generalizzazione_contesti_2026-10-02/cube_r1 --protocol PROTOCOLLO.json
        --out <data>/processed/generalizzazione_contesti_2026-10-02/p3_c_r2
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from arms import Cube, derangement, gene_weight, table_means
from common import Timer, coords_path, data_root, git_state, log, now_utc, sha256, write_json
from fitting import GMCache, fit_c, predict_c
from metrics import blocks_of, score_table
from splits import Split

VERSION = 2


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cube', type=Path, required=True)
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--groups', nargs='*', default=None, help='held-out groups (default: all)')
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    proto = json.loads(a.protocol.read_text(encoding='utf-8'))
    P = proto['parameters']
    timer = Timer()
    cube = Cube(a.cube, min_cells=P['min_cells'])
    keys_info = pd.read_csv(a.cube / 'keys.csv').set_index('target_key')
    coords = pd.read_csv(coords_path(P['gene_coordinates']), sep='\t')
    ens_to_sym = {str(gid).split('.')[0]: s for s, gid in zip(coords['symbol'], coords['gene_id']) if isinstance(gid, str)}
    a.out.mkdir(parents=True)
    log(f'cube: {len(cube.tables)} tables, {len(cube.groups)} groups, {len(cube.genes)} genes (runner v{VERSION})')
    commons, raw_means = table_means(cube, Split('C', '__none__', None, P['n_folds']))
    gm = GMCache(cube, commons, a.out / 'gm_cache')
    swap = derangement(cube.groups, 'swap')
    fits, leak_checks = {}, {}
    held_groups = a.groups or cube.groups
    for g in held_groups:
        cube.reads.clear()
        fitted = fit_c(cube, g, P, commons, raw_means, gm)
        fits[g] = dict(m1_coef=fitted['m1'].coef.tolist(), tm0_coef=fitted['tm0'].coef.tolist(),
                       m1_rows=fitted['m1'].n, m1_null_coefs=[nl.coef.tolist() for nl in fitted['nulls']],
                       m2_choice=dict(k=fitted['k'], d=fitted['d'], ridge=fitted['ridge']),
                       m2_inner={str(c): v for c, v in fitted['inner'].items()}, inner_audit=fitted['inner_audit'],
                       pca_explained=fitted['pca'].explained, fit_keys=fitted['fit_keys'], swap_group=swap[g],
                       permutations=fitted['perms'])
        log(f"{g}: fits done (m2 k={fitted['k']} d={fitted['d']} ridge={fitted['ridge']}) ({timer()} s)")
        records = []
        for e in cube.tables_of(g):
            keys = cube.keys_of(e)
            w = gene_weight(cube.basal[e])
            for blk in blocks_of(keys, P['pds_block']):
                res = predict_c(cube, fitted, e, [keys[i] for i in blk], commons, swap[g])
                if res is None:
                    continue
                bkeys = res['keys']
                truth, _ = cube.get(e, 'raw', bkeys, purpose='truth')
                se, _ = cube.get(e, 'se', bkeys, purpose='truth')
                tpos = cube.target_gene_positions(bkeys, ens_to_sym)
                cells = cube.cells(e, bkeys)
                for name, pred in res['arms'].items():
                    sc = score_table(pred, truth, se, w, bkeys, tpos, block_size=len(bkeys))
                    for i, kk in enumerate(bkeys):
                        records.append(dict(regime='C', held_group=g, table=e, target_key=kk,
                                            stratum=keys_info['stratum'].get(kk, 'other'),
                                            support=int(res['support'][i]), n_cells=float(cells[i]), arm=name,
                                            **{m: float(v[i]) for m, v in sc.items()}))
            log(f'{g}/{e}: scored ({timer()} s)')
        leaked = cube.fit_reads_of(g)
        leak_checks[g] = dict(fit_reads_of_held_group=leaked,
                              truth_reads=sorted(t for t, pp in cube.reads if pp == 'truth'))
        if leaked:
            raise AssertionError(f'{g}: a fit read the held-out tables {leaked}')
        pd.DataFrame(records).to_csv(a.out / f'per_target_C_{g}.csv.gz', index=False, compression='gzip')
        del records, fitted
    write_json(a.out / 'fits.json', fits)
    write_json(a.out / 'run.json', dict(written_utc=now_utc(), git=git_state(), runner_version=VERSION,
                                        protocol=str(a.protocol), protocol_sha256=sha256(a.protocol),
                                        cube=str(a.cube), cube_manifest_sha256=sha256(a.cube / 'manifest.json'),
                                        groups=held_groups, seconds=timer(), leak_checks=leak_checks,
                                        outputs={f.name: sha256(f) for f in sorted(a.out.glob('per_target_*.csv.gz'))}))
    log(f'done in {timer()} s')


if __name__ == '__main__':
    main()
