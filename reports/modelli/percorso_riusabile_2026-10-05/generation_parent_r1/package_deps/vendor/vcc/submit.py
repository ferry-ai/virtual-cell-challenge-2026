"""End-to-end `vcc submit` orchestration.

Mirrors the web submission flow (requirements §5.4) against the CLI edge:

1. validate locally (run ``prep`` if handed a raw ``.h5ad``) — catch what the
   server would reject before uploading. **A ``.vcc``'s PREDICTION is checked as a
   CONTAINER only**: ``validate_vcc`` confirms a non-empty ``pred.h5ad.zst`` member
   is present and never decompresses it. So a pre-prepped ``.vcc`` reaches scoring
   without its contents being seen locally — the gene set, contexts, target
   labels and per-perturbation cell counts are checked by ``prep`` at the time
   the ``.vcc`` was built, or else server-side. (This said "verify the
   watermark", describing a member that was dropped in #379.)
   The one thing read out of the archive is ``meta.json``, a few hundred bytes at
   the front recording the prediction's shape. It is passed to the launch call,
   where ``nnz`` selects the scoring machine; it is optional in both directions and
   an absent or unreadable one simply means the server sizes from the h5ad header.
2. daily-limit pre-check, so a rate-limited user fails fast instead of after a
   multi-GB upload
3. ``POST /api/cli/submissions`` — creates the entry and mints the resumable
   upload URL in one call
4. resumable chunked upload straight to GCS, with MD5 verification
5. ``PUT …/status`` → ``launching``
6. ``POST …/launch`` → triggers the scoring job

If a step after entry creation fails, the entry is marked ``failed`` with the
reason so it does not sit in ``uploading`` and block the team's next submission
— **except when the launch outcome is unknown**. A 5xx from step 6 does not tell
us whether Batch created the job, and recording ``failed`` for a job that is in
fact running is worse than leaving the entry in ``launching``: it is a lie the
rest of the system believes (it releases the one-in-flight guard, so a second
submission is accepted, and the two then race — see #384). An entry stuck in
``launching`` is cleared by the datastore's own staleness window instead, so the
team is not locked out either way.

Presentation is the caller's job: progress is reported through ``on_event`` so
the CLI can render a TTY progress bar and ``--json`` stays clean.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from vcc import api
from vcc._scores import SCORE_KEYS
from vcc.upload import UploadError, upload_file
from vcc.vccfile import InvalidVccError, nnz_from_vcc, validate_vcc

# The submission states that mean "still in progress", mirroring the datastore's
# own in-progress guard (leaderboard.py: uploading/launching/pending + scoring).
# Defined as the BLOCKING set rather than a terminal set on purpose: `published`,
# `failed` and `hidden_admin` are all done, and an unrecognised status must not
# wedge a user out of submitting — the server's 409 remains the real guarantee.
# `pending` is the legacy alias for `uploading`.
IN_PROGRESS_STATES = frozenset({"uploading", "launching", "pending", "scoring"})

# Known finished states. `hidden_admin` is an admin-moderation state applied to a
# PUBLISHED entry when a user is banned; the server does not treat it as holding a
# submission slot, so neither may we — otherwise a banned-then-unbanned user could
# never submit again. `superseded` is a scored-but-off-the-board terminal state
# for a submission that finished AFTER a newer one from the same team already
# published (the server keeps only the newest on the board); it is done, so
# `--wait` must stop on it rather than poll forever.
DONE_STATES = frozenset({"published", "failed", "hidden_admin", "superseded"})


def is_in_progress(status: object) -> bool:
    """True only for a known still-running state."""
    return isinstance(status, str) and status in IN_PROGRESS_STATES


def is_done(status: object) -> bool:
    """True only for a KNOWN finished state.

    A status this CLI version doesn't recognise is deliberately neither: we won't
    block on it (the server's 409 is the real guarantee) and we won't declare it
    finished (that would end `--wait` early or discard live local state).
    """
    return isinstance(status, str) and status in DONE_STATES


DEFAULT_POLL_INTERVAL = 5.0

EventCallback = Callable[..., None]


class SubmitError(Exception):
    """A user-facing submission failure."""


@dataclass
class SubmitResult:
    entry_id: str
    file_path: str
    model_name: str
    is_final: bool
    bytes_uploaded: int
    md5_verified: bool
    job_name: str | None = None
    prepared_from: str | None = None
    final_status: str | None = None
    scores: dict[str, Any] = field(default_factory=dict)
    error_info: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "file_path": self.file_path,
            "model_name": self.model_name,
            "is_final": self.is_final,
            "bytes_uploaded": self.bytes_uploaded,
            "md5_verified": self.md5_verified,
            "job_name": self.job_name,
            "prepared_from": self.prepared_from,
            "final_status": self.final_status,
            **({"scores": self.scores} if self.scores else {}),
            **({"error_info": self.error_info} if self.error_info else {}),
        }


def _emit(on_event: EventCallback | None, kind: str, **data: Any) -> None:
    if on_event:
        on_event(kind, **data)


def prepare_input(
    path: str,
    *,
    genes: str | None,
    perts: str | None = None,
    verify_targets: bool = True,
    check_cell_counts: bool = True,
    on_event: EventCallback | None = None,
    force: bool = False,
) -> tuple[str, str | None, int | None]:
    """Return (vcc_path, prepared_from, nnz).

    ``nnz`` is the prediction's nonzero count. It comes from this call when we prep the
    file, and otherwise from the ``.vcc``'s own ``meta.json`` -- a few hundred bytes at
    the front of the archive, so reading it costs nothing and does NOT mean decompressing
    the multi-GB payload.

    That second source is why this used to return None for every pre-prepped ``.vcc``,
    which is the common `vcc prep` then `vcc submit` flow: with no count the launch path
    provisions the largest machine, and 605 of 625 production jobs took one they did not
    need. Archives written by an older CLI still have no ``meta.json`` and still return
    None; the server bounds the count from the h5ad header in that case, so an old client
    is sized correctly too, just less precisely.

    A ``.vcc`` is validated and used as-is. A ``.h5ad`` is run through prep first
    (Q2: implicit, with a log line), which requires a gene list — and, since prep
    verifies target labels by default, the official ``pert_counts.csv`` via
    ``perts`` (or ``verify_targets=False`` to skip that check).
    """
    p = Path(path)
    if not p.exists():
        raise SubmitError(f"File not found: {p}")

    suffix = p.suffix.lower()  # .VCC / .H5AD are the same file to us
    if suffix == ".vcc":
        try:
            validate_vcc(p)
        except InvalidVccError as exc:
            raise SubmitError(str(exc)) from exc
        # Best-effort: None here is not an error, it just means the server sizes from
        # the h5ad header instead. Never let an unreadable hint fail a submission.
        return str(p), None, nnz_from_vcc(p)

    if suffix == ".h5ad":
        if not genes:
            raise SubmitError(
                f"'{p.name}' is a raw .h5ad, so it must be prepped first. Pass -g/--genes "
                "GENES.csv and --perts pert_counts.csv (both from `vcc datasets download "
                "controls`) to prep it automatically, or run `vcc prep` yourself and submit "
                "the resulting .vcc."
            )
        # Fail up front, BEFORE reading the (multi-GB) .h5ad, if prep would reject
        # for a missing perturbation list — otherwise the user waits through a full
        # read only to be told what's missing (a two-round-trip footgun).
        if verify_targets and not perts:
            raise SubmitError(
                f"'{p.name}' is a raw .h5ad and prep verifies target labels by default, so it "
                "also needs the official perturbation list. Pass --perts pert_counts.csv (from "
                "`vcc datasets download controls`), or --no-verify-targets to skip that check."
            )
        _emit(on_event, "prep_start", input=str(p))
        from vcc import prep as prep_mod  # lazy: anndata only when actually prepping

        try:
            result = prep_mod.run_prep(
                input_path=str(p),
                genes_path=genes,
                perts_path=perts,
                verify_targets=verify_targets,
                check_cell_counts=check_cell_counts,
                force=force,
            )
        except prep_mod.PrepError as exc:
            raise SubmitError(f"Prep failed, so nothing was submitted:\n{exc}") from exc
        _emit(on_event, "prep_done", output=result.output, normalization=result.normalization)
        return str(result.output), str(p), result.nnz

    raise SubmitError(
        f"Unsupported file type '{p.suffix or p.name}'. Submit a .vcc, or a .h5ad "
        "with -g/--genes and --perts so it can be prepped."
    )


def check_no_inflight(
    endpoint: str,
    token: str,
    *,
    pending: dict[str, Any],
    on_event: EventCallback | None = None,
    clear_resume: Callable[[str], None] | None = None,
) -> None:
    """Refuse to start a new submission while a previous one is still live.

    ``pending`` is this profile's locally-recorded in-flight uploads. Each is
    checked against the **server's** current state rather than trusted blindly:

    - still non-terminal -> refuse, and point at ``--resume`` / ``vcc status``
    - terminal, or gone (404) -> stale local bookkeeping; clear it and continue

    This is a courtesy check that produces a good error message. The real
    guarantee is the datastore's per-team in-progress guard (409), which the CLI
    surfaces if this check is somehow bypassed.
    """
    for entry_id in list(pending):
        try:
            entry = api.get_submission(endpoint, token, entry_id)
        except api.ApiError as exc:
            if exc.code == "not_found" or exc.status == 404:
                if clear_resume:
                    clear_resume(entry_id)
                continue
            # Can't tell (network/server problem) — don't block the user on it.
            _emit(on_event, "inflight_check_skipped", entry_id=entry_id, reason=str(exc))
            continue

        status = entry.get("status")
        if not is_in_progress(status):
            # Done (published/failed/hidden_admin) or an unrecognised status:
            # either way it isn't holding a slot, so drop the local record.
            if clear_resume and is_done(status):
                clear_resume(entry_id)
            continue

        # Advertise `vcc cancel` for the statuses where it can free the slot: an
        # uploading/pending entry always, and a `launching` one (its scoring job can
        # be cancelled while still queued). A `scoring` entry's job is already
        # running and can't be stopped, so pointing there would just send the user to
        # a command that tells them to wait.
        if status in ("uploading", "pending", "launching"):
            cancel_hint = (
                f"\n  • abandon it (frees the slot; doesn't use a daily submission): "
                f"vcc cancel {entry_id}"
            )
        else:
            cancel_hint = ""
        raise SubmitError(
            f"You already have a submission in progress: {entry_id} (status: {status}).\n"
            "Your team is allowed one submission in progress at a time, so this one was "
            "not started.\n"
            f"  • check on it:      vcc status {entry_id} --wait\n"
            "  • finish an interrupted upload: vcc submit --resume"
            + cancel_hint
        )


def poll_until_terminal(
    endpoint: str,
    token: str,
    entry_id: str,
    *,
    interval: float = DEFAULT_POLL_INTERVAL,
    timeout: float | None = None,
    on_event: EventCallback | None = None,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Poll a submission until it reaches a terminal state (or the timeout)."""
    started = now()
    last_status: str | None = None
    while True:
        try:
            entry = api.get_submission(endpoint, token, entry_id)
        except api.ApiError as exc:
            # Scoring can run for an hour; a blip or a 502 partway through must
            # not destroy a `--wait`. Terminal client errors (bad/revoked token,
            # entry gone) can never resolve by waiting, so those still raise.
            if exc.status in (400, 401, 403, 404):
                raise
            if timeout is not None and (now() - started) >= timeout:
                raise
            _emit(on_event, "poll_retry", reason=str(exc))
            sleep(interval)
            continue
        status = entry.get("status")
        if status != last_status:
            _emit(on_event, "status", status=status, entry=entry)
            last_status = status
        if is_done(status):
            return entry
        if timeout is not None and (now() - started) >= timeout:
            _emit(on_event, "wait_timeout", status=status)
            return entry
        sleep(interval)


_GCS_UPLOAD_HOST = "storage.googleapis.com"


def _validated_resume(resume: dict[str, Any]) -> tuple[str, str, str, str]:
    """Validate an UNTRUSTED resume record and return (entry_id, upload_url,
    file_path, local_path).

    ``state.json`` is 0600 but not keychain-protected, and its own docstring treats
    it as non-secret -- a shared/NFS HOME, a synced dotfile, or a sandboxed
    dependency can write it. On ``--resume`` the upload PUTs local bytes straight to
    ``upload_url`` with no other gate, so a poisoned record is a file-exfiltration /
    SSRF primitive (issue #422). The whole record is attacker-controlled in that
    threat model, so cross-checking its fields against each other is useless; instead
    re-establish an invariant the server guarantees but the file does not -- the
    upload URL is always an https Google Cloud Storage resumable URI. Plain http (the
    cleartext loopback exfil PoC) and any non-GCS host are refused here. The caller
    separately re-checks that ``local_path`` is a real ``.vcc`` via ``validate_vcc``,
    so the upload cannot be aimed at ``/etc/hosts`` or any non-submission file.
    """

    def _req_str(key: str) -> str:
        value = resume.get(key)
        if not isinstance(value, str) or not value:
            raise SubmitError(
                "Cannot resume: the saved upload record is incomplete or corrupt "
                f"(missing or invalid '{key}'). Start a new `vcc submit`."
            )
        return value

    entry_id = _req_str("entry_id")
    upload_url = _req_str("upload_url")
    file_path = _req_str("file_path")
    local_path = _req_str("local_path")

    try:
        parsed = urlparse(upload_url)
        host = (parsed.hostname or "").lower()
    except ValueError as exc:
        raise SubmitError(
            "Cannot resume: the saved upload URL is not a valid URL. "
            "Start a new `vcc submit`."
        ) from exc
    if parsed.scheme != "https" or not (
        host == _GCS_UPLOAD_HOST or host.endswith("." + _GCS_UPLOAD_HOST)
    ):
        raise SubmitError(
            "Cannot resume: the saved upload URL is not an https Google Cloud Storage "
            "endpoint, which is the only kind vcc ever creates. Your state file may be "
            "corrupt or tampered with -- start a new `vcc submit`."
        )
    return entry_id, upload_url, file_path, local_path


def run_submit(
    *,
    endpoint: str,
    token: str,
    path: str,
    model_name: str,
    description: str | None = None,
    genes: str | None = None,
    perts: str | None = None,
    verify_targets: bool = True,
    check_cell_counts: bool = True,
    wait: bool = False,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    wait_timeout: float | None = None,
    on_event: EventCallback | None = None,
    force: bool = False,
    skip_limit_check: bool = False,
    resume: dict[str, Any] | None = None,
    pending_uploads: dict[str, Any] | None = None,
    save_resume: Callable[[str, dict[str, Any]], None] | None = None,
    clear_resume: Callable[[str], None] | None = None,
) -> SubmitResult:
    """Run the full submission flow and return a :class:`SubmitResult`."""
    if resume:
        # Continue a previously created entry: skip validation + create. state.json is
        # an UNTRUSTED source here, so re-validate the upload target rather than
        # trusting the record verbatim (#422).
        entry_id, upload_url, file_path, vcc_path = _validated_resume(resume)
        model_name = resume.get("model_name", model_name)
        is_final = bool(resume.get("is_final"))
        prepared_from = resume.get("prepared_from")
        # The count IS recoverable on a resume, now that `vcc prep` records it inside the
        # archive: the interrupted run did not persist it, but the `.vcc` it staged did.
        # This used to send None and take the largest tier -- and `--resume` is named in
        # this branch's own motivation as one of the paths that arrive with nothing, so
        # leaving it would have missed a workflow the change set out to fix.
        #
        # Read AFTER the checks below, once the staged path has been validated as a real
        # `.vcc` (#422): an untrusted state.json must not aim even a small read somewhere
        # arbitrary. Best-effort either way -- None just restores the old behaviour.
        nnz = None
        if not Path(vcc_path).exists():
            raise SubmitError(
                f"Cannot resume: the file it was uploading is gone ({vcc_path}). "
                "Start a new `vcc submit`."
            )
        # The staged file must still be a real .vcc, not an arbitrary local file a
        # tampered state.json could aim the upload at (#422). validate_vcc opens the
        # container and checks its prediction member, so /etc/hosts and friends fail.
        try:
            validate_vcc(vcc_path)
        except InvalidVccError as exc:
            raise SubmitError(
                f"Cannot resume: the staged file did not validate as a .vcc ({exc}) "
                "Start a new `vcc submit`."
            ) from exc
        nnz = nnz_from_vcc(vcc_path)
        _emit(on_event, "resume", entry_id=entry_id, file=vcc_path)
    else:
        # Refuse before prepping/uploading if a previous submission is still live.
        if pending_uploads:
            check_no_inflight(
                endpoint, token, pending=pending_uploads, on_event=on_event, clear_resume=clear_resume
            )

        vcc_path, prepared_from, nnz = prepare_input(
            path,
            genes=genes,
            perts=perts,
            verify_targets=verify_targets,
            check_cell_counts=check_cell_counts,
            on_event=on_event,
            force=force,
        )

        if not skip_limit_check:
            _emit(on_event, "limit_check")
            limits = api.get_limits(endpoint, token)
            if limits.get("limit_reached"):
                raise SubmitError(
                    "Your team has already used its submission allowance for today "
                    "(resets at 00:00 UTC). Nothing was uploaded."
                )

        file_name = Path(vcc_path).name
        _emit(on_event, "create_start", model_name=model_name, file=file_name)
        created = api.create_submission(
            endpoint,
            token,
            model_name=model_name,
            description=description,
            file_name=file_name,
            file_type="application/x-tar",
        )
        entry_id = created.get("entry_id")
        upload_url = created.get("upload_url")
        file_path = created.get("file_path")
        is_final = bool(created.get("is_final"))
        if not (entry_id and upload_url and file_path):
            raise SubmitError("The server did not return a usable submission (missing entry or upload URL).")
        _emit(on_event, "created", entry_id=entry_id, is_final=is_final)

        if save_resume:
            save_resume(
                entry_id,
                {
                    "entry_id": entry_id,
                    "upload_url": upload_url,
                    "file_path": file_path,
                    "local_path": str(vcc_path),
                    "model_name": model_name,
                    "is_final": is_final,
                    "prepared_from": prepared_from,
                },
            )

    def _fail_entry(reason: str) -> None:
        """Mark the entry failed so it doesn't block the team's next submission."""
        try:
            api.set_submission_status(endpoint, token, entry_id, "failed", error_message=reason[:500])
        except api.ApiError:
            pass  # best effort — never mask the original failure

    # --- upload ---
    _emit(on_event, "upload_start", file=vcc_path, entry_id=entry_id)
    try:
        upload_result = upload_file(
            upload_url,
            vcc_path,
            progress=lambda done, total: _emit(on_event, "upload_progress", done=done, total=total),
        )
    except UploadError as exc:
        # Leave the entry alone on upload failure: --resume can still continue it.
        raise SubmitError(str(exc)) from exc
    _emit(on_event, "upload_done", bytes=upload_result.bytes_sent, verified=upload_result.verified)

    # --- mark launching ---
    try:
        api.set_submission_status(endpoint, token, entry_id, "launching")
    except api.ApiError as exc:
        _fail_entry(f"CLI could not mark the submission launching: {exc}")
        raise SubmitError(f"Upload finished but the submission could not be advanced: {exc}") from exc

    # --- trigger scoring ---
    try:
        launched = api.launch_submission(endpoint, token, entry_id, file_path, nnz=nnz)
    except api.ApiError as exc:
        # Only record `failed` when the launch DEFINITELY did not happen.
        #
        # A 5xx here is ambiguous: the job may have been created and the response
        # lost. Marking the entry failed on that is how a live scoring job came to
        # be recorded as failed in #384 — the job ran 22 minutes and published a
        # real score while its entry said `failed`, which then let a second
        # submission past the one-in-flight guard and ended in the newer entry
        # being deleted. A wrong terminal status is worse than a slow one: an entry
        # left in `launching` is released by the datastore's own staleness window
        # (UPLOAD_STALE_MINUTES), so the team is not locked out either way.
        #
        # A 4xx is the server telling us it rejected the request outright (bad
        # file_path, entry not found, gate closed) — nothing was launched, so
        # failing the entry is correct and keeps the slot free immediately.
        definitely_not_launched = exc.status is not None and 400 <= exc.status < 500
        if definitely_not_launched:
            _fail_entry(f"CLI could not launch scoring: {exc}")
            raise SubmitError(
                f"Upload finished but scoring could not be started: {exc}"
            ) from exc
        raise SubmitError(
            f"Upload finished, but the CLI could not confirm scoring started: {exc}\n"
            f"The job may be running anyway — the entry has been left alone rather than "
            f"marked failed.\nCheck it with: vcc status {entry_id}"
        ) from exc

    job_name = launched.get("job_name")
    _emit(on_event, "launched", job_name=job_name, entry_id=entry_id)

    if clear_resume:
        clear_resume(entry_id)

    result = SubmitResult(
        entry_id=entry_id,
        file_path=file_path,
        model_name=model_name,
        is_final=is_final,
        bytes_uploaded=upload_result.bytes_sent,
        md5_verified=upload_result.verified,
        job_name=job_name,
        prepared_from=prepared_from,
    )

    if wait:
        entry = poll_until_terminal(
            endpoint,
            token,
            entry_id,
            interval=poll_interval,
            timeout=wait_timeout,
            on_event=on_event,
        )
        result.final_status = entry.get("status")
        result.error_info = entry.get("error_info")
        # Carry every score field `vcc status` / _echo_scores knows about — incl.
        # the 2026 (vcc2026) set — so `vcc submit --wait` and `vcc status` show the
        # same metrics. SCORE_KEYS is the single source shared with cli._SCORE_FIELDS
        # so the two can't drift. Null keys (the metric set this entry didn't get)
        # are filtered out.
        result.scores = {k: entry.get(k) for k in SCORE_KEYS if entry.get(k) is not None}

    return result
