"""An offline adapter that reads its answers from files.

It exists so the engine can be exercised end to end -- routing, rounds, convergence,
stop reasons, reports, resume after a crash -- without touching any external service.
That matters twice over: the loop is testable, and the first trial of a new brief can be
rehearsed locally before a single character reaches an external chat.

Answers are looked up by decreasing specificity:

    <script_dir>/<stage>-<subtask>-<role>-<round>.txt
    <script_dir>/<stage>-<role>-<round>.txt
    <script_dir>/<role>-<round>.txt
    <script_dir>/<role>.txt

A missing file is a transport error on purpose: a silent stand-in answer would be
exactly the kind of substitution this project refuses to make.

When the same slot is asked twice in one run -- a format repair, or a transport retry --
the second call first looks for `<name>-try2.txt`, the third for `-try3.txt`, and falls
back to the plain name when there is none. That is what lets a rehearsal reproduce the
sequence that actually happens on a real channel: an unreadable answer, one repair, a
good answer, and no second copy of the original question.
"""

from __future__ import annotations

from pathlib import Path

from ..util import utc_now
from .base import Adapter, Health, Reply, Request, TransportError


class ScriptedAdapter(Adapter):
    name = "scripted"

    def __init__(self, service: str, config: dict) -> None:
        super().__init__(service, config)
        self.script_dir = Path(config.get("script_dir", "")).resolve()
        self.calls: list[str] = []
        self._served: dict[tuple[str, str, str, str], int] = {}

    def _slot(self, request: Request) -> tuple[str, str, str, str]:
        stage, subtask, round_number = _decode(request.conversation_key)
        return (stage, subtask, request.role, round_number)

    def _candidates(self, request: Request, attempt: int = 1) -> list[Path]:
        stage, subtask, round_number = _decode(request.conversation_key)
        names = [
            f"{stage}-{subtask}-{request.role}-{round_number}.txt",
            f"{stage}-{request.role}-{round_number}.txt",
            f"{request.role}-{round_number}.txt",
            f"{request.role}.txt",
        ]
        if attempt > 1:
            names = [f"{name[:-4]}-try{attempt}.txt" for name in names] + names
        return [self.script_dir / name for name in names]

    def preflight(self) -> Health:
        ok = self.script_dir.is_dir()
        return Health(ok=ok, detail=("" if ok else f"missing script dir {self.script_dir}"),
                      checked_utc=utc_now())

    def send(self, request: Request) -> Reply:
        slot = self._slot(request)
        self._served[slot] = self._served.get(slot, 0) + 1
        attempt = self._served[slot]
        candidates = self._candidates(request, attempt)
        for path in candidates:
            if path.is_file():
                self.calls.append(path.name)
                request.sent()
                return Reply(text=path.read_text(encoding="utf-8"), service=self.service,
                             meta={"source": str(path), "adapter": self.name,
                                   "slot_attempt": attempt})
        raise TransportError(
            "empty",
            "no scripted answer for " + " / ".join(path.name for path in candidates),
            recoverable=False,
        )


def _decode(conversation_key: str) -> tuple[str, str, str]:
    """conversation_key is '<stage>:<subtask>:<round>' built by the engine."""
    parts = (conversation_key or "::").split(":")
    while len(parts) < 3:
        parts.append("")
    return parts[0] or "stage", parts[1] or "none", parts[2] or "1"
