"""Upload progress rendering: bar, transfer rate, and ETA.

Kept separate from both the uploader (which only reports byte counts) and the
CLI (which decides where output goes) so the formatting is unit-testable with a
fake clock instead of eyeballed.

TTY vs pipe matters here: a carriage-return bar is right for a terminal and
useless noise in a log file or CI, so a non-TTY stream gets periodic plain lines
instead (R3 — long operations must show progress, without spamming).
"""

from __future__ import annotations

import time
from collections import deque
from typing import Callable, TextIO

BAR_WIDTH = 24
# Rate is averaged over a short trailing window so it reflects current
# throughput rather than a whole-run average dragged down by a slow start.
RATE_WINDOW_SECONDS = 5.0
MIN_REDRAW_INTERVAL = 0.1   # seconds between TTY repaints
NON_TTY_STEP_PERCENT = 10   # how often to emit a plain line when piped


def format_bytes(n: float) -> str:
    """Human-readable byte count (binary units)."""
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024 or unit == "TiB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TiB"


def format_rate(bytes_per_second: float | None) -> str:
    if not bytes_per_second or bytes_per_second <= 0:
        return "-- B/s"
    return f"{format_bytes(bytes_per_second)}/s"


def format_duration(seconds: float | None) -> str:
    """Compact duration: ``45s``, ``2m03s``, ``1h04m``."""
    if seconds is None or seconds < 0 or seconds != seconds or seconds == float("inf"):
        return "--"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m{seconds % 60:02d}s"
    return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}m"


class ProgressRenderer:
    """Render upload progress to a stream, adapting to TTY vs pipe."""

    def __init__(
        self,
        total: int,
        *,
        stream: TextIO,
        is_tty: bool,
        now: Callable[[], float] = time.monotonic,
        bar_width: int = BAR_WIDTH,
        min_interval: float = MIN_REDRAW_INTERVAL,
        verb: str = "uploaded",
        initial: int | None = None,
    ) -> None:
        self.total = max(int(total), 0)
        self.stream = stream
        self.is_tty = is_tty
        self._now = now
        self.bar_width = bar_width
        self.min_interval = min_interval
        self.verb = verb

        self._start = now()
        self._samples: deque[tuple[float, int]] = deque()
        # -inf so the first update always paints (0.0 would collide with a
        # monotonic clock that starts at 0 and swallow the opening frame).
        self._last_draw = float("-inf")
        self._last_pct_emitted = -1
        self._done = 0
        # Bytes already transferred when we attached (non-zero only on a genuine
        # resume), so the summary reports what THIS run actually moved. Pass it
        # explicitly: inferring it from the first progress callback misreads a
        # fresh transfer's first chunk as a resume point.
        self._start_done: int | None = initial
        self._finished = False

    # -- rate math ------------------------------------------------------------

    def _record(self, done: int) -> None:
        t = self._now()
        self._samples.append((t, done))
        cutoff = t - RATE_WINDOW_SECONDS
        while len(self._samples) > 2 and self._samples[0][0] < cutoff:
            self._samples.popleft()

    def rate(self) -> float | None:
        """Bytes/second over the trailing window (None until measurable)."""
        if len(self._samples) < 2:
            return None
        (t0, b0), (t1, b1) = self._samples[0], self._samples[-1]
        elapsed = t1 - t0
        if elapsed <= 0 or b1 <= b0:
            return None
        return (b1 - b0) / elapsed

    def eta_seconds(self) -> float | None:
        rate = self.rate()
        if not rate or self.total <= 0:
            return None
        remaining = self.total - self._done
        return remaining / rate if remaining > 0 else 0.0

    def percent(self) -> int:
        if self.total <= 0:
            return 100
        return min(100, int(self._done * 100 / self.total))

    # -- rendering ------------------------------------------------------------

    def line(self) -> str:
        pct = self.percent()
        filled = int(self.bar_width * pct / 100)
        bar = "█" * filled + "░" * (self.bar_width - filled)
        return (
            f"[{bar}] {pct:3d}%  "
            f"{format_bytes(self._done)} / {format_bytes(self.total)}  "
            f"{format_rate(self.rate())}  ETA {format_duration(self.eta_seconds())}"
        )

    def update(self, done: int, *, force: bool = False) -> None:
        self._done = min(int(done), self.total) if self.total else int(done)
        if self._start_done is None:
            self._start_done = self._done
        self._record(self._done)
        now = self._now()

        if self.is_tty:
            if not force and (now - self._last_draw) < self.min_interval and self._done < self.total:
                return
            self._last_draw = now
            # \x1b[K erases from the cursor to end of line: the rendered line
            # shrinks as the ETA counts down (2m03s -> 45s), and without this
            # the tail of the previous, longer line stays on screen.
            self.stream.write("\r  " + self.line() + "\x1b[K")
            self.stream.flush()
            return

        # Piped/CI: emit a plain line every NON_TTY_STEP_PERCENT, never \r.
        pct = self.percent()
        step = pct - (pct % NON_TTY_STEP_PERCENT)
        if force or step > self._last_pct_emitted:
            self._last_pct_emitted = step
            self.stream.write("  " + self.line() + "\n")
            self.stream.flush()

    def finish(self) -> None:
        """Final repaint plus a summary line (average rate over the whole run)."""
        if self._finished:
            return
        self._finished = True
        self.update(self._done, force=True)
        if self.is_tty:
            self.stream.write("\n")
        elapsed = max(self._now() - self._start, 1e-9)
        resumed_from = self._start_done or 0
        transferred = max(self._done - resumed_from, 0)
        average = transferred / elapsed
        detail = (
            f"  {self.verb} {format_bytes(transferred)} "
            f"(resumed at {format_bytes(resumed_from)} of {format_bytes(self.total)}) "
            if resumed_from
            else f"  {self.verb} {format_bytes(transferred)} "
        )
        self.stream.write(f"{detail}in {format_duration(elapsed)} (avg {format_rate(average)})\n")
        self.stream.flush()
