"""What a research reply may say, and what we are willing to write down as a fact.

This module is the boundary of the research mode, the way `protocol` is the boundary of
the debugging loop, and it carries one extra duty: keeping apart things that read alike
and mean very different amounts.

A query can be **proposed** (nobody ran it), **declared** by the worker (it says it ran
it), or **observed** in the channel (an artefact of the session shows it ran). Only the
engine may set the third, from evidence it collected itself; no field of any reply can
reach it. A source can have been **found**, had its **abstract** read, had its **full
text or a section** read, or been **not accessible** -- and every one of those levels is
recorded as *declared by that worker*, because we did not watch them read.

A claim is a **result reported by the authors**, a **worker's interpretation**, or a
**new hypothesis**. The parser cannot tell whether a claim is true, and does not try.
What it can do, and does, is flag the structural shapes in which a false attribution
usually arrives: a result attributed to a source nobody opened, or to a source that was
never listed, or without a locator. A flag is a reason to look, not a verdict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace as _replace
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from ..protocol import ContentProblem, find_result_object
from ..util import normalise, short_id

RESEARCH_SENTINEL = "ORCH-RESEARCH-V1"

MAX_FIELD_CHARS = 8_000
MAX_LIST_ITEMS = 60

# How a query came to be written down. The order is the order of strength, and code only
# ever moves a record *down* it, never up.
SEARCH_PROVENANCE = ("proposed", "declared_by_worker", "observed_in_channel")
SEARCH_STATUS = ("executed", "not_executed", "failed", "blocked")

# What the worker says it got out of a source. "found" means a hit in a result list and
# nothing more; it is the level a fabricated reference is most comfortable at.
CONSULTED = ("found", "abstract", "full_text_or_section", "not_accessible")

CLAIM_NATURE = ("reported_by_authors", "worker_interpretation", "new_hypothesis")
HYPOTHESIS_STATUS = ("open", "supported_declared", "contradicted_declared", "undecided")

# Everything the engine will read out of a research reply. Anything else is dropped and
# the drop is recorded: a reply that writes "max_rounds" or "budget" lands in the archive
# as text and changes nothing. `operator_requests` is the one place a worker may ask for
# something -- it is shown to the operator and acted on by nobody.
ALLOWED_KEYS = frozenset({
    "summary", "synthesis", "searches", "sources", "claims", "hypotheses", "gaps",
    "leads", "agreements", "complementary", "contradictions", "unsupported_assumptions",
    "search_gaps", "open_questions", "saturation_claim", "operator_requests",
    "confidence",
})

_DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.I)
_TRACKING = re.compile(r"^(utm_|ref$|ref_|fbclid$|gclid$|mc_[ce]id$)", re.I)


def _clip(value: Any, limit: int = MAX_FIELD_CHARS) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    return text.strip()[:limit]


def _as_list(value: Any) -> list[Any]:
    if value in (None, "", {}):
        return []
    if isinstance(value, list):
        return value[:MAX_LIST_ITEMS]
    return [value]


def _strings(value: Any, limit: int = 600) -> tuple[str, ...]:
    return tuple(_clip(item, limit) for item in _as_list(value) if _clip(item, limit))


def _one_of(value: Any, allowed: tuple[str, ...], fallback: str,
            issues: list[str], label: str) -> str:
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if text in allowed:
        return text
    if text:
        issues.append(f"{label} {text!r} non e' uno di {allowed}; letto come {fallback!r}")
    return fallback


# --------------------------------------------------------------- identity of a source

def normalise_doi(raw: str) -> str:
    """A DOI reduced to its bare form. Empty when there is nothing DOI-shaped here."""
    text = _DOI_PREFIX.sub("", (raw or "").strip()).strip().rstrip(".").lower()
    return text if text.startswith("10.") and "/" in text else ""


def normalise_url(raw: str) -> str:
    """A URL reduced to what identifies the document, not how someone arrived at it.

    Scheme and host lowercased, `www.` dropped, fragment dropped, tracking parameters
    dropped, a trailing slash dropped. Deliberately conservative: two addresses that
    differ in their path stay two sources, because they usually are.
    """
    text = (raw or "").strip()
    if not text or "://" not in text:
        return ""
    try:
        parts = urlsplit(text)
    except ValueError:
        return ""
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query = "&".join(sorted(
        item for item in parts.query.split("&")
        if item and not _TRACKING.match(item.split("=")[0])
    ))
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, query, ""))


def source_key(*, doi: str = "", url: str = "", title: str = "", authors: str = "",
               year: str = "") -> tuple[str, str]:
    """The key two records must share to be the same source, and which kind it is.

    Order matters and is the whole policy. A DOI is an identifier, so it merges. A
    normalised URL is an identifier, so it merges. Failing both, the key is the *exact*
    normalised title with its authors and year -- an exact match of declared metadata,
    which is not the same thing as two titles looking alike. Nothing in this module
    merges on similarity: two papers with near-identical titles are routinely two papers,
    and a wrong merge destroys the record of who found what.
    """
    doi_key = normalise_doi(doi)
    if doi_key:
        return f"doi:{doi_key}", "doi"
    url_key = normalise_url(url)
    if url_key:
        return f"url:{url_key}", "url"
    fingerprint = "|".join(normalise(part) for part in (title, authors, year))
    return f"meta:{fingerprint}", "metadata"


# ------------------------------------------------------------------------- records

@dataclass(frozen=True)
class Search:
    """One query: what was asked, where, with which filters, and how sure we are it ran."""

    query: str
    service: str = ""
    filters: str = ""
    status: str = "not_executed"
    provenance: str = "proposed"
    note: str = ""
    role: str = ""
    phase: int = 0
    step_id: str = ""

    @property
    def ident(self) -> str:
        return "Q-" + short_id(normalise(self.query), normalise(self.service),
                               normalise(self.filters), self.role, length=10)

    def as_record(self) -> dict[str, Any]:
        return {"id": self.ident, "query": self.query, "service": self.service,
                "filters": self.filters, "status": self.status,
                "provenance": self.provenance, "note": self.note, "role": self.role,
                "phase": self.phase, "step_id": self.step_id}


@dataclass(frozen=True)
class Source:
    """A document a worker says it reached, with the level it says it reached it at."""

    title: str
    authors: str = ""
    year: str = ""
    doi: str = ""
    url: str = ""
    consulted: str = "found"
    access_note: str = ""
    found_via: str = ""
    local_id: str = ""          # the label the worker used inside its own reply
    role: str = ""
    phase: int = 0
    step_id: str = ""

    @property
    def key(self) -> str:
        return source_key(doi=self.doi, url=self.url, title=self.title,
                          authors=self.authors, year=self.year)[0]

    @property
    def key_kind(self) -> str:
        return source_key(doi=self.doi, url=self.url, title=self.title,
                          authors=self.authors, year=self.year)[1]

    @property
    def ident(self) -> str:
        return "F-" + short_id(self.key, length=10)

    def as_record(self) -> dict[str, Any]:
        return {"id": self.ident, "key": self.key, "key_kind": self.key_kind,
                "title": self.title, "authors": self.authors, "year": self.year,
                "doi": self.doi, "url": self.url, "consulted": self.consulted,
                "access_note": self.access_note, "found_via": self.found_via,
                "local_id": self.local_id, "role": self.role, "phase": self.phase,
                "step_id": self.step_id}


@dataclass(frozen=True)
class Claim:
    """A statement, what it leans on, and what kind of statement it is."""

    text: str
    nature: str = "worker_interpretation"
    supported_by: tuple[str, ...] = ()      # source ids, after local ids are resolved
    contradicted_by: tuple[str, ...] = ()
    about_hypothesis: str = ""
    locator: str = ""
    limits: str = ""
    role: str = ""
    phase: int = 0
    step_id: str = ""
    flags: tuple[str, ...] = ()

    @property
    def ident(self) -> str:
        return "C-" + short_id(normalise(self.text), self.role, length=10)

    def as_record(self) -> dict[str, Any]:
        return {"id": self.ident, "text": self.text, "nature": self.nature,
                "supported_by": list(self.supported_by),
                "contradicted_by": list(self.contradicted_by),
                "about_hypothesis": self.about_hypothesis, "locator": self.locator,
                "limits": self.limits, "role": self.role, "phase": self.phase,
                "step_id": self.step_id, "flags": list(self.flags)}


@dataclass(frozen=True)
class Hypothesis:
    statement: str
    ident_hint: str = ""
    initial_evidence: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    proposed_tests: tuple[str, ...] = ()
    status: str = "open"
    role: str = ""
    phase: int = 0
    step_id: str = ""

    @property
    def ident(self) -> str:
        hint = (self.ident_hint or "").strip()
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,15}", hint):
            return hint.upper()
        return "H-" + short_id(normalise(self.statement), length=10)

    def as_record(self) -> dict[str, Any]:
        return {"id": self.ident, "statement": self.statement,
                "initial_evidence": list(self.initial_evidence),
                "alternatives": list(self.alternatives),
                "proposed_tests": list(self.proposed_tests), "status": self.status,
                "role": self.role, "phase": self.phase, "step_id": self.step_id}


@dataclass(frozen=True)
class Gap:
    missing: str
    search_that_would_close_it: str = ""
    role: str = ""
    phase: int = 0
    step_id: str = ""

    @property
    def ident(self) -> str:
        return "G-" + short_id(normalise(self.missing), self.role, length=10)

    def as_record(self) -> dict[str, Any]:
        return {"id": self.ident, "missing": self.missing,
                "search_that_would_close_it": self.search_that_would_close_it,
                "role": self.role, "phase": self.phase, "step_id": self.step_id}


@dataclass(frozen=True)
class Lead:
    """A line of enquiry, in the four parts the brief demands of it.

    A lead missing any of the four is not selectable. That is not pedantry: a
    "hypothesis" with no alternative explanation and no search that separates the two is
    a thing to believe, not a thing to check, and phase 3 has room for two of these.
    """

    hypothesis: str
    starting_evidence: str = ""
    alternative_explanation: str = ""
    distinguishing_search: str = ""
    strategy_change: str = ""
    role: str = ""
    position: int = 0
    step_id: str = ""

    @property
    def ident(self) -> str:
        return "L-" + short_id(normalise(self.hypothesis), length=10)

    @property
    def is_well_formed(self) -> bool:
        return all(part.strip() for part in (self.hypothesis, self.starting_evidence,
                                             self.alternative_explanation,
                                             self.distinguishing_search))

    @property
    def missing_parts(self) -> tuple[str, ...]:
        parts = {"ipotesi": self.hypothesis, "evidenze di partenza": self.starting_evidence,
                 "spiegazione alternativa": self.alternative_explanation,
                 "ricerca che le distingue": self.distinguishing_search}
        return tuple(name for name, value in parts.items() if not value.strip())

    def as_record(self) -> dict[str, Any]:
        return {"id": self.ident, "hypothesis": self.hypothesis,
                "starting_evidence": self.starting_evidence,
                "alternative_explanation": self.alternative_explanation,
                "distinguishing_search": self.distinguishing_search,
                "strategy_change": self.strategy_change, "role": self.role,
                "position": self.position, "step_id": self.step_id,
                "well_formed": self.is_well_formed,
                "missing_parts": list(self.missing_parts)}


@dataclass
class ResearchRecord:
    """Everything read out of one reply, already attributed to its worker and phase."""

    role: str = ""
    phase: int = 0
    step_id: str = ""
    summary: str = ""
    synthesis: str = ""
    searches: tuple[Search, ...] = ()
    sources: tuple[Source, ...] = ()
    claims: tuple[Claim, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()
    gaps: tuple[Gap, ...] = ()
    leads: tuple[Lead, ...] = ()
    agreements: tuple[str, ...] = ()
    complementary: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    unsupported_assumptions: tuple[str, ...] = ()
    search_gaps: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    saturation_claim: str = ""
    operator_requests: tuple[str, ...] = ()
    confidence: str = "unknown"
    dropped_keys: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()

    def attributed(self, *, role: str, phase: int, step_id: str) -> "ResearchRecord":
        """Stamp the worker, the phase and the step onto every record read from it.

        Done in one place so nothing can end up in the dossier without an author and a
        file to go back to. Identifiers of searches and claims include the role, so the
        same query run by both workers stays two records -- who searched is part of what
        happened. Sources are the exception: they are keyed on the document, which is how
        one paper found twice counts once.
        """
        def stamp(items):
            return tuple(_replace(item, role=role, phase=phase, step_id=step_id)
                         for item in items)

        self.role, self.phase, self.step_id = role, phase, step_id
        self.searches = stamp(self.searches)
        self.sources = stamp(self.sources)
        self.claims = stamp(self.claims)
        self.hypotheses = stamp(self.hypotheses)
        self.gaps = stamp(self.gaps)
        self.leads = tuple(_replace(lead, role=role, step_id=step_id)
                           for lead in self.leads)
        # Flagging already ran at parse time, so `response.parsed.json` carries it too.
        # Both operations are idempotent, and re-running them here keeps the two paths --
        # parsed live, or re-read from disk on a resume -- producing the same record.
        self.issues = tuple(dict.fromkeys(tuple(self.issues) + _structural_flags(self)))
        self.claims = tuple(_flag_claim(claim, self.sources) for claim in self.claims)
        return self

    def as_record(self) -> dict[str, Any]:
        return {
            "role": self.role, "phase": self.phase, "step_id": self.step_id,
            "summary": self.summary, "synthesis": self.synthesis,
            "searches": [item.as_record() for item in self.searches],
            "sources": [item.as_record() for item in self.sources],
            "claims": [item.as_record() for item in self.claims],
            "hypotheses": [item.as_record() for item in self.hypotheses],
            "gaps": [item.as_record() for item in self.gaps],
            "leads": [item.as_record() for item in self.leads],
            "agreements": list(self.agreements),
            "complementary": list(self.complementary),
            "contradictions": list(self.contradictions),
            "unsupported_assumptions": list(self.unsupported_assumptions),
            "search_gaps": list(self.search_gaps),
            "open_questions": list(self.open_questions),
            "saturation_claim": self.saturation_claim,
            "operator_requests": list(self.operator_requests),
            "confidence": self.confidence,
            "dropped_keys": list(self.dropped_keys), "issues": list(self.issues),
        }


# ------------------------------------------------------------------ structural flags

def _flag_claim(claim: Claim, sources: tuple[Source, ...]) -> Claim:
    """Mark the shapes a false attribution usually arrives in. Never a verdict on truth.

    Three shapes, and each is a fact about the record rather than about the world:

    * a result attributed to the authors of a source the reply never listed;
    * a result attributed to a source the worker says it only *found*, or could not
      access, which means nobody read the sentence being attributed;
    * a result attributed to authors with no locator saying where in the document it is.

    A flagged claim is kept, shown, and left for a person. The parser cannot read a paper
    and will not pretend to: semantic falsity is out of reach here, and a scenario in the
    rehearsal exists precisely to keep that limit visible.
    """
    if claim.nature != "reported_by_authors":
        return claim

    by_id = {item.ident: item for item in sources}
    flags = list(claim.flags)
    if not claim.supported_by:
        flags.append("attribuito agli autori senza indicare una fonte")
    for ident in claim.supported_by:
        source = by_id.get(ident)
        if source is None:
            flags.append(f"attribuito a una fonte non elencata nella risposta ({ident})")
        elif source.consulted in ("found", "not_accessible"):
            flags.append(
                f"attribuito agli autori di {ident}, che pero' risulta «{source.consulted}»: "
                f"nessuno ha letto il testo a cui l'affermazione viene attribuita")
    if not claim.locator.strip():
        flags.append("attribuito agli autori senza localizzatore nel documento")
    return _replace(claim, flags=tuple(dict.fromkeys(flags)))


def _structural_flags(record: "ResearchRecord") -> tuple[str, ...]:
    issues: list[str] = []
    executed = [item for item in record.searches if item.status == "executed"]
    if record.sources and not executed:
        issues.append("elenca fonti senza dichiarare alcuna ricerca eseguita: le fonti "
                      "potrebbero venire da conoscenza pregressa, non da una ricerca")
    if record.saturation_claim.strip():
        issues.append("dichiara una saturazione della letteratura: resta una sua "
                      "affermazione motivata, non una misura")
    return tuple(issues)


# -------------------------------------------------------------------------- parsing

def _parse_searches(raw: Any, issues: list[str]) -> tuple[Search, ...]:
    found: list[Search] = []
    for item in _as_list(raw):
        if isinstance(item, str):
            item = {"query": item}
        if not isinstance(item, dict) or not _clip(item.get("query"), 600):
            issues.append("scartata una ricerca senza query")
            continue
        status = _one_of(item.get("status"), SEARCH_STATUS, "not_executed", issues, "stato")
        # Provenance is derived, never read. A reply that writes
        # "provenance": "observed_in_channel" is asking to be believed about its own
        # honesty; the strongest thing a reply can earn is "the worker says so".
        #
        # A query that failed or was blocked is still something the worker says it *did*:
        # it went somewhere and hit something. Only `not_executed` is a query nobody
        # claims to have run, and only that one is "proposed".
        provenance = "proposed" if status == "not_executed" else "declared_by_worker"
        if "provenance" in item:
            issues.append("il campo 'provenance' di una ricerca e' stato ignorato: la "
                          "provenienza la assegna l'orchestratore, non la risposta")
        found.append(Search(
            query=_clip(item["query"], 600), service=_clip(item.get("service"), 200),
            filters=_clip(item.get("filters"), 400), status=status,
            provenance=provenance, note=_clip(item.get("note"), 600)))
    return tuple(found)


def _parse_sources(raw: Any, issues: list[str]) -> tuple[Source, ...]:
    found: list[Source] = []
    for index, item in enumerate(_as_list(raw)):
        if isinstance(item, str):
            item = {"title": item}
        if not isinstance(item, dict):
            issues.append("scartata una fonte che non e' un oggetto")
            continue
        title = _clip(item.get("title"), 600)
        doi = _clip(item.get("doi"), 200)
        url = _clip(item.get("url"), 600)
        if not (title or doi or url):
            issues.append("scartata una fonte senza titolo, DOI o URL")
            continue
        found.append(Source(
            title=title, authors=_clip(item.get("authors"), 400),
            year=_clip(item.get("year"), 20), doi=doi, url=url,
            consulted=_one_of(item.get("consulted"), CONSULTED, "found", issues,
                              "livello di consultazione"),
            access_note=_clip(item.get("access_note"), 600),
            found_via=_clip(item.get("found_via"), 400),
            local_id=_clip(item.get("id"), 40) or f"F{index + 1}"))
    return tuple(found)


def _resolve_refs(values: Any, sources: tuple[Source, ...], issues: list[str],
                  label: str) -> tuple[str, ...]:
    """Turn the labels a worker used inside its own reply into our stable source ids.

    A worker cannot know an id we derive from a DOI, so it labels its sources F1, F2 and
    refers to those. A reference that matches nothing is *kept as written* rather than
    dropped: it is evidence that the reply pointed at something it never listed, and the
    claim carries a flag saying so.
    """
    by_local = {item.local_id.lower(): item.ident for item in sources if item.local_id}
    by_doi = {normalise_doi(item.doi): item.ident for item in sources if normalise_doi(item.doi)}
    by_url = {normalise_url(item.url): item.ident for item in sources if normalise_url(item.url)}
    resolved: list[str] = []
    for value in _strings(values, 400):
        key = value.strip()
        target = (by_local.get(key.lower()) or by_doi.get(normalise_doi(key))
                  or by_url.get(normalise_url(key)))
        if target is None:
            issues.append(f"{label}: il riferimento {key!r} non corrisponde a nessuna "
                          f"fonte elencata nella stessa risposta")
            target = key
        resolved.append(target)
    return tuple(dict.fromkeys(resolved))


def _parse_claims(raw: Any, sources: tuple[Source, ...], issues: list[str]) -> tuple[Claim, ...]:
    found: list[Claim] = []
    for item in _as_list(raw):
        if isinstance(item, str):
            item = {"text": item}
        if not isinstance(item, dict) or not _clip(item.get("text"), 2000):
            issues.append("scartata un'affermazione senza testo")
            continue
        found.append(Claim(
            text=_clip(item["text"], 2000),
            nature=_one_of(item.get("nature"), CLAIM_NATURE, "worker_interpretation",
                           issues, "natura dell'affermazione"),
            supported_by=_resolve_refs(item.get("supported_by"), sources, issues,
                                       "supported_by"),
            contradicted_by=_resolve_refs(item.get("contradicted_by"), sources, issues,
                                          "contradicted_by"),
            about_hypothesis=_clip(item.get("about_hypothesis"), 60),
            locator=_clip(item.get("locator"), 300),
            limits=_clip(item.get("limits"), 1000)))
    return tuple(found)


def _parse_hypotheses(raw: Any, issues: list[str]) -> tuple[Hypothesis, ...]:
    found: list[Hypothesis] = []
    for item in _as_list(raw):
        if isinstance(item, str):
            item = {"statement": item}
        if not isinstance(item, dict):
            continue
        statement = _clip(item.get("statement") or item.get("text"), 2000)
        if not statement:
            issues.append("scartata un'ipotesi senza enunciato")
            continue
        found.append(Hypothesis(
            statement=statement, ident_hint=_clip(item.get("id"), 40),
            initial_evidence=_strings(item.get("initial_evidence")),
            alternatives=_strings(item.get("alternatives")),
            proposed_tests=_strings(item.get("proposed_tests")),
            status=_one_of(item.get("status"), HYPOTHESIS_STATUS, "open", issues,
                           "stato dell'ipotesi")))
    return tuple(found)


def _parse_gaps(raw: Any, issues: list[str]) -> tuple[Gap, ...]:
    found: list[Gap] = []
    for item in _as_list(raw):
        if isinstance(item, str):
            item = {"missing": item}
        if not isinstance(item, dict) or not _clip(item.get("missing"), 1000):
            issues.append("scartata una lacuna senza descrizione")
            continue
        found.append(Gap(missing=_clip(item["missing"], 1000),
                         search_that_would_close_it=_clip(
                             item.get("search_that_would_close_it"), 600)))
    return tuple(found)


def _parse_leads(raw: Any, issues: list[str]) -> tuple[Lead, ...]:
    found: list[Lead] = []
    for position, item in enumerate(_as_list(raw)):
        if isinstance(item, str):
            item = {"hypothesis": item}
        if not isinstance(item, dict) or not _clip(item.get("hypothesis"), 2000):
            issues.append("scartata una pista senza ipotesi")
            continue
        lead = Lead(
            hypothesis=_clip(item["hypothesis"], 2000),
            starting_evidence=_clip(item.get("starting_evidence"), 2000),
            alternative_explanation=_clip(item.get("alternative_explanation"), 2000),
            distinguishing_search=_clip(item.get("distinguishing_search"), 2000),
            strategy_change=_clip(item.get("strategy_change"), 2000),
            position=position)
        if not lead.is_well_formed:
            issues.append("pista incompleta, non selezionabile: mancano "
                          + ", ".join(lead.missing_parts))
        found.append(lead)
    return tuple(found)


def parse_research_reply(text: str, *, require_synthesis: bool = True) -> ResearchRecord:
    """Read a research reply into the record. Raises ContentProblem when unreadable.

    Tolerant about where the block is, strict about what comes out of it -- the same
    stance as the debugging contract, for the same reason: a web chat is a lossy channel,
    and the cost of a missed block is a wasted round, while the cost of a field we did
    not ask for is a rule changed by a reply.
    """
    document = find_result_object(text, sentinel=RESEARCH_SENTINEL,
                                  rescue_keys=("synthesis", "summary", "sources"))
    issues: list[str] = []
    dropped = tuple(sorted(set(document) - ALLOWED_KEYS))

    synthesis = _clip(document.get("synthesis"))
    if require_synthesis and not synthesis:
        raise ContentProblem("missing_synthesis",
                             "il blocco di risultato non contiene 'synthesis'")

    sources = _parse_sources(document.get("sources"), issues)
    record = ResearchRecord(
        summary=_clip(document.get("summary"), 2000),
        synthesis=synthesis,
        searches=_parse_searches(document.get("searches"), issues),
        sources=sources,
        claims=_parse_claims(document.get("claims"), sources, issues),
        hypotheses=_parse_hypotheses(document.get("hypotheses"), issues),
        gaps=_parse_gaps(document.get("gaps"), issues),
        leads=_parse_leads(document.get("leads"), issues),
        agreements=_strings(document.get("agreements"), 2000),
        complementary=_strings(document.get("complementary"), 2000),
        contradictions=_strings(document.get("contradictions"), 2000),
        unsupported_assumptions=_strings(document.get("unsupported_assumptions"), 2000),
        search_gaps=_strings(document.get("search_gaps"), 2000),
        open_questions=_strings(document.get("open_questions"), 2000),
        saturation_claim=_clip(document.get("saturation_claim"), 2000),
        operator_requests=_strings(document.get("operator_requests"), 2000),
        confidence=_one_of(document.get("confidence"),
                           ("low", "medium", "high", "unknown"), "unknown", issues,
                           "confidenza"),
        dropped_keys=dropped,
        issues=tuple(issues),
    )
    # Structural flags are computed here, before anything is stored, so the archived
    # `response.parsed.json` already says which attributions are worth a look.
    record.issues = tuple(dict.fromkeys(record.issues + _structural_flags(record)))
    record.claims = tuple(_flag_claim(claim, record.sources) for claim in record.claims)
    return record
