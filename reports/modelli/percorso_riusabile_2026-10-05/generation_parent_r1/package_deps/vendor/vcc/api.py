"""HTTP client for the vcc CLI's server surface.

The CLI talks only to the site's ``/api/cli/*`` routes, authenticating with the
``vcc_pat_…`` token the user pastes. Everything behind those routes is the
server's business: the CLI holds no cloud credential of any kind, and there is
no second host it needs to reach.

``httpx`` is imported at module top on purpose — this module is itself imported
lazily by the commands that need the network, so ``vcc --help`` never pays for it.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from vcc._version import vcc_version
from vcc.config import credentials_url, normalize_endpoint

DEFAULT_TIMEOUT = 20.0


class ApiError(Exception):
    """A request to the vcc API failed, with a message naming the next action (R1)."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status: int | None = None,
        blockers: list[str] | None = None,
    ) -> None:
        self.code = code
        self.status = status
        # Some 403s (e.g. dataset access_denied) name exactly what's missing.
        self.blockers = blockers or []
        super().__init__(message)


def user_agent() -> str:
    """Identify the CLI and its version so the server can audit-tag CLI traffic (O3)."""
    return f"vcc-cli/{vcc_version()}"


def _auth_error_message(code: str, endpoint: str) -> str:
    """Map an edge error code to an actionable message (AR2 — never a stack trace)."""
    portal = credentials_url(endpoint)
    match code:
        case "missing_token":
            return (
                "No API token was sent. Set VCC_TOKEN or run `vcc login --token-stdin`."
            )
        case "invalid_token":
            return (
                "Your API token is invalid or has been revoked.\n"
                f"Create a new one at {portal}, then run `vcc login --token-stdin`.\n"
                "If VCC_TOKEN is set in your shell, it overrides `vcc login` — run "
                "`unset VCC_TOKEN` (or update it)."
            )
        case "token_revoked":
            return (
                "Your API token has been revoked.\n"
                f"Create a new one at {portal}, then run `vcc login --token-stdin`.\n"
                "Note: generating a token revokes any previous one, so another machine "
                "may have replaced it.\n"
                "If VCC_TOKEN is set in your shell, it overrides `vcc login` — run "
                "`unset VCC_TOKEN` (or update it)."
            )
        case "token_expired":
            return (
                "Your API token has expired.\n"
                f"Create a new one at {portal}, then run `vcc login --token-stdin`.\n"
                "If VCC_TOKEN is set in your shell, it overrides `vcc login` — run "
                "`unset VCC_TOKEN` (or update it)."
            )
        case "auth_unavailable":
            return (
                "The server could not verify your token right now (auth backend unavailable). "
                "This is a server-side problem — try again shortly."
            )
        case "user_not_found":
            return (
                "Your token resolved, but no VCC account matches it. "
                "If your account was deleted or recreated, generate a new token at "
                f"{portal}."
            )
        case "user_lookup_failed":
            return (
                "The server could not load your account right now. "
                "This is a server-side problem — try again shortly."
            )
        case "identity_not_verified":
            return (
                "Your identity is not verified yet, which is required to submit.\n"
                f"Complete verification in the web app: {normalize_endpoint(endpoint)}/app"
            )
        case "not_found":
            return "No such submission for your account (it may belong to another user, or never existed)."
        case "invalid_file_path":
            return "The server rejected the upload path for this submission. Start a fresh `vcc submit`."
        case "dataset_not_found":
            return (
                "No such dataset. Run `vcc datasets list` to see what's available."
            )
        case "preregistration" | "preregistration_active":
            # `preregistration` is what the server sends (one shared gate in
            # front of every /api/cli/* route).
            # `preregistration_active` is accepted too so an older server build
            # still gets the friendly message rather than a bare code.
            return (
                "The VCC CLI isn't available yet — the challenge is still in pre-registration.\n"
                f"Watch {normalize_endpoint(endpoint)} for the opening announcement."
            )
        case "final_week_not_active":
            return (
                "That dataset is only available during the final week of the challenge."
            )
        case "submissions_closed":
            return "The challenge is closed, so dataset downloads are no longer available."
        case "access_denied":
            return (
                "Your account can't download datasets yet. Complete identity verification "
                f"in the web app: {endpoint}/app"
            )
        case "file_not_found_in_bucket":
            return (
                "The server could not find that dataset file in storage. "
                "This is a server-side problem — please report it."
            )
        case "signed_url_failed" | "server_configuration_error":
            return (
                f"The server could not produce a download link ({code}). "
                "This is a server-side problem — try again shortly."
            )
        case "create_failed" | "upload_url_failed" | "lookup_failed" | "limits_lookup_failed" | "status_update_failed":
            return (
                f"The server could not complete the request ({code}). "
                "This is a server-side problem — try again shortly."
            )
        case _:
            # Unknown codes are usually a datastore `detail` string, which is
            # already human-readable (rate limits, feature gates, team state).
            return code


def get_me(endpoint: str, token: str, *, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """Validate a token and return the caller's identity from ``GET /api/cli/me``.

    Response fields: email, name, display_name, organization, approved,
    identity_verified, status, team_id, team_name, pending_team_invites,
    can_submit, blockers.

    Raises :class:`ApiError` — never leaks the token into the message.
    """
    url = f"{normalize_endpoint(endpoint)}/api/cli/me"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": user_agent(),
    }
    try:
        response = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    except httpx.TimeoutException as exc:
        raise ApiError(
            f"Timed out contacting {endpoint} after {timeout:.0f}s. "
            "Check your network, or pass --endpoint if you meant a different environment."
        ) from exc
    except httpx.InvalidURL as exc:
        # Same as _request: InvalidURL is not an httpx.HTTPError subclass, so
        # without this it escapes as a raw traceback. get_me is the FIRST network
        # call of login/whoami/doctor, so it needs the clause too (#429).
        raise ApiError(f"Could not build a valid request URL for {endpoint}: {exc}.") from exc
    except httpx.HTTPError as exc:
        raise ApiError(
            f"Could not reach {endpoint}: {exc}. "
            "Check your network, or pass --endpoint if you meant a different environment."
        ) from exc

    if response.status_code == 200:
        try:
            body = response.json()
        except ValueError as exc:
            raise ApiError(
                f"{endpoint} returned a non-JSON response to /api/cli/me. "
                "If this endpoint is correct, this is a server-side problem."
            ) from exc
        if not isinstance(body, dict):
            raise ApiError("Unexpected response shape from /api/cli/me (expected an object).")
        return body

    # Error path: the edge reports a machine-readable code in {"error": ...}.
    code: str | None = None
    try:
        payload = response.json()
        if isinstance(payload, dict):
            raw = payload.get("error") or payload.get("detail")
            if isinstance(raw, str):
                code = raw
    except ValueError:
        code = None

    if response.status_code == 404 and not code:
        raise ApiError(
            f"{endpoint} has no /api/cli/me endpoint (404). "
            "This server may be too old for this CLI, or the endpoint is wrong.",
            status=404,
        )
    if code:
        raise ApiError(_auth_error_message(code, endpoint), code=code, status=response.status_code)
    raise ApiError(
        f"Unexpected response from {endpoint} (HTTP {response.status_code}).",
        status=response.status_code,
    )


def _request(
    method: str,
    endpoint: str,
    path: str,
    token: str,
    *,
    json_body: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Call a `/api/cli/*` route and return its JSON, mapping errors to ApiError.

    Shared by every submission call so auth failures, transport failures, and
    server error codes are reported identically wherever they occur.
    """
    url = f"{normalize_endpoint(endpoint)}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": user_agent(),
    }
    if json_body is not None:
        headers["Content-Type"] = "application/json"

    try:
        response = httpx.request(
            method, url, headers=headers, json=json_body, timeout=timeout, follow_redirects=True
        )
    except httpx.TimeoutException as exc:
        raise ApiError(f"Timed out contacting {endpoint} after {timeout:.0f}s.") from exc
    except httpx.InvalidURL as exc:
        # InvalidURL is NOT an httpx.HTTPError subclass, so it would otherwise
        # escape as a raw traceback (#419). A control-char endpoint is already
        # rejected upstream (config.validate_endpoint); this also backstops an
        # oversized/degenerate id interpolated into the path ("URL too long").
        raise ApiError(f"Could not build a valid request URL for {endpoint}: {exc}.") from exc
    except httpx.HTTPError as exc:
        raise ApiError(f"Could not reach {endpoint}: {exc}.") from exc

    try:
        body = response.json()
    except ValueError as exc:
        if response.is_success:
            # A 2xx carrying HTML (a proxy error page, a captive portal, a login
            # redirect) previously became {}, which surfaced downstream as a
            # baffling "missing entry or upload URL". Name the real problem.
            raise ApiError(
                f"{endpoint} returned HTTP {response.status_code} but the body was not JSON. "
                "Something between this CLI and the server is rewriting responses "
                "(a proxy or captive portal), or the endpoint is wrong."
            ) from exc
        body = None

    if response.is_success:
        if not isinstance(body, dict):
            raise ApiError(
                f"{endpoint} returned HTTP {response.status_code} with an unexpected "
                "response shape (expected a JSON object)."
            )
        return body

    code: str | None = None
    blockers: list[str] = []
    if isinstance(body, dict):
        raw = body.get("error") or body.get("detail")
        if isinstance(raw, str):
            code = raw
        raw_blockers = body.get("blockers")
        if isinstance(raw_blockers, list):
            blockers = [b for b in raw_blockers if isinstance(b, str)]
    if response.status_code == 404 and not code:
        # A bare 404 (no JSON error code) means the route isn't there at all —
        # usually a server predating this CLI feature, or the wrong --endpoint.
        raise ApiError(
            f"{endpoint} has no {path} endpoint (404). That server may be running a build "
            "without this feature, or --endpoint points somewhere unexpected.",
            status=404,
        )
    if code:
        message = _auth_error_message(code, endpoint)
        if blockers:
            explain = {
                "identity_not_verified": "identity verification is incomplete",
                "account_not_approved": "your account is awaiting approval",
                "no_team": "you are not on a team yet",
                "pending_team_invites": "a teammate has not accepted their invitation",
            }
            for blocker in blockers:
                message += f"\n  • {explain.get(blocker, blocker)}"
        if response.status_code == 409:
            # The datastore's per-team in-progress guard. Its detail text is
            # clear but doesn't say what to DO about it.
            message = (
                f"{message}\n"
                "  • check the one that's running: vcc status <entry-id> --wait\n"
                "  • finish an interrupted upload: vcc submit --resume\n"
                "  • abandon a stuck upload (frees the slot; doesn't use a daily submission): "
                "vcc cancel <entry-id>\n"
                "An abandoned submission is released automatically after a timeout."
            )
        raise ApiError(message, code=code, status=response.status_code, blockers=blockers)
    raise ApiError(
        f"Unexpected response from {endpoint} (HTTP {response.status_code}).",
        status=response.status_code,
    )


def get_limits(endpoint: str, token: str) -> dict[str, Any]:
    """Daily-limit pre-check: ``{"limit_reached": bool}``."""
    return _request("GET", endpoint, "/api/cli/submissions/limits", token)


def create_submission(
    endpoint: str,
    token: str,
    *,
    model_name: str,
    file_name: str,
    description: str | None = None,
    file_type: str | None = None,
) -> dict[str, Any]:
    """Create the leaderboard entry and mint a resumable upload URL in one call.

    Returns ``{entry_id, upload_url, file_path, is_final}``.
    """
    body: dict[str, Any] = {"model_name": model_name, "file_name": file_name}
    if description:
        body["description"] = description
    if file_type:
        body["file_type"] = file_type
    return _request("POST", endpoint, "/api/cli/submissions", token, json_body=body)


def set_submission_status(
    endpoint: str, token: str, entry_id: str, status: str, error_message: str | None = None
) -> dict[str, Any]:
    """Transition a submission (e.g. ``uploading`` -> ``launching``)."""
    body: dict[str, Any] = {"status": status}
    if error_message:
        body["error_message"] = error_message
    # Percent-encode: `vcc cancel` feeds a user-typed entry_id straight here, so a value
    # with path/control characters must not rewrite the request path (mirrors
    # get_submission). The lookup is ownership-scoped server-side, so this is
    # defense-in-depth, not an auth boundary.
    return _request(
        "PUT", endpoint, f"/api/cli/submissions/{quote(entry_id, safe='')}/status", token, json_body=body
    )


def launch_submission(
    endpoint: str,
    token: str,
    entry_id: str,
    file_path: str,
    nnz: int | None = None,
) -> dict[str, Any]:
    """Trigger scoring for an uploaded submission. Returns ``{job_name, message}``.

    ``nnz`` is the prediction's nonzero count, which prep already computed. It selects
    the scoring machine: memory there tracks nonzeros, and neither the cell count nor
    the compressed size predicts it — the one submission that ever OOM'd the scorer had
    a normal cell count and was the SMALLEST upload of the three. Omitted when unknown
    (a dense matrix, or a ``.vcc`` submitted without a prep in the same run), and the
    server then provisions the larger machine rather than guessing small.
    """
    body: dict[str, Any] = {"file_path": file_path}
    if nnz is not None:
        body["nnz"] = int(nnz)
    return _request(
        "POST",
        endpoint,
        f"/api/cli/submissions/{entry_id}/launch",
        token,
        json_body=body,
    )


def cancel_submission(endpoint: str, token: str, entry_id: str) -> dict[str, Any]:
    """Abandon an in-progress submission, freeing the team's slot.

    The server decides what's safe: an ``uploading`` entry is just failed; a
    ``launching``/``scoring`` entry's Batch job is deleted ONLY while it is still
    queued (no machine yet), else the entry is left alone. Returns one of:

    - ``{"status": "cancelled", "killed_job": bool}`` — freed (killed_job True if a
      queued scoring job was deleted).
    - ``{"status": "not_cancelled", "reason": "running"|"terminal"}`` — not freed,
      because the scoring job already started (or the entry was already terminal).

    A 404 (not the caller's entry, or gone) raises ApiError like any other call.
    """
    return _request(
        "POST", endpoint, f"/api/cli/submissions/{quote(entry_id, safe='')}/cancel", token
    )


def get_submission(endpoint: str, token: str, entry_id: str) -> dict[str, Any]:
    """Fetch one submission's status/scores, scoped to the caller."""
    # Percent-encode: entry_id comes straight from argv, so a value with path or
    # control characters must not rewrite the request path (mirrors
    # get_dataset_download). The lookup is ownership-scoped server-side, so this is
    # defense-in-depth, not an auth boundary (#401).
    return _request("GET", endpoint, f"/api/cli/submissions/{quote(entry_id, safe='')}", token)


def list_datasets(endpoint: str, token: str) -> dict[str, Any]:
    """Catalog of downloadable datasets with per-item availability.

    Returns ``{"datasets": [{id, filename, description, available,
    unavailable_reason}]}``.
    """
    return _request("GET", endpoint, "/api/cli/datasets", token)


def get_dataset_download(endpoint: str, token: str, dataset_id: str) -> dict[str, Any]:
    """Mint a short-lived signed download URL plus size/checksums.

    Returns ``{id, filename, url, expires_at, size_bytes, md5, crc32c}``. Note
    ``md5`` is ``None`` for composite GCS objects (the training bundle), so
    verification must prefer ``crc32c``.
    """
    # Percent-encode: dataset_id comes straight from argv, so a value like
    # "../../x" must not be able to rewrite the request path.
    return _request(
        "GET", endpoint, f"/api/cli/datasets/{quote(dataset_id, safe='')}/download", token
    )
