"""Check that A/B retained the same transfer cells, with bounded reads and no scoring."""
import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
from vcc2026.sc_stream import read_frame


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def equal_datasets(a, b):
    if a.shape != b.shape or a.dtype != b.dtype or a.ndim != 1:
        return False
    return all(np.array_equal(a[start:start + 1_000_000], b[start:start + 1_000_000])
               for start in range(0, len(a), 1_000_000))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a', required=True, type=Path)
    ap.add_argument('--b', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    hashes = {'a': sha(args.a), 'b': sha(args.b)}
    result = {'sha256': hashes, 'file_bytes_identical': hashes['a'] == hashes['b'],
              'scores_read': False, 'stack_prediction_arrays_compared': False}
    with h5py.File(args.a, 'r') as a, h5py.File(args.b, 'r') as b:
        x, y = a['X'], b['X']
        assert isinstance(x, h5py.Group) and isinstance(y, h5py.Group)
        assert x.attrs['encoding-type'] == y.attrs['encoding-type'] == 'csr_matrix'
        checks = {'shape': np.array_equal(x.attrs['shape'], y.attrs['shape']),
                  'obs': read_frame(a['obs']).equals(read_frame(b['obs'])),
                  'var': read_frame(a['var']).equals(read_frame(b['var']))}
        checks.update({key: equal_datasets(x[key], y[key]) for key in ['indptr', 'indices', 'data']})
        result['transfer_array_checks'] = checks
        result['transfer_cells_exact'] = all(checks.values())
        result['shape'] = np.asarray(x.attrs['shape']).tolist()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
