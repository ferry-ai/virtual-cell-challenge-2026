"""Normalize changed document endings and enumerate only this renewal's files."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
for name in ("docs/piani/trasferimento-modelli.md", "reports/modelli/README.md"):
    file = ROOT / name
    file.write_text(file.read_text(encoding="utf-8").rstrip() + "\n", encoding="utf-8", newline="\n")
base = json.loads((HERE / "snapshot_manifest.json").read_text(encoding="utf-8"))["base_commit"]
paths = set(subprocess.check_output(["git", "-c", "core.safecrlf=false", "diff", "--name-only", base], cwd=ROOT, text=True).splitlines())
paths.discard("docs/SOTTOMISSIONE.md")  # Only line-ending noise from the navigation script; restored separately.
paths.add("docs/PROMPT_CLAUDE.md")
for directory in (ROOT / "docs/storico/rinnovo_2026-10-01", HERE):
    paths.update(file.relative_to(ROOT).as_posix() for file in directory.rglob("*") if file.is_file() and "__pycache__" not in file.parts)
paths.add("reports/analisi/rinnovo_repo_2026-10-01/stage_paths.json")
(HERE / "stage_paths.json").write_text(json.dumps(sorted(paths), indent=2) + "\n", encoding="utf-8")
print("\n".join(sorted(paths)))
