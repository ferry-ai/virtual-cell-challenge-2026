"""Freeze only a completed confirmation's small reports; no cellular arrays."""
from pathlib import Path
import argparse
import hashlib
import json
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run = args.source / 'confirmation'
    if not (run / 'selection.json').is_file():
        raise FileNotFoundError('Confirmation is incomplete; no partial report read')
    if args.out.exists():
        raise FileExistsError(args.out)
    expected = {'bench.json', 'run_manifest.json', 'selection.json'}
    expected.update(f'{prefix}_{arm}_s{seed}.{suffix}'
                    for prefix, suffix in [('result', 'json'), ('diagnostics', 'json'),
                                           ('per_pert', 'csv'), ('components', 'csv')]
                    for arm in ('a1_p0', 'a1p5_p1', 'a1p5_p0p5') for seed in (1, 2, 3))
    reports = sorted(p for p in run.iterdir() if p.is_file() and p.suffix in {'.json', '.csv'})
    if {p.name for p in reports} != expected:
        raise ValueError('Completed confirmation report allowlist differs')
    reports += [args.source / name for name in ('target_manifest.json', 'development_environment.json')]
    payloads, records = [], []
    for source in reports:
        if source.stat().st_size > 2_000_000:
            raise ValueError(f'Report too large: {source}')
        data = source.read_bytes()
        if source.read_bytes() != data:
            raise RuntimeError(f'Report changed while reading: {source}')
        relative = source.relative_to(args.source)
        payloads.append((relative, data))
        records.append({'path': relative.as_posix(), 'source': str(source), 'bytes': len(data),
                        'sha256': hashlib.sha256(data).hexdigest()})
    args.out.mkdir(parents=True)
    for relative, data in payloads:
        target = args.out / relative
        target.parent.mkdir(exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
    manifest = {'copied_utc': datetime.now(timezone.utc).isoformat(),
                'scope': 'Complete confirmation JSON/CSV and frozen target/environment manifests only',
                'files': records, 'total_bytes': sum(item['bytes'] for item in records)}
    with (args.out / 'COPY_MANIFEST.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'files': len(records), 'bytes': manifest['total_bytes'], 'out': str(args.out)}))


if __name__ == '__main__':
    main()
