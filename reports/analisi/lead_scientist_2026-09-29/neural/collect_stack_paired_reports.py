"""Recover085 small complete reports and runtime receipt after dispatcher rc0."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
RUNS = Path('G:/Il mio Drive/vcc2026/runs')
SOURCE = RUNS / 'lead_stack_paired_score_2026-09-29_r1'
SETUP = RUNS / 'lead_stack_paired_scoring_setup_2026-09-29_r1'
OUT = HERE / 'stack_paired_scoring_results_r1'
NAMES = ['components_stack.csv', 'components_transfer.csv', 'evaluation_manifest.json',
         'per_pert_stack.csv', 'per_pert_transfer.csv', 'pilot_comparison.json',
         'result_stack.json', 'result_transfer.json', 'scorer_config.json', 'scoring_pip_freeze.txt']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def collect_receipt():
    out = HERE / 'stack_paired_scoring_runtime_r1'
    if out.exists():
        raise FileExistsError(out)
    path = SETUP/'preflight_runtime_receipt.json'
    raw = path.read_bytes(); receipt = json.loads(raw)
    contract_path = HERE/'stack_paired_scoring_setup_r1'/'job_contract.json'
    contract = json.loads(contract_path.read_text())
    assert receipt['status'] == 'PASS' and receipt['site'] == 'runtime'
    assert receipt['job_id'] == contract['job_id']
    assert receipt['manifest_sha256'] == sha(contract_path.read_bytes())
    assert receipt['validator_sha256'] == sha((HERE/'stack_paired_scoring_setup_r1'/'preflight.py').read_bytes())
    expected, actual = [{row['id']: row for row in table} for table in [contract['inputs'], receipt['inputs']]]
    assert expected.keys() == actual.keys() and len(actual) == 15
    for key,item in expected.items():
        assert actual[key]['path'] == item['paths']['runtime'] and actual[key]['sha256'] == item['sha256'] and actual[key]['bytes'] == item['bytes']
    assert receipt['new_outputs'] == [item['paths']['runtime'] for item in contract['outputs']]
    assert raw == path.read_bytes()
    out.mkdir()
    with (out/path.name).open('xb') as stream:
        stream.write(raw)
    assert sha((out/path.name).read_bytes()) == sha(raw)
    verification = {'collected_utc': datetime.now(timezone.utc).isoformat(), 'status': 'runtime_preflight_verified',
        'receipt_checked_utc': receipt['checked_utc'], 'source': str(path), 'receipt_sha256': sha(raw),
        'manifest_sha256': receipt['manifest_sha256'], 'input_count': 15,
        'scope': 'Only preflight; no scientific outcome or completed scoring implied'}
    with (out/'verification.json').open('x', encoding='utf-8') as stream:
        json.dump(verification,stream,indent=2); stream.write('\n')
    print(json.dumps(verification,indent=2))


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    done = [line for line in (RUNS/'jobs'/'dispatcher.log').read_text(encoding='utf-8').splitlines()
            if 'finished 085_lead_stack_paired_rescore_r1.sh rc=' in line]
    assert len(done) == 1 and done[0].endswith('rc=0')
    files = {f'{arm}/{name}': SOURCE/arm/name for arm in ['A','B'] for name in NAMES}
    files |= {'complete.json': SOURCE/'complete.json', 'preflight_runtime_receipt.json': SETUP/'preflight_runtime_receipt.json'}
    raw = {}
    for name, path in files.items():
        assert path.is_file() and path.stat().st_size < 2000000
        raw[name] = path.read_bytes()
        if name.endswith('.json'):
            json.loads(raw[name])
    complete = json.loads(raw['complete.json'])
    assert complete['status'] == 'both_scores_complete'
    assert complete['comparisons'] == {arm: sha(raw[f'{arm}/pilot_comparison.json']) for arm in ['A','B']}
    receipt = json.loads(raw['preflight_runtime_receipt.json'])
    contract_path = HERE/'stack_paired_scoring_setup_r1'/'job_contract.json'
    contract = json.loads(contract_path.read_text())
    assert receipt['status'] == 'PASS' and receipt['site'] == 'runtime'
    assert receipt['job_id'] == contract['job_id']
    assert receipt['manifest_sha256'] == sha(contract_path.read_bytes())
    assert receipt['validator_sha256'] == sha((HERE/'stack_paired_scoring_setup_r1'/'preflight.py').read_bytes())
    expected, actual = [{row['id']: row for row in table} for table in [contract['inputs'], receipt['inputs']]]
    assert expected.keys() == actual.keys() and len(actual) == 15
    for key, item in expected.items():
        assert actual[key]['path'] == item['paths']['runtime'] and actual[key]['sha256'] == item['sha256'] and actual[key]['bytes'] == item['bytes']
    for arm in ['A','B']:
        versions = json.loads(raw[f'{arm}/evaluation_manifest.json'])['versions']
        assert all(contract['required_runtime_versions'][key] == value for key,value in versions.items())
    OUT.mkdir()
    inventory = []
    for name, content in raw.items():
        assert content == files[name].read_bytes()
        path = OUT/name; path.parent.mkdir(exist_ok=True)
        with path.open('xb') as stream:
            stream.write(content)
        assert sha(path.read_bytes()) == sha(content)
        inventory.append({'name': name, 'source': str(files[name]), 'bytes': len(content), 'sha256': sha(content)})
    with (OUT/'collection.json').open('x', encoding='utf-8') as stream:
        json.dump({'collected_utc': datetime.now(timezone.utc).isoformat(), 'dispatcher_completion': done[0],
                   'files': inventory, 'scope': 'Small complete reports only; no original predictions or truth copied'},stream,indent=2)
        stream.write('\n')
    print(json.dumps({'out': str(OUT), 'file_count': len(inventory), 'dispatcher_completion': done[0],
        'comparison': {arm: json.loads(raw[f'{arm}/pilot_comparison.json']) for arm in ['A','B']}},indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['--receipt-only']:
        collect_receipt()
    elif not sys.argv[1:]:
        main()
    else:
        raise SystemExit('Use no argument or --receipt-only')
