"""Reconcile independent CD4 verification receipts; no remote reads or launches."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / 'reports/sorgenti/ingestione_completa_2026-10-03/cd4'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    spec_path = OLD / 'specs/cd4_v1.json'
    spec = json.loads(spec_path.read_text(encoding='utf-8'))
    found = {}
    paths = sorted(OLD.glob('esito_verifica_*/source_complete.json'))
    paths += sorted(HERE.glob('verifica_*/source_complete.json'))
    for path in paths:
        raw = path.read_bytes()
        receipt = json.loads(raw)
        assert receipt['ok'] is True, path
        assert receipt['verdict'] and all(v is True for v in receipt['verdict'].values()), path
        for unit, counts in receipt['units'].items():
            name = unit.removeprefix('cd4_')
            assert name in spec['files'], unit
            expected = spec['files'][name]['cells']
            assert counts['covers_the_unit'] is True, unit
            assert counts['expected_rows'] == counts['rows'] == expected, unit
            assert counts['cells'] + counts['excluded'] == expected, unit
            assert name not in found, f'duplicate receipt: {unit}'
            found[name] = {
                **counts, 'receipt': path.relative_to(ROOT).as_posix(),
                'sha256': hashlib.sha256(raw).hexdigest(),
            }
    missing = sorted(set(spec['files']) - set(found))
    result = {
        'utc': datetime.now(timezone.utc).isoformat(),
        'claim': 'Independent remote receipts reconciled locally; not proof of training use.',
        'spec': spec_path.relative_to(ROOT).as_posix(),
        'spec_sha256': hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        'expected_units': len(spec['files']), 'verified_units': len(found),
        'complete': not missing, 'missing': missing, 'units': found,
        'totals_verified': {key: sum(v[key] for v in found.values())
                            for key in ('rows', 'cells', 'excluded', 'bytes')},
    }
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('verified_units', 'expected_units', 'missing')}))


if __name__ == '__main__':
    main()
