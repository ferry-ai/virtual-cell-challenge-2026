"""The common dossier, assembled by code, and the report a person reads.

"Deterministic" here means something specific: given the same replies, this module
produces the same dossier, and it produces it by *collecting* rather than by deciding.
The two syntheses survive side by side and verbatim. Nothing merges them. No third model
is consulted -- that was offered as a future option, with its own budget, and a future
option is not this file.

What the code does decide, it decides mechanically:

* two source records are the same document when they share a DOI or a normalised URL
  (`contract.source_key`), never when their titles look alike;
* a contradiction is recorded when the workers point the same source in opposite
  directions, or when one of them declared a contradiction in phase 2;
* **no contradiction is ever closed by the program.** It is not able to read the paper
  that would settle one, and a contradiction filed away without evidence is worse than a
  contradiction. Closing one is the operator's, with the artefacts in front of them.

The last rule has a sibling that runs through the whole report: a worker's claim that the
literature is exhausted is printed as a claim, attributed, and never turned into a fact
about the literature. "We found no evidence in the searches we recorded" and "there is no
evidence" are different sentences, and only the first one is ours to write.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..protocol import ContentProblem
from ..store import Store
from ..util import clip, utc_now, write_json_new, write_new
from .contract import Claim, ResearchRecord, parse_research_reply

PHASE_STAGES = {1: "research_phase1", 2: "research_phase2", 3: "research_phase3"}
STAGE_PHASES = {stage: phase for phase, stage in PHASE_STAGES.items()}

OUTCOMES = (
    "human_stop", "service_unavailable", "limit_reached", "unresolved_disagreement",
    "deepening_needed", "plan_completed",
)

OUTCOME_WORDS = {
    "plan_completed": "piano completato",
    "deepening_needed": "approfondimenti ancora necessari",
    "unresolved_disagreement": "disaccordo irrisolto",
    "limit_reached": "limite raggiunto",
    "service_unavailable": "servizio non disponibile",
    "human_stop": "arresto richiesto dall'operatore",
}

PROVENANCE_WORDS = {
    "proposed": "proposta, non eseguita",
    "declared_by_worker": "dichiarata dal worker",
    "observed_in_channel": "osservata negli artefatti del canale",
}

CONSULTED_WORDS = {
    "found": "trovata in un elenco di risultati",
    "abstract": "abstract consultato",
    "full_text_or_section": "testo completo o sezione consultata",
    "not_accessible": "non accessibile",
}

NATURE_WORDS = {
    "reported_by_authors": "riferita dagli autori",
    "worker_interpretation": "interpretazione del worker",
    "new_hypothesis": "ipotesi nuova",
}

STATUS_WORDS = {
    "executed": "eseguita", "not_executed": "non eseguita", "failed": "fallita",
    "blocked": "bloccata",
}


# --------------------------------------------------------------------- merged source

@dataclass
class MergedSource:
    """One document, with what each worker separately said about it.

    The per-worker levels are kept rather than collapsed on purpose. If one worker read
    the full text and the other only saw the title in a result list, the useful record is
    both of those facts, attributed. A single "best" level would quietly let the stronger
    claim stand for both.
    """

    ident: str
    key: str
    key_kind: str
    title: str = ""
    authors: str = ""
    year: str = ""
    doi: str = ""
    url: str = ""
    per_worker: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def found_by(self) -> tuple[str, ...]:
        return tuple(sorted(self.per_worker))

    @property
    def best_declared(self) -> str:
        order = ["not_accessible", "found", "abstract", "full_text_or_section"]
        levels = [entry["consulted"] for entry in self.per_worker.values()]
        return max(levels, key=order.index) if levels else "found"

    def as_record(self) -> dict[str, Any]:
        return {"id": self.ident, "key": self.key, "key_kind": self.key_kind,
                "title": self.title, "authors": self.authors, "year": self.year,
                "doi": self.doi, "url": self.url, "found_by": list(self.found_by),
                "per_worker": self.per_worker,
                "best_declared_consulted": self.best_declared}


def merge_sources(records: Iterable[ResearchRecord]) -> list[MergedSource]:
    """Collapse source records onto documents. Identifier-based, order-independent."""
    merged: dict[str, MergedSource] = {}
    for record in records:
        for source in record.sources:
            entry = merged.get(source.key)
            if entry is None:
                entry = MergedSource(ident=source.ident, key=source.key,
                                     key_kind=source.key_kind, title=source.title,
                                     authors=source.authors, year=source.year,
                                     doi=source.doi, url=source.url)
                merged[source.key] = entry
            # Fill blanks from whoever supplied them; never overwrite, so the first
            # worker's metadata is not silently replaced by the second's.
            for attribute in ("title", "authors", "year", "doi", "url"):
                if not getattr(entry, attribute) and getattr(source, attribute):
                    setattr(entry, attribute, getattr(source, attribute))
            entry.per_worker.setdefault(source.role, {})
            previous = entry.per_worker[source.role]
            order = ["not_accessible", "found", "abstract", "full_text_or_section"]
            if (not previous
                    or order.index(source.consulted) > order.index(previous["consulted"])):
                entry.per_worker[source.role] = {
                    "consulted": source.consulted, "access_note": source.access_note,
                    "found_via": source.found_via, "phase": source.phase,
                    "step_id": source.step_id, "local_id": source.local_id}
    return [merged[key] for key in sorted(merged)]


# ------------------------------------------------------------------- contradictions

@dataclass(frozen=True)
class Contradiction:
    kind: str                    # declared | derived
    text: str
    raised_by: tuple[str, ...]
    phase: int
    source_id: str = ""
    hypothesis: str = ""
    step_ids: tuple[str, ...] = ()

    @property
    def ident(self) -> str:
        from ..util import short_id, normalise
        return "X-" + short_id(self.kind, normalise(self.text), self.source_id, length=10)

    def as_record(self) -> dict[str, Any]:
        return {"id": self.ident, "kind": self.kind, "text": self.text,
                "raised_by": list(self.raised_by), "phase": self.phase,
                "source_id": self.source_id, "hypothesis": self.hypothesis,
                "step_ids": list(self.step_ids), "status": "open"}


def find_contradictions(records: Sequence[ResearchRecord]) -> list[Contradiction]:
    """Contradictions the record shows, of two kinds, both left open.

    `declared` is what a worker wrote in phase 2. `derived` is structural: two workers
    pointing the same source in opposite directions. Neither is a judgement about which
    side is right -- that would need reading the source, which this program cannot do.
    """
    found: list[Contradiction] = []
    for record in records:
        for text in record.contradictions:
            found.append(Contradiction(kind="declared", text=text,
                                       raised_by=(record.role,), phase=record.phase,
                                       step_ids=(record.step_id,)))

    supports: dict[str, list[Claim]] = {}
    against: dict[str, list[Claim]] = {}
    for record in records:
        for claim in record.claims:
            for ident in claim.supported_by:
                supports.setdefault(ident, []).append(claim)
            for ident in claim.contradicted_by:
                against.setdefault(ident, []).append(claim)
    # One record per (source, pair of workers), not one per pair of claims. Two people
    # disagreeing about one paper across several sentences are having one disagreement;
    # emitting five of them would inflate the count that decides the campaign's outcome,
    # and bury the two real ones.
    for ident in sorted(set(supports) & set(against)):
        pairs: dict[tuple[str, str], list[Claim]] = {}
        for positive in supports[ident]:
            for negative in against[ident]:
                if positive.role == negative.role:
                    continue            # one worker reading a source both ways is not a
                                        # disagreement between workers; it is nuance.
                pairs.setdefault((positive.role, negative.role), []).extend(
                    [positive, negative])
        for (pro_role, con_role), claims in sorted(pairs.items()):
            pro = [claim for claim in claims if claim.role == pro_role]
            con = [claim for claim in claims if claim.role == con_role]
            found.append(Contradiction(
                kind="derived",
                text=(f"{pro_role} usa {ident} a sostegno di "
                      + "; ".join(f"[{claim.ident}] «{clip(claim.text, 160)}»"
                                  for claim in pro)
                      + f" — {con_role} usa la stessa fonte contro "
                      + "; ".join(f"[{claim.ident}] «{clip(claim.text, 160)}»"
                                  for claim in con)),
                raised_by=(pro_role, con_role),
                phase=max(claim.phase for claim in claims), source_id=ident,
                hypothesis=next((claim.about_hypothesis for claim in claims
                                 if claim.about_hypothesis), ""),
                step_ids=tuple(sorted({claim.step_id for claim in claims}))))
    unique: dict[str, Contradiction] = {}
    for item in found:
        unique.setdefault(item.ident, item)
    return [unique[key] for key in sorted(unique)]


# ------------------------------------------------------------------------- ledger

@dataclass
class Ledger:
    """What the campaign actually cost, counting repairs and retries.

    Six main responses that took fourteen interactions is not six interactions, and the
    quota was spent either way. Both numbers are reported; only the first is capped.
    """

    seats_planned: int = 0
    seats_answered: int = 0
    main_responses: int = 0
    repairs: int = 0
    retries: int = 0
    unparsed: int = 0
    abandoned: int = 0
    transport_errors: int = 0
    elapsed_minutes: float = 0.0

    @property
    def total_interactions(self) -> int:
        return self.main_responses + self.repairs + self.retries

    def as_record(self) -> dict[str, Any]:
        return {**self.__dict__, "total_interactions": self.total_interactions}


def ledger_from_store(store: Store, run_id: str) -> Ledger:
    """Count what happened from the recorded steps, not from an in-memory counter.

    Reading it back from the store is what makes the number survive a resume: a campaign
    interrupted and continued has to charge itself for the sends it already made.
    """
    ledger = Ledger()
    slots: dict[tuple[str, int, str], list] = {}
    for step in store.steps(run_id):
        if step.stage not in STAGE_PHASES:
            continue
        slots.setdefault((step.stage, step.round, step.role), []).append(step)
    for steps in slots.values():
        ledger.main_responses += 1
        ordered = sorted(steps, key=lambda item: item.planned_utc)
        ledger.retries += max(0, len([s for s in ordered if s.attempt == 1]) - 1)
        ledger.repairs += max(0, len(ordered) - 1 - ledger_extra_retries(ordered))
        if any(step.status == "answered" for step in ordered):
            ledger.seats_answered += 1
        ledger.unparsed += sum(1 for step in ordered if step.status == "unparsed")
        ledger.abandoned += sum(1 for step in ordered if step.status == "abandoned")
        ledger.transport_errors += sum(1 for step in ordered
                                       if step.status == "transport_error")
    ledger.seats_planned = len(slots)
    return ledger


def ledger_extra_retries(steps: Sequence[Any]) -> int:
    """Steps in a slot that are transport retries rather than format repairs."""
    return max(0, len([step for step in steps if step.attempt == 1]) - 1)


# ------------------------------------------------------------- reading back the run

def records_from_store(store: Store, run_id: str) -> list[ResearchRecord]:
    """Rebuild the structured records from the replies on disk.

    Re-parsed from `response.raw.txt` rather than read out of a serialised form, so the
    dossier and a regenerated report always agree with the verbatim text a person can
    open, and a change in how we read a reply cannot leave stale structure behind.
    """
    records: list[ResearchRecord] = []
    for step in store.steps(run_id):
        phase = STAGE_PHASES.get(step.stage)
        if phase is None or step.status != "answered":
            continue
        raw = store.reply_text(step) or ""
        try:
            record = parse_research_reply(raw)
        except ContentProblem:
            continue
        records.append(record.attributed(role=step.role, phase=phase,
                                         step_id=step.step_id))
    records.sort(key=lambda item: (item.phase, item.role))
    return records


# -------------------------------------------------------------------------- dossier

def build_dossier(store: Store, run_id: str, *, research, selection_record: dict | None,
                  outcome: str, outcome_detail: str, capability: dict,
                  plan_only: bool) -> dict[str, Any]:
    """Assemble the dossier. Pure collection: nothing here decides what is true."""
    records = records_from_store(store, run_id)
    sources = merge_sources(records)
    contradictions = find_contradictions(records)
    ledger = ledger_from_store(store, run_id)

    hypotheses: dict[str, dict[str, Any]] = {}
    for seed in research.hypotheses:
        hypotheses[seed.ident] = {"id": seed.ident, "statement": seed.statement,
                                  "origin": "operatore", "declared": []}
    for record in records:
        for item in record.hypotheses:
            entry = hypotheses.setdefault(
                item.ident, {"id": item.ident, "statement": item.statement,
                             "origin": f"{record.role} fase {record.phase}", "declared": []})
            if not entry["statement"]:
                entry["statement"] = item.statement
            entry["declared"].append({
                "role": record.role, "phase": record.phase, "status": item.status,
                "statement": item.statement, "alternatives": list(item.alternatives),
                "proposed_tests": list(item.proposed_tests), "step_id": record.step_id})

    return {
        "run_id": run_id,
        "built_utc": utc_now(),
        "note": ("Dossier assemblato da codice deterministico. Le sintesi dei due worker "
                 "sono conservate separate e verbatim: nessuna sintesi consensuale e' "
                 "stata prodotta, e nessun terzo modello e' stato interrogato. Nessuna "
                 "contraddizione viene chiusa dal programma."),
        "brief": research.as_record(),
        "outcome": outcome,
        "outcome_detail": outcome_detail,
        "search": {"plan_only": plan_only,
                   "capability": {name: item.as_record()
                                  for name, item in sorted(capability.items())},
                   "channel_evidence": (
                       "Il canale puo' mostrare che l'interruttore di ricerca era acceso, "
                       "non quali query siano state eseguite. Nessuna ricerca di questa "
                       "campagna e' quindi 'osservata negli artefatti del canale': tutte "
                       "quelle eseguite restano dichiarazioni dei worker.")},
        "leads": selection_record or {},
        "ledger": ledger.as_record(),
        "searches": [item.as_record() for record in records for item in record.searches],
        "sources": [item.as_record() for item in sources],
        "claims": [item.as_record() for record in records for item in record.claims],
        "hypotheses": [hypotheses[key] for key in sorted(hypotheses)],
        "gaps": [item.as_record() for record in records for item in record.gaps],
        "contradictions": [item.as_record() for item in contradictions],
        "agreements": [{"role": record.role, "phase": record.phase, "text": text}
                       for record in records for text in record.agreements],
        "complementary": [{"role": record.role, "phase": record.phase, "text": text}
                          for record in records for text in record.complementary],
        "unsupported_assumptions": [
            {"role": record.role, "phase": record.phase, "text": text}
            for record in records for text in record.unsupported_assumptions],
        "open_questions": [{"role": record.role, "phase": record.phase, "text": text}
                           for record in records for text in record.open_questions],
        "saturation_claims": [
            {"role": record.role, "phase": record.phase, "text": record.saturation_claim}
            for record in records if record.saturation_claim.strip()],
        "operator_requests": [
            {"role": record.role, "phase": record.phase, "text": text}
            for record in records for text in record.operator_requests],
        "dropped_keys": [{"role": record.role, "phase": record.phase,
                          "keys": list(record.dropped_keys)}
                         for record in records if record.dropped_keys],
        "reader_issues": [{"role": record.role, "phase": record.phase, "issue": issue}
                          for record in records for issue in record.issues],
        "syntheses": [{"role": record.role, "phase": record.phase,
                       "summary": record.summary, "synthesis": record.synthesis,
                       "step_id": record.step_id} for record in records],
    }


def decide_outcome(dossier_parts: dict[str, Any], *, interrupted: str | None,
                   phases_done: int, expected_phases: int, plan_only: bool,
                   seats_planned: int, seats_answered: int) -> tuple[str, str]:
    """Which of the six endings this campaign had, and why. Fixed order of precedence.

    human_stop > service_unavailable > limit_reached > unresolved_disagreement >
    deepening_needed > plan_completed. The order is not arbitrary: the ones above are
    facts about the run being cut short, and they have to be said before anything is said
    about what the run found.
    """
    if interrupted in ("human_stop", "service_unavailable", "limit_reached"):
        return interrupted, {
            "human_stop": "l'operatore ha fermato la campagna",
            "service_unavailable": "un servizio non ha risposto e non e' stato sostituito",
            "limit_reached": "budget esaurito: risposte principali, interazioni o tempo",
        }[interrupted]
    if phases_done < expected_phases:
        return "limit_reached", (f"eseguite {phases_done} fasi su {expected_phases}")
    if dossier_parts.get("contradictions"):
        return "unresolved_disagreement", (
            f"{len(dossier_parts['contradictions'])} contraddizioni restano aperte; il "
            f"programma non ne chiude nessuna da solo")
    reasons: list[str] = []
    if plan_only:
        reasons.append("la ricerca sul web non era disponibile su almeno un canale: per "
                       "quel worker le query sono un piano non eseguito")
    unexecuted = [item for item in dossier_parts.get("searches", [])
                  if item["status"] != "executed"]
    if unexecuted:
        reasons.append(f"{len(unexecuted)} ricerche proposte non sono state eseguite")
    if dossier_parts.get("gaps"):
        reasons.append(f"{len(dossier_parts['gaps'])} lacune dichiarate restano aperte")
    rejected = (dossier_parts.get("leads") or {}).get("rejected") or []
    over_cap = [item for item in rejected if "oltre il tetto" in item.get("reason", "")]
    if over_cap:
        reasons.append(f"{len(over_cap)} piste sono rimaste fuori dal tetto")
    if seats_answered < seats_planned:
        reasons.append(f"{seats_planned - seats_answered} risposte principali non sono "
                       f"arrivate")
    if reasons:
        return "deepening_needed", "; ".join(reasons)
    return "plan_completed", ("le tre fasi sono state eseguite, le ricerche delle piste "
                              "sono state dichiarate eseguite e non restano lacune")


# --------------------------------------------------------------------------- report

def _table(header: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_(nessuna)_\n"
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join("---" for _ in header) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ")
                                       for cell in row) + " |")
    return "\n".join(lines) + "\n"


def _step_dir(store: Store, run_id: str, step_id: str) -> str:
    step = store.step(step_id)
    return f"`steps/{Path(step.directory).name}/`" if step else "—"


def build_research_report(store: Store, run_id: str, dossier: dict[str, Any]) -> Path:
    """The eight sections the operator asked for, each pointing back at the artefacts."""
    directory = store.run_dir(run_id)
    run = store.run(run_id)
    brief = dossier["brief"]
    out: list[str] = []

    out.append(f"# Rapporto di ricerca — {brief['title']}\n")
    out.append(
        f"- **Run:** `{run_id}`\n"
        f"- **Incarico:** `{brief['id']}` versione {brief['version']} "
        f"(sha256 `{brief['sha256'][:16]}`)\n"
        f"- **Modalita':** `scientific_research`, {brief['budget']['max_phases']} fasi\n"
        f"- **Esito:** **{OUTCOME_WORDS.get(dossier['outcome'], dossier['outcome'])}** — "
        f"{dossier['outcome_detail']}\n"
        f"- **Avvio:** {run['started_utc'] or '—'} · **Fine:** {run['ended_utc'] or '—'}\n"
        f"- **Dossier completo:** `dossier.json` · **risposte verbatim:** `steps/`\n"
        f"- **Rapporto generato:** {utc_now()}\n")
    out.append(
        "\n> Questo rapporto raccoglie, non concilia. Le due sintesi restano separate e "
        "verbatim in appendice; nessuna sintesi consensuale e' stata prodotta e nessun "
        "terzo modello e' stato interrogato. Dove una ricerca risulta «dichiarata dal "
        "worker» vuol dire che il worker dice di averla eseguita e che noi non l'abbiamo "
        "vista eseguire: il canale non espone le query.\n")

    # ------------------------------------------------------------- 1. domanda
    out.append("\n## 1. Domanda e perimetro\n")
    out.append(f"\n**Domanda:** {brief['question']}\n")
    out.append(f"\n**Perimetro:** {brief['scope']}\n")
    if brief.get("out_of_scope"):
        out.append(f"\n**Fuori perimetro:** {brief['out_of_scope']}\n")
    out.append("\n**Criteri di pertinenza** dichiarati prima di contattare i worker:\n\n")
    out.append(_table(["id", "criterio"],
                      [[item["id"], item["text"]] for item in brief["relevance_criteria"]]))
    if brief.get("perspectives"):
        out.append("\n**Prospettive assegnate:**\n\n")
        out.append(_table(["worker", "prospettiva"],
                          [[role, text] for role, text in sorted(brief["perspectives"].items())]))

    # -------------------------------------------------- 2. cosa è stato cercato
    out.append("\n## 2. Cosa e' stato cercato, e dove\n")
    search = dossier["search"]
    out.append(f"\n{search['channel_evidence']}\n")
    out.append("\n**Capacita' di ricerca dei canali**, come risulta dalla configurazione "
               "e non da un'assunzione:\n\n")
    out.append(_table(["servizio", "stato", "modalita'", "dettaglio"],
                      [[item["service"], item["state"], item["mode"] or "—", item["detail"]]
                       for item in search["capability"].values()]))
    executed = [item for item in dossier["searches"] if item["status"] == "executed"]
    out.append(f"\n**Ricerche registrate: {len(dossier['searches'])} in tutto, "
               f"{len(executed)} dichiarate eseguite.**\n\n")
    out.append(_table(
        ["fase", "worker", "query", "dove", "filtri", "stato", "provenienza", "passo"],
        [[item["phase"], item["role"], clip(item["query"], 160), item["service"] or "—",
          item["filters"] or "—", STATUS_WORDS.get(item["status"], item["status"]),
          PROVENANCE_WORDS.get(item["provenance"], item["provenance"]),
          _step_dir(store, run_id, item["step_id"])]
         for item in dossier["searches"]]))
    out.append(f"\n**Fonti distinte: {len(dossier['sources'])}.** Deduplicate su DOI o URL "
               f"normalizzato; due titoli simili senza identificatore comune restano due "
               f"fonti. Il livello di consultazione e' quello **dichiarato** da ciascun "
               f"worker.\n\n")
    rows = []
    for item in dossier["sources"]:
        levels = "; ".join(
            f"{role}: {CONSULTED_WORDS.get(entry['consulted'], entry['consulted'])}"
            for role, entry in sorted(item["per_worker"].items()))
        rows.append([item["id"], clip(item["title"], 150) or "—", item["year"] or "—",
                     item["doi"] or item["url"] or "—", item["key_kind"],
                     ", ".join(item["found_by"]), levels])
    out.append(_table(["id", "titolo", "anno", "DOI/URL", "chiave", "trovata da",
                       "livello dichiarato"], rows))
    both = [item for item in dossier["sources"] if len(item["found_by"]) > 1]
    if both:
        out.append(
            ("\nUna fonte e' stata trovata da entrambi i worker e conta una volta sola: "
             if len(both) == 1 else
             f"\n{len(both)} fonti sono state trovate da entrambi i worker e contano una "
             f"volta sola: ")
            + ", ".join(item["id"] for item in both) + ".\n")

    # ----------------------------------------------------------- 3. evidenze
    out.append("\n## 3. Evidenze principali e contrarie\n")
    out.append("\nLa colonna «natura» e' quella dichiarata da chi ha risposto. «Riferita "
               "dagli autori» vuol dire che il worker la attribuisce agli autori di una "
               "fonte: non l'abbiamo verificata leggendo il documento, e il parser non e' "
               "in grado di farlo.\n\n")
    rows = []
    for item in dossier["claims"]:
        rows.append([item["id"], item["role"], f"f{item['phase']}",
                     NATURE_WORDS.get(item["nature"], item["nature"]),
                     clip(item["text"], 260),
                     ", ".join(item["supported_by"]) or "—",
                     ", ".join(item["contradicted_by"]) or "—",
                     clip(item["locator"], 80) or "—",
                     clip(item["limits"], 120) or "—"])
    out.append(_table(["id", "worker", "fase", "natura", "affermazione", "a sostegno",
                       "contrarie", "localizzatore", "limiti"], rows))

    flagged = [item for item in dossier["claims"] if item["flags"]]
    out.append("\n### Attribuzioni da guardare\n")
    if not flagged:
        out.append("\n_(nessuna: nessuna affermazione attribuita agli autori presenta le "
                   "forme strutturali sospette che il programma sa riconoscere)_\n")
    else:
        out.append(
            "\nQueste affermazioni sono dichiarate come risultati riferiti dagli autori e "
            "hanno una forma che spesso accompagna un'attribuzione sbagliata. **Non e' un "
            "verdetto**: il programma non ha letto le fonti e non sa dire se "
            "un'affermazione sia falsa. E' un elenco di punti dove guardare.\n\n")
        out.append(_table(["id", "worker", "affermazione", "perche' segnalata", "passo"],
                          [[item["id"], item["role"], clip(item["text"], 200),
                            "; ".join(item["flags"]),
                            _step_dir(store, run_id, item["step_id"])]
                           for item in flagged]))

    for label, key in (("Accordi dichiarati", "agreements"),
                       ("Contributi complementari", "complementary"),
                       ("Assunzioni senza sostegno segnalate", "unsupported_assumptions")):
        out.append(f"\n### {label}\n\n")
        out.append(_table(["worker", "fase", "testo"],
                          [[item["role"], item["phase"], clip(item["text"], 400)]
                           for item in dossier[key]]))

    # ----------------------------------------------------------- 4. ipotesi
    out.append("\n## 4. Ipotesi, e come sono cambiate\n")
    out.append("\nGli stati sono **dichiarazioni dei worker**, non verifiche. Nessuno stato "
               "in questa tabella e' stato prodotto da un controllo del programma.\n\n")
    rows = []
    for item in dossier["hypotheses"]:
        history = "; ".join(f"{entry['role']} f{entry['phase']}: {entry['status']}"
                            for entry in item["declared"]) or "mai ripresa"
        rows.append([item["id"], clip(item["statement"], 240), item["origin"], history])
    out.append(_table(["id", "enunciato", "origine", "stati dichiarati"], rows))
    # One row per (hypothesis, worker, alternative). A worker restating the same
    # alternative in every phase is one alternative, not four; who proposed it stays,
    # because two workers arriving at the same alternative separately is worth seeing.
    from ..util import normalise as _normalise

    alternatives: list[tuple[str, str, str]] = []
    seen_alternatives: set[tuple[str, str, str]] = set()
    for item in dossier["hypotheses"]:
        for entry in item["declared"]:
            for alternative in entry["alternatives"]:
                key = (item["id"], entry["role"], _normalise(alternative))
                if key in seen_alternatives:
                    continue
                seen_alternatives.add(key)
                alternatives.append((item["id"], entry["role"], alternative))
    out.append("\n**Spiegazioni alternative messe sul tavolo:**\n\n")
    out.append(_table(["ipotesi", "worker", "alternativa"],
                      [[a, b, clip(c, 300)] for a, b, c in alternatives]))

    # ------------------------------------------- 5. contraddizioni e lacune
    out.append("\n## 5. Contraddizioni e lacune\n")
    out.append("\n**Il programma non chiude nessuna contraddizione.** Non e' in grado di "
               "leggere la fonte che ne deciderebbe una, e una contraddizione archiviata "
               "senza evidenza e' peggio di una contraddizione aperta. Restano tutte qui, "
               "con i passi da cui vengono.\n\n")
    out.append(_table(["id", "tipo", "sollevata da", "fase", "fonte", "testo", "passi"],
                      [[item["id"],
                        "dichiarata" if item["kind"] == "declared" else "derivata dalla "
                        "struttura (stessa fonte, direzioni opposte)",
                        ", ".join(item["raised_by"]), item["phase"],
                        item["source_id"] or "—", clip(item["text"], 300),
                        ", ".join(_step_dir(store, run_id, s) for s in item["step_ids"])]
                       for item in dossier["contradictions"]]))
    out.append("\n**Lacune dichiarate:**\n\n")
    out.append(_table(["id", "worker", "fase", "cosa manca", "ricerca che la colmerebbe"],
                      [[item["id"], item["role"], item["phase"], clip(item["missing"], 300),
                        clip(item["search_that_would_close_it"], 260) or "—"]
                       for item in dossier["gaps"]]))
    if dossier["saturation_claims"]:
        out.append("\n**Dichiarazioni di saturazione.** Un worker sostiene di aver esaurito "
                   "la letteratura utile. E' una sua affermazione motivata: il programma "
                   "puo' contare i duplicati e l'assenza di riferimenti nuovi, non "
                   "dedurne che la letteratura sia esaurita. «Non abbiamo trovato evidenze "
                   "nelle ricerche registrate» non diventa «non esistono evidenze».\n\n")
        out.append(_table(["worker", "fase", "dichiarazione"],
                          [[item["role"], item["phase"], clip(item["text"], 500)]
                           for item in dossier["saturation_claims"]]))

    # ------------------------------------------- 6. ricerche non eseguite
    out.append("\n## 6. Ricerche proposte e non eseguite\n")
    pending = [item for item in dossier["searches"] if item["status"] != "executed"]
    if dossier["search"]["plan_only"]:
        unable = sorted(item["service"] for item in dossier["search"]["capability"].values()
                        if item["state"] != "available")
        able = sorted(item["service"] for item in dossier["search"]["capability"].values()
                      if item["state"] == "available")
        out.append(
            "\n> Questa campagna e' girata **senza ricerca sul web su almeno un canale**: "
            f"{', '.join(unable)} non ha un controllo di ricerca osservato, e la "
            f"configurazione chiedeva di restituire un piano invece di fermarsi. "
            + (f"Su {', '.join(able)} la ricerca era invece disponibile. Le due meta' "
               f"della campagna non sono confrontabili alla pari, e questo va tenuto "
               f"presente leggendo gli accordi della sezione 3.\n" if able else
               "Tutto quello che segue e' un piano non eseguito.\n"))
    out.append("\nQueste sono le query che restano da fare. Sono il punto di partenza piu' "
               "economico di una campagna successiva.\n\n")
    out.append(_table(["fase", "worker", "query", "dove", "filtri", "stato", "nota"],
                      [[item["phase"], item["role"], clip(item["query"], 200),
                        item["service"] or "—", item["filters"] or "—",
                        STATUS_WORDS.get(item["status"], item["status"]),
                        clip(item["note"], 200) or "—"] for item in pending]))

    # ------------------------------------- 7. prossimo approfondimento
    out.append("\n## 7. Prossimo approfondimento suggerito\n")
    selection = dossier.get("leads") or {}
    if selection:
        out.append(f"\n**Regola di selezione delle piste**, applicata dal programma: "
                   f"{selection.get('rule', '—')}\n")
        out.append(f"\nPiste considerate: {selection.get('considered', 0)}; "
                   f"selezionate: {len(selection.get('selected', []))} "
                   f"(tetto {selection.get('cap', '—')}).\n\n")
        rows = []
        for item in selection.get("selected", []):
            rows.append([item["id"], ", ".join(item["proposed_by"]),
                         clip(item["hypothesis"], 240),
                         clip(item["alternative_explanation"], 240),
                         clip(item["distinguishing_search"], 240),
                         clip(item.get("strategy_change", ""), 200) or "—"])
        out.append(_table(["id", "proposta da", "ipotesi", "spiegazione alternativa",
                           "ricerca che le distingue", "cambio di strategia"], rows))
        if selection.get("merged"):
            out.append("\nEntrambi i worker avevano proposto la stessa pista: "
                       + "; ".join(f"{item['kept']} anche da {item['also_proposed_by']}"
                                   for item in selection["merged"])
                       + ". Non c'e' ripescaggio di una seconda pista: che i due siano "
                         "arrivati alla stessa e' un'informazione, non un posto vuoto.\n")
        if selection.get("rejected"):
            out.append("\n**Piste scartate, con il motivo:**\n\n")
            out.append(_table(["id", "worker", "ipotesi", "motivo"],
                              [[item["id"], item.get("role", "—"),
                                clip(item.get("hypothesis", ""), 200), item["reason"]]
                               for item in selection["rejected"]]))
    proposals = [item for item in dossier["open_questions"] if item["phase"] == 3]
    out.append("\n**Domande aperte alla fine della fase 3:**\n\n")
    out.append(_table(["worker", "domanda"],
                      [[item["role"], clip(item["text"], 400)] for item in proposals]))
    out.append("\nLe ricerche della sezione 6 e le lacune della sezione 5 sono, insieme a "
               "queste domande, il materiale di una campagna successiva. Il sistema non ne "
               "avvia nessuna: non esiste un percorso di codice che crei un nuovo incarico.\n")

    # ------------------------------------- 8. arresto e consumo
    out.append("\n## 8. Perche' si e' fermata, e quanto e' costata\n")
    ledger = dossier["ledger"]
    out.append(f"\n**Esito:** {OUTCOME_WORDS.get(dossier['outcome'], dossier['outcome'])} — "
               f"{dossier['outcome_detail']}\n")
    out.append(f"\n**Consumo di interazioni.** Il conteggio include riparazioni di formato "
               f"e tentativi di canale, non solo le risposte principali.\n\n")
    out.append(_table(
        ["voce", "valore"],
        [["posti previsti (fasi x worker)", ledger["seats_planned"]],
         ["posti con una risposta utilizzabile", ledger["seats_answered"]],
         ["risposte principali", ledger["main_responses"]],
         ["riparazioni di formato", ledger["repairs"]],
         ["tentativi di canale ripetuti", ledger["retries"]],
         ["risposte non leggibili", ledger["unparsed"]],
         ["passi abbandonati", ledger["abandoned"]],
         ["errori di canale", ledger["transport_errors"]],
         ["**interazioni totali**", f"**{ledger['total_interactions']}**"],
         ["tetto di risposte principali", brief["budget"]["max_main_responses"]],
         ["tetto di interazioni totali", brief["budget"]["max_total_interactions"]],
         ["tetto di tempo (minuti)", brief["budget"]["max_wall_clock_minutes"]]]))

    if dossier["operator_requests"]:
        out.append("\n**Richieste dei worker all'operatore.** Sono state registrate e non "
                   "hanno cambiato nulla: budget, instradamento e permessi si leggono solo "
                   "dalla configurazione.\n\n")
        out.append(_table(["worker", "fase", "richiesta"],
                          [[item["role"], item["phase"], clip(item["text"], 400)]
                           for item in dossier["operator_requests"]]))
    if dossier["dropped_keys"]:
        out.append("\n**Campi scartati nelle risposte** (non previsti dal contratto, quindi "
                   "senza effetto):\n\n")
        out.append(_table(["worker", "fase", "campi"],
                          [[item["role"], item["phase"], ", ".join(item["keys"])]
                           for item in dossier["dropped_keys"]]))
    if dossier["reader_issues"]:
        out.append("\n**Segnalazioni del lettore di risposte:**\n\n")
        out.append(_table(["worker", "fase", "segnalazione"],
                          [[item["role"], item["phase"], clip(item["issue"], 400)]
                           for item in dossier["reader_issues"]]))

    # ----------------------------------------------------------- appendice
    out.append("\n## Appendice A — le sintesi, verbatim\n")
    out.append("\nConservate separate. Il dossier non le fonde, e nessun modello e' stato "
               "chiamato a farlo: sarebbe una campagna a parte, con un budget suo.\n")
    for item in dossier["syntheses"]:
        out.append(f"\n### {item['role']} — fase {item['phase']} — "
                   f"{_step_dir(store, run_id, item['step_id'])}\n")
        if item["summary"]:
            out.append(f"\n*{item['summary']}*\n")
        out.append("\n" + clip(item["synthesis"], 12000) + "\n")

    out.append("\n## Appendice B — tracciabilita'\n")
    rows = []
    for step in store.steps(run_id):
        if step.stage not in STAGE_PHASES:
            continue
        rows.append([STAGE_PHASES[step.stage], step.role, step.service, step.status,
                     f"{(step.duration_ms or 0) / 1000:.1f}s", step.error_kind or "—",
                     f"`{Path(step.directory).name}`"])
    out.append(_table(["fase", "worker", "servizio", "stato", "durata", "errore",
                       "cartella"], rows))
    out.append(f"\nTutti i percorsi sono relativi a `{directory}`. Il dossier completo, con "
               f"ogni campo letto da ogni risposta, e' in `dossier.json`.\n")

    stamp = utc_now().replace(":", "").replace("-", "")
    path = directory / f"ricerca-{stamp}.md"
    serial = 2
    while path.exists():
        path = directory / f"ricerca-{stamp}-{serial}.md"
        serial += 1
    write_new(path, "".join(out))
    store.event(run_id, "research_report_written", {"path": str(path)})
    return path


def write_dossier(store: Store, run_id: str, dossier: dict[str, Any]) -> Path:
    directory = store.run_dir(run_id)
    path = directory / "dossier.json"
    serial = 2
    while path.exists():
        path = directory / f"dossier-{serial}.json"
        serial += 1
    write_json_new(path, dossier)
    store.event(run_id, "dossier_written", {"path": str(path)})
    return path
