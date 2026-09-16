"""Run the daily chain -- plan, review, implementation -- once per day.

The chain has three stages. Each one leaves a marker in
``reports/ciclo_giornaliero/<date>/``, and a stage runs only when the previous
marker exists and its own does not, so running this script twice on the same day
never repeats work. The contract, in Italian, is ``docs/CICLO_GIORNALIERO.md``.

1. **Plan** -- Claude, morning routine of the Claude app (skill
   ``piano-mattutino``). It writes the two daily plans and ends with ``seal``,
   which records their sha256 in ``01_piano.json``.
2. **Review** -- Codex (``codex exec``, skill ``$revisione-piano``). It reads the
   sealed plan, criticises it, picks the step that matters most and writes
   ``02_revisione.md`` plus the prompt sheet ``03_prompt_claude.md``. This script
   checks the reply and the sheet, then writes ``02_codex.json``.
3. **Implementation** -- Claude (``claude -p``), started by this script as soon
   as a valid sheet exists. It works in a git worktree on branch
   ``ciclo/<date>``; this script runs the checks, commits locally and writes
   ``03_claude.json``. Nothing is pushed and nothing is submitted.

Why markers and not a file watcher: a watcher fires on a half-written file and
can fire twice. A marker is written once, after the stage has finished, and it
carries the sha256 of what the next stage is allowed to read.

    python scripts/32_daily_cycle.py seal --plan docs/PIANO_IMPLEMENTATIVO_2026-09-17.md \
        --plan docs/PIANO_COMPRENSIONE_2026-09-17.md \
        --snapshot reports/leaderboard_2026-09-17/ --checker ok --tests ok
    python scripts/32_daily_cycle.py run              # stages 2 and 3, waiting for stage 1
    python scripts/32_daily_cycle.py run --dry-run    # print what would run, change nothing
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
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CYCLE_ROOT = Path("reports") / "ciclo_giornaliero"
CONFIG_DIR = Path("configs") / "ciclo_giornaliero"

SEAL = "01_piano.json"
REVIEW = "02_revisione.md"
SHEET = "03_prompt_claude.md"
CODEX_REPLY = "02_codex.risposta.json"
CODEX_MARKER = "02_codex.json"
CLAUDE_MARKER = "03_claude.json"
OUTCOME = "04_esito_claude.md"
LOCK = ".lock"
INPUTS = ".ciclo"

CHECK_STATES = ("ok", "fallito", "non_eseguito")
CODEX_OUTCOMES = ("prompt_pronto", "nessun_passo", "saltato")
CLAUDE_OUTCOMES = ("completato", "parziale", "bloccato")

# The sheet Codex writes is the only free text that reaches an agent with write
# access. Its shape is fixed, and it may not even *mention* these commands: the
# prohibitions are added by the fixed preamble, never by the sheet.
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

# Exit codes of `run`, by outcome. 2 is a legitimate "nothing to do today".
EXIT_CODES = {
    "completato": 0, "parziale": 0, "gia_fatto": 0,
    "saltato": 2, "nessun_passo": 2, "non_avviato": 2,
    "bloccato": 3,
    "errore": 1, "foglio_non_valido": 1,
}

DEFAULTS: dict = {
    "seal_deadline": "12:00",
    "poll_minutes": 10,
    "lock_stale_hours": 8,
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
}


class CycleError(RuntimeError):
    """A precondition of the chain is not met; the message says which."""


class LockBusy(CycleError):
    """Another run of the chain holds the lock for this day."""


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
    """The parsed object, or None when the file is missing or not a JSON object."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_new_json(path: Path, payload: dict) -> None:
    """Write a marker. A marker is never overwritten: mode 'x' fails if it exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


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


@dataclass
class Cycle:
    root: Path
    date: dt.date
    settings: dict
    data_root: Path

    @property
    def dir(self) -> Path:
        return self.root / CYCLE_ROOT / self.date.isoformat()

    def path(self, name: str) -> Path:
        return self.dir / name

    @property
    def branch(self) -> str:
        return f"ciclo/{self.date.isoformat()}"

    @property
    def worktree(self) -> Path:
        base = self.settings.get("worktree_root") or (self.data_root / "worktrees")
        return Path(base) / f"ciclo-{self.date.isoformat()}"

    @property
    def log_dir(self) -> Path:
        base = self.settings.get("log_root") or (self.data_root / "ciclo")
        return Path(base) / self.date.isoformat()

    def template(self, name: str) -> str:
        return (self.root / CONFIG_DIR / name).read_text(encoding="utf-8")

    def deadline(self) -> dt.datetime:
        hours, minutes = (int(x) for x in self.settings["seal_deadline"].split(":"))
        return dt.datetime.combine(self.date, dt.time(hours, minutes))


class Lock:
    """One run per day at a time. A lock older than `stale_hours` is a crashed run."""

    def __init__(self, path: Path, stale_hours: float) -> None:
        self.path = path
        self.stale_hours = stale_hours
        self.broke_stale = False

    def __enter__(self) -> "Lock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            age_hours = (time.time() - self.path.stat().st_mtime) / 3600
            if age_hours < self.stale_hours:
                raise LockBusy(f"another run holds {self.path} ({age_hours:.1f} h old)")
            self.path.unlink()
            self.broke_stale = True
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"pid": os.getpid(), "started_utc": now_utc()}))
        return self

    def __exit__(self, *exc) -> None:
        self.path.unlink(missing_ok=True)


# ------------------------------------------------------------------ processes

def run_process(argv: list[str], *, cwd: Path, stdin_text: str | None,
                timeout_s: float, log_path: Path) -> tuple[int | None, str, str, float]:
    """Run one command with a hard timeout and keep its full output in a log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        proc = subprocess.run(argv, cwd=cwd, input=stdin_text, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=timeout_s)
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


# ------------------------------------------------------------------ checks

def validate_sheet(text: str) -> list[str]:
    problems = []
    if not text.strip():
        return ["foglio vuoto"]
    size = len(text.encode("utf-8"))
    if size > MAX_SHEET_BYTES:
        problems.append(f"foglio di {size} byte, oltre il limite di {MAX_SHEET_BYTES}")
    lines = {line.strip() for line in text.splitlines()}
    problems += [f"sezione mancante: {s}" for s in SHEET_SECTIONS if s not in lines]
    problems += [f"contiene un'espressione vietata: {p.pattern}"
                 for p in FORBIDDEN if p.search(text)]
    return problems


def _is_str_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


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


def parse_claude_output(stdout: str) -> tuple[dict | None, dict | None]:
    """The `--output-format json` result object, and its structured part."""
    result = None
    text = stdout.strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        for line in reversed(text.splitlines()):
            try:
                result = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    if not isinstance(result, dict):
        return None, None
    structured = result.get("structured_output")
    if structured is None and isinstance(result.get("result"), str):
        try:
            structured = json.loads(result["result"])
        except json.JSONDecodeError:
            structured = None
    return result, structured if isinstance(structured, dict) else None


def verify_seal(cycle: Cycle) -> tuple[bool, str, dict | None]:
    seal = read_json(cycle.path(SEAL))
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
    """Poll for stage 1 until the deadline. A broken seal is final: waiting will not fix it."""
    deadline = cycle.deadline()
    poll_seconds = max(1.0, float(cycle.settings["poll_minutes"]) * 60)
    while True:
        ok, reason, seal = verify_seal(cycle)
        if ok or seal is not None:
            return ok, reason
        remaining = (deadline - clock()).total_seconds()
        if remaining <= 0:
            return False, f"{reason} alle {deadline:%H:%M}"
        sleep(min(poll_seconds, remaining))


# ------------------------------------------------------------------ stages

def cmd_seal(cycle: Cycle, *, plans: list[str], snapshot: str | None, checker: str,
             tests: str, page_url: str | None, by: str) -> dict:
    if not plans:
        raise CycleError("seal needs at least one --plan")
    entries = []
    for raw in plans:
        plan = Path(raw) if Path(raw).is_absolute() else cycle.root / raw
        if not plan.is_file():
            raise CycleError(f"plan not found: {raw}")
        if cycle.date.isoformat() not in plan.name:
            raise CycleError(f"{plan.name} is not dated {cycle.date.isoformat()}")
        entries.append({"path": relative(cycle.root, plan), "sha256": sha256(plan),
                        "bytes": plan.stat().st_size})
    if snapshot and not (cycle.root / snapshot).exists():
        raise CycleError(f"snapshot not found: {snapshot}")
    payload = {
        "stage": 1, "esito": "sigillato", "date": cycle.date.isoformat(),
        "sealed_utc": now_utc(), "by": by, "plans": entries, "snapshot": snapshot,
        "checks": {"checker": checker, "tests": tests}, "page_url": page_url,
    }
    write_new_json(cycle.path(SEAL), payload)
    return payload


def stage_review(cycle: Cycle, *, dry_run: bool = False, runner=run_process) -> dict:
    """Stage 2: Codex reads the sealed plan and writes the review and the sheet."""
    done = read_json(cycle.path(CODEX_MARKER))
    if done is not None:
        return {**done, "gia_fatto": True}
    started = now_utc()
    ok, reason, seal = verify_seal(cycle)
    if not ok:
        payload = {"stage": 2, "date": cycle.date.isoformat(), "esito": "saltato",
                   "motivo": reason, "started_utc": started, "ended_utc": now_utc()}
        if not dry_run:
            write_new_json(cycle.path(CODEX_MARKER), payload)
        return payload

    settings = cycle.settings["codex"]
    exe = resolve_codex(cycle.settings)
    plans = [cycle.root / entry["path"] for entry in seal["plans"]]
    impl = next((p for p in plans if "IMPLEMENTATIVO" in p.name), plans[0])
    comp = next((p for p in plans if "COMPRENSIONE" in p.name), plans[-1])
    prompt = render(cycle.template("prompt_codex.md"), {
        "date": cycle.date.isoformat(),
        "cycle_dir": cycle.dir,
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

    stray = cycle.path(CODEX_MARKER)
    code, _, _, seconds = runner(argv, cwd=cycle.dir, stdin_text=prompt,
                                 timeout_s=float(settings["timeout_minutes"]) * 60,
                                 log_path=cycle.log_dir / "fase2_codex.log")
    problems = []
    if stray.exists():  # the agent wrote the script's marker: set it aside, keep it
        stray.rename(cycle.path("02_codex.agente.json"))
        problems.append("Codex ha scritto 02_codex.json, che spetta allo script")
    reply = read_json(cycle.path(CODEX_REPLY))
    problems += check_codex_reply(reply)
    review = cycle.path(REVIEW)
    if not review.is_file() or not review.read_text(encoding="utf-8").strip():
        problems.append("02_revisione.md assente o vuoto")

    sheet_info = None
    sheet_problems: list[str] = []
    sheet = cycle.path(SHEET)
    if reply and reply.get("esito") == "prompt_pronto":
        if sheet.is_file():
            sheet_problems = validate_sheet(sheet.read_text(encoding="utf-8"))
            sheet_info = {"path": relative(cycle.root, sheet), "sha256": sha256(sheet)}
        else:
            sheet_problems = ["esito prompt_pronto ma 03_prompt_claude.md assente"]

    if code != 0:
        outcome, why = "errore", f"codex exec è uscito con {code}"
    elif problems:
        outcome, why = "errore", "; ".join(problems)
    elif sheet_problems:
        outcome, why = "foglio_non_valido", "; ".join(sheet_problems)
    else:
        outcome, why = reply["esito"], reply["motivo"]

    payload = {
        "stage": 2, "date": cycle.date.isoformat(), "esito": outcome, "motivo": why,
        "started_utc": started, "ended_utc": now_utc(), "seconds": round(seconds, 1),
        "exit_code": code, "codex": exe, "codex_version": tool_version(exe),
        "seal_sha256": sha256(cycle.path(SEAL)),
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "risposta": reply,
        "revisione": ({"path": relative(cycle.root, review), "sha256": sha256(review)}
                      if review.is_file() else None),
        "foglio": sheet_info,
        "problemi": problems + sheet_problems,
        "log": str(cycle.log_dir / "fase2_codex.log"),
    }
    write_new_json(cycle.path(CODEX_MARKER), payload)
    return payload


def _copy_inputs(cycle: Cycle, worktree: Path, seal: dict) -> None:
    target = worktree / INPUTS
    target.mkdir(parents=True, exist_ok=True)
    for name in (SEAL, REVIEW, SHEET):
        shutil.copy2(cycle.path(name), target / name)
    for entry in seal["plans"]:
        source = cycle.root / entry["path"]
        shutil.copy2(source, target / source.name)


def prepare_worktree(cycle: Cycle, base: str) -> Path:
    worktree = cycle.worktree
    if worktree.exists():
        current = git(["rev-parse", "--abbrev-ref", "HEAD"], worktree)
        if current != cycle.branch:
            raise CycleError(f"{worktree} exists but is on {current}, not {cycle.branch}")
        return worktree  # a run that stopped half-way: reuse, never recreate
    worktree.parent.mkdir(parents=True, exist_ok=True)
    known = subprocess.run(["git", "rev-parse", "--verify", "--quiet",
                            f"refs/heads/{cycle.branch}"], cwd=cycle.root,
                           capture_output=True).returncode == 0
    if known:
        git(["worktree", "add", str(worktree), cycle.branch], cycle.root)
    else:
        git(["worktree", "add", "-b", cycle.branch, str(worktree), base], cycle.root)
    return worktree


def _finish_implementation(cycle: Cycle, payload: dict, dry_run: bool) -> dict:
    if not dry_run:
        write_new_json(cycle.path(CLAUDE_MARKER), payload)
    return payload


def stage_implement(cycle: Cycle, *, dry_run: bool = False, runner=run_process,
                    login_check=claude_logged_in) -> dict:
    """Stage 3: Claude implements the sheet in the day's worktree; the script commits."""
    done = read_json(cycle.path(CLAUDE_MARKER))
    if done is not None:
        return {**done, "gia_fatto": True}
    started = now_utc()
    base_payload = {"stage": 3, "date": cycle.date.isoformat(), "started_utc": started}

    review = read_json(cycle.path(CODEX_MARKER))
    if review is None or review.get("esito") != "prompt_pronto":
        stage2 = "assente" if review is None else review.get("esito")
        return _finish_implementation(cycle, {**base_payload, "esito": "non_avviato",
                                              "motivo": f"fase 2: {stage2}",
                                              "ended_utc": now_utc()}, dry_run)
    sheet = cycle.path(SHEET)
    sheet_text = sheet.read_text(encoding="utf-8") if sheet.is_file() else ""
    if not sheet.is_file() or sha256(sheet) != (review.get("foglio") or {}).get("sha256"):
        return _finish_implementation(cycle, {**base_payload, "esito": "non_avviato",
                                              "motivo": "foglio assente o modificato dopo la validazione",
                                              "ended_utc": now_utc()}, dry_run)
    problems = validate_sheet(sheet_text)
    ok, reason, seal = verify_seal(cycle)
    if problems or not ok:
        why = "; ".join(problems) if problems else reason
        return _finish_implementation(cycle, {**base_payload, "esito": "non_avviato",
                                              "motivo": why, "ended_utc": now_utc()}, dry_run)

    settings = cycle.settings["claude"]
    exe = resolve_claude(cycle.settings)
    logged, auth = login_check(exe)
    if not logged:
        return _finish_implementation(cycle, {**base_payload, "esito": "bloccato",
                                              "motivo": auth, "claude": exe,
                                              "ended_utc": now_utc()}, dry_run)

    step = (review.get("risposta") or {}).get("passo") or {}
    preamble = render(cycle.template("preambolo_claude.md"), {
        "date": cycle.date.isoformat(),
        "worktree": cycle.worktree,
        "branch": cycle.branch,
        "inputs": INPUTS,
        "outcome": f"{INPUTS}/{OUTCOME}",
        "step_id": step.get("id", "?"),
    })
    prompt = f"{preamble}\n\n---\n\n{sheet_text}"
    schema = json.dumps(json.loads(
        (cycle.root / CONFIG_DIR / "claude_output.schema.json").read_text(encoding="utf-8")),
        separators=(",", ":"))
    argv = [*exe, "-p", "--output-format", "json", "--json-schema", schema,
            "--permission-mode", settings["permission_mode"],
            "--permission-prompts", "none",
            "-n", f"ciclo {cycle.date.isoformat()}",
            *settings["extra_args"],
            "--allowedTools", *settings["allowed_tools"],
            "--disallowedTools", *settings["disallowed_tools"]]
    base = git(["rev-parse", "HEAD"], cycle.root)
    if dry_run:
        return {"stage": 3, "esito": "dry_run", "argv": argv, "prompt": prompt,
                "worktree": str(cycle.worktree), "branch": cycle.branch, "base": base}

    worktree = prepare_worktree(cycle, base)
    _copy_inputs(cycle, worktree, seal)
    code, out, _, seconds = runner(argv, cwd=worktree, stdin_text=prompt,
                                   timeout_s=float(settings["timeout_minutes"]) * 60,
                                   log_path=cycle.log_dir / "fase3_claude.log")
    result, reply = parse_claude_output(out)
    reply_problems = check_claude_reply(reply)

    outcome_file = worktree / INPUTS / OUTCOME
    outcome_copy = None
    if outcome_file.is_file():
        target = cycle.path(OUTCOME)
        if not target.exists():
            shutil.copy2(outcome_file, target)
        outcome_copy = relative(cycle.root, target)

    checks = {}
    python = sys.executable
    for step_check in cycle.settings["verify"]:
        check_argv = [python if a == "{python}" else a for a in step_check["argv"]]
        check_code, _, _, _ = runner(
            check_argv, cwd=worktree, stdin_text=None,
            timeout_s=float(step_check.get("timeout_minutes", 10)) * 60,
            log_path=cycle.log_dir / f"verifica_{step_check['name']}.log")
        checks[step_check["name"]] = "ok" if check_code == 0 else "fallito"

    commit = None
    files: list[str] = []
    git(["add", "-A", "--", ".", f":(exclude){INPUTS}"], worktree)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=worktree).returncode
    if staged != 0:
        summary = ", ".join(f"{k}={v}" for k, v in checks.items()) or "nessuna"
        agent_outcome = (reply or {}).get("esito", "sconosciuto")
        message = (f"ciclo {cycle.date.isoformat()}: {step.get('id', '?')} "
                   f"{step.get('titolo', '')}".strip()
                   + f"\n\nesito dell'agente: {agent_outcome}; verifiche: {summary}"
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
    if outcome == "completato" and any(v != "ok" for v in checks.values()):
        outcome, why = "parziale", f"{why} — verifiche: {checks}"

    payload = {
        **base_payload, "esito": outcome, "motivo": why, "ended_utc": now_utc(),
        "seconds": round(seconds, 1), "exit_code": code, "claude": exe,
        "claude_version": tool_version(exe), "auth": auth,
        "session_id": (result or {}).get("session_id"),
        "cost_usd": (result or {}).get("total_cost_usd"),
        "risposta": reply, "problemi": reply_problems,
        "worktree": str(worktree), "branch": cycle.branch, "base": base,
        "commit": commit, "file_modificati": files, "verifiche": checks,
        "esito_claude": outcome_copy,
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "log": str(cycle.log_dir / "fase3_claude.log"),
    }
    return _finish_implementation(cycle, payload, dry_run)


# ------------------------------------------------------------------ commands

def _show_dry_run(stage: dict) -> None:
    print(f"--- fase {stage['stage']} (prova a secco) ---")
    for key in ("worktree", "branch", "base"):
        if key in stage:
            print(f"{key}: {stage[key]}")
    shown = [a if len(a) < 160 else a[:60] + "…" for a in stage["argv"]]
    print("comando:", " ".join(shown))
    print("prompt:")
    print(stage["prompt"])


def cmd_run(cycle: Cycle, *, dry_run: bool, wait: bool) -> int:
    finished = read_json(cycle.path(CLAUDE_MARKER))
    if finished is not None:
        print(f"ciclo {cycle.date}: già concluso ({finished.get('esito')})")
        return EXIT_CODES["gia_fatto"]
    if dry_run:
        ok, reason, _ = verify_seal(cycle)
        print(f"fase 1: {reason}")
        review = stage_review(cycle, dry_run=True)
        if review.get("esito") == "dry_run":
            _show_dry_run(review)
        else:
            print(f"fase 2: {review.get('esito')} — {review.get('motivo')}")
        if read_json(cycle.path(CODEX_MARKER)) is None:
            print("fase 3: dipende dalla fase 2, che in prova a secco non gira")
            return 0
        implement = stage_implement(cycle, dry_run=True)
        if implement.get("esito") == "dry_run":
            _show_dry_run(implement)
        else:
            print(f"fase 3: {implement.get('esito')} — {implement.get('motivo')}")
        return 0

    with Lock(cycle.path(LOCK), float(cycle.settings["lock_stale_hours"])):
        if wait:
            ok, reason = wait_for_seal(cycle)
            print(f"fase 1: {reason}", flush=True)
        review = stage_review(cycle)
        print(f"fase 2: {review.get('esito')} — {review.get('motivo')}", flush=True)
        implement = stage_implement(cycle)
        print(f"fase 3: {implement.get('esito')} — {implement.get('motivo')}", flush=True)
    return EXIT_CODES.get(implement.get("esito"), 1)


def cmd_status(cycle: Cycle) -> int:
    print(f"ciclo {cycle.date.isoformat()} — {cycle.dir}")
    for name, label in ((SEAL, "fase 1, piano"), (CODEX_MARKER, "fase 2, revisione"),
                        (CLAUDE_MARKER, "fase 3, implementazione")):
        data = read_json(cycle.path(name))
        if data is None:
            print(f"  {label}: assente")
            continue
        line = f"  {label}: {data.get('esito', '?')}"
        if data.get("motivo"):
            line += f" — {data['motivo']}"
        if data.get("commit"):
            line += f" — commit {data['commit'][:10]} su {data.get('branch')}"
        print(line)
    lock = cycle.path(LOCK)
    if lock.exists():
        print(f"  in corso: {lock.read_text(encoding='utf-8')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", help="day of the cycle, YYYY-MM-DD (default: today)")
    parser.add_argument("--root", default=str(REPO_ROOT), help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)

    seal = sub.add_parser("seal", help="stage 1: record the plans' sha256")
    seal.add_argument("--plan", action="append", default=[], required=True)
    seal.add_argument("--snapshot")
    seal.add_argument("--checker", choices=CHECK_STATES, default="non_eseguito")
    seal.add_argument("--tests", choices=CHECK_STATES, default="non_eseguito")
    seal.add_argument("--page-url")
    seal.add_argument("--by", default="claude")

    run = sub.add_parser("run", help="stages 2 and 3, waiting for stage 1")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--no-wait", action="store_true",
                     help="do not poll for stage 1: check once")

    sub.add_parser("fase2", help="stage 2 only")
    sub.add_parser("fase3", help="stage 3 only")
    sub.add_parser("status", help="print the day's markers")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    date = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    try:
        cycle = Cycle(root=root, date=date, settings=load_settings(root),
                      data_root=resolve_data_root(root))
        if args.command == "seal":
            payload = cmd_seal(cycle, plans=args.plan, snapshot=args.snapshot,
                               checker=args.checker, tests=args.tests,
                               page_url=args.page_url, by=args.by)
            print(f"sigillato: {cycle.path(SEAL)} ({len(payload['plans'])} piani)")
            return 0
        if args.command == "run":
            return cmd_run(cycle, dry_run=args.dry_run, wait=not args.no_wait)
        if args.command == "status":
            return cmd_status(cycle)
        with Lock(cycle.path(LOCK), float(cycle.settings["lock_stale_hours"])):
            stage = stage_review(cycle) if args.command == "fase2" else stage_implement(cycle)
        print(f"{args.command}: {stage.get('esito')} — {stage.get('motivo')}")
        return EXIT_CODES.get(stage.get("esito"), 1)
    except FileExistsError as exc:
        print(f"segnale già presente, niente da fare: {exc.filename}", file=sys.stderr)
        return 2
    except CycleError as exc:
        print(f"errore: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
