"""Credential storage and token resolution for the vcc CLI.

Design per requirements §5.2.4–§5.2.5:

- A token from ``VCC_TOKEN`` is used transiently and **never** written to disk.
- ``vcc login`` prefers the OS-native secure store via ``keyring`` (macOS
  Keychain, Windows Credential Manager, Linux SecretService/KWallet).
- **Keyring is never assumed.** The active backend is probed; if it is absent or
  is a known-insecure fallback (the plaintext/obfuscated ``keyrings.alt``
  backends that ``keyring`` silently selects on headless Linux, bare containers,
  and no-D-Bus HPC nodes), the CLI does **not** pretend it is secure — it
  refuses to store until the user explicitly opts in to a ``0600`` file, or
  points them at ``VCC_TOKEN`` (R-KeyStore).

Deviation from the plan worth knowing: the plan's fallback was an "encrypted
file (key derived from a passphrase or a machine-bound key)". A machine-bound
key sitting on the same disk as the ciphertext is obfuscation, not encryption,
and a passphrase prompt would break the headless/CI use cases this fallback
exists to serve. So the fallback here is an explicit, clearly-labeled ``0600``
plaintext file behind ``--store-plaintext`` — honest about what it is, rather
than security theater. ``VCC_TOKEN`` remains the recommended path on shared
infrastructure.
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from vcc.config import TOKEN_PREFIX, config_dir

KEYRING_SERVICE = "vcc"

# Backends we accept as genuinely OS-protected. Anything not on this list is
# treated as insecure — fail-safe, so an unknown/new backend is never silently
# trusted with a credential.
_SECURE_BACKENDS = frozenset(
    {
        "keyring.backends.macOS.Keyring",
        "keyring.backends.OS_X.Keyring",  # older keyring naming
        "keyring.backends.Windows.WinVaultKeyring",
        "keyring.backends.SecretService.Keyring",
        "keyring.backends.libsecret.Keyring",
        "keyring.backends.kwallet.DBusKeyring",
        "keyring.backends.kwallet.DBusKeyringKWallet4",
    }
)

StorageKind = Literal["keyring", "file", "none"]
TokenSource = Literal["env", "keyring", "file"]


class AuthError(Exception):
    """A user-facing credential problem (nothing stored, unusable store, …)."""


class InsecureStoreError(AuthError):
    """No secure OS credential store is available and plaintext wasn't allowed."""


@dataclass(frozen=True)
class KeyringProbe:
    status: Literal["secure", "insecure", "unavailable"]
    backend: str

    @property
    def usable(self) -> bool:
        return self.status == "secure"


@dataclass(frozen=True)
class ResolvedToken:
    token: str
    source: TokenSource


def redact(token: str) -> str:
    """Render a token safe for logs/terminal: prefix + last 4 only (AR5).

    Never print or log a raw token anywhere, including under --verbose/--debug.
    """
    if not token:
        return "(empty)"
    tail = token[-4:] if len(token) >= 4 else ""
    return f"{TOKEN_PREFIX}…{tail}" if token.startswith(TOKEN_PREFIX) else f"…{tail}"


def probe_keyring() -> KeyringProbe:
    """Classify the active keyring backend without storing anything."""
    try:
        import keyring
        from keyring.backends import fail as keyring_fail
    except Exception as exc:  # noqa: BLE001 — keyring itself failed to import
        return KeyringProbe("unavailable", f"import failed: {exc}")

    try:
        backend = keyring.get_keyring()
    except Exception as exc:  # noqa: BLE001
        return KeyringProbe("unavailable", f"backend lookup failed: {exc}")

    cls = type(backend)
    name = f"{cls.__module__}.{cls.__qualname__}"

    if isinstance(backend, keyring_fail.Keyring):
        return KeyringProbe("unavailable", name)

    # A chainer delegates to the first viable backend; classify by what it holds.
    inner = getattr(backend, "backends", None)
    if inner:
        for candidate in inner:
            c = type(candidate)
            cname = f"{c.__module__}.{c.__qualname__}"
            if cname in _SECURE_BACKENDS:
                return KeyringProbe("secure", cname)
        first = type(inner[0])
        return KeyringProbe("insecure", f"{first.__module__}.{first.__qualname__}")

    if name in _SECURE_BACKENDS:
        return KeyringProbe("secure", name)
    return KeyringProbe("insecure", name)


# --- on-disk state -----------------------------------------------------------

def _state_path() -> Path:
    return config_dir() / "state.json"


def _credentials_path() -> Path:
    return config_dir() / "credentials.json"


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON with 0600 permissions, creating the parent dir 0700.

    The file is created with restrictive permissions *before* the secret is
    written (open with mode 0600) so there is no window where it is world-readable.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, stat.S_IRWXU)  # 0700
    except OSError:
        pass  # best effort (e.g. Windows / exotic filesystems)

    tmp = path.with_suffix(path.suffix + ".tmp")
    # The rename is inside the try as well: if os.replace fails (permissions, a
    # cross-device path, disk full) the temp file must not be left behind — and
    # for credentials.json that stray file would hold a live token.
    try:
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        # OSError covers the missing file plus permission errors, a path that is
        # unexpectedly a directory, and unreadable media. None of those should
        # crash a command that merely wanted to look at cached state.
        return {}
    return data if isinstance(data, dict) else {}


def read_profile_state(profile: str) -> dict[str, Any]:
    """Non-secret per-profile state: endpoint, cached identity, storage kind."""
    profiles = _read_json(_state_path()).get("profiles")
    if not isinstance(profiles, dict):
        return {}
    entry = profiles.get(profile)
    return entry if isinstance(entry, dict) else {}


def write_profile_state(profile: str, updates: dict[str, Any]) -> None:
    """Merge updates into one profile's state, leaving other profiles alone (AR6)."""
    state = _read_json(_state_path())
    profiles = state.get("profiles")
    if not isinstance(profiles, dict):
        profiles = {}
    entry = profiles.get(profile)
    entry = dict(entry) if isinstance(entry, dict) else {}
    entry.update(updates)
    profiles[profile] = entry
    state["profiles"] = profiles
    _write_private_json(_state_path(), state)


def clear_profile_state(profile: str) -> bool:
    """Drop one profile's non-secret state. Returns True if anything was removed."""
    state = _read_json(_state_path())
    profiles = state.get("profiles")
    if not isinstance(profiles, dict) or profile not in profiles:
        return False
    del profiles[profile]
    state["profiles"] = profiles
    _write_private_json(_state_path(), state)
    return True


# --- token storage -----------------------------------------------------------

def _file_tokens() -> dict[str, Any]:
    creds = _read_json(_credentials_path()).get("tokens")
    return creds if isinstance(creds, dict) else {}


def store_token(profile: str, token: str, *, allow_plaintext: bool = False) -> StorageKind:
    """Persist a token for a profile, preferring the OS secure store.

    Returns the storage actually used. Raises :class:`InsecureStoreError` when no
    secure backend exists and ``allow_plaintext`` is False — the CLI must never
    silently degrade to plaintext (R-KeyStore).
    """
    probe = probe_keyring()
    if probe.usable:
        import keyring

        try:
            keyring.set_password(KEYRING_SERVICE, profile, token)
            return "keyring"
        except Exception as exc:  # noqa: BLE001 — backend can fail at write time
            if not allow_plaintext:
                raise InsecureStoreError(
                    f"The OS credential store ({probe.backend}) failed to save the token: {exc}\n"
                    "Re-run with --store-plaintext to save it to a 0600 file instead, "
                    "or set VCC_TOKEN in your environment for each session."
                ) from exc

    if not allow_plaintext:
        raise InsecureStoreError(
            f"No secure OS credential store is available (backend: {probe.backend}).\n"
            "vcc will not silently write your token to plaintext. Choose one:\n"
            "  • set VCC_TOKEN in your environment (recommended on shared/HPC/CI machines — never touches disk)\n"
            "  • re-run: vcc login --token-stdin --store-plaintext   (saves to a 0600 file)"
        )

    tokens = _file_tokens()
    tokens[profile] = token
    _write_private_json(_credentials_path(), {"tokens": tokens})
    return "file"


def get_stored_token(profile: str) -> tuple[str | None, TokenSource | None]:
    """Read a stored token for a profile (keyring first, then the 0600 file)."""
    probe = probe_keyring()
    if probe.usable:
        try:
            import keyring

            token = keyring.get_password(KEYRING_SERVICE, profile)
            if token:
                return token, "keyring"
        except Exception:  # noqa: BLE001 — treat a broken backend as "nothing stored"
            pass

    token = _file_tokens().get(profile)
    if isinstance(token, str) and token:
        return token, "file"
    return None, None


def resolve_token(profile: str) -> ResolvedToken:
    """Resolve the token to use.

    Precedence (§5.2.1): ``VCC_TOKEN`` env var, then whatever ``vcc login``
    stored. An env token is transient — it is never persisted.
    """
    env_token = os.environ.get("VCC_TOKEN")
    if env_token and env_token.strip():
        # An empty/whitespace-only VCC_TOKEN (e.g. `export VCC_TOKEN=`) is not a
        # credential — fall through to the stored one rather than sending blanks
        # and failing with a confusing server-side auth error.
        return ResolvedToken(env_token.strip(), "env")

    token, source = get_stored_token(profile)
    if token and source:
        return ResolvedToken(token, source)

    raise AuthError(
        "Not logged in. Set VCC_TOKEN, or run `vcc login --token-stdin` "
        "with a token from your Credentials page."
    )


def delete_token(profile: str) -> list[StorageKind]:
    """Remove a profile's stored token from every location. Returns what was cleared.

    Only touches the given profile — other profiles are untouched (AR6).
    """
    cleared: list[StorageKind] = []

    try:
        import keyring
        import keyring.errors

        try:
            if keyring.get_password(KEYRING_SERVICE, profile):
                keyring.delete_password(KEYRING_SERVICE, profile)
                cleared.append("keyring")
        except keyring.errors.PasswordDeleteError:
            pass
        except Exception:  # noqa: BLE001 — nothing to clear if the backend is broken
            pass
    except Exception:  # noqa: BLE001 — keyring not importable
        pass

    tokens = _file_tokens()
    if profile in tokens:
        del tokens[profile]
        if tokens:
            _write_private_json(_credentials_path(), {"tokens": tokens})
        else:
            _credentials_path().unlink(missing_ok=True)
        cleared.append("file")

    return cleared


# --- in-flight upload state (for `vcc submit --resume`) ----------------------

def save_pending_upload(profile: str, entry_id: str, data: dict[str, Any]) -> None:
    """Record an in-flight submission so an interrupted upload can be resumed (R4).

    Contains no secret — just the entry id, the GCS session URI, and the local
    path — but it lives in the same 0600 state file as everything else.
    """
    state = read_profile_state(profile)
    pending = state.get("pending_uploads")
    pending = dict(pending) if isinstance(pending, dict) else {}
    pending[entry_id] = data
    write_profile_state(profile, {"pending_uploads": pending})


def list_pending_uploads(profile: str) -> dict[str, Any]:
    pending = read_profile_state(profile).get("pending_uploads")
    return pending if isinstance(pending, dict) else {}


def get_pending_upload(profile: str, entry_id: str | None = None) -> dict[str, Any] | None:
    """Return a specific pending upload, or the only one if unambiguous."""
    pending = list_pending_uploads(profile)
    if entry_id:
        entry = pending.get(entry_id)
        return entry if isinstance(entry, dict) else None
    if len(pending) == 1:
        (only,) = pending.values()
        return only if isinstance(only, dict) else None
    return None


def clear_pending_upload(profile: str, entry_id: str) -> None:
    pending = list_pending_uploads(profile)
    if entry_id in pending:
        del pending[entry_id]
        write_profile_state(profile, {"pending_uploads": pending})
