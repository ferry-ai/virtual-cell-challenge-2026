"""The human-in-the-channel adapter: the prompt is handed over, the answer is pasted back.

Web interfaces change without notice, and when one does the honest options are to stop
or to let a person carry the message. This adapter is the second one, made explicit: it
writes the prompt where the operator can copy it, then waits for a reply file to appear.
Nothing is fabricated and nothing is silently substituted -- the run records that this
step went through a human channel.

It doubles as the recovery path after a crash, when a question may already have been
delivered and only the answer is missing.
"""

from __future__ import annotations

import time
from pathlib import Path

from ..util import utc_now
from .base import Adapter, Health, Reply, Request, TransportError

REPLY_FILENAME = "reply.paste.txt"


class ManualAdapter(Adapter):
    name = "manual"

    def __init__(self, service: str, config: dict) -> None:
        super().__init__(service, config)
        self.poll_seconds = float(config.get("poll_seconds", 3))
        self.wait_seconds = int(config.get("wait_seconds", 1800))
        self.announce = bool(config.get("announce", True))

    def preflight(self) -> Health:
        return Health(ok=True, detail="waits for a person", checked_utc=utc_now())

    def send(self, request: Request) -> Reply:
        if request.artifact_dir is None:
            raise TransportError("launch", "the manual adapter needs a step directory",
                                 recoverable=False)
        directory = Path(request.artifact_dir)
        reply_path = directory / REPLY_FILENAME
        if self.announce:
            print(
                f"\n[manuale] {request.service} / {request.role}\n"
                f"  prompt : {directory / 'prompt.txt'}\n"
                f"  incolla la risposta in: {reply_path}\n"
                f"  in attesa fino a {self.wait_seconds}s (Ctrl+C per fermare)\n",
                flush=True)

        request.sent()          # the prompt is on disk, in front of a person
        deadline = time.monotonic() + (request.timeout_seconds or self.wait_seconds)
        while time.monotonic() < deadline:
            if reply_path.is_file():
                # Wait for the file to stop growing: a paste is not atomic.
                size = -1
                while True:
                    current = reply_path.stat().st_size
                    if current == size:
                        break
                    size = current
                    time.sleep(min(1.0, self.poll_seconds))
                text = reply_path.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    return Reply(text=text, service=self.service,
                                 meta={"adapter": self.name, "path": str(reply_path),
                                       "channel": "human"})
            time.sleep(self.poll_seconds)
        raise TransportError("timeout", f"no {REPLY_FILENAME} within the wait window")
