""".. `.vcc` package constants and validation.

Deliberately stdlib-only (``tarfile``) so `vcc submit` can validate an existing
`.vcc` without importing anndata/scipy. ``prep`` imports the same constants, so
the writer and the validator can never drift apart.
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

PRED_MEMBER = "pred.h5ad.zst"

# Small JSON sidecar carrying the prediction's shape, written FIRST so it can be read
# from the first few KiB of the archive without touching the multi-GB payload.
#
# This is what lets the server size the scoring machine correctly. `nnz` decides the
# machine, and until now it only reached the server when the CLI happened to prep and
# submit in one invocation -- a pre-prepped `.vcc` carried no count, so the server
# escalated to its largest tier for 605 of 625 production jobs. The server can now
# recover an upper bound from the h5ad's own header (a 256 KiB ranged read), but this
# member gives it the EXACT figure for free.
#
# OPTIONAL, in both directions: archives written before this existed have no meta.json
# and must keep working, and nothing may fail because it is absent or malformed.
META_MEMBER = "meta.json"
META_SCHEMA = 1


class InvalidVccError(Exception):
    """The file is not a usable `.vcc` package."""


def validate_vcc(path: str | Path) -> None:
    """Raise :class:`InvalidVccError` unless ``path`` is a valid `.vcc`.

    A `.vcc` is a tar carrying the compressed prediction as ``pred.h5ad.zst``.
    Validation is exactly that: the member is present and not empty.

    There used to be a second member, ``watermark.txt``, holding the literal
    ``vcc-prep``, and both this check and the web UI's required it. It never
    established anything useful -- it was written by the same step that wrote the
    prediction, so it only confirmed that prep had run, which the presence of
    ``pred.h5ad.zst`` already says. Meanwhile it was an extra way for a genuine
    submission to be rejected (the UI matched on an 8-byte length, so any 8-byte
    file passed and a reworded watermark failed).

    Only non-emptiness is checked, deliberately -- no expected size. The
    compressed payload's length depends on the prediction, so any specific
    figure would be wrong for somebody. An archive that still carries the old
    watermark member validates fine; the member is simply ignored.
    """
    p = Path(path)
    if not p.exists():
        raise InvalidVccError(f"File not found: {p}")
    if not p.is_file():
        # Reject any non-regular file. A directory (notably one named *.vcc) passes
        # exists() with a nonzero st_size, then crashes tarfile.open with
        # IsADirectoryError — not a TarError, so it escaped as a raw traceback
        # (#402). FIFOs/sockets/device nodes are largely caught by the st_size == 0
        # check below, but a positive is_file() test closes the whole class in one
        # place (no new cross-module helper) and gives a clear message. is_file()
        # follows symlinks, so a symlink to a real .vcc still passes.
        detail = "is a directory" if p.is_dir() else "is not a regular file"
        raise InvalidVccError(
            f"'{p}' {detail}, not a .vcc file.\n"
            "Pass the .vcc file produced by `vcc prep`."
        )
    if p.stat().st_size == 0:
        raise InvalidVccError(f"File is empty: {p}")

    try:
        with tarfile.open(p, "r:*") as tar:
            try:
                member = tar.getmember(PRED_MEMBER)
            except KeyError:
                raise InvalidVccError(
                    f"'{p.name}' is not a valid .vcc: missing the prediction member "
                    f"({PRED_MEMBER}).\nRun `vcc prep` on your .h5ad to produce a .vcc."
                ) from None
            size = member.size
    except tarfile.TarError as exc:
        # tarfile reports every codec it tried; keep just the first line so the
        # user sees "not a valid archive", not a wall of codec errors.
        reason = str(exc).splitlines()[0].rstrip(":").strip()
        raise InvalidVccError(
            f"'{p.name}' is not a valid .vcc archive ({reason}).\n"
            "Run `vcc prep` on your .h5ad to produce one."
        ) from exc

    if size == 0:
        raise InvalidVccError(
            f"'{p.name}' contains an empty prediction ({PRED_MEMBER} is 0 bytes). "
            "Re-run `vcc prep` to regenerate it."
        )


def read_vcc_meta(path: str | Path) -> dict | None:
    """The `.vcc`'s ``meta.json``, or None when it has none / it is unusable.

    Cheap by construction: reads one small tar member and never touches the compressed
    prediction, so this costs a few KiB on a multi-GB archive.

    Returns None rather than raising for EVERY failure -- a missing member (any archive
    written before the member existed), malformed JSON, a hostile payload. The caller's
    fallback is simply to send no ``nnz``, which is exactly what it did before, and a
    submission must never fail because an optional hint could not be read.
    """
    try:
        with tarfile.open(path, "r:*") as tar:
            try:
                member = tar.getmember(META_MEMBER)
            except KeyError:
                return None
            # A `.vcc` is participant-controlled, so bound the read rather than
            # trusting the header: this member is a few hundred bytes and anything
            # claiming to be large is not ours.
            if not member.isfile() or member.size <= 0 or member.size > 64 * 1024:
                return None
            fh = tar.extractfile(member)
            if fh is None:
                return None
            data = json.loads(fh.read().decode("utf-8"))
    except Exception:
        # A bare `except` because the contract above is "never raise", and the typed
        # tuple this replaced did not honour it. `json.loads` raises RecursionError on
        # deeply nested input -- `json.loads("[" * 20000)` -- and RecursionError derives
        # from RuntimeError, not ValueError, so it escaped and `vcc submit` died with a
        # traceback on an archive whose prediction member was perfectly fine. A 64 KiB
        # member is ~65,000 nesting levels, far past the limit, and a truncated write
        # reaches it as easily as a hostile archive. The caller's fallback is to send no
        # nnz, which is what every older client already does.
        return None
    return data if isinstance(data, dict) else None


def nnz_from_vcc(path: str | Path) -> int | None:
    """The exact stored-nonzero count recorded by `vcc prep`, or None.

    None means "unknown", never "zero" -- the server then falls back to bounding it from
    the h5ad header, which is why a wrong answer here would be worse than no answer.
    """
    meta = read_vcc_meta(path)
    if not meta:
        return None
    # The version field only does its job if a reader consults it. A schema this build has
    # never heard of may redefine what ``nnz`` counts -- stored vs true nonzeros,
    # per-context counts, a change of units -- and participants do not upgrade, so the
    # readers that meet a schema-2 sidecar will be exactly these ones. Unknown means
    # "unknown", which is the already-correct fallback: the server bounds the count from
    # the h5ad header instead.
    schema = meta.get("schema")
    if isinstance(schema, bool) or not isinstance(schema, int):
        return None
    if not 1 <= schema <= META_SCHEMA:
        return None
    nnz = meta.get("nnz")
    # Reject anything that is not a plain positive int. `bool` is an int subclass in
    # Python and would sail through an isinstance check.
    if isinstance(nnz, bool) or not isinstance(nnz, int) or nnz <= 0:
        return None
    return nnz
