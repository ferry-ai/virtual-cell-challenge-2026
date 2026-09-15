"""The incarico: the only thing the operator hands to the system, and its versioning.

A brief carries the question, the context, the materials, the expected result and the
acceptance criteria. Two properties matter beyond holding those fields:

* **It is versioned by content.** The engine records the hash of every registered
  version; editing a brief without bumping its version is refused, so results produced
  under an older wording stay recognisable as such.
* **It bounds what leaves the machine.** A material is sent to an external chat only if
  its path sits inside the brief's own directory or a root the operator listed
  explicitly. The default therefore sends project files nowhere.
* **It declares which kind of campaign it is.** `mode: debug` (the default, and what
  every brief written before this field meant) runs the proposal-and-critique loop;
  `mode: scientific_research` runs the three-phase research loop, which reads its own
  `research:` block. A brief that names no mode behaves exactly as it always did.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .util import load_document, sha256_bytes, sha256_text, slugify

MAX_MATERIAL_BYTES = 200_000
CHECK_KINDS = ("human", "contains", "regex", "numeric")
MODES = ("debug", "scientific_research")


class BriefError(ValueError):
    """The brief is malformed, or asks for something the guards refuse."""


@dataclass(frozen=True)
class AcceptanceCriterion:
    """One statement that must hold, and how the engine can tell whether it does."""

    ident: str
    text: str
    check: dict[str, Any]

    @property
    def kind(self) -> str:
        return str(self.check.get("kind", "human"))

    @property
    def is_automatic(self) -> bool:
        return self.kind != "human"


@dataclass(frozen=True)
class Material:
    """A file the operator chose to include, with the bytes actually read."""

    ident: str
    path: Path
    sha256: str
    size_bytes: int
    text: str


@dataclass(frozen=True)
class Subtask:
    """A unit of the solve loop. Predeclared here, or proposed by the framing stage."""

    ident: str
    title: str
    question: str
    route: str | None = None
    criteria: tuple[str, ...] = ()          # ids of acceptance criteria it must satisfy
    origin: str = "brief"                   # brief | frame | operator


@dataclass(frozen=True)
class Brief:
    brief_id: str
    version: int
    title: str
    question: str
    context: str
    expected_result: str
    acceptance_criteria: tuple[AcceptanceCriterion, ...]
    materials: tuple[Material, ...]
    subtasks: tuple[Subtask, ...]
    route: str
    limits: dict[str, Any]
    source_path: Path
    content_sha256: str
    mode: str = "debug"
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    def criterion(self, ident: str) -> AcceptanceCriterion | None:
        for criterion in self.acceptance_criteria:
            if criterion.ident == ident:
                return criterion
        return None


def _require(document: dict, key: str, path: Path) -> Any:
    if key not in document or document[key] in (None, ""):
        raise BriefError(f"{path}: missing required field {key!r}")
    return document[key]


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolve_material(entry: Any, *, brief_dir: Path, allowed_roots: tuple[Path, ...],
                      index: int) -> Material:
    if isinstance(entry, str):
        entry = {"path": entry}
    if not isinstance(entry, dict) or "path" not in entry:
        raise BriefError(f"material #{index}: expected a path or a mapping with 'path'")
    path = Path(entry["path"])
    path = (brief_dir / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_file():
        raise BriefError(f"material {path} does not exist")

    permitted = (brief_dir.resolve(), *allowed_roots)
    if not any(_is_within(path, root) for root in permitted):
        raise BriefError(
            f"material {path} is outside every allowed root. Materials are sent to "
            f"external chats: add its directory to outbound.allowed_roots on purpose, "
            f"or move the file next to the brief. Allowed now: "
            + ", ".join(str(root) for root in permitted)
        )
    data = path.read_bytes()
    if len(data) > MAX_MATERIAL_BYTES:
        raise BriefError(
            f"material {path} is {len(data)} bytes, over the {MAX_MATERIAL_BYTES} limit; "
            f"extract the part that matters instead of sending the whole file"
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BriefError(f"material {path} is not UTF-8 text") from error
    return Material(
        ident=str(entry.get("id") or f"M{index + 1}"),
        path=path, sha256=sha256_bytes(data), size_bytes=len(data), text=text,
    )


def _parse_criteria(raw: Any, path: Path, *, required: bool = True
                    ) -> tuple[AcceptanceCriterion, ...]:
    """Parse the acceptance criteria. Required, except in research mode.

    A research brief states *relevance* criteria instead -- what makes a source count --
    which is a different question from when an answer is accepted. Demanding both would
    get one of them filled in to satisfy the loader, and a criterion written to satisfy a
    loader is worse than no criterion.
    """
    if raw in (None, []) and not required:
        return ()
    if not isinstance(raw, list) or not raw:
        raise BriefError(f"{path}: acceptance_criteria must be a non-empty list")
    criteria: list[AcceptanceCriterion] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw):
        if isinstance(entry, str):
            entry = {"text": entry}
        if not isinstance(entry, dict) or not entry.get("text"):
            raise BriefError(f"{path}: acceptance criterion #{index} has no text")
        ident = str(entry.get("id") or f"C{index + 1}")
        if ident in seen:
            raise BriefError(f"{path}: duplicate acceptance criterion id {ident!r}")
        seen.add(ident)
        check = entry.get("check") or {"kind": "human"}
        if not isinstance(check, dict):
            raise BriefError(f"{path}: check for {ident} must be a mapping")
        kind = str(check.get("kind", "human"))
        if kind not in CHECK_KINDS:
            raise BriefError(f"{path}: check kind {kind!r} for {ident} not in {CHECK_KINDS}")
        criteria.append(AcceptanceCriterion(ident=ident, text=str(entry["text"]), check=check))
    return tuple(criteria)


def _parse_subtasks(raw: Any, path: Path) -> tuple[Subtask, ...]:
    if raw in (None, []):
        return ()
    if not isinstance(raw, list):
        raise BriefError(f"{path}: subtasks must be a list")
    subtasks: list[Subtask] = []
    for index, entry in enumerate(raw):
        if isinstance(entry, str):
            entry = {"title": entry, "question": entry}
        if not isinstance(entry, dict) or not entry.get("title"):
            raise BriefError(f"{path}: subtask #{index} has no title")
        subtasks.append(Subtask(
            ident=str(entry.get("id") or f"S{index + 1}"),
            title=str(entry["title"]),
            question=str(entry.get("question") or entry["title"]),
            route=entry.get("route"),
            criteria=tuple(str(item) for item in entry.get("criteria", ())),
            origin="brief",
        ))
    return tuple(subtasks)


def canonical_content(document: dict, materials: tuple[Material, ...]) -> str:
    """What the version hash covers: the brief's own fields and the material bytes.

    A material edited on disk changes the hash even though the brief file did not, which
    is the honest reading: the input to the campaign changed.
    """
    payload = {
        "brief": {key: value for key, value in sorted(document.items()) if key != "version"},
        "materials": [
            {"id": material.ident, "sha256": material.sha256, "bytes": material.size_bytes}
            for material in materials
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def load_brief(path: Path | str, *, allowed_roots: tuple[Path, ...] = ()) -> Brief:
    """Read and validate a brief. Raises BriefError with a message that says how to fix it."""
    path = Path(path).resolve()
    document = load_document(path)
    brief_dir = path.parent

    title = str(_require(document, "title", path))
    brief_id = str(document.get("id") or slugify(title))
    version = document.get("version", 1)
    if not isinstance(version, int) or version < 1:
        raise BriefError(f"{path}: version must be an integer >= 1")

    mode = str(document.get("mode", "debug"))
    if mode not in MODES:
        raise BriefError(f"{path}: mode is {mode!r}; allowed: {MODES}")

    materials = tuple(
        _resolve_material(entry, brief_dir=brief_dir, allowed_roots=allowed_roots, index=index)
        for index, entry in enumerate(document.get("materials", []) or [])
    )
    research_mode = mode == "scientific_research"
    criteria = _parse_criteria(
        document.get("acceptance_criteria") if research_mode
        else _require(document, "acceptance_criteria", path),
        path, required=not research_mode)
    subtasks = _parse_subtasks(document.get("subtasks"), path)

    known = {criterion.ident for criterion in criteria}
    for subtask in subtasks:
        unknown = set(subtask.criteria) - known
        if unknown:
            raise BriefError(
                f"{path}: subtask {subtask.ident} names unknown criteria {sorted(unknown)}"
            )

    limits = document.get("limits") or {}
    if not isinstance(limits, dict):
        raise BriefError(f"{path}: limits must be a mapping")

    return Brief(
        brief_id=brief_id,
        version=version,
        title=title,
        question=str(_require(document, "question", path)),
        context=str(document.get("context", "")),
        expected_result=str(_require(document, "expected_result", path)),
        acceptance_criteria=criteria,
        materials=materials,
        subtasks=subtasks,
        route=str(document.get("route", "full")),
        limits=limits,
        source_path=path,
        content_sha256=sha256_text(canonical_content(document, materials)),
        mode=mode,
        raw=document,
    )
