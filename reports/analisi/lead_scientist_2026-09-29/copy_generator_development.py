"""Copy only completed development reports; never visit confirmation outputs."""
from pathlib import Path
import argparse
import hashlib
import json
from datetime import datetime, timezone


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    files = [a.source / name for name in ('target_manifest.json', 'development_environment.json')]
    development = a.source / 'development'
    files += sorted(x for x in development.iterdir() if x.is_file() and x.suffix in {'.json', '.csv'})
    expected = {'bench.json', 'run_manifest.json', 'selection.json', 'depth_control_fit.json'}
    expected.update(f'{prefix}_{arm}_s1.{ext}' for prefix, ext in (
        ('result', 'json'), ('diagnostics', 'json'), ('per_pert', 'csv'), ('components', 'csv'))
        for arm in [f'a{amp}_p{phi}' for amp in ('1', '1p5', '2') for phi in ('0', '0p25', '0p5', '1')] + ['bins_a1', 'bins_a2'])
    if {x.name for x in files[2:]} != expected:
        raise ValueError('Development report allowlist mismatch')
    records = []
    payloads = []
    for source in files:
        if source.stat().st_size > 2_000_000:
            raise ValueError(f'Report size exceeds limit: {source}')
        data = source.read_bytes()
        if source.read_bytes() != data:
            raise RuntimeError(f'File changed while reading: {source}')
        relative = source.relative_to(a.source)
        payloads.append((relative, data))
        records.append({'path': relative.as_posix(), 'source': str(source), 'bytes': len(data),
                        'sha256': hashlib.sha256(data).hexdigest()})
    a.out.mkdir(parents=True)
    for relative, data in payloads:
        dest = a.out / relative
        dest.parent.mkdir(exist_ok=True)
        with dest.open('xb') as f:
            f.write(data)
    manifest = {'copied_utc': datetime.now(timezone.utc).isoformat(),
                'scope': 'Completed development reports plus target manifest and environment only; no confirmation outputs, NPZ, NPY or raw data read or copied.',
                'files': records, 'total_bytes': sum(x['bytes'] for x in records)}
    (a.out / 'COPY_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'files': len(records), 'bytes': manifest['total_bytes'], 'out': str(a.out)}))


if __name__ == '__main__':
    main()
