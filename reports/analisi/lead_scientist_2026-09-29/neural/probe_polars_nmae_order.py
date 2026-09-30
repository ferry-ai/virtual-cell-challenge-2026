"""Tiny synthetic reproduction of the scorer's join/group mean reduction order.

No biological data or model scoring. Output establishes floating-point behavior
of the local installed Polars, not the exact unobserved runtime execution path.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def worker():
    import numpy as np
    import polars as pl
    rng = np.random.default_rng(20260929)
    targets = np.repeat([f'T{i}' for i in range(12)], 1000)
    features = np.tile([f'G{i}' for i in range(1000)], 12)
    x = rng.lognormal(0, 2, size=len(targets))
    y = rng.normal(0, .5, len(targets)) * x
    real = pl.DataFrame({'target': targets, 'feature': features, 'log2_fold_change': x})
    pred = pl.DataFrame({'target': targets, 'feature': features, 'log2_fold_change': y})
    bits, orders = [], set()
    for _ in range(64):
        merged = real.join(pred, on=['target', 'feature'], suffix='_pred', how='left')
        agg = merged.group_by('target').agg(
            num=(pl.col('log2_fold_change_pred') - pl.col('log2_fold_change')).abs().mean(),
            den=pl.col('log2_fold_change').abs().mean(), n_gate=pl.len())
        orders.add(tuple(agg['target'].to_list()))
        values = {t: num/den for t, num, den, n in agg.iter_rows()}
        bits.append(np.array([values[t] for t in sorted(values)]).view(np.uint64))
    numbers = np.stack(bits)
    print(json.dumps({'threads': pl.thread_pool_size(), 'polars_version': pl.__version__,
        'iterations': 64, 'rows': len(targets), 'distinct_target_orders': len(orders),
        'distinct_value_vectors': len({r.tobytes() for r in numbers}),
        'max_ulp_span_by_target': (numbers.max(0)-numbers.min(0)).tolist(),
        'first_values_bits': numbers[0].tolist()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if args.worker:
        worker(); return
    out = Path(__file__).with_name('stack_ab_numerical_diagnostic_r1') / 'polars_probe.json'
    if out.exists():
        raise FileExistsError(out)
    results = []
    for threads in (1, 2, 4):
        env = os.environ | {'POLARS_MAX_THREADS': str(threads), 'OMP_NUM_THREADS': '1',
                            'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'PYTHONHASHSEED': '0'}
        run = subprocess.run([sys.executable, str(Path(__file__)), '--worker'], env=env,
                             capture_output=True, text=True, check=True)
        results.append(json.loads(run.stdout))
    result = {'claim': 'Synthetic numerical mechanism, not proof of exact original root cause',
              'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'runs': results}
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
