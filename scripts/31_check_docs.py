"""Check that the project-understanding docs still describe files that exist.

The failure this guards against is quiet: a report gets renamed, a checkpoint is added
without an index row, a registry entry points at a path that moved, and the map keeps
reading as if it were true. Prose does not fail loudly on its own, so the mechanical
parts of it are checked here — paths, anchors, numbering, required metadata, and the
rule that a flagged document must carry a review sheet.

A path listed in `docs/ARCHIVIO_CODICE.md` counts as existing: that file says which
code was moved into an archive tag on purpose, and with which command it comes back.

It checks structure, never claims: no amount of green output means the science is
right. Standard library only.

    python scripts/31_check_docs.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import re
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
    """Paths that docs/ARCHIVIO_CODICE.md declares archived in a tag.

    Removing code from the branch does not remove it from the project: an annotated
    tag keeps it, and reports and checkpoints go on naming it. A checkpoint cannot be
    corrected, so the check has to tell a path archived on purpose from one that
    vanished by accident -- the first is listed there with the command that brings it
    back, the second is not listed anywhere and is still an error.
    """
    path = root / "docs" / "ARCHIVIO_CODICE.md"
    if not path.exists():
        return frozenset()
    return frozenset(BACKTICK_PATH.findall(path.read_text(encoding="utf-8")))


def is_archived(raw: str) -> bool:
    """True for a listed path, and for a directory that holds one."""
    archived = archived_paths(REPO_ROOT)
    if raw in archived:
        return True
    prefix = raw if raw.endswith("/") else raw + "/"
    return any(entry.startswith(prefix) for entry in archived)


def path_exists(raw: str) -> bool:
    """Repo-relative path, glob allowed. Absolute paths are outside our control."""
    if any(ch in raw for ch in "*?["):
        return any(REPO_ROOT.glob(raw)) or is_archived(raw)
    return (REPO_ROOT / raw).exists() or is_archived(raw)


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
    files += sorted((REPO_ROOT / "docs" / "checkpoints").glob("*.md"))
    for path in files:
        if not path.exists():
            errors.append(f"{path.relative_to(REPO_ROOT)} missing")
            continue
        text = path.read_text(encoding="utf-8")
        for raw in BACKTICK_PATH.findall(text):
            if not path_exists(raw):
                errors.append(f"{path.name}: `{raw}` does not exist")
        for target in MD_LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            file_part, _, anchor = target.partition("#")
            other = path if not file_part else (path.parent / file_part)
            if not other.exists():
                errors.append(f"{path.name}: link to missing {target}")
                continue
            if anchor and anchor not in anchors(other.read_text(encoding="utf-8")):
                errors.append(f"{path.name}: anchor {target} does not resolve")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args()

    errors: list[str] = []
    numbers = check_checkpoints(errors)
    check_index(numbers, errors)
    check_registry(errors)
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
        print(f"{len(archived)} path(s) accepted as archived, from docs/ARCHIVIO_CODICE.md.")
    print("Structure only. This says nothing about whether the claims are true.")


if __name__ == "__main__":
    main()
