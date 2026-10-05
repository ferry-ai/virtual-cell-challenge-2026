"""`vcc datasets` — list and download challenge reference data.

Backs requirement **P2** (fetch reference data with checksum verification and a
local cache) so contestants stop hand-downloading files from the web app.

The catalog is server-side and allowlisted; this module never constructs object
paths. Downloads go through a short-lived signed URL, streamed straight to disk
by :mod:`vcc.download` — these files reach several GB.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from vcc import api
from vcc.download import (
    ChecksumMismatch,
    DownloadError,
    download_file,
    part_path,
    verify_file,
)
from vcc.lock import LockHeldError, SubmitLock

EventCallback = Callable[..., None]


class DatasetError(Exception):
    """A user-facing datasets failure."""


@dataclass
class DownloadOutcome:
    dataset_id: str
    filename: str
    path: str
    size_bytes: int
    verified_with: str | None
    checksum_ok: bool | None
    skipped: bool = False          # already present and verified
    resumed_from: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "filename": self.filename,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "verified_with": self.verified_with,
            "checksum_ok": self.checksum_ok,
            "skipped": self.skipped,
            "resumed_from": self.resumed_from,
            "notes": self.notes,
        }


def _emit(on_event: EventCallback | None, kind: str, **data: Any) -> None:
    if on_event:
        on_event(kind, **data)


def default_dest_dir() -> Path:
    """Where downloads land by default: ``$VCC_DATA_DIR`` or the cwd."""
    override = os.environ.get("VCC_DATA_DIR")
    return Path(override).expanduser() if override else Path.cwd()


def list_datasets(endpoint: str, token: str) -> list[dict[str, Any]]:
    """Return the catalog, or raise :class:`DatasetError` with a clear message."""
    try:
        body = api.list_datasets(endpoint, token)
    except api.ApiError as exc:
        raise DatasetError(str(exc)) from exc
    datasets = body.get("datasets")
    if not isinstance(datasets, list):
        raise DatasetError("The server returned an unexpected dataset catalog.")
    return datasets


def download_dataset(
    endpoint: str,
    token: str,
    dataset_id: str,
    *,
    dest_dir: Path | str | None = None,
    output: Path | str | None = None,
    force: bool = False,
    on_event: EventCallback | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> DownloadOutcome:
    """Download one dataset, resuming and verifying.

    - an existing, checksum-verified file is left alone unless ``force``
    - an interrupted ``.part`` file is resumed
    - the signed URL is re-minted automatically if it expires mid-transfer
    """
    _emit(on_event, "resolve", dataset_id=dataset_id)
    try:
        info = api.get_dataset_download(endpoint, token, dataset_id)
    except api.ApiError as exc:
        raise DatasetError(str(exc)) from exc

    filename = info.get("filename") or dataset_id
    # The server-supplied filename is untrusted. When we join it into the download
    # directory (no explicit -o/--output), a value like "../../x" or "/abs/path"
    # would let a malicious/compromised server write outside the chosen dir. Require
    # a bare, separator-free name so the write always stays inside dest_dir.
    if (
        filename in ("", ".", "..")
        or "/" in filename
        or "\\" in filename
        or os.path.isabs(filename)
    ):
        raise DatasetError(f"Server returned an unsafe dataset filename: {filename!r}")
    size_bytes = info.get("size_bytes")
    crc32c = info.get("crc32c")
    md5 = info.get("md5")
    url = info.get("url")
    if not url:
        raise DatasetError("The server did not return a download link for that dataset.")

    target = Path(output) if output else Path(dest_dir or default_dest_dir()) / filename
    if target.is_dir():
        # e.g. a directory already exists with the dataset's filename; verifying
        # or writing it would raise IsADirectoryError deep in the download.
        raise DatasetError(
            f"Cannot write to '{target}' — it is a directory. "
            "Pass -o/--output with a file path, or choose a different -d/--dir."
        )
    # Single-flight, keyed by the resolved target. Two `vcc datasets download`
    # runs for the same file share one `<target>.part`, and there was no guard:
    # the second run opens the .part for append, the first finalizes with
    # os.replace, and the second's writes then follow the RENAMED inode. It
    # streams happily to 100% and dies at finalize on a path that no longer
    # exists — surfacing as "Could not write '<target>': [Errno 2] No such file
    # or directory: '<target>.part'" (#383), with a corrupt file left behind that
    # only the *next* run's checksum catches. Easy to hit: interrupt a download
    # and re-run before the first process has actually exited.
    lock = SubmitLock(
        _download_lock_path(target),
        label="vcc datasets download",
        advice=(
            "Two downloads of the same file would share one .part and corrupt it. "
            "Wait for it to finish, or use -o/--output to download somewhere else."
        ),
    )
    try:
        lock.acquire()
    except LockHeldError as exc:
        raise DatasetError(str(exc)) from exc

    try:
        return _download_locked(
            endpoint, token, dataset_id,
            target=target, filename=filename, url=url, size_bytes=size_bytes,
            crc32c=crc32c, md5=md5, force=force, on_event=on_event, progress=progress,
        )
    finally:
        lock.release()


def _download_lock_path(target: Path) -> Path:
    """Lock file for one download target, under the config dir (never beside the
    data, which may be a read-only or shared mount).

    ``resolve()`` unconditionally, so every spelling of the same file maps to one
    key: it normalizes ``..``/``.`` segments and follows symlinks, which
    ``absolute()`` does not. Keying on ``absolute()`` for relative inputs let
    ``-d sub/..`` and ``-d .`` produce two different locks for one file — two
    runs would both acquire, and the shared ``.part`` corruption this lock exists
    to prevent would happen anyway. Non-strict by default, so a target that does
    not exist yet (the normal case) resolves fine.
    """
    from vcc.config import config_dir

    key = hashlib.sha256(str(target.resolve()).encode()).hexdigest()[:16]
    return config_dir() / "locks" / f"download-{key}.lock"


def _download_locked(
    endpoint: str,
    token: str,
    dataset_id: str,
    *,
    target: Path,
    filename: str,
    url: str,
    size_bytes: int | None,
    crc32c: str | None,
    md5: str | None,
    force: bool,
    on_event: EventCallback | None,
    progress: Callable[[int, int], None] | None,
) -> DownloadOutcome:
    """The download itself, with the target lock already held."""
    notes: list[str] = []
    if not crc32c and not md5:
        # Not fatal, but the user should know the bytes went unverified.
        notes.append("the server advertised no checksum, so the file could not be verified")

    # Already downloaded? Verify rather than trust the filename.
    if target.exists() and not force:
        _emit(on_event, "verify_existing", path=str(target))
        algorithm, ok = verify_file(target, crc32c=crc32c, md5=md5)
        if ok is True:
            return DownloadOutcome(
                dataset_id=dataset_id, filename=filename, path=str(target),
                size_bytes=target.stat().st_size, verified_with=algorithm,
                checksum_ok=True, skipped=True,
                notes=notes + ["already present and checksum-verified; nothing to do"],
            )
        if ok is False:
            notes.append("an existing file failed verification and was re-downloaded")
            _emit(on_event, "existing_corrupt", path=str(target))
        else:
            # Nothing to compare against; don't silently clobber the user's file.
            if size_bytes and target.stat().st_size == size_bytes:
                return DownloadOutcome(
                    dataset_id=dataset_id, filename=filename, path=str(target),
                    size_bytes=target.stat().st_size, verified_with=None,
                    checksum_ok=None, skipped=True,
                    notes=notes + [
                        "already present with the expected size (unverified — no checksum "
                        "available); pass --force to download again"
                    ],
                )

    def refresh() -> str:
        """Re-mint the signed URL — it lives ~3 h, less than a big download may take.

        Called from deep inside download_file, so it must raise DatasetError like
        every other path here: an ApiError escaping (expired token, server down
        mid-download) would surface as a traceback rather than a clean failure,
        since the CLI only catches DatasetError.
        """
        _emit(on_event, "url_refresh", dataset_id=dataset_id)
        try:
            fresh = api.get_dataset_download(endpoint, token, dataset_id)
        except api.ApiError as exc:
            raise DatasetError(
                f"The download link expired and could not be renewed: {exc}"
            ) from exc
        new_url = fresh.get("url")
        if not new_url:
            raise DatasetError("The server did not return a fresh download link.")
        return new_url

    existing_part = part_path(target)
    if existing_part.exists() and not force:
        _emit(on_event, "resume", path=str(existing_part), bytes=existing_part.stat().st_size)

    _emit(on_event, "download_start", filename=filename, size_bytes=size_bytes, path=str(target))
    try:
        result = download_file(
            url,
            target,
            size_bytes=size_bytes,
            crc32c=crc32c,
            md5=md5,
            progress=progress,
            refresh_url=refresh,
            resume=not force,
        )
    except ChecksumMismatch as exc:
        raise DatasetError(str(exc)) from exc
    except DownloadError as exc:
        raise DatasetError(str(exc)) from exc
    except OSError as exc:
        # Permission denied, disk full, a read-only mount: the CLI only catches
        # DatasetError, so an OSError here would surface as a traceback.
        raise DatasetError(f"Could not write '{target}': {exc}") from exc

    return DownloadOutcome(
        dataset_id=dataset_id,
        filename=filename,
        path=str(result.path),
        size_bytes=result.size_bytes,
        verified_with=result.verified_with,
        checksum_ok=result.checksum_ok,
        resumed_from=result.resumed_from,
        notes=notes,
    )
