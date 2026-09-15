"""The adapter interface, and the error taxonomy the engine reacts to.

One distinction runs through the whole system and starts here: **a broken channel is
not a bad answer.** A dead browser, an expired session or a timeout is a `TransportError`
and may be retried or escalated to the operator; a reply that arrived but does not
satisfy the contract is a `ContentProblem` (in `protocol`) and is never retried blindly,
because sending the same prompt again would only produce the same shape of answer.

An adapter is also the only place allowed to touch the outside world, and it returns
text. It does not decide what happens next.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

TRANSPORT_KINDS = (
    "launch",        # the CLI or the browser would not start
    "auth",          # not logged in, session expired, consent wall
    "navigation",    # the page did not load or changed shape beyond recognition
    "timeout",       # no complete answer within the allowed time
    "empty",         # the channel returned nothing at all
    "rate_limit",    # the service refused for quota reasons
    "unknown",
)


class TransportError(RuntimeError):
    """The channel failed. Says nothing about the quality of any answer.

    `delivered` is the field that decides whether a retry is safe. A failure before the
    message left (a composer that would not open, a session that expired) can be retried:
    nothing was asked. A failure *after* the message was sent -- the interface hanging on
    a reply that never settles -- must never be retried automatically, because sending the
    same prompt again would ask the same question twice in the same conversation.
    """

    def __init__(self, kind: str, detail: str = "", *, recoverable: bool = True,
                 delivered: bool = False) -> None:
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind = kind if kind in TRANSPORT_KINDS else "unknown"
        self.detail = detail
        self.recoverable = recoverable and not delivered
        self.delivered = delivered


@dataclass(frozen=True)
class Request:
    """One question for one service."""

    prompt: str
    role: str
    service: str
    step_id: str
    run_id: str = ""               # web chats open one conversation per run, and stay in it
    conversation_key: str = ""     # stage:subtask:round, for adapters that key on the step
    timeout_seconds: int = 300
    expect_marker: str = ""        # the contract's sentinel: text without it is not done yet
    artifact_dir: Any = None       # pathlib.Path; screenshots and transport logs land here
    on_sent: Any = None            # called the moment the prompt leaves, and not before
    should_abort: Any = None       # asked while waiting: returns a reason, or None

    def sent(self) -> None:
        """Adapters call this right after the send. The record follows the fact."""
        if self.on_sent is not None:
            self.on_sent()

    def abort_requested(self) -> str | None:
        """Adapters ask this while waiting, so the operator can cut a long wait short."""
        return self.should_abort() if self.should_abort is not None else None


@dataclass(frozen=True)
class Reply:
    text: str
    service: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Health:
    ok: bool
    detail: str
    checked_utc: str = ""


class Adapter(ABC):
    """A channel to one service. Stateless between runs; may hold a session in-process."""

    name: str = "adapter"

    def __init__(self, service: str, config: dict[str, Any]) -> None:
        self.service = service
        self.config = config

    @abstractmethod
    def preflight(self) -> Health:
        """Cheap check that the channel could work. Never sends a prompt."""

    @abstractmethod
    def send(self, request: Request) -> Reply:
        """Deliver the prompt and return the verbatim answer, or raise TransportError."""

    def close(self) -> None:
        """Release whatever the adapter holds. Safe to call more than once."""
