"""Compare one committed report tree with exact working bytes, without EOL conversion."""
import argparse
import hashlib
import subprocess
from percorso import HERE, ROOT, now, write_new


def main(commit, out):
    prefix = HERE.relative_to(ROOT).as_posix()
    records = subprocess.check_output(['git', 'ls-tree', '-rz', commit, '--', prefix], cwd=ROOT)
    checked = 0; mismatches = []
    for record in records.split(b'\0'):
        if not record: continue
        header, name = record.split(b'\t', 1); mode, kind, expected = header.split()
        if kind != b'blob': continue
        path = ROOT / name.decode('utf-8')
        if not path.is_file():
            mismatches.append(dict(path=name.decode('utf-8'), reason='missing worktree file')); continue
        digest = hashlib.sha1(('blob %d\0' % path.stat().st_size).encode())
        with path.open('rb') as source:
            for block in iter(lambda: source.read(1 << 20), b''): digest.update(block)
        checked += 1
        if digest.hexdigest() != expected.decode():
            mismatches.append(dict(path=name.decode('utf-8'), reason='worktree bytes differ from named commit'))
    if not checked: raise ValueError('empty report tree')
    write_new(out, dict(utc=now(), commit=commit, files_checked=checked, mismatches=mismatches,
        method='raw git blob SHA1 against exact worktree bytes; no newline conversion'))
    print(checked, 'committed files checked;', len(mismatches), 'working differences')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('commit'); parser.add_argument('out')
    args = parser.parse_args(); main(args.commit, args.out)
