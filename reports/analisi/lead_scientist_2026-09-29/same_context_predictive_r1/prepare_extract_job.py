"""Prepare one private local extraction contract. No matrix ingestion, fit or launch."""
import argparse
import csv
from importlib import metadata
import json
from pathlib import Path
import sys

from stream_screen import digest
import vcc2026.resources as resources


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inventory', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--channel', type=int, default=1)
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError('Prepared job destination must be new')
    if not 1 <= args.channel <= 16:
        raise ValueError('Channel index must be 1..16')
    inv = json.loads(args.inventory.read_text())
    txs = sorted(r['path'] for r in inv['mtx_headers'] if r['path'].endswith('_transcriptome_matrix.mtx.gz'))
    chosen = Path(txs[args.channel - 1])
    prefix = chosen.name.removesuffix('_transcriptome_matrix.mtx.gz')
    recorded = {str(Path(r['path']).resolve()): r for r in inv['raw_files']}
    paths = {f'{m}_{part}': chosen.with_name(f'{prefix}_{m}_{part}.{ext}')
             for m in ['transcriptome', 'labels', 'guides']
             for part, ext in [('matrix', 'mtx.gz'), ('features', 'tsv.gz')]}
    pilot = [r for r in inv['retained_derivatives_and_code'] if Path(r['path']).name == 'pilot_channel.py']
    qc = [r for r in inv['retained_derivatives_and_code']
          if Path(r['path']).name.startswith(prefix) and r['path'].endswith('.h5ad.json')]
    if len(pilot) != 1 or len(qc) != 1:
        raise ValueError('Historical pilot/QC reference ambiguous')
    paths['pilot_code'] = Path(pilot[0]['path'])
    paths['old_qc'] = Path(qc[0]['path'])
    panel_file = Path(inv['source_root']) / 'table_s2_panel.csv'
    with panel_file.open(encoding='utf-8-sig', newline='') as f:
        next(f)
        panel = [r['symbol'] for r in csv.DictReader(f) if str(r.get('entrez', '')).isdigit()]
    if len(set(panel)) != 374:
        raise ValueError('Targeted response panel changed')
    out = args.out.resolve()
    code_dir = Path(__file__).resolve().parent
    validator = code_dir.parent / 'learning/preflight.py'
    output = out / f'channel_{args.channel:02d}'
    job = {'job_id': f'masked_screen_channel_{args.channel:02d}', 'claim': 'Extraction only; no fit',
           'paths': {k: str(v.resolve()) for k, v in paths.items()} |
                    {'panel_genes': panel, 'pilot_code_sha256': pilot[0]['sha256']},
           'out': str(output), 'expected_cells': 36600, 'chunk_size': 100000, 'memory_mib': 700}
    out.mkdir(parents=True)
    job_path = out / 'extraction.json'
    job_path.write_text(json.dumps(job, indent=2) + '\n', encoding='utf-8')
    inputs = []
    # Raw input hashes are the original acquisition records here; the actual
    # preflight must rehash them in full before execution. Never claim otherwise.
    all_paths = [*paths.values(), panel_file, args.inventory, job_path, code_dir / 'stream_screen.py',
                 code_dir / 'PROTOCOLLO.md', Path(resources.__file__), validator]
    for i, path in enumerate(all_paths):
        path = path.resolve()
        record = recorded.get(str(path))
        expected = record['sha256'] if record else digest(path)
        size = record['bytes'] if record else path.stat().st_size
        if path.stat().st_size != size:
            raise ValueError('Input size changed from acquisition')
        inputs.append({'id': f'input_{i:02d}', 'paths': {'local': str(path), 'runtime': str(path)},
                       'bytes': size, 'sha256': expected})
    environment = {'python': {'paths': {'local': sys.executable, 'runtime': sys.executable}},
                   'packages': {name: metadata.version(name) for name in ['numpy', 'scipy', 'pandas']},
                   'imports': ['numpy', 'scipy.sparse', 'pandas', 'vcc2026.resources'], 'probes': []}
    manifest = {'schema_version': 1, 'job_id': job['job_id'],
                'incident_ids': ['E-20260929-002', 'E-20260929-004', 'E-20260929-005'],
                'incident_guards': ['Non-object NPZ roundtrip', 'Complete input/response axes',
                                    'Full hashes before scientific work; no marker-only success'],
                'inputs': inputs, 'outputs': [{'id': 'extracted_channel', 'paths': {'local': str(output), 'runtime': str(output)},
                                             'must_be_absent': True}],
                'target_checks': [], 'environment': environment}
    manifest_path = out / 'preflight_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (out / 'PREPARATO_NON_ESEGUITO.txt').write_text(
        'Contratto preparato; nessun preflight o ingestione eseguiti.\n'
        'SHA raw da acquisizione: il preflight deve ricalcolarli integralmente.\n'
        'Prima: controllare spazio disco/concorrenza con il recupero VCC.\n'
        f'Python: {sys.executable}\n'
        f'Preflight: {validator}\n'
        f'Manifest SHA256: {digest(manifest_path)}\n'
        'Comandi (dal repository, non avviati dal builder):\n'
        f'.\\scripts\\py.cmd "{validator}" validate --manifest "{manifest_path}" --site local --receipt "{out / "preflight_receipt.json"}"\n'
        f'.\\scripts\\py.cmd "{code_dir / "stream_screen.py"}" --job "{job_path}" --preflight-manifest "{manifest_path}" --preflight-receipt "{out / "preflight_receipt.json"}"\n', encoding='utf-8')
    print(json.dumps({'status': 'PREPARED_NOT_RUN', 'channel': args.channel,
                      'input_files': len(inputs), 'raw_input_bytes': sum(r['bytes'] for r in inputs[:6]),
                      'manifest_sha256': digest(manifest_path), 'extraction_sha256': digest(job_path)}))


if __name__ == '__main__':
    main()
