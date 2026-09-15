"""The three-phase research loop. Deterministic code, from the first prompt to the dossier.

It reuses the debugging engine for everything that was already paid for in bugs: a step
written down before it is sent, an id derived from the prompt so a resume recognises work
already done, a delivered question never resent, one repair and no more, code from a
model quarantined rather than run, pause and stop honoured between steps. What it changes
is the shape of the campaign:

    fase 1   ricerca indipendente          i due non si vedono
    fase 2   confronto e piste             ciascuno vede i risultati della fase 1
    fase 3   ricerca mirata e sintesi      ciascuno approfondisce le piste scelte

Three properties are load-bearing, and each has a test:

* **Every phase's view is built before anyone is asked.** Whoever is contacted second
  receives nothing the first one produced. The technical order of the sends is not
  allowed to be an advantage.
* **The leads are chosen by a rule, not by a model** (`leads.select_leads`). No model is
  asked which line of enquiry is worth the remaining budget -- including Claude, which is
  not reachable from this process at all.
* **The budget counts repairs and retries**, and the ledger is read back from the
  recorded steps rather than from a counter in memory, so an interrupted campaign charges
  itself for the sends it already made.
"""

from __future__ import annotations

from typing import Any, Callable

from ..briefs import Brief, Subtask
from ..engine import (
    Engine, NeedsReconciliation, OperatorStop, ServiceUnavailable,
)
from ..protocol import ContentProblem, ParsedReply
from ..settings import Settings
from ..store import Store
from ..util import clip, utc_now, write_json_new
from . import prompts
from .campaign import SearchCapability, load_research_brief, search_capability
from .contract import RESEARCH_SENTINEL, ResearchRecord, parse_research_reply
from .dossier import (
    PHASE_STAGES, build_dossier, build_research_report, decide_outcome, ledger_from_store,
    write_dossier,
)
from .leads import Selection, assign, select_leads

CAMPAIGN_SUBTASK = "R1"


class BudgetExhausted(RuntimeError):
    """The campaign has spent what it was allowed. Not an error: a declared ending."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class SearchUnavailable(RuntimeError):
    """The campaign needs a search tool the configured channels do not offer."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ResearchEngine(Engine):
    """A campaign in `scientific_research` mode. One brief, one subtask, three phases."""

    sentinel = RESEARCH_SENTINEL

    def __init__(self, store: Store, settings: Settings, brief: Brief, run_id: str, *,
                 log: Callable[[str], None] = print,
                 allow_unverified_profiles: bool = False,
                 heartbeat: Callable[[], None] | None = None) -> None:
        research = load_research_brief(brief, settings)
        row = store.run(run_id)
        route = settings.route(row["route"] if row else settings.default_route)
        self.workers: tuple[str, ...] = tuple(sorted(route.roles("solve")))
        self.route = route
        self.research = research
        self.capability: dict[str, SearchCapability] = {}
        self.plan_only = False
        self._records: list[ResearchRecord] = []
        self._selection = Selection(cap=research.budget.max_leads)
        self._interrupted: str | None = None
        self._interrupt_detail = ""

        overrides: dict[str, dict[str, bool]] = {}
        for role in self.workers:
            service = settings.service_of(role)
            state = search_capability(settings, service, wanted=research.search.required)
            self.capability[service] = state
            if state.can_search:
                # Asked for here, enforced and verified by the adapter before the first
                # message. If the switch cannot be set, nothing is sent: a campaign that
                # half-searched is worse than one that did not.
                overrides[service] = {state.mode_name: True}

        super().__init__(store, settings, brief, run_id, log=log,
                         allow_unverified_profiles=allow_unverified_profiles,
                         mode_overrides=overrides, heartbeat=heartbeat)

    # ------------------------------------------------------------------ contract
    def _parse(self, text: str, *, require_proposal: bool = True) -> ParsedReply:
        record = parse_research_reply(text, require_synthesis=require_proposal)
        return ParsedReply(
            raw=text, summary=record.summary, proposal=record.synthesis,
            open_questions=record.open_questions, dropped_keys=record.dropped_keys,
            issues=record.issues, confidence=record.confidence, research=record)

    def _repair_prompt(self, problem: ContentProblem) -> str:
        return prompts.repair_prompt(problem)

    # -------------------------------------------------------------------- budget
    def _already_answered(self, phase: int, role: str) -> bool:
        """Has this seat already produced an answer, in this run or an earlier attempt?"""
        return any(step.status == "answered" for step in
                   self.store.steps(self.run_id, subtask_id=CAMPAIGN_SUBTASK,
                                    stage=PHASE_STAGES[phase])
                   if step.role == role)

    def _spend(self, phase: int, role: str) -> None:
        """Refuse to open a seat the budget does not cover. Checked before the send.

        A seat that already has an answer costs nothing to revisit: `_ask` will hand back
        what is on disk without contacting anyone. Charging for it again would make a
        resumed campaign spend its whole budget re-reading its own transcript and then
        report `limit_reached` for work it had already finished -- which is what happened
        the first time this ran twice.
        """
        if self._already_answered(phase, role):
            return
        budget = self.research.budget
        ledger = ledger_from_store(self.store, self.run_id)
        if ledger.main_responses >= budget.max_main_responses:
            raise BudgetExhausted(
                f"{ledger.main_responses} risposte principali su un tetto di "
                f"{budget.max_main_responses}: la fase {phase} di {role} non parte")
        if ledger.total_interactions >= budget.max_total_interactions:
            raise BudgetExhausted(
                f"{ledger.total_interactions} interazioni totali (riparazioni e tentativi "
                f"compresi) su un tetto di {budget.max_total_interactions}")
        elapsed = self._elapsed_minutes()
        if budget.max_wall_clock_minutes and elapsed >= budget.max_wall_clock_minutes:
            raise BudgetExhausted(
                f"{elapsed:.0f} minuti trascorsi su un tetto di "
                f"{budget.max_wall_clock_minutes}")

    # --------------------------------------------------------------------- steps
    def _ask_worker(self, phase: int, role: str, prompt: str) -> ResearchRecord | None:
        self._spend(phase, role)
        turn = self._ask(stage=PHASE_STAGES[phase], subtask_id=CAMPAIGN_SUBTASK,
                         round_number=phase, role=role, prompt=prompt)
        if turn.parsed is None or turn.parsed.research is None:
            self.store.event(self.run_id, "research_seat_empty",
                             {"phase": phase, "role": role, "service": turn.service,
                              "status": turn.step.status if turn.step else "unknown",
                              "error": turn.step.error_kind if turn.step else ""})
            self.log(f"     [fase {phase}] {role} non ha consegnato una risposta "
                     f"utilizzabile: la fase prosegue senza, e il rapporto lo dice.")
            return None
        record = turn.parsed.research.attributed(role=role, phase=phase,
                                                 step_id=turn.step.step_id)
        self._records.append(record)
        self._ingest(record)
        return record

    def _ingest(self, record: ResearchRecord) -> None:
        """Write the structured record into the store, so `orch status` can see it grow."""
        def put(kind: str, ident: str, status: str, payload: dict[str, Any]) -> None:
            self.store.record_finding(
                run_id=self.run_id, subtask_id=CAMPAIGN_SUBTASK,
                round_number=record.phase, kind=kind, ident=ident, status=status,
                payload={**payload, "role": record.role, "phase": record.phase},
                step_id=record.step_id)

        for item in record.searches:
            put("research_search", item.ident, item.status, item.as_record())
        for item in record.sources:
            put("research_source", item.ident, item.consulted, item.as_record())
        for item in record.claims:
            put("research_claim", item.ident, item.nature, item.as_record())
        for item in record.hypotheses:
            put("research_hypothesis", item.ident, item.status, item.as_record())
        for item in record.gaps:
            put("research_gap", item.ident, "open", item.as_record())
        for text in record.operator_requests:
            # Recorded so it is visible, and acted on by nothing. Budget, routing and
            # permissions are read from configuration; a reply cannot reach them.
            put("research_operator_request", "OR-" + record.step_id[:8] + "-"
                + str(abs(hash(text)) % 10_000), "recorded", {"text": text})
            self.log(f"     [richiesta all'operatore da {record.role}] {clip(text, 160)} "
                     f"— registrata, nessun effetto sul budget.")
        if record.dropped_keys:
            self.store.event(self.run_id, "research_keys_dropped",
                             {"role": record.role, "phase": record.phase,
                              "keys": list(record.dropped_keys)})

    # -------------------------------------------------------------------- digests
    def _digest(self, role: str, upto_phase: int) -> str:
        """One worker's results so far, rendered from the structured record.

        Deterministic and bounded: what travels between phases is what the contract read,
        not the raw text of an answer. A field we never parsed cannot influence the next
        phase, which is the same boundary the debugging loop draws around a proposal.
        """
        records = [item for item in self._records
                   if item.role == role and item.phase <= upto_phase]
        if not records:
            return ""
        parts: list[str] = []
        for record in records:
            parts.append(f"--- {record.role}, fase {record.phase} ---")
            if record.summary:
                parts.append(f"In sintesi: {record.summary}")
            parts.append(record.synthesis)
            if record.searches:
                parts.append("Ricerche registrate:")
                for item in record.searches:
                    parts.append(
                        f"  [{item.ident}] «{item.query}» su {item.service or 'non detto'}"
                        + (f", filtri: {item.filters}" if item.filters else "")
                        + f" — stato: {item.status}"
                        + (f" ({item.note})" if item.note else ""))
            if record.sources:
                parts.append("Fonti:")
                for item in record.sources:
                    parts.append(
                        f"  [{item.local_id} = {item.ident}] {item.title or '(senza titolo)'}"
                        + (f", {item.authors}" if item.authors else "")
                        + (f", {item.year}" if item.year else "")
                        + (f" — DOI {item.doi}" if item.doi else "")
                        + (f" — {item.url}" if item.url and not item.doi else "")
                        + f" — livello dichiarato: {item.consulted}"
                        + (f" ({item.access_note})" if item.access_note else ""))
            if record.claims:
                parts.append("Affermazioni:")
                for item in record.claims:
                    parts.append(
                        f"  [{item.ident}] ({item.nature}) {item.text}"
                        + (f" — a sostegno: {', '.join(item.supported_by)}"
                           if item.supported_by else "")
                        + (f" — contrarie: {', '.join(item.contradicted_by)}"
                           if item.contradicted_by else "")
                        + (f" — dove: {item.locator}" if item.locator else "")
                        + (f" — limiti: {item.limits}" if item.limits else ""))
            if record.hypotheses:
                parts.append("Ipotesi:")
                for item in record.hypotheses:
                    parts.append(f"  [{item.ident}] ({item.status}) {item.statement}"
                                 + (f" — alternative: {'; '.join(item.alternatives)}"
                                    if item.alternatives else ""))
            if record.gaps:
                parts.append("Lacune:")
                for item in record.gaps:
                    parts.append(f"  [{item.ident}] {item.missing}"
                                 + (f" — la colmerebbe: {item.search_that_would_close_it}"
                                    if item.search_that_would_close_it else ""))
            if record.open_questions:
                parts.append("Domande aperte:")
                parts.extend(f"  - {item}" for item in record.open_questions)
            if record.saturation_claim:
                parts.append(f"Dichiara saturazione: {record.saturation_claim} "
                             f"(e' una sua affermazione, non una misura)")
        return "\n".join(parts)

    def _peer_blocks(self, reader: str, upto_phase: int) -> list[str]:
        blocks: list[str] = []
        for role in self.workers:
            if role == reader:
                continue
            digest = self._digest(role, upto_phase)
            blocks.append(prompts.peer_block(
                role, "", digest, usable=bool(digest),
                note="nessun record leggibile per quella fase"))
        return blocks

    # --------------------------------------------------------------------- phases
    def _phase1(self) -> None:
        self.log(f"[fase 1] ricerca indipendente — {', '.join(self.workers)}")
        built = {
            role: prompts.phase1_prompt(
                self.research, role=role, service=self.settings.service_of(role),
                capability=self.capability, plan_only=self.plan_only)
            for role in self.workers
        }
        for role in self.workers:
            self._ask_worker(1, role, built[role])

    def _phase2(self) -> None:
        self.log("[fase 2] confronto e piano di approfondimento")
        # Built before anyone is asked, from phase 1 only: whoever is contacted second
        # receives exactly what the first one received.
        built = {
            role: prompts.phase2_prompt(
                self.research, role=role, service=self.settings.service_of(role),
                capability=self.capability, plan_only=self.plan_only,
                own_digest=self._digest(role, 1), peer_blocks=self._peer_blocks(role, 1))
            for role in self.workers
        }
        for role in self.workers:
            self._ask_worker(2, role, built[role])

    def _choose_leads(self) -> Selection:
        # Frozen on the first pass. A resumed campaign reads the file instead of choosing
        # again: the rule would give the same answer, but re-deciding is the wrong
        # posture, and a phase-3 prompt built from a fresh selection could hash
        # differently and ask a question that was already asked.
        frozen = self.store.run_dir(self.run_id) / "leads.json"
        if frozen.exists():
            from ..util import read_json

            selection = Selection.from_record(read_json(frozen))
            self.log(f"  piste gia' scelte in questo run, rilette da {frozen.name}: "
                     + (", ".join(item.ident for item in selection.selected) or "nessuna"))
            return selection
        leads_by_role = {
            role: [lead for record in self._records
                   if record.role == role and record.phase == 2
                   for lead in record.leads]
            for role in self.workers
        }
        selection = select_leads(leads_by_role, cap=self.research.budget.max_leads)
        self.store.event(self.run_id, "research_leads_selected", selection.as_record())
        write_json_new(self.store.run_dir(self.run_id) / "leads.json",
                       {"chosen_utc": utc_now(), **selection.as_record()})
        if selection.selected:
            self.log("  piste scelte dalla regola: "
                     + "; ".join(f"{item.ident} ({', '.join(item.proposed_by)})"
                                 for item in selection.selected))
        else:
            self.log("  nessuna pista completa nelle quattro parti: la fase 3 consolida "
                     "quello che c'e' e dichiara cosa servirebbe.")
        return selection

    def _phase3(self) -> None:
        self.log("[fase 3] ricerca mirata e sintesi")
        self._selection = self._choose_leads()
        assignment = assign(self._selection, self.workers,
                            policy=self.research.lead_assignment)
        open_contradictions = [text for record in self._records
                               if record.phase == 2 for text in record.contradictions]
        built = {
            role: prompts.phase3_prompt(
                self.research, role=role, service=self.settings.service_of(role),
                capability=self.capability, plan_only=self.plan_only,
                leads=assignment.get(role, ()), own_digest=self._digest(role, 2),
                open_contradictions=open_contradictions)
            for role in self.workers
        }
        for role in self.workers:
            self._ask_worker(3, role, built[role])

    # ----------------------------------------------------------------- search gate
    def _resolve_search(self) -> None:
        """Decide, before any contact, whether this campaign can actually search."""
        policy = self.research.search
        missing = sorted(name for name, item in self.capability.items()
                         if not item.can_search)
        self.store.event(self.run_id, "research_search_capability",
                         {"policy": policy.as_record(),
                          "capability": {name: item.as_record()
                                         for name, item in sorted(self.capability.items())}})
        if not policy.required:
            self.plan_only = True
            self.log("[ricerca] la campagna non chiede la ricerca sul web: i worker "
                     "produrranno un piano di query non eseguite.")
            return
        if not missing:
            self.log("[ricerca] interruttore di ricerca dichiarato su tutti i servizi: "
                     + ", ".join(f"{name}={item.mode_name}"
                                 for name, item in sorted(self.capability.items())))
            self.log("  Attenzione: sappiamo che l'interruttore c'e' e verra' verificato, "
                     "non quali query verranno eseguite. Le ricerche resteranno "
                     "dichiarazioni dei worker.")
            return
        detail = "; ".join(self.capability[name].detail for name in missing)
        if policy.on_unavailable == "halt":
            raise SearchUnavailable(
                f"la ricerca sul web e' richiesta ma non e' disponibile su {', '.join(missing)}. "
                f"{detail} Nessun messaggio e' stato inviato. Per far girare la campagna "
                f"senza ricerca, e ottenere un piano esplicitamente non eseguito, metti "
                f"research.search.on_unavailable: plan_only nell'incarico.")
        self.plan_only = True
        able = sorted(name for name, item in self.capability.items() if item.can_search)
        self.log(f"[ricerca] non disponibile su {', '.join(missing)}. "
                 f"on_unavailable: plan_only — la campagna gira. Ogni worker viene "
                 f"informato del PROPRIO canale, non di una media: "
                 + (f"{', '.join(able)} cerca davvero; " if able else "")
                 + f"{', '.join(missing)} restituisce un piano di ricerche NON eseguite. "
                 f"Nessuna conoscenza pregressa verra' presentata come risultato di una "
                 f"ricerca, e il rapporto dice chi ha potuto cercare e chi no.")

    # -------------------------------------------------------------------- closing
    def _close_out(self, outcome_hint: str | None, phases_done: int) -> str:
        ledger = ledger_from_store(self.store, self.run_id)
        parts = build_dossier(self.store, self.run_id, research=self.research,
                              selection_record=self._selection.as_record(),
                              outcome="", outcome_detail="",
                              capability=self.capability, plan_only=self.plan_only)
        outcome, detail = decide_outcome(
            parts, interrupted=outcome_hint, phases_done=phases_done,
            expected_phases=self.research.budget.max_phases, plan_only=self.plan_only,
            seats_planned=ledger.seats_planned, seats_answered=ledger.seats_answered)
        if self._interrupt_detail:
            detail = f"{detail}. {self._interrupt_detail}"
        parts["outcome"], parts["outcome_detail"] = outcome, detail
        # The run's final state is written *before* the report, so the report can print
        # the time the campaign ended instead of a dash. The status is decided here and
        # only confirmed by the caller.
        status = ("finished" if outcome in ("plan_completed", "deepening_needed",
                                            "unresolved_disagreement") else "stopped")
        self.store.set_run_status(self.run_id, status, reason=outcome,
                                  detail=self._interrupt_detail or detail)
        dossier_path = write_dossier(self.store, self.run_id, parts)
        path = build_research_report(self.store, self.run_id, parts)
        self.store.set_subtask_status(self.run_id, CAMPAIGN_SUBTASK, "stopped",
                                      reason=outcome, detail=detail,
                                      rounds_done=phases_done)
        self.store.record_round(run_id=self.run_id, subtask_id=CAMPAIGN_SUBTASK,
                                round_number=max(1, phases_done), decision=outcome,
                                reason=detail, numbers=ledger.as_record(),
                                delta={"phases_done": phases_done})
        self.log(f"[esito] {outcome}: {detail}")
        self.log(f"[rapporto di ricerca] {path}")
        self.log(f"[dossier] {dossier_path}")
        return outcome

    # ------------------------------------------------------------------------ run
    def run(self) -> str:
        row = self.store.run(self.run_id)
        if row is None:
            raise ValueError(f"unknown run {self.run_id}")
        self.store.set_run_status(self.run_id, "running")
        self.log(f"[avvio] campagna di ricerca {self.run_id} — «{self.research.title}» "
                 f"v{row['brief_version']}, percorso «{self.route.name}», "
                 f"worker: {', '.join(self.workers)}")
        self.store.put_subtask(
            self.run_id,
            Subtask(ident=CAMPAIGN_SUBTASK, title=self.research.title,
                    question=self.research.question, origin="brief"),
            position=0, route=self.route.name, status="running")

        phases_done = 0
        outcome_hint: str | None = None
        try:
            self._resolve_search()
            self._phase1()
            phases_done = 1
            self._phase2()
            phases_done = 2
            self._phase3()
            phases_done = 3
        except SearchUnavailable as stop:
            self.store.event(self.run_id, "research_halted_no_search", {"detail": stop.detail})
            self.store.set_run_status(self.run_id, "stopped", reason="search_unavailable",
                                      detail=stop.detail)
            self.log(f"[ricerca non disponibile] {stop.detail}")
            self.close()
            return "stopped"
        except BudgetExhausted as stop:
            outcome_hint, self._interrupt_detail = "limit_reached", stop.detail
            self.log(f"[budget esaurito] {stop.detail}")
        except OperatorStop as stop:
            outcome_hint, self._interrupt_detail = "human_stop", stop.detail
            self.log("[fermata dall'operatore]")
        except ServiceUnavailable as stop:
            outcome_hint, self._interrupt_detail = "service_unavailable", stop.detail
            self.log(f"[servizio non disponibile] {stop.detail}")
        except NeedsReconciliation as stop:
            self.log(f"[da riconciliare] {stop.detail}")
            self.close()
            return "needs_reconciliation"
        except Exception as error:  # noqa: BLE001
            import traceback

            report = traceback.format_exc()
            stamp = utc_now().replace(":", "").replace("-", "")
            path = self.store.run_dir(self.run_id) / f"error-{stamp}.txt"
            try:
                from ..util import write_new as _write
                _write(path, report)
            except OSError:
                path = None
            summary = f"{type(error).__name__}: {str(error)[:400]}"
            self.store.event(self.run_id, "run_failed",
                             {"error": summary, "traceback": str(path)})
            self.store.set_run_status(self.run_id, "failed", reason="unexpected_error",
                                      detail=summary)
            self.log(f"[errore non previsto] {summary}")
            self.close()
            return "failed"
        finally:
            self.close()

        outcome = self._close_out(outcome_hint, phases_done)
        return ("finished" if outcome in ("plan_completed", "deepening_needed",
                                          "unresolved_disagreement") else "stopped")

def research_report(store: Store, settings: Settings, brief: Brief, run_id: str):
    """Regenerate the dossier and the report for a campaign that already ran."""
    research = load_research_brief(brief, settings)
    row = store.run(run_id)
    route = settings.route(row["route"])
    capability = {}
    for role in sorted(route.roles("solve")):
        service = settings.service_of(role)
        capability[service] = search_capability(settings, service,
                                                wanted=research.search.required)
    plan_only = any(not item.can_search for item in capability.values()) or \
        not research.search.required
    leads_path = store.run_dir(run_id) / "leads.json"
    selection_record: dict[str, Any] = {}
    if leads_path.exists():
        from ..util import read_json
        selection_record = read_json(leads_path)
    ledger = ledger_from_store(store, run_id)
    parts = build_dossier(store, run_id, research=research,
                          selection_record=selection_record, outcome="", outcome_detail="",
                          capability=capability, plan_only=plan_only)
    phases_done = len({item["phase"] for item in parts["syntheses"]})
    outcome, detail = decide_outcome(
        parts, interrupted=None, phases_done=phases_done,
        expected_phases=research.budget.max_phases, plan_only=plan_only,
        seats_planned=ledger.seats_planned, seats_answered=ledger.seats_answered)
    parts["outcome"], parts["outcome_detail"] = outcome, detail
    write_dossier(store, run_id, parts)
    return build_research_report(store, run_id, parts)
