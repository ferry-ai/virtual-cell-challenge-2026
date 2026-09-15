"""The research half of a brief: scope, relevance, hypotheses, budget, search policy.

A debugging brief asks a question and says when an answer is accepted. A research brief
has to say four more things before anyone is contacted, and all four are the operator's
to decide, never a model's:

* **the perimeter** -- what is in scope and what is deliberately out;
* **what counts as relevant**, so "I found something" can be argued with;
* **the budget**, in responses and in minutes, counted including repairs and retries;
* **what happens when the workers cannot actually search**, which is a real state of the
  world and not an edge case: one of the two services here has no search control we have
  ever observed.

Everything in this module is read from the brief file and from the orchestrator
configuration. Nothing here can be moved by a reply -- `operator_requests` in the reply
contract exists so a worker can *ask*, and asking is all it does.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..briefs import Brief, BriefError
from ..settings import Settings
from ..util import short_id

ON_SEARCH_UNAVAILABLE = ("halt", "plan_only")
LEAD_ASSIGNMENT = ("both", "cross", "own")


@dataclass(frozen=True)
class Budget:
    """Hard bounds for one campaign. Read from configuration, enforced by the engine.

    `max_main_responses` counts the seats in the plan: one per worker per phase. Repairs
    and transport retries do **not** get their own seat -- they would let a campaign that
    keeps failing to answer consume the whole budget on one phase -- but they are counted
    separately and reported, because "six responses" that cost fourteen interactions is
    not six interactions, and the operator is paying in quota either way.
    """

    max_phases: int = 3
    max_main_responses: int = 6
    max_repairs_per_response: int = 1
    max_leads: int = 2
    max_wall_clock_minutes: int = 90
    max_total_interactions: int = 12

    @classmethod
    def from_config(cls, *mappings: dict[str, Any] | None) -> "Budget":
        values: dict[str, Any] = {}
        for mapping in mappings:
            for key, value in (mapping or {}).items():
                if key in cls.__dataclass_fields__:
                    values[key] = int(value)
        budget = cls(**values)
        if budget.max_phases != 3:
            raise BriefError(
                f"budget.max_phases e' {budget.max_phases}: questa versione ha tre fasi "
                f"fisse (ricerca indipendente, confronto, approfondimento). Cambiarne il "
                f"numero cambia i prompt, non solo un contatore.")
        if budget.max_repairs_per_response > 1:
            raise BriefError(
                "budget.max_repairs_per_response non puo' superare 1: una sola riparazione "
                "di formato per risposta, come nel ciclo di debug.")
        return budget

    def as_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class SearchPolicy:
    """Whether the workers must really search, and what to do when they cannot.

    `required` is the honest default. The alternative a research loop slides into on its
    own is a model answering from memory in the shape of a literature review, which is
    the single most expensive failure this mode could have: it produces references that
    parse, sound right, and were never looked up.
    """

    required: bool = True
    on_unavailable: str = "halt"
    note: str = ""

    @classmethod
    def from_config(cls, mapping: dict[str, Any] | None) -> "SearchPolicy":
        mapping = mapping or {}
        policy = str(mapping.get("on_unavailable", "halt"))
        if policy not in ON_SEARCH_UNAVAILABLE:
            raise BriefError(
                f"research.search.on_unavailable e' {policy!r}; ammessi: "
                f"{ON_SEARCH_UNAVAILABLE}. 'halt' non parte, 'plan_only' produce un piano "
                f"di ricerche esplicitamente non eseguite.")
        return cls(required=bool(mapping.get("required", True)), on_unavailable=policy,
                   note=str(mapping.get("note", "")))

    def as_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class RelevanceCriterion:
    ident: str
    text: str


@dataclass(frozen=True)
class SeedHypothesis:
    """A hypothesis the operator brings in, with the id the workers must refer to."""

    ident: str
    statement: str
    initial_evidence: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    status: str = "open"

    def as_record(self) -> dict[str, Any]:
        return {"id": self.ident, "statement": self.statement,
                "initial_evidence": list(self.initial_evidence),
                "alternatives": list(self.alternatives), "status": self.status}


@dataclass(frozen=True)
class ResearchBrief:
    """A brief read in research mode. The base brief keeps its versioning and its guards."""

    brief: Brief
    scope: str
    out_of_scope: str
    relevance_criteria: tuple[RelevanceCriterion, ...]
    hypotheses: tuple[SeedHypothesis, ...]
    perspectives: dict[str, str]
    budget: Budget
    search: SearchPolicy
    lead_assignment: str = "both"
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def title(self) -> str:
        return self.brief.title

    @property
    def question(self) -> str:
        return self.brief.question

    def perspective_for(self, role: str) -> str:
        return self.perspectives.get(role, "")

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.brief.brief_id, "version": self.brief.version,
            "sha256": self.brief.content_sha256, "title": self.title,
            "question": self.question, "scope": self.scope,
            "out_of_scope": self.out_of_scope,
            "relevance_criteria": [{"id": item.ident, "text": item.text}
                                   for item in self.relevance_criteria],
            "hypotheses": [item.as_record() for item in self.hypotheses],
            "perspectives": dict(self.perspectives),
            "budget": self.budget.as_record(), "search": self.search.as_record(),
            "lead_assignment": self.lead_assignment,
        }


def is_research_brief(brief: Brief) -> bool:
    return str(brief.raw.get("mode", "")).strip() == "scientific_research"


def _criteria(raw: Any) -> tuple[RelevanceCriterion, ...]:
    if not isinstance(raw, list) or not raw:
        raise BriefError(
            "research.relevance_criteria deve essere una lista non vuota: senza criteri di "
            "pertinenza «ho trovato qualcosa» non e' contestabile.")
    found: list[RelevanceCriterion] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw):
        if isinstance(entry, str):
            entry = {"text": entry}
        if not isinstance(entry, dict) or not entry.get("text"):
            raise BriefError(f"research.relevance_criteria #{index} non ha testo")
        ident = str(entry.get("id") or f"P{index + 1}")
        if ident in seen:
            raise BriefError(f"criterio di pertinenza duplicato: {ident!r}")
        seen.add(ident)
        found.append(RelevanceCriterion(ident=ident, text=str(entry["text"])))
    return tuple(found)


def _hypotheses(raw: Any) -> tuple[SeedHypothesis, ...]:
    found: list[SeedHypothesis] = []
    for index, entry in enumerate(raw or []):
        if isinstance(entry, str):
            entry = {"statement": entry}
        if not isinstance(entry, dict) or not entry.get("statement"):
            raise BriefError(f"research.hypotheses #{index} non ha 'statement'")
        found.append(SeedHypothesis(
            ident=str(entry.get("id") or f"H{index + 1}"),
            statement=str(entry["statement"]),
            initial_evidence=tuple(str(item) for item in entry.get("initial_evidence", ())),
            alternatives=tuple(str(item) for item in entry.get("alternatives", ())),
            status=str(entry.get("status", "open"))))
    return tuple(found)


def load_research_brief(brief: Brief, settings: Settings) -> ResearchBrief:
    """Read the `research:` block of an already-loaded brief. Raises BriefError."""
    document = brief.raw.get("research")
    if not isinstance(document, dict):
        raise BriefError(
            f"{brief.source_path}: mode e' 'scientific_research' ma manca il blocco "
            f"'research:' con perimetro, criteri di pertinenza, ipotesi e budget.")

    perspectives_raw = document.get("perspectives") or {}
    if not isinstance(perspectives_raw, dict):
        raise BriefError("research.perspectives deve mappare un ruolo a una prospettiva")
    unknown = [role for role in perspectives_raw if role not in settings.roles]
    if unknown:
        raise BriefError(
            f"research.perspectives nomina ruoli che la configurazione non conosce: "
            f"{unknown}. I ruoli disponibili sono {sorted(settings.roles)}.")

    assignment = str(document.get("lead_assignment", "both"))
    if assignment not in LEAD_ASSIGNMENT:
        raise BriefError(
            f"research.lead_assignment e' {assignment!r}; ammessi: {LEAD_ASSIGNMENT}. "
            f"'both' fa approfondire ogni pista a entrambi, ed e' l'unico che produce due "
            f"letture confrontabili della stessa pista.")

    scope = str(document.get("scope", "")).strip()
    if not scope:
        raise BriefError("research.scope e' obbligatorio: senza perimetro una campagna di "
                         "ricerca non ha un criterio per fermarsi né per escludere nulla.")

    return ResearchBrief(
        brief=brief,
        scope=scope,
        out_of_scope=str(document.get("out_of_scope", "")).strip(),
        relevance_criteria=_criteria(document.get("relevance_criteria")),
        hypotheses=_hypotheses(document.get("hypotheses")),
        perspectives={str(role): str(text) for role, text in perspectives_raw.items()},
        budget=Budget.from_config((settings.raw.get("research") or {}).get("budget"),
                                  document.get("budget")),
        search=SearchPolicy.from_config(document.get("search")),
        lead_assignment=assignment,
        raw=document,
    )


# ------------------------------------------------------------------ search capability

@dataclass(frozen=True)
class SearchCapability:
    """What we know about one service's ability to search the web, and how we know it.

    Three states, kept apart because they are three different amounts of knowledge:

    * `available` -- the service profile describes a composer control that turns web
      search on, and the adapter will set it and read the state back before sending. That
      is an observation about the channel, and it is as far as observation goes here.
    * `undeclared` -- nobody has described such a control for this service. It may well
      have one; we have not looked at it, and a selector nobody observed is a guess.
    * `disabled` -- the campaign asked for it off.

    Note what `available` does **not** buy: it says the switch was on, never that any
    particular query ran. Those are different facts and the record keeps them apart.
    """

    service: str
    state: str                      # available | undeclared | disabled
    mode_name: str = ""
    detail: str = ""

    @property
    def can_search(self) -> bool:
        return self.state == "available"

    def as_record(self) -> dict[str, Any]:
        return {"service": self.service, "state": self.state, "mode": self.mode_name,
                "detail": self.detail}


def search_capability(settings: Settings, service: str, *, wanted: bool = True) -> SearchCapability:
    """Resolve, from configuration alone, whether this service can be made to search."""
    config = settings.service_config(service)
    declared = (config.get("search") or {}) if isinstance(config.get("search"), dict) else {}
    mode_name = str(declared.get("mode", "")).strip()
    if not wanted:
        return SearchCapability(service, "disabled", mode_name,
                                "la campagna non chiede la ricerca sul web")
    if not mode_name:
        return SearchCapability(
            service, "undeclared", "",
            f"il profilo di {service} non dichiara un controllo di ricerca sul web. "
            f"Puo' darsi che l'interfaccia ne abbia uno: non e' stato osservato, e un "
            f"selettore mai visto e' un'ipotesi, non una configurazione.")
    profile_modes = {}
    # The adapter reads the selector map from services/<profile>.yaml; here we can only
    # check that the service config names a mode, and let preflight do the rest. Naming a
    # mode the profile never describes fails loudly in `apply_modes`, before any send.
    return SearchCapability(
        service, "available", mode_name,
        f"il profilo dichiara '{mode_name}' come interruttore di ricerca sul web; "
        f"l'adattatore lo imposta e ne rilegge lo stato prima del primo messaggio "
        f"{profile_modes or ''}".strip())


def campaign_id(research: ResearchBrief, route_name: str) -> str:
    return "RS-" + short_id(research.brief.content_sha256, route_name, length=8)
