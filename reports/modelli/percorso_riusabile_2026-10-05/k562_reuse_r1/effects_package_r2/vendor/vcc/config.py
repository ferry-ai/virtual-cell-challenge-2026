"""Endpoint / profile / config-directory resolution for the vcc CLI.

Dependency-free and cheap to import (no network or crypto libs) so it can be
used from any command without hurting cold start (D6).
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from vcc import _build

# One endpoint is the whole surface: the CLI authenticates to the site's
# /api/cli/* routes with the user's token and never holds a cloud credential.
PROD_ENDPOINT = "https://virtualcellchallenge.org"
DEFAULT_ENDPOINT = PROD_ENDPOINT

# Where users create/regenerate their API token (show-once). Referenced in error
# messages so a bad-credential failure always names the next action (R1/AR2).
CREDENTIALS_PATH = "/app/credentials"

DEFAULT_PROFILE = "default"
TOKEN_PREFIX = "vcc_pat_"

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}


class ConfigError(Exception):
    """A user-facing configuration problem (bad endpoint, unusable config dir)."""


def config_dir() -> Path:
    """Return the vcc config directory, honoring VCC_CONFIG_DIR then XDG.

    VCC_CONFIG_DIR exists so tests (and users with unusual setups) can redirect
    all on-disk state without touching the real home directory.
    """
    override = os.environ.get("VCC_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser() / "vcc"
    return Path.home() / ".config" / "vcc"


def resolve_profile(explicit: str | None = None) -> str:
    """Profile precedence: --profile flag > VCC_PROFILE env > "default" (AR4)."""
    return explicit or os.environ.get("VCC_PROFILE") or DEFAULT_PROFILE


def normalize_endpoint(url: str) -> str:
    """Strip a trailing slash so path joins never produce a double slash."""
    return url.rstrip("/")


def is_loopback(url: str) -> bool:
    """True if the URL's host is loopback (local dev)."""
    host = (urlparse(url).hostname or "").lower()
    return host in _LOOPBACK_HOSTS


def validate_endpoint(url: str) -> str:
    """Validate the endpoint's scheme and return it normalized.

    Security posture (requirement S2, slightly stricter than the plan): a
    bearer token must never cross a network in cleartext, so plain ``http`` is
    accepted **only** for a loopback host (the documented local-dev path) and
    rejected outright otherwise. There is deliberately no flag to override this
    for a remote host — the plan gates ``--allow-insecure`` on localhost, and a
    localhost-only allowance needs no flag at all.
    """
    # A non-string endpoint (e.g. a bare number hand-written into state.json)
    # would crash `.strip()`/urlparse with an opaque AttributeError on *every*
    # network command, bypassing the --json contract (#403). Reject it cleanly.
    if not isinstance(url, str):
        raise ConfigError(
            f"Endpoint must be a URL string, got {type(url).__name__}. "
            "Check the 'endpoint' value in your config (state.json), --endpoint, or "
            "$VCC_ENDPOINT."
        )
    # Copy-paste and env vars pick up stray whitespace; urlparse would then fail
    # to see the scheme and produce a confusing error about the wrong thing.
    url = url.strip()
    # Reject control characters (tab/newline/…): urlparse().hostname silently drops
    # them for the loopback check, but they survive into the request URL and raise
    # httpx.InvalidURL deep in the network layer, bypassing --json (#419). A stray
    # \t/\n from an unquoted $(...) or a copy-paste is the usual source. Cover C0
    # controls + DEL, C1 controls (incl. NEL U+0085), and the Unicode line/
    # paragraph separators (U+2028/U+2029) — httpx rejects all of these, none is
    # valid in a URL, and IDN code points (> U+009F, not a separator) still pass.
    def _is_control(ch: str) -> bool:
        cp = ord(ch)
        return cp < 0x20 or cp == 0x7F or 0x80 <= cp <= 0x9F or ch in ("\u2028", "\u2029")

    if any(_is_control(ch) for ch in url):
        raise ConfigError(
            f"Endpoint contains a control character: {url!r}. "
            "Remove any stray tab/newline (often from an unquoted shell variable)."
        )
    # urlparse is lenient, but reading .hostname parses the authority and raises a
    # bare ValueError on a malformed IPv6 literal (e.g. an unclosed '[::1') — another
    # instance of the crash class this guard exists to prevent (#429). Map it to a
    # clean ConfigError instead of letting it reach the main() catch-all.
    try:
        parsed = urlparse(url)
        scheme, host = parsed.scheme, parsed.hostname
    except ValueError as exc:
        raise ConfigError(f"Endpoint is not a valid URL: '{url}' ({exc}).") from exc
    if scheme not in ("http", "https"):
        raise ConfigError(
            f"Endpoint must be an http(s) URL, got '{url}'. "
            f"Example: --endpoint {DEFAULT_ENDPOINT}"
        )
    if not host:
        raise ConfigError(f"Endpoint has no host: '{url}'")
    if scheme == "http" and not is_loopback(url):
        raise ConfigError(
            f"Refusing to send credentials over plain HTTP to a non-local host: '{url}'. "
            "Use https:// (plain http is allowed only for localhost during development)."
        )
    return normalize_endpoint(url)


def channel() -> str:
    """Build channel: ``"dev"`` in the repo, ``"release"`` in published artifacts.

    Read through the module (not a ``from`` import) so it reflects the value baked
    into the installed artifact, and so tests can patch it.
    """
    return getattr(_build, "CHANNEL", "dev")


def endpoint_is_locked() -> bool:
    """True when this build may only talk to production (released artifacts)."""
    return channel() == "release"


def _same_endpoint(a: str, b: str) -> bool:
    return normalize_endpoint(a).rstrip("/").lower() == normalize_endpoint(b).rstrip("/").lower()


def resolve_endpoint(explicit: str | None = None, stored: str | None = None) -> str:
    """Resolve which deployment to talk to.

    Dev builds: ``--endpoint`` > ``VCC_ENDPOINT`` > the profile's stored value >
    production. The stored value is what ``vcc login --endpoint …`` recorded, so a
    developer who logged in against localhost keeps talking to it.

    Released builds (installed from PyPI) are **locked to production**: a
    non-production ``--endpoint``/``VCC_ENDPOINT`` is rejected with an explicit
    error, and any stored endpoint is ignored so a value written by an earlier dev
    build can't redirect a released one.
    """
    if endpoint_is_locked():
        for value, origin in ((explicit, "--endpoint"), (os.environ.get("VCC_ENDPOINT"), "VCC_ENDPOINT")):
            if value and not _same_endpoint(value, PROD_ENDPOINT):
                raise ConfigError(
                    f"This is a released build of vcc, which only talks to {PROD_ENDPOINT}, "
                    f"so {origin} cannot be changed.\n"
                    "If you are developing against a local or staging deployment, install the "
                    "CLI from a source checkout (`uv pip install -e cli/`) instead."
                )
        return PROD_ENDPOINT

    chosen = explicit or os.environ.get("VCC_ENDPOINT") or stored or DEFAULT_ENDPOINT
    return validate_endpoint(chosen)


def credentials_url(endpoint: str) -> str:
    """Full URL of the API-key portal page for this endpoint."""
    return f"{normalize_endpoint(endpoint)}{CREDENTIALS_PATH}"
