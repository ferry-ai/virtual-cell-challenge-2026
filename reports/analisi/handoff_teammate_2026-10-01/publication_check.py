"""Check new Git blobs and named handoff files, without printing credential contents."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PATTERNS = {
    'private_key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'github_token': re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    'aws_access_key': re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'openai_key': re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}\b'),
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--file', action='append', default=[])
    args = parser.parse_args()
    head = git('rev-parse', 'HEAD').decode().strip()
    objects = git('rev-list', '--objects', f'{args.base}..{head}').splitlines()
    ids = [line.split(b' ', 1)[0] for line in objects]
    metadata = subprocess.check_output(
        ['git', 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'],
        cwd=ROOT, input=b'\n'.join(ids)+b'\n')
    blobs = []
    for line in metadata.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1] == b'blob':
            blobs.append((parts[0], int(parts[2])))
    payload = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT,
                                     input=b'\n'.join(oid for oid, _ in blobs)+b'\n') if blobs else b''
    findings = []
    cursor = 0
    for oid, size in blobs:
        header_end = payload.index(b'\n', cursor)
        header = payload[cursor:header_end].split()
        if header != [oid, b'blob', str(size).encode()]:
            raise ValueError('Unexpected Git batch header')
        raw = payload[header_end+1:header_end+1+size]
        cursor = header_end+size+2
        for label, pattern in PATTERNS.items():
            if pattern.search(raw):
                findings.append({'object': oid.decode(), 'pattern': label})
    files = []
    for name in args.file:
        path = (ROOT/name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError(f'Not a repository file: {name}')
        raw = path.read_bytes()
        files.append({'path': name, 'bytes': len(raw)})
        for label, pattern in PATTERNS.items():
            if pattern.search(raw):
                findings.append({'path': name, 'pattern': label})
    result = {
        'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'base': args.base, 'head_before_handoff_commit': head,
        'commits': int(git('rev-list', '--count', f'{args.base}..{head}')),
        'new_blobs': len(blobs), 'new_blob_bytes': sum(size for _, size in blobs),
        'largest_blob_bytes': max((size for _, size in blobs), default=0),
        'blobs_over_100MB': [oid.decode() for oid, size in blobs if size > 100_000_000],
        'named_working_files': files, 'credential_pattern_findings': findings,
        'scope': 'Recognizable credential formats and sizes; not proof of absence of all confidential material.'}
    with args.out.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({key: result[key] for key in
                      ('head_before_handoff_commit', 'new_blobs', 'largest_blob_bytes',
                       'blobs_over_100MB', 'credential_pattern_findings')}, indent=2))


if __name__ == '__main__':
    main()
