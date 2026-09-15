"""Acceptance checks: the only thing allowed to turn a criterion green.

What these checks can and cannot do is worth being blunt about. A `contains` or
`numeric` check verifies that the answer *states* a value the operator committed to in
advance, inside the brief, before any model saw the question. That is weaker than an
experiment and much stronger than two models agreeing with each other, which is the
failure mode this project keeps guarding against.

A criterion whose check is `human` never passes by itself. It stays `pending`, and a run
that ends with a pending criterion is reported as needing validation, not as complete.

Model output can suggest checks; it can never mark one as passed. `checks_suggested`
lands in the report as a proposal for the operator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from .briefs import AcceptanceCriterion

PASS, FAIL, PENDING = "pass", "fail", "pending"
# A fourth state, and it earns its place: a voice that never arrived has not failed a
# criterion, it was never examined. The two used to share the `fail` row, which wrote
# «this proposal gets the number wrong» into the report for a round in which that seat
# had said nothing at all.
ABSENT = "absent"


@dataclass(frozen=True)
class CheckResult:
    criterion_id: str
    kind: str
    status: str
    detail: str
    evidence: str = ""

    @property
    def ok(self) -> bool:
        return self.status == PASS

    def as_record(self) -> dict[str, Any]:
        return {"criterion": self.criterion_id, "kind": self.kind, "status": self.status,
                "detail": self.detail, "evidence": self.evidence[:400]}


def _snippet(text: str, start: int, end: int, width: int = 90) -> str:
    left = max(0, start - width // 2)
    right = min(len(text), end + width // 2)
    return ("..." if left else "") + text[left:right].replace("\n", " ") + ("..." if right < len(text) else "")


def _check_contains(criterion: AcceptanceCriterion, text: str) -> CheckResult:
    wanted = str(criterion.check.get("value", ""))
    if not wanted:
        return CheckResult(criterion.ident, "contains", FAIL, "check has no 'value'")
    case_sensitive = bool(criterion.check.get("case_sensitive", False))
    haystack = text if case_sensitive else text.lower()
    needle = wanted if case_sensitive else wanted.lower()
    position = haystack.find(needle)
    if position < 0:
        return CheckResult(criterion.ident, "contains", FAIL,
                           f"the answer does not contain {wanted!r}")
    return CheckResult(criterion.ident, "contains", PASS, f"found {wanted!r}",
                       _snippet(text, position, position + len(wanted)))


def _check_regex(criterion: AcceptanceCriterion, text: str) -> CheckResult:
    pattern = str(criterion.check.get("pattern", ""))
    if not pattern:
        return CheckResult(criterion.ident, "regex", FAIL, "check has no 'pattern'")
    flags = 0 if criterion.check.get("case_sensitive") else re.IGNORECASE
    try:
        match = re.search(pattern, text, flags | re.MULTILINE)
    except re.error as error:
        return CheckResult(criterion.ident, "regex", FAIL, f"invalid pattern: {error}")
    if not match:
        return CheckResult(criterion.ident, "regex", FAIL, f"no match for /{pattern}/")
    return CheckResult(criterion.ident, "regex", PASS, f"matched /{pattern}/",
                       _snippet(text, match.start(), match.end()))


_NUMBER = r"[-+]?\d[\d\s.,']*(?:[eE][-+]?\d+)?"


def _parse_number(raw: str) -> float | None:
    # U+2212 is what a model writes when it means a minus sign, and float() refuses it.
    cleaned = raw.strip().replace(" ", "").replace("'", "").replace(chr(8722), "-")
    if cleaned.count(",") and cleaned.count("."):
        # 1.234,56 (it) vs 1,234.56 (en): the last separator is the decimal one.
        decimal = max(cleaned.rfind(","), cleaned.rfind("."))
        cleaned = re.sub(r"[.,]", "", cleaned[:decimal]) + "." + cleaned[decimal + 1:]
    elif cleaned.count(",") == 1 and len(cleaned.split(",")[1]) != 3:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _check_numeric(criterion: AcceptanceCriterion, text: str) -> CheckResult:
    check = criterion.check
    pattern = str(check.get("pattern", "")) or None
    if pattern:
        try:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        except re.error as error:
            return CheckResult(criterion.ident, "numeric", FAIL, f"invalid pattern: {error}")
        if not match:
            return CheckResult(criterion.ident, "numeric", FAIL, f"no match for /{pattern}/")
        raw = match.group(match.lastindex or 0)
        span = match.span(match.lastindex or 0)
    else:
        label = str(check.get("label", ""))
        if not label:
            return CheckResult(criterion.ident, "numeric", FAIL,
                               "numeric check needs 'pattern' or 'label'")
        found = re.search(re.escape(label) + r"\D{0,20}(" + _NUMBER + ")", text, re.IGNORECASE)
        if not found:
            return CheckResult(criterion.ident, "numeric", FAIL,
                               f"no number found after {label!r}")
        raw, span = found.group(1), found.span(1)

    value = _parse_number(raw)
    if value is None:
        return CheckResult(criterion.ident, "numeric", FAIL, f"{raw!r} is not a number")
    evidence = _snippet(text, *span)

    if "equals" in check:
        expected = float(check["equals"])
        tolerance = float(check.get("tolerance", 0))
        if abs(value - expected) <= tolerance:
            return CheckResult(criterion.ident, "numeric", PASS,
                               f"{value:g} equals {expected:g} (tolerance {tolerance:g})", evidence)
        return CheckResult(criterion.ident, "numeric", FAIL,
                           f"{value:g} differs from {expected:g} (tolerance {tolerance:g})", evidence)
    lower, upper = check.get("min"), check.get("max")
    if lower is not None and value < float(lower):
        return CheckResult(criterion.ident, "numeric", FAIL, f"{value:g} < {float(lower):g}", evidence)
    if upper is not None and value > float(upper):
        return CheckResult(criterion.ident, "numeric", FAIL, f"{value:g} > {float(upper):g}", evidence)
    if lower is None and upper is None:
        return CheckResult(criterion.ident, "numeric", FAIL,
                           "numeric check has neither 'equals' nor 'min'/'max'")
    return CheckResult(criterion.ident, "numeric", PASS, f"{value:g} within bounds", evidence)


def run_check(criterion: AcceptanceCriterion, text: str) -> CheckResult:
    kind = criterion.kind
    if kind == "human":
        return CheckResult(criterion.ident, "human", PENDING,
                           "richiede una verifica umana: nessun controllo automatico dichiarato")
    if kind == "contains":
        return _check_contains(criterion, text)
    if kind == "regex":
        return _check_regex(criterion, text)
    if kind == "numeric":
        return _check_numeric(criterion, text)
    return CheckResult(criterion.ident, kind, FAIL, f"unknown check kind {kind!r}")


def run_checks(criteria: Iterable[AcceptanceCriterion], text: str) -> list[CheckResult]:
    return [run_check(criterion, text) for criterion in criteria]


def checks_not_run(criteria: Iterable[AcceptanceCriterion], reason: str) -> list[CheckResult]:
    """What to record for a seat that produced no usable answer this round.

    Running the checks against the empty string would be arithmetic on nothing, and it
    reads in the report as a verdict on a model that did not speak.
    """
    return [CheckResult(criterion.ident, criterion.kind, ABSENT, reason)
            for criterion in criteria]


def all_verified(results: Iterable[CheckResult]) -> bool:
    """True only if every criterion has an automatic check and every one of them passed.

    An `absent` is not a pass: a criterion nobody was asked about this round is not a
    criterion met.
    """
    results = list(results)
    return bool(results) and all(result.status == PASS for result in results)
