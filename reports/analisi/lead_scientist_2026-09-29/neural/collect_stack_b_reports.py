"""Copy only the ten complete job084 reports after dispatcher rc0, with hashes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = Path('G:/Il mio Drive/vcc2026/runs')
SOURCE = RUNS / 'lead_stack_score_b_2026-09-29_r1'
OUT = HERE / 'stack_b_scoring_r1'
NAMES = ['components_stack.csv', 'components_transfer.csv', 'evaluation_manifest.json',
         'per_pert_stack.csv', 'per_pert_transfer.csv', 'pilot_comparison.json',
         'result_stack.json', 'result_transfer.json', 'scorer_config.json', 'scoring_pip_freeze.txt']


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    lines = [s for s in (RUNS / 'jobs' / 'dispatcher.log').read_text(encoding='utf-8').splitlines()
             if 'finished 084_lead_stack_score_b_r1.sh rc=' in s]
    assert len(lines) == 1 and lines[0].endswith('rc=0')
    originals = {}
    for name in NAMES:
        path = SOURCE / name
        assert path.is_file() and path.stat().st_size < 2000000
        raw = path.read_bytes()
        if name.endswith('.json'):
            json.loads(raw)
        originals[name] = raw
    OUT.mkdir()
    files = []
    for name, raw in originals.items():
        assert raw == (SOURCE / name).read_bytes()
        with (OUT / name).open('xb') as stream:
            stream.write(raw)
        sha = hashlib.sha256(raw).hexdigest()
        assert hashlib.sha256((OUT / name).read_bytes()).hexdigest() == sha
        files.append({'name': name, 'source': str(SOURCE / name), 'bytes': len(raw), 'sha256': sha})
    receipt = {'collected_utc': datetime.now(timezone.utc).isoformat(), 'dispatcher_completion': lines[0],
               'files': files, 'scope': 'Ten original small reports only; no H5AD/NPZ copied'}
    with (HERE / 'stack_b_scoring_r1_files.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2); stream.write('\n')
    result = json.loads(originals['pilot_comparison.json'])
    print(json.dumps({'output': str(OUT), 'file_count': len(files), 'dispatcher_completion': lines[0],
        'comparison': result}, indent=2))


if __name__ == '__main__':
    main()
