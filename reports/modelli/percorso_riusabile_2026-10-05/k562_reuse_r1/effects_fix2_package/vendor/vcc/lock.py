"""Single-flight lock so two `vcc submit` runs can't race on one machine.

The authoritative in-progress guard is server-side (the datastore rejects a
second active submission per team with 409). This lock closes the *local* race
that guard can't see cleanly: two `vcc submit` processes started at once — a
double-tap, a retry loop, or a script run twice — can both pass their pre-checks
before either creates an entry, and only find out at the 409 (having already
prepped and possibly uploaded).

Design notes:
- ``O_CREAT | O_EXCL`` is the atomic primitive, and works on POSIX and Windows.
- A crashed run must not lock the user out forever, so a lock is stealable when
  its owning PID is gone (checked directly on POSIX) or when it is older than
  ``stale_after`` (the backstop everywhere, since a PID check can't be trusted
  across reboots or on Windows).
- Uploads are legitimately long, so ``stale_after`` is hours, not minutes.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable

DEFAULT_STALE_AFTER = 6 * 60 * 60  # seconds


class LockHeldError(Exception):
    """Another process holds the lock."""


def _pid_alive(pid: int) -> bool | None:
    """True/False if determinable, None if we cannot tell on this platform."""
    if pid <= 0:
        return False
    if os.name == "posix":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # exists, owned by someone else
        except OSError:
            return None
        return True
    return None  # Windows: fall back to the staleness window


class SubmitLock:
    """Advisory single-flight lock backed by an exclusive-create file."""

    def __init__(
        self,
        path: str | Path,
        *,
        stale_after: float = DEFAULT_STALE_AFTER,
        now: Callable[[], float] = time.time,
        pid: int | None = None,
        label: str = "vcc submit",
        advice: str | None = None,
    ) -> None:
        self.path = Path(path)
        self.stale_after = stale_after
        self._now = now
        self.pid = os.getpid() if pid is None else pid
        self.label = label
        # What the user should do about a held lock. Defaults to the submit
        # advice this class was written for; `vcc datasets download` passes its
        # own, since the consequence there is a corrupted file, not a 409.
        self.advice = advice or (
            "Wait for it to finish — submitting twice would create a second entry and "
            "your team is allowed only one submission in progress at a time."
        )
        self._acquired = False

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def _is_stale(self, info: dict[str, Any]) -> bool:
        """A lock is stale if its owner is gone, or it has simply aged out.

        An unreadable/garbage lock file counts as stale — otherwise a corrupted
        write would wedge submissions permanently.
        """
        if not info:
            return True
        owner = info.get("pid")
        if isinstance(owner, int) and owner != self.pid:
            if _pid_alive(owner) is False:
                return True
        created = info.get("created_at")
        if not isinstance(created, (int, float)):
            return True
        return (self._now() - created) > self.stale_after

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {"pid": self.pid, "created_at": self._now(), "label": self.label}
        )
        for attempt in (1, 2):
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                info = self._read()
                if attempt == 1 and self._is_stale(info):
                    # Reclaim an abandoned lock, then retry the exclusive create
                    # once. If someone else wins that race we fall through to the
                    # held-error below rather than stomping their lock.
                    try:
                        self.path.unlink()
                    except OSError:
                        pass
                    continue
                raise LockHeldError(self._held_message(info)) from None
            else:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(payload)
                self._acquired = True
                return

    def _held_message(self, info: dict[str, Any]) -> str:
        owner = info.get("pid", "unknown")
        created = info.get("created_at")
        age = ""
        if isinstance(created, (int, float)):
            minutes = max(int((self._now() - created) / 60), 0)
            age = f", started {minutes} min ago"
        return (
            f"Another `{self.label}` is already running on this machine "
            f"(pid {owner}{age}).\n"
            f"{self.advice}\n"
            f"If that process is gone, delete the stale lock: {self.path}"
        )

    def release(self) -> None:
        """Release the lock, but only if we still own it."""
        if not self._acquired:
            return
        info = self._read()
        if info.get("pid") == self.pid:
            try:
                self.path.unlink()
            except OSError:
                pass
        self._acquired = False

    def __enter__(self) -> "SubmitLock":
        self.acquire()
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()
