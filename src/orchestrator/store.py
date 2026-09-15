"""Persistent state: a SQLite index, an append-only event log, and files on disk.

The split is deliberate. SQLite holds what the engine needs to make decisions and to
resume -- run status, step status, findings, the operator's control commands. The files
hold the evidence: every prompt exactly as sent, every reply exactly as received,
written once and never rewritten. If the database were lost the transcripts would still
be readable; if the transcripts were lost the database would be worth little.

Crash behaviour is the reason a step's row is written *before* the request goes out. A
step found in state `dispatched` after a restart is one we cannot prove was delivered,
so it is never resent automatically: it is surfaced for reconciliation.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .util import append_jsonl, read_json, utc_now, write_json_new, write_new

SCHEMA_VERSION = 1

STEP_STATES = (
    "planned",          # decided by the engine, nothing sent
    "dispatched",       # request handed to an adapter; delivery unknown until settled
    "answered",         # a reply arrived and satisfied the contract
    "unparsed",         # a reply arrived and did not; the text is kept
    "transport_error",  # the channel failed: browser, CLI, timeout, expired session
    "abandoned",        # the operator or the engine gave up on this step
)

RUN_STATES = ("created", "running", "paused", "stopped", "finished", "failed",
              "awaiting_plan_approval", "needs_reconciliation")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS briefs (
    brief_id TEXT NOT NULL, version INTEGER NOT NULL, sha256 TEXT NOT NULL,
    title TEXT NOT NULL, source_path TEXT NOT NULL, registered_utc TEXT NOT NULL,
    PRIMARY KEY (brief_id, version));

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY, brief_id TEXT NOT NULL, brief_version INTEGER NOT NULL,
    brief_sha256 TEXT NOT NULL, label TEXT, route TEXT NOT NULL, status TEXT NOT NULL,
    stop_reason TEXT, stop_detail TEXT, created_utc TEXT NOT NULL,
    started_utc TEXT, ended_utc TEXT, deadline_utc TEXT);

CREATE TABLE IF NOT EXISTS subtasks (
    run_id TEXT NOT NULL, subtask_id TEXT NOT NULL, title TEXT NOT NULL,
    question TEXT NOT NULL, route TEXT NOT NULL, criteria TEXT NOT NULL,
    origin TEXT NOT NULL, status TEXT NOT NULL, stop_reason TEXT, stop_detail TEXT,
    rounds_done INTEGER NOT NULL DEFAULT 0, position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, subtask_id));

CREATE TABLE IF NOT EXISTS steps (
    step_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, subtask_id TEXT,
    stage TEXT NOT NULL, round INTEGER NOT NULL, role TEXT NOT NULL,
    service TEXT NOT NULL, attempt INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL,
    prompt_sha256 TEXT NOT NULL, directory TEXT NOT NULL,
    planned_utc TEXT NOT NULL, dispatched_utc TEXT, settled_utc TEXT,
    duration_ms INTEGER, error_kind TEXT, error_detail TEXT);

CREATE TABLE IF NOT EXISTS rounds (
    run_id TEXT NOT NULL, subtask_id TEXT NOT NULL, round INTEGER NOT NULL,
    decision TEXT, reason TEXT, numbers_json TEXT, delta_json TEXT,
    recorded_utc TEXT NOT NULL,
    PRIMARY KEY (run_id, subtask_id, round));

CREATE TABLE IF NOT EXISTS findings (
    run_id TEXT NOT NULL, subtask_id TEXT, round INTEGER NOT NULL, kind TEXT NOT NULL,
    ident TEXT NOT NULL, status TEXT NOT NULL, payload_json TEXT NOT NULL,
    step_id TEXT, first_seen_utc TEXT NOT NULL, last_seen_utc TEXT NOT NULL,
    PRIMARY KEY (run_id, subtask_id, kind, ident));

CREATE TABLE IF NOT EXISTS control (
    run_id TEXT PRIMARY KEY, command TEXT NOT NULL, note TEXT,
    requested_utc TEXT NOT NULL, acknowledged_utc TEXT);

CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, utc TEXT NOT NULL,
    kind TEXT NOT NULL, payload_json TEXT NOT NULL);

CREATE INDEX IF NOT EXISTS steps_by_run ON steps (run_id, stage, round);
CREATE INDEX IF NOT EXISTS events_by_run ON events (run_id, seq);
"""


def state_root(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Where runs live. Outside the repository, because the repository is in OneDrive.

    Order: the explicit argument, then VCC2026_ORCH_ROOT, then
    <VCC2026_DATA_ROOT>/orchestrator, then a default next to the analysis data.
    """
    if explicit:
        return Path(explicit).resolve()
    if os.environ.get("VCC2026_ORCH_ROOT"):
        return Path(os.environ["VCC2026_ORCH_ROOT"]).resolve()
    data_root = os.environ.get("VCC2026_DATA_ROOT") or "C:/Users/ferra/vcc2026-data"
    return (Path(data_root) / "orchestrator").resolve()


@dataclass(frozen=True)
class StepRecord:
    step_id: str
    run_id: str
    subtask_id: str | None
    stage: str
    round: int
    role: str
    service: str
    attempt: int
    status: str
    prompt_sha256: str
    directory: str
    planned_utc: str
    dispatched_utc: str | None
    settled_utc: str | None
    duration_ms: int | None
    error_kind: str | None
    error_detail: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "StepRecord":
        return cls(**{key: row[key] for key in cls.__dataclass_fields__})

    @property
    def path(self) -> Path:
        return Path(self.directory)


class Store:
    """The one place that writes state. Single process, single thread, synchronous."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = state_root(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "runs").mkdir(exist_ok=True)
        self.database_path = self.root / "orchestrator.sqlite3"
        try:
            self.connection = sqlite3.connect(str(self.database_path))
        except sqlite3.OperationalError as exc:
            writable = os.access(self.root, os.W_OK)
            raise sqlite3.OperationalError(
                f"unable to open orchestrator database at {self.database_path} "
                f"(parent exists={self.root.is_dir()} writable={writable} "
                f"is_file={self.database_path.is_file()}): {exc}"
            ) from exc
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript(_SCHEMA)
        self.connection.execute(
            "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),))
        self.connection.commit()

    # ------------------------------------------------------------------ plumbing
    def close(self) -> None:
        self.connection.close()

    def _write(self, sql: str, parameters: Iterable[Any] = ()) -> sqlite3.Cursor:
        cursor = self.connection.execute(sql, tuple(parameters))
        self.connection.commit()
        return cursor

    def run_dir(self, run_id: str) -> Path:
        return self.root / "runs" / run_id

    # -------------------------------------------------------------------- briefs
    def register_brief(self, brief, *, bump: bool = False) -> int:
        """Record this brief version, or refuse a silent edit. Returns the version used.

        Editing a brief without changing its version would make two different inputs
        share an identity, and every result produced under either would become
        ambiguous. So the store refuses, and `bump` is the explicit way forward.
        """
        row = self.connection.execute(
            "SELECT sha256 FROM briefs WHERE brief_id = ? AND version = ?",
            (brief.brief_id, brief.version)).fetchone()
        version = brief.version
        if row is not None and row["sha256"] != brief.content_sha256:
            if not bump:
                raise ValueError(
                    f"brief {brief.brief_id} v{brief.version} is already registered with "
                    f"different content (recorded {row['sha256'][:12]}, now "
                    f"{brief.content_sha256[:12]}). Bump 'version' in the file, or pass "
                    f"--bump-version to register the next one."
                )
            highest = self.connection.execute(
                "SELECT MAX(version) AS top FROM briefs WHERE brief_id = ?",
                (brief.brief_id,)).fetchone()["top"] or brief.version
            version = int(highest) + 1
        self._write(
            "INSERT OR IGNORE INTO briefs (brief_id, version, sha256, title, source_path,"
            " registered_utc) VALUES (?, ?, ?, ?, ?, ?)",
            (brief.brief_id, version, brief.content_sha256, brief.title,
             str(brief.source_path), utc_now()))
        return version

    def brief_versions(self, brief_id: str) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            "SELECT * FROM briefs WHERE brief_id = ? ORDER BY version", (brief_id,)))

    # ---------------------------------------------------------------------- runs
    def create_run(self, *, run_id: str, brief, version: int, route: str, label: str | None,
                   deadline_utc: str | None, snapshot: dict) -> Path:
        directory = self.run_dir(run_id)
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "steps").mkdir()
        write_json_new(directory / "run.json", snapshot)
        self._write(
            "INSERT INTO runs (run_id, brief_id, brief_version, brief_sha256, label, route,"
            " status, created_utc, deadline_utc) VALUES (?, ?, ?, ?, ?, ?, 'created', ?, ?)",
            (run_id, brief.brief_id, version, brief.content_sha256, label, route,
             utc_now(), deadline_utc))
        self.event(run_id, "run_created", {"brief": brief.brief_id, "version": version,
                                           "route": route, "label": label})
        return directory

    def set_run_status(self, run_id: str, status: str, *, reason: str | None = None,
                       detail: str | None = None) -> None:
        if status not in RUN_STATES:
            raise ValueError(f"unknown run status {status!r}")
        stamp = utc_now()
        fields = ["status = ?"]
        values: list[Any] = [status]
        if status == "running":
            fields.append("started_utc = COALESCE(started_utc, ?)")
            values.append(stamp)
        if status in ("finished", "stopped", "failed"):
            fields.append("ended_utc = ?")
            values.append(stamp)
        if reason is not None:
            fields.append("stop_reason = ?")
            values.append(reason)
        if detail is not None:
            fields.append("stop_detail = ?")
            values.append(detail)
        values.append(run_id)
        self._write(f"UPDATE runs SET {', '.join(fields)} WHERE run_id = ?", values)
        self.event(run_id, "run_status", {"status": status, "reason": reason, "detail": detail})

    def run(self, run_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()

    def runs(self, limit: int = 50) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            "SELECT * FROM runs ORDER BY created_utc DESC LIMIT ?", (limit,)))

    def latest_run_id(self) -> str | None:
        row = self.connection.execute(
            "SELECT run_id FROM runs ORDER BY created_utc DESC LIMIT 1").fetchone()
        return row["run_id"] if row else None

    # ------------------------------------------------------------------ subtasks
    def put_subtask(self, run_id: str, subtask, *, position: int, route: str,
                    status: str = "pending") -> None:
        self._write(
            "INSERT OR REPLACE INTO subtasks (run_id, subtask_id, title, question, route,"
            " criteria, origin, status, rounds_done, position) VALUES (?,?,?,?,?,?,?,?,"
            " COALESCE((SELECT rounds_done FROM subtasks WHERE run_id=? AND subtask_id=?),0), ?)",
            (run_id, subtask.ident, subtask.title, subtask.question, route,
             ",".join(subtask.criteria), subtask.origin, status, run_id, subtask.ident,
             position))

    def set_subtask_status(self, run_id: str, subtask_id: str, status: str, *,
                           reason: str | None = None, detail: str | None = None,
                           rounds_done: int | None = None) -> None:
        fields = ["status = ?"]
        values: list[Any] = [status]
        if reason is not None:
            fields.append("stop_reason = ?")
            values.append(reason)
        if detail is not None:
            fields.append("stop_detail = ?")
            values.append(detail)
        if rounds_done is not None:
            fields.append("rounds_done = ?")
            values.append(rounds_done)
        values += [run_id, subtask_id]
        self._write(f"UPDATE subtasks SET {', '.join(fields)} WHERE run_id = ? AND subtask_id = ?",
                    values)

    def subtasks(self, run_id: str) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            "SELECT * FROM subtasks WHERE run_id = ? ORDER BY position", (run_id,)))

    # --------------------------------------------------------------------- steps
    def plan_step(self, *, step_id: str, run_id: str, subtask_id: str | None, stage: str,
                  round_number: int, role: str, service: str, prompt: str,
                  attempt: int = 1) -> StepRecord:
        """Reserve a step id and write the prompt to disk before anything is sent.

        The UNIQUE primary key is the duplicate-send guard: the same run, subtask, round,
        role and prompt produce the same id, so a resumed run recognises work already
        done instead of asking the same question twice.
        """
        from .util import sha256_text

        existing = self.step(step_id)
        if existing is not None:
            return existing
        directory = self.run_dir(run_id) / "steps" / f"{stage}-{round_number:02d}-{role}-{step_id[:8]}"
        if attempt > 1:
            directory = directory.with_name(directory.name + f"-a{attempt}")
        directory.mkdir(parents=True, exist_ok=True)
        write_new(directory / "prompt.txt", prompt)
        self._write(
            "INSERT INTO steps (step_id, run_id, subtask_id, stage, round, role, service,"
            " attempt, status, prompt_sha256, directory, planned_utc)"
            " VALUES (?,?,?,?,?,?,?,?,'planned',?,?,?)",
            (step_id, run_id, subtask_id, stage, round_number, role, service, attempt,
             sha256_text(prompt), str(directory), utc_now()))
        self.event(run_id, "step_planned", {"step_id": step_id, "stage": stage,
                                            "round": round_number, "role": role,
                                            "service": service, "dir": str(directory)})
        return self.step(step_id)

    def mark_dispatched(self, step_id: str) -> None:
        """Commit the intent to send *before* sending, so a crash leaves a trace."""
        self._write("UPDATE steps SET status = 'dispatched', dispatched_utc = ? WHERE step_id = ?",
                    (utc_now(), step_id))
        row = self.step(step_id)
        self.event(row.run_id, "step_dispatched", {"step_id": step_id, "role": row.role,
                                                   "service": row.service})

    def settle_step(self, step_id: str, status: str, *, duration_ms: int | None = None,
                    error_kind: str | None = None, error_detail: str | None = None) -> None:
        if status not in STEP_STATES:
            raise ValueError(f"unknown step status {status!r}")
        self._write(
            "UPDATE steps SET status = ?, settled_utc = ?, duration_ms = ?, error_kind = ?,"
            " error_detail = ? WHERE step_id = ?",
            (status, utc_now(), duration_ms, error_kind, error_detail, step_id))
        row = self.step(step_id)
        self.event(row.run_id, "step_settled", {"step_id": step_id, "status": status,
                                                "role": row.role, "service": row.service,
                                                "error_kind": error_kind,
                                                "error_detail": (error_detail or "")[:400]})

    def step(self, step_id: str) -> StepRecord | None:
        row = self.connection.execute(
            "SELECT * FROM steps WHERE step_id = ?", (step_id,)).fetchone()
        return StepRecord.from_row(row) if row else None

    def steps(self, run_id: str, *, subtask_id: str | None = None,
              stage: str | None = None) -> list[StepRecord]:
        sql = "SELECT * FROM steps WHERE run_id = ?"
        values: list[Any] = [run_id]
        if subtask_id is not None:
            sql += " AND subtask_id = ?"
            values.append(subtask_id)
        if stage is not None:
            sql += " AND stage = ?"
            values.append(stage)
        sql += " ORDER BY planned_utc, round"
        return [StepRecord.from_row(row) for row in self.connection.execute(sql, values)]

    def unsettled_steps(self, run_id: str) -> list[StepRecord]:
        return [step for step in self.steps(run_id) if step.status == "dispatched"]

    # ------------------------------------------------------------------ artefacts
    def save_reply(self, step: StepRecord, text: str, *, parsed: dict | None = None,
                   meta: dict | None = None) -> Path:
        path = step.path / "response.raw.txt"
        write_new(path, text)
        if parsed is not None:
            write_json_new(step.path / "response.parsed.json", parsed)
        if meta is not None:
            write_json_new(step.path / "transport.json", meta)
        return path

    def reply_text(self, step: StepRecord) -> str | None:
        path = step.path / "response.raw.txt"
        return path.read_text(encoding="utf-8") if path.exists() else None

    def parsed_reply(self, step: StepRecord) -> dict | None:
        path = step.path / "response.parsed.json"
        return read_json(path) if path.exists() else None

    # ------------------------------------------------------------------- findings
    def record_finding(self, *, run_id: str, subtask_id: str | None, round_number: int,
                       kind: str, ident: str, status: str, payload: dict,
                       step_id: str | None) -> bool:
        """Insert or refresh a finding. Returns True when it is new to this run."""
        import json as _json

        row = self.connection.execute(
            "SELECT ident FROM findings WHERE run_id = ? AND IFNULL(subtask_id,'') = ?"
            " AND kind = ? AND ident = ?",
            (run_id, subtask_id or "", kind, ident)).fetchone()
        stamp = utc_now()
        if row is None:
            self._write(
                "INSERT INTO findings (run_id, subtask_id, round, kind, ident, status,"
                " payload_json, step_id, first_seen_utc, last_seen_utc)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (run_id, subtask_id, round_number, kind, ident, status,
                 _json.dumps(payload, ensure_ascii=False), step_id, stamp, stamp))
            return True
        self._write(
            "UPDATE findings SET status = ?, payload_json = ?, last_seen_utc = ?"
            " WHERE run_id = ? AND IFNULL(subtask_id,'') = ? AND kind = ? AND ident = ?",
            (status, _json.dumps(payload, ensure_ascii=False), stamp, run_id,
             subtask_id or "", kind, ident))
        return False

    def findings(self, run_id: str, *, subtask_id: str | None = None,
                 kind: str | None = None, status: str | None = None) -> list[sqlite3.Row]:
        sql = "SELECT * FROM findings WHERE run_id = ?"
        values: list[Any] = [run_id]
        if subtask_id is not None:
            sql += " AND IFNULL(subtask_id,'') = ?"
            values.append(subtask_id)
        if kind is not None:
            sql += " AND kind = ?"
            values.append(kind)
        if status is not None:
            sql += " AND status = ?"
            values.append(status)
        return list(self.connection.execute(sql + " ORDER BY first_seen_utc", values))

    # --------------------------------------------------------------------- rounds
    def record_round(self, *, run_id: str, subtask_id: str, round_number: int,
                     decision: str, reason: str, numbers: dict, delta: dict) -> None:
        import json as _json

        self._write(
            "INSERT OR REPLACE INTO rounds (run_id, subtask_id, round, decision, reason,"
            " numbers_json, delta_json, recorded_utc) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, subtask_id, round_number, decision, reason,
             _json.dumps(numbers, ensure_ascii=False),
             _json.dumps(delta, ensure_ascii=False), utc_now()))
        self.event(run_id, "round_evaluated", {"subtask": subtask_id, "round": round_number,
                                               "decision": decision, "reason": reason,
                                               "numbers": numbers})

    def rounds(self, run_id: str, subtask_id: str) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            "SELECT * FROM rounds WHERE run_id = ? AND subtask_id = ? ORDER BY round",
            (run_id, subtask_id)))

    # -------------------------------------------------------------------- control
    def request_control(self, run_id: str, command: str, note: str | None = None) -> None:
        if command not in ("pause", "resume", "stop", "approve_plan", "skip_step"):
            raise ValueError(f"unknown control command {command!r}")
        self._write(
            "INSERT OR REPLACE INTO control (run_id, command, note, requested_utc,"
            " acknowledged_utc) VALUES (?, ?, ?, ?, NULL)",
            (run_id, command, note, utc_now()))
        self.event(run_id, "control_requested", {"command": command, "note": note})

    def pending_control(self, run_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM control WHERE run_id = ? AND acknowledged_utc IS NULL",
            (run_id,)).fetchone()

    def acknowledge_control(self, run_id: str) -> None:
        self._write("UPDATE control SET acknowledged_utc = ? WHERE run_id = ?",
                    (utc_now(), run_id))

    # --------------------------------------------------------------------- events
    def event(self, run_id: str | None, kind: str, payload: dict) -> None:
        import json as _json

        stamp = utc_now()
        self._write("INSERT INTO events (run_id, utc, kind, payload_json) VALUES (?,?,?,?)",
                    (run_id, stamp, kind, _json.dumps(payload, ensure_ascii=False)))
        if run_id:
            directory = self.run_dir(run_id)
            if directory.exists():
                append_jsonl(directory / "events.jsonl",
                             {"utc": stamp, "kind": kind, **payload})

    def events(self, run_id: str, *, since: int = 0, limit: int = 200) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            "SELECT * FROM events WHERE run_id = ? AND seq > ? ORDER BY seq LIMIT ?",
            (run_id, since, limit)))
