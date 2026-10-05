"""GCS resumable upload for `vcc submit`.

Speaks the GCS resumable protocol directly against the session URI minted by the
frontend, so the CLI needs no Google credentials and no `google-cloud-storage`
dependency — the signed session URI *is* the capability.

Protocol (matching the web UI's contract):
- ``PUT`` each chunk with ``Content-Range: bytes {start}-{end}/{total}``
- ``308`` means "committed so far"; the ``Range`` response header gives the last
  committed byte, which is the authoritative resume point
- ``200``/``201`` completes the upload and returns the object resource JSON,
  including ``md5Hash`` — which we compare against the local digest so a silently
  corrupted upload can't be marked ready for scoring.
"""

from __future__ import annotations

import base64
import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import httpx

# 5 MiB, matching the web UI. Must be a multiple of 256 KiB per the GCS protocol.
CHUNK_SIZE = 5 * 1024 * 1024
_CHUNK_MULTIPLE = 256 * 1024

MAX_RETRIES = 6
UPLOAD_TIMEOUT = 300.0
# Transient conditions worth retrying; everything else fails fast.
_RETRY_STATUS = frozenset({408, 429, 500, 502, 503, 504})


class UploadError(Exception):
    """The upload could not be completed."""


@dataclass
class UploadResult:
    bytes_sent: int
    md5_local: str
    md5_remote: str | None
    verified: bool
    response: dict[str, Any]


ProgressCallback = Callable[[int, int], None]  # (bytes_done, total)


def file_md5_base64(path: str | Path, *, block: int = 1024 * 1024) -> str:
    """Base64-encoded MD5 of a file — the form GCS reports in ``md5Hash``."""
    # usedforsecurity=False so this works on FIPS-enabled hosts, where a bare
    # hashlib.md5() raises. This only cross-checks the digest GCS reports.
    digest = hashlib.md5(usedforsecurity=False)  # noqa: S324
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(block), b""):
            digest.update(chunk)
    return base64.b64encode(digest.digest()).decode("ascii")


def _committed_offset(session_url: str, total: int, client: httpx.Client) -> int:
    """Ask GCS how much it has committed (``bytes */total``), for resume."""
    response = client.put(
        session_url,
        headers={"Content-Range": f"bytes */{total}"},
        content=b"",
        timeout=UPLOAD_TIMEOUT,
    )
    if response.status_code in (200, 201):
        return total  # already complete
    if response.status_code == 308:
        rng = response.headers.get("Range")
        if not rng:
            return 0  # nothing committed yet
        # Range: bytes=0-{last_byte_inclusive}
        try:
            return int(rng.split("-")[-1]) + 1
        except ValueError as exc:
            raise UploadError(f"Could not parse resume offset from Range header {rng!r}") from exc
    raise UploadError(
        f"Upload session is no longer usable (HTTP {response.status_code}). "
        "Start a new submission."
    )


def _committed_offset_with_retry(
    session_url: str,
    total: int,
    client: httpx.Client,
    *,
    max_retries: int,
    sleep: Callable[[float], None],
) -> int:
    """Query the committed offset, retrying transient failures with backoff.

    Used for the FIRST query, before any chunk has been sent. That one has no
    surrounding retry loop to fall back on, so a single blip here would abort an
    upload that had not yet moved a byte.
    """
    attempts = 0
    while True:
        try:
            return _committed_offset(session_url, total, client)
        except (httpx.HTTPError, UploadError) as exc:
            attempts += 1
            if attempts > max_retries:
                raise UploadError(
                    f"Could not start the upload after {max_retries} retries: {exc}. "
                    "Re-run with `--resume` to try again."
                ) from exc
            sleep(min(2 ** attempts, 30))


def _safe_committed_offset(session_url: str, total: int, client: httpx.Client, fallback: int) -> int:
    """Re-query the committed offset, falling back if the query itself fails.

    The offset query is a network call like any other, so it can fail transiently
    (a blip, a 503). Letting that propagate out of a retry handler would abort the
    whole upload from inside the code meant to recover it — so on failure we keep
    the last known offset and let the normal retry/backoff loop try again.
    """
    try:
        return _committed_offset(session_url, total, client)
    except (httpx.HTTPError, UploadError):
        return fallback


def upload_file(
    session_url: str,
    path: str | Path,
    *,
    chunk_size: int = CHUNK_SIZE,
    progress: ProgressCallback | None = None,
    max_retries: int = MAX_RETRIES,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> UploadResult:
    """Upload ``path`` to a GCS resumable session URI, resuming and retrying.

    Returns an :class:`UploadResult` including whether GCS's MD5 matched ours.
    """
    if chunk_size % _CHUNK_MULTIPLE != 0:
        raise ValueError(f"chunk_size must be a multiple of {_CHUNK_MULTIPLE} bytes")

    p = Path(path)
    total = p.stat().st_size
    if total == 0:
        raise UploadError(f"Refusing to upload an empty file: {p}")

    md5_local = file_md5_base64(p)
    owns_client = client is None
    client = client or httpx.Client(timeout=UPLOAD_TIMEOUT)

    try:
        # An existing session may already hold bytes (a resumed submit).
        offset = _committed_offset_with_retry(
            session_url, total, client, max_retries=max_retries, sleep=sleep
        )
        # Report the true starting offset first — including 0 on a fresh upload.
        # Skipping the offset==0 case let the progress renderer take a fresh
        # transfer's first committed chunk as its baseline (see progress.py's
        # `_start_done` fallback), so the summary read e.g.
        # "uploaded 46.1 MiB (resumed at 5.0 MiB of 51.1 MiB)" for an upload that
        # actually started from zero.
        if progress:
            progress(offset, total)

        final: httpx.Response | None = None
        attempts = 0

        with open(p, "rb") as fh:
            while offset < total:
                fh.seek(offset)
                chunk = fh.read(chunk_size)
                end = offset + len(chunk) - 1
                headers = {
                    "Content-Range": f"bytes {offset}-{end}/{total}",
                    "Content-Length": str(len(chunk)),
                }
                try:
                    response = client.put(session_url, headers=headers, content=chunk, timeout=UPLOAD_TIMEOUT)
                except httpx.HTTPError as exc:
                    attempts += 1
                    if attempts > max_retries:
                        raise UploadError(
                            f"Upload failed after {max_retries} retries: {exc}. "
                            f"Re-run with `--resume` to continue from {offset} bytes."
                        ) from exc
                    sleep(min(2 ** attempts, 30))
                    offset = _safe_committed_offset(session_url, total, client, offset)
                    if progress:
                        progress(offset, total)
                    continue

                if response.status_code in (200, 201):
                    offset = total
                    final = response
                    if progress:
                        progress(total, total)
                    break
                if response.status_code == 308:
                    attempts = 0  # progress made; reset the backoff budget
                    rng = response.headers.get("Range")
                    if rng:
                        try:
                            offset = int(rng.split("-")[-1]) + 1
                        except ValueError as exc:
                            raise UploadError(
                                f"Could not parse resume offset from Range header {rng!r}"
                            ) from exc
                    else:
                        # No Range on a 308 means GCS has NOT told us what it
                        # committed. Assuming the whole chunk landed can leave a
                        # gap in the object, so ask for the authoritative offset
                        # instead of guessing in either direction (guessing 0
                        # would needlessly re-send everything).
                        offset = _safe_committed_offset(session_url, total, client, 0)
                    if progress:
                        progress(offset, total)
                    continue
                if response.status_code in _RETRY_STATUS:
                    attempts += 1
                    if attempts > max_retries:
                        raise UploadError(
                            f"Upload failed after {max_retries} retries "
                            f"(last status {response.status_code}). Re-run with `--resume`."
                        )
                    sleep(min(2 ** attempts, 30))
                    offset = _safe_committed_offset(session_url, total, client, offset)
                    if progress:
                        progress(offset, total)
                    continue
                raise UploadError(
                    f"Upload rejected by storage (HTTP {response.status_code}). "
                    f"{response.text[:200]}"
                )

        payload: dict[str, Any] = {}
        if final is not None:
            try:
                body = final.json()
                if isinstance(body, dict):
                    payload = body
            except ValueError:
                payload = {}

        md5_remote = payload.get("md5Hash")
        # A resumed upload that was already complete returns no object body; treat
        # a missing remote digest as "unverified" rather than a mismatch.
        verified = bool(md5_remote) and md5_remote == md5_local
        if md5_remote and not verified:
            raise UploadError(
                "Upload completed but the checksum did not match "
                f"(local {md5_local}, storage {md5_remote}). The file may be corrupted in transit; "
                "please retry the submission."
            )

        return UploadResult(
            bytes_sent=total,
            md5_local=md5_local,
            md5_remote=md5_remote,
            verified=verified,
            response=payload,
        )
    finally:
        if owns_client:
            client.close()
