"""Replace the word LAVORO with PROCEDURE in the live files that route agents today.

Whole files, except docs/REGISTRO.md, where only the rows and sheet lines that route a reader
change (by line number, checked against their text first). Bytes and line endings are kept.
"""
import re
from pathlib import Path

REPO = Path(r"C:/Users/ferra/OneDrive/Desktop/vcc2026")
WHOLE = [
    "CLAUDE.md", "README.md", "configs/CLAUDE.md", "scripts/CLAUDE.md", "reports/CLAUDE.md",
    "reports/invii/README.md", "docs/CLAUDE.md", "docs/AGENTI.md", "docs/AMBITI.md",
    "docs/ERRORI.md", "docs/GENERALIZZAZIONE.md", "docs/PIANI.md", "docs/PROGETTO.md",
    "docs/piani/dati-affidabilita.md", "docs/piani/invii-finale.md",
    "docs/piani/modello-competitivo.md", "docs/piani/revisione-critica.md",
    "tests/test_live_tree.py",
]
REGISTRO_LINES = {115: "| `docs/LAVORO.md` | attuale", 119: "| `src/vcc2026/CLAUDE.md`",
                  310: "| `docs/SOTTOMISSIONE.md`", 979: "- **È ancora usato o citato:**",
                  982: "  I comandi del percorso vivo stanno in"}
WORD = re.compile(rb"\bLAVORO\b")

total = 0
for rel in WHOLE:
    p = REPO / rel
    data = p.read_bytes()
    new, n = WORD.subn(b"PROCEDURE", data)
    if n:
        p.write_bytes(new)
    total += n
    print(f"{rel}: {n}")

p = REPO / "docs" / "REGISTRO.md"
lines = p.read_bytes().split(b"\n")
for number, start in REGISTRO_LINES.items():
    line = lines[number - 1]
    assert line.decode("utf-8").startswith(start), (number, line[:80])
    lines[number - 1], n = WORD.subn(b"PROCEDURE", line)
    total += n
    print(f"docs/REGISTRO.md:{number}: {n}")
p.write_bytes(b"\n".join(lines))
print("total", total)
