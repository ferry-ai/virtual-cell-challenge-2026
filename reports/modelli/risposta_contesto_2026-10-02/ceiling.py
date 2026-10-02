"""Reproducibility of the effect-space truth: weighted cosine between two independent halves of one screen.

For a table whose cells were split in two independent halves (cells and controls), the cosine between the
two half estimates, on the cube genes with the cube's expression weights and the target's own gene
excluded, says how much of the truth is repeatable at half depth. It is a diagnostic of the bench, not a
model result: no arm is involved. Halves: HepG2 (hepg2_universe.py, this study) and VIPerturb K562 Flex
(universe_viperturb_2026-09-28_half{a,b}).

    py.cmd ceiling.py --cube <cube_r1> --hepg2 <hepg2_r2> --out <report>/ceiling_r1
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from arms import Cube, gene_weight
from common import data_root, log, now_utc, sha256, write_json
from metrics import score_table

from vcc2026.genes import official_axis


def half_rows(folder: Path, stem: str, symbols: list[str], axis_pos: np.ndarray) -> dict:
    out = {}
    want = set(symbols)
    for f in sorted(p for p in folder.glob(f'{stem}_*.npz') if re.fullmatch(rf'{re.escape(stem)}_\d+\.npz', p.name)):
        with np.load(f, allow_pickle=False) as z:
            targets = z['targets'].astype(str)
            take = [i for i, t in enumerate(targets) if t in want]
            if take:
                raw = z['raw'][take][:, axis_pos]
                for j, i in enumerate(take):
                    out[targets[i]] = raw[j]
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cube', type=Path, required=True)
    p.add_argument('--hepg2', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    cube = Cube(a.cube)
    axis_pos = pd.Index(list(official_axis().symbols)).get_indexer(cube.genes)
    coords = pd.read_csv(data_root() / 'external/annotation/gene_coordinates_gencode_v50.tsv', sep='\t')
    ens_to_sym = {str(g).split('.')[0]: s for s, g in zip(coords['symbol'], coords['gene_id']) if isinstance(g, str)}
    a.out.mkdir(parents=True)
    pairs = {'hepg2_nadig': (a.hepg2 / 'universe_hepg2_halfa', 'hepg2_halfa', a.hepg2 / 'universe_hepg2_halfb', 'hepg2_halfb'),
             'k562_viperturb': (data_root() / 'processed/universe_viperturb_2026-09-28_halfa', 'viperturb',
                                data_root() / 'processed/universe_viperturb_2026-09-28_halfb', 'viperturb')}
    summary = {}
    frames = []
    for table, (fa, sa, fb, sb) in pairs.items():
        rows = cube.rows[table]
        rows = rows[rows.usable]
        sym = dict(zip(rows.target_key, rows.target))
        keys = list(rows.target_key)
        A = half_rows(fa, sa, [sym[k] for k in keys], axis_pos)
        B = half_rows(fb, sb, [sym[k] for k in keys], axis_pos)
        keys = [k for k in keys if sym[k] in A and sym[k] in B]
        ya = np.vstack([A[sym[k]] for k in keys]).astype(np.float32)
        yb = np.vstack([B[sym[k]] for k in keys]).astype(np.float32)
        w = gene_weight(cube.basal[table])
        tpos = cube.target_gene_positions(keys, ens_to_sym)
        se = np.full_like(yb, np.nan)
        sc = score_table(ya, yb, se, w, keys, tpos, block_size=300)
        f = pd.DataFrame(dict(table=table, target_key=keys, cells=cube.cells(table, keys),
                              cos_half=sc['cos'], cos_spec_half=sc['cos_spec'], pds_half=sc['pds']))
        frames.append(f)
        summary[table] = dict(targets=len(keys),
                              cos_half_median=float(np.nanmedian(sc['cos'])),
                              cos_half_mean=float(np.nanmean(sc['cos'])),
                              cos_spec_half_median=float(np.nanmedian(sc['cos_spec'])),
                              pds_half_mean=float(np.nanmean(sc['pds'])),
                              by_cells_tercile=f.groupby(pd.qcut(f.cells, 3, duplicates='drop'), observed=True)['cos_half']
                              .median().rename(str).to_dict())
        log(f'{table}: {summary[table]}')
    out = pd.concat(frames)
    out.to_csv(a.out / 'ceiling_per_target.csv.gz', index=False, compression='gzip')
    write_json(a.out / 'ceiling.json', dict(
        written_utc=now_utc(), claim='measured: half/half reproducibility of the truth; diagnostic, no model',
        reading=('each half has about half the cells: the cosine between a full-depth truth and a perfect predictor '
                 'would be higher than these values (Spearman-Brown); they bound what effect-space indices can reach'),
        summary=summary, per_target=dict(file='ceiling_per_target.csv.gz', sha256=sha256(a.out / 'ceiling_per_target.csv.gz'))))


if __name__ == '__main__':
    main()
