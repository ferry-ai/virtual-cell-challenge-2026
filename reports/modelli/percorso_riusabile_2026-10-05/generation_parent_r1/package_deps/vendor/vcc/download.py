"""Resumable, verified HTTP download for `vcc datasets download`.

These files are large (the training bundle is ~4.3 GB), so this streams to disk
in chunks, never buffering a whole file, and resumes an interrupted transfer with
a ``Range`` request against a ``.part`` file.

Two hazards specific to this endpoint (both called out by the server-side PR):

1. **Verify with crc32c, fall back to md5.** GCS omits ``md5Hash`` for composite
   (multipart-uploaded) objects — which the training zip is — so md5 is ``null``
   there. Preferring md5 would silently skip verification on the main download.
   crc32c is computed incrementally as bytes land, so a multi-GB file is verified
   without a second read.

2. **Signed URLs expire (3 h).** A resume attempted after expiry gets a 4xx from
   GCS, and retrying the stale URL can never succeed — the caller must mint a new
   one. ``refresh_url`` is that hook; expiry is treated as "get a fresh URL",
   distinct from a transient network error.
"""

from __future__ import annotations

import base64
import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import httpx

CHUNK_BYTES = 1024 * 1024      # 1 MiB read size while streaming
MAX_RETRIES = 6
CONNECT_TIMEOUT = 30.0
READ_TIMEOUT = 300.0
# GCS returns 400/403 for an expired or malformed signature.
_EXPIRED_STATUS = frozenset({400, 401, 403})
_RETRY_STATUS = frozenset({408, 429, 500, 502, 503, 504})

ProgressCallback = Callable[[int, int], None]
RefreshUrl = Callable[[], str]


class DownloadError(Exception):
    """The download could not be completed."""


class ChecksumMismatch(DownloadError):
    """The finished file did not match the checksum the server advertised."""


@dataclass
class DownloadResult:
    path: Path
    size_bytes: int
    resumed_from: int
    verified_with: str | None      # "crc32c" | "md5" | None
    checksum_ok: bool | None       # None when the server advertised neither


def _crc32c_factory():
    """Return a fresh incremental crc32c hasher, or None if unavailable.

    ``google-crc32c`` ships wheels with a C implementation and falls back to pure
    Python; either is fine here. If the import fails we degrade to md5-only
    verification rather than failing the download outright.
    """
    try:
        import google_crc32c
    except Exception:  # noqa: BLE001
        return None
    return google_crc32c.Checksum()


def _b64(digest: bytes) -> str:
    return base64.b64encode(digest).decode("ascii")


class _Hashers:
    """Computes crc32c and md5 incrementally as bytes stream past."""

    def __init__(self) -> None:
        self.crc = _crc32c_factory()
        # usedforsecurity=False so this still works on FIPS-enabled hosts, where a
        # bare hashlib.md5() raises. MD5 here only cross-checks GCS's own digest.
        self.md5 = hashlib.md5(usedforsecurity=False)  # noqa: S324

    def update(self, data: bytes) -> None:
        if self.crc is not None:
            self.crc.update(data)
        self.md5.update(data)

    @property
    def crc32c_b64(self) -> str | None:
        if self.crc is None:
            return None
        return _b64(self.crc.digest())

    @property
    def md5_b64(self) -> str:
        return _b64(self.md5.digest())


def part_path(target: Path) -> Path:
    return target.with_name(target.name + ".part")


def verify_file(
    path: Path, *, crc32c: str | None = None, md5: str | None = None
) -> tuple[str | None, bool | None]:
    """Verify an existing file. Returns (algorithm_used, ok).

    Prefers crc32c because md5 is absent for composite GCS objects. Returns
    ``(None, None)`` when neither checksum is available to compare against.
    """
    if not crc32c and not md5:
        return None, None

    hashers = _Hashers()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK_BYTES), b""):
            hashers.update(chunk)

    if crc32c and hashers.crc32c_b64 is not None:
        return "crc32c", hashers.crc32c_b64 == crc32c
    if md5:
        return "md5", hashers.md5_b64 == md5
    # crc32c advertised but no hasher available and no md5 to fall back to.
    return None, None


def download_file(
    url: str,
    target: Path | str,
    *,
    size_bytes: int | None = None,
    crc32c: str | None = None,
    md5: str | None = None,
    progress: ProgressCallback | None = None,
    refresh_url: RefreshUrl | None = None,
    max_retries: int = MAX_RETRIES,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
    resume: bool = True,
) -> DownloadResult:
    """Stream ``url`` to ``target``, resuming and verifying.

    Writes to ``<target>.part`` and renames on success, so a partial file is never
    mistaken for a complete one.
    """
    target = Path(target)
    part = part_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    offset = part.stat().st_size if (resume and part.exists()) else 0
    if not resume and part.exists():
        part.unlink()

    # A resumed transfer can't reuse the earlier run's rolling hash, so verify by
    # re-reading at the end; a fresh transfer hashes as it streams (one pass).
    hashers = _Hashers() if offset == 0 else None
    resumed_from = offset
    owns_client = client is None
    client = client or httpx.Client(
        timeout=httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT),
        # Storage providers and CDNs redirect; without this a 302 would be
        # written to disk as the "file" and then fail the checksum.
        follow_redirects=True,
    )
    attempts = 0
    # Bound URL re-minting. If the storage provider keeps rejecting freshly signed
    # URLs (clock skew, misconfigured signer), refreshing forever would hammer our
    # own API in a tight loop and never succeed.
    refreshes = 0
    MAX_REFRESHES = 3
    # Guards against spinning forever when the server keeps returning a
    # successful-but-empty body (e.g. it advertised a larger size than it
    # actually serves, or a proxy truncates). An error beats an infinite hang.
    stalls = 0
    MAX_STALLS = 3

    # Report the starting offset up front so a renderer knows where this run
    # actually began (0 for a fresh download, >0 for a resume) rather than
    # inferring it from the first chunk that lands.
    if progress:
        progress(offset, size_bytes or 0)

    try:
        while True:
            if size_bytes is not None and offset >= size_bytes and size_bytes > 0:
                break

            # Remember where this attempt started so a connection that dropped
            # mid-transfer still counts as progress (see the except below).
            offset_at_attempt_start = offset

            headers: dict[str, str] = {}
            if offset:
                headers["Range"] = f"bytes={offset}-"

            try:
                with client.stream("GET", url, headers=headers) as response:
                    if response.status_code in _EXPIRED_STATUS:
                        response.read()
                        if refresh_url is None:
                            raise DownloadError(
                                f"The download link was rejected (HTTP {response.status_code}); "
                                "it has most likely expired. Re-run the command to get a fresh link."
                            )
                        refreshes += 1
                        if refreshes > MAX_REFRESHES:
                            raise DownloadError(
                                f"The download link was rejected (HTTP {response.status_code}) "
                                f"even after {MAX_REFRESHES} fresh links. This looks like a "
                                "server-side signing problem rather than an expiry — please report it."
                            )
                        url = refresh_url()
                        continue  # retry immediately with the new URL
                    if response.status_code in _RETRY_STATUS:
                        response.read()
                        attempts += 1
                        if attempts > max_retries:
                            raise DownloadError(
                                f"Download failed after {max_retries} retries "
                                f"(last status {response.status_code}). Re-run to resume."
                            )
                        sleep(min(2 ** attempts, 30))
                        continue
                    if response.status_code not in (200, 206):
                        response.read()
                        raise DownloadError(
                            f"Download failed with HTTP {response.status_code}."
                        )
                    # A server that ignores Range replies 200 with the whole body;
                    # start over rather than appending a duplicate prefix.
                    if offset and response.status_code == 200:
                        offset = 0
                        resumed_from = 0
                        hashers = _Hashers()
                        part.unlink(missing_ok=True)

                    total = size_bytes
                    if total is None:
                        length = response.headers.get("Content-Length")
                        if length and length.isdigit():
                            total = offset + int(length)

                    mode = "ab" if offset else "wb"
                    before = offset
                    with open(part, mode) as fh:
                        for chunk in response.iter_bytes(CHUNK_BYTES):
                            if not chunk:
                                continue
                            fh.write(chunk)
                            if hashers is not None:
                                hashers.update(chunk)
                            offset += len(chunk)
                            if progress:
                                progress(offset, total or offset)
                    attempts = 0  # a completed body resets the retry budget

                    if offset == before:
                        stalls += 1
                        if stalls >= MAX_STALLS:
                            raise DownloadError(
                                f"The server stopped sending data at {offset} bytes but said the "
                                f"file is {size_bytes} bytes. Its size metadata may be wrong, or "
                                "the transfer is being truncated."
                            )
                    else:
                        stalls = 0
            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                # A 4.3 GB download over a flaky link can drop many times while
                # still advancing every time. Only count an attempt as "failed"
                # if it moved nothing — otherwise a long, healthy-but-lossy
                # transfer would exhaust the budget and give up mid-file.
                if offset > offset_at_attempt_start:
                    attempts = 0
                else:
                    attempts += 1
                if attempts > max_retries:
                    raise DownloadError(
                        f"Download failed after {max_retries} retries: {exc}. Re-run to resume."
                    ) from exc
                sleep(min(2 ** attempts, 30))
                offset = part.stat().st_size if part.exists() else 0
                hashers = None  # rolling hash is no longer trustworthy
                continue

            if size_bytes is None or offset >= size_bytes:
                break

        # The .part must still be there. It can vanish under us if something else
        # finalized the same download (renaming it onto the target) while this run
        # was mid-stream — our writes then follow the renamed inode and this path
        # is gone. `vcc datasets download` now takes a per-target lock so that
        # can't happen, but a hand-deleted .part or a second tool would hit it,
        # and the raw FileNotFoundError read as a nonsense "Could not write
        # <target>: No such file or directory: <target>.part" (#383).
        # EAFP, not exists()-then-stat(): the thing being guarded against IS a
        # concurrent rename, so a check-then-use pair has a window in which the
        # file can vanish between the two calls and the raw FileNotFoundError
        # escapes anyway.
        try:
            actual = part.stat().st_size
        except FileNotFoundError as exc:
            raise DownloadError(
                f"The partial download '{part.name}' disappeared before it could be "
                "finalized — another download of the same file was probably running. "
                "Re-run the command to download it cleanly."
            ) from exc
        if size_bytes is not None and actual != size_bytes:
            raise DownloadError(
                f"Downloaded {actual} bytes but the server said the file is {size_bytes} bytes. "
                "Re-run to resume or re-download."
            )

        # --- verify (crc32c first — md5 is null for composite objects) ---
        algorithm: str | None = None
        ok: bool | None = None
        if crc32c or md5:
            if hashers is not None:
                if crc32c and hashers.crc32c_b64 is not None:
                    algorithm, ok = "crc32c", hashers.crc32c_b64 == crc32c
                elif md5:
                    algorithm, ok = "md5", hashers.md5_b64 == md5
            else:
                algorithm, ok = verify_file(part, crc32c=crc32c, md5=md5)

        if ok is False:
            part.unlink(missing_ok=True)
            raise ChecksumMismatch(
                f"{algorithm} checksum mismatch — the downloaded file is corrupt, so it was "
                "discarded. Re-run the command to download again."
            )

        os.replace(part, target)
        return DownloadResult(
            path=target,
            size_bytes=actual,
            resumed_from=resumed_from,
            verified_with=algorithm,
            checksum_ok=ok,
        )
    finally:
        if owns_client:
            client.close()
