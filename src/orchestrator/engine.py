"""The loop itself: deterministic code that decides who is asked what, and when to stop.

Everything the engine does is a function of the brief, the configuration and what is
already recorded on disk. A model reply contributes text and structured fields; it never
contributes a decision. Concretely:

* the route comes from configuration (a reply may *hint*, and the hint is resolved
  against the allowlist or ignored);
* counters, timeouts, retries and stop conditions come from `Limits`;
* a step is written down before it is sent, so a crash cannot hide a delivered question;
* a step already answered is never asked again -- the id is derived from the prompt.

The run is single-threaded and synchronous on purpose. Two browser sessions typing at
once is not worth the class of bug it buys, and the operator watches one thing happen at
a time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable

from .adapters import Adapter, Reply, Request, TransportError, build_adapter
from .briefs import Brief, Subtask
from .checks import ABSENT, CheckResult, PASS, PENDING, checks_not_run, run_checks
from .convergence import (
    Decision, Evaluation, Limits, RoleTurn, RoundState, describe, evaluate, round_delta,
)
from .protocol import (
    SENTINEL, ContentProblem, ParsedReply, PeerContribution, StandIn, code_blocks,
    frame_prompt, parse_reply, repair_prompt, review_prompt, solve_prompt,
)
from .settings import Settings
from .store import Store, StepRecord
from .util import read_json, short_id, similarity, utc_now, write_json_new


class RunInterrupted(RuntimeError):
    """Base for the ways a run stops without finishing its plan."""

    decision = Decision.HUMAN_STOP
    reason = "interrupted"

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail or self.reason)
        self.detail = detail


class OperatorStop(RunInterrupted):
    decision, reason = Decision.HUMAN_STOP, "operator_stop"


class ServiceUnavailable(RunInterrupted):
    decision, reason = Decision.SERVICE_UNAVAILABLE, "service_unavailable"


class NeedsReconciliation(RunInterrupted):
    """A step was in flight when the process died. Never resent without a decision."""

    decision, reason = Decision.HUMAN_STOP, "needs_reconciliation"


class AwaitingPlanApproval(RunInterrupted):
    decision, reason = Decision.HUMAN_STOP, "awaiting_plan_approval"


@dataclass
class Turn:
    """One role's contribution to one round, as the engine sees it after parsing."""

    role: str
    service: str
    step: StepRecord
    parsed: ParsedReply | None
    raw: str

    @property
    def usable(self) -> bool:
        """A reply that satisfied the contract and actually carries a proposal."""
        return self.parsed is not None and bool(self.parsed.proposal.strip())

    @property
    def proposal(self) -> str:
        """The proposal, or nothing. Never the raw text of an unreadable answer.

        Half an answer forwarded as a whole one is the failure this guards against: it
        would be checked, compared and quoted as if it were a position the model took.
        The raw text is kept on disk and shown in the report, but it does not travel.
        """
        return self.parsed.proposal if self.usable else ""

    def as_peer(self) -> PeerContribution:
        if not self.usable:
            return PeerContribution(
                role=self.role, usable=False,
                note=self.step.error_kind or "risposta non conforme al contratto")
        return PeerContribution(role=self.role, proposal=self.parsed.proposal,
                                changes=self.parsed.changes,
                                open_questions=self.parsed.open_questions)


class Engine:
    # Which contract this engine reads back. The research mode sets its own, and that is
    # the only thing that decides where a result block ends and a code artefact begins.
    sentinel = SENTINEL

    def __init__(self, store: Store, settings: Settings, brief: Brief, run_id: str, *,
                 log: Callable[[str], None] = print,
                 allow_unverified_profiles: bool = False,
                 mode_overrides: dict[str, dict[str, bool]] | None = None,
                 heartbeat: Callable[[], None] | None = None) -> None:
        self.store = store
        self.settings = settings
        self.brief = brief
        self.run_id = run_id
        self.log = log
        # Called while waiting for a service, so a run that is working does not look dead.
        # The lock is refreshed only when the engine writes a log line, and it writes none
        # during a wait: after two minutes `orch status` said «processo non attivo» about a
        # process that was mid-answer. Someone reading that could reasonably force a second
        # process onto the same run.
        self.heartbeat = heartbeat or (lambda: None)
        self.allow_unverified_profiles = allow_unverified_profiles
        # Composer switches this campaign needs on top of the ones the service already
        # declares -- the research mode uses it to demand the web-search toggle. They are
        # merged into the adapter's configuration, where `apply_modes` enforces and
        # verifies them before anything is sent. Empty for the debug loop.
        self.mode_overrides = {service: dict(modes)
                               for service, modes in (mode_overrides or {}).items()}
        self.limits = Limits.from_config(settings.raw.get("limits"), brief.limits)
        self._adapters: dict[str, Adapter] = {}
        # Two counters on purpose. An absence is the service failing and can end the run;
        # a skip is the operator choosing not to wait and never can. Both count towards
        # handing the seat to a reserve, because either way that service is not producing.
        self._absences: dict[str, int] = {}
        self._skips: dict[str, int] = {}
        self._checked: set[str] = set()
        self._paused_notified = False
        # A seat whose usual holder stopped answering can be handed to the reserve the
        # route declares. Kept here for the rest of the run, and rebuilt from the events
        # when a run resumes, so a resumed run does not queue up behind a dead service
        # again.
        self._seat: dict[str, str] = {}

    # ------------------------------------------------------------------ contract
    def _parse(self, text: str, *, require_proposal: bool = True) -> ParsedReply:
        """Read a reply under this engine's contract.

        A seam, not a feature: the research mode reads a different set of fields out of a
        reply, and everything around it -- resume, one repair, quarantine, the rule that a
        delivered question is never resent -- must stay the code that was already tested.
        """
        return parse_reply(text, require_proposal=require_proposal)

    def _repair_prompt(self, problem: ContentProblem) -> str:
        return repair_prompt(problem)

    # ------------------------------------------------------------------ adapters
    def adapter(self, service: str) -> Adapter:
        if service not in self._adapters:
            config = dict(self.settings.service_config(service))
            if self.allow_unverified_profiles:
                config["allow_unverified"] = True
            extra = self.mode_overrides.get(service)
            if extra:
                config["modes"] = {**(config.get("modes") or {}), **extra}
            adapter = build_adapter(service, config, state_root=self.store.root,
                                    config_dir=self.settings.config_dir)
            self._adapters[service] = adapter
        adapter = self._adapters[service]
        if service not in self._checked:
            health = adapter.preflight()
            self.store.event(self.run_id, "service_preflight",
                             {"service": service, "ok": health.ok, "detail": health.detail})
            if not health.ok:
                raise ServiceUnavailable(f"{service}: {health.detail}")
            self._checked.add(service)
        return adapter

    def close(self) -> None:
        for adapter in self._adapters.values():
            adapter.close()
        self._adapters.clear()

    # ------------------------------------------------------------------- control
    def _control_gate(self) -> None:
        """Honour pause/stop between steps. A pause holds here until the operator says go."""
        while True:
            pending = self.store.pending_control(self.run_id)
            if pending is None:
                return
            command = pending["command"]
            if command == "stop":
                self.store.acknowledge_control(self.run_id)
                raise OperatorStop(pending["note"] or "")
            if command == "skip_step":
                # A skip asked while nothing is waiting refers to a step that already
                # ended: drop it, or it would silently give up on the next one.
                self.store.acknowledge_control(self.run_id)
                self.log("[skip ignorato] nessun passo era in attesa")
                return
            if command == "pause":
                if not self._paused_notified:
                    self.store.set_run_status(self.run_id, "paused")
                    self.log("[pausa] richiesta dall'operatore: "
                             "`orch resume` per continuare, `orch stop` per fermare.")
                    self._paused_notified = True
                time.sleep(2.0)
                continue
            # resume / approve_plan: acknowledge and carry on
            self.store.acknowledge_control(self.run_id)
            if self._paused_notified:
                self.store.set_run_status(self.run_id, "running")
                self._paused_notified = False
                self.log("[ripresa]")
            return

    def _elapsed_minutes(self) -> float:
        row = self.store.run(self.run_id)
        started = row["started_utc"] if row else None
        if not started:
            return 0.0
        begin = datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - begin).total_seconds() / 60.0

    # --------------------------------------------------------------------- steps
    def _existing_answer(self, *, stage: str, subtask_id: str | None, round_number: int,
                         role: str, prompt_sha: str) -> StepRecord | None:
        for step in self.store.steps(self.run_id, stage=stage):
            if (step.role == role and (step.subtask_id or None) == (subtask_id or None)
                    and step.round == round_number and step.prompt_sha256 == prompt_sha
                    and step.status in ("answered", "unparsed")):
                return step
        return None

    def _existing_repair(self, *, stage: str, subtask_id: str | None, round_number: int,
                         role: str, unparsed_sha: str) -> StepRecord | None:
        """The answer a repair produced in this slot, when the first attempt was unreadable.

        A slot is one stage, subtask, round and role, and the engine sends at most two
        questions into it: the real one, and -- if the reply did not parse -- one repair
        asking for the result block alone. So an *answered* step in the slot whose prompt
        is not the main prompt can only be that repair.

        Without this, a resumed run found the unreadable first attempt, stopped looking,
        and carried on as if that model had never answered: the repaired answer sat on
        disk, ignored, and the peer was told a voice was missing. Found on the research
        rehearsal of 2026-09-14, and the debugging loop had the same hole.
        """
        for step in self.store.steps(self.run_id, stage=stage):
            if (step.role == role and (step.subtask_id or None) == (subtask_id or None)
                    and step.round == round_number and step.status == "answered"
                    and step.prompt_sha256 != unparsed_sha):
                return step
        return None

    def _in_flight(self, *, stage: str, subtask_id: str | None, round_number: int,
                   role: str) -> StepRecord | None:
        for step in self.store.steps(self.run_id, stage=stage):
            if (step.role == role and (step.subtask_id or None) == (subtask_id or None)
                    and step.round == round_number and step.status == "dispatched"):
                return step
        return None

    def _service_for(self, role: str) -> str:
        """Who holds this seat right now: the reserve if it was handed over, else the map."""
        return self._seat.get(role) or self.settings.service_of(role)

    def _ask(self, *, stage: str, subtask_id: str | None, round_number: int, role: str,
             prompt: str, require_proposal: bool = True, service: str | None = None,
             reserve: str | None = None) -> Turn:
        """Ask one role one question, with resume, retry and repair handled here.

        `service` overrides who is asked -- that is how a reserve answers in a seat --
        and `reserve` says whether one exists, which is what decides between stopping the
        run and handing the seat over when a service goes quiet for good.
        """
        from .util import sha256_text

        self._control_gate()
        service = service or self._service_for(role)
        prompt_sha = sha256_text(prompt)

        done = self._existing_answer(stage=stage, subtask_id=subtask_id,
                                     round_number=round_number, role=role, prompt_sha=prompt_sha)
        if done is not None and done.status == "unparsed":
            repaired = self._existing_repair(stage=stage, subtask_id=subtask_id,
                                             round_number=round_number, role=role,
                                             unparsed_sha=done.prompt_sha256)
            if repaired is not None:
                done = repaired
        if done is not None:
            raw = self.store.reply_text(done) or ""
            parsed = None
            if done.status == "answered":
                try:
                    parsed = self._parse(raw, require_proposal=require_proposal)
                except ContentProblem:
                    parsed = None
            self.log(f"  [ripreso] {stage}/{role} round {round_number} da {done.step_id[:8]}")
            # `done.service`, not the seat's current holder: if a reserve answered this
            # step the first time round, the resumed run has to say so too.
            return Turn(role=role, service=done.service or service, step=done, parsed=parsed,
                        raw=raw)

        stranded = self._in_flight(stage=stage, subtask_id=subtask_id, round_number=round_number,
                                   role=role)
        if stranded is not None:
            self.store.set_run_status(self.run_id, "needs_reconciliation")
            raise NeedsReconciliation(
                f"lo step {stranded.step_id[:8]} ({stage}/{role}) risulta inviato ma senza "
                f"risposta registrata: non lo reinvio da solo. Guarda "
                f"{stranded.directory} e usa `orch reconcile`.")

        attempt = 1
        while attempt <= self.limits.transport_retries + 10:
            step_id = short_id(self.run_id, stage, subtask_id or "-", str(round_number), role,
                               prompt_sha, f"attempt{attempt}")
            spent = self.store.step(step_id)
            if spent is not None and spent.status in ("abandoned", "transport_error"):
                if (spent.status == "abandoned" and spent.dispatched_utc
                        and spent.error_kind != "reconciled"):
                    # This attempt ended without an answer, not without a send: the
                    # question is already sitting in that conversation. Asking again on a
                    # resume would put the same question in the same chat twice, which is
                    # exactly what a delivered step must never suffer. Only the operator
                    # declaring it never arrived (`orch reconcile --abandon`) reopens it.
                    self.log(f"  [gia' chiesta] {stage}/{role} round {round_number}: la "
                             f"domanda era partita e non ha avuto risposta; non la rimando.")
                    return Turn(role=role, service=spent.service or service, step=spent,
                                parsed=None, raw="")
                # That attempt is closed and its folder holds what happened. A new try is a
                # new attempt with its own id and its own directory: the previous evidence
                # is neither overwritten nor mistaken for this one.
                attempt += 1
                continue
            step = self.store.plan_step(step_id=step_id, run_id=self.run_id,
                                        subtask_id=subtask_id, stage=stage,
                                        round_number=round_number, role=role, service=service,
                                        prompt=prompt, attempt=attempt)
            adapter = self.adapter(service)
            request = Request(prompt=prompt, role=role, service=service, step_id=step_id,
                              run_id=self.run_id,
                              conversation_key=f"{stage}:{subtask_id or 'none'}:{round_number}",
                              timeout_seconds=int(self.settings.service_config(service)
                                                  .get("timeout_seconds", 300)),
                              expect_marker=self.sentinel, artifact_dir=step.path)
            self.log(f"  -> {stage}/{role} ({service}) round {round_number}, tentativo {attempt}")
            started = time.monotonic()
            # 'dispatched' now means the prompt really left, because the adapter says so
            # after the send. Marking it earlier made the log claim a question had been
            # asked when the browser had not even opened.
            departure: list[float] = []

            def note_departure() -> None:
                departure.append(time.monotonic())
                self.store.mark_dispatched(step_id)

            def abort_if_asked() -> str | None:
                # Asked once a second by the adapter while it waits, which makes it the
                # one place that knows the run is still alive during a long answer.
                self.heartbeat()
                pending = self.store.pending_control(self.run_id)
                if pending is None:
                    return None
                if pending["command"] == "skip_step":
                    return "richiesta di saltare questo passo"
                if pending["command"] == "stop":
                    return "richiesta di fermare il run"
                return None

            request = replace(request, on_sent=note_departure, should_abort=abort_if_asked)
            try:
                reply: Reply = adapter.send(request)
            except TransportError as error:
                elapsed = int((time.monotonic() - started) * 1000)
                pending = self.store.pending_control(self.run_id)
                if pending is not None and pending["command"] == "skip_step":
                    # The operator decided not to wait. The step is given up, not retried
                    # and not resent. What happens next depends on whether the seat has a
                    # reserve: with one, «I am not waiting for this» means «ask the other
                    # service», which is what the operator expects; without one, the round
                    # goes on with a voice missing and the peer is told so.
                    self.store.acknowledge_control(self.run_id)
                    self.store.settle_step(step_id, "abandoned", duration_ms=elapsed,
                                           error_kind="skipped",
                                           error_detail=f"saltato dall'operatore: {error}")
                    self._skips[service] = self._skips.get(service, 0) + 1
                    self.log(f"     [saltato] {service} non ha risposto e l'operatore ha "
                             f"scelto di non aspettare")
                    # A skip is the operator acting, not a measurement of the service, so
                    # it can hand the seat over but must never end the run.
                    self._hand_over_if_possible(role=role, service=service, reserve=reserve,
                                                round_number=round_number)
                    return Turn(role=role, service=service, step=self.store.step(step_id),
                                parsed=None, raw="")
                if error.delivered or departure:
                    # The question went out and no answer came back. The operator's policy
                    # is to carry on without that voice for this round rather than stop the
                    # whole run: the other model is told the answer never arrived, and the
                    # report records which round was half. What is never done is resending
                    # -- the question is already sitting in that conversation.
                    if not departure:
                        self.store.mark_dispatched(step_id)
                    self.store.settle_step(step_id, "abandoned", duration_ms=elapsed,
                                           error_kind=error.kind,
                                           error_detail=f"nessuna risposta: {error}"[:2000])
                    self._absences[service] = self._absences.get(service, 0) + 1
                    missed = self._absences[service]
                    self.store.event(self.run_id, "step_delivered_without_reply",
                                     {"step_id": step_id, "service": service, "role": role,
                                      "consecutive": missed, "detail": str(error)[:400]})
                    self.log(f"     [assente] {service} non ha risposto ({error.kind}); "
                             f"il round prosegue senza. Assenze di fila: {missed}")
                    if missed >= max(1, self.limits.absence_tolerance):
                        handed = self._hand_over_if_possible(
                            role=role, service=service, reserve=reserve,
                            round_number=round_number)
                        if not handed:
                            raise ServiceUnavailable(
                                f"{service} non risponde da {missed} round di fila: il ciclo "
                                f"sarebbe un monologo. Ultimo errore: {error}") from error
                    return Turn(role=role, service=service, step=self.store.step(step_id),
                                parsed=None, raw="")
                self.store.settle_step(step_id, "transport_error", duration_ms=elapsed,
                                       error_kind=error.kind, error_detail=str(error)[:2000])
                self.log(f"     errore di canale ({error.kind}): {error}")
                if not error.recoverable or attempt > self.limits.transport_retries:
                    # The channel is down and the question never left. This used to raise
                    # here, and the raise jumped straight past the reserve the caller
                    # would have asked next: a service too broken to be written to was
                    # covered worse than one that merely stayed silent, which is backwards.
                    # It is the same failure of the same service, so it feeds the same
                    # counter and reaches the same reserve. Nothing was sent, so asking
                    # the reserve cannot ask the same question twice.
                    self._absences[service] = self._absences.get(service, 0) + 1
                    missed = self._absences[service]
                    self.store.event(self.run_id, "step_channel_failed",
                                     {"step_id": step_id, "service": service, "role": role,
                                      "consecutive": missed, "kind": error.kind,
                                      "detail": str(error)[:400]})
                    self._hand_over_if_possible(role=role, service=service, reserve=reserve,
                                                round_number=round_number)
                    if not reserve or reserve == service:
                        # No cover, or the one that just fell *is* the cover: there is
                        # nobody else to ask, and the run ends here rather than pretending.
                        raise ServiceUnavailable(
                            f"{service} ({error.kind}): {error}") from error
                    self.log(f"     [canale caduto] {service} ({error.kind}); il posto "
                             f"passa alla riserva per questo round. Assenze di fila: "
                             f"{missed}")
                    return Turn(role=role, service=service, step=self.store.step(step_id),
                                parsed=None, raw="")
                attempt += 1
                time.sleep(min(30, 5 * attempt))
                continue

            elapsed = int((time.monotonic() - started) * 1000)
            try:
                parsed = self._parse(reply.text, require_proposal=require_proposal)
            except ContentProblem as problem:
                self.store.save_reply(step, reply.text, meta={**reply.meta,
                                                              "content_problem": problem.kind})
                self.store.settle_step(step_id, "unparsed", duration_ms=elapsed,
                                       error_kind=problem.kind, error_detail=problem.detail)
                self.log(f"     risposta non conforme ({problem.kind}); chiedo solo il blocco")
                repaired = self._repair(stage=stage, subtask_id=subtask_id,
                                        round_number=round_number, role=role, service=service,
                                        problem=problem, require_proposal=require_proposal)
                if repaired is not None:
                    return repaired
                return Turn(role=role, service=service, step=step, parsed=None, raw=reply.text)

            self._absences[service] = 0        # answered: the streak is over
            self.store.save_reply(step, reply.text, parsed=parsed.as_record(), meta=reply.meta)
            self._quarantine(step, reply.text)
            self.store.settle_step(step_id, "answered", duration_ms=elapsed)
            if parsed.dropped_keys:
                self.store.event(self.run_id, "reply_keys_dropped",
                                 {"step_id": step_id, "keys": list(parsed.dropped_keys)})
            return Turn(role=role, service=service, step=step, parsed=parsed, raw=reply.text)

        raise ServiceUnavailable(
            f"{service}: troppi tentativi consumati su {stage}/{role} round {round_number}")

    def _repair(self, *, stage: str, subtask_id: str | None, round_number: int, role: str,
                service: str, problem: ContentProblem, require_proposal: bool) -> Turn | None:
        """One deterministic retry that asks for the result block and nothing else."""
        from .util import sha256_text

        prompt = self._repair_prompt(problem)
        step_id = short_id(self.run_id, stage, subtask_id or "-", str(round_number), role,
                           sha256_text(prompt), "repair")
        step = self.store.plan_step(step_id=step_id, run_id=self.run_id, subtask_id=subtask_id,
                                    stage=stage, round_number=round_number, role=role,
                                    service=service, prompt=prompt, attempt=2)
        request = Request(prompt=prompt, role=role, service=service, step_id=step_id,
                          run_id=self.run_id,
                          conversation_key=f"{stage}:{subtask_id or 'none'}:{round_number}",
                          expect_marker=self.sentinel, artifact_dir=step.path)
        self.store.mark_dispatched(step_id)
        try:
            reply = self.adapter(service).send(request)
        except TransportError as error:
            self.store.settle_step(step_id, "transport_error", error_kind=error.kind,
                                   error_detail=str(error)[:2000])
            return None
        try:
            parsed = self._parse(reply.text, require_proposal=require_proposal)
        except ContentProblem as second:
            self.store.save_reply(step, reply.text, meta={**reply.meta,
                                                          "content_problem": second.kind})
            self.store.settle_step(step_id, "unparsed", error_kind=second.kind,
                                   error_detail=second.detail)
            return None
        self.store.save_reply(step, reply.text, parsed=parsed.as_record(), meta=reply.meta)
        self.store.settle_step(step_id, "answered")
        return Turn(role=role, service=service, step=step, parsed=parsed, raw=reply.text)

    def _quarantine(self, step: StepRecord, text: str) -> None:
        """Code produced by a model is saved as an artefact to review, and never run.

        The policy is checked at load time (`settings.execution_policy`), so there is no
        code path here that could execute one of these files.
        """
        blocks = code_blocks(text, sentinel=self.sentinel)
        if not blocks:
            return
        directory = step.path / "quarantine"
        directory.mkdir(exist_ok=True)
        readme = directory / "LEGGIMI.txt"
        if not readme.exists():
            from .util import write_new as _write
            _write(readme,
                   "Blocchi di codice estratti da una risposta di un modello.\n"
                   "Sono artefatti da revisionare a mano. L'orchestratore non li esegue e "
                   "non ha un percorso di codice che possa eseguirli.\n"
                   f"Passo: {step.step_id} — {step.stage}/{step.role} ({step.service})\n")
        for index, (suffix, body) in enumerate(blocks, start=1):
            path = directory / f"block-{index:02d}.{suffix}"
            if not path.exists():
                from .util import write_new as _write
                _write(path, body)
        self.store.event(self.run_id, "code_quarantined",
                         {"step_id": step.step_id, "blocks": len(blocks),
                          "dir": str(directory)})

    # ------------------------------------------------------------------ findings
    def _ingest(self, subtask_id: str | None, round_number: int, turn: Turn) -> None:
        if turn.parsed is None:
            self.store.record_finding(
                run_id=self.run_id, subtask_id=subtask_id, round_number=round_number,
                kind="objection", ident=f"UNPARSED-{turn.step.step_id[:8]}", status="open",
                payload={"severity": "major", "raised_by": "orchestrator", "role": turn.role,
                         "text": "la risposta non rispetta il contratto e non e' stata letta",
                         "target": turn.role},
                step_id=turn.step.step_id)
            return
        parsed = turn.parsed
        for item in parsed.evidence:
            self.store.record_finding(
                run_id=self.run_id, subtask_id=subtask_id, round_number=round_number,
                kind="evidence", ident=item.ident, status=item.kind,
                payload={"claim": item.claim, "support": item.support, "type": item.kind,
                         "role": turn.role, "round": round_number},
                step_id=turn.step.step_id)
        for item in parsed.objections:
            self.store.record_finding(
                run_id=self.run_id, subtask_id=subtask_id, round_number=round_number,
                kind="objection", ident=item.ident, status="open",
                payload={"severity": item.severity, "target": item.target, "text": item.text,
                         "raised_by": turn.role, "round": round_number},
                step_id=turn.step.step_id)
        for claim in parsed.resolved_objections:
            self._resolve_objection(subtask_id, claim, by_role=turn.role,
                                    round_number=round_number, step_id=turn.step.step_id)

    def _resolve_objection(self, subtask_id: str | None, claim: str, *, by_role: str,
                           round_number: int, step_id: str) -> None:
        """A claim of resolution is recorded as such; only the objector can close it.

        The distinction matters for the disagreement rule: 'I answered that' is not the
        same as 'I accept the answer', and treating them as equal would let a loop
        declare peace that neither side agreed to.
        """
        import json as _json

        for row in self.store.findings(self.run_id, subtask_id=subtask_id, kind="objection"):
            if row["status"] not in ("open", "resolved_claimed"):
                continue
            payload = _json.loads(row["payload_json"])
            matches = (claim.strip() == row["ident"]
                       or similarity(claim, payload.get("text", "")) >= 0.8)
            if not matches:
                continue
            status = "resolved" if payload.get("raised_by") == by_role else "resolved_claimed"
            payload["resolution"] = {"by": by_role, "round": round_number, "claim": claim[:400]}
            self.store.record_finding(
                run_id=self.run_id, subtask_id=subtask_id, round_number=round_number,
                kind="objection", ident=row["ident"], status=status, payload=payload,
                step_id=step_id)
            return

    def _objections_as_of(self, subtask_id: str | None, as_of_round: int) -> list[dict]:
        """Which objections were open at the end of `as_of_round`.

        Reconstructed from the recorded rounds rather than from the current status,
        because a prompt has to be reproducible: a resumed run must rebuild exactly the
        question it asked the first time, or the step id changes and the same question
        gets asked twice.
        """
        import json as _json

        open_rows: list[dict] = []
        for row in self.store.findings(self.run_id, subtask_id=subtask_id, kind="objection"):
            payload = _json.loads(row["payload_json"])
            raised = int(payload.get("round", row["round"]))
            if raised > as_of_round:
                continue
            resolution = payload.get("resolution") or {}
            accepted = (row["status"] == "resolved"
                        and int(resolution.get("round", 10**6)) <= as_of_round)
            if accepted:
                continue
            open_rows.append({"ident": row["ident"], **payload})
        return open_rows

    def _open_blocking(self, subtask_id: str | None, as_of_round: int,
                       roles: tuple[str, ...] = ()) -> list[str]:
        """Blocking objections aimed at another participant -- not at the material.

        The first real run stopped as 'unresolved disagreement' while the two models
        agreed almost entirely: what stayed open were their *shared* objections to the
        code under review, aimed at its author. Nobody was ever going to resolve those,
        because nobody disputed them. A disagreement is between participants; an objection
        to the material is a finding, and it belongs in the report, not in the stop rule.
        """
        open_rows = self._objections_as_of(subtask_id, as_of_round)
        blocking = [row for row in open_rows if row.get("severity") == "blocking"]
        if not roles:
            return [row["ident"] for row in blocking]
        return [row["ident"] for row in blocking
                if any(role.lower() in str(row.get("target", "")).lower() for role in roles)]

    def _open_disputes(self, subtask_id: str | None, as_of_round: int,
                       roles: tuple[str, ...]) -> list[str]:
        """Open objections one participant aimed at another, blocking or major.

        This is what separates a convergence from a stagnation: both mean nobody is
        producing anything new, and only one of them means nobody is still objecting.
        """
        return [row["ident"] for row in self._objections_as_of(subtask_id, as_of_round)
                if row.get("severity") in ("blocking", "major")
                and any(role.lower() in str(row.get("target", "")).lower() for role in roles)]

    def _open_objections(self, subtask_id: str | None, as_of_round: int):
        from .protocol import Objection

        return [Objection(ident=row["ident"], target=row.get("target", ""),
                          severity=row.get("severity", "major"), text=row.get("text", ""))
                for row in self._objections_as_of(subtask_id, as_of_round)]

    # -------------------------------------------------------------------- stages
    def _stage_frame(self, route) -> list[Subtask]:
        roles = route.roles("frame")
        proposed: list[Subtask] = []
        for role in roles:
            prompt = frame_prompt(self.brief, role=role,
                                  allowed_routes=self.settings.route_names)
            turn = self._ask(stage="frame", subtask_id=None, round_number=1, role=role,
                             prompt=prompt)
            self._ingest(None, 1, turn)
            if turn.parsed is None:
                continue
            for index, item in enumerate(turn.parsed.subtasks):
                criteria = tuple(
                    part.strip() for part in (item.get("criteria") or "").split(",")
                    if part.strip() and self.brief.criterion(part.strip())
                )
                proposed.append(Subtask(
                    ident=f"S{len(proposed) + 1}",
                    title=item["title"][:200],
                    question=item.get("question", item["title"]),
                    route=item.get("route") or None,
                    criteria=criteria,
                    origin=f"frame:{role}",
                ))
        return _merge_subtasks(proposed, self.brief)

    def _plan(self, route) -> list[Subtask]:
        """Fix the subtask list: from the brief, from framing, or from the operator."""
        approved_path = self.store.run_dir(self.run_id) / "plan.approved.json"
        if approved_path.exists():
            document = read_json(approved_path)
            return [Subtask(ident=item["id"], title=item["title"], question=item["question"],
                            route=item.get("route"), criteria=tuple(item.get("criteria", ())),
                            origin=item.get("origin", "operator"))
                    for item in document["subtasks"]]

        if self.brief.subtasks:
            return list(self.brief.subtasks)

        if not route.roles("frame"):
            return [Subtask(ident="S1", title=self.brief.title, question=self.brief.question,
                            criteria=tuple(c.ident for c in self.brief.acceptance_criteria),
                            origin="brief")]

        subtasks = self._stage_frame(route)
        draft = self.store.run_dir(self.run_id) / "plan.json"
        payload = {
            "run_id": self.run_id,
            "drafted_utc": utc_now(),
            "note": ("Proposta dalla fase di inquadramento. Modifica pure questo file, poi "
                     "`orch approve-plan <run>` lo congela in plan.approved.json."),
            "subtasks": [{"id": item.ident, "title": item.title, "question": item.question,
                          "route": item.route, "criteria": list(item.criteria),
                          "origin": item.origin} for item in subtasks],
        }
        if not draft.exists():
            write_json_new(draft, payload)
        if self.settings.plan_approval == "required":
            self.store.set_run_status(self.run_id, "awaiting_plan_approval")
            raise AwaitingPlanApproval(str(draft))
        return subtasks

    def _solve(self, subtask: Subtask, route) -> Evaluation:
        roles = route.roles("solve")
        criteria = [self.brief.criterion(ident) for ident in subtask.criteria]
        criteria = [item for item in criteria if item] or list(self.brief.acceptance_criteria)
        history: list[RoundState] = []
        last_turns: list[Turn] = []
        round_number = 0

        while True:
            round_number += 1
            # Built once, before anyone is asked: both roles are given the same view of
            # the previous round, so whoever is sent first gains nothing from the order.
            peer_views = {turn.role: self._peer_view(turn) for turn in last_turns}
            own_previous = {turn.role: turn.proposal for turn in last_turns if turn.usable}
            previous_service = {turn.role: turn.service for turn in last_turns}
            open_objections = self._open_objections(subtask.ident, round_number - 1)
            turns: list[Turn] = []
            for role in roles:
                reserve = route.reserve_for(role)
                peers = [self._as_read_by(view, role)
                         for name, view in sorted(peer_views.items()) if name != role]
                prompt = solve_prompt(
                    self.brief, subtask, role=role, round_number=round_number,
                    peers=peers, open_objections=open_objections,
                    own_previous=own_previous.get(role))
                turn = self._ask(stage="solve", subtask_id=subtask.ident,
                                 round_number=round_number, role=role, prompt=prompt,
                                 reserve=reserve)
                if reserve and _went_unanswered(turn):
                    turn = self._ask_reserve(
                        subtask, role=role, round_number=round_number, reserve=reserve,
                        absent_service=turn.service, peers=peers,
                        open_objections=open_objections, own_previous=own_previous.get(role),
                        own_previous_from=previous_service.get(role, ""), fallback=turn)
                turns.append(turn)

            # Rounds are synchronous: everyone answered the same state, so findings are
            # recorded only once the round is complete. Otherwise the role asked second
            # would be answering an objection the role asked first raised moments earlier,
            # and "independent proposals" would quietly stop being independent.
            for turn in turns:
                self._ingest(subtask.ident, round_number, turn)

            per_role_checks = {
                turn.role: (run_checks(criteria, turn.proposal) if turn.usable
                            else checks_not_run(
                                criteria, "nessuna risposta utilizzabile in questo round: "
                                          "il controllo non e' stato eseguito"))
                for turn in turns
            }
            aggregated = aggregate_checks(per_role_checks)
            state = RoundState(number=round_number, turns=tuple(
                RoleTurn(role=turn.role, proposal=turn.proposal,
                         evidence_ids=tuple(item.ident for item in (turn.parsed.evidence if turn.parsed else ())),
                         objection_ids=tuple(item.ident for item in (turn.parsed.objections if turn.parsed else ())),
                         resolved_ids=tuple(turn.parsed.resolved_objections if turn.parsed else ()),
                         changes=tuple(turn.parsed.changes if turn.parsed else ()),
                         unparsed=not turn.usable,
                         service=turn.service, family=self.settings.family(turn.service))
                for turn in turns))
            history.append(state)

            evaluation = evaluate(history, checks=aggregated, limits=self.limits,
                                  open_blocking=self._open_blocking(subtask.ident, round_number,
                                                                    tuple(roles)),
                                  open_disputes=self._open_disputes(subtask.ident, round_number,
                                                                    tuple(roles)),
                                  elapsed_minutes=self._elapsed_minutes())
            delta = round_delta(history[-2] if len(history) > 1 else None, state)
            delta["checks"] = {role: [check.as_record() for check in results]
                               for role, results in per_role_checks.items()}
            self.store.record_round(run_id=self.run_id, subtask_id=subtask.ident,
                                    round_number=round_number,
                                    decision=evaluation.decision.value, reason=evaluation.reason,
                                    numbers=evaluation.numbers, delta=delta)
            self.store.set_subtask_status(self.run_id, subtask.ident, "running",
                                          rounds_done=round_number)
            self.log(f"  {describe(evaluation)}")

            last_turns = turns
            if evaluation.is_terminal:
                self.store.set_subtask_status(
                    self.run_id, subtask.ident, "stopped",
                    reason=evaluation.decision.value, detail=describe(evaluation),
                    rounds_done=round_number)
                return evaluation

            checkpoint_every = self.settings.checkpoint_every
            if checkpoint_every and round_number % checkpoint_every == 0:
                self._checkpoint(subtask, route, round_number, last_turns)

    # ------------------------------------------------------------------- reserve
    def _hand_over_if_possible(self, *, role: str, service: str, reserve: str | None,
                               round_number: int) -> bool:
        """Give the seat to the reserve for the rest of the run, if there is one.

        Called both when a service has gone quiet for good and when the operator has
        given up waiting for it repeatedly: in either case, asking it again every round
        costs a full timeout and produces nothing. Returns whether the seat moved.
        """
        missed = self._absences.get(service, 0)
        given_up = self._skips.get(service, 0)
        if not reserve or reserve == service:
            return False
        if missed + given_up < max(1, self.limits.absence_tolerance):
            return False
        self._seat[role] = reserve
        self.store.event(self.run_id, "seat_reassigned",
                         {"role": role, "from": service, "to": reserve,
                          "round": round_number, "absences": missed, "skips": given_up})
        self.log(f"     [subentro stabile] {service}: {missed} assenze e {given_up} "
                 f"rinunce. Da qui in avanti il ruolo {role} e' di {reserve}. Non e' lo "
                 f"stesso modello di prima, e il rapporto lo scrive.")
        return True

    def _peer_view(self, turn: Turn) -> PeerContribution:
        """What the other role is shown, marked when a reserve wrote it.

        Derived from the service recorded on the step rather than from engine state, so
        it stays right after a resume, when the turns are read back from disk.
        """
        view = turn.as_peer()
        seat_service = self.settings.service_of(turn.role)
        if turn.service and turn.service != seat_service:
            view = replace(view, stand_in_for=seat_service, written_by=turn.service)
        return view

    def _as_read_by(self, view: PeerContribution, reader_role: str) -> PeerContribution:
        """Whether the reader is about to read an answer from its own model.

        The same peer view is 'another model' to one reader and 'yourself, twice' to
        another, so the flag belongs to the pair, not to the answer.
        """
        if not view.stand_in_for:
            return view
        # The service that actually wrote it, not whoever holds the seat now: the seat may
        # not have been handed over yet, and the question is who the reader is reading.
        writer = view.written_by or self.settings.service_of(view.role)
        same = self.settings.family(writer) == self.settings.family(
            self._service_for(reader_role))
        return replace(view, same_family=same)

    def _ask_reserve(self, subtask: Subtask, *, role: str, round_number: int, reserve: str,
                     absent_service: str, peers: list[PeerContribution],
                     open_objections, own_previous: str | None,
                     own_previous_from: str, fallback: Turn) -> Turn:
        """Put the reserve session in the seat for this round, and say so everywhere.

        The reserve is a second session of the service that is still answering, so the
        round keeps two voices instead of one. What it does not keep is two models: that
        is recorded on the step, told to the peer, and carried into the stop reason.

        A reserve that cannot be reached -- never logged in, browser refusing to start --
        must not make things worse than having no reserve at all, so the round falls back
        to going on with one voice.
        """
        # Two different situations, and telling them apart is the difference between an
        # accurate prompt and a false one: entering the seat for the first time, or still
        # covering it from the round before, in which case the previous proposal is its own.
        stand_in = StandIn(seat_role=role, absent_service=absent_service,
                           previous_from="" if own_previous_from == reserve
                           else own_previous_from,
                           continuing=own_previous_from == reserve)
        prompt = solve_prompt(self.brief, subtask, role=role, round_number=round_number,
                              peers=peers, open_objections=open_objections,
                              own_previous=own_previous, stand_in=stand_in)
        self.store.event(self.run_id, "stand_in_used",
                         {"role": role, "absent": absent_service, "reserve": reserve,
                          "round": round_number, "subtask": subtask.ident,
                          "reserve_family": self.settings.family(reserve),
                          "absent_family": self.settings.family(absent_service)})
        self.log(f"     [riserva] {reserve} risponde al posto di {absent_service} per il "
                 f"round {round_number}: due sessioni, un modello solo.")
        try:
            return self._ask(stage="solve", subtask_id=subtask.ident,
                             round_number=round_number, role=role, prompt=prompt,
                             service=reserve, reserve=reserve)
        except ServiceUnavailable as error:
            self.store.event(self.run_id, "stand_in_unavailable",
                             {"role": role, "reserve": reserve, "round": round_number,
                              "detail": str(error)[:400]})
            self.log(f"     [riserva non disponibile] {reserve}: {error}. Il round "
                     f"prosegue con una voce sola, come se la riserva non ci fosse.")
            return fallback

    def _checkpoint(self, subtask: Subtask, route, round_number: int, turns: list[Turn]) -> None:
        """A bounded consultation with a reviewer in the middle of the loop."""
        roles = route.roles("checkpoint")
        if not roles:
            return
        digest = _digest(subtask, turns)
        for role in roles:
            prompt = review_prompt(self.brief, role=role, subtask_digests=[digest])
            turn = self._ask(stage="checkpoint", subtask_id=subtask.ident,
                             round_number=round_number, role=role, prompt=prompt)
            self._ingest(subtask.ident, round_number, turn)

    def _stage_review(self, route, digests: list[str]) -> list[Turn]:
        turns: list[Turn] = []
        for role in route.roles("review"):
            prompt = review_prompt(self.brief, role=role, subtask_digests=digests)
            turn = self._ask(stage="review", subtask_id=None, round_number=1, role=role,
                             prompt=prompt)
            self._ingest(None, 1, turn)
            turns.append(turn)
        return turns

    def _restore_seats(self) -> None:
        """Read back which seats were handed to a reserve before the run was interrupted."""
        import json as _json

        seen = 0
        while True:
            batch = self.store.events(self.run_id, since=seen, limit=500)
            if not batch:
                return
            for row in batch:
                seen = row["seq"]
                if row["kind"] != "seat_reassigned":
                    continue
                payload = _json.loads(row["payload_json"])
                self._seat[payload["role"]] = payload["to"]
                self.log(f"[subentro in corso] il ruolo {payload['role']} era gia' passato "
                         f"da {payload['from']} a {payload['to']} al round "
                         f"{payload.get('round', '?')}")

    # ----------------------------------------------------------------------- run
    def run(self) -> str:
        """Execute the run to a stopping point. Returns the run's final status."""
        row = self.store.run(self.run_id)
        if row is None:
            raise ValueError(f"unknown run {self.run_id}")
        route = self.settings.route(row["route"])
        self._restore_seats()
        self.store.set_run_status(self.run_id, "running")
        self.log(f"[avvio] run {self.run_id} — incarico «{self.brief.title}» "
                 f"v{row['brief_version']}, percorso «{route.name}»")

        try:
            subtasks = self._plan(route)
            for position, subtask in enumerate(subtasks):
                chosen = self.settings.route_or_default(subtask.route or route.name)
                self.store.put_subtask(self.run_id, subtask, position=position,
                                       route=chosen.name, status="pending")
            for subtask in subtasks:
                chosen = self.settings.route_or_default(subtask.route or route.name)
                self.log(f"[sottocompito {subtask.ident}] {subtask.title} "
                         f"(percorso {chosen.name})")
                self._solve(subtask, chosen)

            digests = []
            for subtask in subtasks:
                turns = self._last_turns(subtask.ident)
                digests.append(_digest(subtask, turns))
            self._stage_review(route, digests)

        except AwaitingPlanApproval as interruption:
            self.log(f"[in attesa] piano dei sottocompiti da approvare: {interruption.detail}")
            return "awaiting_plan_approval"
        except NeedsReconciliation as interruption:
            self.log(f"[da riconciliare] {interruption.detail}")
            return "needs_reconciliation"
        except OperatorStop as interruption:
            self.store.set_run_status(self.run_id, "stopped", reason="human_stop",
                                      detail=interruption.detail)
            self.log("[fermato dall'operatore]")
            return "stopped"
        except ServiceUnavailable as interruption:
            self.store.set_run_status(self.run_id, "stopped", reason="service_unavailable",
                                      detail=interruption.detail)
            self.log(f"[servizio non disponibile] {interruption.detail}. "
                     f"Nessuna sostituzione ulteriore: il modello manca e si vede.")
            return "stopped"
        except Exception as error:  # noqa: BLE001
            # Anything unforeseen still ends in a recorded state. The run that found this
            # necessary died opening the second browser and left itself marked 'running',
            # with no final event and no report: from the outside it was indistinguishable
            # from a run still in progress.
            import traceback

            report = traceback.format_exc()
            stamp = utc_now().replace(":", "").replace("-", "")
            path = self.store.run_dir(self.run_id) / f"error-{stamp}.txt"
            try:
                from .util import write_new as _write
                _write(path, report)
            except OSError:
                path = None
            summary = f"{type(error).__name__}: {str(error)[:400]}"
            self.store.event(self.run_id, "run_failed",
                             {"error": summary, "traceback": str(path)})
            self.store.set_run_status(self.run_id, "failed", reason="unexpected_error",
                                      detail=summary)
            self.log(f"[errore non previsto] {summary}")
            if path:
                self.log(f"  dettaglio completo: {path}")
            return "failed"
        finally:
            self.close()

        self.store.set_run_status(self.run_id, "finished", reason="completed_plan")
        return "finished"

    def _last_turns(self, subtask_id: str) -> list[Turn]:
        """The last recorded turn of each role on a subtask, read back from the store."""
        latest: dict[str, StepRecord] = {}
        for step in self.store.steps(self.run_id, subtask_id=subtask_id, stage="solve"):
            if step.status != "answered":
                continue
            current = latest.get(step.role)
            if current is None or step.round >= current.round:
                latest[step.role] = step
        turns = []
        for role, step in sorted(latest.items()):
            raw = self.store.reply_text(step) or ""
            try:
                parsed = self._parse(raw, require_proposal=True)
            except ContentProblem:
                parsed = None
            turns.append(Turn(role=role, service=step.service, step=step, parsed=parsed, raw=raw))
        return turns


# ------------------------------------------------------------------- helpers

def _went_unanswered(turn: Turn) -> bool:
    """This seat is empty for this round, whether the service failed or was given up on.

    Skips used to be excluded here, on the reasoning that an operator who chose not to
    wait should not be made to wait again. Watching it happen said otherwise: `orch skip`
    means «stop waiting for this one», and when a reserve exists the useful answer to that
    is to ask the reserve, not to lose the round.

    `transport_error` is here for the same reason, and it is the harder case: a channel
    that broke before the question left. Nothing was sent, so the seat is as empty as
    after a skip and the reserve can be asked without any risk of asking twice.
    """
    return (not turn.usable and turn.step is not None
            and turn.step.status in ("abandoned", "transport_error"))


def aggregate_checks(per_role: dict[str, list[CheckResult]]) -> list[CheckResult]:
    """A criterion counts as passed only if it passed on every role's own proposal.

    Not because agreement proves anything, but because a criterion that holds for one
    answer and not the other identifies no single verified result -- exactly the case a
    person needs to see.
    """
    if not per_role:
        return []
    by_criterion: dict[str, list[CheckResult]] = {}
    for results in per_role.values():
        for result in results:
            by_criterion.setdefault(result.criterion_id, []).append(result)
    aggregated: list[CheckResult] = []
    for criterion_id, results in by_criterion.items():
        failed = [item for item in results if item.status not in (PASS, PENDING, ABSENT)]
        missing = [item for item in results if item.status == ABSENT]
        pending = [item for item in results if item.status == PENDING]
        if failed:
            worst = failed[0]
            aggregated.append(CheckResult(criterion_id, worst.kind, worst.status,
                                          f"{len(failed)}/{len(results)} proposte non passano: "
                                          f"{worst.detail}", worst.evidence))
        elif missing:
            # Not verified, and not failed either: one of the seats was empty. It blocks
            # completion exactly as a failure would, and says something different.
            aggregated.append(CheckResult(
                criterion_id, missing[0].kind, ABSENT,
                f"{len(missing)}/{len(results)} proposte non hanno risposto: "
                f"{missing[0].detail}"))
        elif pending:
            aggregated.append(pending[0])
        else:
            aggregated.append(CheckResult(criterion_id, results[0].kind, PASS,
                                          f"passato su {len(results)} proposte",
                                          results[0].evidence))
    return aggregated


def _merge_subtasks(proposed: list[Subtask], brief: Brief) -> list[Subtask]:
    """Deduplicate the framing proposals by title, deterministically, and cap the list."""
    merged: list[Subtask] = []
    for item in proposed:
        twin = next((existing for existing in merged
                     if similarity(existing.title, item.title) >= 0.85), None)
        if twin is None:
            merged.append(item)
    if not merged:
        merged = [Subtask(ident="S1", title=brief.title, question=brief.question,
                          criteria=tuple(c.ident for c in brief.acceptance_criteria),
                          origin="fallback")]
    return [
        Subtask(ident=f"S{index + 1}", title=item.title, question=item.question,
                route=item.route, criteria=item.criteria, origin=item.origin)
        for index, item in enumerate(merged[:5])
    ]


def _digest(subtask: Subtask, turns: list[Turn]) -> str:
    """What a reviewer is shown: verbatim proposals, not a summary of summaries."""
    parts = [f"Sottocompito {subtask.ident}: {subtask.title}", f"Domanda: {subtask.question}"]
    for turn in turns:
        parts.append(f"\n--- proposta di {turn.role} ({turn.service}), round "
                     f"{turn.step.round} ---\n{turn.proposal}")
        if turn.parsed:
            for item in turn.parsed.objections:
                parts.append(f"[obiezione {item.ident} ({item.severity})] {item.text}")
    return "\n".join(parts)


def deadline_for(limits: Limits) -> str | None:
    if not limits.max_wall_clock_minutes:
        return None
    end = datetime.now(timezone.utc) + timedelta(minutes=limits.max_wall_clock_minutes)
    return end.strftime("%Y-%m-%dT%H:%M:%SZ")
