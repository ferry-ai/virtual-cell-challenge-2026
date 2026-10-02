"""The bench cube: linked targets x shared genes, one block per effect table, plus control descriptors.

Selection rules (fixed here, recorded in the cube manifest; none looks at an outcome):

* tables: the registry's ``role == 'bench'`` (CRISPRi, standard controls);
* target keys, among keys present with >= ``min_cells`` cells in >= 2 line groups, in three strata:
  ``essential`` every key of the two essential-gene screens (HepG2, RPE1); ``panel`` every key of the
  A/B/C validation panel; ``genome`` the other keys whose ``unit_hash(key, 'cube')`` < ``q`` (a stable
  random share of the genome-scale targets, the kind the competition panels contain);
* genes G: official-axis genes measured in at least half of the rows of some table of at least
  ``min_gene_groups`` groups (P0 coverage);
* per table and selected key: raw, SE and shrunk ln fold changes on G (NaN = unmeasured) and cells;
* per table: the control profile on G as log1p CPM, from the same controls the effects were
  estimated against when such a profile exists (basal tables and the basal corpus); its source is
  recorded per table.

Arrays are float32 ``.npy`` files in the data root (memory-mapped by the runner).

    py.cmd cube.py --p0 <report>/p0_r1 --hepg2 <data>/.../hepg2_r2 --out <data>/.../cube_r1
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from common import Timer, data_root, log, now_utc, sha256, write_json
from registry import TABLES
from splits import unit_hash

from vcc2026.genes import official_axis

BASAL_COLUMN = {'k562_gwps': 'k562', 'k562_essential': 'k562ess', 'k562_viperturb': 'viperturb', 'rpe1': 'rpe1',
                'cd4_rest': 'cd4_Rest', 'cd4_stim8hr': 'cd4_Stim8hr', 'cd4_stim48hr': 'cd4_Stim48hr',
                'hct116': 'orion_hct116', 'hek293t': 'orion_hek293t', 'kolf21j': 'kolf'}
COMPETITION = ['A', 'B', 'C']


def table_chunks(root: Path, t: dict, hepg2: Path) -> list[Path]:
    folder = hepg2 / 'universe_hepg2' if t['id'] == 'hepg2_nadig' else root / 'processed' / t['universe']
    return sorted(p for p in folder.glob(f"{t['stem']}_*.npz") if re.fullmatch(rf"{re.escape(t['stem'])}_\d+\.npz", p.name))


def basal_profiles(root: Path, hepg2: Path, tables: list[dict], genes: list[str]) -> tuple[dict, dict]:
    """log1p CPM on ``genes`` per table (NaN where the profile lacks the gene) and its provenance."""
    src = pd.read_csv(root / 'processed' / 'basal_sources_2026-09-28.csv').set_index('gene_name')
    hep = pd.read_csv(hepg2 / 'basal_hepg2.csv').set_index('gene_name')
    corpus = root / 'processed' / 'corpus_basale_2026-09-28' / 'ours'
    meta = pd.read_csv(corpus / 'meta.csv')
    with np.load(corpus / 'profiles.npz', allow_pickle=False) as z:
        counts, library = z['counts'], z['library']
    axis = list(official_axis().symbols)
    pos = pd.Index(axis).get_indexer(genes)
    out, prov = {}, {}
    for t in tables:
        tid = t['id']
        if tid in BASAL_COLUMN:
            v = src.reindex(genes)[BASAL_COLUMN[tid]].to_numpy(float)
            prov[tid] = f"processed/basal_sources_2026-09-28.csv:{BASAL_COLUMN[tid]}"
        elif tid == 'hepg2_nadig':
            v = hep.reindex(genes)['hepg2'].to_numpy(float)
            prov[tid] = 'hepg2_universe basal_hepg2.csv:hepg2 (control sums, this study)'
        elif t['universe'].startswith('generalizzazione_contesti_2026-10-02/newlines_'):
            folder = root / 'processed' / Path(t['universe']).parent
            frame = pd.read_csv(folder / f"basal_{t['stem']}.csv").set_index('gene_name')
            v = frame.reindex(genes)[t['stem']].to_numpy(float)
            prov[tid] = f"{Path(t['universe']).parent}/basal_{t['stem']}.csv (control sums, Kaggle kernel rlab-lead-sums-r1)"
        elif tid.startswith('hipsci_'):
            ctx = tid
            rows = np.flatnonzero(meta['context'].to_numpy() == ctx)
            if not len(rows):
                raise KeyError(f'no basal profiles for {ctx}')
            c = counts[rows][:, pos]
            lib = library[rows].sum()
            v = np.where(np.isnan(c).all(0), np.nan, np.nansum(c, 0)) / lib * 1e6
            prov[tid] = f'processed/corpus_basale_2026-09-28/ours: {len(rows)} control pools of {ctx}'
        else:
            raise KeyError(tid)
        out[tid] = np.log1p(v).astype(np.float32)
    for c in COMPETITION:
        out[f'competition_{c}'] = np.log1p(src.reindex(genes)[c].to_numpy(float)).astype(np.float32)
        prov[f'competition_{c}'] = f'processed/basal_sources_2026-09-28.csv:{c} (official controls; input only)'
    return out, prov


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--p0', type=Path, required=True)
    p.add_argument('--hepg2', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--min-cells', type=float, default=10)
    p.add_argument('--q', type=float, default=0.10, help='stable share of the genome-scale keys')
    p.add_argument('--min-gene-groups', type=int, default=4)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    timer = Timer()
    root = data_root()
    axis = list(official_axis().symbols)
    with gzip.open(a.p0 / 'context_target_study.csv.gz', 'rt', encoding='utf-8') as f:
        cts = pd.read_csv(f, low_memory=False)
    bench_tables = [t for t in TABLES if t['role'] == 'bench']
    ids = [t['id'] for t in bench_tables]
    b = cts[cts.table.isin(ids) & (cts.n_cells >= a.min_cells)]
    groups_per_key = b.groupby('target_key')['group'].nunique()
    eligible = groups_per_key[groups_per_key >= 2]
    essential = set(b[b.group.isin(['HepG2', 'RPE1'])].target_key)
    panel = set(b[b.in_panel_ABC.astype(bool)].target_key)
    stratum = {}
    for k in eligible.index:
        if k in essential:
            stratum[k] = 'essential'
        elif k in panel:
            stratum[k] = 'panel'
        elif unit_hash(k, 'cube') < a.q:
            stratum[k] = 'genome'
    keys = sorted(stratum)
    cov = np.load(a.p0.parent / 'gene_coverage.npz') if (a.p0.parent / 'gene_coverage.npz').exists() else None
    if cov is None:
        heavy = Path(json.loads((a.p0 / 'input_manifest.json').read_text(encoding='utf-8'))['heavy_outputs'][0]['path'])
        cov = np.load(heavy)
    cov_tables = list(cov['tables'].astype(str))
    frac = cov['rows_measured'] / np.maximum(cov['n_rows'][:, None], 1)
    measured_in_group = {}
    for t in bench_tables:
        m = frac[cov_tables.index(t['id'])] >= 0.5
        measured_in_group[t['group']] = measured_in_group.get(t['group'], np.zeros(len(axis), bool)) | m
    n_groups_measuring = np.sum(list(measured_in_group.values()), axis=0)
    gmask = n_groups_measuring >= a.min_gene_groups
    genes = [g for g, k in zip(axis, gmask) if k]
    gpos = np.flatnonzero(gmask)
    log(f'cube: {len(keys)} keys ({int((eligible >= 3).sum())} in >= 3 groups), {len(genes)} genes')
    a.out.mkdir(parents=True)
    key_set = set(keys)
    blocks = {}
    for t in bench_tables:
        sub = b[(b.table == t['id']) & b.target_key.isin(key_set)]
        sym_to_key = dict(zip(sub.target, sub.target_key))
        folder = a.out / t['id']
        folder.mkdir()
        n = len(sym_to_key)
        mm = {k: np.lib.format.open_memmap(folder / f'{k}.npy', mode='w+', dtype=np.float16, shape=(n, len(genes)))
              for k in ('raw', 'se', 'shrunk')}
        tkeys, tsyms, tcells = [], [], []
        i = 0
        for f in table_chunks(root, t, a.hepg2):
            with np.load(f, allow_pickle=False) as z:
                targets = z['targets'].astype(str)
                take = [j for j, s in enumerate(targets) if s in sym_to_key]
                if not take:
                    continue
                for k in mm:
                    mm[k][i:i + len(take)] = z[k][take][:, gpos]
                tkeys += [sym_to_key[targets[j]] for j in take]
                tsyms += [targets[j] for j in take]
                tcells += [int(z['n_cells'][j]) for j in take]
                i += len(take)
        if i != n:
            raise ValueError(f"{t['id']}: {i} rows written, {n} expected")
        for k in mm:
            mm[k].flush()
        del mm
        # two symbols of one key in one table: both rows stay on disk, the one with fewer cells is flagged
        frame = pd.DataFrame(dict(target_key=tkeys, target=tsyms, n_cells=tcells))
        best = frame.reset_index().sort_values('n_cells', ascending=False).drop_duplicates('target_key')['index']
        frame['duplicate_of_key'] = ~frame.index.isin(best)
        frame.to_csv(folder / 'rows.csv', index=False)
        blocks[t['id']] = dict(rows=int(n), group=t['group'], line=t['line'], study=t['study'],
                               assay=t['assay'], state=t['state'], donor=t['donor'],
                               duplicate_symbol_rows=int(frame['duplicate_of_key'].sum()))
        log(f"{t['id']}: {n} rows ({timer()} s)")
    basal, prov = basal_profiles(root, a.hepg2, bench_tables, genes)
    np.savez(a.out / 'basal.npz', **basal)
    pd.Series(genes, name='gene').to_csv(a.out / 'genes.csv', index=False)
    pd.DataFrame(dict(target_key=keys, stratum=[stratum[k] for k in keys],
                      groups=[int(eligible[k]) for k in keys])).to_csv(a.out / 'keys.csv', index=False)
    files = {str(p.relative_to(a.out)): sha256(p) for p in sorted(a.out.rglob('*')) if p.is_file()}
    write_json(a.out / 'manifest.json', dict(
        written_utc=now_utc(), script='reports/modelli/risposta_contesto_2026-10-02/cube.py',
        parameters=dict(min_cells=a.min_cells, q=a.q, min_gene_groups=a.min_gene_groups,
                        p0=str(a.p0), hepg2=str(a.hepg2), storage='float16 .npy (read as float32)'),
        selection=dict(eligible_keys=int(len(eligible)), keys=len(keys),
                       strata=pd.Series(stratum).value_counts().to_dict(), genes=len(genes),
                       groups=sorted(measured_in_group), rule=__doc__.split('Selection rules')[1].split('Arrays')[0]),
        tables=blocks, basal_provenance=prov, files=files, seconds=timer()))
    log(f'done in {timer()} s')


if __name__ == '__main__':
    main()
