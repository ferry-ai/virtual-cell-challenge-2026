"""Local adapter from the vendored estimator to AxisTable. Does not import cloud state."""
from __future__ import annotations

import hashlib
import sys

import numpy as np

from estimator_core import estimate_source as estimate_records
from pins import REPO

sys.path.insert(0, str(REPO / 'src'))
from vcc2026.multisource import AxisTable  # noqa: E402


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def load_count_sum(path, sha256, nbytes):
    if path.name != 'count_sum.npz':
        raise ValueError('refusing matrix ' + path.name + '; count_sum is required')
    if path.stat().st_size != nbytes or sha256_file(path) != sha256:
        raise ValueError('count_sum identity mismatch')
    loaded = np.load(path)
    if list(loaded.files) != ['value']:
        raise ValueError('unexpected count_sum keys')
    return np.asarray(loaded['value'], dtype=np.float64)


def as_axis(table):
    return AxisTable(table['name'], list(table['targets']), np.array(table['shrunk'], copy=True),
                     np.array(table['raw'], copy=True), np.array(table['se'], copy=True),
                     np.array(table['n_cells'], copy=True), dict(table['meta']))


def estimate_source(*args, **kwargs):
    result = estimate_records(*args, **kwargs)
    return {'tables': [as_axis(table) for table in result['tables']],
            'dropped_rows': result['dropped_rows'], 'omitted': result['omitted']}
