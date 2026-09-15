"""Web chats driven in the operator's own browser session, through Playwright.

The channel is the visible interface: a real browser window, a real login the operator
performed by hand, a real message typed into the composer. No session token is read out
of the browser and no private endpoint is called -- partly because the operator asked
for it, and partly because a page we can watch fails visibly while a scraped endpoint
fails silently.

Three things keep this honest:

* **Selectors live in configuration, not in code** (`configs/orchestrator/services/*`).
  A UI change is then a config edit and a loud failure, not a rewrite.
* **A profile must be marked verified before it may send.** Nobody can know another
  product's DOM by thinking about it; `orch probe` looks, the operator confirms, and only
  then does `verified: true` unlock sending. Guessing into an unknown page is how a
  prompt ends up in the wrong box.
* **The profile directory is a browser profile the operator owns**, kept outside the
  repository (the repository is inside OneDrive, which must not sync a browser profile).
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable

from ..protocol import looks_truncated
from ..util import sha256_text, utc_now, write_json_new, write_new
from .base import Adapter, Health, Reply, Request, TransportError

# Turns one rendered assistant message back into text that still has its code fences.
# Chat UIs render markdown, and innerText drops the ``` markers our reply contract needs.
_EXTRACT_JS = """
(element) => {
  const parts = [];
  const walk = (node) => {
    if (node.nodeType === Node.TEXT_NODE) { parts.push(node.textContent); return; }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    const tag = node.tagName.toLowerCase();
    if (tag === 'pre') {
      const code = node.innerText.replace(/\\s+$/, '');
      parts.push('\\n```\\n' + code + '\\n```\\n');
      return;
    }
    if (tag === 'br') { parts.push('\\n'); return; }
    if (tag === 'button' || tag === 'svg' || tag === 'style' || tag === 'script') return;
    for (const child of node.childNodes) walk(child);
    if (['p','div','li','h1','h2','h3','h4','tr'].includes(tag)) parts.push('\\n');
  };
  walk(element);
  return parts.join('').replace(/\\n{3,}/g, '\\n\\n').trim();
}
"""

_CONVERSATION_LINK_JS = """
() => {
  const skip = new Set(['history', 'new', 'chat', 'c', '']);
  const links = Array.from(document.querySelectorAll(
    "a[href*='/chat/'], a[href*='/c/'], a[href*='/conversation']"));
  for (const anchor of links) {
    const parts = new URL(anchor.href).pathname.split('/').filter(Boolean);
    const last = parts[parts.length - 1] || '';
    if (!skip.has(last) && last.length >= 6) return anchor.href;
  }
  return '';
}
"""

_PROBE_JS = """
() => {
  const describe = (element) => {
    const attributes = {};
    for (const name of ['id','name','class','aria-label','placeholder','data-testid','role','type']) {
      const value = element.getAttribute(name);
      if (value) attributes[name] = value.slice(0, 120);
    }
    const box = element.getBoundingClientRect();
    return {tag: element.tagName.toLowerCase(), attributes,
            visible: box.width > 0 && box.height > 0,
            width: Math.round(box.width), height: Math.round(box.height),
            text: (element.innerText || '').slice(0, 80)};
  };
  const collect = (selector, limit) =>
    Array.from(document.querySelectorAll(selector)).slice(0, limit).map(describe);
  return {
    url: location.href,
    title: document.title,
    editors: collect('textarea, [contenteditable="true"], input[type="text"]', 12),
    buttons: collect('button, [role="button"]', 40),
    message_candidates: collect('[data-message-author-role], [class*="markdown"], [class*="message"], article', 25),
  };
}
"""


# --------------------------------------------------------------- the one runtime
#
# Playwright's sync API keeps one driver per process, and starting a second one while the
# first is alive kills the process. Two services in the same run are two adapters, so the
# runtime is shared and reference-counted here, while each adapter keeps its own browser
# context and its own profile directory. That separation is the part that matters: shared
# runtime, separate sessions.
_RUNTIME_LOCK = threading.RLock()
_runtime: Any = None
_runtime_users = 0
_runtime_factory: Callable[[], Any] | None = None      # tests inject a fake here


def set_runtime_factory(factory: Callable[[], Any] | None) -> None:
    """Replace how the runtime is started. Only tests use this."""
    global _runtime_factory
    with _RUNTIME_LOCK:
        _runtime_factory = factory


def acquire_runtime() -> Any:
    """Start the shared runtime if nobody holds it yet, and take a reference."""
    global _runtime, _runtime_users
    with _RUNTIME_LOCK:
        if _runtime is None:
            if _runtime_factory is not None:
                _runtime = _runtime_factory()
            else:
                from playwright.sync_api import sync_playwright  # noqa: PLC0415
                _runtime = sync_playwright().start()
        _runtime_users += 1
        return _runtime


def release_runtime() -> None:
    """Give a reference back, and stop the runtime when the last holder lets go."""
    global _runtime, _runtime_users
    with _RUNTIME_LOCK:
        _runtime_users = max(0, _runtime_users - 1)
        if _runtime_users == 0 and _runtime is not None:
            handle, _runtime = _runtime, None
            try:
                handle.stop()
            except Exception:  # noqa: BLE001, S110 - shutting down must not raise
                pass


def runtime_users() -> int:
    with _RUNTIME_LOCK:
        return _runtime_users


class WebChatAdapter(Adapter):
    """One persistent browser profile per service, kept open for the life of a run."""

    name = "web"

    def __init__(self, service: str, config: dict) -> None:
        super().__init__(service, config)
        self.profile: dict[str, Any] = config.get("profile_data") or {}
        self.user_data_dir = Path(config["user_data_dir"]).resolve()
        self.channel: str = str(config.get("browser_channel", "chrome"))
        self.headless: bool = bool(config.get("headless", False))
        self.slow_mo_ms: int = int(config.get("slow_mo_ms", 120))
        self.allow_unverified: bool = bool(config.get("allow_unverified", False))
        # Playwright disables Chrome's translate UI by default, among other features.
        # Harmless for automation, but the operator has to read these pages.
        self.enable_translate: bool = bool(config.get("enable_translate", False))
        self.locale: str | None = config.get("locale") or self.profile.get("locale")
        self.window_size: str = str(config.get("window_size")
                                    or self.profile.get("window_size") or "1500,1000")
        self._playwright = None
        self._holds_runtime = False
        self._context = None
        self._page = None
        self._modes_applied: dict[str, bool] = {}
        # One signed-in session can hold more than one seat, so the thread it is in is
        # keyed by seat and not by run: `key -> url` for every thread opened, plus which
        # one the page is showing right now.
        self._conversations: dict[str, str] = {}
        self._conversation_for: str | None = None
        self._conversation_url: str = ""

    # ------------------------------------------------------------------- profile
    @property
    def url(self) -> str:
        return str(self.profile.get("url", ""))

    @property
    def selectors(self) -> dict[str, str]:
        return dict(self.profile.get("selectors") or {})

    @property
    def waits(self) -> dict[str, Any]:
        defaults = {"page_load_seconds": 90, "response_timeout_seconds": 420,
                    "stable_seconds": 4, "after_send_seconds": 2,
                    "truncated_grace_seconds": 45, "notice_after_seconds": 120}
        defaults.update(self.profile.get("wait") or {})
        return defaults

    @property
    def is_verified(self) -> bool:
        return bool(self.profile.get("verified"))

    @property
    def requested_modes(self) -> dict[str, bool]:
        """Composer switches the run wants, as name -> desired state, from configuration."""
        raw = self.config.get("modes") or {}
        if isinstance(raw, list):
            return {str(name): True for name in raw}
        return {str(name): bool(value) for name, value in raw.items()}

    # ------------------------------------------------------------------- browser
    def _require_playwright(self):
        try:
            from playwright.sync_api import sync_playwright  # noqa: PLC0415
        except ModuleNotFoundError as error:
            raise TransportError(
                "launch",
                "playwright is not installed in this environment; run `orch doctor` for "
                "the exact command",
                recoverable=False) from error
        return sync_playwright

    def _launch_options(self) -> dict[str, Any]:
        """How the browser is started. Kept apart from starting it, so it can be tested.

        The viewport is the part that bit: in a visible window an emulated viewport is not
        the window, so the page renders at 1280x900 inside whatever size the window happens
        to be, and everything below the fold -- the composer, the cookie banner -- is
        simply not on screen. Headed means no_viewport plus a real window size; only the
        headless case, where there is no window, keeps an emulated one.
        """
        options: dict[str, Any] = {
            "user_data_dir": str(self.user_data_dir),
            "headless": self.headless,
            "slow_mo": self.slow_mo_ms,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if self.headless:
            options["viewport"] = {"width": 1280, "height": 900}
        else:
            options["no_viewport"] = True
            options["args"].append(f"--window-size={self.window_size}")
        if self.channel:
            options["channel"] = self.channel
        if self.locale:
            options["locale"] = self.locale
        if self.enable_translate:
            # Drops Playwright's whole --disable-features list, which contains Translate.
            # Only used where a person is looking at the page, not during a run.
            options["ignore_default_args"] = ["--disable-features"]
        return options

    def open(self, *, url: str | None = None):
        """Open (or reuse) the persistent context and return the page."""
        if self._page is not None:
            return self._page
        self._require_playwright()
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._playwright = acquire_runtime()
        except Exception as error:  # noqa: BLE001
            raise TransportError("launch", f"the browser runtime would not start: "
                                           f"{str(error)[:400]}", recoverable=False) from error
        self._holds_runtime = True
        try:
            self._context = self._playwright.chromium.launch_persistent_context(
                **self._launch_options())
        except Exception as error:  # noqa: BLE001 - playwright raises many shapes
            self.close()
            raise TransportError("launch", str(error)[:600], recoverable=False) from error
        self._context.set_default_timeout(self.waits["page_load_seconds"] * 1000)
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        # Keep exactly one page. Extra tabs are where these interfaces start spinning, and
        # a background tab we never look at can hold the session busy for the one we do.
        self._context.on("page", lambda opened: opened.close()
                         if opened is not self._page else None)
        target = url or self.url
        if target:
            try:
                self._page.goto(target, wait_until="domcontentloaded")
            except Exception as error:  # noqa: BLE001
                raise TransportError("navigation", str(error)[:600]) from error
        return self._page

    def close(self) -> None:
        if self._context is not None:
            try:
                self._context.close()
            except Exception:  # noqa: BLE001, S110 - closing must not mask the real error
                pass
            self._context = None
        if self._holds_runtime:
            release_runtime()       # the runtime stops only when the last adapter lets go
            self._holds_runtime = False
        self._playwright = None
        self._page = None

    @staticmethod
    def conversation_key(run_id: str, role: str) -> str:
        """Which thread a question belongs to: the seat inside the run, not the run.

        A reserve covering a service that went quiet is a second conversation in the
        session that is still answering -- not a second browser profile. A separate
        profile directory is a separate browser identity: it inherits the verified
        selector map and none of the environment those selectors were verified in
        (interface language, dismissed dialogs, preferences), and it buys nothing at all
        unless a second account is signed into it.
        """
        return f"{run_id}:{role}" if run_id and role else run_id

    def ensure_conversation(self, key: str, artifacts: Path | None = None) -> str:
        """Open a fresh conversation for this key, then stay in it for every round.

        One thread per seat per execution, not one per message: the rounds of a run read
        as a conversation in the service's own history, which is what makes a run
        auditable from the other side too. It is not a dependency -- every prompt carries
        the whole state it needs -- so a service that loses the thread costs context, not
        correctness.

        Why the seat and not just the run: were a stand-in to answer in the seat holder's
        own thread, it would read the holder's previous answers as its own context, and
        the two voices the loop exists to keep apart would quietly become one
        conversation.
        """
        page = self.open()
        if self._conversation_for == key:
            return self._conversation_url

        known = self._conversations.get(key)
        if known:
            # Back to a thread this session already opened, instead of starting a second
            # one for the same seat. The switches are checked again on arrival: one that
            # the interface reset while we were in the other conversation would otherwise
            # change what the run is comparing without saying so.
            try:
                page.goto(known, wait_until="domcontentloaded")
                page.wait_for_selector(self.selectors["editor"], timeout=30_000)
            except Exception as error:  # noqa: BLE001
                self._dump(page, artifacts, "conversation-return-failed")
                raise TransportError(
                    "navigation",
                    f"could not return to the conversation for {key}: "
                    f"{str(error)[:400]}") from error
            self.apply_modes(page, artifacts)
            self._conversation_for = key
            self._conversation_url = page.url
            return self._conversation_url

        target = self.profile.get("new_chat_url") or ""
        selector = self.selectors.get("new_chat", "")
        try:
            if target:
                page.goto(target, wait_until="domcontentloaded")
            elif selector:
                page.locator(selector).last.click(timeout=15_000)
            else:
                page.goto(self.url, wait_until="domcontentloaded")
            page.wait_for_selector(self.selectors["editor"], timeout=30_000)
        except Exception as error:  # noqa: BLE001
            self._dump(page, artifacts, "new-conversation-failed")
            raise TransportError(
                "navigation",
                f"could not open a new conversation: {str(error)[:400]}") from error
        self.apply_modes(page, artifacts)      # before the first message, never after
        self._conversations[key] = page.url
        self._conversation_for = key
        self._conversation_url = page.url
        return self._conversation_url

    # --------------------------------------------------------------------- modes
    def _mode_state(self, locator, spec: dict) -> bool | None:
        """Is the switch in the wanted state? None when it cannot be found at all.

        Two shapes, because interfaces differ. A toggle carries its state in an attribute
        (`aria-pressed`); a dropdown shows it as text (`Alto` next to the model name).
        Reading text is not weaker: it is what a person reads to know the same thing.
        """
        expected_text = spec.get("state_text")
        try:
            if expected_text is not None:
                current = locator.inner_text(timeout=8_000)
                return current.strip().casefold() == str(expected_text).strip().casefold()
            value = locator.get_attribute(str(spec.get("state_attribute", "aria-pressed")),
                                          timeout=8_000)
        except Exception:  # noqa: BLE001
            return None
        return None if value is None else (value == str(spec.get("on_value", "true")))

    def apply_modes(self, page, artifacts: Path | None = None) -> dict[str, bool]:
        """Put the composer switches in the state the configuration asks for, and check.

        The point is not convenience: it is that a run must not depend on what the
        interface happens to remember. A campaign whose first round ran with extended
        reasoning and whose third ran without it would compare two different things
        without saying so. If a switch cannot be verified afterwards, nothing is sent.

        A mode marked `settable: false` is only ever *checked*. Some controls are menus
        whose paths have not been mapped, and clicking blindly through an unmapped menu is
        how a run ends up in a state nobody chose.
        """
        described = self.profile.get("modes") or {}
        applied: dict[str, bool] = {}
        for name, desired in self.requested_modes.items():
            spec = described.get(name)
            if not spec or not spec.get("selector"):
                raise TransportError(
                    "navigation",
                    f"the run asks for mode '{name}' but the profile of {self.service} does "
                    f"not describe it", recoverable=False)
            locator = page.locator(spec["selector"]).first
            state = self._mode_state(locator, spec)
            if state is None:
                self._dump(page, artifacts, f"mode-{name}-missing")
                raise TransportError(
                    "navigation",
                    f"mode '{name}': the control was not found ({spec['selector']}). The "
                    f"interface may have changed, or the label may be in another language.",
                    recoverable=False)
            if state != desired and not spec.get("settable", True):
                self._dump(page, artifacts, f"mode-{name}-manual")
                raise TransportError(
                    "navigation",
                    f"mode '{name}': wanted {desired} and the interface says otherwise. This "
                    f"control is check-only ({spec.get('note', 'set it by hand')}): nothing "
                    f"is sent until it is set.", recoverable=False)
            if state != desired:
                try:
                    locator.click(timeout=10_000)
                except Exception as error:  # noqa: BLE001
                    self._dump(page, artifacts, f"mode-{name}-click")
                    raise TransportError(
                        "navigation",
                        f"mode '{name}': the switch would not take a click: {str(error)[:200]}",
                        recoverable=False) from error
                time.sleep(1.0)
                state = self._mode_state(locator, spec)
            if state != desired:
                self._dump(page, artifacts, f"mode-{name}-refused")
                raise TransportError(
                    "navigation",
                    f"mode '{name}': wanted {desired}, it stayed {state}. Nothing is sent in "
                    f"a state other than the declared one.", recoverable=False)
            applied[name] = desired
        self._modes_applied = applied
        return applied

    # -------------------------------------------------------------------- checks
    def preflight(self) -> Health:
        missing = [key for key in ("editor", "message") if not self.selectors.get(key)]
        if not self.url or missing:
            return Health(ok=False, checked_utc=utc_now(),
                          detail=f"profile incomplete: missing {', '.join(missing) or 'url'}")
        described = self.profile.get("modes") or {}
        undescribed = [name for name in self.requested_modes if name not in described]
        if undescribed:
            return Health(ok=False, checked_utc=utc_now(),
                          detail=f"modes requested but not described in the profile: "
                                 f"{', '.join(undescribed)}")
        if not self.is_verified and not self.allow_unverified:
            return Health(ok=False, checked_utc=utc_now(),
                          detail=("profile not verified: run `orch probe " + self.service +
                                  "`, fill the selectors, then set verified: true"))
        try:
            self._require_playwright()
        except TransportError as error:
            return Health(ok=False, detail=error.detail, checked_utc=utc_now())
        wanted = ", ".join(f"{name}={'on' if value else 'off'}"
                           for name, value in sorted(self.requested_modes.items()))
        # A verified selector map says the page is understood; it says nothing about
        # whether *this* session ever signed in. A reserve session inherits the first and
        # not the second, so an unused profile directory is worth showing before a run
        # discovers it mid-round.
        used = (self.user_data_dir / "Default").exists()
        return Health(ok=True, checked_utc=utc_now(),
                      detail=f"profile {self.service}, verified "
                             f"{self.profile.get('verified_on', 'date unknown')}"
                             + (f"; modalita': {wanted}" if wanted else "")
                             + (f"; sessione {self.user_data_dir.name}" if used else
                                f"; sessione {self.user_data_dir.name} MAI USATA: "
                                f"`orch login {self.service}` prima di contarci"))

    def _detect_logged_out(self, page) -> str | None:
        marker = self.selectors.get("logged_out")
        if marker:
            try:
                if page.locator(marker).first.is_visible(timeout=1500):
                    return f"logged-out marker visible ({marker})"
            except Exception:  # noqa: BLE001
                pass
        for fragment in self.profile.get("logged_out_url_fragments", []) or []:
            if fragment.lower() in page.url.lower():
                return f"url looks like a login page ({fragment})"
        return None

    # ---------------------------------------------------------------------- send
    def send(self, request: Request) -> Reply:
        if not self.is_verified and not self.allow_unverified:
            raise TransportError(
                "launch",
                f"the profile for {self.service} is not marked verified; refusing to type "
                f"into a page whose composer has not been confirmed",
                recoverable=False)
        page = self.open()
        artifacts = Path(request.artifact_dir) if request.artifact_dir else None

        logged_out = self._detect_logged_out(page)
        if not logged_out and request.run_id:
            self.ensure_conversation(
                self.conversation_key(request.run_id, request.role), artifacts)
            logged_out = self._detect_logged_out(page)
        if logged_out:
            self._dump(page, artifacts, "logged-out")
            raise TransportError("auth", f"{self.service}: {logged_out}. Run "
                                         f"`orch login {self.service}` and sign in by hand.",
                                 recoverable=False)

        editor = self.selectors["editor"]
        message = self.selectors["message"]
        try:
            before, before_text = self._message_state(page, message)
            self._compose(page, editor, request.prompt, artifacts)
            send_selector = self.selectors.get("send")
            if send_selector:
                page.locator(send_selector).last.click(timeout=15_000)
            else:
                page.keyboard.press(str(self.profile.get("send_key", "Enter")))
            request.sent()          # from here on, the question is out there
        except TransportError:
            raise
        except Exception as error:  # noqa: BLE001
            self._dump(page, artifacts, "compose-failed")
            raise TransportError("navigation", f"could not compose: {str(error)[:400]}") from error

        text, waited = self._await_reply(page, message, before, before_text, request,
                                         artifacts)
        return Reply(text=text, service=self.service,
                     meta={"adapter": self.name, "url": page.url,
                           "conversation_url": self._conversation_url,
                           "conversation_for_run": request.run_id,
                           "conversation_key": self._conversation_for,
                           "modes": dict(self._modes_applied),
                           "prompt_sha256": sha256_text(request.prompt),
                           "prompt_chars": len(request.prompt), "reply_chars": len(text),
                           "waited_seconds": waited, "looked_truncated": looks_truncated(text),
                           "messages_before": before, "channel": "browser"})

    def _compose(self, page, editor: str, prompt: str, artifacts: Path | None) -> None:
        """Put the whole prompt in the composer, then check that it is actually there.

        Never with `type()`. A prompt is long and multi-line, and in a chat composer every
        newline typed as a key event is a send: the question would leave in fragments,
        each one a message of its own. `fill()` sets the text without pressing anything.
        When an editor refuses that -- some rich composers ignore programmatic input --
        the fallback types line by line and uses Shift+Enter for the newlines, which
        inserts instead of sending. Either way the content is read back before anything
        is sent, because a half-written prompt is worse than a failure.
        """
        box = page.locator(editor).last
        box.click(timeout=15_000)
        try:
            box.fill(prompt, timeout=30_000)
        except Exception:  # noqa: BLE001 - some composers refuse fill(); try the slow way
            pass

        if not self._composer_holds(box, prompt):
            box.click(timeout=15_000)
            try:
                box.fill("", timeout=10_000)
            except Exception:  # noqa: BLE001
                page.keyboard.press("Control+A")
                page.keyboard.press("Delete")
            lines = prompt.splitlines()
            for index, line in enumerate(lines):
                if index:
                    page.keyboard.press("Shift+Enter")   # a newline, not a send
                if line:
                    page.keyboard.type(line)

        if not self._composer_holds(box, prompt):
            self._dump(page, artifacts, "composer-mismatch")
            raise TransportError(
                "navigation",
                "the composer does not hold the whole prompt after writing it: refusing to "
                "send a truncated question", recoverable=False)

    @staticmethod
    def _composer_holds(box, prompt: str) -> bool:
        """Compare what is in the box with what should be, tolerating trimming."""
        try:
            current = box.input_value(timeout=5_000)
        except Exception:  # noqa: BLE001 - contenteditable has no value
            try:
                current = box.inner_text(timeout=5_000)
            except Exception:  # noqa: BLE001
                return False
        if not current:
            return False
        squeeze = " ".join(current.split())
        wanted = " ".join(prompt.split())
        return squeeze[:200] == wanted[:200] and abs(len(squeeze) - len(wanted)) <= max(
            20, len(wanted) // 50)

    def _message_state(self, page, message: str) -> tuple[int, str]:
        """How many assistant messages are in the page, and what the last one says.

        Both halves are needed to recognise an answer, and the second is the one that
        matters on a long conversation -- see `_is_new_answer`.
        """
        try:
            count = page.locator(message).count()
            if count == 0:
                return 0, ""
            return count, page.locator(message).nth(count - 1).evaluate(_EXTRACT_JS) or ""
        except Exception:  # noqa: BLE001 - a page mid-render is not a failure
            return 0, ""

    @staticmethod
    def _is_new_answer(count: int, text: str, before_count: int, before_text: str) -> bool:
        """Whether the last assistant message is the answer to the question just asked.

        **Counting messages is not enough, and that cost a real run.** On 2026-09-14 the
        third question of a research campaign was answered by DeepSeek in full, and the
        adapter waited ten minutes and gave up with the answer on screen: these interfaces
        keep only a window of messages in the DOM, so when the new answer arrived the
        oldest one was dropped and the count stayed exactly where it was. A rule that
        waits for `count > before` waits for a number that, on a long enough conversation,
        can never change again.

        The answer is always the *last* assistant message, so that is what we watch.
        Pruning at the top does not touch it; scrolling does not touch it; a new answer
        does, from its first streamed characters. The count is kept as a second signal
        because it is the one that works when the previous answer is still on screen.

        The gap that remains, stated rather than hidden: an answer byte-identical to the
        one before it, on a conversation whose message list did not grow, is invisible
        here. The timeout still catches it, and the dump still holds the evidence.
        """
        if not text:
            return False
        return count > before_count or text != before_text

    def _await_reply(self, page, message: str, before: int, before_text: str,
                     request: Request, artifacts: Path | None) -> tuple[str, float]:
        """Wait for a complete answer: stable text, no streaming marker, no open fence.

        Stability is not completeness. A stream that stalls mid-block looks stable for a
        few seconds and would hand back half a result, which the next round would then
        quote as a position someone took. So a text that still has an unclosed code fence
        buys one extra window before being accepted, and whatever is accepted is recorded
        with the measurement that says whether it looked whole.
        """
        waits = self.waits
        started = time.monotonic()
        deadline = started + (request.timeout_seconds or waits["response_timeout_seconds"])
        streaming = self.selectors.get("streaming")
        stable_for = float(waits["stable_seconds"])
        grace = float(waits.get("truncated_grace_seconds", 45))
        time.sleep(float(waits["after_send_seconds"]))

        last_text, unchanged_since, extended = "", None, False
        noticed = False
        marker = (request.expect_marker or "").strip()
        refusals = [str(phrase).casefold()
                    for phrase in (self.profile.get("service_refusals") or [])]
        notice_after = float(waits.get("notice_after_seconds", 0) or 0)

        while time.monotonic() < deadline:
            reason = request.abort_requested()
            if reason:
                raise TransportError("unknown", f"interrotto dall'operatore: {reason}",
                                     delivered=True)
            try:
                count = page.locator(message).count()
                latest = (page.locator(message).nth(count - 1).evaluate(_EXTRACT_JS)
                          if count else "")
                current = (latest
                           if self._is_new_answer(count, latest, before, before_text)
                           else "")
            except Exception as error:  # noqa: BLE001
                self._dump(page, artifacts, "read-failed")
                raise TransportError(
                    "navigation", f"could not read the reply: {str(error)[:400]}") from error

            if refusals and not current:
                # Nothing from the model yet: if the page is showing a refusal -- too much
                # traffic, upgrade to keep priority -- there is no point waiting out the
                # whole timeout. Checked only while no answer has appeared, so a model that
                # writes the word "traffico" in its answer does not trip it.
                try:
                    page_text = page.evaluate(
                        "() => document.body.innerText.slice(0, 4000)").casefold()
                except Exception:  # noqa: BLE001
                    page_text = ""
                hit = next((phrase for phrase in refusals if phrase in page_text), None)
                if hit:
                    self._dump(page, artifacts, "service-refusal")
                    raise TransportError(
                        "rate_limit",
                        f"il servizio ha rifiutato: la pagina dice «{hit}». Il messaggio era "
                        f"gia' partito, quindi non lo rimando.", delivered=True)

            if notice_after and not noticed and time.monotonic() - started >= notice_after:
                noticed = True
                remaining = int(deadline - time.monotonic())
                for line in (
                    "",
                    f"[attesa] {self.service} non ha ancora risposto dopo "
                    f"{int(notice_after)}s. Aspetto ancora {remaining}s prima di rinunciare.",
                    "  per non aspettare: `orch skip` da un altro terminale (salta questo "
                    "passo), oppure `orch stop` (ferma il run).",
                    "",
                ):
                    print(line, flush=True)

            busy = False
            if streaming:
                try:
                    busy = page.locator(streaming).first.is_visible(timeout=500)
                except Exception:  # noqa: BLE001
                    busy = False

            if current and current == last_text and not busy:
                if unchanged_since is None:
                    unchanged_since = time.monotonic()
                elif time.monotonic() - unchanged_since >= stable_for:
                    if marker and marker not in current:
                        # Stable is not finished. These models write a preamble -- «procedo
                        # con la ricerca mirata» -- then pause to search, sometimes for a
                        # minute or more, then write the answer. Four seconds of silence in
                        # that pause looks exactly like a completed reply, and on
                        # 2026-09-14 Kimi's phase-3 answer was thrown away for it: 422
                        # characters of preamble were accepted, failed the contract, and
                        # spent the one repair the budget allows.
                        #
                        # So while the contract's marker is absent we keep waiting, up to
                        # the deadline the operator set. The cost is real -- a model that
                        # never emits the marker now burns its whole timeout instead of
                        # failing fast -- and it is the cheaper of the two mistakes: the
                        # half-answer is the one that quietly loses work. `orch skip` and
                        # the half-time notice exist for the pathological case.
                        unchanged_since = None
                    elif looks_truncated(current) and not extended:
                        extended = True          # it may still be writing the block
                        deadline = min(deadline, time.monotonic() + grace)
                        unchanged_since = None
                    else:
                        return current, round(time.monotonic() - started, 1)
            else:
                unchanged_since = None
                last_text = current
            time.sleep(1.0)

        elapsed = round(time.monotonic() - started, 1)
        if last_text:
            self._dump(page, artifacts, "incomplete")
            # Hand back what arrived. The engine reads it as a content problem, asks for
            # the result block again, and never forwards it as though it were whole.
            return last_text, elapsed
        recovered = self._recover_after_hang(page, message, before, before_text, artifacts)
        if recovered:
            return recovered, round(time.monotonic() - started, 1)
        self._dump(page, artifacts, "timeout")
        raise TransportError(
            "timeout",
            "the message was sent and no answer ever appeared, not even after a reload. "
            "It is not resent automatically: look at the conversation and use "
            "`orch reconcile`.",
            delivered=True)

    def _recover_after_hang(self, page, message: str, before: int, before_text: str,
                            artifacts: Path | None) -> str:
        """One reload before giving up: the answer is often there, the page just stopped.

        This is the observed failure mode of these interfaces -- a request that never
        settles while the reply exists on the server. Reloading reads it instead of asking
        the question a second time.

        It uses the same rule as the wait loop, and for the same reason: after a reload of
        a long conversation the message list is usually *shorter* than before, so a check
        on the count would throw away the very answer the reload went to fetch.
        """
        try:
            page.reload(wait_until="domcontentloaded")
            self.settle(page, 20.0)
            count, text = self._message_state(page, message)
            if self._is_new_answer(count, text, before, before_text):
                if text and not looks_truncated(text):
                    return text
        except Exception:  # noqa: BLE001 - recovery is best effort, never a new failure
            pass
        return ""

    # ------------------------------------------------------------------ forensics
    def _dump(self, page, artifacts: Path | None, tag: str) -> None:
        """A failure leaves evidence: what the page looked like when it broke."""
        if artifacts is None:
            return
        stamp = utc_now().replace(":", "").replace("-", "")
        try:
            page.screenshot(path=str(artifacts / f"{tag}-{stamp}.png"), full_page=False)
        except Exception:  # noqa: BLE001
            pass
        try:
            write_new(artifacts / f"{tag}-{stamp}.html", page.content()[:2_000_000])
        except Exception:  # noqa: BLE001
            pass

    # ---------------------------------------------------------------------- probe
    def settle(self, page, seconds: float = 25.0) -> float:
        """Wait for a single-page app to actually render, not merely to load.

        `domcontentloaded` fires on the empty shell of these interfaces: the first probe
        written here looked at a blank page and reported no composer at all. So the wait
        is for something interactive to exist, with the time it took recorded next to what
        was seen.
        """
        started = time.monotonic()
        deadline = started + seconds
        try:
            page.wait_for_load_state("networkidle", timeout=int(seconds * 1000))
        except Exception:  # noqa: BLE001 - a chat page may never go idle
            pass
        query = ("() => document.querySelectorAll("
                 "'button,[role=\"button\"],textarea,[contenteditable=\"true\"]').length")
        while time.monotonic() < deadline:
            try:
                if page.evaluate(query):
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(1.0)
        time.sleep(1.5)                      # let the last paint land
        return round(time.monotonic() - started, 1)

    def probe(self, out_dir: Path, *, url: str | None = None,
              follow_conversation: bool = True) -> Path:
        """Look at the live page and write down what is there. Never sends anything.

        It also records what the page complained about while loading -- console errors,
        requests that failed, HTTP errors. An interface that spins forever usually says
        why in one of those three places, and guessing at the cause from the outside is
        how an afternoon disappears.
        """
        page = self.open()
        console: list[str] = []
        failed: list[dict] = []
        http_errors: list[dict] = []
        page.on("console", lambda message: console.append(
            f"{message.type}: {message.text[:300]}") if message.type in ("error", "warning")
            else None)
        page.on("requestfailed", lambda request: failed.append(
            {"url": request.url[:200], "reason": str(request.failure)[:200]}))
        page.on("response", lambda response: http_errors.append(
            {"url": response.url[:200], "status": response.status})
            if response.status >= 400 else None)

        try:
            if url:
                page.goto(url, wait_until="domcontentloaded")
            else:
                page.reload(wait_until="domcontentloaded")
        except Exception:  # noqa: BLE001 - a page that will not reload is itself a finding
            pass
        waited = self.settle(page)
        report = page.evaluate(_PROBE_JS)

        # The home page of a chat service has no messages, and the selector for one
        # message cannot be read from an empty list. Walk into a real conversation
        # instead. The first attempt followed the link to /chat/history, which is a page
        # of links and not a conversation: hence the filter on the last path segment, and
        # the second hop.
        followed = []
        for _ in range(2):
            if any(item["text"].strip() for item in report.get("message_candidates", [])):
                break
            href = page.evaluate(_CONVERSATION_LINK_JS)
            if not href or href in followed:
                break
            try:
                page.goto(href, wait_until="domcontentloaded")
                waited += self.settle(page)
                report = page.evaluate(_PROBE_JS)
                followed.append(href)
            except Exception:  # noqa: BLE001
                break
        report["followed_conversation"] = followed
        report.update({"service": self.service, "probed_utc": utc_now(),
                       "profile_verified": self.is_verified,
                       "user_data_dir": str(self.user_data_dir),
                       "settled_after_seconds": waited,
                       "body_chars": page.evaluate("() => document.body.innerText.length"),
                       "console_problems": console[:40],
                       "failed_requests": failed[:40],
                       "http_errors": http_errors[:40],
                       "language": page.evaluate("() => document.documentElement.lang || ''")})
        stamp = utc_now().replace(":", "").replace("-", "")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{self.service}-{stamp}.json"
        write_json_new(path, report)
        try:
            page.screenshot(path=str(out_dir / f"{self.service}-{stamp}.png"))
        except Exception:  # noqa: BLE001
            pass
        return path
