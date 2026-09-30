"""Check that the project-understanding docs still describe files that exist.

The failure this guards against is quiet: a report gets renamed, a checkpoint is added
without an index row, a registry entry points at a path that moved, and the map keeps
reading as if it were true. Prose does not fail loudly on its own, so the mechanical
parts of it are checked here — paths, anchors, numbering, required metadata, and the
rule that a flagged document must carry a review sheet.

A path listed in `docs/ARCHIVIO.md` counts as existing: that file says which code and
documents were moved into an archive tag on purpose, and with which command they come
back. A path that disappears without being listed there is still an error. A live document
renamed on purpose is listed there too, in the table "Nomi cambiati": its old name is
followed to the new one, anchors included.

It checks structure, never claims: no amount of green output means the science is
right. Standard library only.

With `--status`, it checks nothing and answers one question instead: can I rely on this
document? It prints the registry entries that cover each path, the review sheet to read and,
for a checkpoint, what corrected it, so an agent does not read the whole registry for a row.

    python scripts/31_check_docs.py
    python scripts/31_check_docs.py --status docs/SOTTOMISSIONE.md reports/trial_2026-09-13/
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DOC_STATUSES = ("attuale", "da-verificare", "superato", "storico")
DATA_KINDS = ("grezzo", "derivato", "campione", "temporaneo")
DECISION_STATUSES = ("attiva", "da-verificare", "superata")
CHECKPOINT_TYPES = ("osservazione", "esperimento", "correzione",
                    "cambio-di-strategia", "ricostruzione-retrospettiva")
CHECKPOINT_SECTIONS = ("1. Domanda", "2. Cosa", "3. Cosa", "4. Interpretazione",
                       "5. Spiegazione", "6. Conseguenze", "7. Cosa", "8. Domanda")
SHEET_FIELDS = ("Perché è segnalato:", "Affermazioni contestate:", "Evidenza contraria:",
                "Cosa resta valido:", "È ancora usato o citato:", "Disposizione proposta:",
                "Cosa chiuderebbe la revisione:")

CHECKPOINT_FILE = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
BACKTICK_PATH = re.compile(r"`((?:docs|scripts|src|reports|configs|tests)/[^`\s]*|README\.md|CLAUDE\.md)`")
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def slug(heading: str) -> str:
    """GitHub-style anchor: drop the leading #, lowercase, drop punctuation."""
    text = heading.lstrip("#").strip().lower()
    text = "".join(c for c in text if c.isalnum() or c in " _-")
    return text.replace(" ", "-")


def anchors(text: str) -> set[str]:
    return {slug(line) for line in text.splitlines() if line.startswith("#")}


def tables(text: str) -> list[tuple[int, list[str], list[list[str]]]]:
    """Every markdown table: (1-based line of the header, header cells, data rows)."""
    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    found, lines, i = [], text.splitlines(), 0
    while i < len(lines) - 1:
        if lines[i].lstrip().startswith("|") and set(lines[i + 1].strip()) <= set("|-: "):
            header, rows, j = cells(lines[i]), [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append(cells(lines[j]))
                j += 1
            found.append((i + 1, header, rows))
            i = j
        else:
            i += 1
    return found


def table_by_first_column(text: str, name: str, path: Path, errors: list[str]):
    for _, header, rows in tables(text):
        if header and header[0] == name:
            return header, rows
    errors.append(f"{path.name}: no table whose first column is {name!r}")
    return None, []


@functools.lru_cache(maxsize=None)
def archived_paths(root: Path) -> frozenset[str]:
    """Paths that docs/ARCHIVIO.md declares archived in a tag.

    Checkpoints cannot be corrected, so they go on naming code and documents that
    left the working tree. The archive list is what tells a path removed on purpose
    (listed there, with the command that brings it back) from one that vanished by
    accident (listed nowhere, still an error).
    """
    path = root / "docs" / "ARCHIVIO.md"
    if not path.exists():
        return frozenset()
    # Only the first cell of a table row lists an archived path: the prose around the
    # tables also names paths, including live ones, and those must not count.
    found: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| `"):
            found.update(BACKTICK_PATH.findall(line.split("|")[1]))
    # A renamed document did not leave the tree: its old name is followed, not accepted.
    return frozenset(found - set(renamed_paths(root)))


@functools.lru_cache(maxsize=None)
def renamed_paths(root: Path) -> dict[str, str]:
    """Old name -> new name of the paths renamed on purpose, from docs/ARCHIVIO.md.

    The table whose first column is "Nome vecchio" is the one list. A renamed document keeps
    its text and its headings under the new name, while checkpoints and reports, never edited,
    go on citing the old one. An entry ending in '/' renames everything below it.
    `src/vcc2026/config.py` (`repo_file`) reads the same table.
    """
    path = root / "docs" / "ARCHIVIO.md"
    if not path.exists():
        return {}
    found: dict[str, str] = {}
    for _, header, rows in tables(path.read_text(encoding="utf-8")):
        if not header or header[0] != "Nome vecchio":
            continue
        for row in rows:
            names = [re.findall(r"`([^`]+)`", cell) for cell in row[:2]]
            if len(names) == 2 and names[0] and names[1]:
                found[names[0][0]] = names[1][0]
    return found


def renamed(raw: str) -> str | None:
    """The current name of a path renamed on purpose, or None if it was not renamed."""
    for old, new in renamed_paths(REPO_ROOT).items():
        if raw in (old, old.rstrip("/")):
            return new
        if old.endswith("/") and raw.startswith(old):
            return new + raw[len(old):]
    return None


def is_archived(raw: str) -> bool:
    """A listed path, a path under a listed directory, or a directory holding one."""
    archived = archived_paths(REPO_ROOT)
    if raw in archived:
        return True
    if any(entry.endswith("/") and raw.startswith(entry) for entry in archived):
        return True
    prefix = raw if raw.endswith("/") else raw + "/"
    return any(entry.startswith(prefix) for entry in archived)


def moved(raw: str) -> list[Path]:
    """Where a path under reports/ or docs/ lives after the move of 28 September 2026 (D-046).

    The report folders went one level down, into category folders, and eight analyses went
    into docs/storico/, all with their names unchanged. Checkpoints and reports are never
    edited, so they go on naming the old places: such a path is looked for one level below its
    first folder. `src/vcc2026/config.py` (`repo_file`) follows the same rule for recipes.
    """
    parts = Path(raw).parts
    if len(parts) < 2 or parts[0] not in ("reports", "docs") or not (REPO_ROOT / parts[0]).is_dir():
        return []
    root, rest = REPO_ROOT / parts[0], Path(*parts[1:]).as_posix()
    if any(ch in rest for ch in "*?["):
        return [hit for folder in sorted(root.iterdir()) if folder.is_dir() for hit in folder.glob(rest)]
    return [folder / rest for folder in sorted(root.iterdir())
            if folder.is_dir() and ((folder / rest).exists() or documented_outside_repo(folder / rest))]


def data_suffixes() -> set[str]:
    """Extensions `.gitignore` keeps out of the repository, read from the file itself."""
    path = REPO_ROOT / ".gitignore"
    if not path.exists():
        return set()
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if entry.startswith("*.") and not any(ch in entry[2:] for ch in "*?[]/"):
            found.add(entry[1:])
    return found


def documented_outside_repo(target: Path) -> bool:
    """A heavy artifact `.gitignore` excludes, vouched for by the manifest beside it.

    D-001 keeps data out of the repository, so a clone never contains the `.h5ad` a
    registry row names: only its manifest travels. Accepting the pair keeps the check
    meaningful, because a path with no manifest beside it is still a broken path, and
    keeps the result the same on a fresh clone as on the machine that produced it.
    """
    if target.suffix not in data_suffixes():
        return False
    return (target.parent / f"{target.stem}.manifest.json").exists()


def path_exists(raw: str) -> bool:
    """Repo-relative path, glob allowed. Absolute paths are outside our control.

    A path renamed on purpose exists if its new name does.
    """
    new = renamed(raw)
    return exists_as_named(raw) or (new is not None and exists_as_named(new))


def exists_as_named(raw: str) -> bool:
    """On disk, beside its manifest, archived in a tag, or moved one level down (D-046)."""
    if any(ch in raw for ch in "*?["):
        return any(REPO_ROOT.glob(raw)) or is_archived(raw) or bool(moved(raw))
    target = REPO_ROOT / raw
    return (target.exists() or documented_outside_repo(target) or is_archived(raw)
            or len(moved(raw)) == 1)


def is_repo_relative(raw: str) -> bool:
    return not (len(raw) > 1 and raw[1] == ":") and not raw.startswith(("/", "http"))


def check_checkpoints(errors: list[str]) -> dict[int, Path]:
    directory = REPO_ROOT / "docs" / "checkpoints"
    numbers: dict[int, Path] = {}
    for path in sorted(directory.glob("*.md")):
        match = CHECKPOINT_FILE.match(path.name)
        if not match:
            if path.name not in ("TEMPLATE.md", "INDICE.md"):
                errors.append(f"{path.name}: not named NNNN-slug.md")
            continue
        number = int(match.group(1))
        if number in numbers:
            errors.append(f"checkpoint {number:04d} used twice: {numbers[number].name}, {path.name}")
        numbers[number] = path
        text = path.read_text(encoding="utf-8")

        title = re.search(r"^# CP-(\d{4}) — .+$", text, re.M)
        if not title:
            errors.append(f"{path.name}: first heading must be '# CP-NNNN — <titolo>'")
        elif int(title.group(1)) != number:
            errors.append(f"{path.name}: title says CP-{title.group(1)}, filename says {number:04d}")

        date = re.search(r"^- \*\*Data:\*\* (\S+)$", text, re.M)
        if not date:
            errors.append(f"{path.name}: missing '- **Data:** AAAA-MM-GG'")
        else:
            try:
                dt.date.fromisoformat(date.group(1))
            except ValueError:
                errors.append(f"{path.name}: Data {date.group(1)!r} is not a YYYY-MM-DD date")

        kind = re.search(r"^- \*\*Tipo:\*\* (.+)$", text, re.M)
        if not kind:
            errors.append(f"{path.name}: missing '- **Tipo:**'")
        elif kind.group(1).strip() not in CHECKPOINT_TYPES:
            errors.append(f"{path.name}: Tipo {kind.group(1)!r} not in {CHECKPOINT_TYPES}")

        for field in ("Redatto da:", "Revisione umana:", "Stato:"):
            if f"**{field}**" not in text:
                errors.append(f"{path.name}: missing '- **{field}**'")
        for section in CHECKPOINT_SECTIONS:
            if not re.search(rf"^## {re.escape(section)}", text, re.M):
                errors.append(f"{path.name}: missing section '## {section}...'")
    if not numbers:
        errors.append("docs/checkpoints: no checkpoint found")
    return numbers


def check_index(numbers: dict[int, Path], errors: list[str]) -> None:
    path = REPO_ROOT / "docs" / "checkpoints" / "INDICE.md"
    if not path.exists():
        errors.append("docs/checkpoints/INDICE.md missing")
        return
    text = path.read_text(encoding="utf-8")
    _, rows = table_by_first_column(text, "N", path, errors)
    listed: dict[int, str] = {}
    for row in rows:
        link = MD_LINK.search(row[0])
        if not link:
            errors.append(f"INDICE.md: row {row[0]!r} does not link to a checkpoint file")
            continue
        target = link.group(1)
        if not (path.parent / target).exists():
            errors.append(f"INDICE.md: row links to missing file {target}")
            continue
        match = CHECKPOINT_FILE.match(target)
        if match:
            listed[int(match.group(1))] = target
    for number, file in numbers.items():
        if number not in listed:
            errors.append(f"INDICE.md: no row for {file.name}")
    for number in listed:
        if number not in numbers:
            errors.append(f"INDICE.md: row {number:04d} has no checkpoint file")


def corrections() -> dict[str, str]:
    """Checkpoint file name -> the column "Corretto da" of its index row, when it is filled."""
    path = REPO_ROOT / "docs" / "checkpoints" / "INDICE.md"
    if not path.exists():
        return {}
    _, rows = table_by_first_column(path.read_text(encoding="utf-8"), "N", path, [])
    found = {}
    for row in rows:
        link = MD_LINK.search(row[0])
        if link and len(row) >= 5 and row[4] not in ("", "—"):
            found[link.group(1)] = row[4]
    return found


def check_corrected_checkpoints(errors: list[str]) -> None:
    """A corrected checkpoint's own registry row must not read as a plain 'attuale'.

    Checkpoints are never edited: a correction lives in a later checkpoint and in the index
    column "Corretto da". A registry row of its own that says `attuale` must name the correcting
    checkpoint in its note, or take another state. Rows that cover only the folder are left to
    --status, which prints the correction first.
    """
    fixed = corrections()
    path = REPO_ROOT / "docs" / "REGISTRO.md"
    if not fixed or not path.exists():
        return
    _, docs = table_by_first_column(path.read_text(encoding="utf-8"), "Percorso", path, [])
    for row in docs:
        if len(row) < 5 or row[1] != "attuale":
            continue
        for raw in BACKTICK_PATH.findall(row[0]):
            name = Path(raw).name
            if raw.startswith("docs/checkpoints/") and name in fixed:
                numbers = re.findall(r"\[(\d{4})\]", fixed[name])
                if not any(number in row[3] for number in numbers):
                    errors.append(f"REGISTRO.md: {raw} is 'attuale' but was corrected by "
                                  f"{', '.join(numbers)} (INDICE, Corretto da): name it in the note")


def check_registry(errors: list[str]) -> None:
    path = REPO_ROOT / "docs" / "REGISTRO.md"
    if not path.exists():
        errors.append("docs/REGISTRO.md missing")
        return
    text = path.read_text(encoding="utf-8")
    present = anchors(text)
    sheets = set(re.findall(r"^### (R-\d{3}) ", text, re.M))
    referenced: set[str] = set()

    _, docs = table_by_first_column(text, "Percorso", path, errors)
    for row in docs:
        if len(row) < 5:
            errors.append(f"REGISTRO.md: document row has {len(row)} cells, expected 5: {row[0]}")
            continue
        target, status, replaced, sheet = row[0], row[1], row[2], row[4]
        for raw in BACKTICK_PATH.findall(target):
            if not path_exists(raw):
                errors.append(f"REGISTRO.md: registered path does not exist: {raw}")
        if status not in DOC_STATUSES:
            errors.append(f"REGISTRO.md: status {status!r} for {target} not in {DOC_STATUSES}")
        if status == "superato" and replaced in ("", "—"):
            errors.append(f"REGISTRO.md: {target} is 'superato' without naming what replaced it")
        link = re.search(r"\[(R-\d{3})\]\(#([^)]+)\)", sheet)
        if link:
            referenced.add(link.group(1))
            if link.group(1) not in sheets:
                errors.append(f"REGISTRO.md: {target} points at missing sheet {link.group(1)}")
            elif link.group(2) not in present:
                errors.append(f"REGISTRO.md: anchor #{link.group(2)} does not resolve")
        elif status in ("da-verificare", "superato"):
            errors.append(f"REGISTRO.md: {target} is {status!r} but has no review sheet link")

    _, data = table_by_first_column(text, "Identificatore", path, errors)
    for row in data:
        if len(row) < 6:
            errors.append(f"REGISTRO.md: data row has {len(row)} cells, expected 6: {row[0]}")
            continue
        for raw in BACKTICK_PATH.findall(row[0]):
            if is_repo_relative(raw) and not path_exists(raw):
                errors.append(f"REGISTRO.md: registered data path does not exist: {raw}")
        if row[1] not in DATA_KINDS:
            errors.append(f"REGISTRO.md: data kind {row[1]!r} not in {DATA_KINDS}")
        if row[2] not in DOC_STATUSES:
            errors.append(f"REGISTRO.md: data status {row[2]!r} not in {DOC_STATUSES}")

    for sheet in sorted(sheets - referenced):
        errors.append(f"REGISTRO.md: sheet {sheet} is not referenced by any row")
    for sheet in sorted(sheets):
        body = re.split(rf"^### {sheet} ", text, flags=re.M)[1].split("\n### ")[0]
        for field in SHEET_FIELDS:
            if f"**{field}**" not in body:
                errors.append(f"REGISTRO.md: sheet {sheet} is missing '**{field}**'")

    check_coverage([row[0] for row in docs + data], errors)


def covered_paths(cells: list[str]) -> set[str]:
    """Every repo file a registry entry claims, by the documented entry scope.

    An entry ending in '/' covers that directory and everything below it; an entry
    with a wildcard covers what it matches; anything else covers exactly that file.
    """
    covered: set[str] = set()
    for cell in cells:
        for raw in BACKTICK_PATH.findall(cell):
            if not is_repo_relative(raw):
                continue
            if any(ch in raw for ch in "*?["):
                matched = REPO_ROOT.glob(raw)
            elif raw.endswith("/"):
                matched = (REPO_ROOT / raw).rglob("*")
            else:
                matched = [REPO_ROOT / raw]
            for path in matched:
                if path.is_file():
                    covered.add(path.relative_to(REPO_ROOT).as_posix())
    return covered


def check_coverage(cells: list[str], errors: list[str]) -> None:
    """Every file under docs/ and reports/ must fall inside some registry entry."""
    covered = covered_paths(cells)
    for root in ("docs", "reports"):
        for path in sorted((REPO_ROOT / root).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.name.startswith("."):
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel not in covered:
                errors.append(f"REGISTRO.md: {rel} exists but no registry entry covers it")


def check_decisions(errors: list[str]) -> None:
    path = REPO_ROOT / "docs" / "DECISIONI.md"
    if not path.exists():
        errors.append("docs/DECISIONI.md missing")
        return
    text = path.read_text(encoding="utf-8")
    _, rows = table_by_first_column(text, "ID", path, errors)
    detailed = set(re.findall(r"^### (D-\d{3}) — ", text, re.M))
    listed: set[str] = set()
    for row in rows:
        if not re.fullmatch(r"D-\d{3}", row[0]):
            errors.append(f"DECISIONI.md: id {row[0]!r} is not D-NNN")
            continue
        if row[0] in listed:
            errors.append(f"DECISIONI.md: id {row[0]} appears twice")
        listed.add(row[0])
        if len(row) < 3 or row[2] not in DECISION_STATUSES:
            errors.append(f"DECISIONI.md: {row[0]} status not in {DECISION_STATUSES}")
        if row[0] not in detailed:
            errors.append(f"DECISIONI.md: {row[0]} has no '### {row[0]} — ...' section")
    for decision in sorted(detailed - listed):
        errors.append(f"DECISIONI.md: {decision} has a section but no table row")


def check_links(errors: list[str]) -> None:
    files = [REPO_ROOT / "README.md", REPO_ROOT / "CLAUDE.md",
             REPO_ROOT / "docs" / "PROGETTO.md", REPO_ROOT / "docs" / "REGISTRO.md",
             REPO_ROOT / "docs" / "DECISIONI.md"]
    # The working guide and the archive list are checked when present: an entry point
    # that names a missing stage misdirects the next agent before anything else can.
    files += [path for path in (REPO_ROOT / "docs" / "PROCEDURE.md",
                                REPO_ROOT / "docs" / "ARCHIVIO.md") if path.exists()]
    # So are the folder guides (D-043): the paths they route agents to must exist.
    files += [path for path in (REPO_ROOT / "AGENTS.md", REPO_ROOT / "src" / "vcc2026" / "CLAUDE.md")
              if path.exists()]
    files += sorted(REPO_ROOT.glob("*/CLAUDE.md"))
    files += sorted((REPO_ROOT / "docs" / "checkpoints").glob("*.md"))
    # The plan index and cards, the research rules and the indexes of reports/ and docs/storico/
    # route agents too (D-046): a link there to a report that was never committed is caught.
    files += [path for path in (REPO_ROOT / "docs" / "PIANI.md", REPO_ROOT / "docs" / "GENERALIZZAZIONE.md",
                                REPO_ROOT / "reports" / "README.md") if path.exists()]
    # The map by area and the errors not to repeat are read at the start of every task (D-048),
    # and the page of the agent infrastructure routes to what lives outside the repository (D-049).
    files += [path for path in (REPO_ROOT / "docs" / "AMBITI.md", REPO_ROOT / "docs" / "ERRORI.md",
                                REPO_ROOT / "docs" / "AGENTI.md") if path.exists()]
    files += sorted((REPO_ROOT / "docs" / "piani").glob("*.md"))
    files += sorted((REPO_ROOT / "docs" / "storico").glob("README.md"))
    files += sorted((REPO_ROOT / "reports").glob("*/README.md"))
    for path in files:
        if not path.exists():
            errors.append(f"{path.relative_to(REPO_ROOT)} missing")
            continue
        text = path.read_text(encoding="utf-8")
        # Several guides are called CLAUDE.md: name the file by its path.
        label = path.relative_to(REPO_ROOT).as_posix()
        for raw in BACKTICK_PATH.findall(text):
            if "<" in raw:
                continue  # a template such as reports/trial_<data>/ names no file
            if not path_exists(raw):
                errors.append(f"{label}: `{raw}` does not exist")
        for target in MD_LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            file_part, _, anchor = target.partition("#")
            other = path if not file_part else Path(os.path.normpath(path.parent / file_part))
            if not other.exists():
                try:
                    rel = other.relative_to(REPO_ROOT).as_posix()
                except ValueError:
                    rel = None
                new = renamed(rel) if rel is not None else None
                if new is not None:
                    found = [REPO_ROOT / new]  # its anchors are checked in the renamed file
                else:
                    found = moved(rel) if rel is not None else []
                if len(found) == 1 and found[0].exists():
                    other = found[0]
                else:
                    if rel is None or not is_archived(rel):
                        errors.append(f"{label}: link to missing {target}")
                    continue
            if other.is_dir():
                continue
            if anchor and anchor not in anchors(other.read_text(encoding="utf-8")):
                errors.append(f"{label}: anchor {target} does not resolve")


def entry_covers(entry: str, rel: str) -> bool:
    """Whether a registry entry covers a path, by the scope documented in REGISTRO.md."""
    if any(ch in entry for ch in "*?["):
        return is_repo_relative(entry) and (REPO_ROOT / rel) in set(REPO_ROOT.glob(entry))
    if entry.endswith("/"):
        return rel == entry.rstrip("/") or rel.startswith(entry)
    return rel == entry


def index_verdicts(rel: str) -> list[str]:
    """The column "Vale?" of the folder index that lists the path, if one does.

    Report folders are indexed by the README of their category, and the texts of docs/storico/
    by its README. Those columns and the registry are kept apart and can disagree: printing both
    shows the disagreement instead of hiding it.
    """
    parts = rel.split("/")
    if len(parts) >= 3 and parts[0] == "reports":
        index = REPO_ROOT / "reports" / parts[1] / "README.md"
    elif len(parts) >= 3 and parts[:2] == ["docs", "storico"]:
        index = REPO_ROOT / "docs" / "storico" / "README.md"
    else:
        return []
    if not index.exists():
        return []
    lines = []
    for _, header, rows in tables(index.read_text(encoding="utf-8")):
        names = [i for i, cell in enumerate(header) if cell in ("Cartella", "File")]
        if "Vale?" not in header or not names:
            continue
        verdict, name = header.index("Vale?"), names[0]
        for row in rows:
            if len(row) > max(verdict, name) and any(
                    link.rstrip("/") == parts[2] for link in re.findall(r"\]\(([^)#\s]+)\)", row[name])):
                lines.append(f"  index {index.relative_to(REPO_ROOT).as_posix()}, Vale?: {row[verdict]}")
    return lines


def registry_status(raw: str) -> list[str]:
    """What the registry, the checkpoint index and the folder indexes say about one path.

    The registry entries that cover the path come most specific first: the file itself, then
    the folders above it. A path written before 28 September is followed into its category
    first (`moved`), and a document renamed on purpose to its new name (`renamed`), since
    checkpoints go on citing the old places. An empty list means that nothing covers or indexes
    the path.
    """
    rel = raw.replace("\\", "/").strip().removeprefix("./").rstrip("/")
    followed = None
    if is_repo_relative(rel) and not (REPO_ROOT / rel).exists():
        new = renamed(rel)
        found = [REPO_ROOT / new] if new is not None else moved(rel)
        if len(found) == 1:
            rel = found[0].relative_to(REPO_ROOT).as_posix().rstrip("/")
            followed = (f"  renamed: now {rel} (docs/ARCHIVIO.md, \"Nomi cambiati\")" if new is not None
                        else f"  now at {rel} (moved on 28 September, D-046)")
    path = REPO_ROOT / "docs" / "REGISTRO.md"
    text = path.read_text(encoding="utf-8")
    sheets = {m.group(1): m.group(0).lstrip("# ").strip()
              for m in re.finditer(r"^### (R-\d{3}) .*$", text, re.M)}
    ignored: list[str] = []
    _, docs = table_by_first_column(text, "Percorso", path, ignored)
    _, data = table_by_first_column(text, "Identificatore", path, ignored)
    hits = []
    for row in docs:
        for entry in re.findall(r"`([^`]+)`", row[0]):
            if len(row) >= 5 and entry_covers(entry, rel):
                hits.append((len(entry), entry, row[1], row[2], row[3], row[4]))
    for row in data:
        for entry in re.findall(r"`([^`]+)`", row[0]):
            if len(row) >= 6 and entry_covers(entry, rel):
                hits.append((len(entry), entry, row[2], "—", row[5], "—"))
    lines = []
    for _, entry, status, replaced, note, sheet in sorted(hits, key=lambda hit: -hit[0]):
        lines.append(f"  {status}  (entry `{entry}`)")
        if replaced not in ("", "—"):
            lines.append(f"    replaced by: {replaced}")
        link = re.search(r"\[(R-\d{3})\]\(#([^)]+)\)", sheet)
        if link:
            lines.append(f"    review sheet: {sheets.get(link.group(1), link.group(1))} "
                         f"(docs/REGISTRO.md#{link.group(2)})")
        lines.append(f"    note: {note}")
    match = CHECKPOINT_FILE.match(Path(rel).name)
    if lines and rel.startswith("docs/checkpoints/") and match:
        fix = corrections().get(Path(rel).name)
        if fix:
            # First, before the registry's state: a corrected checkpoint holds only as amended.
            lines.insert(0, f"  corrected: read {fix} (docs/checkpoints/INDICE.md, Corretto da)")
        else:
            lines.append("  docs/checkpoints/INDICE.md, Corretto da: —")
    if not lines:
        lines.append("  no registry entry covers this path")
    lines += index_verdicts(rel)
    if len(lines) == 1 and not hits:
        return []
    if followed:
        lines.insert(0, followed)
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--status", nargs="+", metavar="PATH",
                        help="print what docs/REGISTRO.md says about these paths, and check nothing")
    args = parser.parse_args()

    if args.status:
        # Registry notes carry characters a Windows console codepage lacks (Δ, γ, ≥).
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        uncovered = 0
        for raw in args.status:
            lines = registry_status(raw)
            print(raw)
            print("\n".join(lines) if lines else "  no registry entry covers this path")
            uncovered += not any("(entry `" in line for line in lines)
        raise SystemExit(1 if uncovered else 0)

    errors: list[str] = []
    numbers = check_checkpoints(errors)
    check_index(numbers, errors)
    check_registry(errors)
    check_corrected_checkpoints(errors)
    check_decisions(errors)
    check_links(errors)

    if errors:
        print(f"{len(errors)} problem(s):")
        for error in errors:
            print(f"  - {error}")
        raise SystemExit(1)
    archived = archived_paths(REPO_ROOT)
    print(f"OK: {len(numbers)} checkpoint(s), registry, decisions and links are consistent.")
    if archived:
        print(f"{len(archived)} path(s) accepted as archived, from docs/ARCHIVIO.md.")
    print("Structure only. This says nothing about whether the claims are true.")


if __name__ == "__main__":
    main()
