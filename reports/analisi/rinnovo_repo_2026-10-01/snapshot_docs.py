"""Preserve the pre-renewal navigation documents; run once from the repository."""

import hashlib
import json
import posixpath
import re
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE = "3de6cd08528574fa033ea0d2855c734b530c2222"
DEST = ROOT / "docs/storico/rinnovo_2026-10-01"
FILES = [
    "README.md", "docs/PROGETTO.md", "docs/PIANI.md",
    "docs/CONSEGNA_TEAMMATE.md", "docs/PROMPT_CLAUDE_TEAMMATE.md",
    "docs/PROCEDURE.md", "reports/README.md", "reports/modelli/README.md",
    "reports/sorgenti/README.md",
    *[f"docs/piani/{name}.md" for name in (
        "strategia-scientifica", "modello-competitivo", "piano-giorno-2026-09-30",
        "revisione-critica", "modello-v2", "dati-affidabilita",
        "switch-distribuzioni", "invii-finale", "trasferimento-modelli",
    )],
]


def main():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != BASE or DEST.exists():
        raise SystemExit("Expected the original HEAD and a fresh snapshot destination")
    mapping = {path: f"docs/storico/rinnovo_2026-10-01/{path}" for path in FILES}
    rows = []
    for name in FILES:
        source = ROOT / name
        raw = source.read_bytes()
        target = ROOT / mapping[name]
        target.parent.mkdir(parents=True, exist_ok=True)

        def rebase(match):
            url = match.group(2)
            if not url or url.startswith(("#", "/")) or re.match(r"[a-zA-Z][\w+.-]*:", url):
                return match.group(0)
            file, sep, anchor = url.partition("#")
            original = posixpath.normpath(posixpath.join(posixpath.dirname(name), file))
            # When both documents were copied, keep the historical relationship.
            destination = mapping.get(original, original)
            relative = posixpath.relpath(destination, posixpath.dirname(mapping[name]))
            return match.group(1) + relative + sep + anchor + match.group(3)

        old = raw.decode("utf-8-sig").replace("\r\n", "\n")
        copied = re.sub(r"(\]\()([^\s)]+)(\))", rebase, old)
        target.write_text(copied, encoding="utf-8", newline="\n")
        rows.append({"source": name, "snapshot": mapping[name],
                     "source_sha256": hashlib.sha256(raw).hexdigest(),
                     "snapshot_sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    manifest = {"base_commit": BASE, "created_at": datetime.now().astimezone().isoformat(),
                "transformation": "UTF-8/LF; relative Markdown links rebased; prose unchanged",
                "files": rows}
    (Path(__file__).parent / "snapshot_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Preserved {len(rows)} documents at {BASE}")


if __name__ == "__main__":
    main()
