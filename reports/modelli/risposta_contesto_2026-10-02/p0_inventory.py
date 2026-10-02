"""R-LEAD P0: environment, real scorer, readable inputs and the context x target x study matrix.

Reads only local files (no download, no cloud). Writes, into a new report folder:

* ``preflight.json``         git state, interpreter, libraries, the scorer's vcc2026 preset, resources;
* ``input_manifest.json``    every input file with size and sha256, checked against the chunk hashes
                             the universes recorded when they were built;
* ``tables.csv``             one row per effect table: line, group, donor, state, study, assay, modality,
                             targets, cells, controls, measured genes, availability of cells;
* ``context_target_study.csv.gz``  one row per (table, target), with the reconciled target key;
* ``overlap.json``, ``group_overlap.csv``  links between groups (same target in several lines) and
                             the confounding of line, study and assay;
* ``aliases.json``           targets whose symbol differs across tables for one Ensembl ID, and
                             symbols that resolve to different IDs.

Heavy per-gene coverage goes to the data root (``gene_coverage.npz``) with its hash in the manifest.

    py.cmd p0_inventory.py --out reports/analisi/generalizzazione_contesti_2026-10-02/p0_r1
        --hepg2 <data root>/processed/generalizzazione_contesti_2026-10-02/hepg2_r1
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

from common import (REPO, Timer, data_root, environment, git_state, h5_column, heavy_root, log, now_utc,
                    sha256, write_json)
from registry import COMPETITION_CONTROLS, NOT_LOCAL, TABLES

from vcc2026.genes import official_axis


def scorer_check() -> dict:
    out = dict(importable=False)
    try:
        import cell_eval2
        from vcc2026.de_tools import load_eval_config
        cfg = load_eval_config('vcc2026')
        out.update(importable=True, module=cell_eval2.__file__,
                   compute_metrics=hasattr(cell_eval2, 'compute_metrics'),
                   aggregate_metrics=hasattr(cell_eval2, 'aggregate_metrics'),
                   preset='vcc2026', pert_col=cfg.pert_col, control=cfg.control,
                   de=dict(backend=cfg.de.backend, p_adj_threshold=cfg.de.p_adj_threshold,
                           sort_by=cfg.de.sort_by, min_abs_log2fc=cfg.de.min_abs_log2fc))
        try:
            from cell_eval2.config import EvalConfig
            out['config_class'] = EvalConfig.__module__ + '.' + EvalConfig.__name__
        except Exception as exc:  # recorded
            out['config_class'] = f'error: {exc}'
    except Exception as exc:
        out['error'] = f'{type(exc).__name__}: {exc}'
    return out


def resources() -> dict:
    from vcc2026.resources import snapshot
    snap = snapshot(data_root()).as_dict()
    repo_disk = shutil.disk_usage(REPO)
    snap['repo_disk_free_gib'] = repo_disk.free / 1024**3
    return snap


def gtf_symbols(path: Path) -> dict:
    """GENCODE gene_name -> gene_id (unversioned), first occurrence."""
    out = {}
    pat_id, pat_name = re.compile(r'gene_id "([^"]+)"'), re.compile(r'gene_name "([^"]+)"')
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.split('\t', 8)
            if len(parts) < 9 or parts[2] != 'gene':
                continue
            gid, name = pat_id.search(parts[8]), pat_name.search(parts[8])
            if gid and name:
                out.setdefault(name.group(1), gid.group(1).split('.')[0])
    return out


def source_target_ids(root: Path, hepg2_h5ad: Path) -> dict:
    """Target symbol -> Ensembl ID as the source itself records it, per table id."""
    out = {}
    for tid, f in (('k562_gwps', 'K562_gwps_raw_bulk_01.h5ad'), ('k562_essential', 'K562_essential_raw_bulk_01.h5ad'),
                   ('rpe1', 'rpe1_raw_bulk_01.h5ad')):
        with h5py.File(root / 'external' / f, 'r') as h:
            gt = h5_column(h['obs/gene_transcript'])
        m = {}
        for s in gt:
            parts = s.split('_')
            if len(parts) >= 4 and parts[-1].startswith('ENSG'):
                m.setdefault('_'.join(parts[1:-2]), parts[-1])
        out[tid] = m
    with h5py.File(hepg2_h5ad, 'r') as h:
        gt = h5_column(h['obs/gene_transcript'])
    m = {}
    for s in set(gt):
        parts = s.split('_')
        if len(parts) >= 4 and parts[-1].startswith('ENSG'):
            m.setdefault('_'.join(parts[1:-2]), parts[-1])
    out['hepg2_nadig'] = m
    with h5py.File(root / 'external' / 'cd4_gw' / 'GWCD4i.pseudobulk_merged.h5ad', 'r') as h:
        names = h5_column(h['obs/perturbed_gene_name'])
        ids = h5_column(h['obs/perturbed_gene_id'])
    m = {}
    for n, i in zip(names, ids):
        m.setdefault(n, i)
    for tid in ('cd4_rest', 'cd4_stim8hr', 'cd4_stim48hr'):
        out[tid] = m
    return out


def table_files(root: Path, t: dict, hepg2_dir: Path | None) -> tuple[Path, list[Path]]:
    if t['id'] == 'hepg2_nadig':
        folder = hepg2_dir / 'universe_hepg2'
    else:
        folder = root / 'processed' / t['universe']
    files = sorted(p for p in folder.glob(f"{t['stem']}_*.npz") if re.fullmatch(rf"{re.escape(t['stem'])}_\d+\.npz", p.name))
    return folder, files


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--hepg2', type=Path, required=True, help='output folder of hepg2_universe.py')
    p.add_argument('--skip-hash', action='store_true', help='sizes only (debug); the delivered run hashes')
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    timer = Timer()
    root = data_root()
    axis = list(official_axis().symbols)
    G = len(axis)
    a.out.mkdir(parents=True)
    heavy = heavy_root() / f'p0_{a.out.name}'
    heavy.mkdir(parents=True, exist_ok=False)

    # 1. preflight
    pre = dict(written_utc=now_utc(), git=git_state(), environment=environment(), scorer=scorer_check(),
               resources=resources(), data_root=str(root), heavy_outputs=str(heavy),
               note='CP-0054: scorer visibility differs between sandbox and native shell; this run is native')
    write_json(a.out / 'preflight.json', pre)
    log(f"preflight: scorer importable={pre['scorer']['importable']}")

    # 2. inputs and their hashes
    hepg2_manifest = json.loads((a.hepg2 / 'manifest.json').read_text(encoding='utf-8'))
    hepg2_h5ad = Path(hepg2_manifest['input']['path'])
    inputs, mismatches = [], []
    recorded = {}
    for t in TABLES:
        folder, files = table_files(root, t, a.hepg2)
        man = folder / 'manifest.json'
        if man.exists():
            m = json.loads(man.read_text(encoding='utf-8'))
            for c in m.get('chunks', []) if isinstance(m, dict) else []:
                if isinstance(c, dict) and 'file' in c and 'sha256' in c:
                    recorded[str(folder / c['file'])] = c['sha256']
    seen = set()
    for t in TABLES:
        folder, files = table_files(root, t, a.hepg2)
        if not files:
            raise FileNotFoundError(f"no chunks for {t['id']} in {folder}")
        for f in files + [folder / 'index.csv']:
            if str(f) in seen or not f.exists():
                continue
            seen.add(str(f))
            h = None if a.skip_hash else sha256(f)
            rec = recorded.get(str(f))
            row = dict(table=t['id'], path=str(f.relative_to(root)), bytes=f.stat().st_size, sha256=h,
                       recorded_sha256=rec, matches_record=None if rec is None or h is None else rec == h)
            if row['matches_record'] is False:
                mismatches.append(row)
            inputs.append(row)
    others = [root / 'raw' / 'controls' / 'gene_names.csv', root / 'raw' / 'controls' / 'pert_counts.csv',
              root / 'external' / 'annotation' / 'gene_coordinates_gencode_v50.tsv',
              root / 'external' / 'annotation' / 'gencode.v50.basic.annotation.gtf.gz',
              root / 'external' / 'annotation' / 'string_physical_links.gz',
              root / 'processed' / 'basal_sources_2026-09-28.csv',
              root / 'processed' / 'corpus_basale_2026-09-28' / 'ours' / 'profiles.npz',
              root / 'processed' / 'corpus_basale_2026-09-28' / 'ours' / 'meta.csv',
              root / 'external' / 'vcc2025' / 'pert_counts_Test.csv',
              root / 'external' / 'vcc2025' / 'pert_counts_Training.csv',
              root / 'external' / 'vcc2025' / 'pert_counts_Validation.csv',
              a.hepg2 / 'basal_hepg2.csv', a.hepg2 / 'manifest.json']
    others += [root / 'raw' / 'controls' / f'context_{c}.h5ad' for c in COMPETITION_CONTROLS]
    for f in others:
        inputs.append(dict(table=None, path=str(f.relative_to(root)) if str(f).startswith(str(root)) else str(f),
                           bytes=f.stat().st_size, sha256=None if a.skip_hash else sha256(f)))
    inputs.append(dict(table='hepg2_nadig', path=str(hepg2_h5ad), bytes=hepg2_h5ad.stat().st_size,
                       sha256=hepg2_manifest['input']['sha256'], note='hashed by hepg2_universe.py'))
    log(f'inputs: {len(inputs)} files, {sum(r["bytes"] for r in inputs) / 1e9:.1f} GB, '
        f'{len(mismatches)} hash mismatches against recorded chunk hashes ({timer()} s)')

    # 3. target keys
    gtf = gtf_symbols(root / 'external' / 'annotation' / 'gencode.v50.basic.annotation.gtf.gz')
    coords = pd.read_csv(root / 'external' / 'annotation' / 'gene_coordinates_gencode_v50.tsv', sep='\t')
    axis_ids = {s: str(g).split('.')[0] for s, g in zip(coords['symbol'], coords['gene_id']) if isinstance(g, str)}
    src_ids = source_target_ids(root, hepg2_h5ad)
    panel = set(pd.read_csv(root / 'raw' / 'controls' / 'pert_counts.csv')['target_gene'].astype(str))
    h1 = {k: set(pd.read_csv(root / 'external' / 'vcc2025' / f'pert_counts_{k}.csv').iloc[:, 0].astype(str))
          for k in ('Training', 'Validation', 'Test')}

    def key_of(table_id: str, symbol: str) -> tuple[str, str]:
        sid = src_ids.get(table_id, {}).get(symbol)
        if sid:
            return sid.split('.')[0], 'source'
        if symbol in axis_ids:
            return axis_ids[symbol], 'axis_gencode_v50'
        if symbol in gtf:
            return gtf[symbol], 'gencode_v50_gtf'
        return f'SYM:{symbol}', 'unresolved'

    # 4. per table: targets, cells, measured genes
    rows, trows = [], []
    coverage = {}
    for t in TABLES:
        folder, files = table_files(root, t, a.hepg2)
        index = pd.read_csv(folder / 'index.csv')
        if 'chunk' in index:
            index = index[index['chunk'].isin([f.name for f in files])]
        rows_measured = np.zeros(G, np.int64)
        n_rows = 0
        per_target = {}
        meta = None
        for f in files:
            with np.load(f, allow_pickle=False) as z:
                if meta is None and 'meta' in z.files:
                    meta = json.loads(str(z['meta']))
                fin = np.isfinite(z['raw'])
                targets = z['targets'].astype(str)
                cells = z['n_cells']
            rows_measured += fin.sum(0)
            n_rows += fin.shape[0]
            for tg, n, g in zip(targets, cells, fin.sum(1)):
                per_target[tg] = (int(n), int(g))
        coverage[t['id']] = rows_measured.astype(np.int32)
        for tg, (n, g) in per_target.items():
            k, how = key_of(t['id'], tg)
            trows.append(dict(table=t['id'], line=t['line'], group=t['group'], donor=t['donor'], state=t['state'],
                              study=t['study'], assay=t['assay'], modality=t['modality'], role=t['role'],
                              target=tg, target_key=k, key_source=how, n_cells=n, genes_measured=g,
                              in_panel_ABC=tg in panel, in_h1_2025_train=tg in h1['Training'],
                              in_h1_2025_val=tg in h1['Validation'], in_h1_2025_test=tg in h1['Test']))
        cells = np.array([v[0] for v in per_target.values()])
        rows.append(dict(id=t['id'], line=t['line'], group=t['group'], donor=t['donor'], state=t['state'],
                         study=t['study'], assay=t['assay'], modality=t['modality'], role=t['role'],
                         cells_available=t['cells'], universe=str(folder.relative_to(root)) if str(folder).startswith(str(root)) else str(folder),
                         files=len(files), targets=len(per_target), targets_ge10_cells=int((cells >= 10).sum()),
                         median_cells=float(np.median(cells)) if len(cells) else None,
                         control_cells=(meta or {}).get('n_control_cells'),
                         estimator=(meta or {}).get('se_model'), min_expected=(meta or {}).get('min_expected'),
                         donors_or_pools=len((meta or {}).get('donors') or []) or None,
                         genes_any=int((rows_measured > 0).sum()),
                         genes_half=int((rows_measured >= 0.5 * n_rows).sum()),
                         genes_all=int((rows_measured == n_rows).sum()),
                         in_panel_ABC=sum(tg in panel for tg in per_target), note=t['note'],
                         evidence='; '.join(t['evidence'])))
        log(f"{t['id']}: {len(per_target)} targets, genes measured >= half rows {rows[-1]['genes_half']} ({timer()} s)")
    tables = pd.DataFrame(rows)
    tables.to_csv(a.out / 'tables.csv', index=False)
    cts = pd.DataFrame(trows)
    with gzip.open(a.out / 'context_target_study.csv.gz', 'wt', encoding='utf-8', newline='') as f:
        cts.to_csv(f, index=False)
    np.savez_compressed(heavy / 'gene_coverage.npz', genes=np.array(axis),
                        tables=np.array(list(coverage)), rows_measured=np.vstack(list(coverage.values())),
                        n_rows=np.array([int(r['targets']) for r in rows]))

    # 5. links and confounding (CRISPRi bench tables only; other modalities reported apart)
    bench = cts[(cts.role == 'bench') & (cts.n_cells >= 10)]
    by_key = bench.groupby('target_key')
    groups_per_key = by_key['group'].nunique()
    studies_per_key = by_key['study'].nunique()
    lines_per_key = by_key['line'].nunique()
    groups = sorted(bench.group.unique())
    pres = {g: set(bench.loc[bench.group == g, 'target_key']) for g in groups}
    overlap = pd.DataFrame([[len(pres[g] & pres[h]) for h in groups] for g in groups], index=groups, columns=groups)
    overlap.to_csv(a.out / 'group_overlap.csv')
    alias_pairs = (cts[cts.key_source != 'unresolved'].groupby('target_key')['target'].agg(lambda s: sorted(set(s))))
    alias_pairs = {k: v for k, v in alias_pairs.items() if len(v) > 1}
    conflicts = cts.groupby('target')['target_key'].agg(lambda s: sorted(set(s)))
    conflicts = {k: v for k, v in conflicts.items() if len(v) > 1}
    write_json(a.out / 'aliases.json', dict(
        rule='target_key = Ensembl ID recorded by the source (Replogle, Nadig, Marson obs), else the official axis '
             'GENCODE v50 table (stage 74, with HGNC aliases), else the GENCODE v50 GTF gene_name, else SYM:<symbol>',
        key_sources=cts.key_source.value_counts().to_dict(),
        one_id_several_symbols=alias_pairs, one_symbol_several_ids=conflicts))
    conf = (bench.groupby(['group', 'line', 'study', 'assay']).agg(tables=('table', 'nunique'),
                                                                     targets=('target_key', 'nunique'),
                                                                     median_cells=('n_cells', 'median'))
            .reset_index())
    conf.to_csv(a.out / 'confounding.csv', index=False)
    dist = groups_per_key.value_counts().sort_index()
    panel_keys = {key_of('panel', s)[0] for s in panel}
    write_json(a.out / 'overlap.json', dict(
        unit='CRISPRi bench tables, targets with >= 10 cells, keyed by reconciled target_key',
        groups=groups, tables_per_group=bench.groupby('group')['table'].nunique().to_dict(),
        targets_per_group={g: len(pres[g]) for g in groups},
        keys_by_number_of_groups={int(k): int(v) for k, v in dist.items()},
        keys_in_ge2_groups=int((groups_per_key >= 2).sum()), keys_in_ge3_groups=int((groups_per_key >= 3).sum()),
        keys_in_ge5_groups=int((groups_per_key >= 5).sum()), keys_in_all_groups=int((groups_per_key == len(groups)).sum()),
        keys_in_ge2_studies=int((studies_per_key >= 2).sum()), keys_in_ge2_lines=int((lines_per_key >= 2).sum()),
        panel_ABC_keys_in_ge2_groups=int(sum(groups_per_key.get(k, 0) >= 2 for k in panel_keys)),
        other_modalities=cts[cts.role != 'bench'].groupby('table')['target'].nunique().to_dict(),
        not_local=NOT_LOCAL))
    write_json(a.out / 'input_manifest.json', dict(
        written_utc=now_utc(), data_root=str(root), files=inputs, hash_mismatches=mismatches,
        heavy_outputs=[dict(path=str(heavy / 'gene_coverage.npz'), sha256=sha256(heavy / 'gene_coverage.npz'))],
        outputs={f.name: sha256(f) for f in sorted(a.out.iterdir()) if f.is_file()}, seconds=timer()))
    log(f'done in {timer()} s')


if __name__ == '__main__':
    main()
