"""Bounded adaptation of the retained pilot; extraction only, never a scientific fit.

The historical target parser is extracted by AST after its SHA has been checked.
QC equations match pilot_channel.py; tests compare bounded and dense references.
All source paths and identities stay in the private manifest, not public reports.
"""
from __future__ import annotations
import argparse
import ast
import csv
import gc
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp
from vcc2026.resources import peak_rss_bytes


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def memory_check(limit_mib=700):
    used = peak_rss_bytes()
    if used is None:
        raise RuntimeError('Cannot enforce RSS budget on this platform')
    if used > limit_mib * 2**20:
        raise MemoryError(f'RSS limit exceeded: {used} bytes')
    return used


def matrix_header(path):
    with gzip.open(path, 'rt') as stream:
        first = next(stream)
        if not first.startswith('%%MatrixMarket matrix coordinate'):
            raise ValueError('Only coordinate Matrix Market input is supported')
        lines = 1
        for line in stream:
            lines += 1
            if not line.startswith('%'):
                return (*map(int, line.split()), lines)
    raise ValueError('Missing dimensions')


def triples(path, chunk_size=100_000, memory_mib=700):
    nf, nb, nnz, skip = matrix_header(path)
    count = 0
    for chunk in pd.read_csv(path, compression='gzip', sep=r'\s+', skiprows=skip,
                             names=['f', 'b', 'v'], header=None, chunksize=chunk_size,
                             dtype={'f': np.int32, 'b': np.int32, 'v': np.float32}):
        f = chunk.f.to_numpy() - 1
        b = chunk.b.to_numpy() - 1
        v = chunk.v.to_numpy()
        if np.any(f < 0) or np.any(f >= nf) or np.any(b < 0) or np.any(b >= nb):
            raise ValueError('Matrix coordinate outside declared dimensions')
        if not np.all(np.isfinite(v)) or np.any(v < 0) or np.any(v != np.floor(v)):
            raise ValueError('Expected nonnegative finite integer raw counts')
        count += len(chunk)
        memory_check(memory_mib)
        yield f, b, v
    if count != nnz:
        raise ValueError('Matrix entries disagree with declared nnz')


def features(path):
    with gzip.open(path, 'rt') as stream:
        return [row[1] for row in csv.reader(stream, delimiter='\t')]


def load_historical_parser(path, expected_sha):
    if digest(path) != expected_sha:
        raise ValueError('Historical parser SHA changed')
    parsed = ast.parse(Path(path).read_text(encoding='utf-8'))
    nodes = [n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name == 'target_of']
    if len(nodes) != 1:
        raise ValueError('Historical parser must have exactly one target_of')
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<verified-historical-parser>', 'exec'), namespace)
    return namespace['target_of']


def umi_cells(totals, expected=36600):
    if not len(totals) or np.any(totals < 0) or expected < 1:
        raise ValueError('Invalid barcode totals or expected cell count')
    top = np.partition(totals, max(0, len(totals) - expected))[-expected:]
    threshold = 0.1 * np.quantile(top, 0.99)
    if threshold <= 0:
        raise ValueError('No positive QC threshold')
    return np.flatnonzero(totals >= threshold), float(threshold)


def select_labels(labels, names):
    sums = labels.sum(axis=1)
    maximum = labels.max(axis=1)
    keep = (maximum >= 5) & (maximum >= .8 * np.maximum(sums, 1))
    labels_text = np.asarray(names, dtype=str)[labels.argmax(axis=1)]
    condition = np.where(np.char.startswith(labels_text, 'untreated'), 0, 1).astype(np.uint8)
    return keep, condition


def guide_threshold(guides):
    medians = {t: float(np.median(np.asarray((guides >= t).sum(axis=1)).ravel()))
               for t in (1, 2, 3, 4, 5, 6, 8, 10)}
    best = min(medians, key=lambda t: abs(medians[t] - 13))
    return best, medians


def sparse_selected(path, cell_map, n_cells, n_features, chunk_size, memory_mib):
    parts = []
    for f, b, v in triples(path, chunk_size, memory_mib):
        row = cell_map[b]
        use = row >= 0
        if np.any(use):
            parts.append(sp.coo_matrix((v[use], (row[use], f[use])),
                                      shape=(n_cells, n_features)).tocsr())
        # Collapse partial CSR matrices regularly: bounded list/indptr overhead.
        if len(parts) >= 8:
            combined = parts[0]
            for part in parts[1:]:
                combined = combined + part
            parts = [combined]
    out = sp.csr_matrix((n_cells, n_features), dtype=np.float32)
    for part in parts:
        out = out + part
    out.sum_duplicates()
    out.sort_indices()
    return out


def extract_channel(paths, out, *, expected=36600, chunk_size=100_000, memory_mib=700):
    """Only call after the job's complete input manifest has passed preflight."""
    started = time.time()
    if out.exists():
        raise FileExistsError('Extraction output exists')
    if shutil.disk_usage(out.parent).free < 2 * 2**30:
        raise OSError('Extraction requires at least 2 GiB free disk')
    nf, nb, _, _ = matrix_header(paths['transcriptome_matrix'])
    tx_names = features(paths['transcriptome_features'])
    label_names = features(paths['labels_features'])
    guide_names = features(paths['guides_features'])
    if len(tx_names) != nf or len(tx_names) != len(set(tx_names)):
        raise ValueError('Transcriptome feature axis invalid')
    if len(guide_names) != len(set(guide_names)):
        raise ValueError('Duplicate guide identifiers')
    for modality, axis in [('labels', label_names), ('guides', guide_names)]:
        shape = matrix_header(paths[modality + '_matrix'])
        if shape[0] != len(axis) or shape[1] != nb:
            raise ValueError('Modalities have inconsistent axes')
    totals = np.zeros(nb, np.float64)
    for _, barcodes, values in triples(paths['transcriptome_matrix'], chunk_size, memory_mib):
        np.add.at(totals, barcodes, values)
    cells, threshold = umi_cells(totals, expected)
    mapper = np.full(nb, -1, np.int32)
    mapper[cells] = np.arange(len(cells), dtype=np.int32)
    labels = sparse_selected(paths['labels_matrix'], mapper, len(cells), len(label_names),
                             chunk_size, memory_mib).toarray()
    label_keep, condition = select_labels(labels, label_names)
    old_n_cells = len(cells)
    cells, condition = cells[label_keep], condition[label_keep]
    del labels, label_keep
    mapper[:] = -1
    mapper[cells] = np.arange(len(cells), dtype=np.int32)
    guides = sparse_selected(paths['guides_matrix'], mapper, len(cells), len(guide_names),
                             chunk_size, memory_mib)
    threshold_guide, medians = guide_threshold(guides)
    carried = (guides >= threshold_guide).astype(np.uint8).tocsr()
    del guides
    stats = {'barcodes': nb, 'umi_threshold': threshold, 'cells_by_umi': old_n_cells,
             'cells_with_one_label': len(cells), 'untreated_cells': int(np.sum(condition == 0)),
             'activated_cells': int(np.sum(condition == 1)), 'guide_umi_threshold': threshold_guide,
             'median_guides_per_cell_by_threshold': medians}
    old = json.loads(paths['old_qc'].read_text())
    for key in ['barcodes', 'cells_by_umi', 'cells_with_one_label', 'untreated_cells',
                'activated_cells', 'guide_umi_threshold']:
        if stats[key] != old[key]:
            raise ValueError(f'Historical QC differs: {key}')
    if not np.isclose(threshold, old['umi_threshold'], rtol=1e-12, atol=1e-9):
        raise ValueError('Historical UMI threshold differs')
    parser = load_historical_parser(paths['pilot_code'], paths['pilot_code_sha256'])
    guide_targets = [parser(name) for name in guide_names]
    panel = set(paths['panel_genes'])
    selected = [i for i, name in enumerate(tx_names) if name in panel]
    if len(selected) != old['panel_genes_in_features']:
        raise ValueError('Panel support differs from historical QC')
    gene_map = np.full(nf, -1, np.int32)
    gene_map[selected] = np.arange(len(selected))
    out.mkdir()
    counts = np.lib.format.open_memmap(out / 'counts.npy', mode='w+', dtype=np.float32,
                                      shape=(len(cells), len(selected)))
    counts[:] = 0
    for f, b, v in triples(paths['transcriptome_matrix'], chunk_size, memory_mib):
        rows, cols = mapper[b], gene_map[f]
        keep = (rows >= 0) & (cols >= 0)
        np.add.at(counts, (rows[keep], cols[keep]), v[keep])
    counts.flush()
    if not np.all(np.isfinite(counts)) or np.any(counts < 0):
        raise ValueError('Invalid extracted counts')
    np.savez(out / 'metadata.npz', barcode_index=cells.astype(np.int32), condition=condition,
             library_size=totals[cells], genes=np.asarray([tx_names[i] for i in selected], dtype=str),
             guides=np.asarray(guide_names, dtype=str), guide_targets=np.asarray(guide_targets, dtype=str))
    sp.save_npz(out / 'guides.npz', carried, compressed=True)
    del counts, carried, mapper, totals
    gc.collect()
    stats.update({'claim': 'Extraction only; no split, effect, model fit or score',
                  'historical_qc_equal': True, 'elapsed_seconds': time.time() - started,
                  'peak_rss_bytes': memory_check(memory_mib), 'chunk_triples': chunk_size,
                  'output_files': {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)}
                                   for p in sorted(out.iterdir()) if p.is_file()}})
    (out / 'complete.json').write_text(json.dumps(stats, indent=2) + '\n', encoding='utf-8')
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--job', type=Path, required=True)
    ap.add_argument('--preflight-manifest', type=Path, required=True)
    ap.add_argument('--preflight-receipt', type=Path, required=True)
    args = ap.parse_args()
    job = json.loads(args.job.read_text())
    receipt = json.loads(args.preflight_receipt.read_text())
    manifest = json.loads(args.preflight_manifest.read_text())
    if receipt.get('status') != 'PASS' or receipt.get('manifest_sha256') != digest(args.preflight_manifest):
        raise ValueError('Wrong or failed preflight receipt')
    if receipt.get('job_id') != manifest['job_id'] or receipt.get('site') != 'local':
        raise ValueError('Receipt describes a different extraction job/site')
    declared = {}
    for row in manifest['inputs']:
        path = Path(row['paths']['local'])
        if not path.is_file() or path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise ValueError('Extraction input changed since preflight')
        declared[str(path.resolve())] = row
    for path in [args.job, Path(__file__), *[Path(value) for key, value in job['paths'].items()
                                          if key not in ('panel_genes', 'pilot_code_sha256')]]:
        if str(path.resolve()) not in declared:
            raise ValueError('An extraction input is absent from the preflight manifest')
    expected_outputs = [Path(row['paths']['local']).resolve() for row in manifest['outputs']]
    if expected_outputs != [Path(job['out']).resolve()]:
        raise ValueError('Extraction output differs from preflight')
    paths = {key: Path(value) if key not in ('panel_genes', 'pilot_code_sha256') else value
             for key, value in job['paths'].items()}
    stats = extract_channel(paths, Path(job['out']), expected=job['expected_cells'],
                            chunk_size=job['chunk_size'], memory_mib=job['memory_mib'])
    print(json.dumps({k: v for k, v in stats.items() if k != 'output_files'}))


if __name__ == '__main__':
    main()
