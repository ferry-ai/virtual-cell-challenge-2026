"""Choosing which lines of enquiry phase 3 pays for. Deterministic, and written down.

The rule matters more than the outcome, because the alternative -- asking a model, or
asking Claude, which line looks most promising -- puts a judgement inside the loop at the
exact point where the campaign spends its remaining budget. So:

1. From each worker's phase-2 reply, take its leads **in the order it wrote them** and
   keep the first that is well formed: hypothesis, starting evidence, alternative
   explanation, and a search that would tell the two apart. A lead missing one of the
   four is not a lead, it is a preference.
2. Sort the candidates by role name, so the order the two were contacted in changes
   nothing.
3. Deduplicate. Two leads are the same when their hypotheses normalise to the same text,
   or are textually close above a threshold the configuration sets. A merged lead keeps
   both proposers.
4. Keep at most `max_leads` (two).

**There is no backfill.** If both workers propose the same lead, there is one lead, and
the fact that they converged on it is itself information -- filling the empty slot with
somebody's second choice would hide that. The report says so in as many words.

Step 3 is the one place in this package where textual similarity decides anything, and it
decides how *our own* budget is spent, never what a source is. Sources are merged on
identifiers only, in `contract.source_key`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from ..util import normalise, similarity
from .contract import Lead

DEFAULT_DUPLICATE_SIMILARITY = 0.85

# Below this many characters, only an exact match merges two leads. Similarity on short
# strings measures spelling, not meaning: "pista di A" and "pista di B" score 0.90 and
# are opposites. Found by the tests before it could quietly halve a campaign's phase 3,
# which is exactly the class of bug that would have been invisible in a real run --
# nobody counts the leads they did not get.
MIN_LENGTH_FOR_FUZZY_MATCH = 60


@dataclass(frozen=True)
class SelectedLead:
    """A lead phase 3 will work on, with who proposed it and why it survived."""

    lead: Lead
    proposed_by: tuple[str, ...]
    rank: int

    @property
    def ident(self) -> str:
        return self.lead.ident

    def as_record(self) -> dict[str, Any]:
        return {**self.lead.as_record(), "proposed_by": list(self.proposed_by),
                "rank": self.rank}


@dataclass
class Selection:
    """The outcome of the rule, with everything it left behind and why."""

    selected: tuple[SelectedLead, ...] = ()
    merged: tuple[tuple[str, str], ...] = ()        # (kept id, role whose lead merged in)
    rejected: tuple[dict[str, Any], ...] = ()       # ill-formed or over the cap
    considered: int = 0
    cap: int = 2
    rule: str = ""

    @property
    def idents(self) -> tuple[str, ...]:
        return tuple(item.ident for item in self.selected)

    @classmethod
    def from_record(cls, document: dict[str, Any]) -> "Selection":
        """Rebuild a selection that was already frozen to `leads.json`.

        A resumed campaign must not re-choose. Re-deriving would give the same answer
        today -- the rule is deterministic -- but a phase-3 prompt built from a different
        selection would hash differently, and the resume would ask a question that had
        already been asked. The frozen file is the authority.
        """
        selected = tuple(
            SelectedLead(
                lead=Lead(hypothesis=item.get("hypothesis", ""),
                          starting_evidence=item.get("starting_evidence", ""),
                          alternative_explanation=item.get("alternative_explanation", ""),
                          distinguishing_search=item.get("distinguishing_search", ""),
                          strategy_change=item.get("strategy_change", ""),
                          role=item.get("role", ""), position=item.get("position", 0),
                          step_id=item.get("step_id", "")),
                proposed_by=tuple(item.get("proposed_by", ())),
                rank=int(item.get("rank", 0)))
            for item in document.get("selected", []))
        return cls(
            selected=selected,
            merged=tuple((item["kept"], item["also_proposed_by"])
                         for item in document.get("merged", [])),
            rejected=tuple(document.get("rejected", ())),
            considered=int(document.get("considered", 0)),
            cap=int(document.get("cap", 2)), rule=str(document.get("rule", "")))

    def as_record(self) -> dict[str, Any]:
        return {"rule": self.rule, "cap": self.cap, "considered": self.considered,
                "selected": [item.as_record() for item in self.selected],
                "merged": [{"kept": kept, "also_proposed_by": role}
                           for kept, role in self.merged],
                "rejected": list(self.rejected)}


RULE = (
    "Una proposta prioritaria per worker -- la prima ben formata nell'ordine in cui l'ha "
    "scritta -- ordinate per nome del ruolo, deduplicate sull'ipotesi, troncate a "
    "{cap}. Nessun ripescaggio: se i due propongono la stessa pista, la pista e' una "
    "sola, e il fatto che coincidano e' un'informazione, non un posto vuoto da riempire."
)


def _priority_lead(leads: Sequence[Lead]) -> tuple[Lead | None, list[dict[str, Any]]]:
    """The first well-formed lead, and the ones skipped before it, with the reason."""
    skipped: list[dict[str, Any]] = []
    for lead in leads:
        if lead.is_well_formed:
            return lead, skipped
        skipped.append({"id": lead.ident, "role": lead.role,
                        "hypothesis": lead.hypothesis[:300],
                        "reason": "pista incompleta: mancano "
                                  + ", ".join(lead.missing_parts)})
    return None, skipped


def select_leads(leads_by_role: dict[str, Sequence[Lead]], *, cap: int = 2,
                 duplicate_similarity: float = DEFAULT_DUPLICATE_SIMILARITY) -> Selection:
    """Apply the rule. Pure function of the parsed phase-2 replies."""
    rejected: list[dict[str, Any]] = []
    candidates: list[Lead] = []
    considered = 0

    for role in sorted(leads_by_role):
        leads = list(leads_by_role[role] or [])
        considered += len(leads)
        chosen, skipped = _priority_lead(leads)
        rejected.extend(skipped)
        if chosen is None:
            continue
        candidates.append(chosen)
        for other in leads:
            if other is not chosen:
                rejected.append({"id": other.ident, "role": other.role,
                                 "hypothesis": other.hypothesis[:300],
                                 "reason": "non e' la proposta prioritaria di questo worker"})

    selected: list[SelectedLead] = []
    merged: list[tuple[str, str]] = []
    for lead in candidates:
        twin = next((item for item in selected
                     if _same_lead(item.lead, lead, duplicate_similarity)), None)
        if twin is not None:
            merged.append((twin.ident, lead.role))
            selected[selected.index(twin)] = SelectedLead(
                lead=twin.lead,
                proposed_by=tuple(dict.fromkeys((*twin.proposed_by, lead.role))),
                rank=twin.rank)
            continue
        if len(selected) >= cap:
            rejected.append({"id": lead.ident, "role": lead.role,
                             "hypothesis": lead.hypothesis[:300],
                             "reason": f"oltre il tetto di {cap} piste"})
            continue
        selected.append(SelectedLead(lead=lead, proposed_by=(lead.role,),
                                     rank=len(selected) + 1))

    return Selection(selected=tuple(selected), merged=tuple(merged),
                     rejected=tuple(rejected), considered=considered, cap=cap,
                     rule=RULE.format(cap=cap))


def _same_lead(left: Lead, right: Lead, threshold: float) -> bool:
    """Whether two leads are the same line of enquiry. Conservative by construction.

    Merging two different leads costs a whole lead out of two, and nobody notices the one
    that never ran. So an exact match always merges, a close match merges only when there
    is enough text for closeness to mean anything, and everything else stays two.
    """
    first, second = normalise(left.hypothesis), normalise(right.hypothesis)
    if first == second:
        return True
    if min(len(first), len(second)) < MIN_LENGTH_FOR_FUZZY_MATCH:
        return False
    return similarity(first, second) >= threshold


def assign(selection: Selection, roles: Sequence[str], policy: str = "both"
           ) -> dict[str, tuple[SelectedLead, ...]]:
    """Which worker deepens which lead in phase 3.

    `both` is the default and the only policy that yields two independent readings of the
    same lead, which is what makes a disagreement in phase 3 visible at all. `cross` hands
    each worker the lead the other proposed -- fresher eyes, but nothing to compare -- and
    `own` lets each continue its own. All three are deterministic in the role names, never
    in the order the services were contacted.
    """
    roles = sorted(roles)
    if not selection.selected:
        return {role: () for role in roles}
    if policy == "both":
        return {role: selection.selected for role in roles}
    assignment: dict[str, tuple[SelectedLead, ...]] = {}
    for role in roles:
        if policy == "own":
            mine = tuple(item for item in selection.selected if role in item.proposed_by)
        else:  # cross
            mine = tuple(item for item in selection.selected if role not in item.proposed_by)
        # A worker with nothing assigned would have nothing to do in phase 3; when the
        # split leaves it empty -- one lead, or one both proposed -- it gets everything,
        # because an idle seat is a wasted response out of six.
        assignment[role] = mine or selection.selected
    return assignment
