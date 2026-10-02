"""Build the HepG2 (Nadig) effect universe from the local cells, with the live t25 estimator.

The other universes were built from per-source sums by `vcc2026.multisource.effects_from_pseudobulk`
(quasi-Poisson SE, z-shrinkage, ``min_expected`` 1: the estimator correction kept since t25).
HepG2 had no such table: its cells are read here once, in row blocks, into per-target sums,
and passed to the same function. All cells of a target form one pool against all controls
(median about 50 cells per target is too few for several pools of at least ``min_cells``).

Two independent halves (cells AND controls split by one fixed random draw) give a
reproducibility reference for the effect-space truth; they never enter a fit.

Native genes go onto the official axis by exact symbol, then by Ensembl ID (GENCODE v50 table of
stage 74) for the native genes whose symbol is not on the axis; an axis position is never filled
twice. Unmapped native genes are counted, not summed anywhere.

    py.cmd hepg2_universe.py --out <data root>/processed/generalizzazione_contesti_2026-10-02/hepg2_r1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

from common import Timer, data_root, h5_column, log, now_utc, sha256, write_json

from vcc2026.genes import official_axis
from vcc2026.multisource import effects_from_pseudobulk

CONTROL = 'non-targeting'
CHUNK = 600


def axis_positions(native_symbols, native_ensembl, axis_symbols, axis_table: pd.DataFrame) -> tuple[np.ndarray, dict]:
    """Native gene -> official axis column (-1 if none): exact symbol first, then Ensembl ID."""
    axis_index = {s: i for i, s in enumerate(axis_symbols)}
    pos = np.array([axis_index.get(s, -1) for s in native_symbols], dtype=np.int64)
    taken = set(pos[pos >= 0].tolist())
    ens_to_axis = {}
    for sym, gid in zip(axis_table['symbol'], axis_table['gene_id']):
        if isinstance(gid, str) and sym in axis_index:
            ens_to_axis.setdefault(gid.split('.')[0], axis_index[sym])
    via_ensembl = 0
    for i in np.flatnonzero(pos < 0):
        j = ens_to_axis.get(str(native_ensembl[i]).split('.')[0], -1)
        if j >= 0 and j not in taken:
            pos[i] = j
            taken.add(j)
            via_ensembl += 1
    stats = dict(native=len(native_symbols), by_symbol=int((pos >= 0).sum()) - via_ensembl,
                 by_ensembl=via_ensembl, unmapped=int((pos < 0).sum()))
    return pos, stats


def block_sums(x: np.ndarray, codes: np.ndarray, n_groups: int, out: np.ndarray) -> None:
    """out[g] += sum of rows of x with code g (codes < 0 skipped), by sorted reduceat."""
    keep = codes >= 0
    if not keep.any():
        return
    c = codes[keep]
    xs = x[keep]
    order = np.argsort(c, kind='stable')
    c, xs = c[order], xs[order]
    starts = np.flatnonzero(np.r_[True, c[1:] != c[:-1]])
    out[c[starts]] += np.add.reduceat(xs, starts, axis=0)


def write_universe(folder: Path, stem: str, eff, pos: np.ndarray, n_axis: int, meta: dict) -> dict:
    folder.mkdir(parents=True, exist_ok=False)
    targets = list(eff.targets)
    rows = []
    chunks = []
    for c0 in range(0, len(targets), CHUNK):
        sl = slice(c0, c0 + CHUNK)
        arrays = {}
        for key in ('shrunk', 'raw', 'se'):
            a = np.full((len(targets[sl]), n_axis), np.nan, np.float32)
            a[:, pos[pos >= 0]] = getattr(eff, key)[sl][:, pos >= 0]
            arrays[key] = a
        name = f'{stem}_{c0 // CHUNK:02d}.npz'
        np.savez_compressed(folder / name, targets=np.array(targets[sl]), n_cells=np.asarray(eff.n_cells[sl]),
                            meta=np.array(json.dumps(meta)), **arrays)
        chunks.append(dict(file=name, targets=len(targets[sl]), sha256=sha256(folder / name)))
        rows += [dict(target=t, chunk=name, n_cells=int(n)) for t, n in zip(targets[sl], eff.n_cells[sl])]
    pd.DataFrame(rows).to_csv(folder / 'index.csv', index=False)
    return dict(folder=str(folder), chunks=chunks, targets=len(targets))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--h5ad', type=Path, default=None)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seed', type=int, default=20261002, help='draw of the two independent halves')
    p.add_argument('--block', type=int, default=569 * 2)
    p.add_argument('--min-cells', type=float, default=10.0)
    p.add_argument('--min-expected', type=float, default=1.0)
    a = p.parse_args()
    timer = Timer()
    root = data_root()
    h5ad = a.h5ad or root / 'raw' / 'nadig_hepg2' / 'NadigOConner2024_hepg2.h5ad'
    if a.out.exists():
        raise FileExistsError(a.out)
    axis = list(official_axis().symbols)
    coords = pd.read_csv(root / 'external' / 'annotation' / 'gene_coordinates_gencode_v50.tsv', sep='\t')
    log(f'hashing {h5ad.name}')
    in_hash = sha256(h5ad)
    with h5py.File(h5ad, 'r') as f:
        labels = h5_column(f['obs/gene'])
        batch = np.asarray(f['obs/batch'][:])
        nperts = np.asarray(f['obs/nperts'][:])
        genes = h5_column(f['var/gene_name'])
        ens = h5_column(f['var/ensembl_id'])
        X = f['X']
        n_cells, n_genes = X.shape
        if CONTROL not in set(labels):
            raise ValueError(f'no {CONTROL!r} cells in obs/gene')
        targets = sorted(set(labels) - {CONTROL})
        code = {t: i + 1 for i, t in enumerate(targets)}
        code[CONTROL] = 0
        cell_code = np.array([code[t] for t in labels], dtype=np.int64)
        # one perturbation per perturbed cell, none per control (nperts is 0 for every control)
        cell_code[(cell_code > 0) & (nperts != 1)] = -1
        cell_code[(cell_code == 0) & (nperts != 0)] = -1
        half = np.random.default_rng(a.seed).integers(0, 2, n_cells)
        n_groups = len(targets) + 1
        full = np.zeros((n_groups, n_genes), np.float64)
        halves = np.zeros((2 * n_groups, n_genes), np.float32)   # integer sums far below 2**24
        counts_full = np.bincount(cell_code[cell_code >= 0], minlength=n_groups)
        hc = np.where(cell_code >= 0, cell_code * 2 + half, -1)
        counts_half = np.bincount(hc[hc >= 0], minlength=2 * n_groups)
        integral = True
        for s in range(0, n_cells, a.block):
            e = min(s + a.block, n_cells)
            x = np.asarray(X[s:e], dtype=np.float32)
            integral = integral and bool(np.equal(x, np.floor(x)).all())
            block_sums(x, cell_code[s:e], n_groups, full)
            block_sums(x, hc[s:e], 2 * n_groups, halves)
            if (s // a.block) % 8 == 0:
                log(f'rows {e}/{n_cells} ({timer()} s)')
    pos, mapping = axis_positions(list(genes), list(ens), axis, coords)
    log(f'axis mapping {mapping}')
    out = a.out
    out.mkdir(parents=True)
    results = {}
    basal = {}
    for name, sums, cnt, offset in (('hepg2', full, counts_full, None), ('hepg2_halfa', halves, counts_half, 0),
                                    ('hepg2_halfb', halves, counts_half, 1)):
        if offset is None:
            rows = sums
            ncell = cnt
        else:
            rows = sums[offset::2]
            ncell = cnt[offset::2]
        obs = pd.DataFrame({'target': [CONTROL] + targets, 'donor': 'pool0', 'condition': 'all',
                            'n_cells': ncell.astype(float)})
        keep = ncell > 0
        eff = effects_from_pseudobulk(rows[keep], obs[keep], genes, targets=[t for t, k in zip(targets, keep[1:]) if k],
                                      min_cells=a.min_cells, min_expected=a.min_expected)
        meta = dict(eff.meta, source=str(h5ad), source_sha256=in_hash, estimator=(
            'vcc2026.multisource.effects_from_pseudobulk, one pool of all cells (hepg2_universe.py)'),
            min_cells=a.min_cells, half=None if offset is None else 'AB'[offset], half_seed=a.seed)
        results[name] = write_universe(out / f'universe_{name}', name, eff, pos, len(axis), meta)
        ctrl = rows[0]
        cpm = np.full(len(axis), np.nan)
        cpm[pos[pos >= 0]] = (ctrl / ctrl.sum() * 1e6)[pos >= 0]
        basal[name] = cpm
        log(f'{name}: {len(eff.targets)} targets with >= {a.min_cells:g} cells, controls {int(ncell[0])}')
    pd.DataFrame({'gene_name': axis, **basal}).to_csv(out / 'basal_hepg2.csv', index=False)
    write_json(out / 'manifest.json', dict(
        written_utc=now_utc(), script='reports/modelli/risposta_contesto_2026-10-02/hepg2_universe.py',
        input=dict(path=str(h5ad), sha256=in_hash, shape=[int(n_cells), int(n_genes)], all_values_integral=integral),
        parameters=vars(a) | {'h5ad': str(h5ad), 'out': str(out)}, axis_mapping=mapping,
        cells=dict(controls=int(counts_full[0]), perturbed=int(counts_full[1:].sum()),
                   multi_or_unassigned=int((cell_code < 0).sum()), targets_any_cell=len(targets),
                   median_cells_per_target=float(np.median(counts_full[1:]))),
        universes=results, basal=dict(file='basal_hepg2.csv', sha256=sha256(out / 'basal_hepg2.csv'),
                                      unit='CPM of the control sums over the 9,624 native genes'),
        seconds=timer()))
    log(f'done in {timer()} s')


if __name__ == '__main__':
    main()
