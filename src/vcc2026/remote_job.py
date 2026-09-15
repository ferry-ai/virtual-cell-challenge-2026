"""Resumable remote-job primitives: one block, checksums, interrupt recovery.

The operational plan forbids the laptop-download-then-cloud-upload path and
requires that a killed job resume without duplicating rows or re-fetching
bytes already on disk. This module is the local, testable core of that
contract. It does not talk to Kaggle or Colab.

A file that exists only on ephemeral scratch is not a delivery:
`export_and_verify` re-reads the copy on the persistent path and compares
checksums.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

__all__ = [
    "FetchState",
    "ResumableFetcher",
    "export_and_verify",
    "simulate_interrupt",
]


Opener = Callable[[Request], object]


def _hash_file(path: Path, algo: str, *, block: int = 1 << 20) -> str:
    digest = hashlib.new(algo)
    with path.open("rb") as fh:
        while chunk := fh.read(block):
            digest.update(chunk)
    return digest.hexdigest()


def _md5_file(path: Path) -> str:
    return _hash_file(path, "md5")


def _sha256_file(path: Path) -> str:
    return _hash_file(path, "sha256")


@dataclass
class FetchState:
    """On-disk cursor for a resumable GET. Written after every successful chunk."""

    url: str
    dest: str
    expected_bytes: int | None
    expected_md5: str | None
    max_bytes: int | None
    received: int
    done: bool
    md5: str | None = None
    sha256: str | None = None

    def as_dict(self) -> dict:
        return {
            "url": self.url,
            "dest": self.dest,
            "expected_bytes": self.expected_bytes,
            "expected_md5": self.expected_md5,
            "max_bytes": self.max_bytes,
            "received": self.received,
            "done": self.done,
            "md5": self.md5,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "FetchState":
        return cls(
            url=str(payload["url"]),
            dest=str(payload["dest"]),
            expected_bytes=payload.get("expected_bytes"),
            expected_md5=payload.get("expected_md5"),
            max_bytes=payload.get("max_bytes"),
            received=int(payload["received"]),
            done=bool(payload["done"]),
            md5=payload.get("md5"),
            sha256=payload.get("sha256"),
        )


class ResumableFetcher:
    """GET with Range resume, a `.part` file, and a sidecar state JSON.

    The opener is injectable so tests never hit the network. Partial files are
    never renamed onto the destination until size (and md5, if declared) match.
    """

    def __init__(
        self,
        url: str,
        dest: Path,
        *,
        expected_bytes: int | None = None,
        expected_md5: str | None = None,
        max_bytes: int | None = None,
        chunk_bytes: int = 1 << 20,
        opener: Opener | None = None,
    ) -> None:
        if chunk_bytes < 1:
            raise ValueError("chunk_bytes must be positive")
        self.url = url
        self.dest = Path(dest)
        self.part = self.dest.with_suffix(self.dest.suffix + ".part")
        self.state_path = self.dest.with_suffix(self.dest.suffix + ".fetch.json")
        self.expected_bytes = expected_bytes
        self.expected_md5 = expected_md5.lower() if expected_md5 else None
        self.max_bytes = max_bytes
        self.chunk_bytes = chunk_bytes
        self.opener = opener or urlopen

    def _write_state(self, state: FetchState) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.as_dict(), indent=2, sort_keys=True) + "\n"
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(self.state_path)

    def _incomplete(self, received: int) -> FetchState:
        state = FetchState(
            url=self.url,
            dest=str(self.dest),
            expected_bytes=self.expected_bytes,
            expected_md5=self.expected_md5,
            max_bytes=self.max_bytes,
            received=received,
            done=False,
        )
        self._write_state(state)
        return state

    def load_state(self) -> FetchState | None:
        if not self.state_path.exists():
            return None
        return FetchState.from_dict(json.loads(self.state_path.read_text(encoding="utf-8")))

    def _finished_copy(self) -> FetchState | None:
        if not self.dest.exists():
            return None
        size = self.dest.stat().st_size
        if self.expected_bytes is not None and size != self.expected_bytes:
            return None
        md5 = _md5_file(self.dest)
        if self.expected_md5 is not None and md5 != self.expected_md5:
            raise RuntimeError(
                f"existing {self.dest} md5 {md5} != declared {self.expected_md5}"
            )
        state = FetchState(
            url=self.url,
            dest=str(self.dest),
            expected_bytes=self.expected_bytes,
            expected_md5=self.expected_md5,
            max_bytes=self.max_bytes,
            received=size,
            done=True,
            md5=md5,
            sha256=_sha256_file(self.dest),
        )
        self._write_state(state)
        return state

    def fetch(self, *, stop_after: int | None = None) -> FetchState:
        """Download or resume. `stop_after` is the test hook that simulates a kill."""
        existing = self._finished_copy()
        if existing is not None:
            return existing

        self.part.parent.mkdir(parents=True, exist_ok=True)
        received = self.part.stat().st_size if self.part.exists() else 0
        if self.max_bytes is not None and received > self.max_bytes:
            raise RuntimeError(
                f"partial file {self.part} is {received} bytes, over the "
                f"cap of {self.max_bytes}"
            )

        written_this_call = 0
        mode = "ab" if received else "wb"
        with self.part.open(mode) as fh:
            while True:
                if self.expected_bytes is not None and received >= self.expected_bytes:
                    break
                if self.max_bytes is not None and received >= self.max_bytes:
                    raise RuntimeError(
                        f"byte cap {self.max_bytes} reached for {self.url}"
                    )
                if stop_after is not None and written_this_call >= stop_after:
                    return self._incomplete(received)

                headers = {"Range": f"bytes={received}-"} if received else {}
                request = Request(self.url, headers=headers)
                try:
                    response = self.opener(request)
                except HTTPError as exc:
                    raise RuntimeError(f"HTTP {exc.code} for {self.url}") from exc
                except URLError as exc:
                    raise RuntimeError(f"URL error for {self.url}: {exc}") from exc

                got_any = False
                hit_cap = False
                with response:
                    status = getattr(response, "status", None) or response.getcode()
                    if received and status == 200:
                        raise RuntimeError(
                            f"server ignored Range for {self.url}; refusing to "
                            f"restart a {received}-byte partial"
                        )
                    if received and status != 206:
                        raise RuntimeError(
                            f"resume of {self.url} returned HTTP {status}, not 206"
                        )
                    while True:
                        if stop_after is not None and written_this_call >= stop_after:
                            break
                        to_read = self.chunk_bytes
                        if self.max_bytes is not None:
                            to_read = min(to_read, self.max_bytes - received)
                        if stop_after is not None:
                            to_read = min(to_read, stop_after - written_this_call)
                        if to_read <= 0:
                            hit_cap = self.max_bytes is not None and received >= self.max_bytes
                            break
                        data = response.read(to_read)
                        if not data:
                            break
                        fh.write(data)
                        received += len(data)
                        written_this_call += len(data)
                        got_any = True
                        if self.max_bytes is not None and received >= self.max_bytes:
                            hit_cap = True
                            break

                if stop_after is not None and written_this_call >= stop_after:
                    return self._incomplete(received)
                if hit_cap and (
                    self.expected_bytes is None or received < self.expected_bytes
                ):
                    self._incomplete(received)
                    raise RuntimeError(
                        f"byte cap {self.max_bytes} reached for {self.url}"
                    )
                if self.expected_bytes is None:
                    break
                if received >= self.expected_bytes:
                    break
                if not got_any:
                    raise RuntimeError(
                        f"{self.url} closed after {received} bytes, "
                        f"expected {self.expected_bytes}"
                    )

        if self.expected_bytes is not None and received != self.expected_bytes:
            self._incomplete(received)
            raise RuntimeError(
                f"{self.part} has {received} bytes, expected {self.expected_bytes}"
            )
        md5 = _md5_file(self.part)
        if self.expected_md5 is not None and md5 != self.expected_md5:
            raise RuntimeError(
                f"md5 mismatch for {self.part}: got {md5}, expected {self.expected_md5}"
            )
        sha = _sha256_file(self.part)
        self.part.replace(self.dest)
        state = FetchState(
            url=self.url,
            dest=str(self.dest),
            expected_bytes=self.expected_bytes,
            expected_md5=self.expected_md5,
            max_bytes=self.max_bytes,
            received=received,
            done=True,
            md5=md5,
            sha256=sha,
        )
        self._write_state(state)
        return state


def simulate_interrupt(
    fetcher: ResumableFetcher, *, first_bytes: int
) -> tuple[FetchState, FetchState]:
    """Kill after `first_bytes`, then resume. Used as the contract's self-test."""
    first = fetcher.fetch(stop_after=first_bytes)
    if first.done:
        raise RuntimeError("interrupt simulation finished in one shot; lower first_bytes")
    second = fetcher.fetch()
    if not second.done:
        raise RuntimeError("resume did not finish")
    return first, second


def export_and_verify(src: Path, dest: Path) -> dict:
    """Copy to the persistent path and refuse to report success on hash mismatch."""
    dest = Path(dest)
    sidecar = dest.with_suffix(dest.suffix + ".export.json")
    if dest.exists() or sidecar.exists():
        raise FileExistsError(
            f"{dest} or {sidecar} exists; exports are evidence. Use a new path."
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = Path(src).read_bytes()
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(dest)
    src_hash = hashlib.sha256(data).hexdigest()
    dest_hash = _sha256_file(dest)
    if src_hash != dest_hash:
        raise RuntimeError(
            f"export hash mismatch: source {src_hash} vs persistent {dest_hash}"
        )
    record = {
        "source": str(src),
        "persistent": str(dest),
        "bytes": len(data),
        "sha256": dest_hash,
        "reread_ok": True,
        "claim": "measured",
    }
    sidecar.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
