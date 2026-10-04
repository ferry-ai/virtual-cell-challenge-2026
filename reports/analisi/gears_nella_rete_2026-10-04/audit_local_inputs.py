"""Read-only provenance/coverage check on the existing small descriptor bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    manifest = json.loads((a.bundle / 'manifest.json').read_text())
    matrix = np.load(a.bundle / 'descriptors.npy', mmap_mode='r', allow_pickle=False)
    assert list(matrix.shape) == manifest['shape']
    actual = digest(a.bundle / 'descriptors.npy')
    assert actual == manifest['sha256_descriptors']
    genes = (a.bundle / 'genes.txt').read_text().splitlines()
    assert len(genes) == len(set(genes)) == len(matrix)
    # Deliberately do not rehash the 506 MB DepMap table for this small check.
    inputs = manifest['sources']
    checked = {}
    for key in ('goa', 'obo', 'string_links', 'string_info', 'hgnc'):
        info = inputs[key]
        path = Path(info['path'])
        if not path.is_file():
            checked[key] = {'path': str(path), 'status': 'missing_at_recorded_path',
                            'expected_sha256': info['sha256']}
            continue
        assert path.stat().st_size == info['bytes'], key
        measured = digest(path)
        assert measured == info['sha256'], key
        checked[key] = {'path': str(path), 'bytes': path.stat().st_size,
                        'sha256': measured, 'status': 'verified'}
    flags = {b['block']: int((matrix[:, b['start']:b['stop']] > 0).any(axis=1).sum())
             for b in manifest['layout'] if b['block'].endswith('_present')}
    result = {'descriptor_sha256': actual, 'shape': list(matrix.shape),
              'presence_flags_on_official_axis': flags, 'layout': manifest['layout'],
              'checked_inputs': checked,
              'scope': 'Presence flags, not graph degrees or predictive quality. DepMap source not rehashed. No graph built.'}
    with a.out.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(json.dumps({'shape': result['shape'], 'presence': flags,
                      'source_status': {k: v['status'] for k, v in checked.items()}}))


if __name__ == '__main__':
    main()
