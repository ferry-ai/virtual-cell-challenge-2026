"""Create the next numbered checkpoint from the template, without overwriting.

Checkpoints are immutable dated snapshots: the whole point is that an old one keeps
saying what it said. Hand-numbering them invites two sessions to pick the same number
and one to clobber the other, so the number is assigned here.

Three layers guard that, because two agents can run this at the same time:

1. a lock file serialises cooperating runs while they pick a number and touch the index;
2. the checkpoint is created with O_EXCL, so even a run that ignores the lock can never
   overwrite bytes someone else wrote — it fails, or takes the next free number;
3. `31_check_docs.py` still reports duplicate numbers, which is what catches a file
   created by something that bypasses this script entirely.

Everything that can fail is checked before the file is created: a malformed index or a
drifted template must not leave a half-registered checkpoint behind.

Standard library only: this runs with any Python 3.11+, not just the project venv.

    python scripts/30_new_checkpoint.py --slug cd4-benchmark --title "Primo benchmark su CD4"
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKPOINTS = REPO_ROOT / "docs" / "checkpoints"
FILENAME = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
TYPES = ("osservazione", "esperimento", "correzione",
         "cambio-di-strategia", "ricostruzione-retrospettiva")
HEADER_FIELDS = (
    (re.compile(r"^# CP-NNNN — TITOLO$", re.M), "# CP-{number:04d} — {title}"),
    (re.compile(r"^- \*\*Data:\*\* .*$", re.M), "- **Data:** {date}"),
    (re.compile(r"^- \*\*Tipo:\*\* .*$", re.M), "- **Tipo:** {kind}"),
    (re.compile(r"^- \*\*Redatto da:\*\* .*$", re.M), "- **Redatto da:** {author}"),
)
LOCK_TIMEOUT = 15.0
MAX_CLAIM_ATTEMPTS = 50


@contextmanager
def file_lock(path: Path, timeout: float = LOCK_TIMEOUT):
    """Cooperative lock. A leftover lock file is reported, never silently broken."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"{path} still held after {timeout:g}s. Another checkpoint run may be "
                    f"in progress; if none is, delete that file and retry.") from None
            time.sleep(0.05)
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def existing_numbers(directory: Path) -> dict[int, Path]:
    """Checkpoint number -> file, for every NNNN-slug.md in the directory."""
    found: dict[int, Path] = {}
    for path in sorted(directory.glob("*.md")):
        match = FILENAME.match(path.name)
        if match:
            found[int(match.group(1))] = path
    return found


def validate_template(template: str) -> None:
    """Refuse to render from a template whose header no longer matches."""
    for pattern, _ in HEADER_FIELDS:
        if not pattern.search(template):
            raise ValueError(f"TEMPLATE.md no longer contains a line matching {pattern.pattern!r}")


def render(template: str, number: int, title: str, date: str, kind: str, author: str) -> str:
    validate_template(template)
    text = template
    for pattern, replacement in HEADER_FIELDS:
        value = replacement.format(number=number, title=title, date=date,
                                   kind=kind, author=author)
        text = pattern.sub(lambda _, v=value: v, text, count=1)
    return text


def index_table_end(index_text: str) -> int:
    """Line index of the last row of the table under '## Elenco'. Raises if malformed."""
    lines = index_text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "## Elenco")
    except StopIteration:
        raise ValueError("INDICE.md has no '## Elenco' heading to append to") from None
    rows = [i for i in range(start, len(lines)) if lines[i].lstrip().startswith("|")]
    if len(rows) < 2:
        raise ValueError("INDICE.md has no table under '## Elenco'")
    return rows[-1]


def append_index_row(index_text: str, number: int, filename: str,
                     title: str, date: str, kind: str) -> str:
    """Append a row to the table under '## Elenco', keeping the rest untouched."""
    lines = index_text.splitlines()
    row = f"| [{number:04d}]({filename}) | {date} | {title} | {kind} | — |"
    lines.insert(index_table_end(index_text) + 1, row)
    return "\n".join(lines) + "\n"


def claim(directory: Path, slug: str, body) -> tuple[Path, int]:
    """Take the lowest free number and create that file exclusively. Never overwrites.

    `body(number)` renders the text once the number is settled.
    """
    number = max(existing_numbers(directory), default=0) + 1
    for _ in range(MAX_CLAIM_ATTEMPTS):
        # A badly named file still occupies a number, so check the whole prefix, not
        # just the name we are about to write.
        if not any(directory.glob(f"{number:04d}-*")):
            path = directory / f"{number:04d}-{slug}.md"
            # Render before opening: no caller code runs between creating the file and
            # filling it, so the only window left belongs to a process ignoring both
            # the lock and O_EXCL — which `31_check_docs.py` then reports.
            text = body(number)
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                number += 1
                continue
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            return path, number
        number += 1
    raise FileExistsError(f"no free checkpoint number below {number:04d}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", required=True,
                        help="short kebab-case name, e.g. cd4-benchmark")
    parser.add_argument("--title", required=True, help="human title, in Italian")
    parser.add_argument("--type", default="osservazione", choices=TYPES, dest="kind")
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--author", default="agente")
    parser.add_argument("--dir", type=Path, default=CHECKPOINTS)
    args = parser.parse_args()

    if not SLUG.match(args.slug):
        raise ValueError(f"slug must be lowercase kebab-case: {args.slug!r}")
    if "|" in args.title:
        raise ValueError("title cannot contain '|': it would break the index table")
    dt.date.fromisoformat(args.date)

    directory: Path = args.dir
    template_path = directory / "TEMPLATE.md"
    index_path = directory / "INDICE.md"
    if not template_path.exists():
        raise FileNotFoundError(template_path)

    # Everything that can fail is checked here, before anything is written.
    template = template_path.read_text(encoding="utf-8")
    validate_template(template)
    if index_path.exists():
        index_table_end(index_path.read_text(encoding="utf-8"))

    with file_lock(directory / ".INDICE.lock"):
        out, number = claim(directory, args.slug,
                            lambda n: render(template, n, args.title, args.date,
                                             args.kind, args.author))
        if index_path.exists():
            # Re-read inside the lock: a cooperating run may have appended since.
            updated = append_index_row(index_path.read_text(encoding="utf-8"),
                                       number, out.name, args.title, args.date, args.kind)
            index_path.write_text(updated, encoding="utf-8", newline="\n")

    print(f"-> {out.relative_to(REPO_ROOT) if REPO_ROOT in out.parents else out}")
    print("Fill the eight sections. Every observed number needs an evidence path.")
    print("Corrections to earlier checkpoints go in section 7, never by editing them.")


if __name__ == "__main__":
    main()
