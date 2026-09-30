"""Inventory one local targeted screen without expression parsing or identity disclosure."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mtx_header(path):
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            if not line.startswith('%'):
                f, b, n = map(int, line.split())
                return {'features': f, 'barcodes': b, 'nnz': n, 'triple_array_bytes_lower_bound': n * 12}
    raise ValueError('Missing Matrix Market dimensions')


def symbols(path, column, skip=0):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        for _ in range(skip):
            next(stream)
        return [row[column] for row in csv.DictReader(stream)]


def target_of(name):
    # This is the existing pilot's parsing rule, copied without scientific changes.
    base = name.rsplit('_', 1)[0]
    return 'non-targeting' if base.lower().startswith('non-targeting') or base.upper().startswith('CTRL') else base


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--pilot-root', type=Path, required=True)
    ap.add_argument('--data-root', type=Path, required=True)
    ap.add_argument('--private-out', type=Path, required=True)
    ap.add_argument('--public-out', type=Path, required=True)
    args = ap.parse_args()
    if args.private_out.exists() or args.public_out.exists():
        raise FileExistsError('Inventory outputs must be new')
    channel_root = args.source_root / 'channels'
    recorded = {}
    manifests = []
    for path in sorted(channel_root.glob('manifest*.json')):
        manifests.append({'path': str(path), 'sha256': sha(path)})
        for row in json.loads(path.read_text())['files']:
            name = row['file']
            if name in recorded and recorded[name] != row:
                raise ValueError('Acquisition manifests disagree')
            recorded[name] = row
    files, headers = [], []
    for name, record in sorted(recorded.items()):
        path = channel_root / name
        if Path(name).name != name or not path.is_file() or path.stat().st_size != record['bytes']:
            raise ValueError('Recorded source member missing or changed size')
        small = path.stat().st_size < 1_000_000
        if small and sha(path) != record['sha256']:
            raise ValueError('Small source file hash differs')
        files.append(record | {'path': str(path), 'full_sha256_checked_now': small})
        if name.endswith('_matrix.mtx.gz'):
            headers.append({'path': str(path), **mtx_header(path)})
    guide_paths = sorted(channel_root.glob('*_guides_features.tsv.gz'))
    guide_sets, guide_counts = [], []
    for path in guide_paths:
        with gzip.open(path, 'rt') as stream:
            names = [row[1] for row in csv.reader(stream, delimiter='\t')]
        if len(names) != len(set(names)):
            raise ValueError('Guide identifiers are not unique')
        guide_sets.append(set(names))
        guide_counts.append(Counter(target_of(name) for name in names))
    assert len(guide_sets) == 16 and all(x == guide_sets[0] for x in guide_sets)
    panel = set(symbols(args.source_root / 'table_s2_panel.csv', 'symbol', 1))
    library = set(symbols(args.source_root / 'table_s1_library.csv', 'symbol', 1))
    genes = set(symbols(args.data_root / 'raw/controls/gene_names.csv', 'gene_name'))
    targets = set(symbols(args.data_root / 'raw/controls/pert_counts.csv', 'target_gene'))
    guide_stats = guide_counts[0]
    retained = []
    for path in sorted(args.pilot_root.rglob('*')):
        if path.is_file():
            retained.append({'path': str(path), 'bytes': path.stat().st_size,
                             'sha256': sha(path) if path.stat().st_size < 2_000_000 else None})
    histograms = {'all_targets': dict(sorted(Counter(guide_stats[t] for t in guide_stats if t != 'non-targeting').items())),
                  'official_targets': dict(sorted(Counter(guide_stats.get(t, 0) for t in targets).items()))}
    channel_reports = [json.loads(path.read_text()) for path in sorted((args.pilot_root / 'channels').glob('*.json'))]
    numeric = {key: sum(row[key] for row in channel_reports) for key in ['cells_with_one_label', 'untreated_cells', 'activated_cells']}
    summaries = {}
    for modality in ['transcriptome', 'guides', 'labels']:
        chosen = [h for h in headers if f'_{modality}_' in h['path']]
        summaries[modality] = {'channels': len(chosen), 'max_nnz': max(h['nnz'] for h in chosen),
                              'max_barcodes': max(h['barcodes'] for h in chosen),
                              'max_triple_array_bytes_lower_bound': max(h['triple_array_bytes_lower_bound'] for h in chosen)}
    public = {'claim': 'Local descriptive inventory only; no expression parsed, score or fit',
              'raw_files_in_acquisition_manifests': len(files), 'raw_bytes': sum(x['bytes'] for x in files),
              'raw_large_hashes': 'Acquisition SHA256 retained; sizes verified now, full large-file hashes not rerun',
              'channels': 16, 'guide_axes_equal': True, 'guide_features': len(guide_sets[0]),
              'perturbation_targets_in_library': len(library), 'official_targets_in_library': len(targets & library),
              'targeted_response_genes': len(panel), 'official_response_genes': len(panel & genes),
              'official_axis_genes': len(genes), 'guide_count_histograms': histograms,
              'old_qc_cell_totals': numeric, 'matrix_headers_summary': summaries,
              'retained_small_reports_or_code': len(retained),
              'retained_h5ad_derivatives': sum(x['path'].endswith('.h5ad') for x in retained),
              'removed_derivative_manifest_retained': (args.pilot_root / 'spostati_nel_cestino_2026-09-25.txt').exists(),
              'metadata_license_revalidated': False,
              'context_identity_disclosed': False}
    private = {'source_root': str(args.source_root), 'pilot_root': str(args.pilot_root),
               'acquisition_manifests': manifests, 'raw_files': files, 'mtx_headers': headers,
               'retained_derivatives_and_code': retained,
               'guide_split_inventory': {t: sorted(g for g in guide_sets[0] if target_of(g) == t) for t in sorted(targets)},
               'public_summary': public}
    args.private_out.mkdir(parents=True)
    (args.private_out / 'inventory.json').write_text(json.dumps(private, indent=2) + '\n', encoding='utf-8')
    args.public_out.mkdir(parents=True)
    (args.public_out / 'inventory_summary.json').write_text(json.dumps(public, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(public))


if __name__ == '__main__':
    main()
