"""Copy frozen t28 in bounded windows; never submit or overwrite an artifact.

The source handle closes after every 64 MiB window. A failed window is discarded
before any destination write. Resume is explicit and retains the entire partial.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

import direct_t28_submission as frozen

SIZE = 4161126400
SHA = '0d70ba92d68817b46383b11c53d513a41c85329230b9ff5524ac51f7bd110b32'
WINDOW = 64*1024**2
READ = 8*1024**2
RESERVE = 512*1024**2


def log(**values):
    print(json.dumps({'utc': datetime.now(timezone.utc).isoformat(), **values}), flush=True)


def disk_guard(volume, required):
    free = shutil.disk_usage(volume).free
    if free < required:
        raise OSError(f'Insufficient free disk: {free} bytes; need {required}')
    return free


def identity(path):
    stat = path.stat()
    return {'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns}


def read_window(source, offset, size, volume, reserve, *, opener=None, retries=3, retry_delay=1.):
    """Initial attempt plus at most three retries; destination is never touched."""
    opener = opener or (lambda path: path.open('rb'))
    for attempt in range(retries+1):
        buffer = bytearray()
        try:
            disk_guard(volume, reserve+size)
            with opener(source) as stream:
                stream.seek(offset)
                while len(buffer) < size:
                    block = stream.read(min(READ, size-len(buffer)))
                    if not block:
                        raise EOFError(f'Short source read at {offset+len(buffer)}')
                    buffer.extend(block)
                    disk_guard(volume, reserve+size)
            return buffer
        except (OSError, EOFError) as exc:
            retryable = isinstance(exc, EOFError) or getattr(exc, 'errno', None) == 22
            if not retryable or attempt == retries:
                raise
            log(phase='retry_source_window', offset=offset, window_bytes=size,
                retry=attempt+1, maximum_retries=retries, error=repr(exc))
            time.sleep(retry_delay)
    raise AssertionError('Unreachable')


def copy_payload(source, partial, expected_size, expected_sha, source_identity,
                 volume, *, reserve=RESERVE, window=WINDOW, opener=None):
    """Append only; on any failure the partial remains for an explicit resume."""
    offset = partial.stat().st_size
    frozen.require(0 <= offset <= expected_size, 'Partial exceeds expected size')
    frozen.require(identity(source) == source_identity, 'Source identity changed before copy')
    disk_guard(volume, expected_size-offset+reserve+window)
    with partial.open('ab') as destination:
        while offset < expected_size:
            size = min(window, expected_size-offset)
            buffer = read_window(source, offset, size, volume, reserve, opener=opener)
            disk_guard(volume, reserve+size)
            written = destination.write(buffer)
            destination.flush()
            os.fsync(destination.fileno())
            frozen.require(written == size, 'Short destination write; preserve partial')
            offset += written
            free = disk_guard(volume, reserve)
            log(phase='copied_window', bytes=offset, total_bytes=expected_size,
                source_handle_closed=True, free_bytes=free)
    frozen.require(identity(source) == source_identity, 'Source identity changed after copy')
    digest, total = hashlib.sha256(), 0
    with partial.open('rb') as stream:
        while block := stream.read(READ):
            digest.update(block)
            total += len(block)
            disk_guard(volume, reserve)
    frozen.require(total == expected_size and digest.hexdigest() == expected_sha,
                   'Destination full SHA/size differs; partial preserved, never promoted')
    frozen.require(identity(source) == source_identity, 'Source changed during destination verification')
    return {'bytes': total, 'sha256': digest.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('G:/Il mio Drive/vcc2026/runs/lead_candidate_t28_2026-09-29_r2'))
    parser.add_argument('--destination', type=Path, default=Path('C:/Users/ferra/vcc2026-data/artifacts/t28_local_upload_r1'))
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    source, dest = args.source, args.destination
    frozen.require(source.is_absolute() and dest.is_absolute(), 'Absolute directories required')
    frozen.require(source.resolve() != dest.resolve() and source.resolve() not in dest.resolve().parents,
                   'Destination must be separate from source')
    frozen.require(dest.resolve() != frozen.REPO and frozen.REPO not in dest.resolve().parents,
                   'Large artifact must stay outside repository')
    documents, raw = frozen.load_metadata(source)
    expected, size, nnz = frozen.verify_metadata(documents)
    frozen.require((expected, size) == (SHA, SIZE), 'Not the frozen t28 archive')
    src = source/'prediction.vcc'
    original = identity(src)
    frozen.require(original['bytes'] == SIZE, 'Source size differs')
    volume = Path(dest.anchor)
    plan = {'source': str(src.resolve()), 'destination': str(dest.resolve()),
            'source_identity': original, 'expected_bytes': SIZE, 'expected_sha256': SHA,
            'window_bytes': WINDOW, 'read_bytes': READ, 'reserve_bytes': RESERVE,
            'metadata_sha256': {n: hashlib.sha256(b).hexdigest() for n,b in raw.items()},
            'copier_sha256': frozen.digest(__file__)}
    state = dest/'copy_state.json'
    partial, final = dest/'prediction.vcc.partial', dest/'prediction.vcc'
    if args.resume:
        frozen.require(dest.is_dir() and state.is_file() and partial.is_file(), 'No resumable partial/state')
        frozen.require(json.loads(state.read_text()) == plan, 'Frozen resume state/source differs')
    else:
        frozen.require(not dest.exists(), 'Destination exists; use --resume only for its frozen partial')
        disk_guard(volume, SIZE+RESERVE+WINDOW)
        dest.mkdir(parents=True)
        frozen.write(state, plan)
        with partial.open('xb'):
            pass
    frozen.require(not final.exists(), 'Final exists; never overwrite')
    start = partial.stat().st_size
    lock = dest/'copy.lock'
    # An interrupted process may leave this lock. Never silently break it.
    with lock.open('x') as handle:
        handle.write(str(os.getpid()))
    try:
        verified = copy_payload(src, partial, SIZE, SHA, original, volume)
        frozen.require(all((source/n).read_bytes() == b for n,b in raw.items()), 'Source metadata changed')
        # Metadata is copied only after the entire local payload passed SHA/size.
        for name, data in raw.items():
            target = dest/name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                frozen.require(target.read_bytes() == data, 'Existing local metadata differs')
            else:
                with target.open('xb') as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            frozen.require(target.read_bytes() == data, 'Local metadata readback differs')
        disk_guard(volume, RESERVE)
        frozen.require(identity(src) == original, 'Source changed before promotion')
        frozen.require(not final.exists(), 'Final appeared during copy')
        partial.rename(final)
        frozen.write(dest/'local_copy_complete.json', {
            'status': 'verified_local_copy_not_uploaded', 'file': verified,
            'resume_started_at_bytes': start, 'nnz': nnz, 'state_sha256': frozen.digest(state),
            'metadata_sha256': plan['metadata_sha256'], 'source_identity_after': identity(src),
            'utc': datetime.now(timezone.utc).isoformat()})
        log(phase='complete', destination=str(final), sha256=SHA, bytes=SIZE, uploaded=False)
    finally:
        lock.unlink()  # Remove only this process's transient cooperative lock.


if __name__ == '__main__':
    main()
