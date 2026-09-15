"""Gemini through its official CLI, authenticated with the operator's Google account.

The CLI is a subprocess: the prompt goes in on stdin, the answer comes back on stdout,
and stderr plus the exit code decide whether this was a transport failure. No API key is
read, set or requested anywhere in this file -- authentication is whatever the CLI
already holds for the signed-in account.

What is *not* claimed here: that any particular flag spelling works. `command` and
`stdin` come from the configuration, and `orch doctor` reports what the binary answers,
so a change in the CLI is a config edit and a visible failure rather than a silent one.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from ..util import utc_now, write_new
from .base import Adapter, Health, Reply, Request, TransportError

_AUTH_MARKERS = (
    "not authenticated", "please sign in", "login required", "oauth",
    "reauthenticate", "credentials", "unauthorized", "401",
)
_QUOTA_MARKERS = ("quota", "rate limit", "resource_exhausted", "429", "too many requests")


class GeminiCliAdapter(Adapter):
    name = "gemini_cli"

    def __init__(self, service: str, config: dict) -> None:
        super().__init__(service, config)
        self.command: list[str] = list(config.get("command") or ["gemini"])
        self.stdin_prompt: bool = bool(config.get("stdin", True))
        self.prompt_flag: str = str(config.get("prompt_flag", "-p"))
        self.model: str | None = config.get("model")
        self.timeout_seconds: int = int(config.get("timeout_seconds", 300))
        self.working_dir: str | None = config.get("working_dir")

    # ------------------------------------------------------------------ plumbing
    def _resolve(self) -> str:
        executable = shutil.which(self.command[0])
        if not executable:
            raise TransportError(
                "launch",
                f"{self.command[0]} is not on PATH. Install the official CLI and sign in, "
                f"then re-run `orch doctor`.",
                recoverable=False)
        return executable

    def _argv(self, prompt: str) -> list[str]:
        argv = [self._resolve(), *self.command[1:]]
        if self.model:
            argv += ["-m", self.model]
        if not self.stdin_prompt:
            argv += [self.prompt_flag, prompt]
        return argv

    # -------------------------------------------------------------------- public
    def preflight(self) -> Health:
        try:
            executable = self._resolve()
        except TransportError as error:
            return Health(ok=False, detail=error.detail, checked_utc=utc_now())
        try:
            completed = subprocess.run(
                [executable, "--version"], capture_output=True, text=True, timeout=60,
                encoding="utf-8", errors="replace")
        except (subprocess.TimeoutExpired, OSError) as error:
            return Health(ok=False, detail=f"--version failed: {error}", checked_utc=utc_now())
        detail = (completed.stdout or completed.stderr or "").strip().splitlines()
        return Health(ok=completed.returncode == 0,
                      detail=detail[0] if detail else f"exit {completed.returncode}",
                      checked_utc=utc_now())

    def send(self, request: Request) -> Reply:
        argv = self._argv(request.prompt)
        environment = dict(os.environ, PYTHONIOENCODING="utf-8")
        started = time.monotonic()
        request.sent()   # a subprocess call is atomic: it is out as soon as it runs
        try:
            completed = subprocess.run(
                argv,
                input=request.prompt if self.stdin_prompt else None,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=request.timeout_seconds or self.timeout_seconds,
                cwd=self.working_dir, env=environment,
            )
        except subprocess.TimeoutExpired as error:
            raise TransportError("timeout", f"no answer in {error.timeout}s") from error
        except OSError as error:
            raise TransportError("launch", str(error), recoverable=False) from error

        elapsed_ms = int((time.monotonic() - started) * 1000)
        stderr = (completed.stderr or "").strip()
        if request.artifact_dir is not None and stderr:
            path = Path(request.artifact_dir) / "stderr.txt"
            if not path.exists():
                write_new(path, stderr)

        if completed.returncode != 0:
            lowered = stderr.lower()
            if any(marker in lowered for marker in _AUTH_MARKERS):
                raise TransportError("auth", stderr[:800], recoverable=False)
            if any(marker in lowered for marker in _QUOTA_MARKERS):
                raise TransportError("rate_limit", stderr[:800])
            raise TransportError("unknown", f"exit {completed.returncode}: {stderr[:800]}")

        text = (completed.stdout or "").strip()
        if not text:
            raise TransportError("empty", f"exit 0 but no stdout; stderr: {stderr[:400]}")
        return Reply(text=text, service=self.service,
                     meta={"adapter": self.name, "argv": argv[1:], "exit_code": 0,
                           "duration_ms": elapsed_ms, "stderr_bytes": len(stderr)})
