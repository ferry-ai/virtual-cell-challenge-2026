"""Trace actual neural input/row roles and local source availability without matrix reads."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = Path('C:/Users/ferra/vcc2026-data')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def stat(path):
    path = Path(path)
    return {'path': str(path), 'exists': path.is_file(), 'bytes': path.stat().st_size if path.is_file() else None,
            'content_read': False}


def small_evidence(path):
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def main():
    out = HERE / 'training_copertura_r1'
    if out.exists():
        raise FileExistsError(out)
    historic = REPO / 'reports/analisi/audit_piani_dati_2026-09-26/r1'
    old = load(historic / 'local_external_files.json')
    with (historic / 'accession_mentions.csv').open(encoding='utf-8', newline='') as f:
        mentions = list(csv.DictReader(f))
    current = []
    grouped = defaultdict(lambda: {'files': 0, 'bytes': 0, 'large_files': []})
    for path in sorted((DATA / 'external').rglob('*')):
        if path.is_file():
            relative = path.relative_to(DATA / 'external')
            label = relative.parts[0]
            item = {'relative': str(relative), 'bytes': path.stat().st_size}
            current.append(item)
            grouped[label]['files'] += 1
            grouped[label]['bytes'] += item['bytes']
            if item['bytes'] > 100_000_000:
                grouped[label]['large_files'].append(item)
    dataset = DATA / 'processed/rete_contesti_r2'
    manifest_path = dataset / 'manifest.json'
    manifest = load(manifest_path)
    with (dataset / 'contexts.csv').open(encoding='utf-8', newline='') as f:
        contexts = list(csv.DictReader(f))
    row_context = np.load(dataset / 'row_context.npy', allow_pickle=False)
    folds = {}
    for family in ['k562', 'cd4', 'orion', 'ipsc', 'rpe1']:
        path = HERE / f'kaggle_lead_monitor/r6/seed1/neural_seed1_r1/folds/C_{family}_s1/manifest.json'
        fold = load(path)
        counts = {}
        for role in ['train', 'refit', 'validation', 'test']:
            values = fold['design'][role]
            rows = [r for group in values.values() for r in group] if isinstance(values, dict) else values
            counts[role] = dict(Counter(map(int, row_context[rows])))
        folds[family] = {'manifest': small_evidence(path), 'counts': counts,
                         'code_hashes': fold['code_hashes'],
                         'options': {k: fold['options'][k] for k in ['regime', 'seed', 'selection_seed', 'steps', 'batch']}}
    context_items = []
    for idx, ctx in enumerate(contexts):
        u = manifest['universes'][ctx['context']]
        upath = Path(u['manifest']['path'])
        um = load(upath)
        if sha(upath) != u['manifest']['sha256']:
            raise ValueError('Universe manifest changed from dataset build')
        if sha(Path(u['index']['path'])) != u['index']['sha256']:
            raise ValueError('Universe index changed from dataset build')
        source = {}
        if 'bulk' in um:
            source = {'kind': 'pseudobulk source file', 'file': stat(um['bulk'])}
        elif isinstance(um.get('source'), str):
            source = {'kind': 'pseudobulk source file', 'file': stat(um['source']),
                      'recorded_source_manifest': um.get('source_manifest')}
        elif 'input' in um:
            source = {'kind': 'cellular sums derivative, not raw cells',
                      'file': stat(um['input']['sums']), 'recorded_sha256': um['input']['sha256'],
                      'source_provenance': um.get('source')}
        elif 'files' in um:
            source = {'kind': 'streamed raw shards, persistence not implied',
                      'files': len(um['files']), 'bytes_streamed': um.get('summary', {}).get('bytes_streamed'),
                      'source_provenance': um.get('source'), 'work_directory': str(um.get('work'))}
        context_items.append({'context': ctx['context'], 'family': ctx['family'], 'group': ctx['group'],
                              'modality': ctx['modality'], 'serialized_effect_rows': int(ctx['row_stop']) - int(ctx['row_start']),
                              'universe_manifest': small_evidence(upath), 'universe_index_sha256': u['index']['sha256'],
                              'input': source, 'summary_counts': {k: v for k, v in um.get('summary', {}).items()
                                                              if k in ['targets', 'targets_with_effects', 'cells', 'ntc_cells', 'cells_pass_filter', 'rows_read']},
                              'roles_by_outer_fold': {f: {role: value['counts'][role].get(idx, 0)
                                                        for role in ['train', 'refit', 'validation', 'test']}
                                                     for f, value in folds.items()}})
    included = {str(Path(v['folder']).resolve()) for v in manifest['universes'].values()}
    excluded = []
    for folder in sorted((DATA / 'processed').glob('universe*')):
        upath = folder / 'manifest.json'
        if upath.is_file() and str(folder.resolve()) not in included:
            um = load(upath)
            excluded.append({'folder': folder.name, 'manifest': small_evidence(upath),
                             'rows_with_effects': um.get('summary', {}).get('targets_with_effects'),
                             'context': um.get('context'), 'name': um.get('name'),
                             'source': um.get('source'),
                             'derivative': stat(um['input']['sums']) if 'input' in um and 'sums' in um['input'] else None,
                             'reason_proved_by_inventory': 'Not in active r2 registry; no scientific rejection inferred'})
    result = {'claim': 'File metadata and frozen training role audit, no large expression arrays read',
              'catalog_2026_09_26': {'files': len(old), 'accessions': len(mentions),
                                    'evidence': [small_evidence(historic / name) for name in ['local_external_files.json', 'accession_mentions.csv']],
                                    'accession_list': sorted({m['accession'] for m in mentions}),
                                    'warning': 'Mentioned accessions are not distinct validated datasets'},
              'local_external_now': {'files': len(current), 'bytes': sum(r['bytes'] for r in current), 'groups': dict(grouped),
                                     'check': 'Filesystem sizes only, not full integrity hashes'},
              'neural_dataset': {'manifest': small_evidence(manifest_path), 'counts': manifest['counts'],
                                 'physical_stored_bytes': sum(manifest['bytes'].values()),
                                 'context_rows': context_items, 'folds': folds},
              'available_universes_not_in_r2': excluded,
              'local_truth': stat(DATA / 'raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad'),
              'production_recipe': small_evidence(REPO / 'configs/recipes/t25.json'),
              'limits': ['Train/refit rows are the eligible pool, not evidence that every row appeared in a gradient minibatch.',
                         'Recorded raw SHA values are provenance; this audit does not rehash large files.',
                         'Line/state/donor counts require study metadata; family/context counts are not cell-line counts.']}
    out.mkdir()
    (out / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'catalog_files': len(old), 'catalog_accessions': len(mentions),
                      'external_current_files': len(current), 'external_current_bytes': sum(r['bytes'] for r in current),
                      'r2_serialized_rows': manifest['counts']['rows'], 'r2_bytes': result['neural_dataset']['physical_stored_bytes'],
                      'active_crispri_rows': sum(r['serialized_effect_rows'] for r in context_items if r['modality'] == 'crispri'),
                      'not_in_r2_universes': len(excluded),
                      'not_in_r2_targeted_hipsci': sum('hipsci_' in r['folder'] and r['folder'].endswith('_p2') for r in excluded)}))


if __name__ == '__main__':
    main()
