"""Append immutable incident revisions and derive their current index.

Append validates the hash chain; index never rewrites source incidents.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

STATES = {'observed', 'implemented', 'verified_locally', 'verified_remotely'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_record(record):
    if record.get('schema_version') != 1 or not re.fullmatch('E-20[0-9]{6}-[0-9]{3}', record.get('eid', '')):
        raise ValueError('Invalid incident schema or EID')
    if type(record.get('revision')) is not int or record['revision'] < 1:
        raise ValueError('Revision must be a positive integer')
    for key in ['title', 'symptom', 'cause', 'fix', 'regression_test', 'next_guard', 'scope']:
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError('Missing incident field: ' + key)
    if record.get('state') not in STATES or record.get('claim_type') != 'operational_incident':
        raise ValueError('Unknown state or claim type; negative scientific results are not incidents')
    if not isinstance(record.get('evidence'), list) or not record['evidence']:
        raise ValueError('Incident needs evidence')
    for item in record['evidence']:
        if not item.get('path') or not item.get('supports') or not re.fullmatch('[a-f0-9]{64}', item.get('sha256', '')):
            raise ValueError('Evidence needs a path, SHA256 and supported claim')
    if not isinstance(record.get('cause_verified'), bool):
        raise ValueError('Mark whether the cause is verified')
    if record['state'] == 'verified_remotely':
        check = record.get('remote_verification') or {}
        if not check.get('evidence_path') or not check.get('criterion') or not check.get('observed_utc'):
            raise ValueError('Remote verification needs evidence, observation time and explicit criterion')
        if check['evidence_path'] not in [x['path'] for x in record['evidence']]:
            raise ValueError('Remote verification must cite hashed evidence')
    datetime.fromisoformat(record['recorded_utc'].replace('Z', '+00:00'))


def records(directory):
    result = {}
    for path in sorted(Path(directory).glob('E-*.r*.json')):
        row = json.loads(path.read_text(encoding='utf-8'))
        validate_record(row)
        if path.name != f"{row['eid']}.r{row['revision']:03d}.json":
            raise ValueError('Incident filename differs from identity')
        result.setdefault(row['eid'], []).append((path, row))
    for eid, values in result.items():
        values.sort(key=lambda pair: pair[1]['revision'])
        for index, (path, row) in enumerate(values):
            if row['revision'] != index + 1:
                raise ValueError('Incident revision gap or duplicate: ' + eid)
            expected = None if index == 0 else sha(values[index - 1][0])
            if row.get('previous_sha256') != expected:
                raise ValueError('Incident history hash differs: ' + eid)
    return result


def append(directory, record):
    validate_record(record)
    existing = records(directory).get(record['eid'], [])
    if record['revision'] != len(existing) + 1:
        raise ValueError('Append the next revision; never overwrite an incident')
    previous = sha(existing[-1][0]) if existing else None
    if record.get('previous_sha256') != previous:
        raise ValueError('Previous incident hash differs')
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record['eid']}.r{record['revision']:03d}.json"
    with path.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False); stream.write('\n')
    return path


def index(directory):
    return {'derived_utc': datetime.now(timezone.utc).isoformat(), 'incidents': [
        {'eid': eid, 'revision': items[-1][1]['revision'], 'title': items[-1][1]['title'],
         'state': items[-1][1]['state'], 'record': str(items[-1][0]), 'sha256': sha(items[-1][0])}
        for eid, items in sorted(records(directory).items())]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['append', 'index'])
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--record', type=Path)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    if args.command == 'append':
        if args.record is None:
            p.error('--record is required')
        print(append(args.directory, json.loads(args.record.read_text(encoding='utf-8'))))
    else:
        result = index(args.directory)
        if args.out:
            with args.out.open('x', encoding='utf-8') as stream:
                json.dump(result, stream, indent=2, ensure_ascii=False); stream.write('\n')
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
