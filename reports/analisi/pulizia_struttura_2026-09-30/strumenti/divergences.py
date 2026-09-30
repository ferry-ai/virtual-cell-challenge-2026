"""Read-only: registry state versus the "Vale?" column of the folder index, for every indexed entry.

Prints only pairs where the two plainly disagree: the registry says attuale while the index says
superato, chiuso, storico, no or in parte; or the registry says superato/storico while the index
says sì. Everything else (same meaning, or an index verdict with nuances) is counted, not printed.
"""
import importlib.util
import re
from pathlib import Path

REPO = Path(r"C:/Users/ferra/OneDrive/Desktop/vcc2026")
spec = importlib.util.spec_from_file_location("cd", REPO / "scripts" / "31_check_docs.py")
cd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cd)

reg = (REPO / "docs" / "REGISTRO.md").read_text(encoding="utf-8")
_, docs = cd.table_by_first_column(reg, "Percorso", Path("x"), [])
state = {}
for row in docs:
    for entry in re.findall(r"`([^`]+)`", row[0]):
        state[entry.rstrip("/")] = row[1]

indexes = sorted((REPO / "reports").glob("*/README.md")) + [REPO / "docs" / "storico" / "README.md"]
agree = disagree = missing = 0
for index in indexes:
    base = index.parent.relative_to(REPO).as_posix()
    for _, header, rows in cd.tables(index.read_text(encoding="utf-8")):
        names = [i for i, c in enumerate(header) if c in ("Cartella", "File")]
        if "Vale?" not in header or not names:
            continue
        v, n = header.index("Vale?"), names[0]
        for row in rows:
            if len(row) <= max(v, n):
                continue
            links = re.findall(r"\]\(([^)#\s]+)\)", row[n])
            if not links:
                continue
            path = f"{base}/{links[0]}".rstrip("/")
            verdict = row[v].lower()
            st = state.get(path)
            if st is None:
                missing += 1
                continue
            neg = re.match(r"(superato|chiuso|storico|no\b|in parte|scartat|ritirat)", verdict)
            pos = re.match(r"(sì|si\b|attuale)", verdict)
            if (st == "attuale" and neg) or (st in ("superato", "storico") and pos):
                disagree += 1
                print(f"{st:13} | {path} | index: {row[v][:120]}")
            else:
                agree += 1
print(f"\nagree or nuanced: {agree}; plainly disagree: {disagree}; indexed without own registry row: {missing}")
