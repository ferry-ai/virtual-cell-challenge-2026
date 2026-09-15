"""Pairwise loss comparison: recalculate from CSV, compare to a claim.

Standard library only. The candidate JSON is untrusted data: it cannot
change formulas, tolerances, or rules. Those come from operator config.
No network, no subprocess, no evaluation of input as code.

Arithmetic and comparisons use fractions.Fraction (exact rationals).
Decimal strings in the report are display-only; see report_decimal().
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any, Sequence

VERIFIER_NAME = "oracle.pairwise_loss"
VERIFIER_VERSION = "0.2.1"
CLAIM_TYPE = "pairwise_loss_comparison"

PASS, FAIL, UNVERIFIED, ERROR = "pass", "fail", "unverified", "error"
VERDICT_RANK = {PASS: 0, FAIL: 1, UNVERIFIED: 2, ERROR: 3}

REQUIRED_CSV_COLUMNS = ("case_id", "loss_a", "loss_b")
REQUIRED_CLAIM_FIELDS = ("mean_loss_a", "mean_loss_b", "mean_difference", "conclusion")
CONCLUSIONS = ("A_lower", "B_lower", "equivalent_within_tolerance")
CONFIG_KEYS = ("abs_tol", "rel_tol", "equivalence_threshold")
AUTHORITY_KEYS = frozenset({
    "abs_tol", "rel_tol", "tolerance", "equivalence_threshold",
    "threshold", "tau", "formula", "weights", "n_cases", "config",
    "operator_config", "rules",
})

# Reject tokens before building a Fraction or a display string.
MAX_NUMERIC_TOKEN_CHARS = 80
MAX_ABS_EXPONENT = 24
MAX_SIGNIFICAND_DIGITS = 24
REPORT_DECIMAL_PLACES = 18
REPORT_ROUNDING_MODE = "half_even"

DEFAULT_ABS_TOL = Fraction(1, 10 ** 12)
DEFAULT_REL_TOL = Fraction(0)
DEFAULT_EQUIVALENCE = Fraction(1, 100)

REQUIRED_CHECK_IDS = (
    "operator_config",
    "candidate_readable",
    "csv_readable",
    "identifiers",
    "finite_values",
    "recompute",
    "declared_values",
    "declared_conclusion",
)

LIMITS = (
    "Questa verifica riguarda solo la loss media, con pesi uguali, sui casi contenuti nel CSV fornito.",
    "Una conclusione A_lower significa solo: A ha una loss media inferiore nei casi forniti, oltre la soglia di equivalenza.",
    "Non significa: A generalizza meglio; A è statisticamente superiore; A è biologicamente più corretto; il protocollo di valutazione è valido.",
    "Non è stato eseguito alcun test statistico, né alcun controllo di causalità, leakage o qualità dei dati oltre i controlli strutturali elencati.",
    "Il JSON candidato è un dato non fidato: non può modificare formule, soglie o regole.",
    "Il calcolo e i confronti usano frazioni esatte. Le stringhe decimali del report sono solo visualizzazione.",
)

_NUMBER_TOKEN = re.compile(
    r"^([+-]?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$"
)


# --- small value types -------------------------------------------------------

@dataclass(frozen=True)
class JsonNumber:
    """Original JSON number token. Never converted to float."""
    token: str


@dataclass(frozen=True)
class CheckOutcome:
    id: str
    status: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.id, "status": self.status, "reason": self.reason}


@dataclass(frozen=True)
class OperatorConfig:
    abs_tol: Fraction
    rel_tol: Fraction
    equivalence_threshold: Fraction
    source: str  # "operator" | "defaults"


@dataclass(frozen=True)
class Claim:
    mean_loss_a: Fraction | None
    mean_loss_b: Fraction | None
    mean_difference: Fraction | None
    conclusion: str | None
    ignored_fields: tuple[str, ...]
    present: bool


@dataclass(frozen=True)
class CaseRow:
    case_id: str
    loss_a: Fraction
    loss_b: Fraction


@dataclass(frozen=True)
class Recomputed:
    n_cases: int
    mean_loss_a: Fraction
    mean_loss_b: Fraction
    mean_difference: Fraction
    conclusion: str


@dataclass
class Report:
    verdict: str
    checks: list[CheckOutcome]
    config: OperatorConfig | None = None
    claim: Claim | None = None
    recomputed: Recomputed | None = None
    n_cases: int | None = None
    ignored_candidate_fields: tuple[str, ...] = ()
    value_comparisons: list[dict[str, str]] = field(default_factory=list)
    conclusion_comparison: dict[str, str] | None = None
    inputs: dict[str, str | None] = field(default_factory=dict)
    error_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        declared = None
        if self.claim is not None and self.claim.present:
            declared = {
                "mean_loss_a": _num(self.claim.mean_loss_a),
                "mean_loss_b": _num(self.claim.mean_loss_b),
                "mean_difference": _num(self.claim.mean_difference),
                "mean_loss_a_exact": _exact(self.claim.mean_loss_a),
                "mean_loss_b_exact": _exact(self.claim.mean_loss_b),
                "mean_difference_exact": _exact(self.claim.mean_difference),
                "conclusion": self.claim.conclusion,
            }
        recomputed = None
        if self.recomputed is not None:
            recomputed = {
                "mean_loss_a": report_decimal(self.recomputed.mean_loss_a),
                "mean_loss_b": report_decimal(self.recomputed.mean_loss_b),
                "mean_difference": report_decimal(self.recomputed.mean_difference),
                "mean_loss_a_exact": exact_str(self.recomputed.mean_loss_a),
                "mean_loss_b_exact": exact_str(self.recomputed.mean_loss_b),
                "mean_difference_exact": exact_str(self.recomputed.mean_difference),
                "conclusion": self.recomputed.conclusion,
            }
        config_used = None
        if self.config is not None:
            config_used = {
                "abs_tol": report_decimal(self.config.abs_tol),
                "rel_tol": report_decimal(self.config.rel_tol),
                "equivalence_threshold": report_decimal(self.config.equivalence_threshold),
                "abs_tol_exact": exact_str(self.config.abs_tol),
                "rel_tol_exact": exact_str(self.config.rel_tol),
                "equivalence_threshold_exact": exact_str(self.config.equivalence_threshold),
                "source": self.config.source,
            }
        return {
            "verifier": {
                "name": VERIFIER_NAME,
                "version": VERIFIER_VERSION,
                "claim_type": CLAIM_TYPE,
            },
            "verdict": self.verdict,
            "checks": [c.as_dict() for c in self.checks],
            "n_cases": self.n_cases,
            "declared": declared,
            "recomputed": recomputed,
            "value_comparisons": self.value_comparisons,
            "conclusion_comparison": self.conclusion_comparison,
            "config_used": config_used,
            "report_rounding": {
                "mode": REPORT_ROUNDING_MODE,
                "max_places": REPORT_DECIMAL_PLACES,
                "used_for": (
                    "stringhe decimali di visualizzazione; "
                    "calcolo e confronti restano su frazioni esatte"
                ),
            },
            "numeric_limits": {
                "max_token_chars": MAX_NUMERIC_TOKEN_CHARS,
                "max_abs_exponent": MAX_ABS_EXPONENT,
                "max_significand_digits": MAX_SIGNIFICAND_DIGITS,
            },
            "ignored_candidate_fields": list(self.ignored_candidate_fields),
            "inputs": self.inputs,
            "limits": list(LIMITS),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n"

    def summary_text(self) -> str:
        return render_summary(self)


# --- exact arithmetic and display rounding -----------------------------------

def exact_str(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _terminating_decimal_places(value: Fraction) -> int | None:
    """Places needed for an exact finite decimal, or None if repeating."""
    den = value.denominator
    while den % 2 == 0:
        den //= 2
    twos_removed = value.denominator // den if den else value.denominator
    fives = den
    places_fives = 0
    while fives % 5 == 0:
        fives //= 5
        places_fives += 1
    if fives != 1:
        return None
    places_twos = 0
    t = twos_removed
    while t % 2 == 0:
        t //= 2
        places_twos += 1
    return max(places_twos, places_fives, 1)


def _round_half_even(value: Fraction, places: int) -> Fraction:
    scale = 10 ** places
    scaled = value * scale
    sign = 1 if scaled >= 0 else -1
    abs_scaled = abs(scaled)
    whole = abs_scaled.numerator // abs_scaled.denominator
    remainder = Fraction(abs_scaled.numerator % abs_scaled.denominator,
                         abs_scaled.denominator)
    half = Fraction(1, 2)
    if remainder > half or (remainder == half and whole % 2 == 1):
        whole += 1
    return Fraction(sign * whole, scale)


def report_decimal(value: Fraction) -> str:
    """Display string. Never used for comparisons or conclusions.

    Terminating rationals are written exactly (at least one decimal digit).
    Repeating rationals are rounded half-even to REPORT_DECIMAL_PLACES.
    Scientific notation is never used. The expansion is bounded by
    REPORT_DECIMAL_PLACES so a large exponent cannot inflate the string.
    """
    places = _terminating_decimal_places(value)
    shown = value if places is not None else _round_half_even(value, REPORT_DECIMAL_PLACES)
    if places is None:
        places = REPORT_DECIMAL_PLACES
    sign = "-" if shown < 0 else ""
    shown = abs(shown)
    scale = 10 ** places
    integer = shown.numerator * scale // shown.denominator
    int_part = integer // scale
    frac_part = integer % scale
    frac = f"{frac_part:0{places}d}".rstrip("0")
    if not frac:
        frac = "0"
    return f"{sign}{int_part}.{frac}"


def _num(value: Fraction | None) -> str | None:
    return None if value is None else report_decimal(value)


def _exact(value: Fraction | None) -> str | None:
    return None if value is None else exact_str(value)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def matches(declared: Fraction, recomputed: Fraction,
            abs_tol: Fraction, rel_tol: Fraction) -> bool:
    error = abs(declared - recomputed)
    budget = abs_tol + rel_tol * abs(recomputed)
    return error <= budget


def derived_conclusion(delta: Fraction, tau: Fraction) -> str:
    if abs(delta) <= tau:
        return "equivalent_within_tolerance"
    if delta < 0:
        return "A_lower"
    return "B_lower"


def overall_verdict(checks: Sequence[CheckOutcome]) -> str:
    by_id = {c.id: c for c in checks}
    missing = [cid for cid in REQUIRED_CHECK_IDS if cid not in by_id]
    if missing:
        return ERROR
    worst = PASS
    for check in checks:
        if VERDICT_RANK[check.status] > VERDICT_RANK[worst]:
            worst = check.status
    if worst != PASS:
        return worst
    for cid in REQUIRED_CHECK_IDS:
        if by_id[cid].status != PASS:
            return by_id[cid].status
    return PASS


# --- parsing helpers ---------------------------------------------------------

def parse_numeric_token(raw: str, what: str) -> tuple[Fraction | None, str | None]:
    """Parse a number after checking size limits. Does not build huge values."""
    text = raw.strip()
    if text == "":
        return None, f"{what}: cella vuota"
    if len(text) > MAX_NUMERIC_TOKEN_CHARS:
        return None, (
            f"{what}: token numerico troppo lungo "
            f"({len(text)} caratteri, max {MAX_NUMERIC_TOKEN_CHARS})"
        )
    lowered = text.lower()
    if lowered in {"nan", "+nan", "-nan", "inf", "+inf", "-inf",
                   "infinity", "+infinity", "-infinity"}:
        return None, f"{what}: valore non finito {text!r}"
    if "," in text:
        return None, (
            f"{what}: separatore decimale non ammesso in {text!r}; "
            "si usa il punto"
        )
    match = _NUMBER_TOKEN.match(text)
    if not match:
        return None, f"{what}: non è un numero: {text!r}"
    sign, intpart, fracpart, exp = match.groups()
    fracpart = fracpart or ""
    digits = intpart + fracpart
    significand_digits = (digits.lstrip("0") or "0")
    if len(significand_digits) > MAX_SIGNIFICAND_DIGITS:
        return None, (
            f"{what}: troppe cifre significative "
            f"({len(significand_digits)}, max {MAX_SIGNIFICAND_DIGITS})"
        )
    exponent = int(exp) if exp is not None else 0
    if abs(exponent) > MAX_ABS_EXPONENT:
        return None, (
            f"{what}: esponente {exponent} oltre il limite ±{MAX_ABS_EXPONENT}"
        )
    scale = exponent - len(fracpart)
    if abs(scale) > MAX_ABS_EXPONENT + MAX_SIGNIFICAND_DIGITS:
        return None, f"{what}: scala {scale} oltre il limite"
    significand = int(digits) if digits else 0
    if sign == "-":
        significand = -significand
    if scale >= 0:
        value = Fraction(significand * (10 ** scale), 1)
    else:
        value = Fraction(significand, 10 ** (-scale))
    return value, None


def _json_number(value: Any, what: str) -> tuple[Fraction | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, JsonNumber):
        return parse_numeric_token(value.token, what)
    if isinstance(value, bool):
        return None, f"{what}: tipo non numerico (bool)"
    if isinstance(value, str):
        return None, f"{what}: tipo non numerico (str)"
    return None, f"{what}: tipo non numerico ({type(value).__name__})"


def _load_json_bytes(data: bytes, label: str) -> tuple[Any | None, str | None]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, f"{label}: non è UTF-8 ({exc})"
    try:
        return json.loads(
            text,
            parse_float=JsonNumber,
            parse_int=JsonNumber,
            parse_constant=JsonNumber,
        ), None
    except json.JSONDecodeError as exc:
        return None, f"{label}: JSON non valido ({exc})"


def _read_file(path: Path) -> tuple[bytes | None, str | None]:
    try:
        return path.read_bytes(), None
    except OSError as exc:
        return None, f"lettura fallita: {exc}"


# --- config / claim / csv ----------------------------------------------------

def parse_operator_config(obj: Any, source: str) -> tuple[OperatorConfig | None, str | None]:
    if not isinstance(obj, dict):
        return None, "la configurazione deve essere un oggetto JSON"
    unknown = sorted(k for k in obj if k not in CONFIG_KEYS)
    if unknown:
        return None, f"chiavi di configurazione sconosciute: {', '.join(unknown)}"

    values: dict[str, Fraction] = {
        "abs_tol": DEFAULT_ABS_TOL,
        "rel_tol": DEFAULT_REL_TOL,
        "equivalence_threshold": DEFAULT_EQUIVALENCE,
    }
    for key in CONFIG_KEYS:
        if key not in obj:
            continue
        parsed, err = _json_number(obj[key], key)
        if err:
            return None, err
        if parsed is None:
            return None, f"{key}: manca"
        if parsed < 0:
            return None, f"{key}: deve essere ≥ 0, trovato {report_decimal(parsed)}"
        values[key] = parsed
    return OperatorConfig(
        abs_tol=values["abs_tol"],
        rel_tol=values["rel_tol"],
        equivalence_threshold=values["equivalence_threshold"],
        source=source,
    ), None


def default_config() -> OperatorConfig:
    return OperatorConfig(
        abs_tol=DEFAULT_ABS_TOL,
        rel_tol=DEFAULT_REL_TOL,
        equivalence_threshold=DEFAULT_EQUIVALENCE,
        source="defaults",
    )


def parse_claim(obj: Any) -> tuple[Claim | None, str | None, str | None]:
    """Return (claim, error_reason, unverified_reason). At most one of the last two."""
    if not isinstance(obj, dict):
        return None, "il candidato deve essere un oggetto JSON", None

    ignored = tuple(sorted(k for k in obj if k not in REQUIRED_CLAIM_FIELDS
                           and k != "claim_type"))
    if "claim_type" in obj and obj["claim_type"] != CLAIM_TYPE:
        return None, (
            f"claim_type {obj['claim_type']!r} non è {CLAIM_TYPE!r}"
        ), None

    missing = [k for k in REQUIRED_CLAIM_FIELDS if k not in obj or obj[k] is None]
    numbers: dict[str, Fraction | None] = {}
    for key in ("mean_loss_a", "mean_loss_b", "mean_difference"):
        if key in missing:
            numbers[key] = None
            continue
        parsed, err = _json_number(obj[key], key)
        if err:
            return None, err, None
        numbers[key] = parsed

    conclusion: str | None = None
    if "conclusion" not in missing:
        raw = obj["conclusion"]
        if not isinstance(raw, str):
            return None, f"conclusion: tipo non stringa ({type(raw).__name__})", None
        if raw not in CONCLUSIONS:
            return None, (
                f"conclusion {raw!r} non è una di {', '.join(CONCLUSIONS)}"
            ), None
        conclusion = raw

    claim = Claim(
        mean_loss_a=numbers["mean_loss_a"],
        mean_loss_b=numbers["mean_loss_b"],
        mean_difference=numbers["mean_difference"],
        conclusion=conclusion,
        ignored_fields=ignored,
        present=True,
    )
    if missing:
        return claim, None, f"campi dell'affermazione mancanti: {', '.join(missing)}"
    return claim, None, None


def parse_csv(data: bytes) -> tuple[list[CaseRow] | None, int | None,
                                    CheckOutcome | None, CheckOutcome | None,
                                    CheckOutcome | None]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        readable = CheckOutcome("csv_readable", ERROR, f"CSV non è UTF-8 ({exc})")
        return None, None, readable, None, None
    if text.strip() == "":
        readable = CheckOutcome("csv_readable", ERROR, "CSV vuoto")
        return None, 0, readable, None, None

    try:
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = reader.fieldnames
    except csv.Error as exc:
        readable = CheckOutcome(
            "csv_readable", ERROR, f"CSV non parsabile ({exc})",
        )
        return None, None, readable, None, None
    if fieldnames is None:
        readable = CheckOutcome("csv_readable", ERROR, "CSV senza intestazione")
        return None, None, readable, None, None
    fields = [name.strip() if name else "" for name in fieldnames]
    if any(name == "" for name in fields):
        readable = CheckOutcome("csv_readable", ERROR, "intestazione con colonna vuota")
        return None, None, readable, None, None
    seen_headers: dict[str, int] = {}
    duplicates = []
    for name in fields:
        if name in seen_headers and name not in duplicates:
            duplicates.append(name)
        seen_headers[name] = seen_headers.get(name, 0) + 1
    if duplicates:
        readable = CheckOutcome(
            "csv_readable", ERROR,
            "intestazioni duplicate: " + ", ".join(duplicates),
        )
        return None, None, readable, None, None
    reader.fieldnames = fields
    missing = [c for c in REQUIRED_CSV_COLUMNS if c not in fields]
    if missing:
        readable = CheckOutcome(
            "csv_readable", ERROR,
            f"colonne obbligatorie mancanti: {', '.join(missing)}",
        )
        return None, None, readable, None, None

    rows: list[CaseRow] = []
    seen: dict[str, int] = {}
    id_errors: list[str] = []
    value_errors: list[str] = []
    n_data = 0
    try:
        for index, raw in enumerate(reader, start=2):
            n_data += 1
            case_id = (raw.get("case_id") or "").strip()
            if case_id == "":
                id_errors.append(f"riga {index}: case_id vuoto")
            elif case_id in seen:
                id_errors.append(
                    f"riga {index}: case_id duplicato {case_id!r} "
                    f"(prima alla riga {seen[case_id]})"
                )
            else:
                seen[case_id] = index

            loss_a, err_a = parse_numeric_token(
                raw.get("loss_a") or "", f"riga {index} loss_a",
            )
            loss_b, err_b = parse_numeric_token(
                raw.get("loss_b") or "", f"riga {index} loss_b",
            )
            if err_a:
                value_errors.append(err_a)
            if err_b:
                value_errors.append(err_b)
            if loss_a is not None and loss_b is not None:
                rows.append(CaseRow(case_id, loss_a, loss_b))
    except csv.Error as exc:
        readable = CheckOutcome(
            "csv_readable", ERROR, f"CSV non parsabile ({exc})",
        )
        return None, None, readable, None, None

    if n_data == 0:
        readable = CheckOutcome(
            "csv_readable", ERROR, "CSV senza righe di dati",
        )
        return None, 0, readable, None, None

    readable = CheckOutcome(
        "csv_readable", PASS,
        f"CSV leggibile, {n_data} righe, colonne {', '.join(REQUIRED_CSV_COLUMNS)}",
    )
    if id_errors:
        identifiers = CheckOutcome("identifiers", ERROR, "; ".join(id_errors))
    else:
        identifiers = CheckOutcome(
            "identifiers", PASS, f"{n_data} identificativi non vuoti e univoci",
        )
    if value_errors:
        finite = CheckOutcome("finite_values", ERROR, "; ".join(value_errors))
    else:
        finite = CheckOutcome(
            "finite_values", PASS, f"{n_data} coppie di loss finite",
        )
    usable = identifiers.status == PASS and finite.status == PASS
    return (rows if usable else None), n_data, readable, identifiers, finite


def recompute(rows: Sequence[CaseRow], tau: Fraction) -> tuple[Recomputed | None, str | None]:
    n = len(rows)
    if n == 0:
        return None, "nessun caso da ricalcolare"
    n_frac = Fraction(n)
    sum_a = sum((row.loss_a for row in rows), Fraction(0))
    sum_b = sum((row.loss_b for row in rows), Fraction(0))
    sum_d = sum((row.loss_a - row.loss_b for row in rows), Fraction(0))
    mean_a = sum_a / n_frac
    mean_b = sum_b / n_frac
    delta = sum_d / n_frac
    delta_from_means = mean_a - mean_b
    if delta != delta_from_means:
        return None, (
            f"errore interno: mean(loss_a-loss_b)={exact_str(delta)} "
            f"diverso da mean_a-mean_b={exact_str(delta_from_means)}"
        )
    return Recomputed(
        n_cases=n,
        mean_loss_a=mean_a,
        mean_loss_b=mean_b,
        mean_difference=delta,
        conclusion=derived_conclusion(delta, tau),
    ), None


def _skipped(check_id: str, reason: str) -> CheckOutcome:
    return CheckOutcome(check_id, UNVERIFIED, reason)


# --- verification ------------------------------------------------------------

def verify_bytes(
    csv_bytes: bytes | None,
    candidate_bytes: bytes | None,
    config_bytes: bytes | None,
    *,
    csv_path: str | None = None,
    candidate_path: str | None = None,
    config_path: str | None = None,
    csv_missing: bool = False,
    candidate_missing: bool = False,
    config_missing: bool = False,
    config_requested: bool = False,
) -> Report:
    try:
        return _verify_bytes_inner(
            csv_bytes, candidate_bytes, config_bytes,
            csv_path=csv_path, candidate_path=candidate_path, config_path=config_path,
            csv_missing=csv_missing, candidate_missing=candidate_missing,
            config_missing=config_missing, config_requested=config_requested,
        )
    except (OverflowError, MemoryError, ValueError) as exc:
        checks = [
            CheckOutcome("operator_config", ERROR, f"overflow o valore non rappresentabile: {exc}"),
            _skipped("candidate_readable", "non eseguito: overflow"),
            _skipped("csv_readable", "non eseguito: overflow"),
            _skipped("identifiers", "non eseguito: overflow"),
            _skipped("finite_values", "non eseguito: overflow"),
            _skipped("recompute", "non eseguito: overflow"),
            _skipped("declared_values", "non eseguito: overflow"),
            _skipped("declared_conclusion", "non eseguito: overflow"),
        ]
        return Report(verdict=ERROR, checks=checks, error_note=str(exc))


def _verify_bytes_inner(
    csv_bytes: bytes | None,
    candidate_bytes: bytes | None,
    config_bytes: bytes | None,
    *,
    csv_path: str | None,
    candidate_path: str | None,
    config_path: str | None,
    csv_missing: bool,
    candidate_missing: bool,
    config_missing: bool,
    config_requested: bool,
) -> Report:
    checks: list[CheckOutcome] = []
    inputs: dict[str, str | None] = {
        "csv_path": csv_path,
        "csv_sha256": sha256_hex(csv_bytes) if csv_bytes is not None else None,
        "candidate_path": candidate_path,
        "candidate_sha256": sha256_hex(candidate_bytes) if candidate_bytes is not None else None,
        "config_path": config_path,
        "config_sha256": sha256_hex(config_bytes) if config_bytes is not None else None,
    }

    config: OperatorConfig | None = None
    if config_missing and config_requested:
        checks.append(CheckOutcome(
            "operator_config", UNVERIFIED,
            "file di configurazione dell'operatore assente",
        ))
    elif config_bytes is None and not config_requested:
        config = default_config()
        checks.append(CheckOutcome(
            "operator_config", PASS,
            "configurazione predefinita (nessun file operatore)",
        ))
    elif config_bytes is None:
        checks.append(CheckOutcome(
            "operator_config", ERROR, "configurazione non letta",
        ))
    else:
        obj, err = _load_json_bytes(config_bytes, "configurazione")
        if err:
            checks.append(CheckOutcome("operator_config", ERROR, err))
        else:
            config, err = parse_operator_config(obj, "operator")
            if err:
                checks.append(CheckOutcome("operator_config", ERROR, err))
            else:
                checks.append(CheckOutcome(
                    "operator_config", PASS,
                    "configurazione operatore accettata",
                ))

    claim: Claim | None = None
    if candidate_missing:
        checks.append(CheckOutcome(
            "candidate_readable", UNVERIFIED, "file candidato assente",
        ))
    elif candidate_bytes is None:
        checks.append(CheckOutcome(
            "candidate_readable", ERROR, "candidato non letto",
        ))
    else:
        obj, err = _load_json_bytes(candidate_bytes, "candidato")
        if err:
            checks.append(CheckOutcome("candidate_readable", ERROR, err))
        else:
            claim, err, unverified = parse_claim(obj)
            if err:
                checks.append(CheckOutcome("candidate_readable", ERROR, err))
            elif unverified:
                checks.append(CheckOutcome("candidate_readable", UNVERIFIED, unverified))
            else:
                checks.append(CheckOutcome(
                    "candidate_readable", PASS, "affermazione candidato leggibile",
                ))

    rows = None
    n_cases: int | None = None
    if csv_missing:
        checks.append(CheckOutcome("csv_readable", UNVERIFIED, "file CSV assente"))
        checks.append(_skipped("identifiers", "non eseguito: CSV assente"))
        checks.append(_skipped("finite_values", "non eseguito: CSV assente"))
    elif csv_bytes is None:
        checks.append(CheckOutcome("csv_readable", ERROR, "CSV non letto"))
        checks.append(_skipped("identifiers", "non eseguito: CSV non letto"))
        checks.append(_skipped("finite_values", "non eseguito: CSV non letto"))
    else:
        rows, n_cases, readable, identifiers, finite = parse_csv(csv_bytes)
        assert readable is not None
        checks.append(readable)
        if identifiers is None:
            checks.append(_skipped(
                "identifiers",
                f"non eseguito: {readable.reason}",
            ))
        else:
            checks.append(identifiers)
        if finite is None:
            checks.append(_skipped(
                "finite_values",
                f"non eseguito: {readable.reason}",
            ))
        else:
            checks.append(finite)

    recomputed: Recomputed | None = None
    structural_ok = (
        rows is not None
        and config is not None
        and all(c.status == PASS
                for c in checks if c.id in {"identifiers", "finite_values", "csv_readable"})
    )
    if not structural_ok or config is None or rows is None:
        checks.append(_skipped(
            "recompute",
            "non eseguito: i controlli strutturali sul CSV non sono tutti passati",
        ))
    else:
        recomputed, err = recompute(rows, config.equivalence_threshold)
        if err:
            checks.append(CheckOutcome("recompute", ERROR, err))
            recomputed = None
        else:
            checks.append(CheckOutcome(
                "recompute", PASS,
                f"ricalcolate medie e differenza su {recomputed.n_cases} casi",
            ))

    value_comparisons: list[dict[str, str]] = []
    conclusion_comparison: dict[str, str] | None = None
    ignored = claim.ignored_fields if claim is not None else ()

    can_compare_values = (
        recomputed is not None
        and claim is not None
        and claim.mean_loss_a is not None
        and claim.mean_loss_b is not None
        and claim.mean_difference is not None
        and config is not None
    )
    if not can_compare_values:
        checks.append(_skipped(
            "declared_values",
            "non eseguito: manca il ricalcolo oppure un valore dichiarato",
        ))
    else:
        assert recomputed is not None and claim is not None and config is not None
        pairs = (
            ("mean_loss_a", claim.mean_loss_a, recomputed.mean_loss_a),
            ("mean_loss_b", claim.mean_loss_b, recomputed.mean_loss_b),
            ("mean_difference", claim.mean_difference, recomputed.mean_difference),
        )
        mismatches: list[str] = []
        for name, declared, star in pairs:
            ok = matches(declared, star, config.abs_tol, config.rel_tol)
            abs_err = abs(declared - star)
            value_comparisons.append({
                "name": name,
                "declared": report_decimal(declared),
                "declared_exact": exact_str(declared),
                "recomputed": report_decimal(star),
                "recomputed_exact": exact_str(star),
                "abs_error": report_decimal(abs_err),
                "abs_error_exact": exact_str(abs_err),
                "status": PASS if ok else FAIL,
            })
            if not ok:
                mismatches.append(
                    f"{name}: dichiarato {report_decimal(declared)}, "
                    f"ricalcolato {report_decimal(star)}"
                )
        if mismatches:
            checks.append(CheckOutcome(
                "declared_values", FAIL, "; ".join(mismatches),
            ))
        else:
            checks.append(CheckOutcome(
                "declared_values", PASS,
                "i tre valori dichiarati coincidono col ricalcolo entro le tolleranze",
            ))

    can_compare_conclusion = (
        recomputed is not None
        and claim is not None
        and claim.conclusion is not None
        and config is not None
    )
    if not can_compare_conclusion:
        checks.append(_skipped(
            "declared_conclusion",
            "non eseguito: manca il ricalcolo oppure la conclusione dichiarata",
        ))
    else:
        assert recomputed is not None and claim is not None and config is not None
        ok = claim.conclusion == recomputed.conclusion
        conclusion_comparison = {
            "declared": claim.conclusion or "",
            "recomputed": recomputed.conclusion,
            "equivalence_threshold": report_decimal(config.equivalence_threshold),
            "equivalence_threshold_exact": exact_str(config.equivalence_threshold),
            "abs_delta": report_decimal(abs(recomputed.mean_difference)),
            "abs_delta_exact": exact_str(abs(recomputed.mean_difference)),
            "status": PASS if ok else FAIL,
        }
        if ok:
            checks.append(CheckOutcome(
                "declared_conclusion", PASS,
                f"conclusione {claim.conclusion} coerente col ricalcolo "
                f"(|delta|={report_decimal(abs(recomputed.mean_difference))}, "
                f"soglia={report_decimal(config.equivalence_threshold)})",
            ))
        else:
            checks.append(CheckOutcome(
                "declared_conclusion", FAIL,
                f"dichiarata {claim.conclusion}, ricalcolata {recomputed.conclusion} "
                f"(|delta|={report_decimal(abs(recomputed.mean_difference))}, "
                f"soglia={report_decimal(config.equivalence_threshold)})",
            ))

    return Report(
        verdict=overall_verdict(checks),
        checks=checks,
        config=config,
        claim=claim,
        recomputed=recomputed,
        n_cases=n_cases if recomputed is None else recomputed.n_cases,
        ignored_candidate_fields=ignored,
        value_comparisons=value_comparisons,
        conclusion_comparison=conclusion_comparison,
        inputs=inputs,
    )


def verify_paths(
    csv_path: Path | str,
    candidate_path: Path | str,
    config_path: Path | str | None = None,
) -> Report:
    csv_path = Path(csv_path)
    candidate_path = Path(candidate_path)
    config_p = Path(config_path) if config_path is not None else None

    csv_missing = not csv_path.is_file()
    cand_missing = not candidate_path.is_file()
    cfg_missing = bool(config_p is not None and not config_p.is_file())

    csv_bytes = None if csv_missing else _read_file(csv_path)[0]
    cand_bytes = None if cand_missing else _read_file(candidate_path)[0]
    cfg_bytes = None
    cfg_read_error = None
    if config_p is not None and not cfg_missing:
        cfg_bytes, cfg_read_error = _read_file(config_p)

    report = verify_bytes(
        csv_bytes,
        cand_bytes,
        cfg_bytes,
        csv_path=str(csv_path),
        candidate_path=str(candidate_path),
        config_path=str(config_p) if config_p is not None else None,
        csv_missing=csv_missing,
        candidate_missing=cand_missing,
        config_missing=cfg_missing,
        config_requested=config_p is not None,
    )
    if cfg_read_error and not cfg_missing:
        patched = []
        for check in report.checks:
            if check.id == "operator_config" and check.status == ERROR:
                patched.append(CheckOutcome("operator_config", ERROR, cfg_read_error))
            else:
                patched.append(check)
        report.checks = patched
        report.verdict = overall_verdict(patched)
    return report


def render_summary(report: Report) -> str:
    lines = [
        f"Oracolo {VERIFIER_NAME} {VERIFIER_VERSION}",
        f"Esito complessivo: {report.verdict.upper()}",
        f"Casi: {report.n_cases if report.n_cases is not None else 'n/d'}",
        "",
        "Controlli:",
    ]
    for check in report.checks:
        lines.append(f"  - {check.id}: {check.status} — {check.reason}")
    lines.append("")
    if report.config is not None:
        lines.append(
            "Tolleranze e soglia "
            f"(fonte: {report.config.source}): "
            f"abs_tol={report_decimal(report.config.abs_tol)}, "
            f"rel_tol={report_decimal(report.config.rel_tol)}, "
            f"equivalence_threshold={report_decimal(report.config.equivalence_threshold)}"
        )
        lines.append(
            "Arrotondamento del report: "
            f"{REPORT_ROUNDING_MODE}, max {REPORT_DECIMAL_PLACES} decimali "
            "(solo visualizzazione; i confronti sono su frazioni esatte)."
        )
    if report.ignored_candidate_fields:
        lines.append(
            "Chiavi candidato ignorate: "
            + ", ".join(report.ignored_candidate_fields)
        )
    if report.claim is not None and report.claim.present:
        lines.append("Valori dichiarati:")
        lines.append(f"  mean_loss_a={_num(report.claim.mean_loss_a)}")
        lines.append(f"  mean_loss_b={_num(report.claim.mean_loss_b)}")
        lines.append(f"  mean_difference={_num(report.claim.mean_difference)}")
        lines.append(f"  conclusion={report.claim.conclusion}")
    if report.recomputed is not None:
        lines.append("Valori ricalcolati:")
        lines.append(
            f"  mean_loss_a={report_decimal(report.recomputed.mean_loss_a)} "
            f"({exact_str(report.recomputed.mean_loss_a)})"
        )
        lines.append(
            f"  mean_loss_b={report_decimal(report.recomputed.mean_loss_b)} "
            f"({exact_str(report.recomputed.mean_loss_b)})"
        )
        lines.append(
            f"  mean_difference={report_decimal(report.recomputed.mean_difference)} "
            f"({exact_str(report.recomputed.mean_difference)})"
        )
        lines.append(f"  conclusion={report.recomputed.conclusion}")
    lines.append("")
    lines.append("Hash SHA-256 degli input letti:")
    for key in ("csv_sha256", "candidate_sha256", "config_sha256"):
        lines.append(f"  {key}: {report.inputs.get(key) or 'n/d'}")
    lines.append("")
    lines.append("Limiti della verifica:")
    for limit in LIMITS:
        lines.append(f"  - {limit}")
    lines.append("")
    return "\n".join(lines)
