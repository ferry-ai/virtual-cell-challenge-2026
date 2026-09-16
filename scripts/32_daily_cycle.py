"""Run the chain of cycles -- plan, review, implementation, control -- as often as asked.

A *cycle* moves through four stages, and each stage leaves a signal in
``reports/ciclo_giornaliero/<giornata>/ciclo-NN/``. A stage runs only when the
previous signal exists and its own does not, so nothing is ever done twice. The
contract, in Italian, is ``docs/CICLO_GIORNALIERO.md``.

1. **Plan** -- only cycle 01. Claude, morning routine of the Claude app (skill
   ``piano-mattutino``), ends with ``seal``, which writes ``01_piano.json``.
2. **Review** -- Codex. In cycle 01, ``codex exec`` reviews the sealed plan and
   writes the sheet for Claude plus the acceptance tests (``collaudo/``). In every
   later cycle the same files come out of a conversation between the owner and
   Codex in the desktop app, and Codex itself starts the cycle with ``avvia``.
   Either way this script checks them and writes ``02_codex.json``.
3. **Implementation** -- Claude (``claude -p``) in a git worktree, on a branch
   that continues from the previous cycle. This script runs the acceptance tests
   before and after, the checks, commits locally and writes ``03_claude.json``.
4. **Control** -- Grok (``grok -p``, read-only). It writes its own analysis,
   then may ask for up to ``max_campagne`` orchestrator campaigns (DeepSeek and
   Kimi), which this script validates and starts, waking Grok after each one. The
   script writes the report ``05_resoconto.md`` and ``04_grok.json``: the cycle
   is closed and everyone sleeps until the next signal.

The *guardiano* is one long-running process that polls the signals and moves the
oldest open cycle by one stage at a time. There is no automatic end of day: a
day ("giornata") only names folders, from ``day_start`` to ``day_start``.

Why signals and not a file watcher: a watcher fires on a half-written file and
can fire twice. A signal is written once, after the stage has finished, and it
carries the sha256 of what the next stage is allowed to read.

    python scripts/32_daily_cycle.py seal --plan docs/PIANO_IMPLEMENTATIVO_2026-09-17.md \
        --plan docs/PIANO_COMPRENSIONE_2026-09-17.md --checker ok --tests ok
    python scripts/32_daily_cycle.py guardiano            # poll forever
    python scripts/32_daily_cycle.py guardiano --una-volta
    python scripts/32_daily_cycle.py bozza                # a draft folder for Codex
    python scripts/32_daily_cycle.py avvia --bozza <cartella>
    python scripts/32_daily_cycle.py run                  # wait for the plan, then drain
    python scripts/32_daily_cycle.py status

Standard library only, like the other process scripts (30, 31).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CYCLE_ROOT = Path("reports") / "ciclo_giornaliero"
CONFIG_DIR = Path("configs") / "ciclo_giornaliero"

CYCLE_DIR = re.compile(r"^ciclo-(\d{2,})$")
DAY_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DRAFT_PREFIX = "bozza-"

SEAL = "01_piano.json"
REVIEW = "02_revisione.md"
DIALOGUE = "02_dialogo.md"
STEP_FILE = "passo.json"
SHEET = "03_prompt_claude.md"
TESTS = "collaudo"
CODEX_REPLY = "02_codex.risposta.json"
CODEX_MARKER = "02_codex.json"
CLAUDE_MARKER = "03_claude.json"
OUTCOME = "04_esito_claude.md"
GROK_MARKER = "04_grok.json"
GROK_DIR = "grok"
ORCH_DIR = "orch"
ANALYSIS = "05_analisi_grok.md"
SYNTHESIS = "05_sintesi_grok.md"
REPORT = "05_resoconto.md"
INPUTS = ".ciclo"
PREVIOUS_REPORT = "resoconto_precedente.md"
LOCK_NAME = "guardiano.lock"

CHECK_STATES = ("ok", "fallito", "non_eseguito")
CODEX_OUTCOMES = ("prompt_pronto", "nessun_passo", "saltato")
CLAUDE_OUTCOMES = ("completato", "parziale", "bloccato")
GROK_OUTCOMES = ("ok", "problemi", "bloccante")
DRAFT_FILES = {SHEET, DIALOGUE, STEP_FILE, REVIEW, TESTS}
TEST_SUFFIXES = (".py", ".json", ".txt", ".csv", ".md")

# The sheet is the only free text that reaches an agent with write access, and the
# acceptance tests are code this script runs. Neither may even *mention* these
# commands: the prohibitions are added by the fixed preamble, never by an agent.
SHEET_SECTIONS = ("## Obiettivo", "## Contesto", "## Passi",
                  "## Regola di accettazione", "## Vincoli", "## Consegna")
FORBIDDEN = (
    re.compile(r"\bvcc(?:\.cmd)?\s+submit\b", re.IGNORECASE),
    re.compile(r"\bgit\s+push\b", re.IGNORECASE),
    re.compile(r"dangerously", re.IGNORECASE),
    re.compile(r"bypassPermissions", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\bRemove-Item\b[^\n]*-Recurse", re.IGNORECASE),
)
MAX_SHEET_BYTES = 15_000
MAX_MATERIAL_BYTES = 150_000  # the orchestrator refuses a material over 200 KB

# Exit codes of `run`, by the outcome of the day's first cycle.
EXIT_CODES = {
    "completato": 0, "parziale": 0, "gia_fatto": 0,
    "saltato": 2, "nessun_passo": 2, "non_avviato": 2, "foglio_non_valido": 2,
    "bloccato": 3,
    "errore": 1,
}

DEFAULTS: dict = {
    "day_start": "08:00",
    "seal_deadline": "12:00",
    "poll_minutes": 10,
    "poll_seconds": 60,
    "worktree_root": None,
    "log_root": None,
    "codex": {
        "exe": None,
        "args": ["-s", "workspace-write"],
        "extra_args": [],
        "timeout_minutes": 45,
    },
    "claude": {
        "exe": None,
        "permission_mode": "acceptEdits",
        "allowed_tools": ["Read", "Edit", "Write", "Glob", "Grep"],
        "disallowed_tools": ["WebFetch", "WebSearch"],
        "extra_args": [],
        "timeout_minutes": 90,
    },
    "verify": [
        {"name": "checker", "argv": ["{python}", "scripts/31_check_docs.py"],
         "timeout_minutes": 5},
    ],
    "collaudo": {
        "obbligatorio": True,
        "argv": ["{python}", "-m", "unittest", "discover", "-s", "{dir}", "-t", "{dir}"],
        "timeout_minutes": 20,
        "max_bytes": 200_000,
    },
    "grok": {
        "exe": None,
        "args": ["--permission-mode", "plan", "--disable-web-search"],
        "extra_args": [],
        "max_turns": 60,
        "timeout_minutes": 30,
    },
    "orchestratore": {
        "abilitato": True,
        "max_campagne": 3,
        "exe": None,
        "route": "deep_kimi",
        "max_rounds": 2,
        "max_wall_clock_minutes": 30,
        "timeout_minutes": 45,
    },
}


class CycleError(RuntimeError):
    """A precondition of the chain is not met; the message says which."""


class LockBusy(CycleError):
    """Another process is already moving the chain."""


# --------------------------------------------------------------------------- basics

def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict | None:
    """The parsed object, or None when the file is missing or not a JSON object.

    A signal being written is not valid JSON yet, so a poller reads it as absent.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_new_json(path: Path, payload: dict) -> None:
    """Write a signal or a record. It is never overwritten: mode 'x' fails if it exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_new_text(path: Path, text: str) -> bool:
    """Write a text once. False when the file already exists (a resumed stage)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(text)
    except FileExistsError:
        return False
    return True


def merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if key.startswith("_"):
            continue  # comment keys in the JSON settings
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = value
    return out


def load_settings(root: Path) -> dict:
    path = root / CONFIG_DIR / "ciclo.json"
    override = read_json(path) if path.exists() else {}
    if override is None:
        raise CycleError(f"{path} is not a JSON object")
    return merge(DEFAULTS, override)


def resolve_data_root(root: Path) -> Path:
    env = os.environ.get("VCC2026_DATA_ROOT")
    if env:
        return Path(env)
    config = root / "configs" / "config.yaml"
    if config.exists():
        match = re.search(r"""^data_root:\s*["']?([^"'\n#]+?)["']?\s*(?:#.*)?$""",
                          config.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            return Path(match.group(1).strip())
    raise CycleError("data_root not found: set VCC2026_DATA_ROOT or configs/config.yaml")


def render(template: str, values: dict) -> str:
    """Fill ``{{name}}`` placeholders. An unknown placeholder is an error, not a blank."""
    def fill(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            raise CycleError(f"unknown placeholder {{{{{key}}}}} in template")
        return str(values[key])
    return re.sub(r"\{\{([a-z_]+)\}\}", fill, template)


def relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def parse_hhmm(text: str) -> dt.time:
    hours, minutes = (int(part) for part in text.split(":"))
    return dt.time(hours, minutes)


def giornata_for(moment: dt.datetime, day_start: str) -> dt.date:
    """The working day a moment belongs to: a cycle started at 03:00 is yesterday's."""
    if moment.time() >= parse_hhmm(day_start):
        return moment.date()
    return moment.date() - dt.timedelta(days=1)


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit].rstrip() + " […]"


def _is_str_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


# --------------------------------------------------------------------------- model

@dataclass
class Chain:
    """The repository-wide view: settings, paths and every cycle on disk."""
    root: Path
    settings: dict
    data_root: Path

    @property
    def base_dir(self) -> Path:
        return self.root / CYCLE_ROOT

    @property
    def log_root(self) -> Path:
        return Path(self.settings.get("log_root") or (self.data_root / "ciclo"))

    @property
    def worktree_root(self) -> Path:
        return Path(self.settings.get("worktree_root") or (self.data_root / "worktrees"))

    def day_dir(self, day: dt.date) -> Path:
        return self.base_dir / day.isoformat()

    def cycle(self, day: dt.date, number: int) -> "Cycle":
        return Cycle(self, day, number)

    def cycles(self) -> list["Cycle"]:
        """Every ``ciclo-NN`` folder, oldest day first. Flat legacy days are ignored."""
        found = []
        if not self.base_dir.is_dir():
            return found
        for day_dir in sorted(self.base_dir.iterdir()):
            if not (day_dir.is_dir() and DAY_DIR.match(day_dir.name)):
                continue
            day = dt.date.fromisoformat(day_dir.name)
            for child in day_dir.iterdir():
                match = CYCLE_DIR.match(child.name)
                if match and child.is_dir():
                    found.append(Cycle(self, day, int(match.group(1))))
        return sorted(found, key=lambda c: (c.day, c.number))

    def template(self, name: str) -> str:
        return (self.root / CONFIG_DIR / name).read_text(encoding="utf-8")

    def schema(self, name: str) -> str:
        """A JSON schema, compacted to one line for a command-line argument."""
        return json.dumps(json.loads(self.template(name)), separators=(",", ":"))

    def head(self) -> str:
        return git(["rev-parse", "HEAD"], self.root)

    def today(self, clock=dt.datetime.now) -> dt.date:
        return giornata_for(clock(), self.settings["day_start"])


@dataclass
class Cycle:
    chain: Chain
    day: dt.date
    number: int

    @property
    def name(self) -> str:
        return f"{self.day.isoformat()}-{self.number:02d}"

    @property
    def dir(self) -> Path:
        return self.chain.day_dir(self.day) / f"ciclo-{self.number:02d}"

    def path(self, name: str) -> Path:
        return self.dir / name

    def marker(self, name: str) -> dict | None:
        return read_json(self.path(name))

    @property
    def root(self) -> Path:
        return self.chain.root

    @property
    def settings(self) -> dict:
        return self.chain.settings

    @property
    def branch(self) -> str:
        return f"ciclo/{self.name}"

    @property
    def worktree(self) -> Path:
        return self.chain.worktree_root / f"ciclo-{self.name}"

    @property
    def log_dir(self) -> Path:
        return self.chain.log_root / self.day.isoformat() / f"ciclo-{self.number:02d}"

    @property
    def origin(self) -> str | None:
        """'piano' for the morning cycle, 'dialogo' for a cycle Codex started."""
        if self.path(SEAL).exists():
            return "piano"
        codex = self.marker(CODEX_MARKER)
        if codex and codex.get("origine") == "dialogo":
            return "dialogo"
        return None

    @property
    def queued_utc(self) -> str | None:
        """When the cycle entered the queue: the plan seal or the dialogue's start signal."""
        seal = self.marker(SEAL)
        if seal is not None:
            return seal.get("sealed_utc")
        codex = self.marker(CODEX_MARKER)
        if codex and codex.get("origine") == "dialogo":
            return codex.get("ended_utc")
        return None

    @property
    def closed(self) -> bool:
        return self.path(GROK_MARKER).exists()

    def next_stage(self) -> str | None:
        if self.closed or self.queued_utc is None:
            return None
        if not self.path(CODEX_MARKER).exists():
            return "revisione"
        if not self.path(CLAUDE_MARKER).exists():
            return "implementazione"
        return "controllo"


def open_queue(chain: Chain) -> list[Cycle]:
    """Open cycles in the order they were started. Only the first one may move."""
    ready = [c for c in chain.cycles() if c.queued_utc and not c.closed]
    return sorted(ready, key=lambda c: (c.queued_utc, c.day, c.number))


def implemented_before(chain: Chain, cycle: Cycle) -> list[Cycle]:
    """Cycles whose implementation stage has finished, most recent first."""
    done = []
    for other in chain.cycles():
        if (other.day, other.number) == (cycle.day, cycle.number):
            continue
        marker = other.marker(CLAUDE_MARKER)
        if marker and marker.get("ended_utc"):
            done.append((marker["ended_utc"], other))
    done.sort(key=lambda pair: pair[0], reverse=True)
    return [other for _, other in done]


def is_ancestor(commit: str, head: str, cwd: Path) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", commit, head], cwd=cwd,
                          capture_output=True).returncode == 0


def base_for(cycle: Cycle) -> tuple[str, str]:
    """(commit, reason). Continue from the last cycle's work unless it is integrated."""
    head = cycle.chain.head()
    for previous in implemented_before(cycle.chain, cycle):
        marker = previous.marker(CLAUDE_MARKER) or {}
        tip = marker.get("commit") or marker.get("base")
        if not tip:
            continue
        if is_ancestor(tip, head, cycle.root):
            return head, f"HEAD: il lavoro di {previous.name} è già integrato"
        return tip, f"continua da {previous.name}"
    return head, "HEAD: nessun ciclo precedente"


def last_report(cycle: Cycle) -> Path | None:
    for previous in implemented_before(cycle.chain, cycle):
        report = previous.path(REPORT)
        if report.is_file():
            return report
    return None


# ------------------------------------------------------------------ processes

def run_process(argv: list[str], *, cwd: Path, stdin_text: str | None, timeout_s: float,
                log_path: Path, env: dict | None = None
                ) -> tuple[int | None, str, str, float]:
    """Run one command with a hard timeout and keep its full output in a log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        proc = subprocess.run(argv, cwd=cwd, input=stdin_text, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=timeout_s,
                              env=None if env is None else {**os.environ, **env})
        code, out, err = proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        def text(value) -> str:
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value or ""
        code, out = None, text(exc.stdout)
        err = text(exc.stderr) + f"\n[timeout after {timeout_s:.0f} s]"
    except OSError as exc:
        code, out, err = None, "", f"[cannot start: {exc}]"
    seconds = time.monotonic() - started
    shown = " ".join(a if len(a) < 200 else a[:80] + "…" for a in argv)
    log_path.write_text(
        f"$ {shown}\n[cwd] {cwd}\n[exit] {code}\n[seconds] {seconds:.1f}\n\n"
        f"--- stdout ---\n{out}\n--- stderr ---\n{err}\n", encoding="utf-8")
    return code, out, err, seconds


def git(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise CycleError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def tool_version(argv: list[str]) -> str | None:
    try:
        proc = subprocess.run([*argv, "--version"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (proc.stdout or proc.stderr).strip() or None


def as_argv(value) -> list[str]:
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def resolve_codex(settings: dict) -> list[str]:
    """Codex CLI: env override, settings, the path the desktop app records, newest bundle."""
    env = os.environ.get("VCC2026_CODEX_EXE")
    if env:
        return [env]
    if settings["codex"].get("exe"):
        return as_argv(settings["codex"]["exe"])
    config = Path.home() / ".codex" / "config.toml"
    if config.exists():
        match = re.search(r"""CODEX_CLI_PATH\s*=\s*['"]([^'"]+)['"]""",
                          config.read_text(encoding="utf-8", errors="replace"))
        if match and Path(match.group(1)).is_file():
            return [match.group(1)]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        found = sorted(Path(local, "OpenAI", "Codex", "bin").glob("*/codex.exe"),
                       key=lambda p: p.stat().st_mtime)
        if found:
            return [str(found[-1])]
    which = shutil.which("codex")
    if which:
        return [which]
    raise CycleError("Codex CLI not found: set VCC2026_CODEX_EXE")


def _version_key(path: Path) -> tuple:
    return tuple(int(part) if part.isdigit() else 0 for part in path.parent.name.split("."))


def resolve_claude(settings: dict) -> list[str]:
    """Claude Code CLI: env override, settings, newest desktop bundle, PATH."""
    env = os.environ.get("VCC2026_CLAUDE_EXE")
    if env:
        return [env]
    if settings["claude"].get("exe"):
        return as_argv(settings["claude"]["exe"])
    roaming = os.environ.get("APPDATA")
    if roaming:
        found = sorted(Path(roaming, "Claude", "claude-code").glob("*/claude.exe"),
                       key=_version_key)
        if found:
            return [str(found[-1])]
    which = shutil.which("claude")
    if which:
        return [which]
    raise CycleError("Claude Code CLI not found: set VCC2026_CLAUDE_EXE")


def resolve_grok(settings: dict) -> list[str]:
    """Grok Build CLI: env override, settings, the installer's folder, PATH."""
    env = os.environ.get("VCC2026_GROK_EXE")
    if env:
        return [env]
    if settings["grok"].get("exe"):
        return as_argv(settings["grok"]["exe"])
    home = Path.home() / ".grok" / "bin" / ("grok.exe" if os.name == "nt" else "grok")
    if home.is_file():
        return [str(home)]
    which = shutil.which("grok")
    if which:
        return [which]
    raise CycleError("Grok CLI not found: set VCC2026_GROK_EXE")


def resolve_orchestrator(chain: Chain) -> tuple[list[str], dict]:
    """The orchestrator console, called on its own Python so a timeout kills it for real.

    Going through ``orch.cmd`` would leave the Python child alive when the wrapper is
    killed, still driving the browser.
    """
    configured = chain.settings["orchestratore"].get("exe")
    env = {"PYTHONPATH": str(chain.root / "src"), "PYTHONIOENCODING": "utf-8"}
    if configured:
        return as_argv(configured), env
    override = os.environ.get("VCC2026_ORCH_PYTHON")
    scripts = "Scripts" if os.name == "nt" else "bin"
    exe = "python.exe" if os.name == "nt" else "python"
    candidates = [Path(override)] if override else []
    candidates += [chain.data_root / "orch-venv" / scripts / exe,
                   chain.data_root / ".venv" / scripts / exe]
    for python in candidates:
        if python.is_file():
            return [str(python), "-m", "orchestrator.cli"], env
    raise CycleError("orchestrator Python not found: set VCC2026_ORCH_PYTHON")


def claude_logged_in(exe: list[str]) -> tuple[bool, str]:
    """`claude auth status` is JSON; a headless run without a login would fail later."""
    try:
        proc = subprocess.run([*exe, "auth", "status"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"stato di autenticazione di Claude illeggibile: {exc}"
    try:
        status = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False, "lo stato di autenticazione di Claude non è JSON"
    if isinstance(status, dict) and status.get("loggedIn"):
        return True, str(status.get("authMethod"))
    return False, ("Claude CLI non autenticato: eseguire una volta "
                   "`claude auth login` in un terminale")


@contextmanager
def stay_awake():
    """Keep Windows from sleeping while an agent works; a no-op elsewhere."""
    kernel = None
    if os.name == "nt":
        import ctypes  # noqa: PLC0415 -- Windows only
        kernel = ctypes.windll.kernel32
        kernel.SetThreadExecutionState(0x80000000 | 0x00000001)  # CONTINUOUS | SYSTEM
    try:
        yield
    finally:
        if kernel is not None:
            kernel.SetThreadExecutionState(0x80000000)


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes  # noqa: PLC0415 -- Windows only
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class RunnerLock:
    """One process moves the chain at a time. A lock whose process is gone is stale."""

    def __init__(self, path: Path, *, command: str, alive=pid_alive) -> None:
        self.path = path
        self.command = command
        self.alive = alive
        self.broke_stale = False

    def _create(self) -> int:
        return os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

    def __enter__(self) -> "RunnerLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = self._create()
        except FileExistsError:
            holder = read_json(self.path) or {}
            pid = int(holder.get("pid") or 0)
            if self.alive(pid):
                raise LockBusy(f"{holder.get('command', '?')} già attivo (pid {pid}): "
                               f"{self.path}") from None
            self.path.unlink(missing_ok=True)
            self.broke_stale = True
            try:
                fd = self._create()
            except FileExistsError:
                raise LockBusy(f"{self.path} ripreso da un altro processo") from None
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"pid": os.getpid(), "command": self.command,
                                     "started_utc": now_utc()}))
        return self

    def __exit__(self, *exc) -> None:
        self.path.unlink(missing_ok=True)


# ------------------------------------------------------------------ checks

def forbidden_mentions(text: str) -> list[str]:
    return [p.pattern for p in FORBIDDEN if p.search(text)]


def validate_sheet(text: str) -> list[str]:
    problems = []
    if not text.strip():
        return ["foglio vuoto"]
    size = len(text.encode("utf-8"))
    if size > MAX_SHEET_BYTES:
        problems.append(f"foglio di {size} byte, oltre il limite di {MAX_SHEET_BYTES}")
    lines = {line.strip() for line in text.splitlines()}
    problems += [f"sezione mancante: {s}" for s in SHEET_SECTIONS if s not in lines]
    problems += [f"contiene un'espressione vietata: {p}" for p in forbidden_mentions(text)]
    return problems


def test_inventory(folder: Path, max_bytes: int) -> tuple[list[dict], list[str]]:
    """The acceptance tests in a folder: (files with sha256, problems)."""
    if not folder.is_dir():
        return [], ["cartella collaudo assente"]
    files = sorted(p for p in folder.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts)
    problems = []
    if not any(p.name.startswith("test") and p.suffix == ".py" for p in files):
        problems.append("nessun file test*.py nel collaudo")
    total = sum(p.stat().st_size for p in files)
    if total > max_bytes:
        problems.append(f"collaudo di {total} byte, oltre il limite di {max_bytes}")
    for path in files:
        name = path.relative_to(folder).as_posix()
        if path.suffix not in TEST_SUFFIXES:
            problems.append(f"file non ammesso nel collaudo: {name}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        problems += [f"{name} contiene un'espressione vietata: {p}"
                     for p in forbidden_mentions(text)]
    entries = [{"path": p.relative_to(folder).as_posix(), "sha256": sha256(p),
                "bytes": p.stat().st_size} for p in files]
    return entries, problems


def check_codex_reply(reply: dict | None) -> list[str]:
    if reply is None:
        return ["risposta finale di Codex assente o non in JSON"]
    problems = []
    for key, kind in (("data", str), ("esito", str), ("motivo", str),
                      ("piano_verificato", bool)):
        if not isinstance(reply.get(key), kind):
            problems.append(f"campo {key} assente o del tipo sbagliato")
    for key in ("critiche_bloccanti", "domande_per_il_lead"):
        if not _is_str_list(reply.get(key)):
            problems.append(f"campo {key} non è una lista di testi")
    if reply.get("esito") not in CODEX_OUTCOMES:
        problems.append(f"esito {reply.get('esito')!r} non ammesso")
    step = reply.get("passo")
    if reply.get("esito") == "prompt_pronto":
        if not isinstance(step, dict):
            problems.append("esito prompt_pronto senza passo")
        else:
            for key in ("id", "titolo", "perche"):
                if not isinstance(step.get(key), str) or not step.get(key):
                    problems.append(f"passo.{key} assente")
    elif step is not None and not isinstance(step, dict):
        problems.append("passo deve essere un oggetto o null")
    return problems


def check_step(step: dict | None) -> list[str]:
    """The step a dialogue cycle declares in passo.json."""
    if not isinstance(step, dict):
        return ["passo.json assente o non è un oggetto JSON"]
    problems = [f"passo.{key} assente" for key in ("id", "titolo", "perche")
                if not isinstance(step.get(key), str) or not step.get(key).strip()]
    if "metriche" in step and not _is_str_list(step["metriche"]):
        problems.append("passo.metriche non è una lista di testi")
    return problems


def check_claude_reply(reply: dict | None) -> list[str]:
    if reply is None:
        return ["risposta strutturata di Claude assente"]
    problems = []
    if reply.get("esito") not in CLAUDE_OUTCOMES:
        problems.append(f"esito {reply.get('esito')!r} non ammesso")
    for key in ("passo_id", "sintesi", "verifiche"):
        if not isinstance(reply.get(key), str):
            problems.append(f"campo {key} assente")
    for key in ("file_toccati", "blocchi"):
        if not _is_str_list(reply.get(key)):
            problems.append(f"campo {key} non è una lista di testi")
    return problems


def check_grok_reply(reply: dict | None, *, first: bool) -> list[str]:
    if reply is None:
        return ["risposta strutturata di Grok assente"]
    problems = []
    if reply.get("esito") not in GROK_OUTCOMES:
        problems.append(f"esito {reply.get('esito')!r} non ammesso")
    for key in ("analisi_md", "sintesi_md"):
        if not isinstance(reply.get(key), str):
            problems.append(f"campo {key} assente")
    if first and not str(reply.get("analisi_md") or "").strip():
        problems.append("analisi indipendente vuota")
    if not _is_str_list(reply.get("domande_per_l_utente")):
        problems.append("campo domande_per_l_utente non è una lista di testi")
    request = reply.get("richiesta")
    if request is None:
        return problems
    if not isinstance(request, dict):
        return problems + ["richiesta deve essere un oggetto o null"]
    for key in ("titolo", "domanda", "contesto", "risultato_atteso"):
        if not isinstance(request.get(key), str) or not request[key].strip():
            problems.append(f"richiesta.{key} assente")
    if not _is_str_list(request.get("criteri")) or not request.get("criteri"):
        problems.append("richiesta.criteri vuoto")
    if not _is_str_list(request.get("materiali")):
        problems.append("richiesta.materiali non è una lista di testi")
    return problems


def _json_objects(stdout: str):
    text = stdout.strip()
    try:
        yield json.loads(text)
        return
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _structured(result, keys: tuple[str, ...], text_key: str) -> dict | None:
    if not isinstance(result, dict):
        return None
    for key in keys:
        if isinstance(result.get(key), dict):
            return result[key]
    if isinstance(result.get(text_key), str):
        try:
            parsed = json.loads(result[text_key])
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def parse_claude_output(stdout: str) -> tuple[dict | None, dict | None]:
    """The `--output-format json` result object, and its structured part."""
    result = next((r for r in _json_objects(stdout) if isinstance(r, dict)), None)
    return result, _structured(result, ("structured_output",), "result")


def parse_grok_output(stdout: str) -> tuple[dict | None, dict | None]:
    """Grok's `--output-format json` object: `structuredOutput`, else `text` as JSON."""
    result = next((r for r in _json_objects(stdout) if isinstance(r, dict)), None)
    return result, _structured(result, ("structuredOutput", "structured_output"), "text")


def verify_seal(cycle: Cycle) -> tuple[bool, str, dict | None]:
    seal = cycle.marker(SEAL)
    if seal is None:
        return False, "segnale della fase 1 assente", None
    plans = seal.get("plans") or []
    if not plans:
        return False, "sigillo senza piani", seal
    for entry in plans:
        plan = cycle.root / entry["path"]
        if not plan.is_file():
            return False, f"piano sparito dopo il sigillo: {entry['path']}", seal
        if sha256(plan) != entry["sha256"]:
            return False, f"piano modificato dopo il sigillo: {entry['path']}", seal
    return True, "piano sigillato e integro", seal


def wait_for_seal(cycle: Cycle, *, sleep=time.sleep,
                  clock=dt.datetime.now) -> tuple[bool, str]:
    """Poll for the morning plan until the deadline. A broken seal is final."""
    deadline = dt.datetime.combine(cycle.day, parse_hhmm(cycle.settings["seal_deadline"]))
    poll_seconds = max(1.0, float(cycle.settings["poll_minutes"]) * 60)
    while True:
        ok, reason, seal = verify_seal(cycle)
        if ok or seal is not None:
            return ok, reason
        remaining = (deadline - clock()).total_seconds()
        if remaining <= 0:
            return False, f"{reason} alle {deadline:%H:%M}"
        sleep(min(poll_seconds, remaining))


# ------------------------------------------------------------ stages 1 and 2

def cmd_seal(chain: Chain, day: dt.date, *, plans: list[str], snapshot: str | None,
             checker: str, tests: str, page_url: str | None, by: str) -> dict:
    """Stage 1 of cycle 01: record the sha256 of the day's plans."""
    if not plans:
        raise CycleError("seal needs at least one --plan")
    cycle = chain.cycle(day, 1)
    entries = []
    for raw in plans:
        plan = Path(raw) if Path(raw).is_absolute() else chain.root / raw
        if not plan.is_file():
            raise CycleError(f"plan not found: {raw}")
        if day.isoformat() not in plan.name:
            raise CycleError(f"{plan.name} is not dated {day.isoformat()}")
        entries.append({"path": relative(chain.root, plan), "sha256": sha256(plan),
                        "bytes": plan.stat().st_size})
    if snapshot and not (chain.root / snapshot).exists():
        raise CycleError(f"snapshot not found: {snapshot}")
    payload = {
        "stage": 1, "esito": "sigillato", "giornata": day.isoformat(), "ciclo": 1,
        "sealed_utc": now_utc(), "by": by, "plans": entries, "snapshot": snapshot,
        "checks": {"checker": checker, "tests": tests}, "page_url": page_url,
    }
    write_new_json(cycle.path(SEAL), payload)
    return payload


def _file_entry(cycle: Cycle, name: str) -> dict | None:
    path = cycle.path(name)
    if not path.is_file():
        return None
    return {"path": relative(cycle.root, path), "sha256": sha256(path)}


def stage_review(cycle: Cycle, *, dry_run: bool = False, runner=run_process) -> dict:
    """Stage 2 of cycle 01: Codex reviews the sealed plan, writes the sheet and the tests."""
    done = cycle.marker(CODEX_MARKER)
    if done is not None:
        return {**done, "gia_fatto": True}
    started = now_utc()
    base = {"stage": 2, "origine": "piano", "giornata": cycle.day.isoformat(),
            "ciclo": cycle.number, "started_utc": started}
    ok, reason, seal = verify_seal(cycle)
    if not ok:
        payload = {**base, "esito": "saltato", "motivo": reason, "ended_utc": now_utc()}
        if not dry_run:
            write_new_json(cycle.path(CODEX_MARKER), payload)
        return payload

    settings = cycle.settings["codex"]
    exe = resolve_codex(cycle.settings)
    plans = [cycle.root / entry["path"] for entry in seal["plans"]]
    impl = next((p for p in plans if "IMPLEMENTATIVO" in p.name), plans[0])
    comp = next((p for p in plans if "COMPRENSIONE" in p.name), plans[-1])
    prompt = render(cycle.chain.template("prompt_codex.md"), {
        "date": cycle.day.isoformat(),
        "cycle_dir": cycle.dir,
        "tests_dir": cycle.path(TESTS),
        "repo_root": cycle.root,
        "plan_impl": impl,
        "plan_comp": comp,
        "seal": cycle.path(SEAL),
        "skill": cycle.root / ".agents" / "skills" / "revisione-piano" / "SKILL.md",
    })
    schema = cycle.root / CONFIG_DIR / "codex_output.schema.json"
    argv = [*exe, "exec", "-C", str(cycle.dir), *settings["args"],
            "--output-schema", str(schema), "-o", str(cycle.path(CODEX_REPLY)),
            "--json", *settings["extra_args"], "-"]
    if dry_run:
        return {"stage": 2, "esito": "dry_run", "argv": argv, "prompt": prompt}

    code, _, _, seconds = runner(argv, cwd=cycle.dir, stdin_text=prompt,
                                 timeout_s=float(settings["timeout_minutes"]) * 60,
                                 log_path=cycle.log_dir / "fase2_codex.log")
    problems = []
    stray = cycle.path(CODEX_MARKER)
    if stray.exists():  # the agent wrote the script's signal: set it aside, keep it
        stray.rename(cycle.path("02_codex.agente.json"))
        problems.append("Codex ha scritto 02_codex.json, che spetta allo script")
    reply = read_json(cycle.path(CODEX_REPLY))
    problems += check_codex_reply(reply)
    review = cycle.path(REVIEW)
    if not review.is_file() or not review.read_text(encoding="utf-8").strip():
        problems.append("02_revisione.md assente o vuoto")

    sheet_problems: list[str] = []
    tests, test_problems = test_inventory(cycle.path(TESTS),
                                          int(cycle.settings["collaudo"]["max_bytes"]))
    if reply and reply.get("esito") == "prompt_pronto":
        sheet = cycle.path(SHEET)
        if sheet.is_file():
            sheet_problems = validate_sheet(sheet.read_text(encoding="utf-8"))
        else:
            sheet_problems = ["esito prompt_pronto ma 03_prompt_claude.md assente"]
        if cycle.settings["collaudo"]["obbligatorio"] or tests:
            sheet_problems += test_problems

    if code != 0:
        outcome, why = "errore", f"codex exec è uscito con {code}"
    elif problems:
        outcome, why = "errore", "; ".join(problems)
    elif sheet_problems:
        outcome, why = "foglio_non_valido", "; ".join(sheet_problems)
    else:
        outcome, why = reply["esito"], reply["motivo"]

    payload = {
        **base, "esito": outcome, "motivo": why, "ended_utc": now_utc(),
        "seconds": round(seconds, 1), "exit_code": code, "codex": exe,
        "codex_version": tool_version(exe), "avviato_da": "codex exec",
        "seal_sha256": sha256(cycle.path(SEAL)),
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "risposta": reply,
        "revisione": _file_entry(cycle, REVIEW),
        "foglio": _file_entry(cycle, SHEET) if outcome == "prompt_pronto" else None,
        "collaudo": {"file": tests},
        "problemi": problems + sheet_problems,
        "log": str(cycle.log_dir / "fase2_codex.log"),
    }
    write_new_json(cycle.path(CODEX_MARKER), payload)
    return payload


def cmd_bozza(chain: Chain, *, clock=dt.datetime.now) -> Path:
    """An empty draft folder for Codex, inside the current day's folder."""
    day = chain.today(clock)
    stamp = clock().strftime("%H%M%S")
    for attempt in range(50):
        suffix = "" if attempt == 0 else f"-{attempt}"
        draft = chain.day_dir(day) / f"{DRAFT_PREFIX}{stamp}{suffix}"
        try:
            draft.mkdir(parents=True)
        except FileExistsError:
            continue
        (draft / TESTS).mkdir()
        return draft
    raise CycleError("no free draft folder name")


def check_draft(chain: Chain, draft: Path) -> tuple[dict | None, list[str]]:
    problems = []
    unexpected = sorted(p.name for p in draft.iterdir() if p.name not in DRAFT_FILES)
    if unexpected:
        problems.append(f"file non previsti nella bozza: {', '.join(unexpected)}")
    step = read_json(draft / STEP_FILE)
    problems += check_step(step)
    sheet = draft / SHEET
    if sheet.is_file():
        problems += validate_sheet(sheet.read_text(encoding="utf-8"))
    else:
        problems.append(f"{SHEET} assente")
    dialogue = draft / DIALOGUE
    text = dialogue.read_text(encoding="utf-8") if dialogue.is_file() else ""
    if not text.strip():
        problems.append(f"{DIALOGUE} assente o vuoto")
    elif len(text.encode("utf-8")) > MAX_SHEET_BYTES:
        problems.append(f"{DIALOGUE} oltre {MAX_SHEET_BYTES} byte")
    else:
        problems += [f"{DIALOGUE} contiene un'espressione vietata: {p}"
                     for p in forbidden_mentions(text)]
    _, test_problems = test_inventory(draft / TESTS,
                                      int(chain.settings["collaudo"]["max_bytes"]))
    if chain.settings["collaudo"]["obbligatorio"] or (draft / TESTS).is_dir():
        problems += test_problems
    return step, problems


def cmd_avvia(chain: Chain, *, draft: Path, by: str = "codex",
              clock=dt.datetime.now) -> tuple[Cycle, dict]:
    """Start a cycle from a conversation: the draft becomes ``ciclo-NN`` and is queued."""
    draft = draft if draft.is_absolute() else chain.root / draft
    if not draft.is_dir():
        raise CycleError(f"bozza non trovata: {draft}")
    if not draft.resolve().is_relative_to(chain.base_dir.resolve()):
        raise CycleError(f"la bozza deve stare sotto {chain.base_dir}")
    step, problems = check_draft(chain, draft)
    if problems:
        raise CycleError("bozza non valida: " + "; ".join(problems))

    day = chain.today(clock)
    day_dir = chain.day_dir(day)
    day_dir.mkdir(parents=True, exist_ok=True)
    taken = [int(m.group(1)) for p in day_dir.iterdir() if (m := CYCLE_DIR.match(p.name))]
    number = max([1, *taken]) + 1  # 01 belongs to the morning plan
    for _ in range(50):
        target = day_dir / f"ciclo-{number:02d}"
        if not target.exists():
            try:
                draft.rename(target)
                break
            except OSError:
                if not target.exists():
                    raise
        number += 1
    else:
        raise CycleError("nessun numero di ciclo libero")

    cycle = chain.cycle(day, number)
    tests, _ = test_inventory(cycle.path(TESTS), int(chain.settings["collaudo"]["max_bytes"]))
    stamp = now_utc()
    payload = {
        "stage": 2, "origine": "dialogo", "esito": "prompt_pronto",
        "motivo": step["perche"], "giornata": day.isoformat(), "ciclo": number,
        "avviato_da": by, "started_utc": stamp, "ended_utc": stamp,
        "risposta": {"passo": {"id": step["id"], "titolo": step["titolo"],
                               "perche": step["perche"],
                               "metriche": step.get("metriche", [])}},
        "foglio": _file_entry(cycle, SHEET),
        "dialogo": _file_entry(cycle, DIALOGUE),
        "revisione": _file_entry(cycle, REVIEW),
        "collaudo": {"file": tests},
        "problemi": [],
    }
    write_new_json(cycle.path(CODEX_MARKER), payload)
    return cycle, payload


# ------------------------------------------------------------------ stage 3

def _copy_inputs(cycle: Cycle, worktree: Path) -> None:
    """The read-only materials Claude gets in ``.ciclo/``. Never committed."""
    target = worktree / INPUTS
    target.mkdir(parents=True, exist_ok=True)
    for name in (SEAL, REVIEW, DIALOGUE, SHEET):
        if cycle.path(name).is_file():
            shutil.copy2(cycle.path(name), target / name)
    seal = cycle.marker(SEAL)
    for entry in (seal or {}).get("plans", []):
        source = cycle.root / entry["path"]
        shutil.copy2(source, target / source.name)
    if cycle.path(TESTS).is_dir():
        shutil.copytree(cycle.path(TESTS), target / TESTS, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__"))
    previous = last_report(cycle)
    if previous is not None:
        shutil.copy2(previous, target / PREVIOUS_REPORT)


def prepare_worktree(cycle: Cycle, base: str) -> tuple[Path, bool]:
    """(worktree, reused). A worktree left by a stopped run is reused, never recreated."""
    worktree = cycle.worktree
    if worktree.exists():
        current = git(["rev-parse", "--abbrev-ref", "HEAD"], worktree)
        if current != cycle.branch:
            raise CycleError(f"{worktree} exists but is on {current}, not {cycle.branch}")
        return worktree, True
    worktree.parent.mkdir(parents=True, exist_ok=True)
    known = subprocess.run(["git", "rev-parse", "--verify", "--quiet",
                            f"refs/heads/{cycle.branch}"], cwd=cycle.root,
                           capture_output=True).returncode == 0
    if known:
        git(["worktree", "add", str(worktree), cycle.branch], cycle.root)
    else:
        git(["worktree", "add", "-b", cycle.branch, str(worktree), base], cycle.root)
    return worktree, False


def _fill_argv(argv: list[str], values: dict) -> list[str]:
    out = []
    for arg in argv:
        for key, value in values.items():
            arg = arg.replace("{" + key + "}", str(value))
        out.append(arg)
    return out


def run_collaudo(cycle: Cycle, worktree: Path, label: str, *, runner=run_process) -> dict:
    """Run a fresh copy of the tests Codex wrote, taken from the cycle folder.

    The copy Claude can see in ``.ciclo/collaudo`` is never the one that runs, so
    editing it changes nothing.
    """
    run_dir = worktree / INPUTS / f"collaudo_{label}"
    if run_dir.exists():
        shutil.rmtree(run_dir)  # the script's own scratch copy from a stopped run
    shutil.copytree(cycle.path(TESTS), run_dir, ignore=shutil.ignore_patterns("__pycache__"))
    settings = cycle.settings["collaudo"]
    scripts = "Scripts" if os.name == "nt" else "bin"
    venv_python = cycle.chain.data_root / ".venv" / scripts / (
        "python.exe" if os.name == "nt" else "python")
    argv = _fill_argv(settings["argv"], {"python": sys.executable, "dir": run_dir,
                                         "venv_python": venv_python})
    code, out, err, seconds = runner(
        argv, cwd=worktree, stdin_text=None,
        timeout_s=float(settings["timeout_minutes"]) * 60,
        log_path=cycle.log_dir / f"collaudo_{label}.log",
        env={"PYTHONPATH": str(worktree / "src"), "PYTHONIOENCODING": "utf-8",
             "PYTHONDONTWRITEBYTECODE": "1"})  # no __pycache__ in the commit
    text = f"{out}\n{err}"
    ran = re.search(r"Ran (\d+) tests?", text)
    failed = re.search(r"FAILED \(([^)]*)\)", text)
    return {"esito": "ok" if code == 0 else "fallito", "exit_code": code,
            "test": int(ran.group(1)) if ran else None,
            "dettaglio": failed.group(1) if failed else None,
            "seconds": round(seconds, 1)}


def _finish_implementation(cycle: Cycle, payload: dict, dry_run: bool) -> dict:
    if not dry_run:
        write_new_json(cycle.path(CLAUDE_MARKER), payload)
    return payload


def _origin_text(cycle: Cycle) -> str:
    if cycle.origin == "piano":
        return ("dal piano del mattino: il lead scientist lo ha scritto, Codex lo ha "
                "rivisto e ha scelto il passo")
    return ("da un dialogo fra il proprietario del progetto e Codex, che ne ha scritto "
            "il riassunto in `02_dialogo.md`")


def stage_implement(cycle: Cycle, *, dry_run: bool = False, runner=run_process,
                    login_check=claude_logged_in) -> dict:
    """Stage 3: Claude implements the sheet; the script tests, checks and commits."""
    done = cycle.marker(CLAUDE_MARKER)
    if done is not None:
        return {**done, "gia_fatto": True}
    started = now_utc()
    base_payload = {"stage": 3, "giornata": cycle.day.isoformat(), "ciclo": cycle.number,
                    "started_utc": started}

    def stop(outcome: str, why: str, **extra) -> dict:
        return _finish_implementation(cycle, {**base_payload, "esito": outcome,
                                              "motivo": why, **extra,
                                              "ended_utc": now_utc()}, dry_run)

    review = cycle.marker(CODEX_MARKER)
    if review is None or review.get("esito") != "prompt_pronto":
        stage2 = "assente" if review is None else review.get("esito")
        return stop("non_avviato", f"fase 2: {stage2}")
    sheet = cycle.path(SHEET)
    if not sheet.is_file() or sha256(sheet) != (review.get("foglio") or {}).get("sha256"):
        return stop("non_avviato", "foglio assente o modificato dopo la validazione")
    sheet_text = sheet.read_text(encoding="utf-8")
    problems = validate_sheet(sheet_text)
    recorded_tests = (review.get("collaudo") or {}).get("file") or []
    tests, test_problems = test_inventory(cycle.path(TESTS),
                                          int(cycle.settings["collaudo"]["max_bytes"]))
    if recorded_tests or cycle.settings["collaudo"]["obbligatorio"]:
        if tests != recorded_tests:
            problems.append("collaudo assente o modificato dopo la validazione")
        problems += test_problems
    if cycle.origin == "piano":
        ok, reason, _ = verify_seal(cycle)
        if not ok:
            problems.append(reason)
    if problems:
        return stop("non_avviato", "; ".join(problems))

    settings = cycle.settings["claude"]
    exe = resolve_claude(cycle.settings)
    logged, auth = login_check(exe)
    if not logged:
        return stop("bloccato", auth, claude=exe)

    step = (review.get("risposta") or {}).get("passo") or {}
    preamble = render(cycle.chain.template("preambolo_claude.md"), {
        "date": cycle.day.isoformat(),
        "cycle": f"{cycle.number:02d}",
        "origin": _origin_text(cycle),
        "worktree": cycle.worktree,
        "branch": cycle.branch,
        "inputs": INPUTS,
        "tests": f"{INPUTS}/{TESTS}",
        "outcome": f"{INPUTS}/{OUTCOME}",
        "step_id": step.get("id", "?"),
    })
    prompt = f"{preamble}\n\n---\n\n{sheet_text}"
    schema = cycle.chain.schema("claude_output.schema.json")
    argv = [*exe, "-p", "--output-format", "json", "--json-schema", schema,
            "--permission-mode", settings["permission_mode"],
            "--permission-prompts", "none",
            "-n", f"ciclo {cycle.name}",
            *settings["extra_args"],
            "--allowedTools", *settings["allowed_tools"],
            "--disallowedTools", *settings["disallowed_tools"]]
    base, base_why = base_for(cycle)
    if dry_run:
        return {"stage": 3, "esito": "dry_run", "argv": argv, "prompt": prompt,
                "worktree": str(cycle.worktree), "branch": cycle.branch, "base": base}

    worktree, reused = prepare_worktree(cycle, base)
    _copy_inputs(cycle, worktree)
    before = run_collaudo(cycle, worktree, "prima", runner=runner) if tests else None
    code, out, _, seconds = runner(argv, cwd=worktree, stdin_text=prompt,
                                   timeout_s=float(settings["timeout_minutes"]) * 60,
                                   log_path=cycle.log_dir / "fase3_claude.log")
    result, reply = parse_claude_output(out)
    reply_problems = check_claude_reply(reply)

    outcome_copy = None
    outcome_file = worktree / INPUTS / OUTCOME
    if outcome_file.is_file():
        write_new_text(cycle.path(OUTCOME), outcome_file.read_text(encoding="utf-8"))
        outcome_copy = relative(cycle.root, cycle.path(OUTCOME))

    after = run_collaudo(cycle, worktree, "dopo", runner=runner) if tests else None
    checks = {}
    for check in cycle.settings["verify"]:
        check_argv = _fill_argv(check["argv"], {"python": sys.executable})
        check_code, _, _, _ = runner(
            check_argv, cwd=worktree, stdin_text=None,
            timeout_s=float(check.get("timeout_minutes", 10)) * 60,
            log_path=cycle.log_dir / f"verifica_{check['name']}.log")
        checks[check["name"]] = "ok" if check_code == 0 else "fallito"

    commit = None
    files: list[str] = []
    git(["add", "-A", "--", ".", f":(exclude){INPUTS}"], worktree)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=worktree).returncode
    if staged != 0:
        summary = ", ".join(f"{k}={v}" for k, v in checks.items()) or "nessuna"
        collaudo = "assente" if after is None else after["esito"]
        message = (f"ciclo {cycle.name}: {step.get('id', '?')} {step.get('titolo', '')}".strip()
                   + f"\n\nesito dell'agente: {(reply or {}).get('esito', 'sconosciuto')}; "
                   + f"collaudo: {collaudo}; verifiche: {summary}"
                   + f"\nfoglio sha256: {review['foglio']['sha256']}"
                   + "\n\nCo-Authored-By: Claude Code <noreply@anthropic.com>")
        git(["commit", "-m", message], worktree)
        commit = git(["rev-parse", "HEAD"], worktree)
        files = git(["diff", "--name-only", base, commit], worktree).splitlines()

    if code != 0:
        outcome, why = "errore", f"claude -p è uscito con {code}"
    elif reply_problems:
        outcome, why = "errore", "; ".join(reply_problems)
    else:
        outcome, why = reply["esito"], reply["sintesi"]
    if outcome == "completato":
        if any(v != "ok" for v in checks.values()):
            outcome, why = "parziale", f"{why} — verifiche: {checks}"
        elif after is not None and after["esito"] != "ok":
            outcome, why = "parziale", f"{why} — collaudo fallito dopo il lavoro"
        elif before is not None and before["esito"] == "ok" and not reused:
            outcome, why = "parziale", f"{why} — collaudo non informativo: passava già prima"

    payload = {
        **base_payload, "esito": outcome, "motivo": why, "ended_utc": now_utc(),
        "seconds": round(seconds, 1), "exit_code": code, "claude": exe,
        "claude_version": tool_version(exe), "auth": auth,
        "session_id": (result or {}).get("session_id"),
        "costo_nominale_usd": (result or {}).get("total_cost_usd"),
        "risposta": reply, "problemi": reply_problems,
        "worktree": str(worktree), "worktree_riusato": reused,
        "branch": cycle.branch, "base": base, "base_motivo": base_why,
        "commit": commit, "file_modificati": files, "verifiche": checks,
        "collaudo": {"prima": before, "dopo": after, "file": recorded_tests},
        "esito_claude": outcome_copy,
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "log": str(cycle.log_dir / "fase3_claude.log"),
    }
    return _finish_implementation(cycle, payload, dry_run)


# ------------------------------------------------------------------ stage 4

MATERIALS = ("esito_claude.md", "foglio.md", "diff.patch", "collaudo.md", "analisi_grok.md")


def _collaudo_text(implement: dict) -> str:
    collaudo = implement.get("collaudo") or {}
    lines = ["# Collaudo del ciclo", ""]
    for label in ("prima", "dopo"):
        result = collaudo.get(label)
        if result is None:
            lines.append(f"- {label}: non eseguito")
        else:
            lines.append(f"- {label}: {result['esito']}, test {result.get('test')}, "
                         f"dettaglio {result.get('dettaglio')}")
    lines.append(f"- verifiche: {implement.get('verifiche')}")
    return "\n".join(lines) + "\n"


def prepare_materials(cycle: Cycle, implement: dict) -> Path:
    """Plain-text extracts Grok reads and a campaign may attach. Written once."""
    folder = cycle.path(GROK_DIR) / "materiali"
    folder.mkdir(parents=True, exist_ok=True)
    if cycle.path(OUTCOME).is_file():
        write_new_text(folder / "esito_claude.md", cycle.path(OUTCOME).read_text(encoding="utf-8"))
    write_new_text(folder / "foglio.md", cycle.path(SHEET).read_text(encoding="utf-8"))
    write_new_text(folder / "collaudo.md", _collaudo_text(implement))
    commit, base = implement.get("commit"), implement.get("base")
    if commit and base and not (folder / "diff.patch").exists():
        diff = git(["diff", "--stat", "--patch", base, commit], Path(implement["worktree"]))
        data = diff.encode("utf-8")
        if len(data) > MAX_MATERIAL_BYTES:
            diff = (data[:MAX_MATERIAL_BYTES].decode("utf-8", errors="ignore")
                    + "\n\n[diff troncato: completo nel branch del ciclo]\n")
        write_new_text(folder / "diff.patch", diff)
    return folder


def grok_prompt(cycle: Cycle, implement: dict, materials: Path, budget: int) -> str:
    return render(cycle.chain.template("prompt_grok.md"), {
        "date": cycle.day.isoformat(),
        "cycle": f"{cycle.number:02d}",
        "cycle_dir": cycle.dir,
        "worktree": implement.get("worktree") or cycle.root,
        "branch": implement.get("branch") or "-",
        "commit": implement.get("commit") or "nessun commit",
        "outcome": f"{implement.get('esito')} — {implement.get('motivo')}",
        "materials": materials,
        "budget": budget,
    })


def grok_followup_prompt(cycle: Cycle, campaign: dict, remaining: int) -> str:
    report = campaign.get("rapporto")
    return render(cycle.chain.template("prompt_grok_seguito.md"), {
        "date": cycle.day.isoformat(),
        "cycle": f"{cycle.number:02d}",
        "index": campaign["indice"],
        "status": campaign.get("esito"),
        "report": cycle.root / report if report else "nessun rapporto",
        "analysis": cycle.path(ANALYSIS),
        "remaining": remaining,
    })


def grok_call(cycle: Cycle, index: int, prompt: str, cwd: Path, *,
              runner=run_process) -> tuple[dict | None, dict]:
    """One headless Grok turn. Its record is written once, so a resumed stage reuses it."""
    folder = cycle.path(GROK_DIR)
    record_path = folder / f"chiamata-{index:02d}.json"
    existing = read_json(record_path)
    if existing is not None:
        return (existing["risposta"] if existing.get("valida") else None), existing
    prompt_path = folder / f"prompt-{index:02d}.md"
    folder.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    settings = cycle.settings["grok"]
    exe = resolve_grok(cycle.settings)
    argv = [*exe, "--prompt-file", str(prompt_path), "--output-format", "json",
            "--json-schema", cycle.chain.schema("grok_output.schema.json"),
            "--cwd", str(cwd), "--max-turns", str(settings["max_turns"]),
            *settings["args"], *settings["extra_args"]]
    code, out, _, seconds = runner(argv, cwd=cwd, stdin_text=None,
                                   timeout_s=float(settings["timeout_minutes"]) * 60,
                                   log_path=cycle.log_dir / f"fase4_grok_{index:02d}.log")
    result, reply = parse_grok_output(out)
    problems = check_grok_reply(reply, first=index == 1)
    if code != 0:
        problems.insert(0, f"grok è uscito con {code}")
    record = {
        "indice": index, "valida": not problems, "problemi": problems,
        "exit_code": code, "seconds": round(seconds, 1), "grok": exe,
        "session_id": (result or {}).get("sessionId"),
        "modelli": sorted(((result or {}).get("modelUsage") or {}).keys()),
        "costo_nominale_usd": (result or {}).get("total_cost_usd"),
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "risposta": reply,
    }
    write_new_json(record_path, record)
    return (reply if not problems else None), record


def build_brief(cycle: Cycle, index: int, request: dict, materials: Path) -> tuple[Path, list[str]]:
    """A campaign brief from the fixed template: Grok fills the text, never the rules."""
    orch = cycle.settings["orchestratore"]
    folder = cycle.path(ORCH_DIR) / f"campagna-{index}"
    folder.mkdir(parents=True, exist_ok=True)
    attached, dropped = [], []
    for name in request.get("materiali", []):
        source = materials / name
        if name in MATERIALS and source.is_file():
            if not (folder / name).exists():
                shutil.copy2(source, folder / name)
            attached.append(name)
        else:
            dropped.append(name)
    context = (clip(request["contesto"], 4000)
               + "\n\nRegole fisse: proponi e critica, non eseguire codice; distingui "
                 "misure, interpretazioni e ipotesi; un accordo fra modelli non è una "
                 "verifica; niente risultati inventati.")
    document = {
        "id": f"ciclo-{cycle.name}-{index}",
        "version": 1,
        "route": orch["route"],
        "title": clip(request["titolo"], 120),
        "question": clip(request["domanda"], 4000),
        "context": context,
        "expected_result": clip(request["risultato_atteso"], 1000),
        "acceptance_criteria": [
            {"id": f"C{n}", "text": clip(text, 300), "check": {"kind": "human"}}
            for n, text in enumerate(request["criteri"][:6], start=1)],
        "materials": [{"id": f"M{n}", "path": name}
                      for n, name in enumerate(attached, start=1)],
        "limits": {"max_rounds": int(orch["max_rounds"]),
                   "max_wall_clock_minutes": int(orch["max_wall_clock_minutes"])},
    }
    brief = folder / "brief.json"
    if not brief.exists():
        write_new_json(brief, document)
    return brief, dropped


def run_campaign(cycle: Cycle, index: int, request: dict, materials: Path, *,
                 runner=run_process) -> dict:
    """Validate and start one orchestrator campaign. Recorded once, never repeated."""
    record_path = cycle.path(ORCH_DIR) / f"campagna-{index}.json"
    existing = read_json(record_path)
    if existing is not None:
        return existing
    brief, dropped = build_brief(cycle, index, request, materials)
    record = {"indice": index, "titolo": request["titolo"],
              "brief": relative(cycle.root, brief), "materiali_scartati": dropped,
              "started_utc": now_utc()}
    orch, env = resolve_orchestrator(cycle.chain)
    code, out, _, _ = runner([*orch, "brief", str(brief)], cwd=cycle.root, stdin_text=None,
                             timeout_s=300, env=env,
                             log_path=cycle.log_dir / f"orch_{index}_brief.log")
    if code != 0:
        record.update(esito="incarico_non_valido", exit_code=code,
                      dettaglio=clip(out.strip(), 1000))
    else:
        timeout = float(cycle.settings["orchestratore"]["timeout_minutes"]) * 60
        code, out, _, seconds = runner(
            [*orch, "start", "--brief", str(brief), "--label", f"ciclo-{cycle.name}-{index}"],
            cwd=cycle.root, stdin_text=None, timeout_s=timeout, env=env,
            log_path=cycle.log_dir / f"orch_{index}_start.log")
        run_id = re.search(r"run creato: (\S+)", out)
        status = re.search(r"\[stato finale\] (\S+)", out)
        report = re.search(r"\[rapporto\] (.+)", out)
        copy = None
        if report and Path(report.group(1).strip()).is_file():
            copy = cycle.path(ORCH_DIR) / f"campagna-{index}-rapporto.md"
            write_new_text(copy, Path(report.group(1).strip()).read_text(encoding="utf-8"))
        esito = status.group(1) if status else ("timeout" if code is None else "errore")
        record.update(esito=esito, exit_code=code, seconds=round(seconds, 1),
                      run_id=run_id.group(1) if run_id else None,
                      rapporto=relative(cycle.root, copy) if copy else None)
    record["ended_utc"] = now_utc()
    write_new_json(record_path, record)
    return record


def _collaudo_line(implement: dict, label: str) -> str:
    result = (implement.get("collaudo") or {}).get(label)
    return "non eseguito" if result is None else f"{result['esito']} ({result.get('test')} test)"


def write_report(cycle: Cycle, control: dict) -> Path:
    """``05_resoconto.md``: what the owner reads when the cycle closes."""
    review = cycle.marker(CODEX_MARKER) or {}
    implement = cycle.marker(CLAUDE_MARKER) or {}
    step = (review.get("risposta") or {}).get("passo") or {}
    origin = {"piano": "piano del mattino, rivisto da Codex",
              "dialogo": f"dialogo con ChatGPT, avviato da {review.get('avviato_da')}"}
    lines = [
        f"# Resoconto del ciclo {cycle.number:02d} — giornata {cycle.day.isoformat()}",
        "",
        f"- **Origine:** {origin.get(cycle.origin, 'sconosciuta')}",
        f"- **Passo:** {step.get('id', '-')} — {step.get('titolo', '-')}",
        f"- **Revisione:** {review.get('esito', '-')} — {review.get('motivo', '-')}",
        f"- **Implementazione:** {implement.get('esito', '-')} — {implement.get('motivo', '-')}",
    ]
    if implement.get("branch"):
        lines.append(f"- **Branch:** {implement['branch']}, commit "
                     f"{(implement.get('commit') or 'nessuno')[:10]}, partito da "
                     f"{str(implement.get('base'))[:10]} ({implement.get('base_motivo')})")
        lines.append(f"- **Collaudo:** prima {_collaudo_line(implement, 'prima')}, "
                     f"dopo {_collaudo_line(implement, 'dopo')}")
        lines.append(f"- **Verifiche:** {implement.get('verifiche')}")
    lines.append(f"- **Controllo di Grok:** {control.get('esito')} — {control.get('motivo')}")
    for name, label in ((ANALYSIS, "analisi indipendente"), (SYNTHESIS, "sintesi")):
        if cycle.path(name).is_file():
            lines.append(f"- **Grok, {label}:** {relative(cycle.root, cycle.path(name))}")
    for campaign in control.get("campagne") or []:
        lines.append(f"- **Campagna {campaign['indice']}:** {campaign['titolo']} — "
                     f"{campaign.get('esito')}, run {campaign.get('run_id') or '-'}, "
                     f"rapporto {campaign.get('rapporto') or '-'}")
    questions = control.get("domande") or []
    if questions:
        lines += ["", "## Domande per te", ""] + [f"- {q}" for q in questions]
    lines += ["", "## Integrazione", "",
              "Il branch del ciclo non è unito a niente. Il ciclo successivo parte da qui; "
              "unire i branch e aggiornare mappa e registro si fa a parte, su tua richiesta."]
    if cycle.path(SYNTHESIS).is_file():
        lines += ["", "## Sintesi di Grok", "",
                  cycle.path(SYNTHESIS).read_text(encoding="utf-8").strip()]
    path = cycle.path(REPORT)
    write_new_text(path, "\n".join(lines) + "\n")
    return path


def close_cycle(cycle: Cycle, payload: dict) -> dict:
    payload["resoconto"] = relative(cycle.root, cycle.path(REPORT))
    write_report(cycle, payload)
    write_new_json(cycle.path(GROK_MARKER), payload)
    return payload


def _call_summary(record: dict) -> dict:
    return {key: record.get(key) for key in ("indice", "valida", "problemi", "exit_code",
                                             "seconds", "session_id", "costo_nominale_usd")}


def stage_control(cycle: Cycle, *, runner=run_process) -> dict:
    """Stage 4: Grok's own analysis, the campaigns it asks for, the report."""
    done = cycle.marker(GROK_MARKER)
    if done is not None:
        return {**done, "gia_fatto": True}
    implement = cycle.marker(CLAUDE_MARKER)
    if implement is None:
        raise CycleError(f"ciclo {cycle.name}: manca la fase 3")
    base = {"stage": 4, "giornata": cycle.day.isoformat(), "ciclo": cycle.number,
            "started_utc": now_utc(), "campagne": [], "domande": [], "chiamate": []}
    if implement.get("esito") in ("non_avviato", "bloccato"):
        return close_cycle(cycle, {**base, "esito": "non_eseguito",
                                   "motivo": f"fase 3 {implement.get('esito')}: "
                                             f"{implement.get('motivo')}",
                                   "ended_utc": now_utc()})

    materials = prepare_materials(cycle, implement)
    orch = cycle.settings["orchestratore"]
    budget = int(orch["max_campagne"]) if orch["abilitato"] else 0
    worktree = Path(implement.get("worktree") or cycle.root)
    cwd = worktree if worktree.is_dir() else cycle.root
    first, record = grok_call(cycle, 1, grok_prompt(cycle, implement, materials, budget),
                              cwd, runner=runner)
    calls = [_call_summary(record)]
    if first is None:
        return close_cycle(cycle, {**base, "esito": "errore", "chiamate": calls,
                                   "motivo": "; ".join(record["problemi"]),
                                   "ended_utc": now_utc()})
    write_new_text(cycle.path(ANALYSIS), first["analisi_md"])
    write_new_text(materials / "analisi_grok.md", first["analisi_md"])

    latest, campaigns = first, []
    request = first.get("richiesta")
    while request is not None and len(campaigns) < budget:
        campaign = run_campaign(cycle, len(campaigns) + 1, request, materials, runner=runner)
        campaigns.append(campaign)
        remaining = budget - len(campaigns)
        reply, record = grok_call(cycle, len(campaigns) + 1,
                                  grok_followup_prompt(cycle, campaign, remaining),
                                  cwd, runner=runner)
        calls.append(_call_summary(record))
        if reply is None:
            break
        latest = reply
        request = reply.get("richiesta")
    write_new_text(cycle.path(SYNTHESIS), latest["sintesi_md"])
    beyond = request is not None and len(campaigns) >= budget
    payload = {
        **base, "esito": latest["esito"], "esito_iniziale": first["esito"],
        "motivo": f"Grok: {latest['esito']}; campagne {len(campaigns)} su {budget}"
                  + ("; richiesta oltre il tetto ignorata" if beyond else ""),
        "chiamate": calls, "campagne": campaigns,
        "domande": latest.get("domande_per_l_utente") or [],
        "analisi": relative(cycle.root, cycle.path(ANALYSIS)),
        "sintesi": relative(cycle.root, cycle.path(SYNTHESIS)),
        "ended_utc": now_utc(),
    }
    return close_cycle(cycle, payload)


# ------------------------------------------------------------------ commands

STAGES = {"revisione": stage_review, "implementazione": stage_implement,
          "controllo": stage_control}


def log(message: str) -> None:
    print(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {message}", flush=True)


def advance(chain: Chain, *, runner=run_process) -> tuple[Cycle, str, dict] | None:
    """Move the oldest open cycle by one stage. None when nothing is ready."""
    queue = open_queue(chain)
    if not queue:
        return None
    cycle = queue[0]
    stage = cycle.next_stage()
    with stay_awake():
        result = STAGES[stage](cycle, runner=runner)
    log(f"ciclo {cycle.name}, {stage}: {result.get('esito')} — "
        f"{clip(str(result.get('motivo')), 200)}")
    return cycle, stage, result


def cmd_guardiano(chain: Chain, *, once: bool = False, sleep=time.sleep,
                  runner=run_process, alive=pid_alive) -> int:
    """Poll the signals and move the chain. With `once`, stop when nothing is ready."""
    lock = RunnerLock(chain.log_root / LOCK_NAME, command="guardiano", alive=alive)
    with lock:
        if lock.broke_stale:
            log("rimosso il lucchetto di un guardiano non più attivo")
        log(f"guardiano attivo su {chain.base_dir}")
        while True:
            if advance(chain, runner=runner):
                continue
            if once:
                return 0
            sleep(float(chain.settings["poll_seconds"]))


def cmd_run(chain: Chain, day: dt.date, *, dry_run: bool, wait: bool, sleep=time.sleep,
            clock=dt.datetime.now, runner=run_process, alive=pid_alive) -> int:
    """The morning fallback: drain the queue until the day's first cycle is closed."""
    cycle = chain.cycle(day, 1)
    if dry_run:
        ok, reason, _ = verify_seal(cycle)
        print(f"fase 1: {reason}")
        for stage in (stage_review, stage_implement):
            result = stage(cycle, dry_run=True)
            if result.get("esito") != "dry_run":
                print(f"fase {result['stage']}: {result.get('esito')} — {result.get('motivo')}")
                break
            print(f"--- fase {result['stage']} (prova a secco) ---")
            print("comando:", " ".join(a if len(a) < 160 else a[:60] + "…"
                                       for a in result["argv"]))
            print(result["prompt"])
        return 0

    deadline = dt.datetime.combine(day, parse_hhmm(chain.settings["seal_deadline"]))
    poll = max(1.0, float(chain.settings["poll_minutes"]) * 60)
    try:
        with RunnerLock(chain.log_root / LOCK_NAME, command="run", alive=alive):
            while True:
                while advance(chain, runner=runner):
                    pass
                remaining = (deadline - clock()).total_seconds()
                if cycle.closed or not wait or (remaining <= 0 and not cycle.dir.exists()):
                    break
                sleep(min(poll, remaining) if remaining > 0 else poll)
    except LockBusy as exc:
        log(f"niente da fare: {exc}")
        return 0
    implement = cycle.marker(CLAUDE_MARKER)
    if implement is None:
        log(f"ciclo {cycle.name}: nessun piano sigillato")
        return EXIT_CODES["saltato"]
    return EXIT_CODES.get(implement.get("esito"), 1)


def cmd_status(chain: Chain, day: dt.date) -> int:
    print(f"giornata {day.isoformat()} — {chain.day_dir(day)}")
    holder = read_json(chain.log_root / LOCK_NAME)
    if holder and pid_alive(int(holder.get("pid") or 0)):
        print(f"  {holder.get('command')} attivo, pid {holder.get('pid')}, "
              f"dal {holder.get('started_utc')}")
    else:
        print("  nessun guardiano attivo")
    queue = [(c.day, c.number) for c in open_queue(chain)]
    shown = [c for c in chain.cycles() if c.day == day or (c.day, c.number) in queue]
    labels = ((SEAL, "piano"), (CODEX_MARKER, "revisione"),
              (CLAUDE_MARKER, "implementazione"), (GROK_MARKER, "controllo"))
    for cycle in shown:
        if cycle.closed:
            state = "chiuso"
        elif queue and queue[0] == (cycle.day, cycle.number):
            state = "in corso"
        elif (cycle.day, cycle.number) in queue:
            state = "in coda"
        else:
            state = "in attesa del segnale"
        parts = [f"{label}: {marker.get('esito')}" for name, label in labels
                 if (marker := cycle.marker(name)) is not None]
        print(f"  ciclo {cycle.name} [{cycle.origin or '?'}] {state} — "
              + ("; ".join(parts) or "nessun segnale"))
        if cycle.path(REPORT).is_file():
            print(f"    resoconto: {relative(chain.root, cycle.path(REPORT))}")
    if chain.day_dir(day).is_dir():
        for draft in sorted(chain.day_dir(day).glob(f"{DRAFT_PREFIX}*")):
            print(f"  bozza non avviata: {relative(chain.root, draft)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", help="giornata, YYYY-MM-DD (default: quella in corso)")
    parser.add_argument("--root", default=str(REPO_ROOT), help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)

    seal = sub.add_parser("seal", help="stage 1 of cycle 01: record the plans' sha256")
    seal.add_argument("--plan", action="append", default=[], required=True)
    seal.add_argument("--snapshot")
    seal.add_argument("--checker", choices=CHECK_STATES, default="non_eseguito")
    seal.add_argument("--tests", choices=CHECK_STATES, default="non_eseguito")
    seal.add_argument("--page-url")
    seal.add_argument("--by", default="claude")

    run = sub.add_parser("run", help="wait for the morning plan, then drain the queue")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--no-wait", action="store_true",
                     help="do not wait for the plan: drain once and stop")

    guard = sub.add_parser("guardiano", help="poll the signals and move the chain")
    guard.add_argument("--una-volta", action="store_true",
                       help="stop as soon as nothing is ready")

    sub.add_parser("bozza", help="create an empty draft folder for a new cycle")
    start = sub.add_parser("avvia", help="turn a draft into the next cycle")
    start.add_argument("--bozza", required=True)
    start.add_argument("--da", default="codex", help="who starts the cycle")

    sub.add_parser("status", help="print the cycles of the day")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    try:
        chain = Chain(root=root, settings=load_settings(root),
                      data_root=resolve_data_root(root))
        if args.command == "seal":
            day = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
            payload = cmd_seal(chain, day, plans=args.plan, snapshot=args.snapshot,
                               checker=args.checker, tests=args.tests,
                               page_url=args.page_url, by=args.by)
            print(f"sigillato: {chain.cycle(day, 1).path(SEAL)} "
                  f"({len(payload['plans'])} piani)")
            return 0
        day = dt.date.fromisoformat(args.date) if args.date else chain.today()
        if args.command == "run":
            return cmd_run(chain, day, dry_run=args.dry_run, wait=not args.no_wait)
        if args.command == "guardiano":
            return cmd_guardiano(chain, once=args.una_volta)
        if args.command == "bozza":
            draft = cmd_bozza(chain)
            print(f"bozza: {draft}")
            print(f"scrivi: {SHEET}, {DIALOGUE}, {STEP_FILE}, {TESTS}/test_*.py "
                  f"(facoltativo {REVIEW}), poi: avvia --bozza \"{draft}\"")
            return 0
        if args.command == "avvia":
            cycle, _ = cmd_avvia(chain, draft=Path(args.bozza), by=args.da)
            waiting = [c.name for c in open_queue(chain)
                       if (c.day, c.number) != (cycle.day, cycle.number)]
            print(f"ciclo {cycle.name} avviato: {cycle.dir}")
            print("davanti in coda: " + (", ".join(waiting) if waiting else "nessuno"))
            return 0
        return cmd_status(chain, day)
    except FileExistsError as exc:
        print(f"segnale già presente, niente da fare: {exc.filename}", file=sys.stderr)
        return 2
    except LockBusy as exc:
        print(f"niente da fare: {exc}", file=sys.stderr)
        return 0
    except CycleError as exc:
        print(f"errore: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("fermato a mano", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
