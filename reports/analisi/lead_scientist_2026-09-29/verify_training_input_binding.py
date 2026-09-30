"""Bind small local r2 files to each remote training manifest, without large reads."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = Path('C:/Users/ferra/vcc2026-data/processed/rete_contesti_r2')


def main():
    out = HERE / 'training_copertura_r1/runtime_binding.json'
    if out.exists():
        raise FileExistsError(out)
    runs = []
    for family in ['k562', 'cd4', 'orion', 'ipsc', 'rpe1']:
        p = HERE / f'kaggle_lead_monitor/r6/seed1/neural_seed1_r1/folds/C_{family}_s1/manifest.json'
        run = json.loads(p.read_text())
        checked, sizes = [], []
        for name, expected in run['data_files'].items():
            local = DATA / name
            if local.stat().st_size != expected['bytes']:
                raise ValueError('Training input size changed')
            if expected['sha256'] is not None:
                got = hashlib.sha256(local.read_bytes()).hexdigest()
                if got != expected['sha256']:
                    raise ValueError('Small training input SHA changed')
                checked.append({'file': name, 'bytes': expected['bytes'], 'sha256': got})
            else:
                sizes.append({'file': name, 'bytes': expected['bytes'], 'sha256_verified': False})
        runs.append({'family': family, 'small_inputs_checked': checked, 'large_size_only': sizes,
                     'declared_identity_policy': run['large_array_identity']})
    result = {'claim': 'Small-file exact hash binding and large-file size binding only',
              'all_passed': True, 'folds': runs}
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'folds': len(runs), 'hashed_files_per_fold': len(runs[0]['small_inputs_checked']),
                      'large_size_only_per_fold': len(runs[0]['large_size_only'])}))


if __name__ == '__main__':
    main()
