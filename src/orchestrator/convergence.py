"""When to keep going, when to stop, and which kind of stop it was.

The operator's requirement, restated as code: agreement between two solvers is not
evidence of correctness, so "they said the same thing" and "the criteria were checked"
must never collapse into one outcome. This module keeps five endings apart:

* `verified_complete`      -- every acceptance criterion has an automatic check and it passed.
* `unresolved_disagreement`-- a blocking objection survived N rounds with both sides answering.
* `proposals_converged`    -- the proposals stopped changing and agree; validation still missing.
* `stagnation`             -- no new evidence, no new objection, no correction, for N rounds.
* `limit_reached`          -- rounds, wall clock, or a service that stopped answering.

Every loop has a hard round cap, including the ones described as running "to
convergence", and the decision is always recorded with the numbers that produced it so a
person can disagree with the rule rather than guess at it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Sequence

from .checks import ABSENT, CheckResult, PASS, PENDING
from .util import similarity, unified_diff


class Decision(str, Enum):
    CONTINUE = "continue"
    VERIFIED_COMPLETE = "verified_complete"
    PROPOSALS_CONVERGED = "proposals_converged"
    STAGNATION = "stagnation"
    UNRESOLVED_DISAGREEMENT = "unresolved_disagreement"
    LIMIT_REACHED = "limit_reached"
    SERVICE_UNAVAILABLE = "service_unavailable"
    HUMAN_STOP = "human_stop"


TERMINAL = tuple(decision for decision in Decision if decision is not Decision.CONTINUE)


@dataclass(frozen=True)
class Limits:
    """Hard bounds. Read from configuration only -- never from a model reply."""

    max_rounds: int = 6
    stagnation_rounds: int = 2
    convergence_rounds: int = 2
    convergence_similarity: float = 0.92
    self_similarity_stagnation: float = 0.97
    disagreement_rounds: int = 3
    max_wall_clock_minutes: int = 120
    transport_retries: int = 2
    absence_tolerance: int = 2      # consecutive rounds a service may miss before stopping

    @classmethod
    def from_config(cls, *mappings: dict[str, Any] | None) -> "Limits":
        values: dict[str, Any] = {}
        for mapping in mappings:
            for key, value in (mapping or {}).items():
                if key in cls.__dataclass_fields__:
                    values[key] = value
        return cls(**values)


@dataclass(frozen=True)
class RoleTurn:
    role: str
    proposal: str
    evidence_ids: tuple[str, ...] = ()
    objection_ids: tuple[str, ...] = ()
    resolved_ids: tuple[str, ...] = ()
    changes: tuple[str, ...] = ()
    unparsed: bool = False
    service: str = ""
    family: str = ""       # which model answered; two sessions of one model share it


@dataclass(frozen=True)
class RoundState:
    number: int
    turns: tuple[RoleTurn, ...]

    def turn(self, role: str) -> RoleTurn | None:
        for item in self.turns:
            if item.role == role:
                return item
        return None

    @property
    def roles(self) -> tuple[str, ...]:
        return tuple(turn.role for turn in self.turns)


@dataclass(frozen=True)
class Evaluation:
    decision: Decision
    reason: str                       # short machine-readable code
    numbers: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.decision is not Decision.CONTINUE


# ------------------------------------------------------------------ measurements

def cross_agreement(state: RoundState) -> float | None:
    """How close the roles' proposals are to each other in this round."""
    proposals = [turn.proposal for turn in state.turns if turn.proposal.strip()]
    if len(proposals) < 2:
        return None
    scores = [
        similarity(proposals[index], proposals[other])
        for index in range(len(proposals)) for other in range(index + 1, len(proposals))
    ]
    return min(scores)


def one_model_only(state: RoundState) -> bool:
    """True when every proposal in the round came from the same model.

    Happens when a reserve session covers a seat: two voices, one model. The agreement
    between them is a model agreeing with itself, which is not what this loop measures,
    so the decision that follows has to carry the warning rather than hide it.
    """
    speaking = [turn for turn in state.turns if turn.proposal.strip()]
    if len(speaking) < 2 or any(not turn.family for turn in speaking):
        return False
    return len({turn.family for turn in speaking}) == 1


def self_similarity(previous: RoundState, current: RoundState) -> dict[str, float]:
    """How much each role changed its own proposal since the previous round."""
    scores: dict[str, float] = {}
    for turn in current.turns:
        earlier = previous.turn(turn.role)
        if earlier is not None:
            scores[turn.role] = similarity(earlier.proposal, turn.proposal)
    return scores


def round_delta(previous: RoundState | None, current: RoundState) -> dict[str, Any]:
    """What changed since the previous round, in a form the operator can read."""
    delta: dict[str, Any] = {"round": current.number, "roles": {}}
    for turn in current.turns:
        earlier = previous.turn(turn.role) if previous else None
        entry: dict[str, Any] = {
            "new_evidence": sorted(set(turn.evidence_ids) - set(earlier.evidence_ids if earlier else ())),
            "new_objections": sorted(set(turn.objection_ids) - set(earlier.objection_ids if earlier else ())),
            "resolved": sorted(turn.resolved_ids),
            "declared_changes": list(turn.changes),
            "unparsed": turn.unparsed,
        }
        if earlier is not None:
            entry["self_similarity"] = round(similarity(earlier.proposal, turn.proposal), 4)
            entry["diff"] = unified_diff(
                earlier.proposal, turn.proposal,
                before_label=f"{turn.role} round {previous.number}",
                after_label=f"{turn.role} round {current.number}")[:8000]
        delta["roles"][turn.role] = entry
    agreement = cross_agreement(current)
    if agreement is not None:
        delta["cross_agreement"] = round(agreement, 4)
    return delta


def _novelty(state: RoundState, previous: RoundState | None) -> dict[str, int]:
    before_evidence = set()
    before_objections = set()
    if previous is not None:
        for turn in previous.turns:
            before_evidence.update(turn.evidence_ids)
            before_objections.update(turn.objection_ids)
    new_evidence, new_objections, resolved = set(), set(), set()
    for turn in state.turns:
        new_evidence.update(set(turn.evidence_ids) - before_evidence)
        new_objections.update(set(turn.objection_ids) - before_objections)
        resolved.update(turn.resolved_ids)
    return {"new_evidence": len(new_evidence), "new_objections": len(new_objections),
            "resolved_objections": len(resolved)}


def blocking_age(history: Sequence[RoundState], open_blocking: Iterable[str]) -> dict[str, int]:
    """How many real chances a still-open blocking objection has had to be settled.

    Not elapsed rounds: **complete** rounds after the one that raised it. Two corrections
    to the obvious count, both learned from the run of 2026-09-14 00:24, which declared an
    irreconcilable disagreement after Kimi had been given exactly one chance to answer:

    * the round that raises an objection does not count, because rounds are synchronous
      and the other side could not have seen it yet;
    * a round in which anyone was missing does not count either. Settling an objection
      needs the target to answer it *and* the objector to accept the answer, so a round
      with a voice missing was never an opportunity. Without this, a service that times
      out gets convicted of a disagreement it was never allowed to resolve.
    """
    ages: dict[str, int] = {}
    for ident in open_blocking:
        first = next((state.number for state in history
                      if any(ident in turn.objection_ids for turn in state.turns)), None)
        if first is None:
            continue
        ages[ident] = sum(
            1 for state in history
            if state.number > first
            and all(not turn.unparsed and turn.proposal.strip() for turn in state.turns)
        )
    return ages


# ---------------------------------------------------------------------- decision

def _converged(reason: str, window: Sequence[RoundState],
               numbers: dict[str, Any]) -> Evaluation:
    """Convergence, with a note when the window was one model talking to itself.

    The decision does not change -- the proposals did converge -- but the reason does,
    and so does the wording shown to the operator. Two sessions of one model reaching the
    same answer is a weaker fact than two different models doing so, and the difference
    must not be lost between here and the report.
    """
    if any(one_model_only(state) for state in window):
        numbers["same_model_rounds"] = [state.number for state in window
                                        if one_model_only(state)]
        return Evaluation(Decision.PROPOSALS_CONVERGED, reason + "_same_model", numbers)
    return Evaluation(Decision.PROPOSALS_CONVERGED, reason, numbers)


def evaluate(history: Sequence[RoundState], *, checks: Sequence[CheckResult],
             limits: Limits, open_blocking: Sequence[str] = (),
             open_disputes: Sequence[str] = (), elapsed_minutes: float = 0.0,
             service_unavailable: str | None = None) -> Evaluation:
    """Decide whether the solve loop continues. Pure function of recorded state."""
    if not history:
        return Evaluation(Decision.CONTINUE, "no_rounds_yet")

    current = history[-1]
    previous = history[-2] if len(history) > 1 else None
    novelty = _novelty(current, previous)
    agreement = cross_agreement(current)
    self_scores = self_similarity(previous, current) if previous else {}
    passed = sum(1 for check in checks if check.status == PASS)
    pending = sum(1 for check in checks if check.status == PENDING)
    absent = sum(1 for check in checks if check.status == ABSENT)
    failed = len(checks) - passed - pending - absent
    ages = blocking_age(history, open_blocking)

    numbers: dict[str, Any] = {
        "round": current.number,
        "max_rounds": limits.max_rounds,
        "checks": {"passed": passed, "failed": failed, "pending": pending,
                   "absent": absent, "total": len(checks)},
        "cross_agreement": None if agreement is None else round(agreement, 4),
        "self_similarity": {role: round(score, 4) for role, score in self_scores.items()},
        "novelty": novelty,
        "open_blocking": dict(ages),
        "elapsed_minutes": round(elapsed_minutes, 1),
    }

    if service_unavailable:
        return Evaluation(Decision.SERVICE_UNAVAILABLE, service_unavailable, numbers)

    # 1. Verified completion. Every criterion checked automatically, every check green.
    # `absent` counts here as much as `failed` does, and for a sharper reason: a criterion
    # nobody was asked about this round has not been met, and a round missing a voice must
    # never read as the strongest ending the system can reach.
    if checks and failed == 0 and pending == 0 and absent == 0:
        return Evaluation(Decision.VERIFIED_COMPLETE, "all_checks_passed", numbers)

    # 2. A blocking objection that survived long enough is a decision for a person.
    stale_blocking = {ident: age for ident, age in ages.items()
                      if age >= limits.disagreement_rounds}
    if stale_blocking:
        numbers["stale_blocking"] = stale_blocking
        return Evaluation(Decision.UNRESOLVED_DISAGREEMENT, "blocking_objection_persists", numbers)

    # 3. Convergence: the proposals agree and stopped moving, for enough rounds.
    if agreement is not None and len(history) >= limits.convergence_rounds:
        window = history[-limits.convergence_rounds:]
        agreements = [cross_agreement(state) for state in window]
        stable = all(score is not None and score >= limits.convergence_similarity
                     for score in agreements)
        settled = (not self_scores) or all(
            score >= limits.self_similarity_stagnation for score in self_scores.values())
        if stable and settled:
            numbers["agreement_window"] = [None if score is None else round(score, 4)
                                           for score in agreements]
            return _converged("stable_and_agreeing", window, numbers)

    # 4. They stopped producing. Whether that is convergence or stagnation depends on
    #    one thing only: whether anything is still disputed between them.
    #
    #    Textual similarity cannot make that call. Measured on the run of 2026-09-13:
    #    two models that agreed on every substantive point scored 0.345, because they
    #    write differently. A rule that waits for 0.92 across two models waits for ever,
    #    and "run to convergence" would silently mean "run to the cap".
    if len(history) > limits.stagnation_rounds:
        quiet = True
        for position in range(len(history) - limits.stagnation_rounds, len(history)):
            state, earlier = history[position], history[position - 1]
            counts = _novelty(state, earlier)
            moved = any(
                similarity(earlier.turn(turn.role).proposal, turn.proposal)
                < limits.self_similarity_stagnation
                for turn in state.turns
                if earlier.turn(turn.role) is not None
            )
            if counts["new_evidence"] or counts["new_objections"] or counts["resolved_objections"] or moved:
                quiet = False
                break
        if quiet:
            numbers["quiet_rounds"] = limits.stagnation_rounds
            numbers["open_disputes"] = list(open_disputes)
            if not open_disputes:
                return _converged("settled_with_nothing_disputed",
                                  history[-limits.stagnation_rounds:], numbers)
            return Evaluation(Decision.STAGNATION, "no_new_evidence_or_objections", numbers)

    # 5. Hard limits. These apply to every loop, including the ones run "to convergence".
    if current.number >= limits.max_rounds:
        return Evaluation(Decision.LIMIT_REACHED, "max_rounds", numbers)
    if limits.max_wall_clock_minutes and elapsed_minutes >= limits.max_wall_clock_minutes:
        return Evaluation(Decision.LIMIT_REACHED, "wall_clock", numbers)

    return Evaluation(Decision.CONTINUE, "criteria_not_verified_yet", numbers)


# ------------------------------------------------- operator-facing wording (Italian)

_WORDS = {
    Decision.VERIFIED_COMPLETE: (
        "Completamento verificato: tutti i criteri di accettazione hanno un controllo "
        "automatico e tutti sono passati."),
    Decision.PROPOSALS_CONVERGED: (
        "Convergenza delle proposte: le soluzioni sono stabili e concordi, ma la "
        "validazione non e' stata fatta. Non e' una prova di correttezza."),
    Decision.STAGNATION: (
        "Stagnazione: nessuna nuova evidenza, obiezione o correzione nei round previsti."),
    Decision.UNRESOLVED_DISAGREEMENT: (
        "Disaccordo irrisolto: un'obiezione bloccante e' rimasta aperta. Serve una "
        "decisione umana."),
    Decision.LIMIT_REACHED: (
        "Limite raggiunto: numero massimo di round o durata massima."),
    Decision.SERVICE_UNAVAILABLE: (
        "Servizio non disponibile: un modello non ha risposto e non e' stato sostituito."),
    Decision.HUMAN_STOP: "Arresto richiesto dall'operatore.",
    Decision.CONTINUE: "Il ciclo continua: i criteri non sono ancora verificati.",
}


def describe(evaluation: Evaluation) -> str:
    """One sentence in Italian, plus the numbers that produced the decision."""
    numbers = evaluation.numbers
    checks = numbers.get("checks", {})
    details = [
        f"round {numbers.get('round', '?')}/{numbers.get('max_rounds', '?')}",
        f"controlli {checks.get('passed', 0)} ok / {checks.get('failed', 0)} falliti / "
        f"{checks.get('pending', 0)} da verificare a mano"
        + (f" / {checks['absent']} non eseguiti per assenza" if checks.get("absent")
           else ""),
    ]
    if numbers.get("cross_agreement") is not None:
        details.append(f"somiglianza testuale fra proposte "
                       f"{numbers['cross_agreement']:.3f}")
    novelty = numbers.get("novelty") or {}
    if novelty:
        details.append(
            f"novita': {novelty.get('new_evidence', 0)} evidenze, "
            f"{novelty.get('new_objections', 0)} obiezioni, "
            f"{novelty.get('resolved_objections', 0)} risolte")
    if numbers.get("open_blocking"):
        details.append("obiezioni bloccanti aperte: " + ", ".join(
            f"{ident} da {age} round" for ident, age in numbers["open_blocking"].items()))
    sentence = _WORDS[evaluation.decision] + " (" + "; ".join(details) + ")"
    if numbers.get("same_model_rounds"):
        rounds = ", ".join(str(number) for number in numbers["same_model_rounds"])
        sentence += (f" ATTENZIONE: nei round {rounds} hanno risposto due sessioni dello "
                     f"stesso modello, perche' l'altro servizio non ha consegnato. "
                     f"L'accordo li' e' di un modello con se stesso, non fra modelli "
                     f"diversi: vale meno, e va letto sapendolo.")
    return sentence
